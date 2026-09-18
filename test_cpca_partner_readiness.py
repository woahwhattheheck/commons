import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "commercial" / "cpca-hccn-connect" / "test_cpca_partner_readiness.py"


class RetainedCpcaPartnerReadinessTests(unittest.TestCase):
    def _run(self, optimized):
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.append(str(TARGET))
        proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=60)
        output = proc.stdout + proc.stderr
        self.assertEqual(0, proc.returncode, output)
        match = re.search(r"Ran (\d+) tests?", output)
        self.assertIsNotNone(match, output)
        self.assertGreaterEqual(int(match.group(1)), 18, output)
        self.assertRegex(output, r"\bOK\b")

    def test_nested_suite_normal_and_optimized(self):
        self._run(False)
        self._run(True)


if __name__ == "__main__":
    unittest.main()
