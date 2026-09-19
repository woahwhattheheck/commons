from fractions import Fraction
import json
import pathlib
import unittest

import separation_api as s


class SeparationApiTests(unittest.TestCase):
    def test_integer_primitive_equivalence_examples(self):
        self.assertTrue(s.integer_wss_via_divisibility((5, 7, 11, 13)))
        self.assertFalse(s.integer_wss_via_divisibility((2, 3, 4)))
        self.assertFalse(s.integer_wss_via_divisibility((3, 6)))

    def test_rational_control(self):
        pts = (Fraction(13, 6), Fraction(19, 6), Fraction(16, 3))
        self.assertTrue(s.finite_well_separated(pts))
        self.assertTrue(s.pairwise_unit_separated(pts))
        self.assertTrue(s.unit_bin_injective(pts))
        self.assertTrue(s.multiple_exclusion(pts))

    def test_k1_violation_detected(self):
        pts = (Fraction(3, 2), Fraction(2, 1))
        self.assertFalse(s.finite_well_separated(pts))
        self.assertFalse(s.pairwise_unit_separated(pts))

    def test_higher_multiple_violation_detected(self):
        pts = (Fraction(13, 6), Fraction(13, 3))
        self.assertFalse(s.finite_well_separated(pts))
        self.assertTrue(s.pairwise_unit_separated(pts))

    def test_half_open_integer_interval_bound(self):
        pts = (Fraction(13, 6), Fraction(19, 6), Fraction(16, 3))
        for start in range(1, 8):
            for length in range(0, 8):
                self.assertTrue(s.integer_interval_occupancy_bound(pts, start, length))

    def test_exhaustive_receipt_counts(self):
        r = s.build_receipt(18)
        self.assertEqual(r["scan"]["total_subsets"], 131072)
        self.assertEqual(r["scan"]["primitive_or_integer_wss_subsets"], 3896)
        self.assertEqual(r["scan"]["max_primitive_cardinality"], 9)
        self.assertEqual(r["scan"]["maximizer_count"], 14)
        self.assertEqual(r["scan"]["equivalence_mismatches"], 0)
        self.assertEqual(r["scan"]["consequence_failures"], 0)

    def test_committed_receipt_exact(self):
        expected = json.loads(pathlib.Path(__file__).with_name("receipt.json").read_text())
        self.assertEqual(s.build_receipt(18), expected)


if __name__ == "__main__":
    unittest.main()
