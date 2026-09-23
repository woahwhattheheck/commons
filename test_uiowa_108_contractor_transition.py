"""Exercise the complete UIOWA-108 component on the retained root test surface."""
from pathlib import Path
import re
import subprocess
import sys
import unittest

LANE = Path(__file__).resolve().parent / 'revenue' / 'uiowa_rfq_18649_contractor_transition'


class ContractorTransitionRegression(unittest.TestCase):
    def run_component(self, optimized):
        command = [sys.executable]
        if optimized:
            command.append('-O')
        command += ['-m', 'unittest', '-v', 'test_transition', 'test_completion_integrity']
        result = subprocess.run(command, cwd=LANE, text=True, capture_output=True, timeout=180)
        transcript = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, transcript)
        counts = re.findall(r'Ran ([0-9]+) tests?', transcript)
        self.assertTrue(counts, transcript)
        self.assertGreaterEqual(int(counts[-1]), 50, transcript)

    def test_component_normal(self):
        self.run_component(False)

    def test_component_optimized(self):
        self.run_component(True)


if __name__ == '__main__':
    unittest.main()
