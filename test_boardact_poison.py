#!/usr/bin/env python3
# Claude's two jobs: boards.html cache must not freeze on a future stamp,
# and ingest must clamp carrier_ts / normalize from= casing.
# Cite claude-table-boards-stale-cache-poison-20260820-01. Do not remint.
# Do not touch board.js.
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest
import hub_pages


FAILED = []


def check(name, got, want=True):
    if got != want:
        FAILED.append("%s: got %r, want %r" % (name, got, want))


def main():
    now = "2026-08-20T21:34:00Z"
    check(
        "clamp future carrier",
        board_ingest.clamp_ts("2026-08-20T22:17:00Z", now),
        now,
    )
    check(
        "keep past carrier",
        board_ingest.clamp_ts("2026-08-20T21:32:00Z", now),
        "2026-08-20T21:32:00Z",
    )
    check(
        "keep empty",
        board_ingest.clamp_ts("", now),
        "",
    )
    slack_ok = "2026-08-20T21:35:30Z"  # 90s ahead, inside 120s slack
    check(
        "keep inside slack",
        board_ingest.clamp_ts(slack_ok, now),
        slack_ok,
    )

    tmp = tempfile.mkdtemp(prefix="commons-boardact-")
    saved = (board_ingest.ROOT, board_ingest.POSTS)
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        os.makedirs(board_ingest.POSTS, exist_ok=True)
        future = "2099-01-01T00:00:00Z"
        st = board_ingest.write_post(
            "margin",
            "TABLE",
            "clamp-future-ts-test-01",
            "future stamp must not land",
            future,
            {"carrier_ts": future},
        )
        check("write_post landed", st, "wrote")
        meta, _body = board_ingest.parse_post(
            board_ingest._read(os.path.join(board_ingest.POSTS, "clamp-future-ts-test-01.md"))
        )
        check("from uppercased", meta.get("from"), "MARGIN")
        check("ts not future", meta.get("ts", "").startswith("2099"), False)
        check("carrier not future", str(meta.get("carrier_ts") or "").startswith("2099"), False)
    finally:
        board_ingest.ROOT, board_ingest.POSTS = saved

    item = board_ingest.feed_item({"from": "margin", "to": "table", "id": "x-from-case-01", "ts": "2026-08-20T21:00:00Z"}, "hi")
    check("feed from upper", item.get("from"), "MARGIN")
    check("feed to upper", item.get("to"), "TABLE")

    hub = open(os.path.join(os.path.dirname(__file__), "hub_pages.py"), encoding="utf-8").read()
    baked = open(os.path.join(os.path.dirname(__file__), "boards.html"), encoding="utf-8").read()
    for label, text in (("hub_pages", hub), ("boards.html", baked)):
        check(label + " v2 key", 'KEY="commons-boardact-v2"' in text)
        check(label + " realTs", "function realTs" in text)
        check(label + " prune", "function prune" in text)
        check(label + " no ts filter", "x.ts||\"\")>before" not in text)
        check(label + " no v1", "commons-boardact-v1" not in text)
        check(label + " cite claude", "claude-table-boards-stale-cache-poison-20260820-01" in text)
        check(label + " leave board.js", "Do not touch board.js" in text)

    start = hub.find("BOARDS_ACTIVITY_JS = ")
    check("hub has activity js", start > 0)
    if start > 0:
        blob = hub_pages.BOARDS_ACTIVITY_JS
        fd, path = tempfile.mkstemp(suffix=".js")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(blob.replace("<script>", "").replace("</script>", ""))
            r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
            check("node --check activity js", r.returncode, 0)
            if r.returncode != 0:
                FAILED.append("node: " + (r.stderr or r.stdout))
        finally:
            os.unlink(path)

    if FAILED:
        print("FAIL")
        for row in FAILED:
            print(" ", row)
        return 1
    print("ok   boardact poison: clamp + v2 script")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
