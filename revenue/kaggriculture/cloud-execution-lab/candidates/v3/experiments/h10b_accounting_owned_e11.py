# SPDX-License-Identifier: Apache-2.0
"""H10B: allow E11 to defer only SELL rows provably owned by same-call R04 accounting.

Experiment only; default-off and not release wiring.
"""
from __future__ import annotations
from typing import Any, Callable, Mapping

DebtMap = dict[int, dict[str, int]]
NativeSnapshot = tuple[int, dict[str, int]]


def _snapshot_debts(state: Any) -> DebtMap:
    raw = getattr(state, "sale_window_debts", {}) or {}
    if not isinstance(raw, Mapping):
        raise ValueError("invalid sale_window_debts")
    out: DebtMap = {}
    for due_step, items in raw.items():
        due = int(due_step)
        if not isinstance(items, Mapping):
            raise ValueError("invalid debt bucket")
        clean = {}
        for item, quantity in items.items():
            q = int(quantity)
            if q < 0:
                raise ValueError("negative sale debt")
            if q:
                clean[str(item)] = q
        if clean:
            out[due] = clean
    return out


def _snapshot_native(state: Any) -> NativeSnapshot:
    due = int(getattr(state, "sale_due_step", -1))
    raw = getattr(state, "advanced_sales", {}) or {}
    if not isinstance(raw, Mapping):
        raise ValueError("invalid advanced_sales")
    clean = {}
    for item, quantity in raw.items():
        q = int(quantity)
        if q < 0:
            raise ValueError("negative advanced sale")
        if q:
            clean[str(item)] = q
    return due, clean


def _new_future_debt(before: DebtMap, after: DebtMap, step: int) -> DebtMap:
    created: DebtMap = {}
    for due, items in after.items():
        if due <= step:
            continue
        for item, quantity in items.items():
            delta = int(quantity) - int(before.get(due, {}).get(item, 0))
            if delta > 0:
                created.setdefault(due, {})[item] = delta
    return created


def _new_native_advance(before: NativeSnapshot, after: NativeSnapshot, step: int, *, state_replaced: bool) -> dict[str, int]:
    before_due, before_items = before
    after_due, after_items = after
    if after_due != step + 1 or not after_items:
        return {}
    if state_replaced or before_due != after_due:
        return dict(after_items)
    return {item: delta for item, quantity in after_items.items()
            if (delta := int(quantity) - int(before_items.get(item, 0))) > 0}


def _restore_accounting(state: Any, debts: DebtMap, native: NativeSnapshot) -> None:
    state.sale_window_debts = {due: dict(items) for due, items in debts.items()}
    state.sale_due_step = int(native[0])
    state.advanced_sales = dict(native[1])


def _refund(state: Any, created_debt: DebtMap, created_native: Mapping[str, int], items: set[str], step: int):
    debts = _snapshot_debts(state)
    refunded_debt: dict[str, int] = {}
    for due, bucket in created_debt.items():
        for item, quantity in bucket.items():
            if item not in items:
                continue
            have = int(debts.get(due, {}).get(item, 0))
            take = min(have, int(quantity))
            if take:
                remain = have - take
                if remain:
                    debts.setdefault(due, {})[item] = remain
                else:
                    debts.get(due, {}).pop(item, None)
                refunded_debt[item] = refunded_debt.get(item, 0) + take
    state.sale_window_debts = {due: bucket for due, bucket in debts.items() if bucket}

    due, native = _snapshot_native(state)
    refunded_native: dict[str, int] = {}
    if due == step + 1:
        for item, quantity in created_native.items():
            if item not in items:
                continue
            have = int(native.get(item, 0))
            take = min(have, int(quantity))
            if take:
                remain = have - take
                if remain:
                    native[item] = remain
                else:
                    native.pop(item, None)
                refunded_native[item] = refunded_native.get(item, 0) + take
        state.advanced_sales = native
        state.sale_due_step = due if native else -1
    return refunded_debt, refunded_native


def _default_state_getter(observation: Mapping[str, Any]):
    import r04_full_router as r04
    return r04._POLICY.players[int(observation["player"])]


def wrap_r04_agent(parent: Callable, absorption_fn: Callable, *, enabled: bool = False,
                   params: Mapping[str, Any] | None = None,
                   state_getter: Callable[[Mapping[str, Any]], Any] | None = None,
                   e11_apply: Callable | None = None):
    """Wrap R04; mutate only a unique SELL row exactly matching same-call booked quantity."""
    getter = state_getter or _default_state_getter
    histories: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    last_steps: dict[int, int] = {}
    telemetry = {"calls": 0, "changed": 0, "fail_open": 0, "last_by_player": {}}

    def adapter(observation, configuration=None):
        try:
            player = int(observation.get("player", 0)); step = int(observation.get("step", 0))
        except (TypeError, ValueError, AttributeError):
            return parent(observation, configuration)
        if player in last_steps and step <= last_steps[player]:
            histories[player] = []
        last_steps[player] = step

        if not enabled:
            return parent(observation, configuration)

        known = False; before_state = None; debts_before: DebtMap = {}; native_before: NativeSnapshot = (-1, {})
        try:
            before_state = getter(observation)
            debts_before = _snapshot_debts(before_state)
            native_before = _snapshot_native(before_state)
            known = True
        except Exception:
            pass

        parent_action = parent(observation, configuration)
        telemetry["calls"] += 1
        try:
            after_state = getter(observation)
            debts_after = _snapshot_debts(after_state)
            native_after = _snapshot_native(after_state)
        except Exception as error:
            telemetry["fail_open"] += 1
            telemetry["last_by_player"][player] = {"changed": False, "reason": "INVALID_POST_ACCOUNTING_" + type(error).__name__}
            return parent_action

        replaced = known and before_state is not after_state
        if replaced:
            debts_before = {}; native_before = (-1, {})

        cfg = dict(configuration or {}); cfg.update(dict(params or {}))
        history = list(histories.get(player, []))
        apply_fn = e11_apply
        if apply_fn is None:
            from e11_rival_sell import apply_e11 as apply_fn
        try:
            _ignored, report = apply_fn(observation, parent_action, history, cfg, absorption_fn, enabled=True)
        except Exception as error:
            telemetry["fail_open"] += 1
            telemetry["last_by_player"][player] = {"changed": False, "reason": "E11_ERROR_" + type(error).__name__}
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
        if not known:
            telemetry["fail_open"] += 1
            telemetry["last_by_player"][player] = {"changed": False, "reason": "UNKNOWN_PREDECESSOR_ACCOUNTING"}
            return parent_action

        created_debt = _new_future_debt(debts_before, debts_after, step)
        created_native = _new_native_advance(native_before, native_after, step, state_replaced=replaced)
        booked: dict[str, int] = {}
        for bucket in created_debt.values():
            for item, quantity in bucket.items():
                booked[item] = booked.get(item, 0) + int(quantity)
        for item, quantity in created_native.items():
            booked[item] = booked.get(item, 0) + int(quantity)

        raw_market = parent_action.get("market") or [] if isinstance(parent_action, Mapping) else []
        if not isinstance(raw_market, list):
            telemetry["fail_open"] += 1
            telemetry["last_by_player"][player] = {"changed": False, "reason": "BAD_MARKET_QUEUE"}
            return parent_action
        market = [list(row) if isinstance(row, list) else row for row in raw_market]
        eligible = {str(item) for item in report.get("deferred") or []}
        blank: list[tuple[int, str, int]] = []
        ambiguous: list[str] = []
        for item in sorted(eligible):
            quantity = int(booked.get(item, 0))
            if quantity <= 0:
                continue
            matches = []
            for index, row in enumerate(market):
                if isinstance(row, list) and len(row) >= 3 and row[0] == "SELL" and str(row[1]) == item:
                    try:
                        row_q = int(row[2])
                    except (TypeError, ValueError):
                        continue
                    if row_q == quantity:
                        matches.append(index)
            if len(matches) == 1:
                blank.append((matches[0], item, quantity))
            elif len(matches) > 1:
                ambiguous.append(item)

        if ambiguous or not blank or len({index for index, _, _ in blank}) != len(blank):
            telemetry["last_by_player"][player] = {"changed": False, "reason": "NO_UNIQUE_ACCOUNTING_OWNED_ROW", "ambiguous": ambiguous, "booked": booked}
            return parent_action

        items = {item for _, item, _ in blank}
        refunded_debt, refunded_native = _refund(after_state, created_debt, created_native, items, step)
        refunded = {item: refunded_debt.get(item, 0) + refunded_native.get(item, 0) for item in items}
        expected = {item: booked[item] for item in items}
        if refunded != expected:
            _restore_accounting(after_state, debts_after, native_after)
            telemetry["fail_open"] += 1
            telemetry["last_by_player"][player] = {"changed": False, "reason": "REFUND_MISMATCH", "expected": expected, "refunded": refunded}
            return parent_action

        out = dict(parent_action); out_market = list(market)
        for index, _item, _quantity in blank:
            out_market[index] = []
        out["market"] = out_market
        final = dict(report)
        final.update(changed=True, reason="ACCOUNTING_OWNED_E11", booked=booked,
                     blanked=[{"index": i, "item": item, "quantity": q} for i, item, q in blank],
                     refunded_debt=refunded_debt, refunded_native=refunded_native)
        telemetry["changed"] += 1
        telemetry["last_by_player"][player] = final
        return out

    adapter.telemetry = telemetry
    adapter.histories = histories
    return adapter
