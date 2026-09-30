#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import predictable_procurement as pp


HERE = Path(__file__).resolve().parent
ARLENE = HERE.parents[3] / "reference" / "next-panel" / "vendor" / "arlene.py"
C5 = HERE / "c5_market_transition_oracle.py"


def action(*rows):
    return {"farmer": ["PASS"], "hands": [], "market": list(rows)}


def fake(routes, *, max_orders=10, final_step=8, decisions=()):
    return SimpleNamespace(
        routes=lambda: routes,
        MAX_ORDERS=max_orders,
        FINAL_EXECUTABLE_STEP=final_step,
        DECISIONS=decisions,
    )


class PredictableProcurementTests(unittest.TestCase):
    def test_invariant_requires_same_positive_row_in_every_route(self):
        routes = {
            "a": [action(["BUY_PRODUCT", "WHEAT", 2])],
            "b": [action(["BUY_PRODUCT", "WHEAT", 2])],
        }
        r = pp.analyze(fake(routes, final_step=0))
        self.assertEqual(r["invariant_pulses"], [
            {"step": 0, "row": 0, "item": "WHEAT", "qty": 2}
        ])
        self.assertEqual(r["counts"]["route_invariant_pulses"], 1)

    def test_quantity_or_item_disagreement_is_not_invariant(self):
        routes = {
            "a": [action(["BUY_PRODUCT", "WHEAT", 2])],
            "b": [action(["BUY_PRODUCT", "WHEAT", 3])],
            "c": [action(["BUY_PRODUCT", "FERTILIZER", 2])],
        }
        r = pp.analyze(fake(routes, final_step=0))
        self.assertEqual(r["invariant_pulses"], [])
        self.assertEqual(r["counts"]["branch_conditional_stable_pulses"], 3)

    def test_preceding_sell_fails_raw_index_stability_closed(self):
        routes = {
            "a": [action(["SELL", "MILK", 1], ["BUY_PRODUCT", "WHEAT", 1])],
            "b": [action(["SELL", "MILK", 1], ["BUY_PRODUCT", "WHEAT", 1])],
        }
        r = pp.analyze(fake(routes, final_step=0))
        self.assertEqual(r["invariant_pulses"], [])
        self.assertEqual(r["counts"]["all_base_buy_pulses"], 2)
        self.assertEqual(r["counts"]["raw_index_stable_base_buy_pulses"], 0)

    def test_falsey_and_non_sell_prefix_preserve_raw_index(self):
        routes = {
            "a": [action([], ["BUY_SEED", "CARROT", 1], ["BUY_PRODUCT", "FERTILIZER", 4])],
            "b": [action([], ["BUY_SEED", "CARROT", 1], ["BUY_PRODUCT", "FERTILIZER", 4])],
        }
        r = pp.analyze(fake(routes, final_step=0))
        self.assertEqual(r["invariant_pulses"], [
            {"step": 0, "row": 2, "item": "FERTILIZER", "qty": 4}
        ])

    def test_raw_cap_hides_suffix(self):
        prefix = [["BUY_SEED", "CARROT", 1] for _ in range(10)]
        routes = {
            "a": [action(*prefix, ["BUY_PRODUCT", "WHEAT", 1])],
            "b": [action(*prefix, ["BUY_PRODUCT", "WHEAT", 1])],
        }
        r = pp.analyze(fake(routes, final_step=0, max_orders=10))
        self.assertEqual(r["counts"]["all_base_buy_pulses"], 0)

    def test_only_literal_plain_positive_wheat_fert_quantities_certify(self):
        rows = [
            ["BUY_PRODUCT", "WHEAT", True],
            ["BUY_PRODUCT", "WHEAT", 0],
            ["BUY_PRODUCT", "CARROT", 2],
            ["BUY_PRODUCT", "FERTILIZER", 3],
        ]
        routes = {"a": [action(*rows)], "b": [action(*rows)]}
        r = pp.analyze(fake(routes, final_step=0))
        self.assertEqual(r["invariant_pulses"], [
            {"step": 0, "row": 3, "item": "FERTILIZER", "qty": 3}
        ])

    def test_final_step_bound_excludes_later_tape_rows(self):
        routes = {
            "a": [action(), action(["BUY_PRODUCT", "WHEAT", 1])],
            "b": [action(), action(["BUY_PRODUCT", "WHEAT", 1])],
        }
        r = pp.analyze(fake(routes, final_step=0))
        self.assertEqual(r["invariant_pulses"], [])

    def test_public_decisions_are_reported_but_not_promoted_to_authority(self):
        routes = {"a": [action()], "b": [action()]}
        r = pp.analyze(fake(
            routes,
            final_step=0,
            decisions=((0, "px_CARROT", 42, "b"),),
        ))
        self.assertEqual(r["public_decisions"][0]["feature"], "px_CARROT")
        self.assertFalse(r["scope"]["branch_conditional_is_authority"])
        self.assertFalse(r["scope"]["hidden_current_rival_action_used"])

    def test_malformed_route_and_decision_fail_closed(self):
        with self.assertRaises(ValueError):
            pp.analyze(fake({"a": "not-a-route"}, final_step=0))
        with self.assertRaises(ValueError):
            pp.analyze(fake({"a": [action()]}, final_step=0, decisions=((True, "x", 1, "a"),)))

    def test_actual_authenticated_arlene_is_deterministic_and_stable(self):
        module = pp.load_arlene(ARLENE, c5_oracle=C5)
        first = pp.analyze(module)
        second = pp.analyze(module)
        self.assertEqual(first, second)
        self.assertEqual(first["source"]["arlene_git_blob"], pp.ARLENE_GIT_BLOB)
        self.assertEqual(first["source"]["c5_oracle_git_blob"], pp.C5_ORACLE_GIT_BLOB)
        self.assertGreaterEqual(first["counts"]["routes"], 1)
        for pulse in first["invariant_pulses"]:
            self.assertIn(pulse["item"], pp.BUYABLE)
            self.assertGreater(pulse["qty"], 0)
            self.assertLess(pulse["row"], module.MAX_ORDERS)
            self.assertLessEqual(pulse["step"], module.FINAL_EXECUTABLE_STEP)

    def test_source_or_oracle_drift_refuses_before_import(self):
        with tempfile.TemporaryDirectory() as td:
            bad_arlene = Path(td) / "arlene.py"
            bad_arlene.write_bytes(ARLENE.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "Arlene Git blob mismatch"):
                pp.load_arlene(bad_arlene, c5_oracle=C5)

            bad_oracle = Path(td) / "c5.py"
            bad_oracle.write_bytes(C5.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "C5 oracle Git blob mismatch"):
                pp.load_arlene(ARLENE, c5_oracle=bad_oracle)


if __name__ == "__main__":
    unittest.main()
