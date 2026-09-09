# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import factorial_report
import materialize


SCHEDULER_FIXTURE = (
    "before\n"
    + materialize.CARRY_CONTROL
    + "middle\n"
    + materialize.REFERENCE_CONTROL
    + "after\n"
)


class MaterializationTests(unittest.TestCase):
    def test_all_four_factorial_arms_patch_exactly_the_declared_seams(self):
        expectations = {
            "control": (False, False),
            "carry_095": (True, False),
            "force_end": (False, True),
            "both": (True, True),
        }
        rendered = {}
        for arm, (carry, force_end) in expectations.items():
            with self.subTest(arm=arm):
                text, receipt = materialize.patch_scheduler(SCHEDULER_FIXTURE, arm)
                rendered[arm] = text
                self.assertEqual(receipt["carry_discount"], 0.95 if carry else 1.0)
                self.assertEqual(
                    receipt["force_residual_reference_at_horizon"], force_end
                )
                self.assertEqual(materialize.CARRY_PATCH in text, carry)
                self.assertEqual(materialize.CARRY_CONTROL in text, not carry)
                self.assertEqual(materialize.REFERENCE_PATCH in text, force_end)
                self.assertEqual(materialize.REFERENCE_CONTROL in text, not force_end)
        self.assertEqual(len(set(rendered.values())), 4)

    def test_patch_fails_closed_when_source_seam_drifted(self):
        with self.assertRaisesRegex(RuntimeError, "source seam drift"):
            materialize.patch_scheduler(SCHEDULER_FIXTURE.replace("carry=float", "carry = float"), "carry_095")

    def test_generated_entry_rejects_post_binding_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "candidate.py").write_text(
                "def agent(observation, configuration=None): return {'market': []}\n",
                encoding="utf-8",
            )
            (root / "ARM.json").write_text('{"arm":"control"}\n', encoding="utf-8")
            closure = materialize.tree_receipt(root, exclude=frozenset({"bound_entry.py"}))
            entry = root / "bound_entry.py"
            entry.write_text(
                materialize._bound_entry_source(closure, "control"), encoding="utf-8"
            )
            probe = (
                "import importlib.util, pathlib, sys\n"
                f"p=pathlib.Path({str(entry)!r})\n"
                "s=importlib.util.spec_from_file_location('bound_probe',p)\n"
                "m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)\n"
                "assert callable(m.agent)\n"
            )
            ok = subprocess.run(
                [sys.executable, "-B", "-c", probe],
                env={"PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                text=True,
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            (root / "candidate.py").write_text(
                "def agent(observation, configuration=None): return {'market': [['SELL','MILK',1]]}\n",
                encoding="utf-8",
            )
            bad = subprocess.run(
                [sys.executable, "-B", "-c", probe],
                env={"PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("factorial closure mismatch", bad.stderr)


class FactorialReportTests(unittest.TestCase):
    @staticmethod
    def _write_arm(root: Path, arm: str, *, head: str = "a" * 40, mismatch: bool = False) -> Path:
        opponents = ["arlene", "v1"]
        seeds = [11, 13]
        delta = {"control": 0.0, "carry_095": 10.0, "force_end": 5.0, "both": 25.0}[arm]
        games = []
        for opponent in opponents:
            for seed in seeds:
                for seat in (0, 1):
                    own = 100.0 + delta
                    rival = 80.0
                    scores = [own, rival] if seat == 0 else [rival, own]
                    trace_token = f"{arm}:{opponent}:{seed}:{seat}".encode()
                    games.append(
                        {
                            "opponent": opponent,
                            "seed": seed,
                            "candidate_seat": seat,
                            "status": "complete",
                            "failure": None,
                            "scores": scores,
                            "trace_sha256": hashlib.sha256(trace_token).hexdigest(),
                        }
                    )
        shared_eval = "e" * 64 if not mismatch else ("d" * 64 if arm == "both" else "e" * 64)
        report = {
            "schema_version": 1,
            "operation": factorial_report.OPERATION,
            "status": "complete",
            "arm": arm,
            "seeds": seeds,
            "opponents": opponents,
            "expected_cells": len(games),
            "gate": {"valid": True, "errors": [], "accepted": len(games), "expected": len(games)},
            "identity": {
                "operation": factorial_report.OPERATION,
                "arm": arm,
                "git_head": head,
                "engine_ref": "engine",
                "evaluator_source_sha256": "s" * 64,
                "evaluator_effective_sha256": shared_eval,
                "loader_sha256": "l" * 64,
                "opponent_entry_sha256": {"arlene": "1" * 64, "v1": "2" * 64},
                "entry_sha256": hashlib.sha256((arm + "entry").encode()).hexdigest(),
                "closure": {"sha256": hashlib.sha256((arm + "closure").encode()).hexdigest()},
                "materialization_receipt_sha256": hashlib.sha256((arm + "receipt").encode()).hexdigest(),
            },
            "games": games,
        }
        path = root / f"{arm}.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        return path

    def test_factorial_effects_and_selection_are_mathematically_correct(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {arm: self._write_arm(root, arm) for arm in factorial_report.ARMS}
            report = factorial_report.build_report(paths, head="a" * 40, draws=200)
            self.assertEqual(report["status"], "complete")
            self.assertEqual(report["selection"]["selected_arm"], "both")
            self.assertEqual(report["selection"]["decision"], "SCREEN_KEEP_BOTH")
            self.assertAlmostEqual(
                report["factor_effects"]["carry_main"]["group_own_effect"]["mean"], 15.0
            )
            self.assertAlmostEqual(
                report["factor_effects"]["force_end_main"]["group_own_effect"]["mean"], 10.0
            )
            self.assertAlmostEqual(
                report["factor_effects"]["interaction"]["group_own_effect"]["mean"], 10.0
            )
            self.assertEqual(report["design"]["cells"], 8)
            self.assertEqual(report["design"]["groups"], 4)

    def test_cross_arm_evaluator_drift_is_invalid(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                arm: self._write_arm(root, arm, mismatch=True)
                for arm in factorial_report.ARMS
            }
            with self.assertRaisesRegex(RuntimeError, "cross-arm provenance mismatch"):
                factorial_report.build_report(paths, head="a" * 40, draws=10)

    def test_missing_cell_is_invalid_even_when_arm_gate_claims_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {arm: self._write_arm(root, arm) for arm in factorial_report.ARMS}
            payload = json.loads(paths["force_end"].read_text(encoding="utf-8"))
            payload["games"].pop()
            paths["force_end"].write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "accepted games"):
                factorial_report.build_report(paths, head="a" * 40, draws=10)

    def test_bootstrap_is_deterministic(self):
        first = factorial_report.bootstrap_mean_ci([1.0, 2.0, 8.0], draws=100, seed=7)
        second = factorial_report.bootstrap_mean_ci([1.0, 2.0, 8.0], draws=100, seed=7)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
