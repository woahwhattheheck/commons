#!/usr/bin/env python3
"""Add the phone-fit tag to post pages that were generated without it.

A page with <meta charset> but no <meta name="viewport"> is laid out by a phone
at ~980 CSS px and then scaled down: unreadable text, taps landing off-target.
It is invisible from a desktop browser, which is why it survived.

Measured 2026-08-24: 4,933 pages under p/, 3,305 with no viewport tag. They were
written by an older generation of the post template; the current one emits it,
which is why the newest page looks fine and why viewport_check.py -- which
sampled only the newest -- reported the board clean for as long as it did.

This repairs the pages that already exist. It does NOT fix the generator: the
post-page head literal lives in board_ingest.py, which does not parse on main
right now (0759ccf, U+2026 at line 1450) and is being repaired by another
window. Once that lands, the generator needs the same one-line addition or a
full rebuild will undo every page this touched.

Idempotent, and re-runnable after any rebuild. Insert point is immediately after
<meta charset>, matching the current template's ordering.
"""

from __future__ import annotations

import argparse
import glob
import sys

NEEDLE = 'name="viewport"'
TAG = '<meta name="viewport" content="width=device-width, initial-scale=1">'
ANCHOR = '<meta charset="utf-8">'


def repair(text: str) -> str | None:
    """Return repaired text, or None when nothing should change."""
    if NEEDLE in text:
        return None
    if not text.lstrip().startswith("<"):
        # r/*.html are plain-text receipts wearing an .html suffix. A meta tag in
        # one of those is corruption, not a fix.
        return None
    if ANCHOR not in text:
        return None
    return text.replace(ANCHOR, ANCHOR + "\n" + TAG, 1)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="apply (default is a dry run)")
    parser.add_argument("--glob", default="p/*.html")
    args = parser.parse_args(argv)

    changed = skipped = 0
    for path in sorted(glob.glob(args.glob)):
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            continue
        fixed = repair(text)
        if fixed is None:
            skipped += 1
            continue
        changed += 1
        if args.write:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(fixed)

    verb = "repaired" if args.write else "would repair"
    print("%s %d pages, left %d alone (%s)" % (verb, changed, skipped, args.glob))
    if not args.write and changed:
        print("dry run -- pass --write to apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
