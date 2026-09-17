from __future__ import annotations

import subprocess
import sys
import unittest


MODULES = (
    "revenue.wri_open_timber_portal.test_owner_review_proposal",
    "revenue.wri_open_timber_portal.test_engine",
    "revenue.wri_open_timber_portal.test_cli",
)


class WriOpenTimberOwnerReviewRetainedBridge(unittest.TestCase):
    def _run(self, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-m", "unittest", "-v", *MODULES])
        completed = subprocess.run(command, capture_output=True, text=True, timeout=90)
        self.assertEqual(
            completed.returncode,
            0,
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )

    def test_wri_proposal_and_existing_carrier_normal(self) -> None:
        self._run(False)

    def test_wri_proposal_and_existing_carrier_optimized(self) -> None:
        self._run(True)


if __name__ == "__main__":
    unittest.main()
