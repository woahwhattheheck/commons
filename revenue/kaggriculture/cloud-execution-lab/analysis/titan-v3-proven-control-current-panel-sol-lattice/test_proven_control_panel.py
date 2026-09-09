# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import subprocess
import tempfile
import unittest

import proven_control_panel as panel


class ComparisonContractTests(unittest.TestCase):
    @staticmethod
    def cells(value_by_joint, margin_offset=0.0, trace_prefix="base"):
        rows = {}
        for opponent in panel.EXPECTED_OPPONENTS:
            for seed in panel.EXPECTED_SEEDS:
                for seat in panel.EXPECTED_SEATS:
                    value = float(value_by_joint[(opponent, seat)])
                    own = 1000.0 + value
                    rival = 900.0 - margin_offset
                    key = (opponent, seed, seat)
                    rows[key] = {
                        "opponent": opponent,
                        "seed": seed,
                        "candidate_seat": seat,
                        "own_cash": own,
                        "rival_cash": rival,
                        "margin": own - rival,
                        "outcome": "W" if own > rival else "L" if own < rival else "T",
                        "trace_sha256": (trace_prefix + f"-{opponent}-{seed}-{seat}").encode().hex().ljust(64, "0")[:64],
                        "steps": panel.EXPECTED_ACTIONS,
                        "episode_steps": panel.EXPECTED_EPISODE_STEPS,
                    }
        return rows

    def test_positive_marginals_cannot_mask_negative_opponent_seat(self):
        zero = {(opponent, seat): 0.0 for opponent in panel.EXPECTED_OPPONENTS for seat in panel.EXPECTED_SEATS}
        delta = {}
        for opponent in panel.EXPECTED_OPPONENTS:
            delta[(opponent, 0)] = -10.0 if opponent == "arlene" else 30.0
            delta[(opponent, 1)] = 30.0 if opponent == "arlene" else 10.0
        control = self.cells(zero, trace_prefix="control")
        candidate = self.cells(delta, trace_prefix="candidate")
        result = panel.compare_to_control(control, candidate)
        self.assertEqual(result["mean_own_delta"], 17.5)
        self.assertTrue(all(value >= 0 for value in result["per_opponent_mean_own_delta"].values()))
        self.assertEqual(result["per_seat_mean_own_delta"], {"0": 20.0, "1": 15.0})
        self.assertEqual(result["classification"], "REGRESSION_OR_MIXED")
        self.assertEqual(result["negative_opponent_seat_strata"], ["arlene|0"])

    def test_own_cash_ranks_before_margin(self):
        ranking = panel.rank_aggregates({
            "cash": {
                "mean_own_cash": 101.0, "median_own_cash": 100.0,
                "minimum_own_cash": 50.0, "mean_margin": -1000.0,
                "outcomes": {"W": 0, "T": 0, "L": 32},
            },
            "margin": {
                "mean_own_cash": 100.0, "median_own_cash": 100.0,
                "minimum_own_cash": 100.0, "mean_margin": 1000.0,
                "outcomes": {"W": 32, "T": 0, "L": 0},
            },
        })
        self.assertEqual([row["name"] for row in ranking], ["cash", "margin"])

    def test_no_trace_change_is_no_action_signal(self):
        zero = {(opponent, seat): 0.0 for opponent in panel.EXPECTED_OPPONENTS for seat in panel.EXPECTED_SEATS}
        positive = {(opponent, seat): 1.0 for opponent in panel.EXPECTED_OPPONENTS for seat in panel.EXPECTED_SEATS}
        control = self.cells(zero, trace_prefix="same")
        candidate = self.cells(positive, trace_prefix="same")
        # Force exact whole-game trace identity despite synthetic score mutation.
        for key in candidate:
            candidate[key]["trace_sha256"] = control[key]["trace_sha256"]
        result = panel.compare_to_control(control, candidate)
        self.assertEqual(result["classification"], "NO_ACTION_SIGNAL")
        self.assertFalse(result["checks"]["whole_trace_activation_observed"])

    def test_nonfinite_json_is_rejected(self):
        with self.assertRaises(panel.PanelError):
            panel.strict_json_bytes(b'{"x":NaN}', "fixture")

    def test_duplicate_json_key_is_rejected(self):
        with self.assertRaises(panel.PanelError):
            panel.strict_json_bytes(b'{"x":1,"x":2}', "fixture")

    def test_bool_is_not_a_number(self):
        self.assertFalse(panel.is_number(True))
        self.assertFalse(panel.is_number(False))
        self.assertTrue(panel.is_number(1))

    def test_aliasing_closure_ids_are_invalid(self):
        bundles = [
            {"tree": {"sha256": "a" * 64}},
            {"tree": {"sha256": "a" * 64}},
        ]
        self.assertFalse(panel.closures_are_distinct(bundles))
        bundles[1]["tree"]["sha256"] = "b" * 64
        self.assertTrue(panel.closures_are_distinct(bundles))

    def test_panel_checkout_scope_rejects_nonlane_commit(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        repo = Path(temporary.name)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Panel Test"], check=True)
        (repo / "base.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
        base = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        lane_file = repo / panel.LANE_PREFIX / "panel.py"
        lane_file.parent.mkdir(parents=True)
        lane_file.write_text("pass\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "lane"], check=True)
        lane_head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        original_base = panel.PANEL_BASE_COMMIT
        panel.PANEL_BASE_COMMIT = base
        try:
            self.assertEqual(panel.verify_panel_checkout(repo, lane_head), [panel.LANE_PREFIX + "panel.py"])
            (repo / "outside.txt").write_text("forbidden\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "outside"], check=True)
            outside_head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            with self.assertRaisesRegex(panel.PanelError, "outside lane"):
                panel.verify_panel_checkout(repo, outside_head)
        finally:
            panel.PANEL_BASE_COMMIT = original_base

    def test_reused_evaluator_invocation_invalidates_complete_arms(self):
        evaluator_sha = "e" * 64
        loader_sha = "d" * 64
        opponent_sha = {name: format(index + 1, "064x") for index, name in enumerate(panel.EXPECTED_OPPONENTS)}
        engine_sha = "c" * 64
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        bundles = []
        executions = []
        for index, name in enumerate(("frozen-v3", "current-canonical", "submitted-v1", "submitted-v2")):
            entry = root / f"{name}.py"
            entry.write_text(f"# {name}\n", encoding="utf-8")
            bundle = {
                "name": name,
                "role": "control" if name == "frozen-v3" else "candidate",
                "entry": entry,
                "tree": {"files": 1, "sha256": format(index + 10, "064x"), "entries": []},
                "source_receipt": {"name": name},
                "archive": None,
            }
            games = []
            for opponent in panel.EXPECTED_OPPONENTS:
                for seed in panel.EXPECTED_SEEDS:
                    for seat in panel.EXPECTED_SEATS:
                        games.append({
                            "opponent": opponent,
                            "seed": seed,
                            "candidate_seat": seat,
                            "scores": [1000 + index, 900],
                            "status": "complete",
                            "failure": None,
                            "episode_steps": panel.EXPECTED_EPISODE_STEPS,
                            "steps": panel.EXPECTED_ACTIONS,
                            "trace_sha256": hashlib.sha256(
                                f"{name}:{opponent}:{seed}:{seat}".encode()
                            ).hexdigest(),
                        })
            report = {
                "schema_version": 1,
                "seeds": list(panel.EXPECTED_SEEDS),
                "agent_rng_seed": panel.AGENT_RNG_SEED,
                "evaluator_sha256": evaluator_sha,
                "loader_sha256": loader_sha,
                "candidate": {"sha256": panel.sha256_file(entry)},
                "opponents": {key: {"sha256": value} for key, value in opponent_sha.items()},
                "progress": {"state": "complete"},
                "games": games,
                "invocation_id": "reused-invocation",
                "engine_ref": "exact-test-engine",
                "engine_sha256": engine_sha,
                "limits": {"action": 1.0},
                "method": {"paired": True},
            }
            bundles.append(bundle)
            executions.append({"name": name, "returncode": 0, "report": report})

        result = panel.build_report(
            bundles,
            executions,
            evaluator_sha256=evaluator_sha,
            loader_sha256=loader_sha,
            opponent_sha256=opponent_sha,
            panel_base_commit=panel.PANEL_BASE_COMMIT,
            panel_head="f" * 40,
            panel_paths=[panel.LANE_PREFIX + "proven_control_panel.py"],
            current_commit=panel.CURRENT_COMMIT,
        )
        self.assertEqual(result["decision"], "INVALID")
        self.assertFalse(result["custody"]["invocation_ids_distinct"])
        self.assertIn("missing or reused evaluator invocation ID", result["errors"])


if __name__ == "__main__":
    unittest.main()
