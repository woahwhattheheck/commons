# SPDX-License-Identifier: Apache-2.0
"""H8: internal row arbitration for V3.1 R04 evening-flush additions.

This is an experiment, not release wiring.  The live V3.1 R04 wrapper applies
``ROW_ORDER`` before ``EVENING_FLUSH``.  The flush then prepends up to four residual
WOOL/MILK/STRAWBERRY/MELON SELL rows, sorting those new rows by gross ``price * qty``.
That means the newly-created prefix never sees the competitive ``order_sells`` metric
used by R04 for leading SELL rows.

H8 changes *only the order of the rows that EVENING_FLUSH just prepended*.  Every flush
row remains ahead of the pre-flush market.  Quantities, timing, row count and the
pre-existing market suffix are invariant.  Non-default ``marketParams`` fail closed,
matching R04 ROW_ORDER.  Disabled mode returns the exact post-flush action object.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

FLUSH_ITEMS = frozenset({"WOOL", "MILK", "STRAWBERRY", "MELON"})


def apply_flush_internal_row_order(
    observation: Mapping[str, Any],
    pre_flush_action: Mapping[str, Any],
    post_flush_action: Mapping[str, Any],
    configuration: Mapping[str, Any] | None = None,
    *,
    enabled: bool = False,
    sorter: Callable[[list[list[Any]], Mapping[str, Any]], list[list[Any]]] | None = None,
):
    """Reorder only the prefix demonstrably inserted by ``evening_flush``.

    ``pre_flush_action`` is the action immediately before R04's ``evening_flush`` call;
    ``post_flush_action`` is its return value.  The transform proves that the post-flush
    market is exactly ``new_prefix + pre_market`` before touching anything.  Any shape
    mismatch fails closed.

    ``sorter`` is injectable for focused tests.  Production integration should omit it so
    the exact live ``r04_full_router.order_sells`` implementation is reused rather than
    copied into this experiment.
    """
    report: dict[str, Any] = {
        "enabled": bool(enabled),
        "changed": False,
        "reason": "OFF" if not enabled else "NO_OP",
        "flush_prefix_rows": 0,
    }
    if not enabled:
        return post_flush_action, report

    if (configuration or {}).get("marketParams"):
        report["reason"] = "CUSTOM_MARKET_PARAMS"
        return post_flush_action, report

    try:
        pre_market = pre_flush_action.get("market") or []
        post_market = post_flush_action.get("market") or []
    except AttributeError:
        report["reason"] = "BAD_ACTION"
        return post_flush_action, report

    if not isinstance(pre_market, list) or not isinstance(post_market, list):
        report["reason"] = "BAD_MARKET_QUEUE"
        return post_flush_action, report
    if len(post_market) < len(pre_market):
        report["reason"] = "NOT_A_PREPEND"
        return post_flush_action, report

    prefix_len = len(post_market) - len(pre_market)
    if prefix_len == 0:
        report["reason"] = "NO_FLUSH_PREFIX"
        return post_flush_action, report

    # EVENING_FLUSH is a prepend-only transform.  Prove that invariant before changing
    # row order so this layer cannot accidentally arbitrate another transform's rows.
    if post_market[prefix_len:] != pre_market:
        report["reason"] = "SUFFIX_MISMATCH"
        return post_flush_action, report

    prefix = post_market[:prefix_len]
    report["flush_prefix_rows"] = prefix_len
    for order in prefix:
        if (not isinstance(order, list) or len(order) < 3 or order[0] != "SELL"
                or order[1] not in FLUSH_ITEMS):
            report["reason"] = "NON_FLUSH_PREFIX"
            return post_flush_action, report

    if prefix_len < 2:
        report["reason"] = "SINGLE_FLUSH_ROW"
        return post_flush_action, report

    if sorter is None:
        # Lazy import keeps this experiment inert and guarantees any future integrated
        # candidate uses the exact R04 price-impact metric instead of a forked copy.
        from r04_full_router import order_sells as sorter

    inventory = ((observation.get("market") or {}).get("inventory") or {})
    ordered = sorter([list(order) for order in prefix], inventory)
    if ordered == prefix:
        report["reason"] = "ALREADY_ORDERED"
        return post_flush_action, report

    out = dict(post_flush_action)
    out["market"] = ordered + list(post_market[prefix_len:])
    report.update(
        changed=True,
        reason="REORDER_FLUSH_PREFIX",
        before_prefix=[list(order) for order in prefix],
        after_prefix=[list(order) for order in ordered],
    )
    return out, report
