# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import ablate_runtime_prefix as rpa

REPO = Path(__file__).resolve().parents[6]


def git_show(commit: str, path: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{commit}:{path}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout


class RuntimePrefixAblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v4 = git_show(rpa.V4_SOURCE_COMMIT, rpa.SOURCE_PATH)
        cls.v31 = git_show(rpa.V31_SOURCE_COMMIT, rpa.SOURCE_PATH)
        cls.v4_text = cls.v4.decode("utf-8")
        cls.v31_text = cls.v31.decode("utf-8")
        cls.treatment, cls.receipt = rpa.ablate_submitted_v4(cls.v4, cls.v31)
        cls.treatment_text = cls.treatment.decode("utf-8")

    def test_exact_historical_runtime_authorities(self):
        self.assertEqual(rpa.git_blob_sha1(self.v4), rpa.V4_RUNTIME_GIT_BLOB)
        self.assertEqual(rpa.git_blob_sha1(self.v31), rpa.V31_RUNTIME_GIT_BLOB)
        self.assertEqual(self.receipt["control_source_git_blob"], rpa.V4_RUNTIME_GIT_BLOB)
        self.assertEqual(self.receipt["reference_v31_source_git_blob"], rpa.V31_RUNTIME_GIT_BLOB)

    def test_both_submitted_configs_enable_all_three_wrappers(self):
        for commit in (rpa.V31_SOURCE_COMMIT, rpa.V4_SOURCE_COMMIT):
            cfg = json.loads(git_show(commit, rpa.CONFIG_PATH))
            self.assertIs(cfg["seed"], True)
            self.assertIs(cfg["operating_stock"], True)
            self.assertIs(cfg["redundant_hire"], True)

    def test_rejects_any_source_authority_drift(self):
        bad_v4 = bytearray(self.v4)
        bad_v4[-2] ^= 1
        with self.assertRaises(rpa.SourceAuthorityError):
            rpa.ablate_submitted_v4(bytes(bad_v4), self.v31)
        bad_v31 = bytearray(self.v31)
        bad_v31[-2] ^= 1
        with self.assertRaises(rpa.SourceAuthorityError):
            rpa.ablate_submitted_v4(self.v4, bytes(bad_v31))

    def test_treatment_compiles_and_is_deterministic(self):
        again, receipt = rpa.ablate_submitted_v4(self.v4, self.v31)
        self.assertEqual(again, self.treatment)
        self.assertEqual(receipt, self.receipt)
        compile(self.treatment, "runtime-prefix-treatment", "exec")
        self.assertNotEqual(self.treatment, self.v4)

    def test_only_three_method_spans_change(self):
        self.assertEqual(rpa.skeleton(self.treatment_text), rpa.skeleton(self.v4_text))
        self.assertEqual(self.receipt["target_methods"], list(rpa.TARGET_METHODS))
        for name in rpa.TARGET_METHODS:
            self.assertEqual(
                rpa.method_text(self.treatment_text, name),
                rpa.method_text(self.v31_text, name),
                name,
            )
            self.assertNotEqual(
                rpa.method_text(self.v4_text, name),
                rpa.method_text(self.v31_text, name),
                name,
            )

    def test_seed_method_reverts_full_queue_reasoning(self):
        control = rpa.method_text(self.v4_text, "_seed_selected")
        treatment = rpa.method_text(self.treatment_text, "_seed_selected")
        self.assertIn("prefix = market[:maximum]", control)
        self.assertIn("zip(prefix, proposed['market'][:maximum])", control)
        self.assertIn("for o in prefix[i+1:]", control)
        self.assertNotIn("prefix = market[:maximum]", treatment)
        self.assertIn("zip(selected['market'], proposed['market'])", treatment)
        self.assertIn("for o in selected['market'][i+1:]", treatment)

    def test_operating_stock_method_reverts_full_queue_scope(self):
        control = rpa.method_text(self.v4_text, "_operating_stock_selected")
        treatment = rpa.method_text(self.treatment_text, "_operating_stock_selected")
        self.assertIn("prefix_selected = deepcopy(selected)", control)
        self.assertIn("selected.get('market') or []", control)
        self.assertNotIn("prefix_selected", treatment)
        self.assertIn("for o in selected.get('market', [])", treatment)
        self.assertIn("m, obs, cfg, selected, farm, private", treatment)

    def test_redundant_hire_method_reverts_full_queue_gate(self):
        control = rpa.method_text(self.v4_text, "_redundant_hire_selected")
        treatment = rpa.method_text(self.treatment_text, "_redundant_hire_selected")
        self.assertIn("[:maximum]", control)
        self.assertNotIn("[:maximum]", treatment)
        self.assertIn("for o in selected.get('market', [])", treatment)

    def test_unrelated_v4_runtime_mechanics_remain_byte_identical(self):
        # method_text intentionally requires a following def, so this set stops
        # before the terminal act()/__call__ boundary.  The stronger skeleton
        # assertion above already proves all bytes outside target spans unchanged.
        for name in (
            "_feed_stock_selected",
            "_early_capital_selected",
            "_market_pressure_selected",
            "_selected_snapshot",
        ):
            self.assertEqual(
                rpa.method_text(self.treatment_text, name),
                rpa.method_text(self.v4_text, name),
                name,
            )

    def test_suffix_only_seed_is_definite_gate_candidate(self):
        action = {"market": [["PASS"]] * 10 + [["BUY_SEED", "WHEAT", 1]]}
        report = rpa.classify_structural_candidate(action, {})
        self.assertTrue(report["candidate"])
        self.assertTrue(report["seed_gate_delta"])
        self.assertFalse(report["operating_stock_gate_delta"])
        self.assertFalse(report["redundant_hire_gate_delta"])

    def test_suffix_only_fertilizer_sell_is_definite_gate_candidate(self):
        action = {"market": [[]] * 10 + [["SELL", "FERTILIZER", 1]]}
        report = rpa.classify_structural_candidate(action, {})
        self.assertTrue(report["candidate"])
        self.assertTrue(report["operating_stock_gate_delta"])

    def test_suffix_only_hire_is_definite_gate_candidate(self):
        action = {"market": [[]] * 10 + [["HIRE", 1, 2]]}
        report = rpa.classify_structural_candidate(action, {})
        self.assertTrue(report["candidate"])
        self.assertTrue(report["redundant_hire_gate_delta"])

    def test_prefix_seed_with_nonempty_suffix_is_scope_candidate(self):
        action = {"market": [["BUY_SEED", "WHEAT", 1]] + [[]] * 9 + [["BUY_LAND", 0, 0]]}
        report = rpa.classify_structural_candidate(action, {})
        self.assertTrue(report["candidate"])
        self.assertFalse(report["seed_gate_delta"])
        self.assertTrue(report["seed_scope_candidate"])

    def test_prefix_fertilizer_with_nonempty_suffix_is_scope_candidate(self):
        action = {"market": [["SELL", "FERTILIZER", 1]] + [[]] * 9 + [["SELL", "WHEAT", 1]]}
        report = rpa.classify_structural_candidate(action, {})
        self.assertTrue(report["candidate"])
        self.assertFalse(report["operating_stock_gate_delta"])
        self.assertTrue(report["operating_stock_scope_candidate"])

    def test_no_suffix_has_no_structural_candidate(self):
        action = {"market": [["BUY_SEED", "WHEAT", 1], ["SELL", "FERTILIZER", 1], ["HIRE", 1, 2]]}
        report = rpa.classify_structural_candidate(action, {})
        self.assertFalse(report["candidate"])
        self.assertEqual(report["reason"], "no_scope_or_gate_delta")

    def test_minimum_one_cap_matches_v4_wrapper_boundary(self):
        action = {"market": [["PASS"], ["HIRE", 1, 2]]}
        report = rpa.classify_structural_candidate(action, {"maxMarketOrdersPerTurn": 0})
        self.assertEqual(report["cap"], 1)
        self.assertTrue(report["redundant_hire_gate_delta"])

    def test_non_list_market_fails_screen_closed(self):
        self.assertEqual(
            rpa.classify_structural_candidate({"market": "bad"}, {}),
            {"candidate": False, "reason": "market_not_list"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
