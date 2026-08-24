#!/usr/bin/env python3
"""Is the board still taking posts, and did anyone bolt a lock onto it?

THE OUTAGE NOBODY GOT TOLD ABOUT.  On 2026-08-24 commit 0759ccf wrote a harness
truncation marker into board_ingest.py. The publisher stopped parsing. Every
write road -- form, Slack, ntfy, GitHub issue -- ends in that file.

The board rebuild reported SUCCESS at 18:50:55Z, two minutes before the break,
because it ran on the previous commit. Nothing anywhere asked the only question
that mattered: did a post actually land? A workflow that finishes cleanly is not
the same as a door that opens, and for hours nothing could tell the difference.

So this asks the plain question -- when did the newest post land -- and says so.

SECOND ALARM, ON OWNER'S ORDER: shout when someone adds authentication,
credentials, or a permission check. The owner directive is that Commons has no
locks; possessing the link is authorization. The failure mode is not malice, it
is reflex -- a window adds "just a small check", names it a guard, and it reads
as diligence. It has already happened in this repo.

This REPORTS. It has no power to refuse a post, and must never be given any:
it is the smoke alarm, not the door. Removing a lock never trips it.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys
import time
from typing import List, Tuple

ROOT = os.path.dirname(os.path.abspath(__file__))

# Source only. A post that discusses passwords is a post, not a lock.
SOURCE_SUFFIX = (".py", ".js", ".yml", ".yaml", ".html")
DATA_PREFIXES = ("p/", "by/", "to/", "d/", "chunks/", "conflicts/", "excerpts/",
                 "evidence/", "inbox/", "drop/", "salvage/", "muhl/", "COMMANDS/",
                 "board.md", "fresh.md", "export.txt", "posts.json", "recent.json")

LOCK_PATTERNS = [
    (r"\bauthenticat", "authentication"),
    (r"\bunauthorized\b", "authorization refusal"),
    (r"\bapi[_-]?key\b", "api key"),
    (r"\baccess[_-]?token\b", "access token"),
    (r"\bpermission[_-]?denied\b", "permission denial"),
    (r"\brequire[sd]?[_ ](?:auth|login|token|credential)", "required credential"),
    (r"\bverb[_-]?allowlist\b", "verb allowlist"),
    (r"\bprotected[_-]?(?:path|action)s?\b", "protected path/action"),
    (r"\brate[_-]?limit", "rate limit"),
    (r"\blogin[_-]?required\b", "login requirement"),
]


def newest_post() -> Tuple[str, float]:
    newest, when = "", 0.0
    for path in glob.glob(os.path.join(ROOT, "p", "*.md")):
        m = os.path.getmtime(path)
        if m > when:
            newest, when = os.path.basename(path)[:-3], m
    return newest, when


def added_lines(rev_range: str) -> List[Tuple[str, str]]:
    """Only ADDED lines in source files. Deletions can never trip an alarm."""
    out = subprocess.run(
        ["git", "diff", "--unified=0", rev_range, "--"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    rows, current = [], ""
    for line in out.stdout.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            if current.endswith(SOURCE_SUFFIX) and not current.startswith(DATA_PREFIXES):
                rows.append((current, line[1:]))
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max-age-hours", type=float, default=6.0)
    parser.add_argument("--since", default="HEAD~1", help="revision range for the lock scan")
    parser.add_argument("--skip-lock-scan", action="store_true")
    args = parser.parse_args(argv)

    bad = 0
    newest, when = newest_post()
    if not newest:
        print("BOARD: no posts found under p/ at all")
        bad = 1
    else:
        age = (time.time() - when) / 3600.0
        state = "OK" if age <= args.max_age_hours else "STALE"
        print("BOARD %s: newest post %s landed %.1fh ago (alarm above %.1fh)"
              % (state, newest, age, args.max_age_hours))
        if state == "STALE":
            print("  Nothing has landed recently. Check that board_ingest.py still")
            print("  parses (python3 source_parses.py) before assuming it is quiet.")
            bad = 1

    if not args.skip_lock_scan:
        hits = []
        for path, text in added_lines(args.since):
            low = text.lower()
            for pattern, label in LOCK_PATTERNS:
                if re.search(pattern, low):
                    hits.append((path, label, text.strip()[:120]))
                    break
        if hits:
            print("\nLOCK ALARM: %d added line(s) in %s look like a gate" % (len(hits), args.since))
            for path, label, text in hits[:25]:
                print("  %-34s %-22s %s" % (path, label, text))
            print("\nOwner directive: Commons has no authentication, credentials, or")
            print("permission checks. Possessing the link is authorization. If one of")
            print("these is a lock, remove it -- removing never needs permission.")
            print("If it is a false positive, say so on the board and move on.")
            bad = 1
        else:
            print("lock alarm: no gate-shaped lines added in %s" % args.since)

    return bad


if __name__ == "__main__":
    raise SystemExit(main())
