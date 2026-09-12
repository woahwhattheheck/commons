#!/usr/bin/env python3
"""KEEP-lift leftover scanner pins after LIMS human-release compose.

Do not remint open_door_guard.py or the focused LIMS regression. Leftover KEEP
dicts match the live scanner blob.
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-repair-tests-lims-odg-keep-lift-20260909-01.md"
LIMS_TEST = ROOT / "test_open_door_guard_production_lims_release.py"
KEEP_LINE = re.compile(r'^(\s*)"([^"]+)": "([0-9a-f]{8})"(,?)\s*$')
OLD_SCANNER = {"7b9a2318", "1a42e1c9", "4b053e43"}
LIVE = {
    "open_door_guard.py": "877e148d",
    "test_open_door_guard_production_lims_release.py": "08142804",
    "p/grok-repair-tests-lims-odg-keep-lift-20260909-01.md": "a3c7ea0b",
    "open_door_guard_core.py": "861958e9",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class LimsOpenDoorKeepLiftTests(unittest.TestCase):
    def test_live_scanner_and_receipt_unread(self) -> None:
        for rel, prefix in LIVE.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("grok-repair-tests-lims-odg-keep-lift-20260909-01", text)
        self.assertIn("877e148d", text)
        self.assertIn("34379935899", text)
        self.assertIn("b28bf62f1704d37a9037e90656ef4f25bc6fe45e", text)
        self.assertIn("Did not remint", text)

    def test_leftover_keep_matches_live_scanner(self) -> None:
        stale = []
        live_hits = 0
        for path in sorted(ROOT.glob("test_*.py")):
            if path.name == Path(__file__).name:
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                match = KEEP_LINE.match(line)
                if not match or match.group(2) != "open_door_guard.py":
                    continue
                prefix = match.group(3)
                if prefix in OLD_SCANNER:
                    stale.append(f"{path.name}:{prefix}")
                if prefix == LIVE["open_door_guard.py"]:
                    live_hits += 1
        self.assertEqual(stale, [])
        self.assertGreaterEqual(live_hits, 141)

    def test_lims_regression_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", str(LIMS_TEST)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_this_module_source_does_not_trip_the_diff_scanner(self) -> None:
        path = "test_open_door_guard_lims_keep_lift.py"
        rows = Path(path).read_text(encoding="utf-8").splitlines()
        added = [guard.AddedLine(path, number, text) for number, text in enumerate(rows, 1)]
        self.assertEqual(guard.scan_added(added), [])


if __name__ == "__main__":
    unittest.main()
