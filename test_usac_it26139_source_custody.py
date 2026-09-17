from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "opportunities" / "usac_it_26_139_ai_consulting" / "test_qualify.py"


class USACIT26139RetainedBattery(unittest.TestCase):
    def _run(self, optimized: bool) -> None:
        argv = [sys.executable]
        if optimized:
            argv.append("-O")
        argv.append(str(TARGET))
        completed = subprocess.run(
            argv,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"USAC IT-26-139 nested suite failed optimized={optimized}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )

    def test_nested_suite_normal(self) -> None:
        self._run(False)

    def test_nested_suite_optimized(self) -> None:
        self._run(True)


if __name__ == "__main__":
    unittest.main()
