from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
import unittest

# Re-export the canonical hostile suite so retained root discovery executes the
# exact semantic tests rather than a second copy.
from tests.test_multi_framework_evidence_freshness_custody import (  # noqa: F401
    FreshnessCustodyRecoveryTests,
)

ROOT = Path(__file__).resolve().parent
NESTED = ROOT / "tests" / "test_multi_framework_evidence_freshness_custody.py"
PACKAGE = ROOT / "revenue" / "multi_framework_evidence_freshness"


class MultiFrameworkFreshnessRetainedExecutionTests(unittest.TestCase):
    def test_nested_suite_runs_under_optimized_python_with_positive_count(self) -> None:
        sources = [
            PACKAGE / "__init__.py",
            PACKAGE / "gate.py",
            PACKAGE / "custody.py",
            PACKAGE / "cli.py",
            NESTED,
        ]
        subprocess.run(
            [sys.executable, "-m", "py_compile", *map(str, sources)],
            cwd=ROOT,
            check=True,
        )
        completed = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "-v",
                "tests.test_multi_framework_evidence_freshness_custody",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        transcript = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, msg=transcript)
        match = re.search(r"Ran\s+(\d+)\s+tests?", transcript)
        self.assertIsNotNone(match, msg=transcript)
        self.assertGreater(int(match.group(1)), 0, msg=transcript)
        self.assertIn("OK", transcript)


if __name__ == "__main__":
    unittest.main()
