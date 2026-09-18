"""Retained CI bridge for the Westfield workshare truth-boundary suite."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
TEST_DIR = ROOT / "revenue" / "westfield_advancement_data_modeling" / "tests"


class WestfieldAdvancementRetainedTests(unittest.TestCase):
    def _run_nested(self, optimized: bool) -> None:
        cmd = [sys.executable]
        if optimized:
            cmd.append("-O")
        cmd.extend(
            [
                "-m",
                "unittest",
                "discover",
                "-s",
                str(TEST_DIR),
                "-p",
                "test_acceptance.py",
                "-v",
            ]
        )
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("Ran 19 tests", proc.stdout)
        self.assertIn("OK", proc.stdout)

    def test_nested_suite_normal(self):
        self._run_nested(False)

    def test_nested_suite_optimized(self):
        canary = subprocess.run(
            [
                sys.executable,
                "-O",
                "-c",
                "import sys; sys.exit(0 if not __debug__ else 91)",
            ],
            cwd=ROOT,
            check=False,
            timeout=20,
        )
        self.assertEqual(canary.returncode, 0)
        self._run_nested(True)


if __name__ == "__main__":
    unittest.main()
