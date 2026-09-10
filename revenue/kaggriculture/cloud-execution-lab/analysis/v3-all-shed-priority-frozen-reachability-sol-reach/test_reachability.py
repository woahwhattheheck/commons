# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


materialize = load("sol_reach_materialize", HERE / "materialize.py")
analyze = load("sol_reach_analyze", HERE / "analyze.py")


def repository_root() -> Path:
    root = HERE
    while root != root.parent:
        if (root / "revenue/kaggriculture/cloud-execution-lab/exports/titan-current.tar.gz").is_file():
            return root
        root = root.parent
    raise RuntimeError("repository root not found")


def game(seed: int, seat: int, own: float, rival: float, action: str, trace: str):
    scores = [0.0, 0.0]
    scores[seat] = own
    scores[1 - seat] = rival
    return {
        "seed": seed,
        "candidate_seat": seat,
        "opponent": "arlene",
        "status": "complete",
        "failure": None,
        "steps": 719,
        "episode_steps": 720,
        "candidate_action_count": 719,
        "candidate_action_sha256": action * 64,
        "trace_sha256": trace * 64,
        "scores": scores,
    }


def panel(delta_seed: int | None = None, own_delta: float = 0, rival_delta: float = 0):
    games = []
    for seed in analyze.EXPECTED_SEEDS:
        for seat in (0, 1):
            changed = seed == delta_seed
            games.append(
                game(
                    seed,
                    seat,
                    100.0 + (own_delta if changed else 0),
                    90.0 + (rival_delta if changed else 0),
                    "b" if changed else "a",
                    "d" if changed else "c",
                )
            )
    return {
        "candidate": {
            "entry": "main.py",
            "callable": "agent",
            "sha256": analyze.EXPECTED_MAIN_SHA256,
        },
        "opponents": {
            "arlene": {
                "entry": "arlene.py",
                "callable": "agent",
                "sha256": analyze.EXPECTED_OPPONENT_SHA256,
            }
        },
        "seeds": list(analyze.EXPECTED_SEEDS),
        "agent_rng_seed": 20260909,
        "engine_ref": "engine",
        "engine_sha256": {"engine.py": "e" * 64},
        "loader_sha256": "l" * 64,
        "evaluator_sha256": "v" * 64,
        "platform": "linux",
        "limits": {"action_rpc_seconds": 1.0},
        "method": "test",
        "games": games,
    }


class ReachabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive = (
            repository_root()
            / "revenue/kaggriculture/cloud-execution-lab/exports/titan-current.tar.gz"
        )

    def test_exact_current_archive_and_call_path(self):
        members, manifest = materialize._read_archive(self.archive)
        receipt = materialize._bind_live_path(members)
        self.assertEqual(len(manifest["runtime"]), 109)
        self.assertEqual(receipt["consumer"], "frozen")
        self.assertTrue(all(receipt["checks"].values()))

    def test_three_arm_materialization_is_one_factor(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "arms"
            receipt = materialize.materialize(self.archive, output)
            self.assertEqual(
                receipt["variants"]["scheduler_only"]["changed_from_control"],
                ["scheduler.py"],
            )
            self.assertEqual(
                receipt["variants"]["frozen_priority"]["changed_from_control"],
                ["frozen_selected.py"],
            )
            self.assertEqual(
                receipt["variants"]["scheduler_only"]["frozen_selected_sha256"],
                materialize.EXPECTED_FROZEN_SHA256,
            )
            self.assertEqual(
                receipt["variants"]["frozen_priority"]["scheduler_sha256"],
                materialize.EXPECTED_SCHEDULER_SHA256,
            )

    def test_priority_changes_only_order_not_domain_or_quantity(self):
        products = ("CARROT", "TOMATO", "STRAWBERRY", "MILK")
        shed = {"CARROT": 0, "TOMATO": 3, "STRAWBERRY": 4, "MILK": 2}
        pending = {"MILK": 1, "UNKNOWN": 9}
        baseline = {"STRAWBERRY": 4, "TOMATO": 1}
        control = materialize.control_targets(products, shed)
        priority = materialize.priority_targets(products, pending, baseline, shed)
        self.assertEqual(priority, {"MILK": 2, "STRAWBERRY": 4, "TOMATO": 3})
        self.assertEqual(dict(priority), {key: control[key] for key in priority})
        self.assertEqual(set(priority), set(control))

    def test_scheduler_predecessor_is_classified_dormant(self):
        control = panel()
        predecessor = copy.deepcopy(control)
        result = analyze.compare(control, predecessor)
        self.assertEqual(result["summary"]["action_changed_cells"], 0)
        self.assertEqual(result["summary"]["score_changed_cells"], 0)

    def test_live_negative_mirrored_cells_fail_admission(self):
        control = panel()
        candidate = panel(delta_seed=2609097304, own_delta=-6, rival_delta=33)
        result = analyze.compare(control, candidate)
        summary = result["summary"]
        self.assertEqual(summary["action_changed_cells"], 2)
        self.assertEqual(summary["negative_own_cells"], 2)
        self.assertEqual(summary["mean_own_delta"], -0.75)
        self.assertEqual(summary["mean_margin_delta"], -4.875)

    def test_duplicate_or_partial_grid_fails_closed(self):
        duplicate = panel()
        duplicate["games"].append(copy.deepcopy(duplicate["games"][0]))
        with self.assertRaises(analyze.AnalysisError):
            analyze._games(duplicate)
        partial = panel()
        partial["games"].pop()
        with self.assertRaises(analyze.AnalysisError):
            analyze._games(partial)

    def test_retained_report_is_exact_rejection(self):
        report = json.loads((HERE / "CURRENT-ARLENE-REPORT.json").read_text())
        self.assertEqual(
            report["classification"],
            "SCHEDULER_PREDECESSOR_DORMANT__REJECT_LIVE_FACTOR",
        )
        self.assertTrue(report["scheduler_only"]["dormant"])
        frozen = report["frozen_priority"]
        self.assertFalse(frozen["admitted"])
        self.assertEqual(frozen["summary"]["action_changed_cells"], 2)
        self.assertEqual(frozen["summary"]["negative_own_cells"], 2)
        self.assertEqual(frozen["summary"]["min_own_delta"], -6.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
