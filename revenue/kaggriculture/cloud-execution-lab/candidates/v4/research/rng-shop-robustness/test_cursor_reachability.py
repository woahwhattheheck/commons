# SPDX-License-Identifier: Apache-2.0
from hashlib import sha1
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cursor_reachability import (
    LAND_PRICES,
    certified_pre_eod_empty_counts,
    robust_shop_options_from_state,
)
from rng_shop_robustness import ENGINE_SOURCE_BLOB


def git_blob_sha(data: bytes) -> str:
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def farm4(*, money=0, farmer=(0, 0), hands=(), unlocked=None):
    tiles = [
        [None, None, "LOCKED", "LOCKED"],
        [None, None, "LOCKED", "LOCKED"],
        ["LOCKED", "LOCKED", "LOCKED", "LOCKED"],
        ["LOCKED", "LOCKED", "LOCKED", "LOCKED"],
    ]
    return {
        "money": money,
        "tiles": tiles,
        "farmer": list(farmer),
        "hands": [list(p) for p in hands],
        "unlocked_quadrants": list(unlocked or ["NW"]),
    }


def private(*, shed=None, inventories=None):
    base = {
        "WHEAT": 0,
        "CARROT": 0,
        "TOMATO": 0,
        "STRAWBERRY": 0,
        "MELON": 0,
        "EGG": 0,
        "MILK": 0,
        "WOOL": 0,
        "FERTILIZER": 0,
        "GOOSE": 0,
        "COW": 0,
        "SHEEP": 0,
    }
    base.update(shed or {})
    return {"shed": base, "inventories": inventories or [{}], "seeds": {}}


CFG = {
    "boardSize": 4,
    "turnsPerDay": 4,
    "maxMarketOrdersPerTurn": 10,
    "shedCapacity": 100,
}


class CursorReachabilityTests(unittest.TestCase):
    def test_reference_engine_source_and_ordering_are_exactly_pinned(self):
        engine = HERE.parents[3] / "reference" / "engine" / "kaggriculture.py"
        data = engine.read_bytes()
        self.assertEqual(git_blob_sha(data), ENGINE_SOURCE_BLOB)
        text = data.decode("utf-8")
        unit = text.index("_apply_unit_action(obs0.farms[i]")
        market = text.index("    _process_market(state, env)", unit)
        eod = text.index("        _end_of_day(state, env, day)", market)
        self.assertLess(unit, market)
        self.assertLess(market, eod)
        self.assertIn('elif op == "BUY_LAND":\n                _do_buy_land', text)
        self.assertIn('farm["tiles"][y][x] = None', text)
        self.assertIn('if op == "BUILD_COOP":', text)
        self.assertIn('if op == "DIG":', text)

    def test_distinct_unit_tiles_give_complete_integer_interval(self):
        farm = farm4(farmer=(0, 0), hands=((1, 0), (0, 1), (0, 0)))
        farm["tiles"][0][1] = {"kind": "WEED"}
        farm["tiles"][1][0] = {"kind": "PASTURE", "animal": "COW"}
        cert = certified_pre_eod_empty_counts(
            farm, private(inventories=[{}, {}, {}, {}]), step=3, configuration=CFG
        )
        self.assertEqual(cert.base_empty_count, 2)
        self.assertEqual(cert.fill_positions, ((0, 0),))
        self.assertEqual(cert.clear_positions, ((1, 0),))
        self.assertEqual(cert.unit_only_counts, (1, 2, 3))

    def test_build_reachability_does_not_require_seed_inventory(self):
        farm = farm4(farmer=(0, 0))
        cert = certified_pre_eod_empty_counts(
            farm, private(inventories=[{}]), step=3, configuration=CFG
        )
        self.assertIn(cert.base_empty_count - 1, cert.unit_only_counts)

    def test_immediate_buy_land_adds_exact_next_quadrant_locked_count(self):
        farm = farm4(money=LAND_PRICES[0], farmer=(0, 0))
        cert = certified_pre_eod_empty_counts(
            farm, private(), step=3, configuration=CFG
        )
        self.assertTrue(cert.land.guaranteed)
        self.assertEqual(cert.land.quadrant, "NE")
        self.assertEqual(cert.land.locked_tiles_added, 4)
        self.assertEqual(
            set(cert.reachable_counts),
            set(cert.unit_only_counts)
            | {count + 4 for count in cert.unit_only_counts},
        )

    def test_current_shed_sell_floor_can_guarantee_land_before_eod(self):
        farm = farm4(money=995, farmer=(0, 0))
        cert = certified_pre_eod_empty_counts(
            farm,
            private(shed={"WHEAT": 5}),
            step=3,
            configuration={**CFG, "maxMarketOrdersPerTurn": 2},
        )
        self.assertTrue(cert.land.guaranteed)
        self.assertEqual(cert.land.sell_slots_used, 1)
        self.assertEqual(cert.land.guaranteed_cash_floor, 1000)

    def test_order_cap_limits_pre_land_financing_products(self):
        farm = farm4(money=990, farmer=(0, 0))
        stock = private(shed={"WHEAT": 6, "CARROT": 4})
        blocked = certified_pre_eod_empty_counts(
            farm,
            stock,
            step=3,
            configuration={**CFG, "maxMarketOrdersPerTurn": 2},
        )
        self.assertFalse(blocked.land.guaranteed)
        self.assertEqual(blocked.land.guaranteed_cash_floor, 996)
        allowed = certified_pre_eod_empty_counts(
            farm,
            stock,
            step=3,
            configuration={**CFG, "maxMarketOrdersPerTurn": 3},
        )
        self.assertTrue(allowed.land.guaranteed)
        self.assertEqual(allowed.land.sell_slots_used, 2)
        self.assertEqual(allowed.land.guaranteed_cash_floor, 1000)

    def test_market_cap_uses_pinned_engine_int_coercion(self):
        farm = farm4(money=995, farmer=(0, 0))
        stock = private(shed={"WHEAT": 5})
        for raw_cap in ("2", 2.9, True):
            with self.subTest(raw_cap=raw_cap):
                cert = certified_pre_eod_empty_counts(
                    farm,
                    stock,
                    step=3,
                    configuration={**CFG, "maxMarketOrdersPerTurn": raw_cap},
                )
                expected = raw_cap is not True
                self.assertEqual(cert.land.guaranteed, expected)

    def test_nonpositive_market_cap_matches_engine_effective_one_slot(self):
        farm = farm4(money=995, farmer=(0, 0))
        stock = private(shed={"WHEAT": 5})
        for raw_cap in (0, -3):
            with self.subTest(raw_cap=raw_cap):
                cert = certified_pre_eod_empty_counts(
                    farm,
                    stock,
                    step=3,
                    configuration={**CFG, "maxMarketOrdersPerTurn": raw_cap},
                )
                self.assertFalse(cert.land.guaranteed)
                self.assertEqual(cert.land.guaranteed_cash_floor, 995)

    def test_carried_drop_financing_fails_closed_instead_of_underclaiming(self):
        farm = farm4(money=995, farmer=(1, 1))
        with self.assertRaisesRegex(ValueError, "DROP could change BUY_LAND financing"):
            certified_pre_eod_empty_counts(
                farm,
                private(inventories=[{"WHEAT": 5}]),
                step=3,
                configuration={**CFG, "maxMarketOrdersPerTurn": 2},
            )

    def test_non_eod_step_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "final tick"):
            certified_pre_eod_empty_counts(
                farm4(), private(), step=2, configuration=CFG
            )

    def test_state_composition_only_offers_mechanically_reachable_own_counts(self):
        farm = farm4(money=0, farmer=(0, 0), unlocked=["NW", "NE", "SW", "SE"])
        farm["tiles"] = [
            [None, {"kind": "COOP"}, {"kind": "COOP"}, {"kind": "COOP"}],
            [None, None, {"kind": "COOP"}, {"kind": "COOP"}],
            [{"kind": "COOP"} for _ in range(4)],
            [{"kind": "COOP"} for _ in range(4)],
        ]
        cert, rows = robust_shop_options_from_state(
            2051966578,
            farm,
            private(),
            [40, 41, 42],
            step=23,
            configuration=CFG,
            target_shops={"BRUNCH_SPOT"},
        )
        self.assertEqual(cert.reachable_counts, (2, 3))
        self.assertEqual({row.own_empty_count for row in rows}, {2, 3})

    def test_invalid_bool_config_and_bad_shape_fail_closed(self):
        bad = dict(CFG)
        bad["boardSize"] = True
        with self.assertRaises(ValueError):
            certified_pre_eod_empty_counts(farm4(), private(), step=3, configuration=bad)
        malformed = farm4()
        malformed["tiles"].pop()
        with self.assertRaises(ValueError):
            certified_pre_eod_empty_counts(malformed, private(), step=3, configuration=CFG)


if __name__ == "__main__":
    unittest.main()
