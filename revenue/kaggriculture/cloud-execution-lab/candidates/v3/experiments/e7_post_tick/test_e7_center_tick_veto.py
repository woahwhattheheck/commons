#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
for path in (HERE.parent, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import e7_center_tick_veto as e7  # noqa: E402


class E7CenterTickTests(unittest.TestCase):
    def setUp(self):
        e7.reset_report()
        self.old_excluded = e7.r04.SALE_EXCLUDED
        self.old_reserve = e7.r04.reserve_sales
        # Direct reserve-unit tests exercise the factor after a validated
        # standard-config callback. Config validation itself is tested below.
        e7._CENTER_TICK_ENABLED = True

    def tearDown(self):
        e7.r04.SALE_EXCLUDED = self.old_excluded
        e7.r04.reserve_sales = self.old_reserve
        e7.reset_report()

    @staticmethod
    def action():
        return {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "WHEAT", 1]]}

    @staticmethod
    def fake_reserve(action, view, state, tape, step):
        for item, qty in (("MILK", 3), ("FERTILIZER", 2)):
            if item not in e7.r04.SALE_EXCLUDED:
                action["market"].append(["SELL", item, qty])

    def test_non_center_tick_is_exact_parent_delegation(self):
        action = self.action()
        with mock.patch.object(e7, "_ORIGINAL_RESERVE", self.fake_reserve):
            result = e7.guarded_reserve_sales(action, None, object(), [], 289)
        self.assertIsNone(result)
        self.assertEqual(action["market"][-2:], [["SELL", "MILK", 3], ["SELL", "FERTILIZER", 2]])
        self.assertEqual(e7.REPORT["center_tick_calls"], 0)

    def test_center_tick_vetoes_nonfert_but_preserves_parent_fertilizer(self):
        action = self.action()
        e7.r04.SALE_EXCLUDED = ("WHEAT",)
        with mock.patch.object(e7, "_ORIGINAL_RESERVE", self.fake_reserve):
            e7.guarded_reserve_sales(action, None, object(), [], 288)
        self.assertEqual(action["market"][-1], ["SELL", "FERTILIZER", 2])
        self.assertNotIn(["SELL", "MILK", 3], action["market"])
        self.assertEqual(e7.REPORT["counterfactual_activations"], 1)
        self.assertEqual(e7.REPORT["skipped_rows"], 1)
        self.assertEqual(e7.REPORT["skipped_units"], 3)
        self.assertEqual(e7.REPORT["trace"], [{"step": 288, "rows": [{"item": "MILK", "qty": 3}]}])
        self.assertEqual(e7.r04.SALE_EXCLUDED, ("WHEAT",))

    def test_unvalidated_runtime_config_fails_open_even_on_step288(self):
        action = self.action()
        e7._CENTER_TICK_ENABLED = False
        with mock.patch.object(e7, "_ORIGINAL_RESERVE", self.fake_reserve):
            e7.guarded_reserve_sales(action, None, object(), [], 288)
        self.assertIn(["SELL", "MILK", 3], action["market"])
        self.assertEqual(e7.REPORT["center_tick_calls"], 0)

    def test_center_tick_never_enables_parent_excluded_fertilizer(self):
        action = self.action()
        e7.r04.SALE_EXCLUDED = ("WHEAT", "FERTILIZER")
        with mock.patch.object(e7, "_ORIGINAL_RESERVE", self.fake_reserve):
            e7.guarded_reserve_sales(action, None, object(), [], 312)
        self.assertNotIn(["SELL", "MILK", 3], action["market"])
        self.assertNotIn(["SELL", "FERTILIZER", 2], action["market"])
        self.assertEqual(e7.REPORT["skipped_units"], 3)
        self.assertEqual(e7.r04.SALE_EXCLUDED, ("WHEAT", "FERTILIZER"))

    def test_parent_exclusions_restore_when_real_reserve_raises(self):
        calls = {"n": 0}

        def reserve(action, view, state, tape, step):
            calls["n"] += 1
            if calls["n"] == 1:
                return self.fake_reserve(action, view, state, tape, step)
            raise RuntimeError("boom")

        e7.r04.SALE_EXCLUDED = ("WHEAT",)
        with mock.patch.object(e7, "_ORIGINAL_RESERVE", reserve):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                e7.guarded_reserve_sales(self.action(), None, object(), [], 336)
        self.assertEqual(e7.r04.SALE_EXCLUDED, ("WHEAT",))

    def test_before_advance_start_does_not_veto(self):
        action = self.action()
        with mock.patch.object(e7, "_ORIGINAL_RESERVE", self.fake_reserve):
            e7.guarded_reserve_sales(action, None, object(), [], 264)
        self.assertIn(["SELL", "MILK", 3], action["market"])
        self.assertEqual(e7.REPORT["center_tick_calls"], 0)

    def test_last_step_does_not_veto(self):
        action = self.action()
        with mock.patch.object(e7, "_ORIGINAL_RESERVE", self.fake_reserve):
            e7.guarded_reserve_sales(action, None, object(), [], e7.r04.LAST_STEP)
        self.assertIn(["SELL", "MILK", 3], action["market"])
        self.assertEqual(e7.REPORT["center_tick_calls"], 0)

    def test_row_detector_ignores_preexisting_fertilizer_and_malformed(self):
        before = [["SELL", "MILK", 9]]
        after = before + [["SELL", "FERTILIZER", 4], [], ["SELL", "MILK", "2"], ["BUY_PRODUCT", "WHEAT", 1]]
        self.assertEqual(e7._new_nonfert_sell_rows(before, after), [("MILK", 2)])

    def test_runtime_center_interval_requires_literal_int24(self):
        self.assertTrue(e7._standard_center_configuration({"townCenterSellInterval": 24}))
        self.assertTrue(e7._standard_center_configuration(SimpleNamespace(townCenterSellInterval=24)))
        for value in (12, 48, 24.0, "24", True, False, None):
            self.assertFalse(e7._standard_center_configuration({"townCenterSellInterval": value}))
        self.assertFalse(e7._standard_center_configuration({}))
        self.assertFalse(e7._standard_center_configuration(None))

    def test_install_enabled_validates_each_runtime_callback(self):
        sentinel = object()

        def parent(observation, configuration=None):
            return sentinel

        with mock.patch.object(e7.r04, "install", return_value=parent) as installed:
            agent = e7.install(enabled=True)
        self.assertIs(e7.r04.reserve_sales, e7.guarded_reserve_sales)
        self.assertIs(agent({}, {"townCenterSellInterval": 24}), sentinel)
        self.assertTrue(e7._CENTER_TICK_ENABLED)
        self.assertIs(agent({}, {"townCenterSellInterval": 12}), sentinel)
        self.assertFalse(e7._CENTER_TICK_ENABLED)
        self.assertEqual(e7.REPORT["config_accepts"], 1)
        self.assertEqual(e7.REPORT["config_rejections"], 1)
        installed.assert_called_once()

    def test_install_disabled_is_exact_parent_and_restores_original_hook(self):
        sentinel = object()

        def parent(observation, configuration=None):
            return sentinel

        with mock.patch.object(e7.r04, "install", return_value=parent):
            agent = e7.install(enabled=False)
        self.assertIs(agent, parent)
        self.assertIs(agent({}, {"townCenterSellInterval": 12}), sentinel)
        self.assertIs(e7.r04.reserve_sales, e7._ORIGINAL_RESERVE)
        self.assertEqual(e7.REPORT["config_accepts"], 0)
        self.assertEqual(e7.REPORT["config_rejections"], 0)


if __name__ == "__main__":
    unittest.main()
