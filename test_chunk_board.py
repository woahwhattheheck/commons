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

        day_html = chunk_board.render_thin_day_html(
            "2026-08-20",
            80,
            [chunk_board.seed_article(p, prefix="../") for p in days["2026-08-20"]],
            '<link href="../commons.css">',
            "<nav></nav>",
            '<script src="../board.js"></script>',
            seed=24,
        )
        assert_true('data-day="2026-08-20"' in day_html, "thin day sets data-day")
        assert_true('data-limit="24"' in day_html, "thin day sets data-limit 24")
        assert_true('data-chunks="1"' in day_html, "thin day sets data-chunks")
        assert_true("data-endless" not in day_html, "thin day is not endless")
        assert_true("../board.js" in day_html, "thin day loads board.js from site root")
        assert_true("../p/new-a.html" in day_html, "thin day p/ links go up one level")
        assert_true(day_html.count("<article") == 1, "thin day bakes only the day's seed")
        assert_true("chunks/2026-08-20.json" in day_html, "thin day points at that day's chunk")
    finally:
        shutil.rmtree(tmp)

    many = [
        {
            "id": "p-%02d-20260819-01" % i,
            "ts": "2026-08-19T10:%02d:00Z" % (i % 60),
            "from": "A",
            "to": "TABLE",
            "body": "x" * 40,
        }
        for i in range(80)
    ]
    fat_articles = [chunk_board.seed_article(p, prefix="../") for p in many]
    thin = chunk_board.render_thin_day_html(
        "2026-08-19",
        80,
        fat_articles,
        "<style></style>",
        "<nav></nav>",
        "<script></script>",
        seed=24,
    )
    assert_true(thin.count("<article") == 24, "day page bakes 24 of 80")
    assert_true("56 more this day" in thin, "day page names the remainder")

    import hub_pages

    class FakeMod:
        def __init__(self, root):
            self.ROOT = root
            self.CSS = '<link href="./commons.css"><script src="./session.js"></script>'

        def doors(self, parent=False):
            return "<nav>doors</nav>"

        def article_html(self, meta, body, prefix="./"):
            return '<article data-id="%s"><a href="%sp/%s.html">%s</a></article>' % (
                meta["id"], prefix, meta["id"], meta["id"]
            )

        def _write(self, path, text):
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            if not text.endswith("\n"):
                text += "\n"
            open(path, "w", encoding="utf-8").write(text)

    tmp2 = tempfile.mkdtemp(prefix="days-")
    try:
        rows = []
        for i in range(30):
            mid = "arc-%02d-20260818-01" % i
            rows.append((
                "2026-08-18T12:%02d:00Z" % i,
                {"id": mid, "from": "A", "to": "TABLE"},
                "body",
            ))
        rows.append(("2026-08-20T01:00:00Z", {"id": "today-thin-20260820-01", "from": "B", "to": "TABLE"}, "t"))
        hub_pages.rebuild_archive(FakeMod(tmp2), rows)
        day = open(os.path.join(tmp2, "d", "2026-08-18.html"), encoding="utf-8").read()
        assert_true(day.count("<article") == 24, "rebuild_archive bakes 24 of a 30-post day")
        assert_true('data-day="2026-08-18"' in day, "rebuild_archive sets data-day")
        assert_true("../board.js" in day, "rebuild_archive loads board.js with parent prefix")
        assert_true(os.path.isfile(os.path.join(tmp2, "archive.html")), "archive index still written")
    finally:
        shutil.rmtree(tmp2)
    print("CHUNK BOARD TEST: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
