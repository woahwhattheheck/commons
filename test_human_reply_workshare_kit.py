from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

from revenue.human_reply_workshare_kit import test_core, test_truth_guard


ROOT = Path(__file__).resolve().parent
NESTED_MODULES = (
    "revenue.human_reply_workshare_kit.test_core",
    "revenue.human_reply_workshare_kit.test_truth_guard",
)


class HumanReplyWorkshareOptimizedBridgeTests(unittest.TestCase):
    def test_nested_suites_under_python_optimized_mode(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-O", "-m", "unittest", "-v", *NESTED_MODULES],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)


def load_tests(
    loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None
) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(test_core))
    suite.addTests(loader.loadTestsFromModule(test_truth_guard))
    suite.addTests(loader.loadTestsFromTestCase(HumanReplyWorkshareOptimizedBridgeTests))
    return suite


if __name__ == "__main__":
    unittest.main()
