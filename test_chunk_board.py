#!/usr/bin/env python3
"""One check per failure mode for day chunks. Does not fetch. Does not remint."""
from __future__ import annotations

import json
import os
import shutil
import tempfile

import chunk_board


def assert_true(cond, msg):
    if not cond:
        raise SystemExit("FAIL " + msg)
    print("PASS " + msg)


def main() -> int:
    feed = [
        {"id": "new-a", "ts": "2026-08-20T10:00:00Z", "from": "A", "to": "TABLE", "body": "today"},
        {"id": "hid", "ts": "2026-08-20T11:00:00Z", "from": "H", "to": "TABLE", "body": "no", "hidden": "1"},
        {"id": "old-b", "ts": "2026-08-19T10:00:00Z", "from": "B", "to": "TABLE", "body": "yesterday"},
        {"id": "no-ts", "from": "C", "to": "TABLE", "body": "undated"},
    ]
    assert_true(chunk_board.day_of(feed[0]) == "2026-08-20", "day_of uses ts YYYY-MM-DD")
    assert_true(chunk_board.day_of(feed[3]) == "undated", "empty ts is undated")
    days = chunk_board.group_days(feed)
    assert_true("hid" not in [p["id"] for p in days["2026-08-20"]], "hidden rows stay out of chunks")
    assert_true(len(days["2026-08-20"]) == 1 and days["2026-08-20"][0]["id"] == "new-a", "today has the visible row")
    assert_true("2026-08-19" in days and "undated" in days, "groups older and undated")

    tmp = tempfile.mkdtemp(prefix="chunks-")
    try:
        index = chunk_board.write_chunks(feed, tmp)
        assert_true(index["n"] == 3, "index n is visible count")
        assert_true([d["id"] for d in index["days"]] == ["2026-08-20", "2026-08-19", "undated"], "days newest first")
        today = json.load(open(os.path.join(tmp, "chunks", "2026-08-20.json"), encoding="utf-8"))
        assert_true(today[0]["id"] == "new-a", "today json is the post")
        stale = os.path.join(tmp, "chunks", "1999-01-01.json")
        open(stale, "w").write("[]")
        chunk_board.write_chunks(feed, tmp)
        assert_true(not os.path.isfile(stale), "stale day json is removed")
    finally:
        shutil.rmtree(tmp)
    print("CHUNK BOARD TEST: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
