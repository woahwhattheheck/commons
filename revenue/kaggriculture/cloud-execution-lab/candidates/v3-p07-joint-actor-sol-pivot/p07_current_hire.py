# SPDX-License-Identifier: Apache-2.0
"""Narrow current-HIRE admission window for the exact P07 joint-actor key.

SOL-CROSSWIND's source-pinned PR #11975 established the only theorem consumed
here: the official interpreter applies the farmer and every hand already
present in the observation before it processes market orders, and HIRE appends
the new hand/inventory afterward.  Consequently a current executable-prefix
HIRE cannot renumber or execute a newly-created actor during the current unit
stage.

This module does not implement another scheduler.  It wraps the existing exact
``p07_atomic.reconcile`` call, temporarily removes only a certified current
HIRE queue from that primitive's private unit-only simulation, then restores
the complete market bytes and any bounded new-actor action tail before the
action can reach the interpreter.  Future market rows remain visible to—and
are rejected by—the exact primitive.
"""
from __future__ import annotations

from copy import deepcopy
import time
from typing import Any, Mapping, MutableMapping

MAX_OFFICIAL_MARKET_PREFIX = 10


def _blank(order: Any) -> bool:
    """Only the literal action-carrier blank is inert."""
    return order == []


def classify_current_hire(
    selected: Mapping,
    raw: Mapping,
    configuration: Mapping,
    existing_actor_count: int,
) -> dict[str, Any]:
    """Return a fail-closed admission receipt for a current market row."""
    selected_market = selected.get("market", [])
    raw_market = raw.get("market", [])
    if type(selected_market) is not list or type(raw_market) is not list:
        return {"admitted": False, "reason": "malformed_current_market"}
    if selected_market != raw_market:
        return {"admitted": False, "reason": "current_market_source_mismatch"}

    configured = configuration.get("maxMarketOrdersPerTurn", 10)
    # bool is an int subclass.  Accepting it would silently reinterpret the
    # active prefix; all noncanonical carriers are outside this theorem.
    if (
        type(configured) is not int
        or configured < 1
        or configured > MAX_OFFICIAL_MARKET_PREFIX
    ):
        return {
            "admitted": False,
            "reason": "unsupported_market_prefix_config",
        }

    active = selected_market[:configured]
    suffix = selected_market[configured:]
    if any(not _blank(order) for order in suffix):
        return {
            "admitted": False,
            "reason": "inactive_suffix_market_boundary",
        }

    active_hires = 0
    for order in active:
        if _blank(order):
            continue
        if type(order) is not list or order != ["HIRE"]:
            return {
                "admitted": False,
                "reason": "current_non_hire_market_boundary",
            }
        active_hires += 1
    if active_hires == 0:
        return {
            "admitted": False,
            "reason": "current_market_without_executable_hire",
        }

    selected_hands = selected.get("hands", [])
    raw_hands = raw.get("hands", [])
    if type(selected_hands) is not list or type(raw_hands) is not list:
        return {"admitted": False, "reason": "malformed_current_hands"}
    existing_hands = existing_actor_count - 1
    if existing_hands < 0:
        return {"admitted": False, "reason": "invalid_existing_actor_count"}
    if selected_hands[existing_hands:] != raw_hands[existing_hands:]:
        return {
            "admitted": False,
            "reason": "new_actor_tail_source_mismatch",
        }
    extra_actions = max(0, len(selected_hands) - existing_hands)
    if extra_actions > active_hires:
        return {"admitted": False, "reason": "excess_new_actor_actions"}

    return {
        "admitted": True,
        "reason": "certified_current_hire_existing_actors",
        "active_hires": active_hires,
        "extra_actor_actions": extra_actions,
        "executable_prefix": configured,
        "existing_actor_count": existing_actor_count,
    }


def _restore_exact_field(target: MutableMapping, source: Mapping, field: str) -> None:
    if field in source:
        target[field] = deepcopy(source[field])
    else:
        target.pop(field, None)


def _restore_existing_tail(
    target: MutableMapping,
    source: Mapping,
    existing_actor_count: int,
) -> None:
    existing_hands = existing_actor_count - 1
    target_hands = target.get("hands", [])
    source_hands = source.get("hands", [])
    if type(target_hands) is not list or type(source_hands) is not list:
        raise TypeError("hands carrier changed after current-HIRE certification")
    target_hands[existing_hands:] = deepcopy(source_hands[existing_hands:])
    target["hands"] = target_hands


def _record_rejection(
    module: Any,
    spatial: Any,
    observation: Mapping,
    receipt: Mapping[str, Any],
    started: float,
) -> None:
    report = getattr(module, "_report", None)
    if callable(report):
        report(
            spatial,
            observation,
            changed=False,
            reason=str(receipt["reason"]),
            started=started,
            current_hire_window=dict(receipt),
        )
        return
    spatial.p07_report = {
        "phase": "proposal",
        "step": int(observation["step"]),
        "player": int(observation["player"]),
        "changed": False,
        "reason": str(receipt["reason"]),
        "current_hire_window": dict(receipt),
    }


def _append_window_record(
    module: Any,
    spatial: Any,
    observation: Mapping,
    receipt: Mapping[str, Any],
) -> None:
    report = getattr(spatial, "p07_report", None)
    if isinstance(report, MutableMapping):
        report["current_hire_window"] = dict(receipt)
    append = getattr(module, "_append_log", None)
    if callable(append):
        append(
            {
                "phase": "current_hire_window",
                "step": int(observation["step"]),
                "player": int(observation["player"]),
                "changed": bool(
                    isinstance(report, Mapping) and report.get("changed") is True
                ),
                **dict(receipt),
            }
        )


def wrap_reconcile(module: Any, original_reconcile: Any):
    """Build one current-HIRE wrapper around the exact P07 reconciler."""

    def reconcile(
        spatial: Any,
        observation: Mapping,
        selected: Mapping,
        controller: Any,
        *,
        owner_busy: bool = False,
    ) -> Mapping:
        # Preserve the exact predecessor ordering for higher-priority ownership
        # and an unfinalized pair.  Those paths return before its market veto.
        pending = getattr(spatial, "_p07_pending", None)
        now = int(observation["step"])
        if owner_busy or (
            isinstance(pending, Mapping)
            and int(pending.get("step", now)) == now
        ):
            return original_reconcile(
                spatial,
                observation,
                selected,
                controller,
                owner_busy=owner_busy,
            )

        route = controller.R[controller.cur]
        raw = module._route_row(route, now)
        selected_market = selected.get("market", [])
        raw_market = raw.get("market", [])
        if selected_market == [] and raw_market == []:
            return original_reconcile(
                spatial,
                observation,
                selected,
                controller,
                owner_busy=owner_busy,
            )

        started = time.perf_counter()
        try:
            farm = observation["farms"][observation["player"]]
            existing_actor_count = 1 + len(farm.get("hands", []))
            configuration = dict(getattr(spatial, "configuration", {}) or {})
        except (KeyError, TypeError, ValueError):
            receipt = {"admitted": False, "reason": "malformed_current_observation"}
            _record_rejection(module, spatial, observation, receipt, started)
            return selected

        receipt = classify_current_hire(
            selected,
            raw,
            configuration,
            existing_actor_count,
        )
        if not receipt["admitted"]:
            _record_rejection(module, spatial, observation, receipt, started)
            return selected

        if not isinstance(raw, MutableMapping):
            rejected = dict(receipt)
            rejected.update(
                admitted=False,
                reason="current_hire_route_row_not_mutable",
            )
            _record_rejection(module, spatial, observation, rejected, started)
            return selected

        original_row = raw
        certified_selected = deepcopy(selected)
        certified_selected["market"] = []
        certified_row = deepcopy(raw)
        certified_row["market"] = []
        try:
            route[now] = certified_row
        except (KeyError, TypeError, IndexError):
            rejected = dict(receipt)
            rejected.update(
                admitted=False,
                reason="current_hire_route_not_mutable",
            )
            _record_rejection(module, spatial, observation, rejected, started)
            return selected

        try:
            output = original_reconcile(
                spatial,
                observation,
                certified_selected,
                controller,
                owner_busy=owner_busy,
            )
        except BaseException:
            # The theorem may never convert an underlying error into a partial
            # route mutation.
            route[now] = original_row
            raise

        report = getattr(spatial, "p07_report", None)
        changed = isinstance(report, Mapping) and report.get("changed") is True
        if not changed:
            # Preserve exact object identity on a certified but dormant row.
            route[now] = original_row
            _append_window_record(module, spatial, observation, receipt)
            return selected

        current_row = route[now]
        if not isinstance(current_row, MutableMapping):
            route[now] = original_row
            raise TypeError("P07 replaced current route row with non-mapping")
        _restore_exact_field(current_row, original_row, "market")
        _restore_existing_tail(current_row, original_row, existing_actor_count)

        if not isinstance(output, MutableMapping):
            route[now] = original_row
            raise TypeError("P07 returned non-mapping under current HIRE")
        restored = deepcopy(output)
        _restore_exact_field(restored, selected, "market")
        _restore_existing_tail(restored, selected, existing_actor_count)
        _append_window_record(module, spatial, observation, receipt)
        return restored

    reconcile.__name__ = getattr(original_reconcile, "__name__", "reconcile")
    reconcile.__doc__ = (
        "Current-HIRE existing-actor window around "
        + (getattr(original_reconcile, "__doc__", "") or "exact P07")
    )
    return reconcile


def install_current_hire_window(module: Any) -> Any:
    """Patch only the module-global reconciler resolved by installed hooks."""
    if getattr(module, "_p07_current_hire_window_installed", False):
        return module
    original = module.reconcile
    module._p07_current_hire_original_reconcile = original
    module.reconcile = wrap_reconcile(module, original)
    module._p07_current_hire_window_installed = True
    return module
