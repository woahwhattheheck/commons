# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[4]
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import mechanics

_spec = importlib.util.spec_from_file_location(
    "mirror_collision_sell_order", HERE / "mirror_collision_sell_order.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def action(rows):
    return {"farmer": ["PASS"], "hands": [], "market": copy.deepcopy(rows)}


class MirrorCollisionSellOrderTests(unittest.TestCase):
    def setUp(self):
        self.obs = {
            "market": {
                "inventory": {
                    "MELON": 10050,
                    "WOOL": 10050,
                    "MILK": 10000,
                    "EGG": 10000,
                }
            }
        }

    def test_default_off_is_exact_identity(self):
        raw = action([["SELL", "WOOL", 25], ["SELL", "MELON", 25]])
        got = mod.MirrorCollisionSellOrder().transform(
            self.obs, {}, raw, post_unit_shed={"WOOL": 25, "MELON": 25}
        )
        self.assertEqual(got, raw)

    def test_literal_true_only_enables(self):
        raw = action([["SELL", "WOOL", 25], ["SELL", "MELON", 25]])
        for token in (1, "true", [], {}, None, False):
            with self.subTest(token=token):
                got = mod.MirrorCollisionSellOrder().transform(
                    self.obs, {}, raw,
                    post_unit_shed={"WOOL": 25, "MELON": 25},
                    enabled=token,
                )
                self.assertEqual(got, raw)

    def test_concrete_official_rank_inversion(self):
        # At public inventory 10050 and executable fill 25, the incumbent
        # endpoint heuristic ranks WOOL first. Exact mirror-delay exposure
        # ranks MELON first because WOOL reaches the $1 floor and freezes supply.
        self.assertEqual(mod.endpoint_impact_value("MELON", 10050, 25), 775)
        self.assertEqual(mod.endpoint_impact_value("WOOL", 10050, 25), 1350)
        melon = mod.mirror_delay_value("MELON", 10050, 25)
        wool = mod.mirror_delay_value("WOOL", 10050, 25)
        self.assertEqual(melon["mirror_delay_value"], 931)
        self.assertEqual(wool["mirror_delay_value"], 264)
        raw = action([["SELL", "WOOL", 25], ["SELL", "MELON", 25]])
        got = mod.MirrorCollisionSellOrder().transform(
            self.obs, {}, raw,
            post_unit_shed={"WOOL": 25, "MELON": 25},
            enabled=True,
        )
        self.assertEqual(
            got["market"][:2],
            [["SELL", "MELON", 25], ["SELL", "WOOL", 25]],
        )

    def test_floor_freeze_matches_engine_sell_commit_rule(self):
        revenue, end_inventory = mod.sell_block_revenue("WOOL", 10050, 25)
        self.assertEqual(revenue, 289)
        self.assertEqual(end_inventory, 10059)
        score = mod.mirror_delay_value("WOOL", 10050, 25)
        self.assertEqual(score["delayed_cash"], 25)
        self.assertEqual(score["delayed_start_inventory"], 10059)
        self.assertEqual(score["delayed_end_inventory"], 10059)

    def test_post_unit_fill_not_nominal_quantity_drives_score(self):
        raw = action([["SELL", "WOOL", 1000], ["SELL", "MILK", 5]])
        scorer = mod.MirrorCollisionSellOrder()
        got = scorer.transform(
            self.obs, {}, raw,
            post_unit_shed={"WOOL": 1, "MILK": 5},
            enabled=True,
        )
        by_item = {entry["item"]: entry for entry in scorer.diagnostics["scores"]}
        self.assertEqual(by_item["WOOL"]["requested"], 1000)
        self.assertEqual(by_item["WOOL"]["fillable"], 1)
        self.assertEqual(
            sorted(map(tuple, got["market"][:2])),
            sorted(map(tuple, raw["market"][:2])),
        )

    def test_market_prefix_cap_prevents_suffix_reorder(self):
        raw = action([
            ["SELL", "WOOL", 25],
            ["SELL", "MELON", 25],
            ["SELL", "MILK", 5],
        ])
        got = mod.MirrorCollisionSellOrder().transform(
            self.obs, {"maxMarketOrdersPerTurn": 1}, raw,
            post_unit_shed={"WOOL": 25, "MELON": 25, "MILK": 5},
            enabled=True,
        )
        self.assertEqual(got, raw)

    def test_non_sell_barrier_and_tail_are_exact(self):
        raw = action([
            ["SELL", "WOOL", 25],
            ["HIRE"],
            ["SELL", "MELON", 25],
            ["SELL", "MILK", 5],
        ])
        got = mod.MirrorCollisionSellOrder().transform(
            self.obs, {}, raw,
            post_unit_shed={"WOOL": 25},
            enabled=True,
        )
        self.assertEqual(got, raw)

    def test_zero_quantity_is_hard_barrier(self):
        raw = action([
            ["SELL", "WOOL", 25],
            ["SELL", "MELON", 0],
            ["SELL", "MILK", 5],
        ])
        got = mod.MirrorCollisionSellOrder().transform(
            self.obs, {}, raw,
            post_unit_shed={"WOOL": 25},
            enabled=True,
        )
        self.assertEqual(got, raw)

    def test_duplicate_product_fails_closed(self):
        raw = action([
            ["SELL", "WOOL", 3],
            ["SELL", "WOOL", 4],
        ])
        scorer = mod.MirrorCollisionSellOrder()
        got = scorer.transform(
            self.obs, {}, raw,
            post_unit_shed={"WOOL": 7},
            enabled=True,
        )
        self.assertEqual(got, raw)
        self.assertEqual(scorer.diagnostics["status"], "fallback")

    def test_incomplete_or_poisoned_custody_fails_closed(self):
        raw = action([["SELL", "WOOL", 25], ["SELL", "MELON", 25]])
        cases = [
            ({"WOOL": 25}, self.obs),
            ({"WOOL": True, "MELON": 25}, self.obs),
            (
                {"WOOL": 25, "MELON": 25},
                {"market": {"inventory": {"WOOL": 10050, "MELON": "10050"}}},
            ),
        ]
        for shed, obs in cases:
            with self.subTest(shed=shed, obs=obs):
                got = mod.MirrorCollisionSellOrder().transform(
                    obs, {}, raw, post_unit_shed=shed, enabled=True
                )
                self.assertEqual(got, raw)

    def test_bad_prefix_limit_fails_closed(self):
        raw = action([["SELL", "WOOL", 25], ["SELL", "MELON", 25]])
        for bad in (True, 2.0, "2"):
            with self.subTest(bad=bad):
                got = mod.MirrorCollisionSellOrder().transform(
                    self.obs, {"maxMarketOrdersPerTurn": bad}, raw,
                    post_unit_shed={"WOOL": 25, "MELON": 25},
                    enabled=True,
                )
                self.assertEqual(got, raw)

    def test_equal_scores_preserve_incumbent_order(self):
        raw = action([["SELL", "WOOL", 2], ["SELL", "MELON", 3]])
        scorer = mod.MirrorCollisionSellOrder(lambda *_args: 10)
        got = scorer.transform(
            self.obs, {}, raw,
            post_unit_shed={"WOOL": 2, "MELON": 3},
            enabled=True,
        )
        self.assertEqual(got, raw)

    def test_params_forwarded_to_quote(self):
        marker = {"marker": "exact-current"}
        seen = []
        def quote(_item, inventory, params):
            seen.append((inventory, params))
            return 100
        obs = {
            "market": {
                "inventory": {"WOOL": 10000, "MELON": 10000},
                "params": marker,
            }
        }
        raw = action([["SELL", "WOOL", 2], ["SELL", "MELON", 2]])
        mod.MirrorCollisionSellOrder(quote).transform(
            obs, {}, raw,
            post_unit_shed={"WOOL": 2, "MELON": 2},
            enabled=True,
        )
        self.assertTrue(seen)
        self.assertTrue(all(params is marker for _inventory, params in seen))

    def test_input_and_non_market_fields_are_never_mutated(self):
        raw = action([
            ["SELL", "WOOL", 25],
            ["SELL", "MELON", 25],
            ["HIRE"],
            ["SELL", "MILK", 5],
        ])
        raw["meta"] = {"sentinel": [1, 2, 3]}
        snapshot = copy.deepcopy(raw)
        got = mod.MirrorCollisionSellOrder().transform(
            self.obs, {}, raw,
            post_unit_shed={"WOOL": 25, "MELON": 25},
            enabled=True,
        )
        self.assertEqual(raw, snapshot)
        self.assertEqual(got["market"][2:], snapshot["market"][2:])
        self.assertEqual(got["meta"], snapshot["meta"])
        self.assertEqual(len(got["market"]), len(snapshot["market"]))

    def test_truthy_malformed_row_anywhere_fails_closed(self):
        raw = action([["SELL", "WOOL", 25], ["SELL", "MELON", 25], 1])
        got = mod.MirrorCollisionSellOrder().transform(
            self.obs, {}, raw,
            post_unit_shed={"WOOL": 25, "MELON": 25},
            enabled=True,
        )
        self.assertEqual(got, raw)

    def test_engine_and_mechanics_pins_are_explicit(self):
        self.assertEqual(
            mod.ENGINE_BLOB_SHA,
            "3c202c7ee921da239356789e266b694635103fc4",
        )
        self.assertEqual(
            mod.MECHANICS_BLOB_SHA,
            "044a4f9c0a4a44dde10ada57563238bcaf82075d",
        )


if __name__ == "__main__":
    unittest.main()
