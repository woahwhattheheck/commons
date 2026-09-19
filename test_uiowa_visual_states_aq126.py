"""Enroll the Node standard-library visual-state tests without changing workflows."""
from pathlib import Path
import shutil
import subprocess
import unittest


class VisualStatesAQ126(unittest.TestCase):
    def test_actual_app_presentation_contract(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node unavailable: visual-state runtime suite NOT executed")
        suite = Path(__file__).resolve().parent / "revenue/uiowa_rfq_18649_workbench/visual_states_aq126/test_visual_states.js"
        result = subprocess.run([node, "--test", str(suite)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("# tests 32", result.stdout)
        self.assertIn("# pass 32", result.stdout)
        self.assertIn("# skipped 0", result.stdout)


if __name__ == "__main__":
    unittest.main()
