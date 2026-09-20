"""Expose only the portable Civic handoff integration suite to root discovery."""
from pathlib import Path
import subprocess
import sys
import unittest


class CivicPortableHandoffSuite(unittest.TestCase):
    def test_component_suite(self):
        component = (Path(__file__).resolve().parent / "competitions" /
                     "gatewayhacks-2026-civic-ledger")
        optimization = ["-" + "O" * sys.flags.optimize] if sys.flags.optimize else []
        result = subprocess.run(
            [sys.executable, "-B", *optimization, "-m", "unittest", "discover",
             "-s", "tests", "-p", "test_handoff.py", "-v"],
            cwd=component, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
