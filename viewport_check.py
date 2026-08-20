#!/usr/bin/env python3
"""List pages a phone cannot read.

BRYCE-1787154890706-5t8imm and the complaints around it were about the site being
unusable on his phone. The cause was mundane: a page with <meta charset> but no
<meta name="viewport"> renders at a 980px desktop width and gets scaled down, so the
text is unreadable and taps land in the wrong place. It is invisible from a desktop
browser, which is why it survived so long and why it keeps coming back -- every new
page copies a head from an older one, and some of those heads never had it.

This makes it checkable instead of discoverable-by-squinting. Exit 1 if any page is
missing it, so it can gate something later without being rewritten.

Run: python3 viewport_check.py
"""
import glob
import os
import sys

NEEDLE = 'name="viewport"'


def main():
    bad, ok = [], 0
    pages = sorted(glob.glob("*.html") + glob.glob("*/*.html"))
    # p/ is 3,000+ generated post pages sharing one head from board_ingest.py.
    # Listing them all would bury the real answer under identical lines, so check
    # the newest one as the representative -- it still catches a generator that
    # stops emitting the tag.
    posts = [x for x in pages if x.startswith("p/")]
    if posts:
        keep = max(posts, key=lambda f: os.path.getmtime(f))
        pages = [x for x in pages if not x.startswith("p/") or x == keep]
    for path in pages:
        try:
            text = open(path, encoding="utf-8", errors="replace").read(4096)
        except OSError:
            continue
        # r/*.html are plain-text receipts that happen to carry an .html suffix --
        # they start with "RECEIPT", not "<". A viewport meta in one of those would
        # be corruption, not a fix, so anything that is not a document is skipped.
        if not text.lstrip()[:1] == "<":
            continue
        if NEEDLE in text:
            ok += 1
        else:
            bad.append(path)
    for p in bad:
        print("NO VIEWPORT: %s" % p)
    print("%d pages checked, %d missing viewport" % (ok + len(bad), len(bad)))
    if bad:
        print("Generated pages need the fix in the generator, not the file: "
              "hub_pages.VIEWPORT is the constant, and board_ingest.py / "
              "builds_ledger.py carry their own head literals.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
