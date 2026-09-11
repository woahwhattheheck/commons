# SPDX-License-Identifier: Apache-2.0
"""R04 lane E3 (price-forecaster): forward price-path simulation + sale deferral.

    python -m unittest -v checks/test_v3_r04_price_forecaster.py

Covers the pinned price-function port (cross-checked against the router's own
_ro_price on an inventory grid), deterministic town-consumption projection,
the rival-flow estimator, the keep/defer decision (glut now + scarcity later
defers; scarcity now + glut later keeps; fertilizer never defers), the
apply_* rewrite (drops/shrinks SELL rows only, never raises, inactive outside
steps 288-717), the cash guard (upcoming tape purchases are funded first),
and the install()/apply_v3.py/TITAN-CONFIG wiring. Standard library only.
"""
from __future__ import annotations

import copy
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_full_router as r04  # noqa: E402
import r04_price_forecaster as pf  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402

CONFIG = {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 10, "shedCapacity": 100,
          "maxMarketOrdersPerTurn": 10, "farmHandCostMult": 1}


def synthetic_observation(step, market_rows=None, inventory=None, prices=None,
                          shops=(), money=100000, player=0):
    size = 10
    tiles = [["LOCKED"] * size for _ in range(size)]
    farm = {"tiles": tiles, "farmer": [4, 4], "hands": [], "money": money,
            "unlocked_quadrants": ["NW"], "hires_today": 0}
    inv = {p: 10000 for p in pf.PRODUCTS}
    inv.update(inventory or {})
    prc = {p: pf.market_price(p, inv[p]) for p in pf.PRODUCTS}
    prc.update(prices or {})
    return {"step": step, "day": step // 24, "hour": step % 24, "player": player,
            "farms": [farm, copy.deepcopy(farm)],
            "private": {"inventories": [{}], "shed": {}},
            "market": {"inventory": inv, "prices": prc,
                       "rows": [list(r) for r in (market_rows or [])]},
            "town": {"unlocked_shops": list(shops)}}


def action_with_market(rows):
    return {"farmer": ["PASS"], "hands": [],
            "market": [list(r) for r in rows]}


def blank_tape():
    return [{"farmer": ["PASS"], "hands": [], "market": []}
            for _ in range(r04.LAST_STEP + 1)]


class PricePort(unittest.TestCase):
    def test_matches_router_curve_on_grid(self):
        for item in pf.PRODUCTS:
            for inv in (8000, 9500, 9999, 10000, 10001, 10500, 11000, 15000, 50000):
                self.assertEqual(pf.market_price(item, inv),
                                 r04._ro_price(item, inv),
                                 (item, inv))

    def test_floor_and_monotonicity(self):
        for item in pf.PRODUCTS:
            self.assertGreaterEqual(pf.market_price(item, 10 ** 9), 1)
            prices = [pf.market_price(item, inv) for inv in (9000, 10000, 11000)]
            self.assertGreaterEqual(prices[0], prices[1])
            self.assertGreaterEqual(prices[1], prices[2])

    def test_known_spot_values(self):
        # Base prices at I0; violent scarcity spike for CARROT near -1000.
        self.assertEqual(pf.market_price("WHEAT", 10000), 25)
        self.assertEqual(pf.market_price("MILK", 10000), 160)
        self.assertGreater(pf.market_price("CARROT", 9000), 400)


class TownConsumption(unittest.TestCase):
    def test_shop_interval_and_multiplier(self):
        # YARN_STORE is single-product: x2 every 4 steps.
        self.assertEqual(pf.town_consumption("WOOL", 300, 304, ["YARN_STORE"]), 2)
        self.assertEqual(pf.town_consumption("WOOL", 300, 308, ["YARN_STORE"]), 4)
        # BAKERY (EGG, WHEAT): x1 each.
        self.assertEqual(pf.town_consumption("EGG", 300, 304, ["BAKERY"]), 1)
        self.assertEqual(pf.town_consumption("WHEAT", 300, 304, ["BAKERY"]), 1)

    def test_center_interval_and_fertilizer_sink(self):
        self.assertEqual(pf.town_consumption("MILK", 300, 324, []), 1)
        self.assertEqual(pf.town_consumption("MILK", 300, 348, []), 2)
        # FERTILIZER has no town sink at all.
        self.assertEqual(pf.town_consumption("FERTILIZER", 0, 719,
                                             ["BAKERY", "YARN_STORE", "FARMERS_MARKET"]), 0)

    def test_duplicate_shops_consume_independently(self):
        one = pf.town_consumption("WOOL", 300, 304, ["YARN_STORE"])
        two = pf.town_consumption("WOOL", 300, 304, ["YARN_STORE", "YARN_STORE"])
        self.assertEqual(two, 2 * one)

    def test_unknown_shop_ignored(self):
        self.assertEqual(pf.town_consumption("MILK", 300, 304, ["NOPE"]), 0)


class ForecastPeak(unittest.TestCase):
    def test_flat_without_flows(self):
        t, inv = pf.forecast_peak("MILK", 10100, 300, 144, [], 0.0)
        self.assertEqual(t, 1)
        self.assertEqual(inv, 10100)

    def test_consumption_pulls_peak_late(self):
        # Glutted MILK with a consuming shop: inventory only falls, so the
        # best quoted price is at the end of the consumption run (t=142; the
        # last shop tick is step 440, then the price plateaus).
        t, inv = pf.forecast_peak("MILK", 10100, 300, 144, ["PIZZA_SHOP"], 0.0)
        self.assertEqual(t, 142)
        self.assertEqual(int(inv), 10058)
        self.assertEqual(pf.market_price("MILK", 10100), 1)
        self.assertGreater(pf.market_price("MILK", inv), 30)

    def test_rival_glut_pushes_peak_early(self):
        # Heavy rival selling overwhelms town consumption: sell now.
        t, _ = pf.forecast_peak("MILK", 10100, 300, 144, ["PIZZA_SHOP"], 50.0)
        self.assertEqual(t, 1)


class KeepQuantity(unittest.TestCase):
    def test_defers_glut_into_scarcity(self):
        keep = pf.keep_quantity("MILK", 50, 10100, 300, 144, ["PIZZA_SHOP"], 0.0)
        self.assertEqual(keep, 0)

    def test_keeps_scarcity_before_glut(self):
        keep = pf.keep_quantity("MILK", 50, 9900, 300, 144, ["PIZZA_SHOP"], 50.0)
        self.assertEqual(keep, 50)

    def test_fertilizer_never_defers(self):
        # No town sink: the future is never better.
        keep = pf.keep_quantity("FERTILIZER", 200, 10500, 300, 144,
                                ["BAKERY", "YARN_STORE"], 0.0)
        self.assertEqual(keep, 200)

    def test_partial_keep_prefix(self):
        # WOOL at 9900 is a mild scarcity ($240); YARN_STORE deepens it to
        # $244 at the peak. The first 2 units sit inside the 2% margin and
        # sell now; the tail defers.
        keep = pf.keep_quantity("WOOL", 60, 9900, 300, 144, ["YARN_STORE"], 0.0)
        self.assertEqual(keep, 2)

    def test_zero_qty(self):
        self.assertEqual(pf.keep_quantity("MILK", 0, 10100, 300, 144, [], 0.0), 0)

    def test_dollar_floor_sales_kept_when_future_also_floor(self):
        # Deep glut: both now and peak are $1 -> keep (indifferent, keep).
        keep = pf.keep_quantity("STRAWBERRY", 30, 100000, 300, 144, [], 0.0)
        self.assertEqual(pf.market_price("STRAWBERRY", 100000), 1)
        self.assertEqual(keep, 30)


class RivalFlow(unittest.TestCase):
    def setUp(self):
        pf.reset()

    def tearDown(self):
        pf.reset()

    def test_first_observation_yields_no_rates(self):
        rates = pf.update_rival_flow(300, {"MILK": 10000}, [])
        self.assertEqual(rates, {})

    def test_unexplained_jump_is_rival_flow(self):
        pf.update_rival_flow(300, {"MILK": 10000}, [])
        rates = pf.update_rival_flow(304, {"MILK": 10040}, [])
        self.assertGreater(rates["MILK"], 0)

    def test_own_sales_are_subtracted(self):
        pf.update_rival_flow(300, {"MILK": 10000}, [])
        pf.record_our_sales([["SELL", "MILK", 40]])
        rates = pf.update_rival_flow(304, {"MILK": 10040}, [])
        self.assertAlmostEqual(rates["MILK"], 0.0)

    def test_town_consumption_is_added_back(self):
        pf.update_rival_flow(300, {"MILK": 10000}, ["PIZZA_SHOP"])
        # Inventory fell by exactly the town consumption: no rival flow.
        rates = pf.update_rival_flow(304, {"MILK": 9999}, ["PIZZA_SHOP"])
        self.assertAlmostEqual(rates["MILK"], 0.0)

    def test_dollar_floor_sales_do_not_mask_rival_flow(self):
        # We sell 50 units at the $1 floor (no supply impact); rivals sell
        # 30. The estimator must still see the rival flow, not net it out.
        self.assertEqual(pf.market_price("MILK", 10500), 1)
        pf.update_rival_flow(300, {"MILK": 10000}, [])
        pf.record_our_sales([["SELL", "MILK", 50]], {"MILK": 10500})
        rates = pf.update_rival_flow(304, {"MILK": 10030}, [])
        self.assertAlmostEqual(rates["MILK"], 7.5)

    def test_new_episode_resets(self):
        pf.update_rival_flow(300, {"MILK": 10000}, [])
        rates = pf.update_rival_flow(304, {"MILK": 10040}, [])
        self.assertGreater(rates["MILK"], 0)
        pf.update_rival_flow(5, {"MILK": 10000}, [])  # step restarted: new episode
        self.assertEqual(pf._FLOW["rate"], {})
        rates = pf.update_rival_flow(6, {"MILK": 10000}, [])
        self.assertEqual(rates["MILK"], 0.0)


class ApplyRewrite(unittest.TestCase):
    def setUp(self):
        pf.reset()

    def tearDown(self):
        pf.reset()

    def test_inactive_outside_window(self):
        for step in (0, 100, 287, 718):
            obs = synthetic_observation(step, market_rows=[["SELL", "MILK", 50]],
                                        inventory={"MILK": 10100},
                                        shops=["PIZZA_SHOP"])
            action = action_with_market([["SELL", "MILK", 50]])
            self.assertIs(pf.apply_price_forecaster(obs, action), action)

    def test_defers_glutted_milk(self):
        obs = synthetic_observation(300, inventory={"MILK": 10100},
                                    shops=["PIZZA_SHOP"])
        action = action_with_market([["SELL", "MILK", 50]])
        out = pf.apply_price_forecaster(obs, action)
        self.assertEqual(out["market"], [])

    def test_keeps_scarce_milk(self):
        # Warm the flow estimator on steps 298->299 (rival dumping lifts
        # MILK 9850 -> 9900), then apply at step 300: the rival glut makes
        # the future worse, so the scarce sale is kept.
        pf.update_rival_flow(298, {"MILK": 9850}, ["PIZZA_SHOP"])
        pf.update_rival_flow(299, {"MILK": 9900}, ["PIZZA_SHOP"])
        obs = synthetic_observation(300, inventory={"MILK": 9900},
                                    shops=["PIZZA_SHOP"])
        action = action_with_market([["SELL", "MILK", 50]])
        out = pf.apply_price_forecaster(obs, action)
        self.assertEqual(out["market"], [["SELL", "MILK", 50]])

    def test_never_touches_non_sell_rows(self):
        obs = synthetic_observation(300, inventory={"MILK": 10100},
                                    shops=["PIZZA_SHOP"])
        action = action_with_market([["SELL", "MILK", 50],
                                     ["BUY_PRODUCT", "WHEAT", 10],
                                     ["HIRE"]])
        out = pf.apply_price_forecaster(obs, action)
        non_sell = [r for r in out["market"] if r[0] != "SELL"]
        self.assertEqual(non_sell, [["BUY_PRODUCT", "WHEAT", 10], ["HIRE"]])

    def test_never_adds_rows(self):
        obs = synthetic_observation(300, inventory={"MILK": 10100},
                                    shops=["PIZZA_SHOP"])
        action = action_with_market([["SELL", "MILK", 50]])
        out = pf.apply_price_forecaster(obs, action)
        self.assertLessEqual(len(out["market"]), 1)

    def test_malformed_input_returns_action(self):
        action = action_with_market([["SELL", "MILK", 50]])
        self.assertIs(pf.apply_price_forecaster({}, action), action)
        self.assertIs(pf.apply_price_forecaster({"step": 300}, None), None)
        self.assertIs(pf.apply_price_forecaster({"step": "x"},
                                                action), action)

    def test_telemetry(self):
        obs = synthetic_observation(300, inventory={"MILK": 10100},
                                    shops=["PIZZA_SHOP"])
        pf.apply_price_forecaster(obs, action_with_market([["SELL", "MILK", 50]]))
        report = pf.get_report()
        self.assertEqual(report["steps_active"], 1)
        self.assertEqual(report["rows_dropped"], 1)
        self.assertEqual(report["units_deferred"], 50)


class CashGuard(unittest.TestCase):
    def setUp(self):
        pf.reset()

    def tearDown(self):
        pf.reset()

    def test_upcoming_purchase_cost(self):
        tape = blank_tape()
        tape[320]["market"] = [["BUY_ANIMAL", "COW", 2], ["BUY_SEED", "MELON", 3]]
        cost = pf.upcoming_purchase_cost(tape, 300, {})
        self.assertEqual(cost, 2 * 400 + 3 * 80)

    def test_no_tape_no_cost(self):
        self.assertEqual(pf.upcoming_purchase_cost(None, 300, {}), 0.0)

    def test_guard_blocks_deferral_when_cash_tight(self):
        tape = blank_tape()
        tape[310]["market"] = [["BUY_ANIMAL", "COW", 10]]  # $4000 soon
        obs = synthetic_observation(300, inventory={"MILK": 10100},
                                    shops=["PIZZA_SHOP"], money=100)
        action = action_with_market([["SELL", "MILK", 50]])
        out = pf.apply_price_forecaster(obs, action, tape=tape)
        # Cash guard keeps the sale to fund the purchase.
        self.assertEqual(out["market"], [["SELL", "MILK", 50]])
        self.assertGreater(pf.get_report()["cash_guarded"], 0)

    def test_no_guard_when_cash_covers(self):
        tape = blank_tape()
        tape[310]["market"] = [["BUY_ANIMAL", "COW", 10]]
        obs = synthetic_observation(300, inventory={"MILK": 10100},
                                    shops=["PIZZA_SHOP"], money=100000)
        action = action_with_market([["SELL", "MILK", 50]])
        out = pf.apply_price_forecaster(obs, action, tape=tape)
        self.assertEqual(out["market"], [])


class Wiring(unittest.TestCase):
    def tearDown(self):
        r04.PRICE_FORECASTER = False
        pf.reset()

    def test_install_wires_flag(self):
        r04.install(price_forecaster=True)
        self.assertIs(r04.PRICE_FORECASTER, True)
        r04.install(price_forecaster=False)
        self.assertIs(r04.PRICE_FORECASTER, False)

    def test_flag_defaults_off(self):
        r04.install()
        self.assertIs(r04.PRICE_FORECASTER, False)

    def test_features_key_and_diagnostics(self):
        agent = TitanAgent(Features(r04_sale_window=True, r04_price_forecaster=True))
        agent.act(synthetic_observation(0), dict(CONFIG))
        self.assertIs(r04.PRICE_FORECASTER, True)
        self.assertIs(agent.diagnostics["price_forecaster"], True)
        self.assertTrue(agent._v3_active())
        agent2 = TitanAgent(Features(r04_sale_window=True))
        agent2.act(synthetic_observation(0), dict(CONFIG))
        self.assertIs(r04.PRICE_FORECASTER, False)
        self.assertIs(agent2.diagnostics["price_forecaster"], False)

    def test_keys_ship_off(self):
        import json
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_price_forecaster"], False)
        features = Features(**data)
        self.assertIs(features.r04_price_forecaster, False)

    def test_v3_agent_end_to_end_with_flag_on(self):
        # Full installed agent on a synthetic mid-game observation: the lane
        # runs without error and only ever drops/shrinks SELL rows.
        pf.reset()
        agent_fn = r04.install(None, 8, 0, True, True, True, True, True)
        obs = synthetic_observation(400, inventory={"MILK": 10100},
                                    shops=["PIZZA_SHOP"], money=50000)
        out = agent_fn(obs, dict(CONFIG))
        # The lane ran inside the installed agent without error.
        self.assertGreater(pf.get_report()["steps_active"], 0)
        self.assertEqual(set(out), {"farmer", "hands", "market"})


if __name__ == "__main__":
    unittest.main()
