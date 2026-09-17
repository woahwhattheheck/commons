from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEST_DIR = ROOT / "revenue" / "buyer_redline_scope_delta" / "tests"
LIVE_WORKFLOW = ROOT / ".github" / "workflows" / "buyer-redline-scope-delta.yml"


class BuyerRedlineCanonicalBatteryBridge(unittest.TestCase):
    def test_no_dedicated_workflow_slot(self) -> None:
        self.assertFalse(LIVE_WORKFLOW.exists())

    def _run(self, *, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend([
            "-m",
            "unittest",
            "discover",
            "-s",
            str(TEST_DIR),
            "-p",
            "test_*.py",
            "-v",
        ])
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=(
                f"buyer-redline canonical suite failed (optimized={optimized})\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            ),
        )

    def test_canonical_suite_normal(self) -> None:
        self._run(optimized=False)

    def test_canonical_suite_optimized(self) -> None:
        self._run(optimized=True)


if __name__ == "__main__":
    unittest.main()
