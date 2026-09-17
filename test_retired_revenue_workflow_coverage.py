#!/usr/bin/env python3
"""Preserve tests from revenue workflows retired to stay within the 67-slot cap.

Commons' retained root battery executes this file on its ordinary Python.  The
retained ``revenue-hardening`` workflow also runs it on the exact interpreter
families used by the five retired workflows.  That lets workflow-surface stay
at 67 without turning removal of a workflow file into removal of its tests.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

OUTBOUND = (
    "tests/test_outbound_collision_guard.py",
    "tests/test_outbound_collision_guard_release_boundary.py",
)
REPLAY = ("test_outbound_collision_replay_guard.py",)
OSS_GRANT = ("revenue/oss_grant_eligibility_packet/test_compiler.py",)
AUTOPSY = ("revenue/agent_failure_autopsy_fulfillment/test_core.py",)
RFP = (
    "revenue/rfp_clarification_questions/test_compiler.py",
    "revenue/rfp_clarification_questions/test_dedupe.py",
    "revenue/rfp_clarification_questions/test_hostile.py",
)
ALL_SUITES = OUTBOUND + REPLAY + OSS_GRANT + AUTOPSY + RFP

# Match the interpreter coverage of the retired workflows.  Any other
# interpreter (notably the retained root battery's current 3.12) runs all
# suites, so ordinary battery execution remains a complete semantic fence.
SUITES_BY_VERSION = {
    (3, 9): OUTBOUND + REPLAY + OSS_GRANT,
    (3, 10): AUTOPSY,
    (3, 11): RFP,
    (3, 13): OUTBOUND + REPLAY + OSS_GRANT + AUTOPSY,
}


class RetiredRevenueWorkflowCoverage(unittest.TestCase):
    def test_retired_suites_normal_and_optimized(self) -> None:
        suites = SUITES_BY_VERSION.get(sys.version_info[:2], ALL_SUITES)
        self.assertTrue(suites, "retired workflow bridge selected no suites")
        for optimized in (False, True):
            with self.subTest(version=sys.version.split()[0], optimized=optimized):
                command = [sys.executable]
                if optimized:
                    command.append("-O")
                command.extend(["-m", "unittest", "-v", *suites])
                done = subprocess.run(
                    command,
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=240,
                )
                detail = (done.stdout + "\n" + done.stderr)[-20000:]
                self.assertEqual(done.returncode, 0, detail)


if __name__ == "__main__":
    unittest.main()
