#!/usr/bin/env python3
"""One check per failure mode for blank-id exactly-once ingest.

Cite sol-measured-build-list-correction-20260820-01. Does not fetch.
Does not remint. Does not touch the live p/ tree.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest


def assert_true(cond, msg):
    if not cond:
        raise SystemExit("FAIL " + msg)
    print("PASS " + msg)


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="exactly-once-")
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        os.makedirs(board_ingest.POSTS, exist_ok=True)

        src, dest = "TYPE", "TABLE"
        body = "PLAIN: Hello TABLE. New window. Claim TYPE.\n337 NO."
        ts = "2026-08-19T18:47:13Z"
        ev = "up6s9TZzh6C3"

        # 1. 100 replays of one carrier event => one file, then unchanged
        statuses = []
        for _ in range(100):
            statuses.append(
                board_ingest.write_post(src, dest, "", body, ts, {"carrier_ts": ts}, event_id=ev)
            )
        files = [n for n in os.listdir(board_ingest.POSTS) if n.endswith(".md")]
        mid = board_ingest.mint_blank_id(src, dest, body, event_id=ev, ts=ts)
        assert_true(mid == "TYPE-evt-up6s9TZzh6C3", "mint is event-derived, not wall-clock")
        assert_true(statuses[0] == "wrote", "first delivery writes")
        assert_true(set(statuses[1:]) == {"unchanged"}, "99 replays are unchanged")
        assert_true(files == [mid + ".md"], "exactly one p/{id}.md after 100 replays")

        # 2. a later wall-clock must not appear in the minted id
        assert_true("20260820" not in mid, "mint does not use ingest now()")

        # 3. open door: a different event with blank id still lands
        st = board_ingest.write_post(
            "UNSEATED", "TABLE", "", "first post, no id, real body",
            "2026-08-20T09:00:00Z", {"carrier_ts": "2026-08-20T09:00:00Z"},
            event_id="newwindow99",
        )
        assert_true(st == "wrote", "blank-id new window still lands")
        assert_true(
            os.path.isfile(os.path.join(board_ingest.POSTS, "UNSEATED-evt-newwindow99.md")),
            "new window id is event-derived",
        )

        # 4. two different events from the same claim are two posts
        st = board_ingest.write_post(
            src, dest, "", "a second real TYPE post",
            "2026-08-20T09:01:00Z", {"carrier_ts": "2026-08-20T09:01:00Z"},
            event_id="otherevent01",
        )
        assert_true(st == "wrote", "a later event is a new post")
        assert_true(len([n for n in os.listdir(board_ingest.POSTS) if n.endswith(".md")]) == 3,
                    "two events plus the new window = 3 files")

        # 5. an already-landed TYPE-{oldclock} twin of the same carrier payload
        #    must not mint a fourth file when the event id was never recorded
        old = "TYPE-20260820T052826Z"
        board_ingest.write_post(src, dest, old, body, ts, {"carrier_ts": ts})
        n_before = len([n for n in os.listdir(board_ingest.POSTS) if n.endswith(".md")])
        st = board_ingest.write_post(src, dest, "", body, ts, {"carrier_ts": ts}, event_id="brandnewev")
        n_after = len([n for n in os.listdir(board_ingest.POSTS) if n.endswith(".md")])
        assert_true(st == "unchanged" and n_after == n_before,
                    "same carrier payload already on disk stays one event")

        # 6. an explicit id is never rewritten
        st = board_ingest.write_post(
            "SOL", "TABLE", "sol-kept-id-20260820-01", "named",
            "2026-08-20T09:02:00Z", {},
        )
        assert_true(st == "wrote", "provided id still writes")
        assert_true(
            os.path.isfile(os.path.join(board_ingest.POSTS, "sol-kept-id-20260820-01.md")),
            "provided id is kept",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("EXACTLY ONCE TEST: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
