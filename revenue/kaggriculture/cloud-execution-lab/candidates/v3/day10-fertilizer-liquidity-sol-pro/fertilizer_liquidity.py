# SPDX-License-Identifier: Apache-2.0
"""Fail-closed final-boundary FERTILIZER liquidity proposal for TITAN V3."""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

ITEM = "FERTILIZER"


@dataclass(frozen=True)
class LiquiditySettings:
    start_day: int = 8
    end_day: int = 10
    reserve_units: int = 24
    minimum_unit_price: int = 55
    max_units_per_turn: int = 64
    liquidity_target: int = 12_000
    rival_stress_units: int = 32


class ProposalError(ValueError):
    pass


def _integer(value: Any, name: str, minimum: int | None = None) -> int:
    if isinstance(value, bool):
        raise ProposalError(f"{name}_is_boolean")
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ProposalError(f"{name}_not_integer") from exc
    if isinstance(value, float) and (not math.isfinite(value) or value != number):
        raise ProposalError(f"{name}_not_integer")
    if minimum is not None and number < minimum:
        raise ProposalError(f"{name}_below_minimum")
    return number


def executable_market_limit(configuration: Mapping[str, Any] | None) -> int:
    cfg = configuration or {}
    return max(1, _integer(cfg.get("maxMarketOrdersPerTurn", 10), "market_limit"))


def _operation(row: Any) -> str | None:
    if not row:
        return None
    if not isinstance(row, (list, tuple)) or not row or not isinstance(row[0], str):
        raise ProposalError("malformed_market_row")
    return row[0]


def _quantity(row: Sequence[Any]) -> int:
    if len(row) < 3:
        raise ProposalError("market_row_missing_quantity")
    return _integer(row[2], "market_quantity", 0)


def _conflict(active: Sequence[Any]) -> str | None:
    for row in active:
        op = _operation(row)
        if op not in ("SELL", "BUY_PRODUCT"):
            continue
        if len(row) < 2:
            raise ProposalError("market_row_missing_item")
        if row[1] != ITEM:
            continue
        _quantity(row)
        return (
            "incumbent_fertilizer_sale"
            if op == "SELL"
            else "executable_fertilizer_purchase"
        )
    return None


def _slot(market: Sequence[Any], limit: int) -> tuple[int, str] | None:
    if len(market) < limit:
        return len(market), "append"
    prefix = market[:limit]
    last = -1
    for index, row in enumerate(prefix):
        _operation(row)
        if row:
            last = index
    candidate = last + 1
    return (candidate, "trailing_blank") if candidate < limit and not prefix[candidate] else None


def _money(observation: Mapping[str, Any]) -> int:
    player = _integer(observation.get("player"), "player", 0)
    farms = observation.get("farms")
    if not isinstance(farms, (list, tuple)) or player >= len(farms):
        raise ProposalError("malformed_farms")
    farm = farms[player]
    if not isinstance(farm, Mapping):
        raise ProposalError("malformed_farm")
    return _integer(farm.get("money"), "money", 0)


def _inventory(observation: Mapping[str, Any]) -> int:
    market = observation.get("market")
    if not isinstance(market, Mapping):
        raise ProposalError("malformed_market")
    inventory = market.get("inventory")
    if not isinstance(inventory, Mapping) or ITEM not in inventory:
        raise ProposalError("missing_fertilizer_inventory")
    return _integer(inventory[ITEM], "fertilizer_market_inventory")


def _settings(value: LiquiditySettings) -> LiquiditySettings:
    fields = {
        "start_day": _integer(value.start_day, "start_day", 0),
        "end_day": _integer(value.end_day, "end_day", 0),
        "reserve_units": _integer(value.reserve_units, "reserve_units", 0),
        "minimum_unit_price": _integer(value.minimum_unit_price, "minimum_unit_price", 2),
        "max_units_per_turn": _integer(value.max_units_per_turn, "max_units_per_turn", 1),
        "liquidity_target": _integer(value.liquidity_target, "liquidity_target", 0),
        "rival_stress_units": _integer(value.rival_stress_units, "rival_stress_units", 0),
    }
    if fields["end_day"] < fields["start_day"]:
        raise ProposalError("window_is_reversed")
    return LiquiditySettings(**fields)


def _sale(
    available: int,
    inventory: int,
    money: int,
    settings: LiquiditySettings,
    quote: Callable[[int], Any],
) -> tuple[int, int, tuple[int, ...]]:
    gap = max(0, settings.liquidity_target - money)
    if not gap:
        return 0, 0, ()
    cursor = inventory + settings.rival_stress_units
    receipt = 0
    prices: list[int] = []
    for _ in range(min(available, settings.max_units_per_turn)):
        raw = quote(cursor)
        if isinstance(raw, bool):
            raise ProposalError("quote_is_boolean")
        try:
            numeric = float(raw)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ProposalError("quote_not_numeric") from exc
        if not math.isfinite(numeric) or numeric != int(numeric):
            raise ProposalError("quote_not_finite_integer")
        price = int(numeric)
        if price <= 1 or price < settings.minimum_unit_price:
            break
        prices.append(price)
        receipt += price
        cursor += 1
        if receipt >= gap:
            break
    return len(prices), receipt, tuple(prices)


def propose_fertilizer_liquidity(
    observation: Mapping[str, Any],
    configuration: Mapping[str, Any] | None,
    selected: Mapping[str, Any],
    *,
    post_unit_fertilizer: Any,
    quote: Callable[[int], Any],
    settings: LiquiditySettings = LiquiditySettings(),
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    """Append/fill one executable sale without reordering inherited rows."""
    report: dict[str, Any] = {"changed": False, "reason": "declined"}
    try:
        if not isinstance(observation, Mapping):
            raise ProposalError("malformed_observation")
        if not isinstance(selected, Mapping):
            raise ProposalError("malformed_selected_action")
        tuned = _settings(settings)
        cfg = configuration or {}
        step = _integer(observation.get("step"), "step", 0)
        day = step // _integer(cfg.get("turnsPerDay", 24), "turns_per_day", 1)
        report.update(step=step, day=day)
        if not tuned.start_day <= day <= tuned.end_day:
            report["reason"] = "outside_liquidity_window"
            return selected, report

        market = selected.get("market")
        if not isinstance(market, list):
            raise ProposalError("market_queue_not_list")
        limit = executable_market_limit(cfg)
        reason = _conflict(market[:limit])
        if reason:
            report["reason"] = reason
            return selected, report
        place = _slot(market, limit)
        if place is None:
            report["reason"] = "no_final_executable_slot"
            return selected, report

        stock = _integer(post_unit_fertilizer, "post_unit_fertilizer", 0)
        available = max(0, stock - tuned.reserve_units)
        if not available:
            report.update(
                reason="operating_reserve_not_exceeded",
                post_unit_fertilizer=stock,
                reserve_units=tuned.reserve_units,
            )
            return selected, report
        money = _money(observation)
        if money >= tuned.liquidity_target:
            report.update(
                reason="liquidity_target_already_met",
                observed_money=money,
                liquidity_target=tuned.liquidity_target,
            )
            return selected, report
        inventory = _inventory(observation)
        quantity, receipt, prices = _sale(available, inventory, money, tuned, quote)
        if not quantity:
            report.update(
                reason="stressed_price_floor_not_met",
                observed_money=money,
                market_inventory=inventory,
                minimum_unit_price=tuned.minimum_unit_price,
                rival_stress_units=tuned.rival_stress_units,
            )
            return selected, report

        result = copy.deepcopy(selected)
        index, mode = place
        order = ["SELL", ITEM, quantity]
        if mode == "append":
            if index != len(result["market"]):
                raise ProposalError("append_index_mismatch")
            result["market"].append(order)
        else:
            if index >= limit or result["market"][index]:
                raise ProposalError("trailing_slot_mismatch")
            result["market"][index] = order
        report.update(
            changed=True,
            reason="sell_bounded_fertilizer_surplus",
            slot=index,
            slot_mode=mode,
            executable_limit=limit,
            post_unit_fertilizer=stock,
            reserve_units=tuned.reserve_units,
            available_surplus=available,
            quantity=quantity,
            observed_money=money,
            liquidity_target=tuned.liquidity_target,
            market_inventory=inventory,
            rival_stress_units=tuned.rival_stress_units,
            minimum_unit_price=tuned.minimum_unit_price,
            stressed_receipt=receipt,
            stressed_prices=list(prices),
            projected_preexisting_cash_plus_receipt=money + receipt,
            inactive_suffix_rows=max(0, len(market) - limit),
        )
        return result, report
    except (ProposalError, TypeError, KeyError, IndexError, OverflowError) as exc:
        report["reason"] = f"fail_closed:{exc}"
        return selected, report
