"""Repository-root bridge for the independent AP batch review suite."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "revenue/opportunities/unc_ap_ai_peoplesoft"

class APBatchSuite(unittest.TestCase):
    def test_focused_batch_contract(self):
        command = [sys.executable, *(["-O"] if sys.flags.optimize else []),
                   "-W", "error::ResourceWarning", str(PACKAGE / "run_batch_tests.py")]
        result = subprocess.run(command, cwd=PACKAGE, capture_output=True,
                                text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("discovered=94", result.stdout)

if __name__ == "__main__":
    unittest.main()
