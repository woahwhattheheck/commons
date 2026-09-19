"""Date arithmetic for open dependencies and milestone due dates.

Kept separate and pure so it can be tested on its own and so no part of the
packet build reads the wall clock. Every function takes an explicit `as_of`
date: a report that silently depends on when it was run is not reproducible,
and a packet that says "3 days overdue" with no as-of date is unusable as
evidence later.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Any

from schema import UNKNOWN, SchemaError

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

DUE_UNKNOWN = "DUE_DATE_UNKNOWN"
OVERDUE = "OVERDUE"
DUE_TODAY = "DUE_TODAY"
UPCOMING = "UPCOMING"
CLOSED = "CLOSED"


def parse_date(raw: Any) -> Any:
    """ISO date string -> date, or UNKNOWN. Never guesses a date."""
    if raw is UNKNOWN or raw is None or raw == "":
        return UNKNOWN
    if isinstance(raw, datetime.date):
        return raw
    if not isinstance(raw, str) or not _ISO.match(raw.strip()):
        raise SchemaError(f"expected a YYYY-MM-DD date, got {raw!r}")
    y, m, d = (int(p) for p in raw.strip().split("-"))
    try:
        return datetime.date(y, m, d)
    except ValueError as exc:
        raise SchemaError(f"invalid calendar date {raw!r}: {exc}") from exc


def days_between(start: Any, end: Any) -> Any:
    """Calendar days from start to end. UNKNOWN in, UNKNOWN out -- never 0."""
    if start is UNKNOWN or end is UNKNOWN:
        return UNKNOWN
    return (parse_date(end) - parse_date(start)).days


def deadline_from(completion: Any, days: int) -> Any:
    """completion + N calendar days. Used for post-delivery obligation windows.

    Calendar days, not business days: a contract that says 30 days means 30
    days, and quietly converting to business days would move the date.
    """
    if completion is UNKNOWN:
        return UNKNOWN
    if not isinstance(days, int) or isinstance(days, bool):
        raise SchemaError("deadline_from needs an integer number of days")
    return (parse_date(completion) + datetime.timedelta(days=days)).isoformat()


@dataclass
class DueStatus:
    state: str
    days_remaining: Any     # negative when overdue, UNKNOWN when no date
    note: str = ""


def classify_due(needed_by: Any, as_of: Any, closed: bool = False) -> DueStatus:
    """Where a dated obligation stands on a given day.

    A dependency with no date is DUE_DATE_UNKNOWN, not "fine" and not overdue.
    That is the case most likely to be mishandled: an undated open item reads as
    harmless right up until it blocks a milestone.
    """
    if closed:
        return DueStatus(CLOSED, UNKNOWN, "closed; no outstanding date")
    if needed_by is UNKNOWN:
        return DueStatus(
            DUE_UNKNOWN, UNKNOWN,
            "open with no agreed date -- cannot be called on time or late",
        )
    remaining = days_between(as_of, needed_by)
    if remaining < 0:
        return DueStatus(OVERDUE, remaining, f"{abs(remaining)} day(s) past the needed-by date")
    if remaining == 0:
        return DueStatus(DUE_TODAY, 0, "needed today")
    return DueStatus(UPCOMING, remaining, f"{remaining} day(s) remaining")
