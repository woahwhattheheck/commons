"""Focused full-interpreter tests for the corrected Gemini EGG timing frontier."""
import copy
import os
from pathlib import Path
import unittest

import gemini_egg_timing as gt
import sale_window as sw

REFERENCE = Path(os.environ.get("TITAN_REFERENCE", "checks/reference"))
PASS = {"farmer": ["PASS"], "hands": [], "market": []}


def action(*market):
    out = copy.deepcopy(PASS)
    out["market"] = list(market)
    return out


class GeminiEggTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine, cls.Struct = sw.load_engine(REFERENCE)

    def fixture(self, *, step=4, stock=12, rival_stock=0, inventory=10000,
                shops=("BAKERY",) * 8, cap=10):
        state, env = sw.initialize(self.engine, self.Struct, configuration={
            "weedSpawnChance": 0,
            "maxMarketOrdersPerTurn": cap,
        })
        for seat, s in enumerate(state):
            s.observation.step = step
            s.observation.day = step // 24
            s.observation.hour = step % 24
            s.observation.private["shed"]["EGG"] = stock if seat == 0 else rival_stock
            s.observation.farms[seat]["money"] = 0
        state[0].observation.market["inventory"]["EGG"] = inventory
        state[0].observation.town["unlocked_shops"] = list(shops)
        self.engine._refresh_prices(state[0].observation.market)
        return state, env

    @staticmethod
    def tape(own, rival=None):
        rival = rival or [action() for _ in own]
        return [[a, b] for a, b in zip(own, rival)]

    def test_town_egg_absorption_creates_profitable_later_window(self):
        state, env = self.fixture()
        own = [action(["SELL", "EGG", 12])] + [action() for _ in range(5)]
        report = gt.search(
            self.engine, state, env, self.tape(own), start_step=4, seat=0,
            source_turn=0, source_row_index=0, max_delay=5,
        )
        self.assertIsNotNone(report["best_positive"])
        self.assertGreater(report["best_positive"]["own_cash_delta"], 0)
        self.assertTrue(report["best_positive"]["realized_retiming"])
        # Step 8 consumes after market; step 9 is the first placement that can
        # capture both the step-4 and step-8 BAKERY depletion pulses.
        self.assertEqual(report["best_positive"]["target_step"], 9)
        self.assertFalse(report["policy_claim"])
        self.assertFalse(report["literal_direct_egg_short_squeeze_supported"])

    def test_fixed_rival_supply_can_destroy_waiting_edge(self):
        state, env = self.fixture(rival_stock=200)
        own = [action(["SELL", "EGG", 12])] + [action() for _ in range(2)]
        # Rival supply is quoted in the same source turn. The baseline receives
        # the precommit quote, while every delayed candidate faces that supply
        # after commit (net of town depletion), so waiting must not be blessed.
        rival = [action(["SELL", "EGG", 200]), action(), action()]
        report = gt.search(
            self.engine, state, env, self.tape(own, rival), start_step=4, seat=0,
            source_turn=0, source_row_index=0, max_delay=2,
        )
        self.assertIsNone(report["best_positive"])
        self.assertTrue(any(row["realized_retiming"] for row in report["candidates"]))

    def test_refuses_non_egg_or_nonpositive_source(self):
        state, env = self.fixture()
        for row in (["SELL", "MILK", 1], ["BUY_PRODUCT", "EGG", 1],
                    ["SELL", "EGG", 0], ["SELL", "EGG", -1]):
            tape = self.tape([action(row), action()])
            with self.assertRaises(ValueError):
                gt.search(
                    self.engine, state, env, tape, start_step=4, seat=0,
                    source_turn=0, source_row_index=0, max_delay=1,
                )

    def test_destination_never_displaces_live_economics(self):
        full = self.tape([
            action(["SELL", "EGG", 1]),
            action(*([ ["HIRE"] ] * 10)),
            action(["PASS"], ["HIRE"]),
        ])
        self.assertEqual(
            gt.candidate_destinations(full, seat=0, source_turn=0, max_delay=2, cap=10),
            [(2, 0)],
        )

    def test_input_tape_is_immutable(self):
        state, env = self.fixture()
        tape = self.tape([action(["SELL", "EGG", 12]), action(), action()])
        before = sw.digest(tape)
        gt.search(
            self.engine, state, env, tape, start_step=4, seat=0,
            source_turn=0, source_row_index=0, max_delay=2,
        )
        self.assertEqual(before, sw.digest(tape))

    def test_zero_stock_is_not_a_realized_retiming(self):
        state, env = self.fixture(stock=0)
        tape = self.tape([action(["SELL", "EGG", 12]), action()])
        report = gt.search(
            self.engine, state, env, tape, start_step=4, seat=0,
            source_turn=0, source_row_index=0, max_delay=1,
        )
        self.assertIsNone(report["best_positive"])
        self.assertEqual(report["candidates"][0]["source_filled_units"], 0)
        self.assertFalse(report["candidates"][0]["realized_retiming"])


if __name__ == "__main__":
    unittest.main()
