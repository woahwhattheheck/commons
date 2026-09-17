#!/usr/bin/env python3
"""Retained root bridge for the canonical Muse publication-election v2 suites."""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULES = (
    "tools.outbound_send_guard.test_muse_election_v2",
    "tools.outbound_send_guard.test_muse_current_authority_v2",
)
_RAN = re.compile(r"Ran\s+(\d+)\s+tests?\b")


class MuseElectionV2RetainedTests(unittest.TestCase):
    def _run_suite(self, *, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-m", "unittest", "-v", *MODULES])
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=180,
        )
        combined = completed.stdout + "\n" + completed.stderr
        self.assertEqual(
            completed.returncode,
            0,
            f"canonical Muse v2 suite failed ({'optimized' if optimized else 'normal'}):\n{combined}",
        )
        match = _RAN.search(combined)
        self.assertIsNotNone(match, f"unittest did not report an executed test count:\n{combined}")
        self.assertGreater(int(match.group(1)), 0, f"canonical Muse v2 suite executed zero tests:\n{combined}")
        self.assertIn("OK", combined)

    def test_canonical_v2_normal(self) -> None:
        self._run_suite(optimized=False)

    def test_canonical_v2_optimized(self) -> None:
        self._run_suite(optimized=True)


if __name__ == "__main__":
    unittest.main()
