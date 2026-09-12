import unittest

import gemini_public_pressure as G
import rival_route_pressure as R


class GeminiPublicPressureQuadrantCustodyTests(unittest.TestCase):
    def test_all_reachable_engine_prefixes_are_accepted(self):
        for quadrants in G.REACHABLE_QUADRANT_PREFIXES:
            with self.subTest(quadrants=quadrants):
                self.assertEqual(
                    G._quadrants({"unlocked_quadrants": list(quadrants)}, "farm"),
                    quadrants,
                )

    def test_unknown_quadrant_name_cannot_mint_expansion_witness(self):
        with self.assertRaises(R.UnsupportedEvidence):
            G._quadrants({"unlocked_quadrants": ["NW", "BOGUS"]}, "rival")

    def test_unreachable_subset_cannot_mint_expansion_witness(self):
        with self.assertRaises(R.UnsupportedEvidence):
            G._quadrants({"unlocked_quadrants": ["NW", "SW"]}, "rival")

    def test_reordered_unlock_prefix_cannot_mint_expansion_witness(self):
        with self.assertRaises(R.UnsupportedEvidence):
            G._quadrants({"unlocked_quadrants": ["NW", "SW", "NE"]}, "rival")

    def test_missing_quadrant_field_remains_gracefully_unavailable(self):
        self.assertIsNone(G._quadrants({}, "rival"))


if __name__ == "__main__":
    unittest.main()
