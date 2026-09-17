"""Retained root CI bridge for tools.costed_work_batch."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent


class CostedWorkBatchRetainedTests(unittest.TestCase):
    def _run(self, optimized: bool) -> str:
        cmd = [sys.executable]
        if optimized:
            cmd.append("-O")
        cmd.extend(
            ["-m", "unittest", "-v", "tools.costed_work_batch.test_planner"]
        )
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=90,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("OK", proc.stdout)
        self.assertIn("Ran 21 tests", proc.stdout)
        return proc.stdout

    def test_nested_normal(self):
        self._run(False)

    def test_nested_optimized(self):
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
        self._run(True)


if __name__ == "__main__":
    unittest.main()
