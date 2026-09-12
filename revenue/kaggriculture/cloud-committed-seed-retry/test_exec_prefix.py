# SPDX-License-Identifier: Apache-2.0
"""Discriminators for committed-seed executable market-prefix accounting."""
from copy import deepcopy
import unittest

import seed_retry
import test_seed_retry as base


class ExecutablePrefixTests(unittest.TestCase):
    def runtime(self):
        return base.RuntimeAdapterTests().runtime()

    def test_dead_product_suffix_does_not_veto(self):
        runtime = self.runtime()
        runtime.controller.R['fixture'][12]['market'] = [
            *([[]] * 10), ['BUY_PRODUCT', 'WHEAT', 3]
        ]
        action, report = seed_retry.apply_committed_seed_retry(
            runtime, base.fixture(), base.CFG, deepcopy(base.PASS))
        self.assertEqual(report['status'], 'appended')
        self.assertEqual(action['market'], [['BUY_SEED', 'STRAWBERRY', 1]])

    def test_live_product_prefix_still_vetoes(self):
        runtime = self.runtime()
        runtime.controller.R['fixture'][12]['market'] = [
            *([[]] * 9), ['BUY_PRODUCT', 'WHEAT', 3], []
        ]
        action, report = seed_retry.apply_committed_seed_retry(
            runtime, base.fixture(), base.CFG, deepcopy(base.PASS))
        self.assertEqual(report['reason'], 'dynamic_product_obligation_in_reserve_window')
        self.assertEqual(action, base.PASS)

    def test_dead_fixed_cost_suffix_does_not_phantom_reserve(self):
        runtime = self.runtime()
        runtime.controller.R['fixture'][12]['market'] = [
            *([[]] * 10), ['BUY_SEED', 'STRAWBERRY', 10]
        ]
        _, report = seed_retry.apply_committed_seed_retry(
            runtime, base.fixture(), base.CFG, deepcopy(base.PASS))
        self.assertEqual(report['status'], 'appended')

        runtime = self.runtime()
        runtime.controller.R['fixture'][12]['market'] = [
            *([[]] * 9), ['BUY_SEED', 'STRAWBERRY', 10], []
        ]
        _, report = seed_retry.apply_committed_seed_retry(
            runtime, base.fixture(), base.CFG, deepcopy(base.PASS))
        self.assertEqual(report['reason'], 'preserve_reserved_obligations')

    def test_nondefault_limits_define_live_prefix(self):
        runtime = self.runtime()
        runtime.controller.R['fixture'][12]['market'] = [
            *([[]] * 10), ['BUY_PRODUCT', 'WHEAT', 1]
        ]
        cfg = dict(base.CFG, maxMarketOrdersPerTurn=12)
        _, report = seed_retry.apply_committed_seed_retry(
            runtime, base.fixture(), cfg, deepcopy(base.PASS))
        self.assertEqual(report['reason'], 'dynamic_product_obligation_in_reserve_window')

        runtime = self.runtime()
        runtime.controller.R['fixture'][12]['market'] = [
            [], [], [], ['BUY_PRODUCT', 'WHEAT', 1]
        ]
        cfg = dict(base.CFG, maxMarketOrdersPerTurn=3)
        _, report = seed_retry.apply_committed_seed_retry(
            runtime, base.fixture(), cfg, deepcopy(base.PASS))
        self.assertEqual(report['status'], 'appended')


if __name__ == '__main__':
    unittest.main(verbosity=2)
