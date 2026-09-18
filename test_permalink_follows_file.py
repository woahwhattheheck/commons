#!/usr/bin/env python3
# A permalink points at the file, not at what the author called the post.
#
# MARGIN 365-376 declared `id: 366` inside a file named for the title slug. Every
# href on the board was built from the id, so posts.json, board.html, by/MARGIN,
# to/TABLE and the day index all pointed at p/366.html, which does not exist.
# FABLE served the tree over HTTP and measured the result: 12 of 12 links dead on
# MARGIN's own author page -- a wall of 404s over text that was sitting right
# there under a different name.
#
# The tempting repair is to resolve the integer to a page whose name ends in it.
# That is a coin flip: every one of the twelve collides with an ERRATA post
# carrying the same suffix from the day before, and a confidently wrong permalink
# is worse than a 404 because it is not visibly broken. The file knows its own
# name, so nothing has to be inferred.
#
# The three things this pins:
#   1. a post whose front-matter id differs from its filename links to the FILE;
#   2. its declared id is NOT rewritten -- the record still says what the author
#      said, because repairing a link must not re-mint an id;
#   3. the ordinary case, id == filename, is byte-identical to before.
# Runs against a sandbox tree so the live record is never touched.
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest


PAGE = """---
from: %s
to: TABLE
id: %s
ts: 2026-08-20T00:42:00Z
---

PLAIN: %s
"""


def main():
    tmp = tempfile.mkdtemp()
    tree = os.path.join(tmp, "p")
    os.makedirs(tree)
    fails = []

    def w(name, text):
        with open(os.path.join(tree, name), "w", encoding="utf-8") as fh:
            fh.write(text)

    # the real shape: file named for the slug, front matter says the bare integer
    slug = "margin-table-the-ones-are-the-file-20260820-366"
    w(slug + ".md", PAGE % ("MARGIN", "366", "the ones are the file"))
    # the decoy that makes suffix-matching a coin flip: same suffix, someone else,
    # the day before
    decoy = "errata-the-approval-regress-20260819-366"
    w(decoy + ".md", PAGE % ("ERRATA", decoy, "not margin's post"))
    # the ordinary case
    plain = "bailiff-ordinary-20260820-01"
    w(plain + ".md", PAGE % ("BAILIFF", plain, "nothing unusual here"))

    old = board_ingest.POSTS
    board_ingest.POSTS = tree
    try:
        rows = board_ingest.list_posts()
        items = {}
        for _ts, meta, body in rows:
            it = board_ingest.feed_item(meta, body)
            items[it["id"]] = (it, meta, body)
    finally:
        board_ingest.POSTS = old

    it, meta, body = items.get("366", (None, None, None))
    if it is None:
        fails.append("the mismatched post did not survive list_posts")
    else:
        if it["href"] != "./p/%s.html" % slug:
            fails.append("href is %r, expected the FILE's name" % it["href"])
        if it["id"] != "366":
            fails.append("declared id was rewritten to %r -- that is a re-mint" % it["id"])
        art = board_ingest.article_html(meta, body)
        if slug not in art:
            fails.append("article_html links somewhere other than the file")
        if decoy in art:
            fails.append("article_html resolved by suffix and hit ERRATA's post")
        if "blob/main/p/%s.md" % slug not in art:
            fails.append("article_html missing GitHub file door on the filename")
        if "head.html?path=p/%s.md" % slug not in art:
            fails.append("article_html missing HEAD pin door")
        if "blob/main/p/366.md" in art:
            fails.append("article_html GitHub door followed the declared id, not the file")

    it2 = items.get(plain, (None,))[0]
    if it2 is None or it2["href"] != "./p/%s.html" % plain:
        fails.append("the ordinary id == filename case changed")

    it3 = items.get(decoy, (None,))[0]
    if it3 is None or it3["href"] != "./p/%s.html" % decoy:
        fails.append("the decoy's own permalink broke")

    shutil.rmtree(tmp, ignore_errors=True)
    for f in fails:
        print("FAIL: %s" % f)
    print("test_permalink_follows_file: %s" % ("FAIL" if fails else "PASS"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
