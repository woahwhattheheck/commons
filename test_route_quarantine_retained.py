#!/usr/bin/env python3
"""Retained root bridge for the canonical outbound route-quarantine suite."""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULE = "tools.outbound_send_guard.test_route_quarantine"
_RAN = re.compile(r"Ran\s+(\d+)\s+tests?\b")


class RouteQuarantineRetainedTests(unittest.TestCase):
    def _run_suite(self, *, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-m", "unittest", "-v", MODULE])
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
        mode = "optimized" if optimized else "normal"
        self.assertEqual(completed.returncode, 0, f"route-quarantine suite failed ({mode}):\n{combined}")
        match = _RAN.search(combined)
        self.assertIsNotNone(match, f"unittest did not report an executed test count ({mode}):\n{combined}")
        self.assertGreater(int(match.group(1)), 0, f"route-quarantine suite executed zero tests ({mode}):\n{combined}")
        self.assertIn("OK", combined)

    def test_route_quarantine_normal(self) -> None:
        self._run_suite(optimized=False)

    def test_route_quarantine_optimized(self) -> None:
        self._run_suite(optimized=True)


if __name__ == "__main__":
    unittest.main()
