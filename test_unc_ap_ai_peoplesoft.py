"""Run all UNC AP source, batch and review tests without a new Actions workflow."""
from pathlib import Path
import subprocess
import sys
import unittest

PACKAGE = Path(__file__).parent / "revenue" / "opportunities" / "unc_ap_ai_peoplesoft"
CODE = """
import unittest
suite = unittest.defaultTestLoader.discover('.', pattern='test_*.py')
count = suite.countTestCases()
print(f'UNC_AP_TESTS={count}')
if count < 116:
    raise SystemExit('UNC AP discovery lost expected coverage')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
"""


class UNCAPProof(unittest.TestCase):
    def run_mode(self, optimized):
        command = [sys.executable, *(['-O'] if optimized else []), '-B', '-c', CODE]
        result = subprocess.run(command, cwd=PACKAGE, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('UNC_AP_TESTS=', result.stdout)

    def test_normal(self):
        self.run_mode(False)

    def test_optimized(self):
        self.run_mode(True)


if __name__ == '__main__':
    unittest.main()
