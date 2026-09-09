# SPDX-License-Identifier: Apache-2.0
"""Rival-lockstep safety wrapper for the KESTREL early-capital candidate.

The wrapped candidate proves execution against the player's own queue.  The
official engine, however, quotes both players from the same pre-commit market at
each queue index.  Reordering around variable-price BUY_PRODUCT orders or
WHEAT/FERTILIZER sales therefore cannot be certified without the rival queue.

This module keeps the predecessor's useful fixed-cost capital admission only
where public engine semantics give a rival-independent proof:

* active-prefix membership and every order remain unchanged;
* no variable-price BUY_PRODUCT is present in the executable prefix;
* WHEAT/FERTILIZER sales are absent because rivals may buy those products; and
* every moved sale is of a sale-only product with a verified nonincreasing
  public price curve.  Rivals can only add supply for those products, so moving
  our sale earlier cannot reduce its receipt.

When no caller-owned post-unit snapshot exists, unit replay also mirrors the
official interpreter's atomic same-crop PLANT demand prepass before applying
farmer and hand actions.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from collections.abc import Mapping
from typing import Any

from kestrel_early_capital import order_early_capital as _predecessor_order

BUYABLE_PRODUCTS = frozenset(("WHEAT", "FERTILIZER"))
_MAX_CERTIFIED_SHED_CAPACITY = 256


def _configuration_value(configuration: Mapping | None, key: str, default: Any) -> Any:
    if isinstance(configuration, Mapping):
        return configuration.get(key, default)
    return default


def _unit_actions(selected: Mapping) -> list[Any]:
    farmer = selected.get("farmer", ["PASS"])
    hands = selected.get("hands", [])
    if not isinstance(hands, list):
        hands = []
    return [farmer, *hands]


def _atomic_post_unit_snapshot(
    mechanics: Any,
    observation: Mapping,
    configuration: Mapping | None,
    selected: Mapping,
) -> dict:
    """Reconstruct the official completed own unit stage.

    The engine first aggregates PLANT requests by crop.  If demand exceeds the
    currently held seed count, every PLANT for that crop is replaced by PASS;
    only then are farmer and hand actions applied in order.
    """
    if not isinstance(observation, Mapping) or not isinstance(selected, Mapping):
        raise ValueError("malformed unit replay input")
    farms_source = observation.get("farms")
    private_source = observation.get("private")
    if not isinstance(farms_source, list) or not isinstance(private_source, Mapping):
        raise ValueError("missing own unit state")
    player_raw = observation.get("player", 0)
    if isinstance(player_raw, bool):
        raise ValueError("invalid player")
    player = int(player_raw)
    if player < 0 or player >= len(farms_source):
        raise ValueError("invalid player")

    farms = deepcopy(farms_source)
    private = deepcopy(dict(private_source))
    farm = farms[player]
    if not isinstance(farm, dict):
        raise ValueError("invalid farm")
    tiles = farm.get("tiles")
    if not isinstance(tiles, list) or not tiles:
        raise ValueError("missing farm tiles")

    turns_per_day = max(
        1,
        int(_configuration_value(configuration, "turnsPerDay", 24)),
    )
    board_size = int(
        _configuration_value(configuration, "boardSize", len(tiles))
    )
    shed_capacity = int(
        _configuration_value(configuration, "shedCapacity", 100)
    )
    step_raw = observation.get("step", 0)
    if isinstance(step_raw, bool):
        raise ValueError("invalid step")
    day = int(step_raw) // turns_per_day

    apply_unit = getattr(mechanics, "_apply_unit_action", None)
    if not callable(apply_unit):
        raise ValueError("mechanics lacks unit replay")

    actions = _unit_actions(selected)
    demand: dict[Any, int] = {}
    for action in actions:
        if isinstance(action, list) and len(action) >= 2 and action[0] == "PLANT":
            crop = action[1]
            try:
                demand[crop] = demand.get(crop, 0) + 1
            except TypeError as exc:
                raise ValueError("unhashable crop") from exc

    seeds = private.get("seeds", {})
    if not isinstance(seeds, Mapping):
        raise ValueError("missing seed ledger")
    blocked = set()
    for crop, requested in demand.items():
        available = seeds.get(crop, 0)
        if isinstance(available, bool) or not isinstance(available, (int, float)):
            raise ValueError("invalid seed quantity")
        if not math.isfinite(float(available)):
            raise ValueError("invalid seed quantity")
        if requested > available:
            blocked.add(crop)

    for index, action in enumerate(actions):
        allowed = action
        if (
            isinstance(action, list)
            and len(action) >= 2
            and action[0] == "PLANT"
            and action[1] in blocked
        ):
            allowed = ["PASS"]
        apply_unit(
            farm,
            private,
            index,
            allowed,
            board_size,
            day,
            turns_per_day,
            shed_capacity,
        )

    return {
        "farms": farms,
        "private": private,
        "player": player,
        "step": int(step_raw),
    }


def _canonical_order(order: Any) -> str:
    try:
        return json.dumps(
            order,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("uncanonicalizable market order") from exc


def _same_order_multiset(left: list[Any], right: list[Any]) -> bool:
    if len(left) != len(right):
        return False
    return sorted(_canonical_order(order) for order in left) == sorted(
        _canonical_order(order) for order in right
    )


def _sell_item(order: Any) -> str | None:
    if (
        isinstance(order, list)
        and len(order) >= 3
        and order[0] == "SELL"
        and isinstance(order[1], str)
    ):
        return order[1]
    return None


def _sales_never_move_later(
    original: list[Any], candidate: list[Any], products: set[str]
) -> bool:
    """Check the kth sale of every affected product is no later than before."""
    before = {product: 0 for product in products}
    after = {product: 0 for product in products}
    for original_order, candidate_order in zip(original, candidate):
        original_item = _sell_item(original_order)
        candidate_item = _sell_item(candidate_order)
        if original_item in before:
            before[original_item] += 1
        if candidate_item in after:
            after[candidate_item] += 1
        if any(after[product] < before[product] for product in products):
            return False
    return True


def _checked_market_price(
    mechanics: Any,
    item: str,
    inventory: int,
    params: Mapping | None,
) -> float:
    price = mechanics.market_price(item, inventory, params)
    if isinstance(price, bool) or not isinstance(price, (int, float)):
        raise ValueError("non-numeric market price")
    value = float(price)
    if not math.isfinite(value) or value < 1:
        raise ValueError("invalid market price")
    return value


def _rival_lockstep_certificate(
    mechanics: Any,
    observation: Mapping,
    configuration: Mapping | None,
    original_action: Mapping,
    candidate_action: Mapping,
) -> tuple[bool, dict]:
    """Prove a changed queue is safe for every legal hidden rival queue."""
    report: dict[str, Any] = {
        "schema": 1,
        "kind": "sale-only-earlier-fixed-cost",
        "certified": False,
        "barriers": [],
        "products": [],
    }
    if not isinstance(original_action, Mapping) or not isinstance(candidate_action, Mapping):
        report["barriers"].append("malformed_action")
        return False, report
    original_market = original_action.get("market")
    candidate_market = candidate_action.get("market")
    if not isinstance(original_market, list) or not isinstance(candidate_market, list):
        report["barriers"].append("malformed_market")
        return False, report

    try:
        limit = max(
            1,
            int(_configuration_value(configuration, "maxMarketOrdersPerTurn", 10)),
        )
        capacity = int(_configuration_value(configuration, "shedCapacity", 100))
    except (TypeError, ValueError, OverflowError):
        report["barriers"].append("invalid_configuration")
        return False, report
    report["active_prefix_limit"] = limit
    report["shed_capacity"] = capacity
    if capacity < 1 or capacity > _MAX_CERTIFIED_SHED_CAPACITY:
        report["barriers"].append("unsupported_shed_capacity")
        return False, report

    original_active = original_market[:limit]
    candidate_active = candidate_market[:limit]
    if original_market[limit:] != candidate_market[limit:]:
        report["barriers"].append("inactive_tail_changed")
    try:
        if not _same_order_multiset(original_active, candidate_active):
            report["barriers"].append("active_prefix_membership_changed")
    except ValueError:
        report["barriers"].append("uncanonicalizable_order")

    for order in original_active:
        if isinstance(order, list) and order and order[0] == "BUY_PRODUCT":
            report["barriers"].append("variable_price_buy_product")
        item = _sell_item(order)
        if item in BUYABLE_PRODUCTS:
            report["barriers"].append(f"rival_buyable_sale:{item}")

    products = {
        item for order in original_active
        if (item := _sell_item(order)) is not None
    }
    report["products"] = sorted(products)
    if not _sales_never_move_later(original_active, candidate_active, products):
        report["barriers"].append("sale_moved_later")

    market = observation.get("market") if isinstance(observation, Mapping) else None
    inventory = market.get("inventory") if isinstance(market, Mapping) else None
    prices = market.get("prices") if isinstance(market, Mapping) else None
    params = market.get("params") if isinstance(market, Mapping) else None
    if (
        not isinstance(market, Mapping)
        or not isinstance(inventory, Mapping)
        or not isinstance(prices, Mapping)
        or (params is not None and not isinstance(params, Mapping))
    ):
        report["barriers"].append("malformed_public_market")
        return False, report

    curve_checks: dict[str, dict[str, Any]] = {}
    horizon = 2 * capacity
    for item in sorted(products):
        if item in BUYABLE_PRODUCTS:
            continue
        start = inventory.get(item)
        visible = prices.get(item)
        if (
            isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(visible, bool)
            or not isinstance(visible, (int, float))
            or not math.isfinite(float(visible))
            or float(visible) < 1
        ):
            report["barriers"].append(f"invalid_public_quote:{item}")
            continue
        try:
            curve = [
                _checked_market_price(mechanics, item, start + offset, params)
                for offset in range(horizon + 1)
            ]
        except (ArithmeticError, KeyError, LookupError, TypeError, ValueError, OverflowError):
            report["barriers"].append(f"unavailable_price_curve:{item}")
            continue
        if curve[0] != float(visible):
            report["barriers"].append(f"stale_public_quote:{item}")
        if any(later > earlier for earlier, later in zip(curve, curve[1:])):
            report["barriers"].append(f"nonmonotone_price_curve:{item}")
        curve_checks[item] = {
            "inventory_start": start,
            "inventory_end": start + horizon,
            "visible_price": float(visible),
            "end_price": curve[-1],
            "samples": horizon + 1,
        }
    report["curve_checks"] = curve_checks
    report["barriers"] = sorted(set(report["barriers"]))
    report["certified"] = not report["barriers"]
    if report["certified"]:
        report["proof"] = (
            "Rivals cannot buy the sold products; rival actions can only add "
            "same-product supply. Every own sale is no later than before and "
            "the checked public price curves are nonincreasing. All remaining "
            "own costs are fixed, so the predecessor's own-state execution "
            "gate remains valid under every legal rival queue."
        )
    return report["certified"], report


def order_early_capital(
    mechanics: Any,
    observation: Mapping,
    configuration: Mapping | None,
    selected: Any,
    route: Any,
    decisions: Any = (),
    *,
    post_unit: Mapping | None = None,
):
    """Run KESTREL, then admit only a rival-lockstep-certified change."""
    bound_post_unit = post_unit
    generated = False
    if post_unit is None and isinstance(selected, Mapping):
        try:
            bound_post_unit = _atomic_post_unit_snapshot(
                mechanics, observation, configuration, selected
            )
            generated = True
        except (
            ArithmeticError, KeyError, TypeError, ValueError, OverflowError,
            AttributeError,
        ) as error:
            # Preserve the predecessor's fail-closed behavior, but do not let it
            # fall back to its known-sequential unit reconstruction.
            report = {
                "changed": False,
                "reason": "atomic_unit_replay_unavailable",
                "revision": "v3-rival-lockstep-safe",
                "simulation_error": type(error).__name__,
                "post_unit_binding": "unavailable",
            }
            return selected, report

    result, report = _predecessor_order(
        mechanics,
        observation,
        configuration,
        selected,
        route,
        decisions,
        post_unit=bound_post_unit,
    )
    report = deepcopy(report) if isinstance(report, dict) else {"predecessor_report": report}
    report["revision"] = "v3-rival-lockstep-safe"
    report["post_unit_binding"] = (
        "official_atomic_unit_replay" if generated else "caller_snapshot"
    )

    if result == selected:
        report["lockstep_certificate"] = {
            "schema": 1,
            "certified": True,
            "kind": "identity",
            "proof": "No market bytes changed.",
        }
        return result, report

    certified, certificate = _rival_lockstep_certificate(
        mechanics,
        observation,
        configuration,
        selected,
        result,
    )
    report["lockstep_certificate"] = certificate
    if certified:
        report["reason"] = "execution_gain_lockstep_proved"
        return result, report

    report["pre_lockstep_reason"] = report.get("reason")
    report["reason"] = "rival_interleaving_unproven"
    report["changed"] = False
    report["moved"] = 0
    return selected, report


__all__ = [
    "BUYABLE_PRODUCTS",
    "_atomic_post_unit_snapshot",
    "_rival_lockstep_certificate",
    "order_early_capital",
]
