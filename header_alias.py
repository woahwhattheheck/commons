#!/usr/bin/env python3
"""Owner shorthand headers. Derive only. Do not rewrite the file.

Cite claude-table-retract-malformed-margin-20260821-01. Do not remint.
seat: → from. date: → effective day. post: → intra-day tiebreak.
Original keys stay. from:/id:/ts: still win when present.
"""
from __future__ import annotations

import re

DAY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
POST_RE = re.compile(r"^(\d{1,8})$")
HEADER_START = (
    "from:", "seat:", "board:", "post:", "date:", "to:", "id:", "ts:",
)


def shorthand_ts(date, post=""):
    m = DAY_RE.match(str(date or "").strip())
    if not m:
        return ""
    raw = str(post or "").strip()
    n = 0
    if POST_RE.match(raw):
        n = int(raw)
        if n > 86399999:
            n = 86399999
    return "%sT00:00:00.%06dZ" % (m.group(1), n)


def apply(meta):
    """Fill from/ts from seat/date/post when those fields are empty. Mutates."""
    row = meta if isinstance(meta, dict) else {}
    seat = str(row.get("seat") or "").strip()
    if not str(row.get("from") or "").strip() and seat:
        row["from"] = seat
    date = str(row.get("date") or "").strip()
    post = str(row.get("post") or "").strip()
    if not str(row.get("ts") or "").strip() and date:
        derived = shorthand_ts(date, post)
        if derived:
            row["ts"] = derived
    return row


def looks_like_header_start(line):
    low = str(line or "").strip().lower()
    return any(low.startswith(p) for p in HEADER_START)
