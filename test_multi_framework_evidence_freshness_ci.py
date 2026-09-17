from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEST_DIR = ROOT / "tests"
PATTERN = "test_multi_framework_evidence_freshness*.py"


class MultiFrameworkEvidenceFreshnessCIGate(unittest.TestCase):
    def test_normal_focused_suite_executes_and_passes(self) -> None:
        suite = unittest.defaultTestLoader.discover(
            str(TEST_DIR), pattern=PATTERN, top_level_dir=str(ROOT)
        )
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        self.assertGreater(result.testsRun, 0, "freshness suite discovered zero tests")
        self.assertTrue(result.wasSuccessful(), "freshness suite failed under normal Python")

    def test_optimized_focused_suite_executes_and_passes(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-O",
                "-B",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                PATTERN,
                "-v",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        transcript = proc.stdout + proc.stderr
        match = re.search(r"Ran\s+(\d+)\s+tests?", transcript)
        self.assertIsNotNone(match, "optimized freshness suite emitted no unittest count")
        self.assertGreater(int(match.group(1)), 0, "optimized freshness suite ran zero tests")
        self.assertEqual(proc.returncode, 0, transcript)


if __name__ == "__main__":
    unittest.main(verbosity=2)
