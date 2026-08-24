#!/usr/bin/env python3
"""Run the whole battery once, in parallel, and say what is new.

Three problems this replaces.

ONE RUNNER.  There are 89 test files, each with its own `unittest.main()`, and
CI loops them in bash.  One exit code, one summary, one place to add a flag.

PARALLEL.  Serial the battery is ~92s wall and two files are half of it
(test_independent_commons_mcp ~24s, test_head_fresh.js ~20s).  They are
independent processes, so run them at once.

NEW RED VS OLD RED.  This is the one that actually cost something.  On
2026-08-24 the publisher landed on main unparseable and 25 test files started
failing on `import board_ingest`.  Nobody noticed for hours -- not because the
battery was quiet, but because it had ALREADY been red since run #336 that
morning for unrelated reasons.  Receipts kept saying "the battery's only
failure is the pre-existing owner-hash thing", which is knowledge that lived in
Slack prose and therefore did not exist.

known_red.json holds that knowledge instead, and every entry carries an expiry
date, because a permanent exception is just a deleted test with extra steps.
An expected failure is reported and does not fail the run.  Anything else does.
An entry that passes, or is past its date, is reported too -- a stale exception
hides the next real break exactly like the old floor did.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.abspath(__file__))
KNOWN_RED = os.path.join(ROOT, "known_red.json")


def discover() -> List[str]:
    """Glob, never a list.

    tests.yml learned this the hard way: a hand-maintained list of filenames
    drifted three times in one evening, so CI ran 16, 17, 18 tests while 17, 18,
    19 sat on disk.  The window that writes a test is the least likely to notice
    it never ran.
    """
    names = [n for n in os.listdir(ROOT) if n.startswith("test_") and n.endswith((".py", ".js"))]
    return sorted(names)


def load_known_red() -> Dict[str, dict]:
    try:
        with open(KNOWN_RED, encoding="utf-8") as handle:
            return {row["test"]: row for row in json.load(handle)["expected_failures"]}
    except (OSError, ValueError, KeyError):
        return {}


def run_one(name: str, timeout: int) -> Tuple[str, bool, int, str]:
    if name.endswith(".js"):
        if not shutil.which("node"):
            return (name, True, 0, "node absent; skipped")
        cmd = ["node", name]
    else:
        cmd = [sys.executable, name]
    start = time.time()
    try:
        done = subprocess.run(
            cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout
        )
        ok, out = done.returncode == 0, (done.stdout or "") + (done.stderr or "")
    except subprocess.TimeoutExpired:
        ok, out = False, "TIMEOUT after %ss" % timeout
    return (name, ok, int((time.time() - start) * 1000), out.strip()[-1400:])


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=int, default=min(8, (os.cpu_count() or 2)))
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--only", help="substring filter")
    parser.add_argument("--slow", type=int, default=5000, help="ms before a test is called slow")
    args = parser.parse_args(argv)

    tests = [t for t in discover() if not args.only or args.only in t]
    known = load_known_red()
    today = datetime.date.today().isoformat()

    started = time.time()
    results: List[Tuple[str, bool, int, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for row in pool.map(lambda t: run_one(t, args.timeout), tests):
            results.append(row)
    wall = time.time() - started

    new_red, expected_red, stale, passed = [], [], [], []
    for name, ok, ms, out in results:
        entry = known.get(name)
        if ok:
            passed.append((name, ms))
            if entry:
                stale.append((name, "now PASSES -- remove it from known_red.json"))
        elif entry and entry.get("until", "") >= today:
            expected_red.append((name, ms, entry))
        elif entry:
            expected_red.append((name, ms, entry))
            stale.append((name, "exception EXPIRED %s -- fix it or re-date it" % entry.get("until")))
        else:
            new_red.append((name, ms, out))

    print("=" * 72)
    print("battery: %d files, %d passed, %d expected-red, %d NEW RED  (%.1fs wall, %d jobs)"
          % (len(results), len(passed), len(expected_red), len(new_red), wall, args.jobs))
    print("=" * 72)

    slow = sorted([r for r in results if r[2] >= args.slow], key=lambda r: -r[2])
    if slow:
        print("\nslow (>= %dms):" % args.slow)
        for name, _ok, ms, _o in slow:
            print("  %6dms  %s" % (ms, name))

    if expected_red:
        print("\nexpected red (known_red.json):")
        for name, ms, entry in expected_red:
            print("  %-42s until %s  %s" % (name, entry.get("until", "?"), entry.get("why", "")))

    if stale:
        print("\nSTALE EXCEPTIONS -- these hide the next real break:")
        for name, why in stale:
            print("  %-42s %s" % (name, why))

    if new_red:
        print("\nNEW RED -- not expected by known_red.json:")
        for name, ms, out in new_red:
            print("\n--- %s (%dms)" % (name, ms))
            for line in out.splitlines()[-12:]:
                print("    %s" % line)

    if new_red:
        return 1
    if stale:
        # A stale exception is a real failure of the mechanism even when every
        # test passes: it is how the old floor-of-21 rotted into uselessness.
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
