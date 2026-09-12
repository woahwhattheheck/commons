#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import unittest

import check_ledger as C

HERE = Path(__file__).resolve().parent
MASTER = HERE / "GEMINI-ANTIGRAVITY.json"
ANALYZER_ADDENDUM = HERE / "ANALYZER-MARGIN-CLIPPING.json"
TERMINAL_ADDENDUM = HERE / "TERMINAL-MASS-HIRE.json"
ROOT = C.find_repo_root(HERE)
TERMINAL_RECEIPT = ROOT / "revenue/kaggriculture/cloud-execution-lab/candidates/v4/repairs/gameplay/terminal-labor-surge/RECEIPT.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class TerminalMassHireCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master = load_json(MASTER)
        cls.analyzer = load_json(ANALYZER_ADDENDUM)["entry"]
        cls.addendum = load_json(TERMINAL_ADDENDUM)
        cls.entry = cls.addendum["entry"]
        cls.receipt = load_json(TERMINAL_RECEIPT)

    def test_two_omitted_addenda_extend_master_to_23_unique_propositions(self):
        result = C.validate_path(MASTER, ROOT)
        self.assertEqual(result["status"], "PASS")
        master_ids = [entry["id"] for entry in self.master["entries"]]
        self.assertEqual(len(master_ids), 21)
        combined = master_ids + [self.analyzer["id"], self.entry["id"]]
        self.assertEqual(len(combined), 23)
        self.assertEqual(len(set(combined)), 23)
        self.assertNotIn(self.entry["id"], master_ids)

    def test_direct_antigravity_provenance_and_corrected_disposition_are_pinned(self):
        self.assertEqual(
            self.addendum["schema"],
            "titan-v4-gemini-antigravity-convergence-addendum/v1",
        )
        self.assertEqual(self.entry["id"], "gemini.terminal-mass-hire")
        self.assertEqual(self.entry["source_slack_ts"], "1789183677.274829")
        self.assertEqual(self.entry["origin_buckets"], ["pre_manifest_antigravity"])
        self.assertEqual(self.entry["disposition"], "CORRECTED_DESCENDANT")
        self.assertEqual(self.entry["activation"], "DEFAULT_OFF")
        self.assertEqual(self.entry["provenance_pull_numbers"], [12796])
        self.assertIs(self.entry["do_not_repeat_without_new_evidence"], True)

    def test_corrected_engine_contract_kills_blind_mass_hire(self):
        self.assertEqual(self.entry["corrected_sixteen_total_hires_cost"], 2583)
        self.assertIs(self.entry["terminal_reward_is_cash_only"], True)
        self.assertIs(self.entry["blind_mass_hire_supported"], False)
        arithmetic = self.receipt["engine"]["corrected_mass_hire_arithmetic"]
        self.assertEqual(arithmetic["sixteen_total_hires_cost"], 2583)
        self.assertEqual(arithmetic["remaining_cost_after_one_existing_hire"], 2582)
        self.assertIn(
            "terminal_reward_is_farm_money_only",
            self.receipt["engine"]["verified_contract"],
        )

    def test_terminal_descendant_remains_default_off_and_nonproduction(self):
        activation = self.receipt["activation"]
        self.assertIs(activation["production_source_modified"], False)
        self.assertIs(activation["feature_default_modified"], False)
        self.assertIs(activation["archive_or_kaggle_modified"], False)

    def test_all_terminal_evidence_resolves_as_current_regular_v4_files(self):
        for rel in self.entry["canonical_evidence"]:
            C._regular_file_under_v4(ROOT, rel, self.entry["id"])


if __name__ == "__main__":
    unittest.main()
