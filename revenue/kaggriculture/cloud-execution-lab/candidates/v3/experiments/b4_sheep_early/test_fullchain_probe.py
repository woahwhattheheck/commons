#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

import fullchain_probe as b4


def blank_action(hands=0):
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in range(hands)], "market": []}


def tape():
    rows = [blank_action() for _ in range(288)]
    rows[216]["market"] = [["BUY_ANIMAL", "SHEEP", 1]]
    rows[220]["farmer"] = ["PICKUP", "SHEEP", 1]
    rows[224]["farmer"] = ["PLACE", "SHEEP", 1]
    return rows


def observation(*, yarn=True):
    shops = ["YARN_STORE", "BAKERY"] if yarn else ["BAKERY", "PIZZA_SHOP"]
    return {
        "farms": [{"money": 100, "farmer": [0, 0], "hands": [], "tiles": [[{"kind": "PASTURE", "animal": None}]]}],
        "private": {"shed": {"SHEEP": 0}, "inventories": [{"SHEEP": 0}]},
        "town": {"unlocked_shops": shops},
    }


class ChainLinkTests(unittest.TestCase):
    def test_links_one_exact_actor_chain_and_requires_pass_targets(self):
        spec = b4.build_chain_spec(tape(), 7)
        self.assertEqual(spec["status"], "static-shiftable")
        self.assertTrue(spec["static_safe"])
        self.assertEqual([e["target_step"] for e in spec["events"]], [192, 196, 200])
        self.assertEqual([e["kind"] for e in spec["events"]], ["buy", "pickup", "place"])

    def test_authored_target_work_kills_static_shift(self):
        rows = tape()
        rows[196]["farmer"] = ["HARVEST"]
        spec = b4.build_chain_spec(rows, 2)
        self.assertEqual(spec["status"], "static-collision")
        self.assertFalse(spec["static_safe"])
        self.assertIn("target-actor-authored-work", {r["reason"] for r in spec["static_checks"]})

    def test_market_full_kills_static_shift(self):
        rows = tape()
        rows[192]["market"] = [["BUY_SEED", "WHEAT", 1] for _ in range(10)]
        spec = b4.build_chain_spec(rows, 1)
        self.assertEqual(spec["status"], "static-collision")
        self.assertIn("target-market-full", {r["reason"] for r in spec["static_checks"]})

    def test_place_without_linked_pickup_is_ambiguous(self):
        rows = tape()
        rows[220]["farmer"] = ["PASS"]
        spec = b4.build_chain_spec(rows, 3)
        self.assertEqual(spec["status"], "place-without-linked-actor-pickup")
        self.assertEqual(spec["events"], [])

    def test_second_buy_before_place_is_ambiguous(self):
        rows = tape()
        rows[222]["market"] = [["BUY_ANIMAL", "SHEEP", 1]]
        spec = b4.build_chain_spec(rows, 4)
        self.assertEqual(spec["status"], "ambiguous-day9-buy")


class RuntimeTransformTests(unittest.TestCase):
    def setUp(self):
        self.spec = b4.build_chain_spec(tape(), 7)

    def test_yarn_guard_is_required_before_any_shift(self):
        runtime = b4.ShiftRuntime(self.spec)
        action, pending = runtime.transform(blank_action(), observation(yarn=False), 0, 192)
        self.assertEqual(action, blank_action())
        self.assertEqual(pending, [])
        self.assertFalse(runtime.enabled)

    def test_buy_is_appended_after_existing_market_rows(self):
        runtime = b4.ShiftRuntime(self.spec)
        parent = blank_action()
        parent["market"] = [["HIRE"]]
        shifted, pending = runtime.transform(parent, observation(), 0, 192)
        self.assertEqual(shifted["market"], [["HIRE"], ["BUY_ANIMAL", "SHEEP", 1]])
        self.assertEqual(len(pending), 1)
        self.assertEqual(parent["market"], [["HIRE"]])

    def test_worker_shift_requires_prior_success_and_literal_pass(self):
        runtime = b4.ShiftRuntime(self.spec)
        runtime.enabled = True
        unchanged, pending = runtime.transform(blank_action(), observation(), 0, 196)
        self.assertEqual(unchanged, blank_action())
        self.assertEqual(pending, [])
        runtime.success[self.spec["events"][0]["id"]] = True
        authored = blank_action()
        authored["farmer"] = ["FEED"]
        unchanged, pending = runtime.transform(authored, observation(), 0, 196)
        self.assertEqual(unchanged, authored)
        self.assertEqual(pending, [])
        self.assertFalse(runtime.success[self.spec["events"][1]["id"]])

    def test_original_buy_is_suppressed_only_after_shift_success(self):
        runtime = b4.ShiftRuntime(self.spec)
        runtime.enabled = True
        original = blank_action()
        original["market"] = [["SELL", "MILK", 1], ["BUY_ANIMAL", "SHEEP", 1]]
        unchanged, _ = runtime.transform(original, observation(), 0, 216)
        self.assertEqual(unchanged, original)
        runtime.success[self.spec["events"][0]["id"]] = True
        changed, _ = runtime.transform(original, observation(), 0, 216)
        self.assertEqual(changed["market"], [["SELL", "MILK", 1], []])
        self.assertEqual(original["market"][1], ["BUY_ANIMAL", "SHEEP", 1])

    def test_market_suppression_ambiguity_is_recorded_not_guessed(self):
        runtime = b4.ShiftRuntime(self.spec)
        runtime.enabled = True
        runtime.success[self.spec["events"][0]["id"]] = True
        action = blank_action()
        action["market"] = [["BUY_ANIMAL", "SHEEP", 1], ["BUY_ANIMAL", "SHEEP", 1]]
        changed, _ = runtime.transform(action, observation(), 0, 216)
        self.assertEqual(changed, action)
        self.assertEqual(len(runtime.suppression_failures), 1)

    def test_partial_prefix_suppression_failure_rejects_before_no_activation(self):
        runtime = b4.ShiftRuntime(self.spec)
        runtime.enabled = True
        buy, pickup = self.spec["events"][:2]
        runtime.success[buy["id"]] = True
        ambiguous = blank_action()
        ambiguous["market"] = [copy.deepcopy(buy["row"]), copy.deepcopy(buy["row"])]
        unchanged, _ = runtime.transform(ambiguous, observation(), 0, buy["source_step"])
        self.assertEqual(unchanged, ambiguous)
        self.assertEqual(len(runtime.suppression_failures), 1)

        runtime.success[pickup["id"]] = False
        shift = runtime.report()
        self.assertFalse(shift["all_shifted_events_executed"])
        activated, negative, positive, disposition = b4._classify_cells([
            {"delta_margin": 0.0, "shift": shift},
        ])
        self.assertEqual(activated, [])
        self.assertEqual(negative, [])
        self.assertEqual(positive, [])
        self.assertEqual(disposition, "REJECT_SUPPRESSION_PROVENANCE_MISMATCH")


if __name__ == "__main__":
    unittest.main()
