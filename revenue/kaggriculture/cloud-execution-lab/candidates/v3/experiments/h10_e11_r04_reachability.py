# SPDX-License-Identifier: Apache-2.0
"""H10: make shipped E11 measurable on the live R04 route without orphaning sale debt.

This is an experiment, not release wiring.

Exact V3.1 topology returns from ``TitanAgent._v3_r03_act`` whenever R04 is enabled,
so the canonical seller-owned ``_v3_e11_before_pending`` seam is never reached.  A
naive outer wrapper is unsafe: R04's E184 layer may append a current SELL and book
matching ``sale_window_debts``; if E11 then blanks that SELL, the due-step subtraction
would later erase a sale that never happened.

This adapter reuses ``e11_rival_sell.apply_e11`` unchanged and snapshots R04 debt state
around the parent call.  When E11 defers an item, it rolls back *only positive debt
deltas booked by that same parent call* for that item.  Existing debt and debt consumed
at the current step are never recreated.  If the removed SELL quantity cannot cover the
newly-booked debt, the adapter fails closed to the exact parent action and leaves parent
state untouched.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping


DebtMap = dict[int, dict[str, int]]


def _snapshot_debts(state: Any) -> DebtMap:
    raw = getattr(state, "sale_window_debts", {}) or {}
    out: DebtMap = {}
    if not isinstance(raw, Mapping):
        return out
    for due_step, items in raw.items():
        try:
            due = int(due_step)
        except (TypeError, ValueError):
            continue
        if not isinstance(items, Mapping):
            continue
        clean: dict[str, int] = {}
        for item, quantity in items.items():
            try:
                q = max(0, int(quantity))
            except (TypeError, ValueError):
                continue
            if q:
                clean[str(item)] = q
        if clean:
            out[due] = clean
    return out


def _new_future_debt(before: DebtMap, after: DebtMap, step: int) -> DebtMap:
    """Return only positive per-item debt increments due after the current step."""
    created: DebtMap = {}
    for due, items in after.items():
        if due <= step:
            continue
        for item, quantity in items.items():
            delta = max(0, int(quantity) - int(before.get(due, {}).get(item, 0)))
            if delta:
                created.setdefault(due, {})[item] = delta
    return created


def _removed_sell_quantities(before_action: Mapping[str, Any], after_action: Mapping[str, Any]):
    """Prove the E11 result is row-stable blanking and return removed qty by item."""
    before_market = before_action.get("market") or []
    after_market = after_action.get("market") or []
    if not isinstance(before_market, list) or not isinstance(after_market, list):
        return None
    if len(before_market) != len(after_market):
        return None
    removed: dict[str, int] = {}
    for old, new in zip(before_market, after_market):
        if old == new:
            continue
        if (not isinstance(old, list) or len(old) < 3 or old[0] != "SELL" or new != []):
            return None
        try:
            q = max(0, int(old[2]))
        except (TypeError, ValueError):
            return None
        removed[str(old[1])] = removed.get(str(old[1]), 0) + q
    # E11 must not touch farmer/hands or any other top-level field.
    for key in set(before_action) | set(after_action):
        if key == "market":
            continue
        if before_action.get(key) != after_action.get(key):
            return None
    return removed


def _refund_new_debt(state: Any, created: DebtMap, deferred_items: set[str]) -> dict[str, int]:
    """Subtract this call's newly-created debt for E11-deferred items only."""
    current = _snapshot_debts(state)
    refunded: dict[str, int] = {}
    for due, items in created.items():
        for item, quantity in items.items():
            if item not in deferred_items or quantity <= 0:
                continue
            have = int(current.get(due, {}).get(item, 0))
            take = min(have, int(quantity))
            if not take:
                continue
            remain = have - take
            if remain:
                current.setdefault(due, {})[item] = remain
            else:
                current.get(due, {}).pop(item, None)
            refunded[item] = refunded.get(item, 0) + take
    state.sale_window_debts = {
        due: items for due, items in current.items() if items
    }
    return refunded


def _default_state_getter(observation: Mapping[str, Any]):
    import r04_full_router as r04
    return r04._POLICY.players[int(observation["player"])]


def wrap_r04_agent(
    parent: Callable,
    absorption_fn: Callable,
    *,
    enabled: bool = False,
    params: Mapping[str, Any] | None = None,
    state_getter: Callable[[Mapping[str, Any]], Any] | None = None,
    e11_apply: Callable | None = None,
):
    """Return an R04-compatible callable with E11 outermost and debt-atomic.

    ``absorption_fn`` must be the same exact integer per-step absorption callable used by
    the canonical E11 seller seam.  It is injected deliberately so this experiment cannot
    silently substitute a heuristic for an engine transition.
    """
    histories: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    last_steps: dict[int, int] = {}
    telemetry: dict[str, Any] = {
        "calls": 0,
        "changed": 0,
        "fail_closed": 0,
        "last_by_player": {},
    }
    getter = state_getter or _default_state_getter

    def adapter(observation, configuration=None):
        action_state_before = None
        debts_before: DebtMap = {}
        try:
            player = int(observation.get("player", 0))
            step = int(observation.get("step", 0))
        except (TypeError, ValueError, AttributeError):
            return parent(observation, configuration)

        previous_step = last_steps.get(player)
        if previous_step is not None and step <= previous_step:
            histories[player] = []
        last_steps[player] = step

        if enabled:
            try:
                action_state_before = getter(observation)
                debts_before = _snapshot_debts(action_state_before)
            except Exception:
                action_state_before = None
                debts_before = {}

        parent_action = parent(observation, configuration)
        if not enabled:
            return parent_action

        telemetry["calls"] += 1
        try:
            action_state_after = getter(observation)
        except Exception as error:
            telemetry["fail_closed"] += 1
            telemetry["last_by_player"][player] = {
                "enabled": True, "changed": False,
                "reason": "NO_R04_STATE_" + type(error).__name__,
            }
            return parent_action

        # A step reset can replace the player state object.  In that case no debt from the
        # previous episode is a valid predecessor for positive-delta accounting.
        if action_state_before is not action_state_after:
            debts_before = {}
        debts_after = _snapshot_debts(action_state_after)

        cfg = dict(configuration or {})
        cfg.update(dict(params or {}))
        history = list(histories.get(player, []))
        apply_fn = e11_apply
        if apply_fn is None:
            from e11_rival_sell import apply_e11 as apply_fn

        try:
            out, report = apply_fn(
                observation, parent_action, history, cfg, absorption_fn, enabled=True,
            )
        except Exception as error:
            telemetry["fail_closed"] += 1
            telemetry["last_by_player"][player] = {
                "enabled": True, "changed": False,
                "reason": "E11_ERROR_" + type(error).__name__,
            }
            return parent_action

        prices = dict(((observation.get("market") or {}).get("prices") or {}))
        history.append((step, prices))
        try:
            lookback = max(0, int(cfg.get("rival_dump_lookback_steps", 8)))
        except (TypeError, ValueError):
            lookback = 8
        histories[player] = [
            entry for entry in history if 0 <= step - int(entry[0]) <= lookback
        ]

        if not report.get("changed"):
            telemetry["last_by_player"][player] = dict(report)
            return parent_action

        removed = _removed_sell_quantities(parent_action, out)
        if removed is None:
            telemetry["fail_closed"] += 1
            failed = dict(report)
            failed.update(changed=False, reason="FAIL_CLOSED_NON_ROW_STABLE_E11")
            telemetry["last_by_player"][player] = failed
            return parent_action

        deferred_items = {str(item) for item in report.get("deferred") or []}
        created = _new_future_debt(debts_before, debts_after, step)
        created_by_item: dict[str, int] = {}
        for items in created.values():
            for item, quantity in items.items():
                created_by_item[item] = created_by_item.get(item, 0) + int(quantity)

        # If parent accounting claims more newly-advanced quantity than E11 actually removed,
        # we cannot prove atomic rollback.  Preserve the exact parent action + parent debt.
        if any(created_by_item.get(item, 0) > removed.get(item, 0)
               for item in deferred_items):
            telemetry["fail_closed"] += 1
            failed = dict(report)
            failed.update(
                changed=False,
                reason="FAIL_CLOSED_DEBT_EXCEEDS_DEFERRED_SELL",
                removed_sell_qty=removed,
                new_debt_qty=created_by_item,
            )
            telemetry["last_by_player"][player] = failed
            return parent_action

        refunded = _refund_new_debt(action_state_after, created, deferred_items)
        final_report = dict(report)
        final_report.update(
            removed_sell_qty=removed,
            new_debt_qty=created_by_item,
            refunded_new_debt=refunded,
        )
        telemetry["changed"] += 1
        telemetry["last_by_player"][player] = final_report
        return out

    adapter.telemetry = telemetry
    adapter.histories = histories
    return adapter
