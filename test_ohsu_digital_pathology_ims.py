from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent / "revenue" / "ohsu_digital_pathology_ims"


class OhsuDigitalPathologyBatteryBridge(unittest.TestCase):
    def _run(self, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-m", "unittest", "discover", "-s", str(PACKAGE), "-v"])
        subprocess.run(command, check=True)

    def test_ohsu_digital_pathology_ims_normal(self) -> None:
        self._run(False)

    def test_ohsu_digital_pathology_ims_optimized(self) -> None:
        self._run(True)


if __name__ == "__main__":
    unittest.main()
