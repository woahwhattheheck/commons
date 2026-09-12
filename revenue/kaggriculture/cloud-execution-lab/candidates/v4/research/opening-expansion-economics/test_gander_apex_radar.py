import unittest

import gander_apex_radar as R


class GanderApexRadarTests(unittest.TestCase):
    def test_certified_frontier_stays_below_clone_hand_threshold(self):
        report = R.build_report(verify_sources=False)
        frontier = report["gander_frontier"]
        apex = report["apex_clone_contract"]
        proof = report["proof"]

        self.assertEqual(frontier["geese"], 9)
        self.assertEqual(frontier["hires"], 1)
        self.assertEqual(apex["window"], [2, 10])
        self.assertEqual(apex["min_opponent_hands"], 3)
        self.assertEqual(apex["min_opponent_structures"], 1)
        self.assertEqual(proof["hired_hand_margin_below_latch"], 2)
        self.assertFalse(proof["clone_latch_possible"])
        self.assertTrue(proof["window_rows"])
        self.assertTrue(all(not row["clone_latch"] for row in proof["window_rows"]))

    def test_clone_latch_boundary_is_not_weakened(self):
        contract = (2, 10, 3, 1)
        self.assertTrue(R.clone_latch_possible(2, 3, 1, contract))
        self.assertTrue(R.clone_latch_possible(10, 3, 9, contract))
        self.assertFalse(R.clone_latch_possible(2, 2, 9, contract))
        self.assertFalse(R.clone_latch_possible(2, 3, 0, contract))
        self.assertFalse(R.clone_latch_possible(11, 3, 1, contract))

    def test_one_hire_is_invisible_even_with_all_nine_structures_visible(self):
        contract = (2, 10, 3, 1)
        for step in range(2, 11):
            self.assertFalse(R.clone_latch_possible(step, 1, 9, contract))

    def test_bool_numeric_aliases_fail_closed(self):
        contract = (2, 10, 3, 1)
        for state in ((True, 1, 1), (2, True, 1), (2, 1, True)):
            with self.assertRaises(R.RadarCompositionError):
                R.clone_latch_possible(*state, contract)

    def test_scope_does_not_erase_independent_apex_actions(self):
        scope = R.build_report(verify_sources=False)["scope"]
        self.assertEqual(
            scope["claim"],
            "certified GANDER frontier is invisible to Apex clone latch",
        )
        self.assertTrue(
            scope["does_not_claim_apex_has_no_independent_timed_or_predator_actions"]
        )
        self.assertFalse(scope["runtime_change"])
        self.assertFalse(scope["default_change"])

    def test_current_checkout_source_identities_authenticate(self):
        report = R.build_report(verify_sources=True)
        sources = report["sources"]
        self.assertEqual(sources["engine_git_blob"], R.PINNED_ENGINE_GIT_BLOB)
        self.assertEqual(sources["apex_main_sha256"], R.PINNED_APEX_SHA256)
        self.assertEqual(
            sources["gander_engine"]["engine_blob"],
            R.PINNED_ENGINE_GIT_BLOB,
        )
        self.assertEqual(
            sources["apex_sources"]["apex_main_sha256"],
            R.PINNED_APEX_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
