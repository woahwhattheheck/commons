# SPDX-License-Identifier: Apache-2.0
import unittest

from missing_hire_recovery import recover_missing_hire


def observation(hands=3, step=10):
    return {
        "step": step,
        "player": 0,
        "farms": [{"hands": [[0, 0] for _ in range(hands)]}, {"hands": []}],
    }


def route(required=4, step=10):
    rows = [{"farmer": ["PASS"], "hands": [], "market": []}
            for _ in range(step + 2)]
    hands = [["PASS"] for _ in range(required)]
    if required:
        hands[-1] = ["HARVEST"]
    rows[step + 1] = {"farmer": ["PASS"], "hands": hands, "market": []}
    return rows


def prefix_with_budget(budget, hire_cost=250, unsupported=None):
    def certify(queue, stop):
        cash = budget
        outcomes = {}
        for index, order in enumerate(queue[: stop + 1]):
            if unsupported is not None and index == unsupported:
                return {"money": cash, "outcomes": outcomes, "unsupported_index": index}
            if order and order[0] == "SELL":
                cash += max(0, int(order[2])) * 100
            elif order and order[0] == "HIRE":
                completed = int(cash >= hire_cost)
                if completed:
                    cash -= hire_cost
                outcomes[index] = {"required": 1, "completed": completed,
                                   "cost_per_unit": hire_cost}
        return {"money": cash, "outcomes": outcomes, "unsupported_index": None}
    return certify


class MissingHireRecoveryTests(unittest.TestCase):
    def test_replaces_zero_sale_after_guaranteed_receipt(self):
        selected = {"farmer": ["PASS"], "hands": [],
                    "market": [["SELL", "MILK", 3], ["SELL", "WHEAT", 0]]}
        out, report = recover_missing_hire(
            observation(), {}, selected, route=route(), certify_prefix=prefix_with_budget(0))
        self.assertEqual(out["market"], [["SELL", "MILK", 3], ["HIRE"]])
        self.assertTrue(report["changed"])
        self.assertEqual(report["inserted_index"], 1)
        self.assertEqual(report["available_next_hands"], 4)
        self.assertEqual(selected["market"][1], ["SELL", "WHEAT", 0])

    def test_appends_within_limit(self):
        selected = {"farmer": ["PASS"], "hands": [], "market": []}
        out, report = recover_missing_hire(
            observation(), {"maxMarketOrdersPerTurn": 1}, selected,
            route=route(), certify_prefix=prefix_with_budget(250))
        self.assertEqual(out["market"], [["HIRE"]])
        self.assertEqual(report["reason"], "inserted_prefix_certified_hire")

    def test_unfunded_hire_is_fail_closed(self):
        selected = {"farmer": ["PASS"], "hands": [], "market": [[]]}
        out, report = recover_missing_hire(
            observation(), {}, selected, route=route(), certify_prefix=prefix_with_budget(249))
        self.assertEqual(out, selected)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "no_funded_inert_slot")

    def test_existing_funded_hire_satisfies_route(self):
        selected = {"farmer": ["PASS"], "hands": [], "market": [["HIRE"]]}
        out, report = recover_missing_hire(
            observation(), {}, selected, route=route(), certify_prefix=prefix_with_budget(250))
        self.assertEqual(out, selected)
        self.assertEqual(report["reason"], "route_capacity_satisfied")
        self.assertEqual(report["funded_existing_hires"], 1)

    def test_trailing_pass_slots_do_not_create_demand(self):
        candidate_route = route(required=4)
        candidate_route[11]["hands"][-1] = ["PASS"]
        candidate_route[11]["hands"][-2] = ["PASS"]
        selected = {"farmer": ["PASS"], "hands": [], "market": []}
        out, report = recover_missing_hire(
            observation(), {}, selected, route=candidate_route,
            certify_prefix=prefix_with_budget(1000))
        self.assertEqual(out, selected)
        self.assertEqual(report["reason"], "route_capacity_satisfied")

    def test_two_missing_hands_are_not_partially_recovered(self):
        selected = {"farmer": ["PASS"], "hands": [], "market": [[]]}
        out, report = recover_missing_hire(
            observation(hands=2), {}, selected, route=route(required=4),
            certify_prefix=prefix_with_budget(1000))
        self.assertEqual(out, selected)
        self.assertEqual(report["reason"], "not_single_hire_recoverable")

    def test_buy_product_barrier_blocks_later_idle_slot(self):
        selected = {"farmer": ["PASS"], "hands": [],
                    "market": [["BUY_PRODUCT", "MILK", 1], []]}
        out, report = recover_missing_hire(
            observation(), {}, selected, route=route(),
            certify_prefix=prefix_with_budget(1000, unsupported=0))
        self.assertEqual(out, selected)
        self.assertEqual(report["reason"], "no_funded_inert_slot")
        self.assertEqual(report["candidate_failures"][0]["reason"],
                         "unsupported_prefix_barrier")


if __name__ == "__main__":
    unittest.main(verbosity=2)
