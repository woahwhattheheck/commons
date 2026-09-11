# SPDX-License-Identifier: Apache-2.0
"""Source-grounded predecessor tests for IDEA-HUNT-B B1 alternate-day feeding.

This is a negative/scope audit only.  It imports the preserved official engine and
proves that alternate-day feeding is not globally semantics-preserving once CARE
bonuses are active, while also pinning the narrower no-CARE property that motivated
B1: an animal only escapes after two consecutive unfed days.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest


HERE = Path(__file__).resolve()
LAB = HERE.parents[4]
ENGINE_PATH = LAB / "reference" / "engine" / "kaggriculture.py"
R04_PATH = LAB / "candidates" / "v3" / "overlay" / "r04_full_router.py"


def _load_engine():
    # kaggriculture.py only needs resolve_episode_seed at import time.  Keep this
    # focused regression runnable in source-only CI without a Kaggle installation.
    package = types.ModuleType("kaggle_environments")
    utils = types.ModuleType("kaggle_environments.utils")
    utils.resolve_episode_seed = lambda env: 0
    package.utils = utils
    sys.modules["kaggle_environments"] = package
    sys.modules["kaggle_environments.utils"] = utils

    spec = importlib.util.spec_from_file_location("b1_preserved_engine", ENGINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load preserved engine: {ENGINE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ENGINE = _load_engine()


def _simulate(kind: str, feed_on, *, care: bool, days: int = 15):
    """Run exact official EOD animal refreshes and harvest every produced batch."""
    farm = {"tiles": [[ENGINE._new_animal(kind, 0)]]}
    production = []
    for day in range(days):
        tile = farm["tiles"][0][0]
        if not (isinstance(tile, dict) and tile.get("animal") == kind):
            return {"escaped_on_eod": day, "production": production}
        tile["fed_today"] = bool(feed_on(day))
        tile["cared_today"] = bool(care)
        before = int(tile.get("yield_units", 0))
        ENGINE._daily_refresh_animals(farm, day)
        tile = farm["tiles"][0][0]
        if not (isinstance(tile, dict) and tile.get("animal") == kind):
            return {"escaped_on_eod": day, "production": production}
        gained = int(tile.get("yield_units", 0)) - before
        if gained > 0:
            production.append((day + 1, gained))
            # Isolate production cadence from the max-held cap, like an ideal
            # immediate harvest after every produced batch.
            tile["yield_units"] = 0
    return {"escaped_on_eod": None, "production": production}


class B1FeedSemanticsTest(unittest.TestCase):
    def test_alternate_feed_without_care_preserves_base_batches_and_survival(self):
        for kind in ("GOOSE", "COW", "SHEEP"):
            with self.subTest(kind=kind):
                daily = _simulate(kind, lambda day: True, care=False)
                alternate = _simulate(kind, lambda day: day % 2 == 0, care=False)
                self.assertIsNone(alternate["escaped_on_eod"])
                self.assertEqual(alternate["production"], daily["production"])
                self.assertTrue(all(units == 1 for _, units in alternate["production"]))

    def test_alternate_feed_with_care_loses_product_bonus(self):
        expected_first = {"GOOSE": 4, "COW": 6, "SHEEP": 6}
        for kind in ("GOOSE", "COW", "SHEEP"):
            with self.subTest(kind=kind):
                daily = _simulate(kind, lambda day: True, care=True)
                alternate = _simulate(kind, lambda day: day % 2 == 0, care=True)
                self.assertIsNone(alternate["escaped_on_eod"])
                self.assertEqual(daily["production"][0][1], expected_first[kind])
                # The first official production boundary lands on an unfed day
                # for this parity, so pending CARE bonus is not consumed.
                self.assertEqual(alternate["production"][0][1], 1)
                self.assertLess(
                    sum(units for _, units in alternate["production"]),
                    sum(units for _, units in daily["production"]),
                )

    def test_two_consecutive_unfed_days_escape(self):
        result = _simulate("SHEEP", lambda day: False, care=False, days=2)
        self.assertEqual(result["escaped_on_eod"], 1)

    def test_live_r04_v233_couples_feed_then_care(self):
        source = R04_PATH.read_text(encoding="utf-8")
        feed = "if not tile['fed_today'] and inv.get('WHEAT',0):command=['FEED']"
        care = "elif not tile['cared_today']:command=['CARE']"
        self.assertIn(feed, source)
        self.assertIn(care, source)
        self.assertLess(source.index(feed), source.index(care))


if __name__ == "__main__":
    unittest.main()
