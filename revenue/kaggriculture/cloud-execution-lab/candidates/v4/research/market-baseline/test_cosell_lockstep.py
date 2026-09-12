#!/usr/bin/env python3
from __future__ import annotations

import unittest

import cosell_lockstep as m


class FakeEngine:
    PRODUCTS = ("WOOL", "WHEAT", "FERTILIZER")

    @staticmethod
    def _new_farm(board_size, money):
        return {"money": float(money)}

    @staticmethod
    def _new_private():
        return {"shed": {}}

    @staticmethod
    def _new_market():
        market = {"inventory": {x: 10000 for x in FakeEngine.PRODUCTS}, "prices": {}}
        FakeEngine._refresh_prices(market)
        return market

    @staticmethod
    def _refresh_prices(market):
        # Deterministic monotone SELL curve sufficient to exercise the oracle's
        # alignment/terminal-state logic. Exact official-engine coverage is a
        # separate test below when the repository engine is present.
        for item in FakeEngine.PRODUCTS:
            market["prices"][item] = max(1, 1000 - market["inventory"][item])

    @staticmethod
    def _parse(row):
        if not isinstance(row, list) or len(row) < 3 or row[0] != "SELL":
            return None
        item, qty = row[1], row[2]
        if item not in FakeEngine.PRODUCTS or type(qty) is not int or qty <= 0:
            return None
        return {"item": item, "remaining": qty}

    @staticmethod
    def _process_market(states, env):
        cap = max(1, int(env.configuration.get("maxMarketOrdersPerTurn", 10)))
        for slot in range(cap):
            orders = []
            for state in states:
                rows = state.action.get("market", [])
                orders.append(FakeEngine._parse(rows[slot]) if slot < len(rows) else None)
            while any(o is not None and o["remaining"] > 0 for o in orders):
                quoted = []
                for player, order in enumerate(orders):
                    if order is None or order["remaining"] <= 0:
                        quoted.append(None)
                        continue
                    item = order["item"]
                    if states[player].observation.private["shed"].get(item, 0) <= 0:
                        quoted.append(None)
                        orders[player] = None
                        continue
                    quoted.append((item, states[0].observation.market["prices"][item]))
                committed = False
                for player, q in enumerate(quoted):
                    if q is None:
                        continue
                    item, price = q
                    private = states[player].observation.private
                    if private["shed"].get(item, 0) <= 0:
                        orders[player] = None
                        continue
                    private["shed"][item] -= 1
                    states[0].observation.farms[player]["money"] += price
                    # Official engine: a SELL quoted at the $1 floor does not
                    # increase public supply. Mirror that edge exactly.
                    if price > 1:
                        states[0].observation.market["inventory"][item] += 1
                    orders[player]["remaining"] -= 1
                    committed = True
                if not committed:
                    break
                FakeEngine._refresh_prices(states[0].observation.market)


class CosellOracleTests(unittest.TestCase):
    def test_aligned_cosell_beats_wait_on_falling_price(self):
        r = m.compare(FakeEngine, item="WOOL", inventory=900, self_qty=10, rival_qty=10)
        self.assertGreater(r["simultaneous_gain_vs_wait"], 0)
        self.assertEqual(r["misaligned_gain_vs_wait"], 0)
        self.assertTrue(r["same_terminal_state"])
        self.assertEqual(r["terminal_market_inventory"], 920)

    def test_zero_rival_is_no_effect(self):
        r = m.compare(FakeEngine, item="WOOL", inventory=900, self_qty=10, rival_qty=0)
        self.assertEqual(r["simultaneous_gain_vs_wait"], 0)
        self.assertEqual(r["misaligned_gain_vs_wait"], 0)

    def test_partial_overlap_only_shields_shared_units(self):
        short = m.compare(FakeEngine, item="WOOL", inventory=900, self_qty=10, rival_qty=3)
        full = m.compare(FakeEngine, item="WOOL", inventory=900, self_qty=10, rival_qty=10)
        self.assertGreater(short["simultaneous_gain_vs_wait"], 0)
        self.assertLess(short["simultaneous_gain_vs_wait"], full["simultaneous_gain_vs_wait"])

    def test_same_callback_misalignment_equals_wait(self):
        r = m.compare(FakeEngine, item="WHEAT", inventory=910, self_qty=7, rival_qty=5)
        self.assertEqual(r["misaligned_same_callback_self_revenue"], r["wait_behind_self_revenue"])

    def test_quantity_type_poison_fails_closed(self):
        for bad in (True, 1.0, "1", -1):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                m.compare(FakeEngine, item="WOOL", inventory=900, self_qty=bad, rival_qty=1)

    def test_unknown_item_fails_closed(self):
        with self.assertRaises(ValueError):
            m.compare(FakeEngine, item="NOT_REAL", inventory=900, self_qty=1, rival_qty=1)

    def test_curve_preserves_requested_inventory_points(self):
        rows = m.collision_curve(FakeEngine, item="WOOL", inventories=[900, 910, 920], quantity=2)
        self.assertEqual([x["inventory"] for x in rows], [900, 910, 920])
        self.assertTrue(all(x["simultaneous_gain_vs_wait"] > 0 for x in rows))

    def test_floor_transition_refuses_unequal_terminal_counterfactual(self):
        # At inventory 998 the aligned pair is quoted $2/$2 and both units add
        # supply, while wait-behind quotes $2 then $1 and the floor sale does
        # not add supply. The oracle must refuse to call that a pure cash delta.
        with self.assertRaises(AssertionError):
            m.compare(FakeEngine, item="WOOL", inventory=998, self_qty=1, rival_qty=1)

    def test_repository_engine_exact_when_present(self):
        path = m.default_engine_path()
        if not path.is_file():
            self.skipTest("repository engine not mounted in this execution seat")
        engine = m.load_engine(path)
        self.assertEqual(engine._cosell_source_identity["python_git_blob"], m.ENGINE_BLOB)
        self.assertEqual(engine._cosell_source_identity["json_git_blob"], m.ENGINE_JSON_BLOB)
        r = m.compare(engine, item="WOOL", inventory=10000, self_qty=10, rival_qty=10)
        self.assertEqual(r["terminal_market_inventory"], 10020)
        self.assertEqual(r["misaligned_gain_vs_wait"], 0)
        self.assertGreater(r["simultaneous_gain_vs_wait"], 0)


if __name__ == "__main__":
    unittest.main()
