#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

import check_ledger as C

HERE = Path(__file__).resolve().parent
MASTER = HERE / "GEMINI-ANTIGRAVITY.json"
ADDENDUM = HERE / "ANALYZER-MARGIN-CLIPPING.json"
ROOT = C.find_repo_root(HERE)
ANALYZER = ROOT / "revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/agent-index-predictability/analyze_agent_index.py"

spec = importlib.util.spec_from_file_location("agent_index_addendum", ANALYZER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class AnalyzerMarginClippingCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master = load_json(MASTER)
        cls.addendum = load_json(ADDENDUM)
        cls.entry = cls.addendum["entry"]

    def test_master_remains_valid_and_addendum_closes_unique_22nd_proposition(self):
        result = C.validate_path(MASTER, ROOT)
        self.assertEqual(result["status"], "PASS")
        master_ids = [entry["id"] for entry in self.master["entries"]]
        self.assertEqual(len(master_ids), 21)
        self.assertNotIn(self.entry["id"], master_ids)
        combined = master_ids + [self.entry["id"]]
        self.assertEqual(len(combined), 22)
        self.assertEqual(len(set(combined)), 22)

    def test_addendum_pins_direct_antigravity_provenance_and_falsifier(self):
        self.assertEqual(
            self.addendum["schema"],
            "titan-v4-gemini-antigravity-convergence-addendum/v1",
        )
        self.assertEqual(self.entry["id"], "gemini.analyzer-margin-clipping")
        self.assertEqual(self.entry["origin_buckets"], ["pre_manifest_antigravity"])
        self.assertEqual(self.entry["source_slack_ts"], "1789183123.191849")
        self.assertEqual(self.entry["disposition"], "CORRECTED_DESCENDANT")
        self.assertEqual(self.entry["activation"], "RESEARCH_ONLY")
        self.assertEqual(self.entry["provenance_pull_numbers"], [12741])
        self.assertEqual(self.entry["rejected_universal_abs_margin_cap"], 65000)
        self.assertEqual(self.entry["counterexample_legitimate_margin"], 165022)
        self.assertEqual(self.entry["counterexample_seed"], 9922023)
        self.assertIs(self.entry["do_not_repeat_without_new_evidence"], True)

    def test_addendum_evidence_is_current_regular_v4_source(self):
        expected = {
            "revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/agent-index-predictability/analyze_agent_index.py",
            "revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/agent-index-predictability/test_agent_index.py",
        }
        self.assertEqual(set(self.entry["canonical_evidence"]), expected)
        for rel in self.entry["canonical_evidence"]:
            C._regular_file_under_v4(ROOT, rel, self.entry["id"])

    def test_legitimate_165022_margin_survives_without_guessed_default_ceiling(self):
        record = {
            "seed": 9922023,
            "opponent": "starter",
            "seat": 0,
            "rewards": [168572, 3550],
        }
        normalized = mod.normalize_record(record, 0)
        self.assertEqual(normalized["margin"], 165022)

    def test_universal_65000_is_not_silently_reintroduced(self):
        record = {
            "seed": 9922023,
            "opponent": "starter",
            "seat": 0,
            "rewards": [168572, 3550],
        }
        accepted = mod.normalize_record(record, 0, authenticated_max_abs_margin=200000)
        self.assertEqual(accepted["margin"], 165022)
        with self.assertRaises(mod.DataError):
            mod.normalize_record(record, 0, authenticated_max_abs_margin=65000)

    def test_untrusted_margin_only_input_can_be_rejected_without_a_score_cap(self):
        poison = {"seed": 1, "opponent": "A", "seat": 0, "margin": 1e300}
        self.assertEqual(mod.normalize_record(poison, 0)["margin"], 1e300)
        with self.assertRaises(mod.DataError):
            mod.normalize_record(poison, 0, require_structured_outcome=True)

    def test_authenticated_bound_rejects_instead_of_clipping(self):
        accepted = mod.normalize_record(
            {"seed": 1, "opponent": "A", "seat": 0, "rewards": [999, 0]},
            0,
            authenticated_max_abs_margin=1000,
        )
        self.assertEqual(accepted["margin"], 999)
        with self.assertRaises(mod.DataError):
            mod.normalize_record(
                {"seed": 1, "opponent": "A", "seat": 0, "rewards": [1001, 0]},
                0,
                authenticated_max_abs_margin=1000,
            )

    def test_derived_margin_overflow_fails_closed(self):
        with self.assertRaises(mod.DataError):
            mod.normalize_record(
                {"seed": 1, "opponent": "A", "seat": 0,
                 "rewards": [1e308, -1e308]},
                0,
            )


if __name__ == "__main__":
    unittest.main()
