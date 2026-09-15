"""Supporting tests for the existing synthetic POLAR calculator, not engine parity."""
import dataclasses
import json
import math
import random
import unittest
from unittest.mock import patch

import polar_seed_liquidation as p


class AccountingRepairTests(unittest.TestCase):
    def case(self, **overrides):
        args = dict(book=p.MarketBook(10.0, 1.0), committed_output=0,
                    extra_yield=1, buy_seed=1, seed_price=6.0)
        args.update(overrides)
        return p.SeedCase(**args)

    def test_equal_losses_are_not_a_sign_flip(self):
        v = p.evaluate(self.case(book=p.MarketBook(10.0, 0.0), seed_price=20.0))
        self.assertEqual(v.naive_incremental - v.purchase_cost, -10.0)
        self.assertEqual(v.net_sequential, -10.0)
        self.assertFalse(v.sign_flip)

    def test_cost_alone_is_not_a_price_impact_flip(self):
        v = p.evaluate(self.case(committed_output=8, extra_yield=3, seed_price=100.0))
        self.assertEqual(v.naive_incremental - v.purchase_cost, -70.0)
        self.assertEqual(v.net_sequential, -97.0)
        self.assertFalse(v.sign_flip)

    def test_real_positive_to_negative_flip_is_retained(self):
        v = p.evaluate(self.case(committed_output=8, extra_yield=3))
        self.assertEqual(v.naive_net_incremental, 24.0)
        self.assertEqual(v.net_sequential, -3.0)
        self.assertTrue(v.sign_flip)

    def test_sequential_break_even_is_not_strict_sign_flip(self):
        v = p.evaluate(self.case(committed_output=8, extra_yield=3, seed_price=3.0))
        self.assertEqual(v.net_sequential, 0.0)
        self.assertFalse(v.sign_flip)

    def test_naive_break_even_is_not_strict_sign_flip(self):
        v = p.evaluate(self.case(committed_output=8, extra_yield=3, seed_price=30.0))
        self.assertEqual(v.naive_net_incremental, 0.0)
        self.assertLess(v.net_sequential, 0)
        self.assertFalse(v.sign_flip)

    def test_gross_metric_remains_available(self):
        v = p.evaluate(self.case(extra_yield=3, buy_seed=2, seed_price=6.0))
        self.assertEqual(v.naive_incremental, 30.0)
        self.assertEqual(v.purchase_cost, 12.0)
        self.assertEqual(v.naive_net_incremental, 18.0)

    def test_owned_seed_remains_sunk(self):
        v = p.evaluate(self.case(owned_seed=100, buy_seed=0, seed_price=1000.0))
        self.assertEqual(v.purchase_cost, 0.0)
        self.assertEqual(v.naive_net_incremental, v.naive_incremental)

    def test_negative_purchase_cost_is_rejected(self):
        with self.assertRaises(ValueError):
            p.evaluate(self.case(seed_price=-5.0))

    def test_strict_case_counts(self):
        for key in ('committed_output', 'extra_yield', 'owned_seed', 'buy_seed'):
            for value in (-1, -0.5, 0.5, 1.9, True, False, '1', None,
                          float('nan'), float('inf')):
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ValueError):
                        p.evaluate(self.case(**{key: value}))

    def test_strict_market_numbers(self):
        for key in ('quote0', 'impact', 'floor'):
            for value in (-1.0, True, False, '1', None, float('nan'),
                          float('inf'), -float('inf')):
                values = dict(quote0=10.0, impact=1.0, floor=0.0)
                values[key] = value
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ValueError):
                        p.MarketBook(**values)

    def test_floor_above_initial_quote_rejected(self):
        with self.assertRaises(ValueError):
            p.MarketBook(1.0, 1.0, 2.0)

    def test_finite_case_cost_and_yield_metadata(self):
        for key in ('seed_price', 'realized_yield_per_seed'):
            for value in (-1.0, True, '1', None, float('nan'), float('inf')):
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ValueError):
                        self.case(**{key: value})

    def test_liquidation_counts_and_offsets(self):
        book = p.MarketBook(10.0, 1.0)
        for value in (-1, 0.5, True, False, '1', None, float('nan')):
            with self.subTest(value=value):
                for call in (lambda: p.liquidate(book, value),
                             lambda: p.liquidate(book, 0, value),
                             lambda: p.revenue(book, 0, value),
                             lambda: book.price_after(value)):
                    with self.assertRaises(ValueError):
                        call()

    def test_naive_helper_domain(self):
        for value in (-1, 0.5, True, '1', None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    p.naive_incremental(10.0, value)
        for value in (-1.0, True, float('nan'), float('inf')):
            with self.subTest(quote=value):
                with self.assertRaises(ValueError):
                    p.naive_incremental(value, 1)

    def test_wrong_book_type_rejected(self):
        for value in (None, {}, 'linear'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.case(book=value)
                with self.assertRaises(ValueError):
                    p.revenue(value, 0)

    def test_revenue_overflow_rejected(self):
        with self.assertRaises(ValueError):
            p.revenue(p.MarketBook(1e308, 0.0), 2)

    def test_purchase_overflow_rejected(self):
        with self.assertRaises(ValueError):
            p.evaluate(self.case(buy_seed=2, seed_price=1e308))

    def test_naive_overflow_rejected(self):
        with self.assertRaises(ValueError):
            p.naive_incremental(1e308, 2)

    def test_intermediate_nonfinite_price_rejected(self):
        with self.assertRaises(ValueError):
            p.MarketBook(10.0, 1e308).price_after(2)

    def test_huge_numeric_inputs_raise_value_error(self):
        huge = 10 ** 1000
        with self.assertRaises(ValueError):
            p.MarketBook(huge, 0.0)
        with self.assertRaises(ValueError):
            self.case(seed_price=huge)
        with self.assertRaises(ValueError):
            p.naive_incremental(1.0, huge)

    def test_successful_reports_are_finite_json(self):
        v = p.evaluate(self.case(committed_output=8, extra_yield=3))
        data = dataclasses.asdict(v)
        json.dumps(data, allow_nan=False)
        self.assertEqual(data['pricing_model'], 'synthetic-linear')

    def test_inputs_are_not_mutated(self):
        case = self.case(committed_output=8, extra_yield=3)
        before = dataclasses.asdict(case)
        p.evaluate(case)
        p.break_even_extra_yield(case, 10)
        self.assertEqual(dataclasses.asdict(case), before)

    def test_dataclasses_remain_frozen(self):
        case = self.case()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            case.extra_yield = 2
        with self.assertRaises(dataclasses.FrozenInstanceError):
            case.book.quote0 = 0.0

    def test_existing_positional_valuation_arguments_preserved(self):
        v = p.Valuation(1, 2, 3, 4, 5, 6, False, 'i', 'e', 'c')
        self.assertEqual((v.interpreter_sha, v.engine_blob_sha, v.claim), ('i', 'e', 'c'))


class BreakEvenRepairTests(unittest.TestCase):
    def test_horizon_twenty_uses_at_most_twenty_quotes(self):
        case = p.SeedCase(p.MarketBook(1.0, 0.0), 100, 0,
                          buy_seed=1, seed_price=1000.0)
        original = p.MarketBook.price_after
        with patch.object(p.MarketBook, 'price_after', autospec=True,
                          side_effect=original) as counted:
            self.assertIsNone(p.break_even_extra_yield(case, 20))
        self.assertEqual(counted.call_count, 20)
        self.assertEqual([c.args[1] for c in counted.call_args_list], list(range(100, 120)))

    def test_zero_purchase_needs_no_price_walk(self):
        case = p.SeedCase(p.MarketBook(1.0, 0.0), 10000, 0)
        with patch.object(p.MarketBook, 'price_after', side_effect=AssertionError('walk')):
            self.assertEqual(p.break_even_extra_yield(case, 100), 0)

    def test_threshold_at_last_permitted_unit(self):
        case = p.SeedCase(p.MarketBook(1.0, 0.0), 100, 0, buy_seed=1, seed_price=20)
        self.assertIsNone(p.break_even_extra_yield(case, 19))
        self.assertEqual(p.break_even_extra_yield(case, 20), 20)

    def test_zero_horizon(self):
        book = p.MarketBook(1.0, 0.0)
        self.assertIsNone(p.break_even_extra_yield(p.SeedCase(book, 0, 0, buy_seed=1, seed_price=1), 0))
        self.assertEqual(p.break_even_extra_yield(p.SeedCase(book, 0, 0), 0), 0)

    def test_nonzero_floor_can_recover_after_glut(self):
        case = p.SeedCase(p.MarketBook(10.0, 1.0, 1.0), 100, 0,
                          buy_seed=1, seed_price=6.0)
        self.assertEqual(p.break_even_extra_yield(case, 10), 6)

    def test_zero_floor_can_remain_unprofitable(self):
        case = p.SeedCase(p.MarketBook(10.0, 1.0), 8, 0,
                          buy_seed=1, seed_price=4.0)
        self.assertIsNone(p.break_even_extra_yield(case, 100))

    def test_max_extra_must_be_plain_nonnegative_int(self):
        case = p.SeedCase(p.MarketBook(1.0, 0.0), 0, 0)
        for value in (-1, 0.5, True, False, '1', None, float('nan')):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    p.break_even_extra_yield(case, value)

    def test_cost_overflow_rejected_even_at_zero_horizon(self):
        case = p.SeedCase(p.MarketBook(1.0, 0.0), 0, 0,
                          buy_seed=2, seed_price=1e308)
        with self.assertRaises(ValueError):
            p.break_even_extra_yield(case, 0)

    def test_extra_revenue_overflow_rejected(self):
        case = p.SeedCase(p.MarketBook(1e308, 0.0), 0, 0,
                          buy_seed=1, seed_price=1.7e308)
        with self.assertRaises(ValueError):
            p.break_even_extra_yield(case, 2)

    def test_wrong_case_rejected(self):
        for value in (None, {}, 'case'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    p.break_even_extra_yield(value, 0)
                with self.assertRaises(ValueError):
                    p.evaluate(value)

    def test_exhaustive_binary_exact_grid_matches_brute_force(self):
        count = 0
        for quote in (0.0, 1.0, 2.0, 10.0, 17.5):
            for impact in (0.0, 0.25, 1.0, 3.0):
                for floor in (0.0, min(quote, 1.0)):
                    for committed in (0, 1, 8, 32):
                        for cost in (0.0, 0.25, 3.0, 20.0):
                            book = p.MarketBook(quote, impact, floor)
                            case = p.SeedCase(book, committed, 0, buy_seed=1, seed_price=cost)
                            values = [p.evaluate(dataclasses.replace(case, extra_yield=n)).net_sequential
                                      for n in range(21)]
                            expected = next((n for n, net in enumerate(values) if net >= 0), None)
                            with self.subTest(quote=quote, impact=impact, floor=floor,
                                              committed=committed, cost=cost):
                                self.assertEqual(p.break_even_extra_yield(case, 20), expected)
                            count += 1
        self.assertEqual(count, 640)

    def test_random_float_thresholds_match_brute_force(self):
        rng = random.Random(47961)
        for _ in range(200):
            book = p.MarketBook(rng.uniform(1.0, 30.0), rng.uniform(0.0, 3.0), 0.0)
            committed = rng.randrange(12)
            limit = rng.randrange(1, 41)
            witness = rng.randrange(limit + 1)
            cash = p.revenue(book, witness, committed)
            cost = rng.choice((cash, math.nextafter(cash, math.inf), max(0.0, math.nextafter(cash, -math.inf))))
            case = p.SeedCase(book, committed, 0, buy_seed=1, seed_price=cost)
            expected = next((n for n in range(limit + 1)
                             if p.evaluate(dataclasses.replace(case, extra_yield=n)).net_sequential >= 0), None)
            self.assertEqual(p.break_even_extra_yield(case, limit), expected)


if __name__ == '__main__':
    unittest.main()
