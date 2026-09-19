"""Run the isolated sample-precision suite from the repository test entry point."""
from pathlib import Path
import subprocess
import sys
import unittest


class SamplePrecisionSuite(unittest.TestCase):
    def test_component_suite(self):
        root = Path(__file__).resolve().parent
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "-v", "test_precision.py"],
            cwd=root / "revenue" / "uiowa_rfq_18649_sample_precision",
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
