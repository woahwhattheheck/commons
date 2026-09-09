# SPDX-License-Identifier: Apache-2.0
"""Candidate carrier that preserves only committed TITAN continuity state.

Canonical ``main.py`` intentionally discards an instance if its whole-call timer
interrupts a call.  Discarding the possibly-mutated object is correct, but the
object also owns three explicitly committed/replayable fields:
``_completed_route``, ``_completed_seller_state``, and
``_seller_fallback_observations``.  Depending on the interruption point, the
current public observation may already be represented by the seller checkpoint,
may already be queued as a fallback, or may still be missing.  This candidate
transfers only those fields and records the current observation only when neither
safe surface covers it.  Policy, controller, finalizers, and returned actions
remain canonical.

The capsule is JSON-canonical, content-addressed, deep-copied, and cleared at a
true episode step zero.  Any malformed or drifted state degrades to the original
canonical construction path rather than raising in gameplay.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable, Mapping

SCHEMA = "titan.outer-recovery.v1"
_SAFE_FIELDS = (
    "_completed_route",
    "_completed_seller_state",
    "_seller_fallback_observations",
)


def _canonical_bytes(value: Any) -> bytes:
    """Serialize a recovery payload without accepting NaN or custom objects."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _absolute_step(observation: Mapping[str, Any], configuration: Mapping[str, Any] | None) -> int:
    raw = observation.get("step")
    if raw is not None:
        return int(raw)
    cfg = dict(configuration or {})
    return int(observation.get("day", 0)) * int(cfg.get("turnsPerDay", 24)) + int(
        observation.get("hour", 0)
    )


def _step_from_public(value: Any) -> int | None:
    """Return one non-boolean public step, or ``None`` for malformed state."""
    if not isinstance(value, Mapping) or "step" not in value:
        return None
    raw = value.get("step")
    return _nonnegative_int(raw)


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value >= 0 else None


def _public_observation_shape(value: Any) -> tuple[int, int, tuple[int, ...]] | None:
    """Validate TITAN's exact seller-public observation projection.

    Return ``(step, player, rival_row_widths)`` so a caller can also prove that
    every replay row shares one board shape and seat.
    """
    if not isinstance(value, Mapping) or set(value) != {"step", "player", "farms"}:
        return None
    step = _nonnegative_int(value.get("step"))
    player = _nonnegative_int(value.get("player"))
    farms = value.get("farms")
    if step is None or player not in (0, 1) or not isinstance(farms, list) or len(farms) != 2:
        return None
    for index, farm in enumerate(farms):
        if not isinstance(farm, Mapping) or set(farm) != {"tiles"}:
            return None
        tiles = farm.get("tiles")
        if not isinstance(tiles, list):
            return None
        if index == player:
            if tiles:
                return None
            continue
        for row in tiles:
            if not isinstance(row, list):
                return None
            if any(tile is not None and not isinstance(tile, Mapping) for tile in row):
                return None
    rival = farms[1 - player]["tiles"]
    return step, player, tuple(len(row) for row in rival)


def _schedule_map_shape(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    for item, rows in value.items():
        if not isinstance(item, str) or not isinstance(rows, (list, tuple)):
            return False
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) != 2:
                return False
            if _nonnegative_int(row[0]) is None or _nonnegative_int(row[1]) is None:
                return False
    return True


def _seller_payload_shape(seller: Any, fallbacks: Any) -> tuple[bool, str]:
    """Validate every field consumed by ``TitanAgent._restore_seller_state``."""
    if seller is not None:
        if not isinstance(seller, Mapping):
            return False, "malformed_checkpoint"
        if set(seller) != {"planned", "pending", "previous", "observed_harvests"}:
            return False, "malformed_checkpoint_keys"
        if not _schedule_map_shape(seller.get("planned")):
            return False, "malformed_planned"
        pending = seller.get("pending")
        if not isinstance(pending, Mapping) or any(
            not isinstance(item, str) or _nonnegative_int(quantity) is None
            for item, quantity in pending.items()
        ):
            return False, "malformed_pending"
        if not _schedule_map_shape(seller.get("observed_harvests")):
            return False, "malformed_harvests"
    if not isinstance(fallbacks, list):
        return False, "malformed_fallbacks"

    public_rows = []
    if seller is not None and seller.get("previous") is not None:
        public_rows.append(("checkpoint", seller.get("previous")))
    public_rows.extend(("fallback", row) for row in fallbacks)
    parsed = []
    for kind, row in public_rows:
        shape = _public_observation_shape(row)
        if shape is None:
            return False, f"malformed_{kind}_observation"
        parsed.append((kind, shape))
    if parsed:
        first_player = parsed[0][1][1]
        first_widths = parsed[0][1][2]
        if any(shape[1] != first_player for _kind, shape in parsed):
            return False, "seller_player_drift"
        if any(shape[2] != first_widths for _kind, shape in parsed):
            return False, "seller_board_drift"
    return True, "valid"


def _committed_shape(route: Any, seller: Any, fallbacks: Any) -> tuple[bool, str]:
    if route is not None and not isinstance(route, str):
        return False, "route"
    return _seller_payload_shape(seller, fallbacks)


def _seller_observation_coverage(instance: Any, step: int) -> tuple[bool, str]:
    """Prove whether committed seller state already represents ``step``.

    A completed call checkpoints ``consumer.previous`` at the current step and
    clears the fallback queue.  An inner deadline instead leaves the prior
    checkpoint and queues the current public observation.  The outer timer can
    interrupt after either event, so blindly appending would double-observe a
    completed step.  Reject malformed, reordered, or future state rather than
    guessing which mutation completed.
    """
    features = getattr(instance, "features", None)
    consumer = getattr(features, "consumer", None)
    if consumer is not None and consumer != "frozen":
        return True, "not_applicable"

    seller = getattr(instance, "_completed_seller_state", None)
    fallbacks = getattr(instance, "_seller_fallback_observations", None)
    valid, reason = _seller_payload_shape(seller, fallbacks)
    if not valid:
        return False, reason

    checkpoint_step = None
    if seller is not None:
        previous = seller.get("previous")
        if previous is not None:
            checkpoint_step = _step_from_public(previous)
            if checkpoint_step is None:
                return False, "malformed_checkpoint_previous"

    fallback_steps: list[int] = []
    for row in fallbacks:
        row_step = _step_from_public(row)
        if row_step is None:
            return False, "malformed_fallback"
        fallback_steps.append(row_step)
    if fallback_steps != sorted(set(fallback_steps)):
        return False, "malformed_fallback_order"
    if checkpoint_step is not None and any(row_step <= checkpoint_step for row_step in fallback_steps):
        return False, "fallback_before_checkpoint"

    represented = ([checkpoint_step] if checkpoint_step is not None else []) + fallback_steps
    if any(row_step > step for row_step in represented):
        return False, "future_state"
    if checkpoint_step == step:
        return True, "checkpointed"
    if step in fallback_steps:
        return True, "queued"
    return False, "missing"


def ensure_public_observation(
    instance: Any, observation: Mapping[str, Any], step: int
) -> tuple[bool, str]:
    """Ensure exactly one reconstruction-safe representation of this call."""
    covered, reason = _seller_observation_coverage(instance, step)
    if covered:
        return True, reason
    if reason != "missing":
        return False, reason
    remember = getattr(instance, "_remember_seller_fallback", None)
    if not callable(remember):
        return False, "no_recorder"
    observed = deepcopy(dict(observation))
    observed["step"] = step
    try:
        remember(observed)
    except (AttributeError, TypeError, ValueError, IndexError, KeyError, OverflowError, RecursionError):
        return False, "record_failed"
    covered, reason = _seller_observation_coverage(instance, step)
    if not covered:
        return False, f"record_unverified:{reason}"
    return True, "queued_now" if reason == "queued" else reason


def capture_committed(instance: Any) -> dict[str, Any] | None:
    """Return an immutable-content capsule or ``None`` on unsafe source state.

    Only fields that TITAN itself treats as reconstruction-safe are observed.
    In particular, diagnostics, history, spatial/quadrant objects, controller
    internals, selected actions, and post-unit snapshots are never captured.
    """
    try:
        route = getattr(instance, "_completed_route", None)
        seller = getattr(instance, "_completed_seller_state", None)
        fallbacks = getattr(instance, "_seller_fallback_observations", None)
        if fallbacks is None:
            fallbacks = []
        valid, _reason = _committed_shape(route, seller, fallbacks)
        if not valid:
            return None
        payload = {
            "route": deepcopy(route),
            "seller": deepcopy(seller),
            "fallbacks": deepcopy(fallbacks),
        }
        encoded = _canonical_bytes(payload)
    except (AttributeError, TypeError, ValueError, OverflowError, RecursionError):
        return None
    if payload["route"] is None and payload["seller"] is None and not payload["fallbacks"]:
        return None
    return {
        "schema": SCHEMA,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "payload": payload,
    }


def restore_committed(instance: Any, capsule: Mapping[str, Any] | None) -> tuple[bool, str]:
    """Validate then atomically install a capsule onto a fresh TITAN instance."""
    if not isinstance(capsule, Mapping):
        return False, "no_capsule"
    if set(capsule) != {"schema", "sha256", "payload"} or capsule.get("schema") != SCHEMA:
        return False, "schema"
    digest = capsule.get("sha256")
    payload = capsule.get("payload")
    if not isinstance(digest, str) or len(digest) != 64 or not isinstance(payload, Mapping):
        return False, "shape"
    if set(payload) != {"route", "seller", "fallbacks"}:
        return False, "payload_keys"
    route = payload.get("route")
    seller = payload.get("seller")
    fallbacks = payload.get("fallbacks")
    valid, reason = _committed_shape(route, seller, fallbacks)
    if not valid:
        return False, reason
    try:
        encoded = _canonical_bytes(payload)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False, "noncanonical"
    if not hmac.compare_digest(hashlib.sha256(encoded).hexdigest(), digest):
        return False, "digest"
    if any(not hasattr(instance, name) for name in _SAFE_FIELDS):
        return False, "factory_drift"

    # Prepare every detached value before publishing any field.  A failed copy
    # therefore leaves the fresh canonical instance completely untouched.
    try:
        detached_route = deepcopy(route)
        detached_seller = deepcopy(seller)
        detached_fallbacks = deepcopy(fallbacks)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False, "copy"
    instance._completed_route = detached_route
    instance._completed_seller_state = detached_seller
    instance._seller_fallback_observations = detached_fallbacks
    return True, "restored"


class RecoveryCarrier:
    """Own one private canonical-main module and its continuity capsule."""

    def __init__(self, canonical: ModuleType | Any):
        if not hasattr(canonical, "agent") or not callable(canonical.agent):
            raise TypeError("canonical module must expose callable agent")
        factory = getattr(canonical, "_new_instance", None)
        if not callable(factory):
            raise TypeError("canonical module must expose callable _new_instance")
        if not hasattr(canonical, "_INSTANCE"):
            raise TypeError("canonical module must expose _INSTANCE")
        self.canonical = canonical
        self._original_factory: Callable[..., Any] = factory
        self._capsule: dict[str, Any] | None = None
        self._constructed: Any = None
        self.last_report: dict[str, Any] = {"status": "ready"}
        canonical._new_instance = self._new_instance

    def _new_instance(self, root: Any, feature_data: Any) -> Any:
        instance = self._original_factory(root, feature_data)
        self._constructed = instance
        capsule = self._capsule
        if capsule is None:
            self.last_report = {"status": "canonical_fresh"}
            return instance
        restored, reason = restore_committed(instance, capsule)
        self.last_report = {
            "status": "restored" if restored else "restore_rejected",
            "reason": reason,
            "capsule_sha256": capsule.get("sha256") if isinstance(capsule, dict) else None,
        }
        # A malformed capsule never gets another attempt.  A valid capsule has
        # already been copied into the fresh object.  Either way, canonical
        # execution now owns the instance and the external capsule is retired.
        self._capsule = None
        return instance

    def reset(self) -> None:
        self._capsule = None
        self._constructed = None
        self.last_report = {"status": "episode_reset"}

    def capsule(self) -> dict[str, Any] | None:
        return deepcopy(self._capsule)

    def agent(self, observation: Mapping[str, Any], configuration: Mapping[str, Any] | None = None) -> Any:
        step = _absolute_step(observation, configuration)
        if step == 0:
            self.reset()
        before = self.canonical._INSTANCE
        self._constructed = None
        try:
            output = self.canonical.agent(observation, configuration)
        except BaseException:
            # Preserve canonical exception identity and ownership.  No recovery
            # claim is made for calls that canonical main did not contain.
            self._constructed = None
            raise

        after = self.canonical._INSTANCE
        if after is None:
            victim = self._constructed if self._constructed is not None else before
            covered = False
            observation_state = "no_victim"
            if victim is not None:
                # The outer timer may fire before seller observation, after an
                # inner fallback queued it, or after the completed checkpoint
                # already covers it.  Add only the genuinely missing case.
                covered, observation_state = ensure_public_observation(
                    victim, observation, step
                )
            captured = capture_committed(victim) if victim is not None and covered else None
            if captured is not None:
                self._capsule = captured
                self.last_report = {
                    "status": "captured",
                    "capsule_sha256": captured["sha256"],
                    "route": captured["payload"]["route"],
                    "fallback_count": len(captured["payload"]["fallbacks"]),
                    "public_observation": observation_state,
                    "recorded_current_step": observation_state == "queued_now",
                }
            elif self._capsule is None:
                self.last_report = {
                    "status": "canonical_empty",
                    "public_observation": observation_state,
                    "recorded_current_step": observation_state == "queued_now",
                }
        else:
            # A live canonical object is the sole source of truth; do not keep a
            # shadow capsule that could be replayed after unrelated later state.
            self._capsule = None
            if self.last_report.get("status") not in ("restored", "restore_rejected"):
                self.last_report = {"status": "canonical_live"}
        self._constructed = None
        return output


def _load_canonical(root: Path | None = None) -> ModuleType:
    source_root = (root or Path(__file__).resolve().parent.parent.parent).resolve()
    source = source_root / "main.py"
    if not source.is_file() or source.is_symlink():
        raise RuntimeError(f"canonical main.py missing or unsafe: {source}")
    name = "_titan_canonical_main_for_sol_mnemosyne"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load canonical main.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if sys.modules.get(name) is module:
            sys.modules.pop(name, None)
        raise
    return module


_CARRIER: RecoveryCarrier | None = None


def _carrier() -> RecoveryCarrier:
    global _CARRIER
    if _CARRIER is None:
        _CARRIER = RecoveryCarrier(_load_canonical())
    return _CARRIER


def agent(observation: Mapping[str, Any], configuration: Mapping[str, Any] | None = None) -> Any:
    """Kaggriculture entrypoint; returned action bytes come from canonical main."""
    return _carrier().agent(observation, configuration)


def carrier_report() -> dict[str, Any]:
    """Return detached diagnostics for evidence tooling, never gameplay policy."""
    return deepcopy(_carrier().last_report)
