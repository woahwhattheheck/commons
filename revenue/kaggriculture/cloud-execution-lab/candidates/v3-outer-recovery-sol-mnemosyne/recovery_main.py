# SPDX-License-Identifier: Apache-2.0
"""Candidate carrier that preserves only committed TITAN continuity state.

Canonical ``main.py`` intentionally discards an instance if its whole-call timer
interrupts a late finalizer.  Discarding the possibly-mutated object is correct,
but the outer handler does not preserve the current public observation and the
object also owns three explicitly committed/replayable fields:
``_completed_route``, ``_completed_seller_state``, and
``_seller_fallback_observations``.  This candidate transfers only those fields to
the next fresh instance.  Policy, controller, finalizers, and returned actions
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
        if route is not None and not isinstance(route, str):
            return None
        if seller is not None and not isinstance(seller, dict):
            return None
        if fallbacks is None:
            fallbacks = []
        if not isinstance(fallbacks, list) or any(not isinstance(row, dict) for row in fallbacks):
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
    if route is not None and not isinstance(route, str):
        return False, "route"
    if seller is not None and not isinstance(seller, dict):
        return False, "seller"
    if not isinstance(fallbacks, list) or any(not isinstance(row, dict) for row in fallbacks):
        return False, "fallbacks"
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
            recorded = False
            if victim is not None:
                # Current canonical main discards without recording this public
                # observation.  Reuse TitanAgent's own idempotent recorder after
                # the deadline context has exited; a future upstream recorder is
                # harmless because equal-step inputs replace rather than append.
                remember = getattr(victim, "_remember_seller_fallback", None)
                if callable(remember):
                    observed = deepcopy(dict(observation))
                    observed["step"] = step
                    try:
                        remember(observed)
                        recorded = True
                    except (AttributeError, TypeError, ValueError, IndexError, KeyError, RecursionError):
                        recorded = False
            captured = capture_committed(victim) if victim is not None and recorded else None
            if captured is not None:
                self._capsule = captured
                self.last_report = {
                    "status": "captured",
                    "capsule_sha256": captured["sha256"],
                    "route": captured["payload"]["route"],
                    "fallback_count": len(captured["payload"]["fallbacks"]),
                    "recorded_current_step": True,
                }
            elif self._capsule is None:
                self.last_report = {
                    "status": "canonical_empty",
                    "recorded_current_step": recorded,
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
