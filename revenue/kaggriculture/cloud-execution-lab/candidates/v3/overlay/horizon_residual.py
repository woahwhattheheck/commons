# SPDX-License-Identifier: Apache-2.0
"""Measured V1/V2 recovery factor: complete residual stock at a bounded horizon.

This module does not choose a horizon, alter an inherited SELL, or emit an action.
It only completes the seller's reference schedule with the residual quantity that
was not represented by current, pending, or unchanged route SELL rows. The caller
owns activation through the deterministic ``horizon_residual`` package key.
"""
from __future__ import annotations


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("%s must be an integer" % name)
    return value


def _rows(reference):
    rows = []
    for index, row in enumerate(reference):
        if not isinstance(row, (tuple, list)) or len(row) != 2:
            raise TypeError("reference row %d must be a date/quantity pair" % index)
        date = _integer(row[0], "reference date")
        quantity = _integer(row[1], "reference quantity")
        if quantity < 0:
            raise ValueError("reference quantity must be nonnegative")
        rows.append((date, quantity))
    return rows


def _coalesce(rows):
    totals = {}
    for date, quantity in rows:
        totals[date] = totals.get(date, 0) + quantity
    return tuple((date, totals[date]) for date in sorted(totals))


def force_residual_at_horizon(reference, remaining, end, *, item=None, enabled=False):
    """Return the canonical coalesced reference, optionally completed at ``end``.

    ``remaining`` is the already-computed unscheduled residual. Existing rows are
    never moved or reduced; an existing horizon row is coalesced with the residual.
    The input sequence is never mutated. Invalid active inputs raise so the caller
    can fail closed to the canonical reference and record a diagnostic.
    """
    rows = _rows(reference)
    baseline = _coalesce(rows)
    report = {
        "enabled": bool(enabled),
        "changed": False,
        "reason": "HORIZON_RESIDUAL_FLAG_OFF" if not enabled else "HORIZON_RESIDUAL_ZERO",
        "item": item,
        "remaining": remaining,
        "end": end,
        "reference_before": [list(row) for row in baseline],
        "reference_after": [list(row) for row in baseline],
    }
    if not enabled:
        return baseline, report
    remaining = _integer(remaining, "remaining")
    end = _integer(end, "end")
    if remaining < 0:
        raise ValueError("remaining must be nonnegative")
    if rows and end < max(date for date, _quantity in rows):
        raise ValueError("end precedes an inherited reference date")
    if remaining == 0:
        return baseline, report
    result = _coalesce([*rows, (end, remaining)])
    if sum(quantity for _date, quantity in result) != (
        sum(quantity for _date, quantity in baseline) + remaining
    ):
        raise AssertionError("residual reference conservation failed")
    report.update(
        changed=True,
        reason="HORIZON_RESIDUAL_APPENDED",
        reference_after=[list(row) for row in result],
    )
    return result, report
