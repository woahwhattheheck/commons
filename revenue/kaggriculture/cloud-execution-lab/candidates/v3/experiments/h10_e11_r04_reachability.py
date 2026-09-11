# SPDX-License-Identifier: Apache-2.0
"""H10: make shipped E11 measurable on live R04 without phantom sale accounting.

Experiment only; no release wiring.

R04 whole-route delegation bypasses the canonical seller-owned E11 seam. A naive final
wrapper is unsafe because the R04 parent can book a sale before E11 sees the final action:

* before step 288, native ``advance_sales`` records ``advanced_sales`` plus
  ``sale_due_step = step + 1``;
* from step 288 onward, E184 records future ``sale_window_debts``.

If E11 blanks that just-advanced SELL but the matching accounting survives, a later turn
subtracts a sale that never executed. This adapter reuses ``e11_rival_sell.apply_e11``
unchanged, proves its edit is row-stable SELL->[] blanking, identifies only accounting
created by the same parent call, verifies booked quantity is covered by the removed SELL,
and atomically rolls back both bookkeeping paths for deferred items. Existing debt and
current-step debt consumption are never recreated. Any ambiguity fails closed to the exact
parent action and parent state.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

DebtMap = dict[int, dict[str, int]]
NativeSnapshot = tuple[int, dict[str, int]]


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


def _snapshot_native(state: Any) -> NativeSnapshot:
    try:
        due = int(getattr(state, "sale_due_step", -1))
    except (TypeError, ValueError):
        due = -1
    raw = getattr(state, "advanced_sales", {}) or {}
    clean: dict[str, int] = {}
    if isinstance(raw, Mapping):
        for item, quantity in raw.items():
            try:
                q = max(0, int(quantity))
            except (TypeError, ValueError):
                continue
            if q:
                clean[str(item)] = q
    return due, clean


def _new_future_debt(before: DebtMap, after: DebtMap, step: int) -> DebtMap:
    created: DebtMap = {}
    for due, items in after.items():
        if due <= step:
            continue
        for item, quantity in items.items():
            delta = max(0, int(quantity) - int(before.get(due, {}).get(item, 0)))
            if delta:
                created.setdefault(due, {})[item] = delta
    return created


def _new_native_advance(
    before: NativeSnapshot,
    after: NativeSnapshot,
    step: int,
    *,
    state_replaced: bool,
) -> dict[str, int]:
    """Return only native advances demonstrably booked by this parent call."""
    before_due, before_items = before
    after_due, after_items = after
    if after_due != step + 1 or not after_items:
        return {}
    if state_replaced or before_due != after_due:
        return dict(after_items)
    created: dict[str, int] = {}
    for item, quantity in after_items.items():
        delta = max(0, int(quantity) - int(before_items.get(item, 0)))
        if delta:
            created[item] = delta
    return created


def _removed_sell_quantities(before_action: Mapping[str, Any], after_action: Mapping[str, Any]):
    """Prove the E11 result is row-stable SELL->[] blanking and return removed qty."""
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
        if not isinstance(old, list) or len(old) < 3 or old[0] != "SELL" or new != []:
            return None
        try:
            q = max(0, int(old[2]))
        except (TypeError, ValueError):
            return None
        removed[str(old[1])] = removed.get(str(old[1]), 0) + q
    for key in set(before_action) | set(after_action):
        if key != "market" and before_action.get(key) != after_action.get(key):
            return None
    return removed


def _refund_new_debt(state: Any, created: DebtMap, deferred_items: set[str]) -> dict[str, int]:
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
    state.sale_window_debts = {due: items for due, items in current.items() if items}
    return refunded


def _refund_new_native(
    state: Any,
    created: Mapping[str, int],
    deferred_items: set[str],
    step: int,
) -> dict[str, int]:
    """Remove same-call native advances for deferred items and repair the due marker."""
    due, current = _snapshot_native(state)
    refunded: dict[str, int] = {}
    if due != step + 1:
        return refunded
    for item, quantity in created.items():
        if item not in deferred_items or quantity <= 0:
            continue
        have = int(current.get(item, 0))
        take = min(have, int(quantity))
        if not take:
            continue
        remain = have - take
        if remain:
            current[item] = remain
        else:
            current.pop(item, None)
        refunded[item] = refunded.get(item, 0) + take
    state.advanced_sales = current
    state.sale_due_step = due if current else -1
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
    """Return an R04-compatible callable with E11 outermost and sale-accounting atomic."""
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
        native_before: NativeSnapshot = (-1, {})
        predecessor_known = False
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
                native_before = _snapshot_native(action_state_before)
                predecessor_known = True
            except Exception:
                action_state_before = None

        parent_action = parent(observation, configuration)
        if not enabled:
            return parent_action

        telemetry["calls"] += 1
        try:
            action_state_after = getter(observation)
        except Exception as error:
            telemetry["fail_closed"] += 1
            telemetry["last_by_player"][player] = {
                "enabled": True,
                "changed": False,
                "reason": "NO_R04_STATE_" + type(error).__name__,
            }
            return parent_action

        state_replaced = predecessor_known and action_state_before is not action_state_after
        if state_replaced:
            debts_before = {}
            native_before = (-1, {})
        debts_after = _snapshot_debts(action_state_after)
        native_after = _snapshot_native(action_state_after)

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
                "enabled": True,
                "changed": False,
                "reason": "E11_ERROR_" + type(error).__name__,
            }
            return parent_action

        prices = dict(((observation.get("market") or {}).get("prices") or {}))
        history.append((step, prices))
        try:
            lookback = max(0, int(cfg.get("rival_dump_lookback_steps", 8)))
        except (TypeError, ValueError):
            lookback = 8
        histories[player] = [entry for entry in history if 0 <= step - int(entry[0]) <= lookback]

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

        # Without a pre-parent snapshot, any surviving future bookkeeping could predate
        # this call. Never infer that it belongs to the E11-removed SELL.
        if not predecessor_known and (debts_after or native_after[1]):
            telemetry["fail_closed"] += 1
            failed = dict(report)
            failed.update(
                changed=False,
                reason="FAIL_CLOSED_UNKNOWN_PREDECESSOR_SALE_ACCOUNTING",
                removed_sell_qty=removed,
            )
            telemetry["last_by_player"][player] = failed
            return parent_action

        deferred_items = {str(item) for item in report.get("deferred") or []}
        created_debt = _new_future_debt(debts_before, debts_after, step)
        created_native = _new_native_advance(
            native_before, native_after, step, state_replaced=state_replaced,
        )
        booked_by_item: dict[str, int] = {}
        for items in created_debt.values():
            for item, quantity in items.items():
                booked_by_item[item] = booked_by_item.get(item, 0) + int(quantity)
        for item, quantity in created_native.items():
            booked_by_item[item] = booked_by_item.get(item, 0) + int(quantity)

        if any(booked_by_item.get(item, 0) > removed.get(item, 0) for item in deferred_items):
            telemetry["fail_closed"] += 1
            failed = dict(report)
            failed.update(
                changed=False,
                reason="FAIL_CLOSED_BOOKED_QTY_EXCEEDS_DEFERRED_SELL",
                removed_sell_qty=removed,
                booked_sale_qty=booked_by_item,
            )
            telemetry["last_by_player"][player] = failed
            return parent_action

        refunded_debt = _refund_new_debt(action_state_after, created_debt, deferred_items)
        refunded_native = _refund_new_native(
            action_state_after, created_native, deferred_items, step,
        )
        final_report = dict(report)
        final_report.update(
            removed_sell_qty=removed,
            booked_sale_qty=booked_by_item,
            new_debt_qty={
                item: sum(items.get(item, 0) for items in created_debt.values())
                for item in {k for items in created_debt.values() for k in items}
            },
            new_native_advance_qty=dict(created_native),
            refunded_new_debt=refunded_debt,
            refunded_new_native_advance=refunded_native,
            state_replaced=state_replaced,
        )
        telemetry["changed"] += 1
        telemetry["last_by_player"][player] = final_report
        return out

    adapter.telemetry = telemetry
    adapter.histories = histories
    return adapter
