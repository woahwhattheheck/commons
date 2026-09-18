#!/usr/bin/env python3
"""Retained, non-vacuous OneWriter hostile-suite bridge.

This root test keeps the canonical nested OneWriter contract executable from the
repository-wide retained source-parses workflow. It deliberately launches the
same nested test module under both normal Python and real ``python -O`` and
rejects missing/vacuous discovery.
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "competitions" / "emergent-builderfest-2026" / "onewriter" / "test_acceptance.py"
MIN_NESTED_TESTS = 28


class RetainedOneWriterTests(unittest.TestCase):
    def _run_nested(self, optimized: bool) -> None:
        self.assertTrue(TARGET.is_file(), f"missing canonical OneWriter hostile suite: {TARGET}")
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command += ["-m", "unittest", "-v", str(TARGET)]
        proc = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        output = proc.stdout + proc.stderr
        self.assertEqual(0, proc.returncode, output)
        match = re.search(r"Ran (\d+) tests?", output)
        self.assertIsNotNone(match, output)
        self.assertGreaterEqual(int(match.group(1)), MIN_NESTED_TESTS, output)
        self.assertRegex(output, r"\bOK\b")

    def test_nested_suite_normal_and_optimized(self) -> None:
        self._run_nested(False)
        self._run_nested(True)


if __name__ == "__main__":
    unittest.main()
