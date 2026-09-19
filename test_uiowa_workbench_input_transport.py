"""Expose the workbench's actual import/HTTP regressions to root test discovery."""
from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

LANE = Path(__file__).resolve().parent / "revenue" / "uiowa_rfq_18649_workbench"


class WorkbenchInputTransportSuite(unittest.TestCase):
    def run_checked(self, argv):
        result = subprocess.run(argv, cwd=LANE, capture_output=True, text=True, timeout=90)
        output = result.stdout + result.stderr
        print(output, end="", flush=True)
        self.assertEqual(result.returncode, 0, output)

    def test_node_actual_import_handler(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required; transport checks must not silently skip")
        self.run_checked([node, str(LANE / "test_input_transport.js")])

    def test_loopback_http_boundary(self):
        optimize = ["-O"] if sys.flags.optimize else []
        self.run_checked([sys.executable, *optimize, "-m", "unittest", "-v", "test_input_transport.py"])


if __name__ == "__main__":
    unittest.main()
