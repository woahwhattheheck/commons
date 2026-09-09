# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from types import SimpleNamespace
import unittest

from animal_admission import order_report, screen_selected


ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP", "first_yield_day": 4,
              "interval": 1, "max_held": 4, "product": "EGG"},
    "COW": {"cost": 400, "structure": "PASTURE", "first_yield_day": 8,
            "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6,
              "interval": 3, "max_held": 6, "product": "WOOL"},
}
QUOTES = {"WHEAT": 25, "FERTILIZER": 100, "EGG": 50, "MILK": 160, "WOOL": 200}
M = SimpleNamespace(ANIMALS=ANIMALS,
                    market_price=lambda item, inventory: QUOTES[item])


def obs(step):
    return {"step": step, "market": {"inventory": {k: 10000 for k in QUOTES}}}


class AnimalAdmissionTests(unittest.TestCase):
    def test_default_horizon_keeps_early_parent_order(self):
        selected = {"farmer": ["PASS"], "hands": [],
                    "market": [["BUY_ANIMAL", "GOOSE", 1]]}
        before = deepcopy(selected)
        result, report = screen_selected(M, obs(100), {}, selected)
        self.assertIs(result, selected)
        self.assertFalse(report["changed"])
        self.assertEqual(selected, before)
        self.assertTrue(report["orders"][0]["horizon_ok"])

    def test_physically_too_late_order_is_vetoed_in_place_slot(self):
        selected = {"farmer": ["PASS"], "hands": [],
                    "market": [["SELL", "MILK", 1], ["BUY_ANIMAL", "GOOSE", 1],
                               ["BUY_SEED", "WHEAT", 2]]}
        result, report = screen_selected(M, obs(625), {}, selected)
        self.assertTrue(report["changed"])
        self.assertEqual(result["market"], [["SELL", "MILK", 1], [],
                                            ["BUY_SEED", "WHEAT", 2]])
        self.assertEqual(selected["market"][1], ["BUY_ANIMAL", "GOOSE", 1])
        self.assertEqual(report["removed_slots"], [1])

    def test_species_boundary_differs_by_first_yield_delay(self):
        goose = order_report(M, obs(550), {}, "GOOSE", 1)
        cow = order_report(M, obs(550), {}, "COW", 1)
        self.assertTrue(goose["horizon_ok"])
        self.assertFalse(cow["horizon_ok"])
        self.assertLess(goose["first_production_step"], cow["first_production_step"])

    def test_unknown_animal_and_nonpositive_quantity_are_preserved(self):
        selected = {"market": [["BUY_ANIMAL", "LLAMA", 1],
                               ["BUY_ANIMAL", "GOOSE", 0]]}
        result, report = screen_selected(M, obs(700), {}, selected)
        self.assertIs(result, selected)
        self.assertFalse(report["changed"])
        self.assertTrue(all(not row["recognized"] for row in report["orders"]))

    def test_diagnostics_price_full_remaining_service_not_survival_only(self):
        report = order_report(M, obs(100), {}, "SHEEP", 1)
        self.assertGreater(report["production_events_upper"], 0)
        self.assertGreater(report["min_feed_units"], 0)
        self.assertEqual(report["animal_cost"], 500)
        self.assertIn("diagnostic_net_upper", report)

    def test_custom_episode_and_turn_length_define_boundary(self):
        cfg = {"episodeSteps": 100, "turnsPerDay": 10}
        report = order_report(M, obs(60), cfg, "GOOSE", 1)
        self.assertFalse(report["horizon_ok"])
        self.assertEqual(report["last_action_step"], 98)


if __name__ == "__main__":
    unittest.main()
