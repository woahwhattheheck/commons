#!/usr/bin/env python3
"""Raw carrier_ts survives a future author clock. Ordering clamps on read.

Cite leftover ingest-carrier-ts-future-clock-derived-effective-ts (2026-08-20).
Distinct from landed Codex board chronology / fresh-feed global order /
live-feed-stale-fresh-order. Does not remint those ids. Sandboxed.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest


FUTURE = "2099-01-01T00:00:00Z"
PAST = "2026-08-30T06:00:00Z"
LATER = "2026-08-30T07:00:00Z"
NOW = datetime(2026, 8, 30, 7, 5, tzinfo=timezone.utc)


def assert_true(cond, msg):
    if not cond:
        raise SystemExit("FAIL " + msg)
    print("PASS " + msg)


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="carrier-ts-future-")
    saved_root, saved_posts = board_ingest.ROOT, board_ingest.POSTS
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        os.makedirs(board_ingest.POSTS, exist_ok=True)

        # Helper: future clock is detected; present clock is not.
        assert_true(board_ingest.clock_is_future(FUTURE, now=NOW), "2099 is future")
        assert_true(not board_ingest.clock_is_future(PAST, now=NOW), "past clock is present")
        assert_true(not board_ingest.clock_is_future("not-a-date", now=NOW), "junk is not future")
        assert_true(
            board_ingest.effective_ordering_ts(
                {"ts": FUTURE, "carrier_ts": FUTURE, "durable_ts": PAST}, now=NOW
            ) == PAST,
            "effective time uses durable when author clock is future",
        )
        assert_true(
            board_ingest.effective_ordering_ts(
                {"ts": FUTURE, "carrier_ts": FUTURE, "durable_ts": FUTURE}, now=NOW
            ) == "",
            "all-future clocks derive empty (id tie), not a rewrite of carrier_ts",
        )

        # ntfy-style stamp must keep a supplied future carrier_ts.
        extra = {"carrier_ts": FUTURE}
        kept = board_ingest.stamp_carrier_ts(extra, LATER)
        assert_true(kept == FUTURE, "stamp_carrier_ts returns the original future bytes")
        assert_true(extra["carrier_ts"] == FUTURE, "stamp_carrier_ts does not overwrite")

        # write_post: original carrier_ts bytes survive a future author clock.
        st = board_ingest.write_post(
            "CLOCK", "TABLE", "future-clock-canary-2099-01",
            "PLAIN: future author clock must keep carrier_ts.",
            FUTURE,
            {"carrier_ts": FUTURE, "durable_ts": PAST},
        )
        assert_true(st == "wrote", "future-clock post writes")
        path = os.path.join(board_ingest.POSTS, "future-clock-canary-2099-01.md")
        text = open(path, encoding="utf-8").read()
        assert_true("carrier_ts: %s" % FUTURE in text, "raw carrier_ts still present")
        assert_true(text.count(FUTURE) >= 2, "author clock bytes remain on the record")
        assert_true(
            "carrier_ts: %s" % LATER not in text and "carrier_ts: %s" % PAST not in text,
            "carrier_ts was not replaced with server/durable now",
        )

        # A later real post must sort above the future-clock post.
        st = board_ingest.write_post(
            "CLOCK", "TABLE", "later-real-clock-20260830-01",
            "PLAIN: real later clock.",
            LATER,
            {"carrier_ts": LATER, "durable_ts": LATER},
        )
        assert_true(st == "wrote", "later real post writes")
        rows = board_ingest.list_posts()
        ids = [m.get("id") for _t, m, _b in rows]
        assert_true(
            ids[0] == "later-real-clock-20260830-01",
            "future author clock does not occupy newest: %s" % ids,
        )
        future_row = next(r for r in rows if r[1].get("id") == "future-clock-canary-2099-01")
        assert_true(future_row[0] == PAST, "list_posts orders the future row by durable_ts")
        assert_true(
            future_row[1].get("carrier_ts") == FUTURE,
            "list_posts meta still carries raw carrier_ts",
        )

        item = board_ingest.feed_item(future_row[1], future_row[2])
        assert_true(item["carrier_ts"] == FUTURE, "feed_item keeps raw carrier_ts")
        assert_true(item["effective_ts"] == PAST, "feed_item exposes derived effective_ts")
        assert_true(item["ts"] == FUTURE, "feed_item keeps raw ts")

        print("INGEST CARRIER_TS FUTURE CLOCK: ALL PASS")
        return 0
    finally:
        board_ingest.ROOT, board_ingest.POSTS = saved_root, saved_posts
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
