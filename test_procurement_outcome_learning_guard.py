from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class ProcurementOutcomeLearningGuardTests(unittest.TestCase):
    def test_outcome_learning_suite_normal_and_optimized(self):
        root = Path(__file__).resolve().parent
        module = "revenue.procurement_outcome_learning.test_engine"
        for optimized in (False, True):
            command = [sys.executable]
            if optimized:
                command.append("-O")
            command += ["-m", "unittest", "-v", module]
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
