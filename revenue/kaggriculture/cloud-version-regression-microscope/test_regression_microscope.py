from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import regression_microscope as rm


ENGINE = "e" * 64
OPPONENT = "o" * 64


def action(name: str, quantity: int = 1):
    return [{"type": name, "product": "WHEAT", "quantity": quantity}]


def hashlib_seed(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode()).hexdigest()


def identity(label: str, config=None, *, config_text=None):
    result = {
        "source_sha256": (label[0] if label else "s") * 64,
        "archive_sha256": (label[-1] if label else "a") * 64,
        "config_sha256": hashlib_seed(label),
    }
    if config is not None or config_text is not None:
        if config_text is None:
            config_text = json.dumps(config, separators=(",", ":"), sort_keys=True)
        result["config_text"] = config_text
        import hashlib

        result["config_sha256"] = hashlib.sha256(config_text.encode()).hexdigest()
    return result


def cell(
    *,
    opponent="Arlene",
    seed=1,
    seat=0,
    actions=None,
    own=100,
    rival=90,
    world="w1",
    trace="t1",
    engine=ENGINE,
    opponent_sha=OPPONENT,
    state="complete",
    phase="finalize",
):
    actions = actions if actions is not None else [action("WAIT")] * 5
    return {
        "opponent": opponent,
        "seed": seed,
        "seat": seat,
        "state": state,
        "phase": phase,
        "engine_sha256": engine,
        "opponent_sha256": opponent_sha,
        "tested_seat_actions": copy.deepcopy(actions),
        "tested_action_sha256": rm.action_sequence_digest(actions),
        "terminal": {
            "own_cash": own,
            "rival_cash": rival,
            "terminal_world_sha256": world,
            "full_trace_sha256": trace,
        },
    }


def version(label, cells, *, config=None, config_text=None):
    return {
        "identity": identity(label, config, config_text=config_text),
        "cells": cells,
    }


def dataset(versions, *, three_way=None, feature_arms=None):
    value = {
        "schema": rm.SCHEMA,
        "expected_action_count": 5,
        "versions": versions,
    }
    if three_way is not None:
        value["three_way"] = three_way
    if feature_arms is not None:
        value["feature_arms"] = feature_arms
    return value


class RegressionMicroscopeTests(unittest.TestCase):
    def test_three_way_localises_middle_harm_and_candidate_repair(self):
        a0 = [action("WAIT")] * 5
        a1 = copy.deepcopy(a0)
        a1[2] = action("BUY_PRODUCT", 3)
        a2 = copy.deepcopy(a0)
        a2[2] = action("SELL", 2)
        raw = dataset(
            {
                "v1": version("v1", [cell(actions=a0, own=100, rival=90, world="w1", trace="t1")]),
                "v2": version("v2", [cell(actions=a1, own=80, rival=95, world="w2", trace="t2")]),
                "v3": version("v3", [cell(actions=a2, own=110, rival=90, world="w3", trace="t3")]),
            },
            three_way=["v1", "v2", "v3"],
        )
        report = rm.build_report(raw)
        attribution = report["three_way"]["attribution"]
        self.assertEqual(attribution["middle_regression_cells"], ["Arlene|seed=1|seat=0"])
        self.assertEqual(attribution["candidate_repaired_cells"], ["Arlene|seed=1|seat=0"])
        self.assertEqual(attribution["candidate_unrepaired_cells"], [])
        cluster = attribution["harmful_first_divergence_clusters"][0]
        self.assertIn("step=2", cluster["signature"])
        self.assertIn("BUY_PRODUCT", cluster["signature"])

    def test_action_identical_score_drift_is_invalid_not_gain(self):
        actions = [action("WAIT")] * 5
        raw = dataset(
            {
                "base": version("base", [cell(actions=actions, own=100, rival=90, world="w", trace="t")]),
                "candidate": version("candidate", [cell(actions=actions, own=120, rival=90, world="w2", trace="t2")]),
            }
        )
        comparison = rm.build_report(raw)["comparison"]
        row = comparison["cells"][0]
        self.assertEqual(row["classification"], "invalid_confounded")
        self.assertIn("action_identical_own_cash_drift", row["causality_issues"])
        self.assertEqual(comparison["summary"]["promotion_verdict"], "INVALID")

    def test_rival_only_trace_drift_cannot_count_as_activation(self):
        actions = [action("WAIT")] * 5
        raw = dataset(
            {
                "base": version("base", [cell(actions=actions, trace="trace-a")]),
                "candidate": version("candidate", [cell(actions=actions, trace="trace-b")]),
            }
        )
        row = rm.build_report(raw)["comparison"]["cells"][0]
        self.assertFalse(row["action_changed"])
        self.assertEqual(row["classification"], "invalid_confounded")
        self.assertIn("action_identical_full_trace_drift", row["causality_issues"])

    def test_own_down_rival_down_more_is_objective_conflict(self):
        base_actions = [action("WAIT")] * 5
        candidate_actions = copy.deepcopy(base_actions)
        candidate_actions[1] = action("SELL", 1)
        raw = dataset(
            {
                "base": version("base", [cell(actions=base_actions, own=100, rival=100, world="a", trace="a")]),
                "candidate": version("candidate", [cell(actions=candidate_actions, own=90, rival=50, world="b", trace="b")]),
            }
        )
        comparison = rm.build_report(raw)["comparison"]
        row = comparison["cells"][0]
        self.assertEqual(row["classification"], "objective_conflict")
        self.assertEqual(row["delta"]["own_cash"], -10)
        self.assertEqual(row["delta"]["margin"], 40)
        self.assertNotEqual(comparison["summary"]["promotion_verdict"], "ADVANCE")

    def test_cross_cell_activation_laundering_fails_closed(self):
        base_actions = [action("WAIT")] * 5
        changed_actions = copy.deepcopy(base_actions)
        changed_actions[0] = action("SELL", 1)
        base_cells = [
            cell(seed=1, actions=base_actions, own=100, rival=90, world="w1", trace="t1"),
            cell(seed=2, actions=base_actions, own=100, rival=90, world="w2", trace="t2"),
        ]
        candidate_cells = [
            cell(seed=1, actions=changed_actions, own=100, rival=90, world="w1b", trace="t1b"),
            cell(seed=2, actions=base_actions, own=500, rival=90, world="w2b", trace="t2b"),
        ]
        comparison = rm.build_report(
            dataset({"base": version("base", base_cells), "candidate": version("candidate", candidate_cells)})
        )["comparison"]
        self.assertEqual(comparison["summary"]["action_changed_cells"], 1)
        self.assertEqual(comparison["summary"]["promotion_verdict"], "INVALID")
        second = next(row for row in comparison["cells"] if row["cell"]["seed"] == 2)
        self.assertIn("action_identical_own_cash_drift", second["causality_issues"])

    def test_action_change_requires_full_trace_change(self):
        base_actions = [action("WAIT")] * 5
        candidate_actions = copy.deepcopy(base_actions)
        candidate_actions[4] = action("SELL", 2)
        raw = dataset(
            {
                "base": version("base", [cell(actions=base_actions, trace="same", world="a")]),
                "candidate": version("candidate", [cell(actions=candidate_actions, trace="same", world="b")]),
            }
        )
        row = rm.build_report(raw)["comparison"]["cells"][0]
        self.assertEqual(row["classification"], "invalid_confounded")
        self.assertIn("action_changed_but_full_trace_identical", row["causality_issues"])

    def test_exact_returned_action_cardinality_is_required(self):
        raw = dataset(
            {
                "base": version("base", [cell(actions=[action("WAIT")] * 4)]),
                "candidate": version("candidate", [cell(actions=[action("WAIT")] * 5)]),
            }
        )
        with self.assertRaisesRegex(rm.MicroscopeError, "exactly 5 returned actions"):
            rm.build_report(raw)

    def test_declared_action_digest_must_match(self):
        raw_cell = cell()
        raw_cell["tested_action_sha256"] = "bad"
        raw = dataset(
            {
                "base": version("base", [raw_cell]),
                "candidate": version("candidate", [cell()]),
            }
        )
        with self.assertRaisesRegex(rm.MicroscopeError, "does not match"):
            rm.build_report(raw)

    def test_grid_must_match_exactly(self):
        raw = dataset(
            {
                "base": version("base", [cell(seed=1), cell(seed=2)]),
                "candidate": version("candidate", [cell(seed=1)]),
            }
        )
        with self.assertRaisesRegex(rm.MicroscopeError, "grid mismatch"):
            rm.build_report(raw)

    def test_duplicate_cell_is_rejected(self):
        duplicate = cell(seed=1)
        raw = dataset(
            {
                "base": version("base", [duplicate, copy.deepcopy(duplicate)]),
                "candidate": version("candidate", [cell(seed=1)]),
            }
        )
        with self.assertRaisesRegex(rm.MicroscopeError, "duplicate cell"):
            rm.build_report(raw)

    def test_engine_or_opponent_mismatch_is_invalid(self):
        base_actions = [action("WAIT")] * 5
        candidate_actions = copy.deepcopy(base_actions)
        candidate_actions[2] = action("SELL")
        raw = dataset(
            {
                "base": version("base", [cell(actions=base_actions, engine="e1", trace="a")]),
                "candidate": version("candidate", [cell(actions=candidate_actions, engine="e2", trace="b")]),
            }
        )
        row = rm.build_report(raw)["comparison"]["cells"][0]
        self.assertIn("engine_sha256_mismatch", row["causality_issues"])
        self.assertEqual(row["classification"], "invalid_confounded")

    def test_new_loss_blocks_promotion_even_with_positive_own_cash(self):
        base_actions = [action("WAIT")] * 5
        candidate_actions = copy.deepcopy(base_actions)
        candidate_actions[3] = action("BUY_PRODUCT", 2)
        raw = dataset(
            {
                "base": version("base", [cell(actions=base_actions, own=100, rival=90, world="a", trace="a")]),
                "candidate": version("candidate", [cell(actions=candidate_actions, own=110, rival=120, world="b", trace="b")]),
            }
        )
        comparison = rm.build_report(raw)["comparison"]
        self.assertEqual(comparison["summary"]["new_losses"], 1)
        self.assertEqual(comparison["summary"]["promotion_verdict"], "REGRESSION")

    def test_feature_surgery_recommends_disable_only_on_action_bound_own_gain(self):
        base_actions = [action("WAIT")] * 5
        disabled_actions = copy.deepcopy(base_actions)
        disabled_actions[2] = action("SELL", 3)
        control_config = {"features": {"x": True, "y": True}}
        raw = dataset(
            {
                "all": version("all", [cell(actions=base_actions, own=100, rival=90, world="a", trace="a")], config=control_config),
                "no_x": version("no_x", [cell(actions=disabled_actions, own=110, rival=90, world="b", trace="b")], config={"features": {"x": False, "y": True}}),
            },
            feature_arms={
                "control": "all",
                "canonical_control_config_sha256": identity("all", control_config)["config_sha256"],
                "disabled": {"x": "no_x"},
            },
        )
        recommendation = rm.build_report(raw)["feature_surgery"]["recommendations"][0]
        self.assertEqual(recommendation["recommendation"], "candidate_disable")
        self.assertEqual(recommendation["comparison"]["summary"]["promotion_verdict"], "ADVANCE")

    def test_feature_surgery_keeps_feature_when_disabling_reduces_own_cash(self):
        base_actions = [action("WAIT")] * 5
        disabled_actions = copy.deepcopy(base_actions)
        disabled_actions[2] = action("SELL", 3)
        control_config = {"features": {"x": True, "y": True}}
        raw = dataset(
            {
                "all": version("all", [cell(actions=base_actions, own=100, rival=100, world="a", trace="a")], config=control_config),
                "no_x": version("no_x", [cell(actions=disabled_actions, own=90, rival=50, world="b", trace="b")], config={"features": {"x": False, "y": True}}),
            },
            feature_arms={
                "control": "all",
                "canonical_control_config_sha256": identity("all", control_config)["config_sha256"],
                "disabled": {"x": "no_x"},
            },
        )
        recommendation = rm.build_report(raw)["feature_surgery"]["recommendations"][0]
        self.assertNotEqual(recommendation["recommendation"], "candidate_disable")

    def test_negative_opponent_seat_stratum_blocks_advance(self):
        base_actions = [action("WAIT")] * 5
        changed = copy.deepcopy(base_actions)
        changed[1] = action("SELL", 1)
        base_cells = [
            cell(opponent="A", seed=1, seat=0, actions=base_actions, own=100, rival=90, world="a1", trace="a1"),
            cell(opponent="B", seed=2, seat=1, actions=base_actions, own=100, rival=90, world="a2", trace="a2"),
        ]
        candidate_cells = [
            cell(opponent="A", seed=1, seat=0, actions=changed, own=120, rival=90, world="b1", trace="b1"),
            cell(opponent="B", seed=2, seat=1, actions=changed, own=99, rival=90, world="b2", trace="b2"),
        ]
        comparison = rm.build_report(
            dataset({"base": version("base", base_cells), "candidate": version("candidate", candidate_cells)})
        )["comparison"]
        self.assertNotEqual(comparison["summary"]["promotion_verdict"], "ADVANCE")
        self.assertLess(comparison["summary"]["strata"]["B|seat=1"]["mean_own_cash_delta"], 0)

    def test_feature_arm_with_extra_config_change_is_invalid(self):
        base_actions = [action("WAIT")] * 5
        changed = copy.deepcopy(base_actions)
        changed[1] = action("SELL")
        control_config = {"features": {"x": True, "y": True}, "limit": 4}
        arm_config = {"features": {"x": False, "y": True}, "limit": 5}
        raw = dataset(
            {
                "all": version("all", [cell(actions=base_actions, world="a", trace="a")], config=control_config),
                "no_x": version("no_x", [cell(actions=changed, own=110, world="b", trace="b")], config=arm_config),
            },
            feature_arms={
                "control": "all",
                "canonical_control_config_sha256": identity("all", control_config)["config_sha256"],
                "disabled": {"x": "no_x"},
            },
        )
        item = rm.build_report(raw)["feature_surgery"]["recommendations"][0]
        self.assertEqual(item["recommendation"], "invalid_arm")
        self.assertTrue(item["config_closure_issues"])
        self.assertIn("arm_not_exactly_one_feature_bit", item["config_closure_issues"][0])

    def test_rewritten_all_enabled_control_bytes_are_rejected_for_surgery(self):
        base_actions = [action("WAIT")] * 5
        changed = copy.deepcopy(base_actions)
        changed[1] = action("SELL")
        config = {"features": {"x": True}}
        canonical_text = '{"features":{"x":true}}'
        rewritten_text = json.dumps(config, indent=2, sort_keys=True)
        canonical_sha = __import__("hashlib").sha256(canonical_text.encode()).hexdigest()
        raw = dataset(
            {
                "all": version("all", [cell(actions=base_actions, world="a", trace="a")], config_text=rewritten_text),
                "no_x": version("no_x", [cell(actions=changed, own=110, world="b", trace="b")], config={"features": {"x": False}}),
            },
            feature_arms={
                "control": "all",
                "canonical_control_config_sha256": canonical_sha,
                "disabled": {"x": "no_x"},
            },
        )
        item = rm.build_report(raw)["feature_surgery"]["recommendations"][0]
        self.assertEqual(item["recommendation"], "invalid_arm")
        self.assertIn("all_enabled_control_bytes_not_canonical", item["config_closure_issues"])

    def test_cli_writes_deterministic_json_and_markdown(self):
        base_actions = [action("WAIT")] * 5
        candidate_actions = copy.deepcopy(base_actions)
        candidate_actions[0] = action("SELL", 1)
        raw = dataset(
            {
                "base": version("base", [cell(actions=base_actions, own=100, rival=90, world="a", trace="a")]),
                "candidate": version("candidate", [cell(actions=candidate_actions, own=101, rival=90, world="b", trace="b")]),
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.json"
            json_out = root / "report.json"
            markdown_out = root / "report.md"
            source.write_text(json.dumps(raw), encoding="utf-8")
            rc = rm.main(
                [str(source), "--json-out", str(json_out), "--markdown-out", str(markdown_out)]
            )
            self.assertEqual(rc, 0)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["comparison"]["summary"]["promotion_verdict"], "ADVANCE")
            markdown = markdown_out.read_text(encoding="utf-8")
            self.assertIn("TITAN Version Regression Microscope", markdown)
            self.assertIn("**ADVANCE**", markdown)


if __name__ == "__main__":
    unittest.main()
