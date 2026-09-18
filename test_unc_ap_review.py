"""Run the AP review's nonempty normal/optimized suite through existing discovery."""
from pathlib import Path
import subprocess
import sys
import unittest

PACKAGE = Path(__file__).parent / "revenue" / "opportunities" / "unc_ap_ai_peoplesoft"
CODE = """
import unittest
suite = unittest.defaultTestLoader.discover('.', pattern='test_ap_review.py')
count = suite.countTestCases()
print(f'AP_REVIEW_TESTS={count}')
if count < 71:
    raise SystemExit('AP review discovery lost expected coverage')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
"""


class APReviewProof(unittest.TestCase):
    def run_mode(self, optimized):
        command = [sys.executable, *(['-O'] if optimized else []), '-B', '-c', CODE]
        result = subprocess.run(command, cwd=PACKAGE, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('AP_REVIEW_TESTS=', result.stdout)

    def test_normal(self):
        self.run_mode(False)

    def test_optimized(self):
        self.run_mode(True)


if __name__ == '__main__':
    unittest.main()
