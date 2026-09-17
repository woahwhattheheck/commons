from __future__ import annotations

import subprocess
import sys
import unittest

from revenue.human_reply_workshare_kit import test_core, test_truth_guard


class HumanReplyWorkshareOptimizedBridgeTests(unittest.TestCase):
    def test_nested_suite_under_python_optimized_mode(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "revenue.human_reply_workshare_kit.test_core",
                "revenue.human_reply_workshare_kit.test_truth_guard",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=(completed.stdout + "\n" + completed.stderr).strip(),
        )


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None):
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(test_core))
    suite.addTests(loader.loadTestsFromModule(test_truth_guard))
    suite.addTests(loader.loadTestsFromTestCase(HumanReplyWorkshareOptimizedBridgeTests))
    return suite


if __name__ == "__main__":
    unittest.main()
