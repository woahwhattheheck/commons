# SPDX-License-Identifier: Apache-2.0
"""Public-market lower bounds used by the stranded-HIRE certificate."""
from __future__ import annotations
import math
from typing import Any, Mapping, Sequence
import mechanics as m
from realized_hire_payback_common import _Reject, _json_clone, _strict_int

_PUBLIC_BUY_PRODUCTS = frozenset({"WHEAT", "FERTILIZER"})

_MONOTONE_SHAPES = frozenset({"linear", "sq", "sqrt", "log", "log10", "hinge"})

def _finite_number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _Reject("invalid_market_params", f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or (positive and number <= 0):
        raise _Reject("invalid_market_params", f"{name} is outside the admitted domain")
    return number

def _validate_market(
    market: Any, unlocked_shops: Any
) -> tuple[dict[str, int], Mapping[str, Any] | None, list[str]]:
    if not isinstance(market, Mapping):
        raise _Reject("invalid_market_state")
    market_copy = _json_clone(dict(market), "market")
    inventory = market_copy.get("inventory")
    if not isinstance(inventory, dict):
        raise _Reject("invalid_market_inventory")
    normalized_inventory: dict[str, int] = {}
    for product in m.PRODUCTS:
        normalized_inventory[product] = _strict_int(
            inventory.get(product), f"market.inventory.{product}"
        )

    params = market_copy.get("params")
    if params is not None and not isinstance(params, Mapping):
        raise _Reject("invalid_market_params")
    if not params:
        params = None

    shops = _json_clone(unlocked_shops, "unlocked_shops")
    if not isinstance(shops, list):
        raise _Reject("invalid_unlocked_shops")
    for shop in shops:
        if not isinstance(shop, str) or shop not in m.SHOPS:
            raise _Reject("invalid_unlocked_shop", repr(shop)[:120])
    return normalized_inventory, params, shops

def _assert_monotone_price_params(
    product: str, params: Mapping[str, Any] | None
) -> None:
    resolved = params or getattr(m, "MARKET_PARAMS", None)
    if not isinstance(resolved, Mapping) or not isinstance(resolved.get(product), Mapping):
        raise _Reject("invalid_market_params", product)
    row = resolved[product]
    _finite_number(row.get("base"), f"{product}.base", positive=True)
    _finite_number(row.get("I0"), f"{product}.I0")
    _finite_number(row.get("T"), f"{product}.T", positive=True)
    for field in ("below_target", "above_target"):
        if _finite_number(row.get(field), f"{product}.{field}") < 0:
            raise _Reject("nonmonotone_market_params", f"{product}.{field}")
    for field in ("below_func", "above_func"):
        if row.get(field) not in _MONOTONE_SHAPES:
            raise _Reject("nonmonotone_market_params", f"{product}.{field}")

def _town_absorption(
    product: str, step: int, shops: Sequence[str], cfg: Mapping[str, Any]
) -> int:
    shop_interval = _strict_int(
        cfg.get("townShopSellInterval", 4), "townShopSellInterval", minimum=1
    )
    center_interval = _strict_int(
        cfg.get("townCenterSellInterval", 24), "townCenterSellInterval", minimum=1
    )
    amount = 0
    if step % shop_interval == 0:
        for shop in shops:
            products = m.SHOPS[shop]
            if product in products:
                amount += 2 if len(products) == 1 else 1
    if product != "FERTILIZER" and step % center_interval == 0:
        amount += 1
    return amount

def _floor_neutral_sale_proof(
    *,
    product: str,
    sale_step: int,
    current_step: int,
    initial_inventory: Mapping[str, int],
    params: Mapping[str, Any] | None,
    shops: Sequence[str],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    # Rival BUY_PRODUCT can reduce only WHEAT/FERTILIZER inventory, and its
    # hidden shed/cash path is not source-bounded here. Refuse those products.
    if product in _PUBLIC_BUY_PRODUCTS:
        return {
            "guaranteed": False,
            "reason": "rival_buy_can_raise_price",
            "product": product,
            "sale_step": sale_step,
        }
    _assert_monotone_price_params(product, params)
    minimum_inventory = initial_inventory[product]
    for step in range(current_step, sale_step):
        minimum_inventory -= _town_absorption(product, step, shops, cfg)
    price_floor = _strict_int(getattr(m, "PRICE_FLOOR", 1), "PRICE_FLOOR", minimum=1)
    maximum_possible_price = _strict_int(
        m.market_price(product, minimum_inventory, params),
        f"maximum_possible_price.{product}",
        minimum=price_floor,
    )
    guaranteed = maximum_possible_price == price_floor
    return {
        "guaranteed": guaranteed,
        "reason": ("floor_price_public_state_neutral" if guaranteed
                   else "sale_not_guaranteed_at_price_floor"),
        "product": product,
        "sale_step": sale_step,
        "observed_inventory": initial_inventory[product],
        "minimum_inventory_before_sale": minimum_inventory,
        "maximum_possible_price": maximum_possible_price,
        "price_floor": price_floor,
    }
