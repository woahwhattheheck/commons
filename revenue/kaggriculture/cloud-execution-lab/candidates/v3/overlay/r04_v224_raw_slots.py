# SPDX-License-Identifier: Apache-2.0
"""Raw-slot-preserving V224 SELL ordering for TITAN V4.

Frozen V3.1 V224 first filters its market vector and then bubbles SELL rows
left. Filtering removes falsey / zero / malformed rows, but the official
engine executes both players' market orders in lockstep by raw row index.
Those placeholders are therefore timing barriers, not cosmetic whitespace.

This helper keeps V224's useful contiguous SELL bubbling while preserving the
raw executable prefix. Falsey, malformed and non-positive rows are barriers;
same-item BUY_PRODUCT / BUY_ANIMAL remain barriers exactly as in V224.
"""

from __future__ import annotations

MAX_ORDERS = 10
_QUANTITY_VERBS = {"BUY_PRODUCT", "BUY_ANIMAL", "BUY_SEED", "SELL"}


def _positive_effect(row):
    if not isinstance(row, list) or not row or type(row[0]) is not str:
        return False
    if row[0] in ("HIRE", "BUY_LAND"):
        return True
    if row[0] not in _QUANTITY_VERBS:
        return False
    return len(row) >= 3 and type(row[2]) is int and row[2] > 0


def _sell_item(row):
    if (not isinstance(row, list) or len(row) < 3 or row[0] != "SELL"
            or type(row[1]) is not str or type(row[2]) is not int or row[2] <= 0):
        return None
    return row[1]


def _crossable(row, sell_item):
    """Whether V224 may swap ``sell_item`` one raw slot left across ``row``."""
    if not _positive_effect(row):
        return False
    if row[0] == "SELL":
        return False
    if row[0] in ("BUY_PRODUCT", "BUY_ANIMAL") and len(row) > 1 and row[1] == sell_item:
        return False
    return True


def sales_first_raw_slots(action, *, max_orders=MAX_ORDERS):
    """Apply V224 ordering without deleting or crossing raw-slot barriers.

    The exact parent object is returned when no safe swap is available.
    When a swap occurs, V224's existing executable-prefix behavior is retained:
    only the first ``max_orders`` rows are published.
    """
    if not isinstance(action, dict):
        return action
    market = action.get("market")
    if not isinstance(market, list) or type(max_orders) is not int or max_orders <= 0:
        return action

    original = market[:max_orders]
    rows = [list(row) if isinstance(row, list) else row for row in original]
    changed = False

    for index in range(len(rows)):
        item = _sell_item(rows[index])
        if item is None:
            continue
        cursor = index
        while cursor > 0 and _crossable(rows[cursor - 1], item):
            rows[cursor - 1], rows[cursor] = rows[cursor], rows[cursor - 1]
            cursor -= 1
            changed = True

    if not changed:
        return action
    result = dict(action)
    result["market"] = rows
    return result
