# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import unittest

from market_prefix_guard import (
    guard_candidate_action,
    inherited_purchase_indices,
    parse_order,
    preserves_purchase_prefix,
    preserves_scheduler_contract,
    sell_only_scheduler_delta,
    trace_capacity_prefix,
)


CONFIG = {"shedCapacity": 3, "maxMarketOrdersPerTurn": 10}


def legacy_aggregate_feasible(
    baseline_market, candidate_target_sale, *, target="CARROT", shed=None, cap=3
):
    """Minimal mirror of scheduler.py receipt_profile's market aggregation.

    It adds every inherited shed purchase and subtracts non-target inherited
    sales before applying the candidate target sale only at the row's end.
    """
    stock = dict(shed or {})
    total = sum(stock.values())
    for raw in baseline_market:
        parsed = parse_order(raw)
        if parsed is None:
            continue
        op = parsed["type"]
        item = parsed.get("item")
        quantity = parsed.get("remaining", 0)
        if op == "SELL" and item != target:
            stock[item] = max(0, stock.get(item, 0) - quantity)
        elif op in ("BUY_PRODUCT", "BUY_ANIMAL"):
            stock[item] = stock.get(item, 0) + quantity
    total_after_inherited = sum(stock.values())
    return total <= cap and total_after_inherited - candidate_target_sale <= cap - 1


def purchase_commits(trace):
    return [
        (event["index"], event["type"], event["committed"])
        for event in trace["events"]
        if event["type"] in ("BUY_PRODUCT", "BUY_ANIMAL")
    ]


class PredecessorWitnessTests(unittest.TestCase):
    def test_whole_row_aggregate_certifies_purchase_blocking_candidate(self):
        shed = {"CARROT": 1, "EGG": 1, "MILK": 1}
        baseline = [
            ["SELL", "CARROT", 1],
            ["BUY_PRODUCT", "WHEAT", 1],
            ["SELL", "EGG", 1],
            ["SELL", "MILK", 1],
        ]
        candidate = [
            [],
            ["BUY_PRODUCT", "WHEAT", 1],
            ["SELL", "EGG", 1],
            ["SELL", "MILK", 1],
        ]

        self.assertTrue(
            legacy_aggregate_feasible(
                baseline, 0, shed=shed, cap=CONFIG["shedCapacity"]
            ),
            "the exact predecessor shape wrongly certifies the delayed sale",
        )
        control_trace = trace_capacity_prefix(baseline, shed, CONFIG)
        candidate_trace = trace_capacity_prefix(candidate, shed, CONFIG)
        self.assertEqual(purchase_commits(control_trace), [(1, "BUY_PRODUCT", 1)])
        self.assertEqual(purchase_commits(candidate_trace), [(1, "BUY_PRODUCT", 0)])
        safe, report = preserves_purchase_prefix(baseline, candidate, CONFIG)
        self.assertFalse(safe)
        self.assertEqual(report["differing_indices"], [0])

    def test_partial_multiunit_buy_regression_is_visible(self):
        cfg = {"shedCapacity": 4, "maxMarketOrdersPerTurn": 10}
        shed = {"CARROT": 2, "EGG": 1}
        baseline = [
            ["SELL", "CARROT", 2],
            ["BUY_PRODUCT", "WHEAT", 3],
        ]
        candidate = [
            ["SELL", "CARROT", 1],
            ["BUY_PRODUCT", "WHEAT", 3],
        ]
        self.assertEqual(purchase_commits(trace_capacity_prefix(baseline, shed, cfg)), [(1, "BUY_PRODUCT", 3)])
        self.assertEqual(purchase_commits(trace_capacity_prefix(candidate, shed, cfg)), [(1, "BUY_PRODUCT", 2)])
        self.assertFalse(preserves_purchase_prefix(baseline, candidate, cfg)[0])

    def test_buy_animal_uses_same_capacity_gate(self):
        shed = {"CARROT": 1, "EGG": 1, "MILK": 1}
        baseline = [["SELL", "CARROT", 1], ["BUY_ANIMAL", "SHEEP", 1]]
        candidate = [[], ["BUY_ANIMAL", "SHEEP", 1]]
        self.assertEqual(purchase_commits(trace_capacity_prefix(baseline, shed, CONFIG)), [(1, "BUY_ANIMAL", 1)])
        self.assertEqual(purchase_commits(trace_capacity_prefix(candidate, shed, CONFIG)), [(1, "BUY_ANIMAL", 0)])


class PrefixCustodyTests(unittest.TestCase):
    def test_change_after_last_purchase_is_allowed(self):
        baseline = [
            ["BUY_PRODUCT", "WHEAT", 1],
            ["SELL", "CARROT", 1],
        ]
        candidate = [
            ["BUY_PRODUCT", "WHEAT", 1],
            ["SELL", "CARROT", 7],
        ]
        safe, report = preserves_purchase_prefix(baseline, candidate, CONFIG)
        self.assertTrue(safe)
        self.assertEqual(report["guarded_through_index"], 0)

    def test_purchase_row_itself_is_guarded(self):
        baseline = [["BUY_PRODUCT", "WHEAT", 1]]
        candidate = [["BUY_PRODUCT", "WHEAT", 2]]
        self.assertFalse(preserves_purchase_prefix(baseline, candidate, CONFIG)[0])

    def test_blank_rows_count_toward_raw_prefix(self):
        cfg = {"shedCapacity": 3, "maxMarketOrdersPerTurn": 3}
        baseline = [[], ["SELL", "CARROT", 1], ["BUY_PRODUCT", "WHEAT", 1]]
        candidate = [[], [], ["BUY_PRODUCT", "WHEAT", 1]]
        safe, report = preserves_purchase_prefix(baseline, candidate, cfg)
        self.assertFalse(safe)
        self.assertEqual(report["purchase_indices"], [2])
        self.assertEqual(report["differing_indices"], [1])

    def test_inert_suffix_purchase_is_not_guarded(self):
        cfg = {"maxMarketOrdersPerTurn": 2, "shedCapacity": 3}
        baseline = [["SELL", "CARROT", 1], [], ["BUY_PRODUCT", "WHEAT", 1]]
        candidate = [[], [], ["BUY_PRODUCT", "WHEAT", 9]]
        safe, report = preserves_purchase_prefix(baseline, candidate, cfg)
        self.assertTrue(safe)
        self.assertEqual(report["reason"], "NO_INHERITED_SHED_PURCHASE")

    def test_multiple_purchases_guard_through_last_one(self):
        baseline = [
            ["BUY_PRODUCT", "WHEAT", 1],
            ["SELL", "CARROT", 1],
            ["BUY_ANIMAL", "GOOSE", 1],
            ["SELL", "EGG", 1],
        ]
        candidate = deepcopy(baseline)
        candidate[1] = ["SELL", "CARROT", 2]
        safe, report = preserves_purchase_prefix(baseline, candidate, CONFIG)
        self.assertFalse(safe)
        self.assertEqual(report["purchase_indices"], [0, 2])
        self.assertEqual(report["guarded_through_index"], 2)

    def test_no_purchase_allows_scheduler_change(self):
        baseline = [["SELL", "CARROT", 1]]
        candidate = [["SELL", "CARROT", 0]]
        self.assertTrue(preserves_purchase_prefix(baseline, candidate, CONFIG)[0])

    def test_shortened_candidate_prefix_fails_closed(self):
        baseline = [["SELL", "CARROT", 1], ["BUY_PRODUCT", "WHEAT", 1]]
        candidate = [["SELL", "CARROT", 1]]
        safe, report = preserves_purchase_prefix(baseline, candidate, CONFIG)
        self.assertFalse(safe)
        self.assertEqual(report["differing_indices"], [1])


class SchedulerMutationBoundaryTests(unittest.TestCase):
    def test_appended_valid_sell_is_allowed(self):
        safe, report = sell_only_scheduler_delta(
            [["BUY_SEED", "WHEAT", 1]],
            [["BUY_SEED", "WHEAT", 1], ["SELL", "CARROT", 2]],
        )
        self.assertTrue(safe)
        self.assertEqual(report["differing_indices"], [1])

    def test_appended_purchase_is_rejected_even_without_inherited_purchase(self):
        base = [["SELL", "CARROT", 1]]
        candidate = base + [["BUY_PRODUCT", "WHEAT", 1]]
        safe, report = preserves_scheduler_contract(base, candidate, CONFIG)
        self.assertFalse(safe)
        self.assertEqual(report["reason"], "NON_SELL_ROW_APPENDED")

    def test_inherited_blank_cannot_be_filled(self):
        safe, report = sell_only_scheduler_delta(
            [[], ["SELL", "CARROT", 1]],
            [["SELL", "EGG", 1], ["SELL", "CARROT", 1]],
        )
        self.assertFalse(safe)
        self.assertEqual(report["reason"], "NON_SELL_INHERITED_ROW_CHANGED")

    def test_sell_item_cannot_change(self):
        safe, report = sell_only_scheduler_delta(
            [["SELL", "CARROT", 1]], [["SELL", "EGG", 1]]
        )
        self.assertFalse(safe)
        self.assertEqual(report["reason"], "SELL_ROW_MUTATION_OUTSIDE_QUANTITY")

    def test_inherited_market_cannot_be_shortened(self):
        safe, report = sell_only_scheduler_delta(
            [["SELL", "CARROT", 1], []], [["SELL", "CARROT", 1]]
        )
        self.assertFalse(safe)
        self.assertEqual(report["reason"], "INHERITED_ROW_REMOVED")

    def test_safe_sell_suffix_satisfies_combined_contract(self):
        base = [["BUY_PRODUCT", "WHEAT", 1], ["SELL", "CARROT", 1]]
        candidate = [["BUY_PRODUCT", "WHEAT", 1], ["SELL", "CARROT", 4]]
        safe, report = preserves_scheduler_contract(base, candidate, CONFIG)
        self.assertTrue(safe)
        self.assertEqual(report["reason"], "PURCHASE_PREFIX_IDENTICAL")


class TotalityAndWrapperTests(unittest.TestCase):
    def test_parse_order_is_total_over_unhashable_json_shapes(self):
        shapes = [
            [["SELL"], "CARROT", 1],
            ["SELL", ["CARROT"], 1],
            ["BUY_PRODUCT", {"WHEAT": 1}, 1],
            ["BUY_ANIMAL", "SHEEP", float("inf")],
            {"type": "SELL"},
            "SELL",
            None,
        ]
        for shape in shapes:
            with self.subTest(shape=repr(shape)):
                self.assertIsNone(parse_order(shape))

    def test_bad_limit_fails_closed_without_exception(self):
        safe, report = preserves_purchase_prefix(
            [["BUY_PRODUCT", "WHEAT", 1]],
            [["BUY_PRODUCT", "WHEAT", 1]],
            {"maxMarketOrdersPerTurn": float("inf")},
        )
        self.assertFalse(safe)
        self.assertEqual(report["reason"], "BAD_INPUT")

    def test_trace_bad_shed_fails_closed(self):
        trace = trace_capacity_prefix([], {"WHEAT": -1}, CONFIG)
        self.assertFalse(trace["ok"])
        self.assertEqual(trace["reason"], "BAD_INPUT")

    def test_wrapper_off_is_identity_and_nonmutating(self):
        base = {"farmer": ["PASS"], "hands": [], "market": []}
        candidate = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "CARROT", 1]]}
        before = deepcopy(candidate)
        out, report = guard_candidate_action(base, candidate, CONFIG, enabled=False)
        self.assertIs(out, candidate)
        self.assertEqual(candidate, before)
        self.assertEqual(report["reason"], "OFF")

    def test_wrapper_reverts_unsafe_market_atomically(self):
        base = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "CARROT", 1], ["BUY_PRODUCT", "WHEAT", 1]],
        }
        candidate = deepcopy(base)
        candidate["market"][0] = []
        candidate_before = deepcopy(candidate)
        out, report = guard_candidate_action(base, candidate, CONFIG, enabled=True)
        self.assertEqual(out, base)
        self.assertIsNot(out, base)
        self.assertEqual(candidate, candidate_before)
        self.assertTrue(report["changed"])

    def test_wrapper_allows_safe_suffix_edit_by_identity(self):
        base = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["BUY_PRODUCT", "WHEAT", 1], ["SELL", "CARROT", 1]],
        }
        candidate = deepcopy(base)
        candidate["market"][1][2] = 5
        out, report = guard_candidate_action(base, candidate, CONFIG, enabled=True)
        self.assertIs(out, candidate)
        self.assertFalse(report["changed"])

    def test_wrapper_reverts_nonmarket_drift(self):
        base = {"farmer": ["PASS"], "hands": [], "market": []}
        candidate = {"farmer": ["NORTH"], "hands": [], "market": []}
        out, report = guard_candidate_action(base, candidate, CONFIG, enabled=True)
        self.assertEqual(out, base)
        self.assertEqual(report["reason"], "NON_MARKET_ACTION_CHANGED")

    def test_inherited_indices_ignore_buy_seed(self):
        market = [
            ["BUY_SEED", "WHEAT", 1],
            ["BUY_PRODUCT", "WHEAT", 1],
            ["BUY_ANIMAL", "COW", 1],
        ]
        self.assertEqual(inherited_purchase_indices(market, CONFIG), (1, 2))


if __name__ == "__main__":
    unittest.main()
