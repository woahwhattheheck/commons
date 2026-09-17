from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUITES = (
    "tests.test_nhdes_lims_2026_093",
    "tests.test_nhdes_lims_2026_093_builtin_shadow",
)
DEDICATED_WORKFLOW = ROOT / ".github" / "workflows" / "nhdes-lims-2026-093.yml"


class NhdesLims2026093BatteryBridge(unittest.TestCase):
    def test_no_dedicated_workflow_consumes_live_slot(self) -> None:
        self.assertFalse(DEDICATED_WORKFLOW.exists())

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
                f"nested NHDES 2026-093 suites failed (optimized={optimized})\n"
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
