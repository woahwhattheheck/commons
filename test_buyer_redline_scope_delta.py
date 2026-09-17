from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SUITES = (
    "revenue.buyer_redline_scope_delta.test_engine",
    "revenue.buyer_redline_scope_delta.test_hardening",
)
LIVE_WORKFLOW = ROOT / ".github" / "workflows" / "buyer-redline-scope-delta.yml"


class BuyerRedlineScopeDeltaBatteryBridge(unittest.TestCase):
    def test_dedicated_workflow_does_not_consume_a_retained_slot(self) -> None:
        self.assertFalse(LIVE_WORKFLOW.exists())
        self.assertFalse(LIVE_WORKFLOW.is_file())

    def _run(self, *, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-m", "unittest", "-v", *SUITES])
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=(
                f"nested buyer-redline scope-delta suites failed (optimized={optimized})\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            ),
        )

    def test_nested_suites_normal(self) -> None:
        self._run(optimized=False)

    def test_nested_suites_optimized(self) -> None:
        self._run(optimized=True)


if __name__ == "__main__":
    unittest.main()
