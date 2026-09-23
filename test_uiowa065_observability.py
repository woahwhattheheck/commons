"""Root discovery bridge for the isolated UIOWA-065 original and repair suites."""
from pathlib import Path
import subprocess
import sys
import unittest


class ObservabilityDiscoveryTests(unittest.TestCase):
    def test_isolated_component_suite(self):
        kit = Path(__file__).resolve().parent / "revenue" / "uiowa_rfq_18649_observability"
        script = """
import sys, unittest
suite = unittest.defaultTestLoader.discover('.', pattern='test_*.py')
if suite.countTestCases() < 57:
    raise RuntimeError('retained observability test closure was not discovered')
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful() or result.skipped:
    raise SystemExit(1)
"""
        flags = ["-" + "O" * sys.flags.optimize] if sys.flags.optimize else []
        result = subprocess.run([sys.executable, *flags, "-c", script], cwd=kit,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
