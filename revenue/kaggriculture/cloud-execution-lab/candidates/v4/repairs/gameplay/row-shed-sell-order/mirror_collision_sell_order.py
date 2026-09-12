# SPDX-License-Identifier: Apache-2.0
"""Mirror/copy SELL queue-index valuation for the canonical TITAN V4 ROWSHED package.

This is an additive research scorer/transformer.  It does not wire a controller,
change a default, or claim dominance against an unknown opponent.

Pinned official engine blob: 3c202c7ee921da239356789e266b694635103fc4
Pinned mechanics blob:       044a4f9c0a4a44dde10ada57563238bcaf82075d
"""
from __future__ import annotations

from copy import deepcopy
import mechanics

ENGINE_BLOB_SHA = "3c202c7ee921da239356789e266b694635103fc4"
MECHANICS_BLOB_SHA = "044a4f9c0a4a44dde10ada57563238bcaf82075d"
DEFAULT_MAX_MARKET_ORDERS = 10


def _plain_nonnegative_int(value):
    return type(value) is int and value >= 0


def _plain_positive_int(value):
    return type(value) is int and value > 0


def _fallback_copy(selected_action, fallback_action):
    return deepcopy(selected_action if fallback_action is None else fallback_action)


def _prefix_limit(configuration):
    if configuration is None:
        return DEFAULT_MAX_MARKET_ORDERS
    if not isinstance(configuration, dict):
        raise ValueError("configuration must be a dict or None")
    raw = configuration.get("maxMarketOrdersPerTurn", DEFAULT_MAX_MARKET_ORDERS)
    if type(raw) is not int:
        raise ValueError("maxMarketOrdersPerTurn must be a plain int")
    return max(1, raw)


def _quote(price_fn, item, inventory, params):
    value = price_fn(item, inventory, params)
    if type(value) is not int or value < 1:
        raise ValueError("market price must be a plain positive int")
    return value


def sell_block_revenue(item, inventory, units, *, price_fn=None, params=None):
    """Exact solo SELL-block cash under official $1-floor inventory semantics.

    The engine increments public supply only when the quoted SELL price is > $1.
    Once an item reaches the floor, later $1 sales therefore do not keep moving
    the market inventory.
    """
    if not isinstance(item, str) or not item:
        raise ValueError("item must be a non-empty string")
    if not _plain_nonnegative_int(inventory):
        raise ValueError("inventory must be a plain non-negative int")
    if not _plain_nonnegative_int(units):
        raise ValueError("units must be a plain non-negative int")
    if params is not None and not isinstance(params, dict):
        raise ValueError("market params must be a dict or None")

    quote = mechanics.market_price if price_fn is None else price_fn
    level = inventory
    revenue = 0
    for _ in range(units):
        price = _quote(quote, item, level, params)
        revenue += price
        if price > 1:
            level += 1
    return revenue, level


def mirror_delay_value(item, inventory, units, *, price_fn=None, params=None):
    """Own-cash value of our q-unit SELL block clearing before vs after mirror q.

    This is exact only for the stated equal-size same-item mirror counterfactual:
    one opposing block of ``units`` either clears immediately after us or
    immediately before us.  It deliberately does not inspect or predict the
    opponent's current action.
    """
    early_cash, early_end = sell_block_revenue(
        item, inventory, units, price_fn=price_fn, params=params
    )
    _rival_cash, delayed_start = sell_block_revenue(
        item, inventory, units, price_fn=price_fn, params=params
    )
    delayed_cash, delayed_end = sell_block_revenue(
        item, delayed_start, units, price_fn=price_fn, params=params
    )
    value = early_cash - delayed_cash
    if value < 0:
        raise ValueError("price curve produced negative mirror delay value")
    return {
        "item": item,
        "inventory": inventory,
        "units": units,
        "early_cash": early_cash,
        "delayed_cash": delayed_cash,
        "mirror_delay_value": value,
        "early_end_inventory": early_end,
        "delayed_start_inventory": delayed_start,
        "delayed_end_inventory": delayed_end,
    }


def endpoint_impact_value(item, inventory, units, *, price_fn=None, params=None):
    """Incumbent ROWSHED endpoint-drop approximation, for comparison only."""
    if not _plain_nonnegative_int(units):
        raise ValueError("units must be a plain non-negative int")
    quote = mechanics.market_price if price_fn is None else price_fn
    before = _quote(quote, item, inventory, params)
    after = _quote(quote, item, inventory + units, params)
    return (before - after) * units


class MirrorCollisionSellOrder:
    """Research-only ROWSHED candidate ranked by exact mirror-delay exposure.

    Safety envelope follows the existing ROWSHED authority:
    - literal ``enabled is True`` is required;
    - only the leading contiguous, parser-live SELL block in the official market
      prefix can move;
    - falsey, non-SELL, zero/non-positive, or malformed rows are barriers;
    - post-unit shed custody determines executable fill;
    - duplicate products in the reorder block fail closed because their fills
      share one stock pool;
    - all rows, quantities, queue length, non-market fields, and inert suffix
      bytes remain unchanged apart from permutation of admitted SELL rows.

    This transform is not runtime-promotion authority.  Ranking by mirror delay
    is a source-real sensitivity heuristic when the opponent's live queue is
    unknown.
    """

    def __init__(self, price_fn=None):
        self.price_fn = mechanics.market_price if price_fn is None else price_fn
        self.diagnostics = {}

    def transform(
        self,
        observation,
        configuration,
        selected_action,
        *,
        post_unit_shed=None,
        enabled=False,
        fallback_action=None,
    ):
        fallback = _fallback_copy(selected_action, fallback_action)
        self.diagnostics = {
            "status": "identity",
            "reason": "default_off",
            "engine_blob": ENGINE_BLOB_SHA,
            "mechanics_blob": MECHANICS_BLOB_SHA,
            "prefix_limit": None,
            "leading_sell_count": 0,
            "scores": [],
        }
        if enabled is not True:
            return deepcopy(selected_action)

        try:
            if not isinstance(observation, dict):
                raise ValueError("observation must be a dict")
            if not isinstance(selected_action, dict):
                raise ValueError("selected action must be a dict")
            if not isinstance(post_unit_shed, dict):
                raise ValueError("post_unit_shed must be a dict")
            rows = selected_action.get("market", [])
            if not isinstance(rows, list):
                raise ValueError("market orders must be a list")

            limit = _prefix_limit(configuration)
            self.diagnostics["prefix_limit"] = limit

            # Match the canonical ROWSHED fail-closed envelope: a truthy
            # non-list row anywhere in the submitted queue makes custody
            # ambiguous, even when it lies beyond the executable prefix.
            if any(row and not isinstance(row, list) for row in rows):
                raise ValueError("truthy market row must be a list")

            market = observation.get("market")
            if not isinstance(market, dict):
                raise ValueError("observation market must be a dict")
            inventory = market.get("inventory")
            if not isinstance(inventory, dict):
                raise ValueError("market inventory must be a dict")
            params = market.get("params")
            if params is not None and not isinstance(params, dict):
                raise ValueError("market params must be a dict or None")

            lead = 0
            prefix_end = min(len(rows), limit)
            while lead < prefix_end:
                row = rows[lead]
                if not row or not isinstance(row, list) or not row or row[0] != "SELL":
                    break
                # Official _parse_order turns missing/non-positive quantities
                # into an inert row.  Treat that exact coordinate as a barrier;
                # never reorder a live SELL across it.
                if len(row) < 3 or not _plain_positive_int(row[2]):
                    break
                lead += 1

            self.diagnostics["leading_sell_count"] = lead
            if lead < 2:
                self.diagnostics["reason"] = "leading_live_sell_block_lt_2"
                return deepcopy(selected_action)

            seen_items = set()
            scored = []
            for index, row in enumerate(rows[:lead]):
                item, requested = row[1], row[2]
                if not isinstance(item, str) or not item:
                    raise ValueError("SELL item must be a non-empty string")
                if item in seen_items:
                    raise ValueError("duplicate SELL item shares projected shed custody")
                seen_items.add(item)

                if item not in post_unit_shed:
                    raise ValueError("projected shed is incomplete for SELL block")
                stock = post_unit_shed[item]
                if not _plain_nonnegative_int(stock):
                    raise ValueError("projected shed count must be a plain non-negative int")
                if item not in inventory:
                    raise ValueError("market inventory is incomplete for SELL block")
                level = inventory[item]
                if not _plain_nonnegative_int(level):
                    raise ValueError("market inventory must be a plain non-negative int")

                fill = min(requested, stock)
                mirror = mirror_delay_value(
                    item,
                    level,
                    fill,
                    price_fn=self.price_fn,
                    params=params,
                )
                endpoint = endpoint_impact_value(
                    item,
                    level,
                    fill,
                    price_fn=self.price_fn,
                    params=params,
                )
                scored.append({
                    "original_index": index,
                    "row": row,
                    "item": item,
                    "requested": requested,
                    "stock": stock,
                    "fillable": fill,
                    "mirror_delay_value": mirror["mirror_delay_value"],
                    "early_cash": mirror["early_cash"],
                    "delayed_cash": mirror["delayed_cash"],
                    "endpoint_impact": endpoint,
                    "floor_frozen": mirror["early_end_inventory"] < level + fill,
                })

            ordered = sorted(
                scored,
                key=lambda entry: entry["mirror_delay_value"],
                reverse=True,
            )
            result = deepcopy(selected_action)
            result["market"][:lead] = [deepcopy(entry["row"]) for entry in ordered]
            self.diagnostics.update(
                status="research_candidate",
                reason="mirror_delay_rank",
                scores=[
                    {key: value for key, value in entry.items() if key != "row"}
                    for entry in scored
                ],
                ordered_items=[entry["item"] for entry in ordered],
            )
            return result
        except (ValueError, TypeError, KeyError, AttributeError, IndexError, OverflowError) as error:
            self.diagnostics.update(status="fallback", reason=str(error))
            return fallback


def transform(observation, configuration, selected_action, **kwargs):
    return MirrorCollisionSellOrder().transform(
        observation, configuration, selected_action, **kwargs
    )
