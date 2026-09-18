#!/usr/bin/env python3
"""Retained root bridge for the live-pursuit partner-shortlist compiler.

The Commons battery discovers root test_*.py files but not nested revenue tests.
This bridge keeps the complete nested suite and CLI round-trip on the existing
workflow surface so the product does not consume another active Actions slot.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRODUCT = ROOT / "revenue/live_pursuit_partner_shortlist"
TESTS = PRODUCT / "tests"
FIXTURE = PRODUCT / "fixtures/pursuits.synthetic.json"
COMPILER = PRODUCT / "compiler.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
    )


class LivePursuitPartnerShortlistBridge(unittest.TestCase):
    def _nested(self, optimized: bool) -> None:
        argv = [sys.executable]
        if optimized:
            argv.append("-O")
        argv += [
            "-m",
            "unittest",
            "discover",
            "-s",
            str(TESTS.relative_to(ROOT)),
            "-p",
            "test_*.py",
            "-v",
        ]
        result = _run(argv)
        combined = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, combined)
        self.assertRegex(combined, r"Ran 24 tests")
        self.assertIn("OK", combined)

    def test_nested_suite_normal(self):
        self._nested(False)

    def test_nested_suite_optimized(self):
        self._nested(True)

    def test_cli_compile_verify_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out"
            compile_result = _run([
                sys.executable,
                str(COMPILER.relative_to(ROOT)),
                "compile",
                "--input",
                str(FIXTURE.relative_to(ROOT)),
                "--out-dir",
                str(out),
            ])
            self.assertEqual(
                compile_result.returncode,
                0,
                compile_result.stdout + compile_result.stderr,
            )
            verify_result = _run([
                sys.executable,
                str(COMPILER.relative_to(ROOT)),
                "verify",
                "--input",
                str(FIXTURE.relative_to(ROOT)),
                "--out-dir",
                str(out),
            ])
            self.assertEqual(
                verify_result.returncode,
                0,
                verify_result.stdout + verify_result.stderr,
            )


if __name__ == "__main__":
    unittest.main()
