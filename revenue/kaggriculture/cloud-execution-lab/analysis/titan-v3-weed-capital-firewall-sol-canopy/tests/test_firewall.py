from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from weed_capital_firewall import transform


def observation(*, money=142, tile=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[2][4] = tile
    return {
        "player": 0,
        "farms": [{"money": money, "tiles": tiles}, {"money": 0, "tiles": copy.deepcopy(tiles)}],
    }


class FirewallTests(unittest.TestCase):
    def setUp(self):
        self.config = {"maxMarketOrdersPerTurn": 10}
        self.costs = {"COW": 400, "SHEEP": 500, "GOOSE": 300}
        self.queue = {
            "farmer": ["PLACE", "FERTILIZER", 3],
            "hands": [["PASS"]],
            "market": [["SELL", "FERTILIZER", 3], ["BUY_ANIMAL", "COW", 1]],
        }

    def test_exact_reduced_cascade_is_blocked_without_reordering(self):
        obs = observation(tile={"kind": "PASTURE", "animal": "COW"})
        result, report = transform(obs, self.config, self.queue, {(4, 2)}, self.costs)
        self.assertTrue(report["changed"])
        self.assertEqual(report["slot"], 1)
        self.assertEqual(result["market"], [["SELL", "FERTILIZER", 3], []])
        self.assertEqual(result["farmer"], self.queue["farmer"])
        self.assertEqual(len(result["market"]), len(self.queue["market"]))
        self.assertEqual(self.queue["market"][1], ["BUY_ANIMAL", "COW", 1])

    def test_pre_funded_purchase_is_preserved(self):
        obs = observation(money=400, tile={"kind": "PASTURE", "animal": "COW"})
        result, report = transform(obs, self.config, self.queue, {(4, 2)}, self.costs)
        self.assertIs(result, self.queue)
        self.assertFalse(report["changed"])

    def test_no_realized_asset_is_identity(self):
        result, report = transform(observation(), self.config, self.queue, {(4, 2)}, self.costs)
        self.assertIs(result, self.queue)
        self.assertEqual(report["reason"], "weed_asset_not_realized")

    def test_different_species_purchase_is_preserved(self):
        obs = observation(tile={"kind": "PASTURE", "animal": "COW"})
        action = copy.deepcopy(self.queue)
        action["market"][1] = ["BUY_ANIMAL", "SHEEP", 1]
        result, report = transform(obs, self.config, action, {(4, 2)}, self.costs)
        self.assertIs(result, action)
        self.assertFalse(report["changed"])

    def test_no_earlier_sale_is_preserved(self):
        obs = observation(tile={"kind": "PASTURE", "animal": "COW"})
        action = copy.deepcopy(self.queue)
        action["market"] = [["BUY_ANIMAL", "COW", 1]]
        result, report = transform(obs, self.config, action, {(4, 2)}, self.costs)
        self.assertIs(result, action)
        self.assertFalse(report["changed"])

    def test_invalid_site_fails_closed(self):
        obs = observation(tile={"kind": "PASTURE", "animal": "COW"})
        result, report = transform(obs, self.config, self.queue, {(40, 20)}, self.costs)
        self.assertIs(result, self.queue)
        self.assertEqual(report["reason"], "invalid_weed_site")

    def test_market_limit_is_respected(self):
        obs = observation(tile={"kind": "PASTURE", "animal": "COW"})
        result, report = transform(obs, {"maxMarketOrdersPerTurn": 1}, self.queue, {(4, 2)}, self.costs)
        self.assertIs(result, self.queue)
        self.assertFalse(report["changed"])


if __name__ == "__main__":
    unittest.main()
