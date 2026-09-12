# SPDX-License-Identifier: Apache-2.0
"""Evidence-only current-ABI recovery of submitted V3.1 ROW_ORDER.

ROW_ORDER is the baseline requested-quantity SELL priority theorem that precedes
r04_row_shed in the submitted winner.  This module is deliberately a pure
selected-action transform: it never invokes a producer/controller and it does
not project shed stock.  A later row-shed stage may rescore the same leading
SELL block with fillable quantities.

For admitted current-engine rows, the price curves and impact formula are copied
from the exact submitted donor.  Current-ABI ambiguity tightens fail-closed:
falsey rows, nonpositive SELL rows and the first non-SELL row are hard barriers;
malformed executable evidence returns the exact selected action unchanged.
"""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

SUBMITTED_V31_SOURCE = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
SUBMITTED_R04_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/"
    "r04_full_router.py"
)
SUBMITTED_R04_GIT_BLOB = "a3e2fe87c717d128e43c9b65bae2265f40d1d76d"

RO_I0 = 10000
RO_PARAMS = {
    "WHEAT": (25, 400, "sqrt", 0.80, "log", 0.20),
    "CARROT": (35, 450, "hinge", 1.00, "sqrt", 0.70),
    "TOMATO": (60, 200, "hinge", 0.40, "sqrt", 0.60),
    "STRAWBERRY": (120, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON": (250, 300, "log", 0.20, "sq", 3.60),
    "EGG": (50, 332, "hinge", 0.40, "log", 0.20),
    "MILK": (160, 122, "sqrt", 0.60, "linear", 1.60),
    "WOOL": (200, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 200, "linear", 0.40, "linear", 0.40),
}


def _shape(func: str, x: float, span: float) -> float:
    x = max(0.0, x)
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return x ** 0.5
    if func == "log":
        return math.log(1.0 + x)
    if func == "hinge":
        u = x / span
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x


def _price(item: str, inventory: int) -> int:
    base, span, below_f, below_t, above_f, above_t = RO_PARAMS[item]
    if inventory < RO_I0:
        amp = below_t * base / _shape(below_f, span, span)
        price = base + amp * _shape(below_f, RO_I0 - inventory, span)
    else:
        amp = above_t * base / _shape(above_f, span, span)
        price = base - amp * _shape(above_f, inventory - RO_I0, span)
    return max(1, int(round(price)))


def _market_prefix_limit(configuration: Any) -> int:
    if configuration is None:
        return 10
    if not isinstance(configuration, dict):
        raise ValueError("configuration must be a dict or None")
    value = configuration.get("maxMarketOrdersPerTurn", 10)
    if type(value) is not int:
        raise ValueError("maxMarketOrdersPerTurn must be a plain int")
    return max(1, value)


def _market_params_override(configuration: Any) -> bool:
    if configuration is None:
        return False
    if not isinstance(configuration, dict):
        raise ValueError("configuration must be a dict or None")
    params = configuration.get("marketParams")
    if params is not None and not isinstance(params, dict):
        raise ValueError("marketParams must be a dict or None")
    return bool(params)


def _plain_nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


class RowOrderCurrentABI:
    """Sort only the executable contiguous leading SELL block by donor impact."""

    def __init__(self) -> None:
        self.diagnostics: dict[str, Any] = {}

    def transform(self, observation, configuration, selected_action):
        fallback = deepcopy(selected_action)
        self.diagnostics = {
            "status": "fallback",
            "reason": None,
            "leading_sell_count": 0,
            "market_prefix_limit": None,
            "scores": [],
            "submitted_source": SUBMITTED_V31_SOURCE,
            "submitted_r04_git_blob": SUBMITTED_R04_GIT_BLOB,
        }
        try:
            if not isinstance(observation, dict):
                raise ValueError("observation must be a dict")
            if not isinstance(selected_action, dict):
                raise ValueError("selected_action must be a dict")

            limit = _market_prefix_limit(configuration)
            self.diagnostics["market_prefix_limit"] = limit
            if _market_params_override(configuration):
                self.diagnostics.update(
                    status="identity",
                    reason="marketParams_override",
                )
                return deepcopy(selected_action)

            rows = selected_action.get("market", [])
            if not isinstance(rows, list):
                raise ValueError("market must be a list")

            market = observation.get("market")
            if not isinstance(market, dict):
                raise ValueError("observation.market must be a dict")
            inventory = market.get("inventory")
            if not isinstance(inventory, dict):
                raise ValueError("observation.market.inventory must be a dict")

            stop = min(len(rows), limit)
            lead = 0
            while lead < stop:
                row = rows[lead]
                if not row:
                    break
                if not isinstance(row, list):
                    raise ValueError("truthy executable market row must be a list")
                if not row or row[0] != "SELL":
                    break
                if len(row) < 3:
                    raise ValueError("leading SELL row is missing item or quantity")
                item, quantity = row[1], row[2]
                if not isinstance(item, str) or not item:
                    raise ValueError("SELL item must be a non-empty string")
                if not _plain_nonnegative_int(quantity):
                    raise ValueError("SELL quantity must be a plain non-negative int")
                # Current engine rejects nonpositive SELL rows.  Treat one as a
                # barrier so no live row can move across an engine-dead slot.
                if quantity <= 0:
                    break
                if item in RO_PARAMS:
                    if item not in inventory:
                        raise ValueError("market inventory is incomplete for leading SELL block")
                    level = inventory[item]
                    if not _plain_nonnegative_int(level):
                        raise ValueError("market inventory count must be a plain non-negative int")
                lead += 1

            self.diagnostics["leading_sell_count"] = lead
            if lead < 2:
                self.diagnostics.update(
                    status="identity",
                    reason="leading_sell_block_lt_2",
                )
                return deepcopy(selected_action)

            scored = []
            for index, row in enumerate(rows[:lead]):
                item, quantity = row[1], row[2]
                if item not in RO_PARAMS:
                    impact = 0
                else:
                    level = inventory[item]
                    impact = (_price(item, level) - _price(item, level + quantity)) * quantity
                scored.append((impact, index, row))

            # Python's stable sort preserves exact incumbent order for ties.
            ordered = sorted(scored, key=lambda entry: entry[0], reverse=True)
            result = deepcopy(selected_action)
            result["market"][:lead] = [deepcopy(row) for _impact, _index, row in ordered]
            self.diagnostics.update(
                status="applied" if result != selected_action else "identity",
                reason="requested_quantity_price_impact",
                scores=[
                    {
                        "original_index": index,
                        "item": row[1],
                        "requested": row[2],
                        "impact": impact,
                    }
                    for impact, index, row in scored
                ],
            )
            return result
        except (ValueError, TypeError, KeyError, AttributeError, IndexError, OverflowError) as error:
            self.diagnostics["reason"] = str(error)
            return fallback

    act = transform


def transform(observation, configuration, selected_action):
    """Stateless convenience surface matching the current selected-action ABI."""
    return RowOrderCurrentABI().transform(observation, configuration, selected_action)
