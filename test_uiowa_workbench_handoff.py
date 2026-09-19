"""Run the Iowa handoff contract and application tests in the existing CI battery."""
from pathlib import Path
import os
import subprocess
import sys
import unittest


WORKBENCH = Path(__file__).resolve().parent / "revenue" / "uiowa_rfq_18649_workbench"


class IowaWorkbenchHandoffTests(unittest.TestCase):
    def test_handoff_and_application_contracts(self):
        commands = [
            [sys.executable, "-m", "unittest", "-v", "test_workbench.py"],
            ["node", "--test", "test_handoff.js", "handoff_import.test.js", "test_app.js"],
        ]
        for command in commands:
            with self.subTest(command=command):
                result = subprocess.run(command, cwd=WORKBENCH, text=True,
                                        capture_output=True, timeout=60, check=False,
                                        env={**os.environ, "PYTHON": sys.executable})
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
