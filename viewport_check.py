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
    # p/ used to be sampled here: only the NEWEST post page was checked, on the
    # assumption that all of them share one head from board_ingest.py. That
    # assumption was false and the sampling hid the exact bug this file exists to
    # find. Measured 2026-08-24: 4,933 post pages, 3,305 with no viewport at all.
    # The newest one has the tag -- every sampled run came back clean while two
    # thirds of the board was unreadable on a phone.
    #
    # The original worry was real though: 3,305 identical lines buries the answer.
    # So check all of them and SUMMARISE p/ as a count, naming a couple of
    # examples. Nothing is skipped, and nothing is drowned.
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
    posts_bad = [p for p in bad if p.startswith("p/")]
    other_bad = [p for p in bad if not p.startswith("p/")]
    for p in other_bad:
        print("NO VIEWPORT: %s" % p)
    if posts_bad:
        print("NO VIEWPORT: %d post pages under p/, e.g. %s"
              % (len(posts_bad), ", ".join(posts_bad[:3])))
        print("             run: python3 viewport_backfill.py --write")
    print("%d pages checked, %d missing viewport" % (ok + len(bad), len(bad)))
    if bad:
        print("Generated pages need the fix in the generator, not the file: "
              "hub_pages.VIEWPORT is the constant, and board_ingest.py / "
              "builds_ledger.py carry their own head literals.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
