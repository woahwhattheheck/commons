# SPDX-License-Identifier: Apache-2.0
"""Fail-closed public surface for the recovered R04 market microstack.

The historical V224 helper compacts zero/dead rows. At the current selected-action
boundary that is only safe for a zero quantity created *inside this component* by
settling an authenticated prior reservation. A dead row supplied by the current
producer is a barrier/evidence ambiguity and must fail closed instead of being
silently deleted.
"""
from __future__ import annotations

from copy import deepcopy

from market_microstack_current import (
    MAX_ORDERS,
    R04MarketMicrostackCurrentABI as _Base,
)


class R04MarketMicrostackCurrentABI(_Base):
    """Canonical public class; use this instead of the base implementation."""

    @staticmethod
    def _validate_action(action, *, workers=None):
        _Base._validate_action(action, workers=workers)
        market = action.get("market", [])
        if len(market) > MAX_ORDERS:
            raise ValueError("current boundary requires executable market prefix only")
        for row in market:
            if row[0] not in {"HIRE", "BUY_LAND"} and row[2] <= 0:
                raise ValueError("pre-existing nonpositive market row fails closed")

    @staticmethod
    def _sales_first(action):
        """Exact V224 compaction after internal settlement on an admitted input."""
        original = action["market"][:MAX_ORDERS]
        orders = [
            list(row)
            for row in original
            if row
            and (
                row[0] in ("HIRE", "BUY_LAND")
                or (len(row) >= 3 and row[2] > 0)
            )
        ]
        for index in range(len(orders)):
            order = orders[index]
            if order[0] != "SELL":
                continue
            cursor = index
            while cursor > 0:
                previous = orders[cursor - 1]
                if previous[0] == "SELL":
                    break
                if (
                    previous[0] in ("BUY_PRODUCT", "BUY_ANIMAL")
                    and previous[1] == order[1]
                ):
                    break
                orders[cursor - 1], orders[cursor] = (
                    orders[cursor],
                    orders[cursor - 1],
                )
                cursor -= 1
        if orders == original:
            return action, False
        changed = deepcopy(action)
        changed["market"] = orders
        return changed, True
