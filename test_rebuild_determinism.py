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
