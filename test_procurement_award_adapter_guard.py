from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class ProcurementAwardAdapterGuardBridgeTests(unittest.TestCase):
    def test_engine_adapter_and_uri_custody_suites_normal_and_optimized(self):
        root = Path(__file__).resolve().parent
        modules = [
            "revenue.procurement_award_price_intelligence.test_engine",
            "revenue.procurement_award_price_intelligence.test_adapters",
            "revenue.procurement_award_price_intelligence.test_adapter_uri_custody",
        ]
        for optimized in (False, True):
            command = [sys.executable]
            if optimized:
                command.append("-O")
            command += ["-m", "unittest", "-v", *modules]
            result = subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=180,
            )
            self.assertEqual(
                0,
                result.returncode,
                f"optimized={optimized}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
            )


if __name__ == "__main__":
    unittest.main()
