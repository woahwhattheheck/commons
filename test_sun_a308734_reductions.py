from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parent / "revenue" / "sun-a308734" / "reduction_residues.py"
SPEC = importlib.util.spec_from_file_location("sun_a308734_reduction_residues", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
r = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = r
SPEC.loader.exec_module(r)


class SunA308734ReductionTests(unittest.TestCase):
    def test_exact_restricted_square_residue_sets(self) -> None:
        self.assertEqual(r.S5_SQUARES_MOD24, frozenset({1, 4, 16}))
        self.assertEqual(r.S3_SQUARES_MOD12, frozenset({0, 1, 4, 9}))
        self.assertEqual(r.RESTRICTED_SQUARES_MOD8, frozenset({0, 1, 4}))

    def test_conditional_ternary_bridges_cover_exactly_half_primitive_mod24(self) -> None:
        self.assertEqual(r.TERNARY_3_BRIDGE_MOD24, frozenset({2, 11, 14}))
        self.assertEqual(r.TERNARY_5_BRIDGE_MOD12, frozenset({2, 5, 6, 9}))
        self.assertEqual(r.TERNARY_5_BRIDGE_MOD24, frozenset({2, 5, 6, 9, 14, 17, 18, 21}))
        self.assertEqual(
            r.CONDITIONAL_BRIDGE_MOD24,
            frozenset({2, 5, 6, 9, 11, 14, 17, 18, 21}),
        )
        self.assertTrue(r.CONDITIONAL_BRIDGE_MOD24 <= r.PRIMITIVE_MOD24)
        self.assertEqual(len(r.PRIMITIVE_MOD24), 18)
        self.assertEqual(len(r.CONDITIONAL_BRIDGE_MOD24), 9)

    def test_bridge_subtrahends_have_required_exact_semigroup_forms(self) -> None:
        # Ternary-3 bridge subtracts 1^2, 2^2, or 4^2 from the 2^c*5^d semigroup.
        for residue, square in {11: 1, 14: 4, 2: 16}.items():
            n = residue if residue > 2 else residue + 24
            self.assertEqual(r.ternary3_subtrahend(n), square)
            self.assertEqual((n - square) % 24, 10)

        # Ternary-5 bridge subtracts 6^2, 1^2, 2^2, or 3^2 from 2^a*3^b.
        for residue, square in {5: 36, 6: 1, 9: 4, 2: 9}.items():
            n = residue + 36
            self.assertEqual(r.ternary5_subtrahend(n), square)
            self.assertEqual((n - square) % 12, 5)

    def test_only_small_positive_remainder_exceptions_are_directly_witnessed(self) -> None:
        exceptions = {
            n
            for n in range(2, 37)
            if n % 4 != 0
            and n % 24 in r.CONDITIONAL_BRIDGE_MOD24
            and r.conditional_bridge(n) is None
        }
        self.assertEqual(exceptions, {2, 5, 17, 29})
        self.assertEqual(set(r.DIRECT_SMALL_WITNESSES), exceptions)
        for n, witness in r.DIRECT_SMALL_WITNESSES.items():
            with self.subTest(n=n):
                self.assertEqual(witness.value, n)

    def test_every_other_covered_residue_gets_the_claimed_positive_ternary_remainder(self) -> None:
        # Two representatives per covered residue are enough to verify the fixed
        # subtractand/residue plumbing; this is not interval evidence for A308734.
        for residue in sorted(r.CONDITIONAL_BRIDGE_MOD24):
            for n in (residue if residue > 1 else residue + 24, residue + 24):
                if n in r.DIRECT_SMALL_WITNESSES:
                    continue
                certificate = r.conditional_bridge(n)
                self.assertIsNotNone(certificate, (residue, n))
                theorem, square, remainder = certificate
                self.assertGreater(remainder, 0)
                self.assertEqual(n, square + remainder)
                if theorem == "SUN_TERNARY_3":
                    self.assertEqual(remainder % 24, 10)
                elif theorem == "SUN_TERNARY_5":
                    self.assertEqual(remainder % 12, 5)
                else:
                    self.fail(f"unexpected conditional theorem {theorem}")

    def test_four_adic_lift_is_exact_and_closed_in_required_semigroups(self) -> None:
        seeds = list(r.DIRECT_SMALL_WITNESSES.values()) + [r.Representation(7, 4, 2, 3, 1, 2)]
        for witness in seeds:
            with self.subTest(witness=witness):
                lifted = witness.lift_by_four()
                self.assertEqual(lifted.value, 4 * witness.value)
                self.assertEqual(lifted.x, 2 * witness.x)
                self.assertEqual(lifted.y, 2 * witness.y)
                self.assertEqual(lifted.a, witness.a + 1)
                self.assertEqual(lifted.b, witness.b)
                self.assertEqual(lifted.c, witness.c + 1)
                self.assertEqual(lifted.d, witness.d)

    def test_mod8_has_no_standalone_residue_obstruction(self) -> None:
        self.assertEqual(r.TWO_SQUARE_SUMS_MOD8, frozenset({0, 1, 2, 4, 5}))
        self.assertEqual(r.RESTRICTED_PAIR_SUMS_MOD8, r.TWO_SQUARE_SUMS_MOD8)
        table = r.mod8_local_table()
        self.assertEqual(set(table), set(range(8)))
        self.assertTrue(all(choices for choices in table.values()))
        for n_mod8, choices in table.items():
            for pair in choices:
                self.assertIn((n_mod8 - pair) % 8, r.TWO_SQUARE_SUMS_MOD8)

    def test_representation_rejects_non_integer_or_negative_parameters(self) -> None:
        with self.assertRaises(ValueError):
            r.Representation(True, 0, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            r.Representation(0, 0, -1, 0, 0, 0)


if __name__ == "__main__":
    unittest.main()
