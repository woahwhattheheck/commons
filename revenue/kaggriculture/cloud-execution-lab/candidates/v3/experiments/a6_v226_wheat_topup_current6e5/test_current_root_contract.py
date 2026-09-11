# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
EXPECTED_PARENT = "6e5e3c7cc5302d6db4b702cc4fd7c8ca721d7b8a"
EXPECTED_R04 = "7edacbfb4916b8f241b689ded6643240ca02a9ec"
EXPECTED = {
    "horizon": 8,
    "opening": 0,
    "row_order": True,
    "evening_flush": True,
    "sale_fertilizer": True,
    "cattle_early": True,
    "kill_late_water": False,
    "strawberry_endgame": False,
    "strawberry_max_plants": 8,
    "no_late_sale_advance": True,
    "no_late_sale_advance_step": 648,
    "strawberry_topup": True,
    "b5_carrot_fertilizer": True,
    "b5_jit_fertilize": True,
}


def source(name):
    return (HERE / name).read_text(encoding="utf-8")


def assignment_literal(text, name):
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == name:
                return ast.literal_eval(node.value)
    raise AssertionError(f"missing literal assignment {name}")


class CurrentRootA6Contract(unittest.TestCase):
    def test_sources_parse_and_bind_exact_parent(self):
        for name in ("baseline.py", "candidate.py"):
            text = source(name)
            compile(text, str(HERE / name), "exec")
            self.assertEqual(assignment_literal(text, "CURRENT_PARENT"), EXPECTED_PARENT)
            self.assertEqual(assignment_literal(text, "CURRENT_R04_BLOB"), EXPECTED_R04)

    def test_control_and_candidate_preserve_identical_current_tuple(self):
        baseline = assignment_literal(source("baseline.py"), "CURRENT_6E5")
        candidate = assignment_literal(source("candidate.py"), "CURRENT_6E5")
        self.assertEqual(baseline, EXPECTED)
        self.assertEqual(candidate, EXPECTED)
        self.assertEqual(baseline, candidate)
        self.assertIs(baseline["b5_carrot_fertilizer"], True)
        self.assertIs(baseline["b5_jit_fertilize"], True)

    def test_install_is_keyword_based_not_stale_positional_abi(self):
        for name in ("baseline.py", "candidate.py"):
            text = source(name)
            self.assertIn("base.install(host=None, **CURRENT_6E5)", text)
            self.assertNotIn("base.install(\n    None,", text)

    def test_candidate_only_names_v226_as_policy_ablation(self):
        text = source("candidate.py")
        self.assertIn("previous = base._v226_topup", text)
        self.assertIn("base._v226_topup = _no_v226_topup", text)
        self.assertIn("finally:\n        base._v226_topup = previous", text)
        for forbidden in (
            "_V233_PARENT =",
            "_v234_rescue =",
            "POLICY_AGENT =",
            "B5_CARROT_FERTILIZER =",
            "B5_JIT_FERTILIZE =",
        ):
            self.assertNotIn(forbidden, text)

    def test_baseline_has_no_ablation_monkeypatch(self):
        self.assertNotIn("_v226_topup =", source("baseline.py"))


if __name__ == "__main__":
    unittest.main()
