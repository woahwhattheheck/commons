# SPDX-License-Identifier: Apache-2.0
"""Production-wiring contracts for V3.1 H4 strawberry top-up.

Runs from a materialized V3 package after apply_v3 + apply_h4.  The mechanism itself
has its own reviewed experiment suite; these checks bind package defaults, dependency,
and the stronger OFF-path identity used for production wiring.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path
import unittest

import r04_full_router as r04
import r04_h4_strawberry as h4
from titan_runtime import Features, TitanAgent

ROOT = Path(__file__).resolve().parents[1]


def observation(step=5):
    return {
        "step": step,
        "player": 0,
        "market": {"inventory": {}, "prices": {item: 100 for item in r04.PRODUCTS}},
    }


class H4ProductionWiring(unittest.TestCase):
    def test_package_key_ships_false(self):
        config = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIn("r04_strawberry_topup", config)
        self.assertIs(config["r04_strawberry_topup"], False)
        self.assertIs(Features().r04_strawberry_topup, False)

    def test_h4_is_subordinate_to_r04_delegate(self):
        act_source = inspect.getsource(TitanAgent.act)
        self.assertIn(
            "if self.features.r03_full_router or self.features.r04_sale_window:",
            act_source,
        )
        self.assertNotIn(
            "or self.features.r04_strawberry_topup",
            act_source,
        )
        route_source = inspect.getsource(TitanAgent._v3_r03_act)
        self.assertIn("if self.features.r04_strawberry_topup:", route_source)
        self.assertIn("from r04_h4_strawberry import install", route_source)
        self.assertIn("else:\n                    from r04_full_router import install", route_source)

    def test_disabled_wrapper_matches_current_r04_post_policy_chain(self):
        saved = {
            "policy": r04.POLICY_AGENT,
            "row": r04.ROW_ORDER,
            "flush": r04.EVENING_FLUSH,
            "opening": r04.OPEN_ROUNDTRIP,
            "h4": h4.STRAWBERRY_TOPUP,
        }

        def stub(obs, configuration=None):
            return {
                "farmer": ["PASS"],
                "hands": [],
                "market": [["SELL", "WHEAT", 10], ["SELL", "WOOL", 10]],
            }

        try:
            r04.POLICY_AGENT = stub
            r04.ROW_ORDER = True
            r04.EVENING_FLUSH = False
            r04.OPEN_ROUNDTRIP = 0
            h4.STRAWBERRY_TOPUP = False
            obs = observation()
            cfg = {}
            expected = r04.v3_agent(obs, cfg)
            actual = h4.h4_agent(obs, cfg)
            self.assertEqual(actual, expected)
        finally:
            r04.POLICY_AGENT = saved["policy"]
            r04.ROW_ORDER = saved["row"]
            r04.EVENING_FLUSH = saved["flush"]
            r04.OPEN_ROUNDTRIP = saved["opening"]
            h4.STRAWBERRY_TOPUP = saved["h4"]

    def test_reviewed_h4_module_remains_default_off(self):
        self.assertEqual(h4.KEY, "r04_strawberry_topup")
        self.assertIs(h4.STRAWBERRY_TOPUP, False)
        source = inspect.getsource(h4.h4_agent)
        self.assertLess(source.index("reconcile_strawberry"), source.index("base.order_sells"))
        self.assertLess(source.index("base.order_sells"), source.index("base.evening_flush"))
        self.assertLess(source.index("base.evening_flush"), source.index("base.OPEN_ROUNDTRIP"))


if __name__ == "__main__":
    unittest.main()
