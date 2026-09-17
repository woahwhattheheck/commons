from __future__ import annotations

import subprocess
import sys
import unittest


# Root placement is intentional: tests.yml path-filters on root test_*.py.
# This bridge makes semantic-generation repairs execute both normal and -O
# without consuming another active workflow slot.
class TtOneLabLimsRetainedBridge(unittest.TestCase):
    def _run(self, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(
            [
                "-m",
                "unittest",
                "-v",
                "revenue.tt_one_lab_lims_consultant.test_carrier",
            ]
        )
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=90,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )

    def test_normal(self) -> None:
        self._run(False)

    def test_optimized(self) -> None:
        self._run(True)


if __name__ == "__main__":
    unittest.main()
