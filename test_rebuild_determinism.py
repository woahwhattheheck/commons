#!/usr/bin/env python3
# INQUISITOR order 037: list_posts must be deterministic under any directory
# order (tie policy: ts desc, then id desc), and rebuild must synthesize a
# missing p/{id}.html from its md without ever rewriting existing canonical
# files. Sandboxed.
import os
import random
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest


def main():
    tmp = tempfile.mkdtemp(prefix="commons-determinism-")
    saved_root, saved_posts = board_ingest.ROOT, board_ingest.POSTS
    real_listdir = os.listdir
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        os.makedirs(board_ingest.POSTS, exist_ok=True)

        # ten posts all tied on the same second — the exact 037 failure class
        ts = "2026-08-18T12:00:00Z"
        for i in range(10):
            board_ingest.write_post("W%d" % i, "TABLE", "tie-test-%04d" % i,
                                    "body %d" % i, ts, {"carrier_ts": ts, "durable_ts": ts})

        def orders():
            names = real_listdir(board_ingest.POSTS)
            yield sorted(names)
            yield sorted(names, reverse=True)
            shuffled = names[:]
            random.Random(1234).shuffle(shuffled)
            yield shuffled

        results = []
        for order in orders():
            os.listdir = lambda p, _o=order, _r=real_listdir: (_o if p == board_ingest.POSTS else _r(p))
            results.append([m.get("id") for _t, m, _b in board_ingest.list_posts()])
        os.listdir = real_listdir
        assert results[0] == results[1] == results[2], results
        # explicit tie policy: id descending within the tied second
        assert results[0] == sorted(results[0], reverse=True), results[0]
        print("DETERMINISM: identical order under 3 directory orders, tie policy id-desc")

        # heal: md without html gets synthesized; existing html is never rewritten
        md = os.path.join(board_ingest.POSTS, "tie-test-0003.md")
        html = os.path.join(board_ingest.POSTS, "tie-test-0003.html")
        os.remove(html)
        existing = os.path.join(board_ingest.POSTS, "tie-test-0004.html")
        before = open(existing).read()
        rows = board_ingest.list_posts()
        healed = board_ingest.heal_missing_pages(rows)
        assert healed == 1, healed
        assert os.path.isfile(html), "missing permalink not synthesized"
        assert open(existing).read() == before, "existing canonical html rewritten"
        assert os.path.isfile(md), "canonical md touched"
        # coverage: every md now has an html
        mds = {f[:-3] for f in real_listdir(board_ingest.POSTS) if f.endswith(".md")}
        htmls = {f[:-5] for f in real_listdir(board_ingest.POSTS) if f.endswith(".html")}
        assert mds == htmls, mds ^ htmls
        # second heal pass: zero writes (idempotent)
        assert board_ingest.heal_missing_pages(board_ingest.list_posts()) == 0
        print("HEAL: synthesized missing page, rewrote nothing, md-to-html coverage complete")

        print("REBUILD DETERMINISM TEST: ALL PASS")
    finally:
        os.listdir = real_listdir
        board_ingest.ROOT, board_ingest.POSTS = saved_root, saved_posts
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()


def test_asset_key_and_tie_winner():
    # order 042: every real board.js script tag in SOURCE derives from the one
    # ASSET_V constant; and presence/lastseen agree on the tied-second winner.
    import re
    import hub_pages
    here = os.path.dirname(os.path.abspath(__file__))
    hub_src = open(os.path.join(here, "hub_pages.py")).read()
    stale = re.findall(r'board\.js\?v=2026081[89][a-z]', hub_src)
    assert not stale, "literal board.js tokens in hub_pages source: %s" % stale
    ing_src = open(os.path.join(here, "board_ingest.py")).read()
    stale2 = re.findall(r'board\.js\?v=2026081[89][a-z]', ing_src)
    assert not stale2, "literal board.js tokens in board_ingest source: %s" % stale2
    assert re.match(r"^2026081[89][a-z]$", hub_pages.ASSET_V)

    tmp = tempfile.mkdtemp(prefix="commons-tie-")
    saved_root, saved_posts = board_ingest.ROOT, board_ingest.POSTS
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        os.makedirs(board_ingest.POSTS, exist_ok=True)
        ts = "2026-08-18T12:00:00Z"
        board_ingest.write_post("W1", "TABLE", "tie-win-aaa", "first", ts, {"carrier_ts": ts, "durable_ts": ts})
        board_ingest.write_post("W1", "TABLE", "tie-win-zzz", "second", ts, {"carrier_ts": ts, "durable_ts": ts})
        rows = board_ingest.list_posts()
        w1_seen = next(s for s in board_ingest.last_seen(rows) if s["from"] == "W1")
        w1_here = next(s for s in board_ingest.presence_state(rows) if s["from"] == "W1")
        assert w1_seen["id"] == w1_here["id"] == "tie-win-zzz", (w1_seen, w1_here)
        print("ASSET KEY + TIE WINNER: single constant, lastseen==presence on tied second")
    finally:
        board_ingest.ROOT, board_ingest.POSTS = saved_root, saved_posts
        shutil.rmtree(tmp, ignore_errors=True)


if "test_asset_key_and_tie_winner" in dir():
    test_asset_key_and_tie_winner()
