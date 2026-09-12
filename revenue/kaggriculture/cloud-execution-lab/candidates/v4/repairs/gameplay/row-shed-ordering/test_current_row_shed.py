# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import math
import random
import unittest

import current_row_shed as rs

PARAMS = {
    "WHEAT": (25, 400, "sqrt", 0.80, "log", 0.20),
    "CARROT": (35, 450, "hinge", 1.00, "sqrt", 0.70),
    "TOMATO": (60, 200, "hinge", 0.40, "sqrt", 0.60),
    "STRAWBERRY": (120, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON": (250, 300, "log", 0.20, "sq", 3.60),
    "EGG": (50, 332, "hinge", 0.40, "log", 0.20),
    "MILK": (160, 122, "sqrt", 0.60, "linear", 1.60),
    "WOOL": (200, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 200, "linear", 0.40, "linear", 0.40),
}
PRODUCTS = tuple(PARAMS)
I0 = 10_000


def shape(name, x, span):
    x = max(0.0, x)
    if name == "linear": return x
    if name == "sq": return x * x
    if name == "sqrt": return x ** 0.5
    if name == "log": return math.log(1.0 + x)
    if name == "hinge":
        u = x / span
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x


def price(item, inventory):
    base, span, below_f, below_t, above_f, above_t = PARAMS[item]
    if inventory < I0:
        amp = below_t * base / shape(below_f, span, span)
        value = base + amp * shape(below_f, I0 - inventory, span)
    else:
        amp = above_t * base / shape(above_f, span, span)
        value = base - amp * shape(above_f, inventory - I0, span)
    return max(1, int(round(value)))


def legacy_reference(market, inventory, shed=None):
    """Literal small reference for the reviewed 7cbe552 order_sells body."""
    lead = 0
    while lead < len(market) and market[lead] and market[lead][0] == "SELL":
        lead += 1
    if lead < 2:
        return market
    if shed is not None:
        block = market[:lead]
        if any(len(o) < 3 or type(o[2]) is not int or o[2] < 0 for o in block):
            return market
        if not isinstance(shed, dict) or any(
            type(shed.get(o[1])) is not int or shed[o[1]] < 0 for o in block
        ):
            shed = None

    def drop(order):
        item = order[1]
        if item not in PARAMS or len(order) < 3:
            return 0
        level = int(inventory.get(item, I0))
        quantity = max(0, int(order[2]))
        if shed is not None:
            quantity = min(quantity, max(0, shed[item]))
        return (price(item, level) - price(item, level + quantity)) * quantity

    return sorted(market[:lead], key=drop, reverse=True) + market[lead:]


def obs(inventory=None, params=None):
    result = {"market": {"inventory": dict(inventory or {})}}
    if params is not None:
        result["market"]["params"] = params
    return result


class RowShedPure(unittest.TestCase):
    def call(self, market, inventory=None, shed=None):
        return rs.order_leading_sells(
            market, dict(inventory or {}), shed,
            price_at=price, priced_items=PRODUCTS,
        )

    def test_sellable_units_change_priority(self):
        market = [["SELL", "WOOL", 1000], ["SELL", "MILK", 6], ["HIRE"], ["SELL", "EGG", 3]]
        self.assertEqual(
            self.call(copy.deepcopy(market), shed={"WOOL": 1, "MILK": 6}),
            [["SELL", "MILK", 6], ["SELL", "WOOL", 1000], ["HIRE"], ["SELL", "EGG", 3]],
        )

    def test_falsey_slot_is_barrier_and_tail_index_is_unchanged(self):
        market = [["SELL", "WOOL", 1000], [], ["SELL", "MILK", 6]]
        self.assertEqual(self.call(copy.deepcopy(market), shed={"WOOL": 1}), market)

    def test_rows_and_quantities_are_never_edited(self):
        market = [["SELL", "WOOL", 1000], ["SELL", "MILK", 6], ["SELL", "STRAWBERRY", 40], ["BUY_SEED", "WHEAT", 3]]
        snapshot = copy.deepcopy(market)
        out = self.call(market, shed={"WOOL": 0, "MILK": 6, "STRAWBERRY": 2})
        self.assertEqual(sorted(map(tuple, out[:3])), sorted(map(tuple, snapshot[:3])))
        self.assertEqual(out[3:], snapshot[3:])
        self.assertEqual(market, snapshot)

    def test_incomplete_projection_falls_back_for_whole_block(self):
        market = [["SELL", "WOOL", 1000], ["SELL", "MILK", 6], ["HIRE"]]
        expected = legacy_reference(copy.deepcopy(market), {}, None)
        self.assertEqual(self.call(copy.deepcopy(market), shed={"MILK": 6}), expected)

    def test_type_poisoned_projection_falls_back_for_whole_block(self):
        market = [["SELL", "WOOL", 1000], ["SELL", "MILK", 6], ["HIRE"]]
        expected = legacy_reference(copy.deepcopy(market), {}, None)
        for bad in (True, 1.0, "1", -1):
            with self.subTest(bad=bad):
                self.assertEqual(self.call(copy.deepcopy(market), shed={"WOOL": bad, "MILK": 6}), expected)

    def test_poisoned_request_preserves_raw_parent_order(self):
        for quantity in (True, 1.0, "1", -1):
            market = [["SELL", "WOOL", quantity], ["SELL", "MILK", 6], ["HIRE"]]
            with self.subTest(quantity=quantity):
                self.assertEqual(self.call(copy.deepcopy(market), shed={"WOOL": 1, "MILK": 6}), market)

    def test_equal_scores_are_stable(self):
        market = [["SELL", "UNKNOWN_A", 1], ["SELL", "UNKNOWN_B", 2], ["HIRE"]]
        self.assertEqual(self.call(copy.deepcopy(market), shed={"UNKNOWN_A": 1, "UNKNOWN_B": 2}), market)

    def test_random_valid_domain_matches_exact_legacy_reference(self):
        rng = random.Random(20260911)
        for _ in range(800):
            n = rng.randint(0, 5)
            block = []
            shed = {}
            inventory = {}
            for _index in range(n):
                item = rng.choice(PRODUCTS)
                quantity = rng.randint(0, 1200)
                block.append(["SELL", item, quantity])
                shed[item] = rng.randint(0, 25)
                inventory[item] = rng.randint(9500, 10600)
            tail = rng.choice(([], [["HIRE"]], [[], ["SELL", "WOOL", 3]], [["BUY_SEED", "WHEAT", 1]]))
            market = block + copy.deepcopy(tail)
            expected = legacy_reference(copy.deepcopy(market), copy.deepcopy(inventory), copy.deepcopy(shed))
            actual = self.call(copy.deepcopy(market), copy.deepcopy(inventory), copy.deepcopy(shed))
            self.assertEqual(actual, expected)


class CurrentABIEnvelope(unittest.TestCase):
    def apply(self, action, observation, shed):
        return rs.transform_selected(
            action, observation, shed, price_at=price, priced_items=PRODUCTS,
        )

    def test_success_returns_new_action_but_preserves_row_objects(self):
        a = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WOOL", 1000], ["SELL", "MILK", 6]]}
        first, second = a["market"]
        out = self.apply(a, obs(), {"WOOL": 1, "MILK": 6})
        self.assertIsNot(out, a)
        self.assertIs(out["market"][0], second)
        self.assertIs(out["market"][1], first)
        self.assertEqual(a["market"], [["SELL", "WOOL", 1000], ["SELL", "MILK", 6]])

    def test_noop_returns_exact_parent_object(self):
        a = {"market": [["SELL", "WOOL", 1], [], ["SELL", "MILK", 6]]}
        self.assertIs(self.apply(a, obs(), {"WOOL": 1}), a)

    def test_truthy_custom_market_params_fail_closed(self):
        a = {"market": [["SELL", "WOOL", 1000], ["SELL", "MILK", 6]]}
        self.assertIs(self.apply(a, obs(params={"WOOL": {"base": 999}}), {"WOOL": 1, "MILK": 6}), a)

    def test_falsey_params_keep_default_market_contract(self):
        a = {"market": [["SELL", "WOOL", 1000], ["SELL", "MILK", 6]]}
        out = self.apply(a, obs(params={}), {"WOOL": 1, "MILK": 6})
        self.assertEqual(out["market"][0], ["SELL", "MILK", 6])

    def test_malformed_current_abi_envelopes_fail_closed(self):
        base = {"market": [["SELL", "WOOL", 1000], ["SELL", "MILK", 6]]}
        cases = (
            (None, obs(), {"WOOL": 1, "MILK": 6}),
            ({"market": "bad"}, obs(), {"WOOL": 1, "MILK": 6}),
            ({"market": [["SELL", "WOOL", 1000], 1]}, obs(), {"WOOL": 1, "MILK": 6}),
            (base, {"market": []}, {"WOOL": 1, "MILK": 6}),
            (base, {"market": {"inventory": "bad"}}, {"WOOL": 1, "MILK": 6}),
            (base, obs(), [1, 2]),
        )
        for action, observation, shed in cases:
            with self.subTest(action=action, observation=observation, shed=shed):
                self.assertIs(self.apply(action, observation, shed), action)

    def test_quote_or_inventory_poison_fails_closed(self):
        a = {"market": [["SELL", "WOOL", 1000], ["SELL", "MILK", 6]]}
        out = rs.transform_selected(
            a, obs({"WOOL": object(), "MILK": 10000}), {"WOOL": 1, "MILK": 6},
            price_at=price, priced_items=PRODUCTS,
        )
        self.assertIs(out, a)
        out = rs.transform_selected(
            a, obs(), {"WOOL": 1, "MILK": 6},
            price_at=lambda *_args: (_ for _ in ()).throw(ValueError("poison")),
            priced_items=PRODUCTS,
        )
        self.assertIs(out, a)

    def test_raw_slot_cardinality_and_tail_identity_survive_reorder(self):
        tail = ["BUY_SEED", "WHEAT", 1]
        a = {"market": [["SELL", "WOOL", 1000], ["SELL", "MILK", 6], tail, [], ["SELL", "EGG", 4]]}
        out = self.apply(a, obs(), {"WOOL": 1, "MILK": 6})
        self.assertEqual(len(out["market"]), len(a["market"]))
        self.assertIs(out["market"][2], tail)
        self.assertIs(out["market"][3], a["market"][3])
        self.assertIs(out["market"][4], a["market"][4])


if __name__ == "__main__":
    unittest.main()
