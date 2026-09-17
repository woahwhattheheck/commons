from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SUITE = "tests.test_nysdec_hale_creek_khemia_partner"
LIVE_WORKFLOW = ROOT / ".github" / "workflows" / "nysdec-hale-creek-khemia-partner.yml"


class NysdecHaleCreekKhemiaPartnerBatteryBridge(unittest.TestCase):
    def test_dedicated_workflow_does_not_consume_a_retained_slot(self) -> None:
        self.assertFalse(LIVE_WORKFLOW.exists())
        self.assertFalse(LIVE_WORKFLOW.is_file())

    def _run(self, *, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-m", "unittest", "-v", SUITE])
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
                f"nested NYS DEC Hale Creek Khemia suite failed (optimized={optimized})\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            ),
        )

    def test_nested_suite_normal(self) -> None:
        self._run(optimized=False)

    def test_nested_suite_optimized(self) -> None:
        self._run(optimized=True)


if __name__ == "__main__":
    unittest.main()
