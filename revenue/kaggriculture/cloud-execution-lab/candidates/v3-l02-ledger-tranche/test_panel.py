# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import run_panel as panel


def game(opponent, seed, seat, scores, trace):
    return {"opponent": opponent, "seed": seed, "candidate_seat": seat,
            "status": "complete", "failure": None, "scores": scores,
            "trace_sha256": trace * 64}


def result(variant, games, candidate_sha="a" * 64):
    return {"variant": variant, "shard": 0, "returncode": 0,
            "report": {"schema_version": 1, "engine_ref": panel.ENGINE_REF,
                       "progress": {"state": "complete"},
                       "candidate": {"sha256": candidate_sha}, "opponents": {},
                       "engine_sha256": {}, "loader_sha256": "b" * 64,
                       "evaluator_sha256": "c" * 64, "limits": {}, "games": games}}


class PanelValidationTests(unittest.TestCase):
    def test_complete_grid_pairs_exact_cells(self):
        seeds = [1]; opponents = ["arlene"]
        base_games = [game("arlene", 1, 0, [100, 90], "a"),
                      game("arlene", 1, 1, [90, 100], "b")]
        cand_games = [game("arlene", 1, 0, [110, 90], "c"),
                      game("arlene", 1, 1, [90, 110], "d")]
        baseline, gate = panel.collect_games([result("baseline", base_games)],
                                             "baseline", seeds, opponents)
        candidate, cgate = panel.collect_games([result("candidate", cand_games)],
                                                "candidate", seeds, opponents)
        self.assertTrue(gate["valid"] and cgate["valid"])
        rows = panel.pair_games(baseline, candidate)
        summary = panel.summarize(rows)
        self.assertEqual(summary["cells"], 2)
        self.assertEqual(summary["mean_own_delta"], 10)
        self.assertEqual(summary["mean_margin_delta"], 10)
        self.assertEqual(summary["trace_changed_cells"], 2)

    def test_missing_cell_is_invalid_not_silently_averaged(self):
        games = [game("arlene", 1, 0, [100, 90], "a")]
        _, gate = panel.collect_games([result("baseline", games)],
                                      "baseline", [1], ["arlene"])
        self.assertFalse(gate["valid"])
        self.assertTrue(any("missing cells" in error for error in gate["errors"]))

    def test_failed_cell_is_not_accepted(self):
        games = [game("arlene", 1, 0, [100, 90], "a"),
                 {**game("arlene", 1, 1, [90, 100], "b"),
                  "status": "timeout", "failure": "deadline"}]
        accepted, gate = panel.collect_games([result("candidate", games)],
                                             "candidate", [1], ["arlene"])
        self.assertNotIn(("arlene", 1, 1), accepted)
        self.assertFalse(gate["valid"])

    def test_advance_gate_requires_v1_and_arlene(self):
        global_summary = {"trace_changed_cells": 12, "mean_own_delta": 100,
                          "mean_margin_delta": 120}
        strata = {name: {"mean_own_delta": 1} for name in panel.OPPONENTS}
        self.assertEqual(panel.verdict(global_summary, strata)["decision"], "ADVANCE")
        strata["v1"] = {"mean_own_delta": -1}
        self.assertEqual(panel.verdict(global_summary, strata)["decision"], "REJECT")


def _stripped(pythonpath=None, probe="import scheduler"):
    with tempfile.TemporaryDirectory(prefix="kag-eval-agent-") as tmp:
        env = {
            "PATH": os.defpath,
            "HOME": tmp,
            "LANG": "C.UTF-8",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        if pythonpath is not None:
            env["PYTHONPATH"] = pythonpath
        return subprocess.run(
            [sys.executable, "-B", "-c", probe],
            cwd=tmp, env=env, capture_output=True, text=True,
        )


class IsolatedSourcePathTests(unittest.TestCase):
    def test_lab_only_stripped_env_cannot_import_scheduler(self):
        result = _stripped(pythonpath=str(panel.LAB))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("observed_clone", result.stderr)

    def test_source_pythonpath_includes_pulse_and_quickstep(self):
        pythonpath = panel.isolated_source_pythonpath(panel.LAB)
        parts = [Path(item) for item in pythonpath.split(os.pathsep)]
        self.assertIn(panel.LAB.resolve(), parts)
        self.assertIn((panel.KAG / "cloud-runtime-pulse").resolve(), parts)
        self.assertIn((panel.KAG / "cloud-quickstep").resolve(), parts)

    def test_stripped_env_with_source_pythonpath_imports_scheduler(self):
        pythonpath = panel.isolated_source_pythonpath(panel.LAB)
        result = _stripped(pythonpath=pythonpath, probe=panel.ISOLATED_IMPORT_PROBE)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_evaluator_patch_forwards_isolated_pythonpath(self):
        source = (
            "class Actor:\n"
            + panel.EVALUATOR_ENV_SEAM
            + "\n        self.proc = None\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            origin = Path(tmp) / "evaluate.py"
            target = Path(tmp) / "evaluate-l02.py"
            origin.write_text(source, encoding="utf-8")
            panel.patch_evaluator(origin, target)
            text = target.read_text(encoding="utf-8")
            self.assertIn('os.environ.get("TITAN_L02_PYTHONPATH")', text)
            self.assertIn('env["PYTHONPATH"] = os.environ["TITAN_L02_PYTHONPATH"]', text)

    def test_assert_isolated_source_imports_accepts_complete_path(self):
        pythonpath = panel.isolated_source_pythonpath(panel.LAB)
        panel.assert_isolated_source_imports(panel.LAB, pythonpath)

    def test_assert_isolated_source_imports_rejects_lab_only(self):
        with self.assertRaises(RuntimeError) as raised:
            panel.assert_isolated_source_imports(panel.LAB, str(panel.LAB))
        self.assertIn("observed_clone", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
