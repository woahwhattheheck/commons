"""Run the workbench's HTTP query-routing regressions from root discovery."""
from pathlib import Path
import subprocess
import sys
import unittest


class WorkbenchQueryRoutingDiscoveryTests(unittest.TestCase):
    def test_http_query_contract(self):
        root = Path(__file__).resolve().parent
        cwd = root / "revenue" / "uiowa_rfq_18649_workbench"
        command = [sys.executable]
        if sys.flags.optimize:
            command.append("-O")
        command.extend(["-B", "-m", "unittest", "-v", "test_static_queries.py"])
        result = subprocess.run(
            command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertRegex(result.stdout, r"Ran [1-9][0-9]* tests?", result.stdout)


if __name__ == "__main__":
    unittest.main()
