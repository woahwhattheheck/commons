#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace

import cobuy_719_collision_atlas as atlas


def _route(actions, length=3):
    return list(actions) + [
        {"farmer": ["PASS"], "hands": [], "market": []}
    ] * (length - len(actions))


def _fake_apex_tape(buy_steps: dict[int, tuple[int, int, int]] | None = None) -> str:
    """Build the exact 2x719 tape shape expected by the production parser."""
    buy_steps = buy_steps or {}
    routes = []
    for _ in range(2):
        encoded = []
        for step in range(atlas.TURNS):
            if step in buy_steps:
                op, item, qty = buy_steps[step]
                encoded.append(f'"0 1 {op} {item} {qty}"')
            else:
                encoded.append('"0 0"')
        routes.append("{" + ",".join(encoded) + "}")
    return (
        f"constexpr int kTurns = {atlas.TURNS};\n"
        "constexpr int kRoutes = 2;\n"
        "const char* const kEncodedTapes[kRoutes][kTurns] = {\n"
        + ",\n".join(routes)
        + "\n};\n"
    )


class AtlasUnitTests(unittest.TestCase):
    def test_arlene_intersection_fails_closed_after_sell_prefix(self):
        routes = {
            "a": _route(
                [
                    {"market": [["BUY_PRODUCT", "WHEAT", 13]]},
                    {
                        "market": [
                            ["SELL", "MILK", 1],
                            ["BUY_PRODUCT", "WHEAT", 3],
                        ]
                    },
                    {"market": [["BUY_PRODUCT", "FERTILIZER", 2]]},
                ]
            ),
            "b": _route(
                [
                    {"market": [["BUY_PRODUCT", "WHEAT", 13]]},
                    {"market": [["BUY_PRODUCT", "WHEAT", 3]]},
                    {"market": [["BUY_PRODUCT", "FERTILIZER", 2]]},
                ]
            ),
        }
        module = SimpleNamespace(
            routes=lambda: routes,
            MAX_ORDERS=atlas.MAX_ORDERS,
            FINAL_EXECUTABLE_STEP=2,
        )
        per = atlas.arlene_route_pulses(module)
        invariant = atlas._invariant_pulses(per)
        self.assertEqual(
            invariant,
            [
                {"step": 0, "row": 0, "item": "WHEAT", "qty": 13},
                {"step": 2, "row": 0, "item": "FERTILIZER", "qty": 2},
            ],
        )

    def test_apex_guard_boundaries_fail_closed_except_verified_opening(self):
        buys = {
            0: (4, 0, 13),
            1: (4, 0, 1),
            144: (4, 0, 2),
            288: (4, 8, 3),
            432: (4, 0, 4),
            576: (4, 8, 5),
            718: (4, 0, 6),
        }
        text = _fake_apex_tape(buys)
        per = atlas.apex_route_pulses(text, native_verified_opening=True)
        route0 = {(p["step"], p["item"]): p for p in per["0"]}
        self.assertTrue(route0[(0, "WHEAT")]["raw_index_stable"])
        self.assertTrue(route0[(1, "WHEAT")]["raw_index_stable"])
        for step, item in (
            (144, "WHEAT"),
            (288, "FERTILIZER"),
            (432, "WHEAT"),
            (576, "FERTILIZER"),
            (718, "WHEAT"),
        ):
            self.assertFalse(route0[(step, item)]["raw_index_stable"])

        unverified = atlas.apex_route_pulses(text, native_verified_opening=False)
        opening = next(p for p in unverified["0"] if p["step"] == 0)
        self.assertFalse(opening["raw_index_stable"])

    def test_apex_pass_rows_compress_like_python_entrypoint(self):
        # PASS is omitted by Apex _unpack_action, so following BUY becomes row0.
        text = _fake_apex_tape()
        text = text.replace('"0 0"', '"0 2 0 0 1 4 0 2"', 1)
        per = atlas.apex_route_pulses(text, native_verified_opening=True)
        pulse = next(p for p in per["0"] if p["step"] == 0)
        self.assertEqual(
            (pulse["row"], pulse["item"], pulse["qty"]),
            (0, "WHEAT", 2),
        )

    def test_source_contracts_fail_closed(self):
        with self.assertRaises(ValueError):
            atlas._assert_apex_source_contracts("", "", "")
        main = (
            "action['market'] = market[:10]\n"
            "market = [o for o in market if o[0] == 'SELL']"
        )
        guard = (
            "inline void budget_sales_first(Action& action)\n"
            "if (added > 0 && settings.sales_first) budget_sales_first(result);\n"
            "action.orders[action.n_orders++]"
        )
        policy = "if (state.step == 0) selected_route = 0;"
        atlas._assert_apex_source_contracts(main, guard, policy)


class ExactCheckoutTests(unittest.TestCase):
    def test_exact_checkout_atlas_is_deterministic_and_preserves_opening(self):
        root = Path(__file__).resolve().parents[7]
        paths = atlas.default_paths(root)
        if not all(path.exists() for path in paths.values()):
            self.skipTest("full source checkout not present")
        first = atlas.build_atlas(**paths)
        second = atlas.build_atlas(**paths)
        self.assertEqual(first, second)
        self.assertTrue(first["opening_native_receipt_verified"])
        self.assertTrue(first["controls"]["step0_wheat_collision_present"])
        self.assertTrue(first["controls"]["step0_wheat_same_row"])
        opening = [
            c
            for c in first["authoritative_collisions"]
            if c["step"] == 0 and c["item"] == "WHEAT"
        ]
        self.assertEqual(len(opening), 1)
        self.assertEqual(
            (
                opening[0]["own_row"],
                opening[0]["own_qty"],
                opening[0]["rival_row"],
                opening[0]["rival_qty"],
            ),
            (0, 13, 0, 13),
        )
        excluded = set(
            first["scope"]["guard_boundaries_excluded_without_native_receipt"]
        )
        for collision in first["authoritative_collisions"]:
            self.assertNotIn(collision["step"], excluded)
            self.assertLessEqual(collision["own_row"], atlas.MAX_ORDERS - 1)
            self.assertLessEqual(collision["rival_row"], atlas.MAX_ORDERS - 1)
            self.assertIn(collision["item"], atlas.BUYABLE)
        json.dumps(first, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
