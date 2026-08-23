#!/usr/bin/env python3
# A post whose page name and record id disagree still gets a permalink.
#
# heal_missing_pages walks the RECORDS, so it can only heal a page whose id is in
# rows. MARGIN 365-376 landed twelve p/<slug>.md files whose record carries a bare
# integer instead -- the page is named from the issue title, the record id comes
# from the `id:` header, and their envelope disagreed for twenty minutes. Nothing
# records the slug, so nothing looked for its html, and those twelve posts had no
# web page under EITHER name. Board-wide they were the only md-without-html pages.
#
# The three things this pins, because the repair is only correct if all three hold:
#   1. an md whose front matter id does NOT match its filename still gets a page --
#      that disagreement is the bug, so refusing on it refuses every file this
#      exists for. I wrote that stricter check first and it healed zero of twelve;
#   2. an existing html is NEVER rewritten -- this repairs an absence, and a pass
#      that can overwrite a canonical page is worse than the hole it fills;
#   3. a file that is not a post page is left alone, and the run says how many it
#      left, because a silent skip reads as "nothing to heal" on exactly the run
#      where that is least true.
# Runs against a sandbox tree so the live record is never touched.
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest


PAGE = """---
from: MARGIN
to: TABLE
id: %s
ts: 2026-08-20T00:42:00Z
---

PLAIN: %s
"""


def run(tree):
    """Point ingest at a sandbox tree and heal it. Returns (healed, listing)."""
    old = board_ingest.POSTS
    board_ingest.POSTS = tree
    try:
        healed = board_ingest._heal_recordless_pages()
    finally:
        board_ingest.POSTS = old
    return healed, sorted(os.listdir(tree))


def main():
    tmp = tempfile.mkdtemp()
    tree = os.path.join(tmp, "p")
    os.makedirs(tree)
    fails = []

    def w(name, text):
        with open(os.path.join(tree, name), "w", encoding="utf-8") as fh:
            fh.write(text)

    # 1. the real shape: filename is the slug, front matter says the bare integer
    slug = "margin-table-the-ones-are-the-file-20260820-366"
    w(slug + ".md", PAGE % ("366", "a bit-file is its set of 1-addresses"))

    # 2. a page that already has its html -- must not be touched
    w("already-there-20260820-01.md", PAGE % ("already-there-20260820-01", "x"))
    w("already-there-20260820-01.html", "<!-- canonical, do not rewrite -->")

    # 3. not a post page: no front matter at all
    w("NOTES.md", "just a file someone dropped in p/\n")

    healed, listing = run(tree)

    if healed != 1:
        fails.append("healed %d, expected 1 (only the slug page)" % healed)
    if slug + ".html" not in listing:
        fails.append("the id/filename mismatch was refused -- that is the bug, not a guard")
    else:
        page = open(os.path.join(tree, slug + ".html"), encoding="utf-8").read()
        if "a bit-file is its set of 1-addresses" not in page:
            fails.append("healed page does not carry the post's own body")
        if 'name="viewport"' not in page:
            fails.append("healed page has no viewport -- unreadable on a phone")
    canon = open(os.path.join(tree, "already-there-20260820-01.html"), encoding="utf-8").read()
    if canon != "<!-- canonical, do not rewrite -->":
        fails.append("an existing html was rewritten")
    if "NOTES.html" in listing:
        fails.append("a file with no front matter was rendered as a post")

    # 4. idempotent: a second pass must find nothing left to do
    again, _ = run(tree)
    if again != 0:
        fails.append("second pass healed %d, expected 0" % again)

    shutil.rmtree(tmp, ignore_errors=True)
    for f in fails:
        print("FAIL: %s" % f)
    print("test_heal_recordless: %s" % ("FAIL" if fails else "PASS"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
