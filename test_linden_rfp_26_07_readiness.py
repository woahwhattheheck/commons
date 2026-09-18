from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import unittest

# Re-export the canonical hostile suite so the retained root battery executes the
# exact same TestCase rather than maintaining a second semantic test copy.
from tests.test_linden_rfp_26_07_readiness import LindenRfpReadinessTests  # noqa: F401

ROOT = Path(__file__).resolve().parent
TOOL = ROOT / "tools" / "linden_rfp_26_07_readiness.py"
NESTED_TEST = ROOT / "tests" / "test_linden_rfp_26_07_readiness.py"
SOURCES = ROOT / "revenue" / "procurement" / "linden-rfp-26-07" / "source_register.json"
STATE = ROOT / "revenue" / "procurement" / "linden-rfp-26-07" / "readiness_state.json"


class LindenRfpRetainedExecutionSurfaceTests(unittest.TestCase):
    """Keep the retired path-scoped workflow's proof inside retained CI."""

    def test_optimized_suite_and_fail_closed_fixture(self):
        subprocess.run(
            [sys.executable, "-m", "py_compile", str(TOOL), str(NESTED_TEST)],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "-v",
                "tests.test_linden_rfp_26_07_readiness",
            ],
            cwd=ROOT,
            check=True,
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--sources",
                str(SOURCES),
                "--state",
                str(STATE),
                "--expect-not-ready",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
