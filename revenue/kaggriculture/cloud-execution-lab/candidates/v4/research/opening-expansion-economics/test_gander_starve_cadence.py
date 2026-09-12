import unittest

import gander_starve_cadence as G


class GanderStarveCompositeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = G.build_report()
        cls.safe = cls.report["safe_composite"]

    def test_safe_composite_survives_all_nine_geese(self):
        self.assertTrue(self.safe["survived"])
        self.assertIsNone(self.safe["escaped_day"])
        self.assertEqual(self.safe["living_geese"], 9)
        self.assertEqual(self.safe["max_consecutive_unfed_seen"], 1)

    def test_day1_is_mandatory_after_unfed_eod0(self):
        predecessor = self.report["mandatory_day1_feed_predecessor"]
        self.assertFalse(predecessor["survived"])
        self.assertEqual(predecessor["escaped_day"], 1)
        self.assertEqual(self.safe["feed_days"][0], 1)
        self.assertEqual(self.safe["skip_days"][0], 2)

    def test_alternation_halves_remaining_feed_load_without_output_loss(self):
        self.assertEqual(len(self.safe["feed_days"]), 15)
        self.assertEqual(len(self.safe["skip_days"]), 14)
        self.assertEqual(self.safe["wheat_consumed"], 135)
        self.assertEqual(self.safe["wheat_saved_vs_feed_daily_days_1_29"], 126)
        self.assertEqual(self.safe["action_attempts"]["feed_attempts"], 135)
        self.assertEqual(
            self.safe["feed_actions_saved_vs_feed_daily_days_1_29"], 126
        )
        self.assertEqual(self.safe["egg_total"], 9 * 27)
        self.assertEqual(self.safe["fertilizer_total"], 9 * 30)

    def test_skip_feed_slots_realize_egg_without_held_cap_clipping(self):
        # Mature EGG is harvested only on even skip-feed days.  Two production
        # refreshes can accumulate between those visits, still below max_held=4.
        self.assertEqual(self.safe["action_attempts"]["harvest_attempts"], 13 * 9)
        self.assertLessEqual(self.safe["max_goose_yield_units_seen"], 2)
        self.assertEqual(self.safe["final_held_egg"], 2 * 9)

    def test_same_two_worker_geometry_fits_after_daily_hire(self):
        self.assertEqual(self.safe["action_attempts"]["hire_orders"], 29)
        self.assertLessEqual(self.safe["max_route_actions_after_hire"], 23)
        self.assertEqual(
            self.safe["source_contract"]["gander_day1_service_counts"],
            {
                "PICKUP": 2,
                "FEED": 9,
                "COLLECT_FERTILIZER": 9,
                "DROP": 2,
            },
        )

    def test_care_is_explicitly_out_of_scope(self):
        self.assertEqual(self.safe["action_attempts"]["care_attempts"], 0)
        self.assertFalse(self.safe["source_contract"]["care_used"])
        self.assertFalse(self.safe["source_contract"]["economics_claim"])
        self.assertTrue(
            self.report["interpretation"]["wheat_savings_are_units_not_cash"]
        )
        self.assertFalse(self.report["interpretation"]["market_prices_modeled"])

    def test_current_engine_identity_is_exact(self):
        self.assertEqual(self.safe["engine_git_blob"], G.PINNED_ENGINE_GIT_BLOB)
        self.assertEqual(self.safe["engine_sha256"], G.PINNED_ENGINE_SHA256)
        self.assertEqual(
            self.safe["source_contract"]["starve_engine_git_blob"],
            G.PINNED_ENGINE_GIT_BLOB,
        )


if __name__ == "__main__":
    unittest.main()
