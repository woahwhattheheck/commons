# SPDX-License-Identifier: Apache-2.0
"""Focused S13 packaging/wiring contracts. Standard library only."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scheduler  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402

EXPECTED_TAIL_SHA256 = "ead794d663a01967723932613fef800a0345b67daabefcf6799c812c933a6a54"


def observation(step=718):
    return {
        "step": step,
        "player": 0,
        "farms": [
            {"money": 1000, "unlocked_quadrants": ["NW"], "hires_today": 0,
             "tiles": [[None]], "farmer": [0, 0], "hands": []},
            {"money": 1000, "unlocked_quadrants": ["NW"], "hires_today": 0,
             "tiles": [[None]], "farmer": [0, 0], "hands": []},
        ],
        "private": {"shed": {"WHEAT": 1}, "seeds": {}, "inventories": [{}]},
        "market": {"prices": {"WHEAT": 10}, "inventory": {"WHEAT": 50}},
        "town": {"unlocked_shops": ["BAKERY"]},
    }


def projected(_obs, _action, _cfg):
    return {}, {"shed": {"WHEAT": 5}}


class S13PackageContracts(unittest.TestCase):
    def test_exact_tail_artifact_hash(self):
        digest = hashlib.sha256((ROOT / "tail_settlement.py").read_bytes()).hexdigest()
        self.assertEqual(digest, EXPECTED_TAIL_SHA256)

    def test_config_key_exists_and_ships_off(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIn("s13_tail_sweep", data)
        self.assertIs(data["s13_tail_sweep"], False)
        features = Features(**data)
        self.assertIs(features.s13_tail_sweep, False)
        self.assertFalse(TitanAgent(features)._v3_active())

    def test_off_path_is_object_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 1]]}
        agent = TitanAgent(Features())
        agent.diagnostics = {}
        self.assertIs(agent._v3_post(observation(), {}, action), action)

    def test_on_path_uses_scheduler_projector_and_records_certificate(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 1]]}
        before = deepcopy(action)
        old = scheduler.post_units
        scheduler.post_units = projected
        try:
            agent = TitanAgent(Features(s13_tail_sweep=True))
            agent.diagnostics = {}
            out = agent._v3_post(
                observation(718),
                {"titan_v3": agent._v3_config(), "episodeSteps": 720,
                 "maxMarketOrdersPerTurn": 10, "townShopSellInterval": 4,
                 "townCenterSellInterval": 24},
                action,
            )
        finally:
            scheduler.post_units = old
        self.assertEqual(action, before)
        self.assertEqual(out["market"], [["SELL", "WHEAT", 5]])
        report = agent.diagnostics["v3"]["s13_tail_sweep"]
        self.assertTrue(report["changed"])
        self.assertTrue(report["execution_certified"])
        self.assertEqual(report["added_sell_units"], {"WHEAT": 4})

    def test_shop_consumed_product_is_held_before_last_shop_tick(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 1]]}
        old = scheduler.post_units
        scheduler.post_units = projected
        try:
            agent = TitanAgent(Features(s13_tail_sweep=True))
            agent.diagnostics = {}
            out = agent._v3_post(
                observation(700),
                {"titan_v3": agent._v3_config(), "episodeSteps": 720,
                 "maxMarketOrdersPerTurn": 10, "townShopSellInterval": 4,
                 "townCenterSellInterval": 24},
                action,
            )
        finally:
            scheduler.post_units = old
        self.assertEqual(out, action)
        report = agent.diagnostics["v3"]["s13_tail_sweep"]
        self.assertFalse(report["changed"])
        self.assertIn("WHEAT", report["held_for_consumption"])

    def test_projector_exception_fails_closed(self):
        def boom(*_args, **_kwargs):
            raise RuntimeError("probe")

        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 1]]}
        old = scheduler.post_units
        scheduler.post_units = boom
        try:
            agent = TitanAgent(Features(s13_tail_sweep=True))
            agent.diagnostics = {}
            out = agent._v3_post(
                observation(718),
                {"titan_v3": agent._v3_config(), "episodeSteps": 720},
                action,
            )
        finally:
            scheduler.post_units = old
        self.assertEqual(out, action)
        report = agent.diagnostics["v3"]["s13_tail_sweep"]
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "baseline_projection_failed")


if __name__ == "__main__":
    unittest.main()
