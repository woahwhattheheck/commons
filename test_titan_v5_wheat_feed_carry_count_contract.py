"""Certified helper counts obey the same exact-integer contract as input counts.

Regression for Commons PR #15761 at 9d28247a10ad1b911050eb865b7a74bba6eb5cf2.
ZZ-THALWEG-62F9; original oracle and predecessor-test credit is unchanged.
All records are synthetic. These tests do not execute the gameplay runtime.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
MODULE = ROOT / 'revenue/kaggriculture/cloud-execution-lab/candidates/v5/lean-feed-carry-economics/wheat_feed_carry_oracle.py'
SPEC = importlib.util.spec_from_file_location('wheat_count_contract_subject', MODULE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError('cannot load wheat carry oracle')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
FIELDS = ('required_wheat', 'observed_shed_wheat', 'eod_wheat_credit', 'withheld_units')


def packet(stock=1, returned=0, required=1, offered=1):
    # Independent fixture arithmetic: never ask the production helper to tell
    # this test which recorded quantity should count as correct.
    sold = min(stock, offered)
    withheld = max(0, required - (stock - sold + returned))
    return {
        'observed_shed_wheat': stock,
        'eod_wheat_credit': returned,
        'required_wheat': required,
        'offered_wheat': offered,
        'helper_report': {
            'certified': True, 'changed': withheld > 0,
            'required_wheat': required, 'observed_shed_wheat': stock,
            'eod_wheat_credit': returned, 'withheld_units': withheld,
        },
    }


class WheatHelperCountContractTests(unittest.TestCase):
    def rejected(self, p, field):
        with self.assertRaisesRegex(m.WheatCensusError, 'helper ' + field):
            m.analyze_certified_window(p)

    def test_equivalent_booleans_are_not_recorded_counts(self):
        for base in (packet(), packet(0, 1, 0, 0)):
            for field in FIELDS:
                with self.subTest(field=field, expected=base['helper_report'][field]):
                    p = copy.deepcopy(base)
                    p['helper_report'][field] = bool(p['helper_report'][field])
                    self.rejected(p, field)

    def test_equivalent_floats_are_not_recorded_counts(self):
        for base in (packet(), packet(0, 1, 0, 0), packet(100, 100, 200, 2)):
            for field in FIELDS:
                with self.subTest(field=field, expected=base['helper_report'][field]):
                    p = copy.deepcopy(base)
                    p['helper_report'][field] = float(p['helper_report'][field])
                    self.rejected(p, field)

    def test_json_round_trip_does_not_erase_numeric_type_contract(self):
        for field in FIELDS:
            for convert in (bool, float):
                with self.subTest(field=field, convert=convert.__name__):
                    p = packet()
                    p['helper_report'][field] = convert(p['helper_report'][field])
                    self.rejected(json.loads(json.dumps(p)), field)

    def test_missing_certified_count_names_the_field(self):
        for field in FIELDS:
            with self.subTest(field=field):
                p = packet()
                del p['helper_report'][field]
                self.rejected(p, field)

    def test_null_text_container_and_negative_counts_are_rejected(self):
        for field in FIELDS:
            for value in (None, '1', [], {}, -1):
                with self.subTest(field=field, value=value):
                    p = packet()
                    p['helper_report'][field] = value
                    self.rejected(p, field)

    def test_helper_count_upper_bounds_are_preserved(self):
        bounds = {'required_wheat': 200, 'observed_shed_wheat': 100,
                  'eod_wheat_credit': 100, 'withheld_units': 2}
        for field, maximum in bounds.items():
            with self.subTest(field=field):
                p = packet()
                p['helper_report'][field] = maximum + 1
                self.rejected(p, field)

    def test_different_but_valid_integer_is_still_a_mismatch(self):
        for field in FIELDS:
            with self.subTest(field=field):
                p = packet()
                p['helper_report'][field] = 0 if p['helper_report'][field] else 1
                with self.assertRaisesRegex(m.WheatCensusError, 'helper ' + field + ' mismatch'):
                    m.analyze_certified_window(p)

    def test_valid_integer_boundaries_and_zero_remain_accepted(self):
        cases = [(0, 0, 0, 0), (1, 0, 1, 1), (0, 1, 1, 1),
                 (100, 100, 200, 2), (100, 0, 2, 100),
                 (100, 100, 0, 100), (1, 1, 2, 1)]
        for args in cases:
            with self.subTest(args=args):
                p = packet(*args)
                result = m.analyze_certified_window(p)
                self.assertEqual(result['state'], m.NEGATIVE)
                self.assertEqual(result['current_policy_withheld'], p['helper_report']['withheld_units'])
                self.assertIs(result['candidate_build_authorized'], False)
                self.assertIs(result['promotion_authorized'], False)

    def test_uncertified_report_can_still_omit_counts(self):
        p = packet()
        p['helper_report'] = {'certified': False, 'reason': 'window not supported'}
        result = m.analyze_certified_window(p)
        self.assertEqual(result['state'], m.UNCERTIFIED)
        self.assertEqual(result['reason'], 'window not supported')
        self.assertIs(result['candidate_build_authorized'], False)
        self.assertIs(result['promotion_authorized'], False)

    def test_non_boolean_certification_does_not_become_certified(self):
        for value in (0, 1, 'true', None):
            with self.subTest(value=value):
                p = packet()
                p['helper_report']['certified'] = value
                self.assertEqual(m.analyze_certified_window(p)['state'], m.UNCERTIFIED)

    def test_changed_flag_remains_an_exact_boolean(self):
        for p in (packet(), packet(0, 0, 0, 0)):
            p['helper_report']['changed'] = int(p['helper_report']['changed'])
            with self.assertRaisesRegex(m.WheatCensusError, 'helper changed flag mismatch'):
                m.analyze_certified_window(p)

    def test_upstream_gap_still_does_not_imply_candidate_authority(self):
        result = m.analyze_certified_window(packet(5, 0, 1, 3))
        self.assertEqual(result['upstream_balance_offer_gap_units'], 1)
        self.assertEqual(result['current_policy_withheld'], 0)
        self.assertEqual(result['min_provable_withheld'], 0)
        self.assertEqual(result['upstream_offer_census_state'], m.UPSTREAM_GATE)
        self.assertIs(result['candidate_build_authorized'], False)
        self.assertIs(result['promotion_authorized'], False)


if __name__ == '__main__':
    unittest.main()
