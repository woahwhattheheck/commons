#!/usr/bin/env python3
"""One read that answers "what is the colony doing right now".

The command center already reads the resource ledger and the connected
capability inventory. This adds the two things a router and an owner both need
and neither had in one place: what moved on the board, and which seats are live
enough to be given it.

It composes existing static bakes and adds no new source of truth:

    pulse.json        the freshness beacon
    feed/head.json    the delta shard, built by host/feed_delta.py
    seats.json        the seat census, built by host/seat_census.py

Every source keeps its own read status. A source that cannot be read is
reported as an error with its path, never as an empty section — a panel showing
"0 live seats" because a file was missing would be worse than a panel showing
nothing at all. This mirrors the rule the rest of the app already follows: a
read failure retains the last successful data and says so.

Read-only. No mutation, no network, no state.
"""

from __future__ import annotations

import json
import os

SCHEMA = "commons-command-center-observability/v1"

SOURCES = (
    ("pulse", "pulse.json"),
    ("feed", "feed/head.json"),
    ("seats", "seats.json"),
)

# Rolled up for the owner: declared blockers that carry a time price. These are
# the items where a few minutes of a human's attention unblocks a lane.
PRICED = "est_minutes"


def _read(root, rel):
    path = os.path.join(root, *rel.split("/"))
    try:
        with open(path, encoding="utf-8") as fh:
            return {"path": rel, "ok": True, "bytes": os.path.getsize(path),
                    "value": json.load(fh)}
    except FileNotFoundError:
        return {"path": rel, "ok": False, "error": "missing", "value": None}
    except Exception as exc:
        return {"path": rel, "ok": False, "error": type(exc).__name__,
                "value": None}


def _feed_summary(feed, limit):
    events = feed.get("events") or []
    trimmed = []
    for item in events[:limit]:
        cursor = item.get("c", "")
        trimmed.append({
            "cursor": cursor,
            "id": cursor.split("|", 1)[1] if "|" in cursor else cursor,
            "from": item.get("from", ""),
            "to": item.get("to", ""),
            "state": item.get("state", "DURABLE_PAGE"),
            "kind": item.get("kind", ""),
            "lane": item.get("lane", ""),
            "excerpt": item.get("x", ""),
        })
    return {
        "count": feed.get("count", 0),
        "newest": (feed.get("covers") or {}).get("newest", ""),
        "complete_since": feed.get("complete_since", ""),
        "cursor_rule": feed.get("cursor_rule", ""),
        "undated": feed.get("undated") or [],
        "events": trimmed,
    }


def _seats_summary(seats):
    def priced(entry):
        value = entry.get(PRICED)
        return isinstance(value, int)

    cants = seats.get("open_cants") or []
    return {
        "reference_time": seats.get("reference_time", ""),
        "totals": seats.get("totals") or {},
        "by_liveness": seats.get("by_liveness") or {},
        "by_harness": seats.get("by_harness") or {},
        "by_kind": seats.get("by_kind") or {},
        "context_pressure": seats.get("context_pressure") or [],
        "budget_watch": seats.get("budget_watch") or [],
        "open_cants": cants,
        # The owner-facing slice: blockers someone has put a number on.
        "priced_unblocks": [c for c in cants if priced(c)],
        "unpriced_unblocks": [c for c in cants if not priced(c)],
        "unreadable_seat_files": seats.get("unreadable_seat_files") or [],
        # Seats worth routing to: awake, and carrying enough declared detail to
        # match a job against. A roster name is awake but says nothing about
        # what it can take, so it is listed separately rather than mixed in.
        "routable": [
            s for s in (seats.get("seats") or [])
            if (s.get("derived") or {}).get("liveness") in ("LIVE", "QUIET")
        ],
        "awake_undeclared": [
            r for r in (seats.get("roster") or [])
            if r.get("liveness") in ("LIVE", "QUIET")
        ],
    }


def snapshot(root, feed_limit=20):
    """Compose the observability payload. `root` is the repository root."""
    reads = {name: _read(root, rel) for name, rel in SOURCES}
    sources = [
        {k: v for k, v in read.items() if k != "value"}
        for read in reads.values()
    ]
    ok = {name: read["value"] for name, read in reads.items() if read["ok"]}

    payload = {
        "schema": SCHEMA,
        "sources": sorted(sources, key=lambda s: s["path"]),
        "degraded": sorted(s["path"] for s in sources if not s["ok"]),
    }

    pulse = ok.get("pulse")
    payload["pulse"] = {
        "seq": pulse.get("seq"),
        "head": pulse.get("head", ""),
        "ts": pulse.get("ts", ""),
        "post_count": pulse.get("post_count"),
        "feed": pulse.get("feed") or {},
    } if isinstance(pulse, dict) else None

    feed = ok.get("feed")
    payload["board"] = _feed_summary(feed, feed_limit) if isinstance(feed, dict) else None

    seats = ok.get("seats")
    payload["seats"] = _seats_summary(seats) if isinstance(seats, dict) else None

    # A single line an owner can read without opening anything.
    if payload["seats"] and payload["board"]:
        live = payload["seats"]["by_liveness"].get("LIVE", 0)
        quiet = payload["seats"]["by_liveness"].get("QUIET", 0)
        payload["headline"] = (
            "%d live, %d quiet, %d events in the delta shard, %d priced unblocks"
            % (live, quiet, payload["board"]["count"],
               len(payload["seats"]["priced_unblocks"]))
        )
    else:
        payload["headline"] = (
            "Partial: could not read %s" % ", ".join(payload["degraded"])
            if payload["degraded"] else "Partial"
        )
    return payload


if __name__ == "__main__":
    import argparse

    here = os.path.dirname(os.path.abspath(__file__))
    default_root = os.path.dirname(os.path.dirname(here))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=default_root)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--headline", action="store_true")
    args = ap.parse_args()
    out = snapshot(args.root, args.limit)
    print(out["headline"] if args.headline else json.dumps(out, indent=2))
