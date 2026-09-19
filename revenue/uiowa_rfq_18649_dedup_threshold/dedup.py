#!/usr/bin/env python3
"""Order-preserving dedup: four strategies, one contract.

OPS-PERF-SCAN found 15 sites in the delivered kit written as::

    seen = []
    for x in items:
        if x not in seen:
            seen.append(x)

That is O(n^2) in the length of ``seen``. Those findings were published with
magnitude UNKNOWN. This module exists to measure the cost curve and to provide a
replacement that is safe to adopt without auditing each site.

THE CONTRACT every strategy here must satisfy
---------------------------------------------
Return each distinct item exactly once, in FIRST-SEEN order. That ordering is
not incidental -- the sites doing this are building ordered outputs (distinct
colours in a document, distinct terms in a question), and a faster function that
returns them in a different order is a broken function, not an optimization.
``test_dedup_threshold.py`` asserts all strategies agree before anything is
timed.

WHY ``ordered_unique`` AND NOT JUST "USE A SET"
-----------------------------------------------
A set needs hashable elements. Some of the flagged sites may be deduplicating
dicts or lists, where ``set``/``dict.fromkeys`` raise ``TypeError``. Blanket
advice to "use a set" would break those. ``ordered_unique`` takes the fast path
when it can and falls back to the scan when it cannot, per item, so it is a
drop-in for the existing code regardless of element type.

Python 3 standard library only.
"""
from __future__ import annotations


def dedup_list_scan(items):
    """The form the kit currently uses. O(n^2) in the number of distinct items."""
    seen = []
    for x in items:
        if x not in seen:
            seen.append(x)
    return seen


def dedup_dict_fromkeys(items):
    """The stdlib idiom. O(n), order-preserving since 3.7. Hashable only."""
    return list(dict.fromkeys(items))


def dedup_set_aside(items):
    """Explicit set alongside the output list. O(n). Hashable only."""
    seen_set = set()
    out = []
    for x in items:
        if x not in seen_set:
            seen_set.add(x)
            out.append(x)
    return out


def ordered_unique(items):
    """O(n) for hashable items, correct for everything else.

    Hashable items go through a set. The first unhashable item switches that
    element to a linear scan of the unhashable ones only -- so a list of dicts
    still works (at the old cost) and a mixed sequence works too, instead of
    raising TypeError the way the set-based strategies do.

    This is the one safe to recommend without first auditing whether a given
    site's elements are hashable.
    """
    seen_hashable = set()
    seen_unhashable = []
    out = []
    for x in items:
        try:
            if x in seen_hashable:
                continue
            seen_hashable.add(x)
        except TypeError:
            # Unhashable: fall back to the scan, but only across the other
            # unhashable items, not the whole output.
            if any(x == other for other in seen_unhashable):
                continue
            seen_unhashable.append(x)
        out.append(x)
    return out


#: name -> (callable, requires_hashable)
STRATEGIES = {
    "list_scan": (dedup_list_scan, False),
    "dict_fromkeys": (dedup_dict_fromkeys, True),
    "set_aside": (dedup_set_aside, True),
    "ordered_unique": (ordered_unique, False),
}

#: The strategy this lane recommends, and why it is not one of the faster two.
RECOMMENDED = "ordered_unique"
