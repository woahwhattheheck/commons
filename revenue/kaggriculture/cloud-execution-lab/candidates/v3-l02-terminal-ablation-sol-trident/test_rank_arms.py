# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import rank_arms
from ablation import ARMS


def digest(label):
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def report(arm, own, margin, worst=-20, changed=4):
    opponents = ["arlene", "v1"]
    expected = 4
    candidate = digest("candidate:" + arm)
    canonical = digest("canonical")
    evaluator = digest("evaluator")
    loader = digest("loader")
    opponent_evidence = {
        name: {"path": f"/{name}.py", "sha256": digest("opponent:" + name)}
        for name in opponents
    }
    context = {
        "opponents": opponent_evidence,
        "engine_sha256": digest("engine"),
        "loader_sha256": loader,
        "evaluator_sha256": evaluator,
        "limits": {"action_timeout": 1.0, "startup_timeout": 15.0,
                   "game_timeout": 180.0},
    }

    def gate(agent_digest):
        return {
            "valid": True,
            "errors": [],
            "expected": expected,
            "accepted": expected,
            "provenance": [{"shard": 0, "candidate": {"sha256": agent_digest}, **context}],
        }

    per = {
        "arlene": {"mean_own_delta": worst},
        "v1": {"mean_own_delta": own},
    }
    sha = {
        "candidate": candidate,
        "overlay": digest("overlay"),
        "canonical_main": canonical,
        "candidate_base": digest("candidate_base"),
        "ablation": digest("ablation"),
        "titan_runtime": digest("titan_runtime"),
        "frozen_selected": digest("frozen_selected"),
        "scheduler": digest("scheduler"),
        "config": digest("config"),
        "source_manifest": digest("source_manifest"),
        "evaluator": evaluator,
        "evaluator_source": digest("evaluator_source"),
        "loader": loader,
    }
    return {
        "status": "complete",
        "identity": {
            "git_head": "a" * 40,
            "sha256": sha,
            "opponent_entries": {name: evidence["sha256"]
                                 for name, evidence in opponent_evidence.items()},
            "opponent_bundles": {name: {"sha256": digest("bundle:" + name)}
                                 for name in opponents},
            "ablation_arm": arm,
            "ablation_bundle": {"sha256": digest("ablation_bundle"), "files": 12},
        },
        "seeds": [1],
        "opponents": opponents,
        "expected_cells_per_variant": expected,
        "summary": {"mean_own_delta": own, "mean_margin_delta": margin,
                    "min_own_delta": worst, "cells": expected,
                    "trace_changed_cells": changed},
        "per_opponent": per,
        "baseline_gate": gate(canonical),
        "candidate_gate": gate(candidate),
    }


def complete_reports(*, positive_arm="once_all", own=3, margin=1):
    reports = []
    for arm in ARMS:
        values = (own, margin) if arm == positive_arm else (-2, 8)
        reports.append(report(arm, *values))
    return reports


class RankTests(unittest.TestCase):
    def write(self, root, name, value):
        path = root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def paths(self, root, reports):
        return [self.write(root, f"{index}.json", value)
                for index, value in enumerate(reports)]

    def test_positive_bounded_arm_requires_full_panel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = rank_arms.rank(self.paths(root, complete_reports()))
        self.assertEqual(result["decision"], "FULL_PANEL_REQUIRED")
        self.assertEqual(result["recommended_arm"], "once_all")
        self.assertEqual(set(result["screen_identity"]["candidate_entry_sha256"]), set(ARMS))

    def test_margin_only_denial_does_not_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = [report(arm, -1, 100) for arm in ARMS]
            result = rank_arms.rank(self.paths(root, reports))
        self.assertEqual(result["decision"], "NO_ARM_SURVIVES_SCREEN")
        self.assertIsNone(result["recommended_arm"])

    def test_grid_drift_and_duplicate_json_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = complete_reports()
            reports[1]["seeds"] = [2]
            with self.assertRaisesRegex(ValueError, "immutable screen grid"):
                rank_arms.rank(self.paths(root, reports))
            bad = root / "bad.json"
            bad.write_text('{"status":"complete","status":"complete"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                rank_arms.load_report(bad)

    def test_missing_arm_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "incomplete arm set"):
                rank_arms.rank(self.paths(root, complete_reports()[:-1]))

    def test_duplicate_candidate_closure_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = complete_reports()
            duplicate = reports[0]["identity"]["sha256"]["candidate"]
            reports[1]["identity"]["sha256"]["candidate"] = duplicate
            reports[1]["candidate_gate"]["provenance"][0]["candidate"]["sha256"] = duplicate
            with self.assertRaisesRegex(ValueError, "same candidate entry digest"):
                rank_arms.rank(self.paths(root, reports))

    def test_dependency_closure_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = complete_reports()
            reports[2]["identity"]["sha256"]["scheduler"] = digest("other scheduler")
            with self.assertRaisesRegex(ValueError, "one dependency closure"):
                rank_arms.rank(self.paths(root, reports))

    def test_execution_context_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = complete_reports()
            for gate in ("baseline_gate", "candidate_gate"):
                reports[3][gate]["provenance"][0]["engine_sha256"] = digest("other engine")
            with self.assertRaisesRegex(ValueError, "one execution context"):
                rank_arms.rank(self.paths(root, reports))

    def test_agent_provenance_and_gate_completeness_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = complete_reports()
            reports[1]["candidate_gate"]["provenance"][0]["candidate"]["sha256"] = digest("wrong")
            with self.assertRaisesRegex(ValueError, "agent digest drift"):
                rank_arms.rank(self.paths(root, reports))
            reports = complete_reports()
            reports[1]["candidate_gate"]["accepted"] = 3
            with self.assertRaisesRegex(ValueError, "incomplete candidate_gate"):
                rank_arms.rank(self.paths(root, reports))

    def test_cell_and_opponent_coverage_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = complete_reports()
            reports[4]["summary"]["cells"] = 3
            with self.assertRaisesRegex(ValueError, "incomplete paired cells"):
                rank_arms.rank(self.paths(root, reports))
            reports = complete_reports()
            reports[4]["per_opponent"].pop("v1")
            with self.assertRaisesRegex(ValueError, "opponent coverage mismatch"):
                rank_arms.rank(self.paths(root, reports))


if __name__ == "__main__":
    unittest.main()
