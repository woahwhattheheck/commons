from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class ConsolidatedRevenueGuardWorkflowTests(unittest.TestCase):
    def run_ok(self, *argv: str) -> None:
        proc = subprocess.run(
            [sys.executable, *argv],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"command failed: {sys.executable} {' '.join(argv)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )

    def test_outbound_collision_guard_normal_and_optimized(self) -> None:
        modules = (
            "tests.test_outbound_collision_guard",
            "tests.test_outbound_collision_guard_release_boundary",
        )
        self.run_ok("-m", "py_compile", "revenue/outbound_collision_guard/core.py", "tests/test_outbound_collision_guard.py", "tests/test_outbound_collision_guard_release_boundary.py")
        self.run_ok("-m", "unittest", "-v", *modules)
        self.run_ok("-O", "-m", "unittest", "-v", *modules)
        self.run_ok("-m", "revenue.outbound_collision_guard.demo")

    def test_outbound_collision_replay_guard_normal_and_optimized(self) -> None:
        module = "test_outbound_collision_replay_guard.py"
        self.run_ok("-m", "py_compile", "revenue/outbound_collision_replay_guard/engine.py", "revenue/outbound_collision_replay_guard/demo/demo.py", module)
        self.run_ok("-m", "unittest", "-v", module)
        self.run_ok("-O", "-m", "unittest", "-v", module)
        self.run_ok("-m", "revenue.outbound_collision_replay_guard.demo.demo")

    def test_agent_autopsy_fulfillment_normal_and_optimized(self) -> None:
        module = "revenue.agent_failure_autopsy_fulfillment.test_core"
        self.run_ok("-m", "py_compile", "revenue/agent_failure_autopsy_fulfillment/core.py", "revenue/agent_failure_autopsy_fulfillment/test_core.py")
        self.run_ok("-m", "unittest", "-v", module)
        self.run_ok("-O", "-m", "unittest", "-v", module)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            self.run_ok("revenue/agent_failure_autopsy_fulfillment/core.py", "compile", "revenue/agent_failure_autopsy_fulfillment/sample_input.json", str(out))
            self.run_ok("revenue/agent_failure_autopsy_fulfillment/core.py", "verify", str(out / "packet.json"))

    def test_oss_grant_eligibility_normal_and_optimized(self) -> None:
        module = "revenue.oss_grant_eligibility_packet.test_compiler"
        self.run_ok("-m", "py_compile", "revenue/oss_grant_eligibility_packet/__init__.py", "revenue/oss_grant_eligibility_packet/__main__.py", "revenue/oss_grant_eligibility_packet/compiler.py", "revenue/oss_grant_eligibility_packet/test_compiler.py")
        self.run_ok("-m", "unittest", "-v", module)
        self.run_ok("-O", "-m", "unittest", "-v", module)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "grant"
            self.run_ok(
                "-m", "revenue.oss_grant_eligibility_packet", "compile",
                "--programs", "revenue/oss_grant_eligibility_packet/reference_programs.json",
                "--input", "revenue/oss_grant_eligibility_packet/fixtures/synthetic_project.json",
                "--out-dir", str(out),
            )
            self.run_ok(
                "-m", "revenue.oss_grant_eligibility_packet", "verify",
                "--programs", "revenue/oss_grant_eligibility_packet/reference_programs.json",
                "--input", "revenue/oss_grant_eligibility_packet/fixtures/synthetic_project.json",
                "--packet", str(out / "packet.json"),
                "--markdown", str(out / "packet.md"),
                "--receipt", str(out / "receipt.json"),
            )

    def test_rfp_clarification_normal_and_optimized(self) -> None:
        modules = (
            "revenue.rfp_clarification_questions.test_compiler",
            "revenue.rfp_clarification_questions.test_dedupe",
            "revenue.rfp_clarification_questions.test_hostile",
        )
        self.run_ok(
            "-m", "py_compile",
            "revenue/rfp_clarification_questions/_core.py",
            "revenue/rfp_clarification_questions/_rows.py",
            "revenue/rfp_clarification_questions/_render.py",
            "revenue/rfp_clarification_questions/_engine.py",
            "revenue/rfp_clarification_questions/compiler.py",
            "revenue/rfp_clarification_questions/_test_support.py",
            "revenue/rfp_clarification_questions/test_compiler.py",
            "revenue/rfp_clarification_questions/test_dedupe.py",
            "revenue/rfp_clarification_questions/test_hostile.py",
        )
        self.run_ok("-m", "unittest", "-v", *modules)
        self.run_ok("-O", "-m", "unittest", "-v", *modules)


if __name__ == "__main__":
    unittest.main(verbosity=2)
