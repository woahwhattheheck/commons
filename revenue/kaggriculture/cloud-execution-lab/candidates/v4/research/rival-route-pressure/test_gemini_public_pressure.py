from __future__ import annotations

from copy import deepcopy
import math
import unittest

import gemini_public_pressure as G
import rival_route_pressure as R


CFG = {
    "episodeSteps": 720,
    "townShopSellInterval": 4,
    "townCenterSellInterval": 24,
}


def observation(
    *,
    step=40,
    own_quadrants=("NW",),
    rival_quadrants=("NW", "NE"),
    prices=None,
    shops=None,
    rival_tiles=None,
    private=None,
):
    own = {"tiles": [[None]], "money": 3000}
    rival = {
        "tiles": rival_tiles if rival_tiles is not None else [[None]],
        "money": 3000,
    }
    if own_quadrants is not None:
        own["unlocked_quadrants"] = list(own_quadrants)
    if rival_quadrants is not None:
        rival["unlocked_quadrants"] = list(rival_quadrants)
    return {
        "step": step,
        "player": 0,
        "farms": [own, rival],
        "private": private if private is not None else {"shed": {"WOOL": 999}},
        "town": {"unlocked_shops": list(shops or [])},
        "market": {"inventory": {}, "prices": dict(prices or {})},
    }


class GeminiPublicPressureTests(unittest.TestCase):
    def test_expansion_and_dump_witnesses_can_coexist(self):
        obs = observation(step=40, prices={"WOOL": 20})
        got = G.public_pressure_profile(obs, CFG, {"WOOL": 40}, horizon=1)
        self.assertTrue(got["expansion_evidence"]["gemini_early_expander_witness"])
        self.assertTrue(got["has_dump_witness"])
        self.assertEqual(got["dump_witness_products"], ["WOOL"])

    def test_shop_arb_is_exact_drain_not_fractional_weight(self):
        obs = observation(step=4, shops=["YARN_STORE"], prices={"WOOL": 20})
        got = G.public_pressure_profile(obs, CFG, {"WOOL": 20}, horizon=1)
        row = next(row for row in got["product_rows"] if row["product"] == "WOOL")
        self.assertEqual(row["known_current_town_drain"], 2)
        self.assertTrue(row["has_known_current_town_drain"])
        self.assertFalse(got["overrides_engine_absorption"])

    def test_rival_visible_supply_is_reported_without_private_inventory(self):
        tiles = [[{"kind": "PASTURE", "animal": "SHEEP", "yield_units": 3}]]
        a = observation(rival_tiles=tiles, private={"shed": {"WOOL": 0}})
        b = observation(rival_tiles=tiles, private={"shed": {"WOOL": 999999}})
        ga = G.public_pressure_profile(a, CFG, horizon=1)
        gb = G.public_pressure_profile(b, CFG, horizon=1)
        self.assertEqual(ga, gb)
        row = next(row for row in ga["product_rows"] if row["product"] == "WOOL")
        self.assertEqual(row["visible_rival_standing_yield"], 3)
        self.assertEqual(row["visible_rival_productive_sources"], 1)

    def test_missing_quadrant_surface_keeps_other_public_evidence(self):
        obs = observation(
            own_quadrants=None,
            rival_quadrants=None,
            prices={"MILK": 20},
            shops=["PIZZA_SHOP"],
        )
        got = G.public_pressure_profile(obs, CFG, {"MILK": 40}, horizon=1)
        self.assertFalse(got["expansion_evidence"]["available"])
        self.assertEqual(got["dump_witness_products"], ["MILK"])

    def test_horizon_is_clipped_to_episode_end(self):
        got = G.public_pressure_profile(observation(step=719), CFG, horizon=24)
        self.assertEqual(got["end"], 719)

    def test_step_outside_episode_fails_closed(self):
        with self.assertRaises(R.UnsupportedEvidence):
            G.public_pressure_profile(observation(step=720), CFG)

    def test_nan_prior_price_fails_closed(self):
        with self.assertRaises(R.UnsupportedEvidence):
            G.public_pressure_profile(
                observation(prices={"WOOL": 20}), CFG, {"WOOL": math.nan})

    def test_duplicate_quadrants_fail_closed(self):
        with self.assertRaises(R.UnsupportedEvidence):
            G.public_pressure_profile(
                observation(rival_quadrants=("NW", "NW")), CFG)

    def test_report_is_non_authoritative_and_inputs_are_not_mutated(self):
        obs = observation(prices={"WOOL": 20}, shops=["YARN_STORE"])
        prior = {"WOOL": 40}
        before = deepcopy((obs, prior))
        got = G.public_pressure_profile(obs, CFG, prior, horizon=2)
        self.assertEqual((obs, prior), before)
        self.assertFalse(got["decision_authority"])
        self.assertFalse(got["mutates_action"])
        self.assertNotIn("allow", got)
        self.assertNotIn("deny", got)
        self.assertNotIn("choose", got)

    def test_exact_threshold_matches_original_o01_boundary(self):
        got = G.public_pressure_profile(
            observation(prices={"WHEAT": 25}), CFG, {"WHEAT": 40}, horizon=1)
        self.assertIn("WHEAT", got["dump_witness_products"])


if __name__ == "__main__":
    unittest.main()
