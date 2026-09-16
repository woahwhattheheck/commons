from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
CARRIER = ROOT / "revenue" / "opportunities" / "army_sbir_arm26bx06_nv012"


class ArmySbirArm26Bx06Nv012BatteryBridge(unittest.TestCase):
    def _run(self, *args: str, optimized: bool = False) -> subprocess.CompletedProcess[str]:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(args)
        return subprocess.run(
            command,
            cwd=CARRIER,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )

    def _require_ok(self, cp: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(cp.returncode, 0, (cp.stdout, cp.stderr))

    def test_exact_carrier_normal_and_optimized(self) -> None:
        compile_run = self._run(
            "-m", "py_compile", "decision_program.py", "qualification_gate.py",
            "tests/test_carrier.py", "tests/test_strict_cli.py",
        )
        self._require_ok(compile_run)

        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                suite = self._run("-B", "-m", "unittest", "discover", "-s", "tests", "-v", optimized=optimized)
                self._require_ok(suite)

        point = self._run("-B", "decision_program.py", "evaluate", "examples/point_trade.json")
        g1 = self._run("-B", "decision_program.py", "evaluate", "examples/long_horizon_g1.json")
        g2 = self._run("-B", "decision_program.py", "evaluate", "examples/long_horizon_g2.json")
        refresh = self._run(
            "-B", "decision_program.py", "verify-refresh",
            "examples/long_horizon_g1.json", "examples/long_horizon_g2.json",
        )
        qualification = self._run("-B", "qualification_gate.py", "qualification.example.json")
        for cp in (point, g1, g2, refresh, qualification):
            self._require_ok(cp)

        self.assertEqual(json.loads(point.stdout)["readiness"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(json.loads(g2.stdout)["readiness"], "HOLD")
        self.assertEqual(json.loads(qualification.stdout)["disposition"], "HOLD")
        self.assertTrue(json.loads(refresh.stdout)["human_re_review_required"])


if __name__ == "__main__":
    unittest.main()
