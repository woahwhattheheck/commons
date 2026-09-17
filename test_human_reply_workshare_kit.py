from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
MODULE = "revenue.human_reply_workshare_kit.test_core"


class HumanReplyWorkshareRetainedBattery(unittest.TestCase):
    def _run_suite(self, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command += ["-m", "unittest", MODULE, "-v"]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )
        if completed.returncode != 0:
            self.fail(completed.stdout)
        self.assertIn("Ran 28 tests", completed.stdout)
        self.assertIn("OK", completed.stdout)

    def test_nested_suite_normal(self):
        self._run_suite(False)

    def test_nested_suite_optimized(self):
        self._run_suite(True)


if __name__ == "__main__":
    unittest.main()
