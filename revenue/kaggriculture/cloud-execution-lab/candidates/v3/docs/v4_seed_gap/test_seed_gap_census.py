# SPDX-License-Identifier: Apache-2.0
import copy
from pathlib import Path
import tempfile
import unittest
import seed_gap_census as c


def action(farmer=None, hands=None, market=None):
    return {'farmer': ['PASS'] if farmer is None else farmer,
            'hands': [] if hands is None else hands,
            'market': [] if market is None else market}


class SeedLedgerTests(unittest.TestCase):
    def test_atomic_shortage_does_not_partially_consume(self):
        rows = [action(market=[['BUY_SEED', 'WHEAT', 1]]),
                action(['PLANT', 'WHEAT'], [['PLANT', 'WHEAT']])]
        out = c.seed_ledger(rows)
        self.assertEqual(out['ending_seeds']['WHEAT'], 1)
        self.assertEqual(out['modeled_plants_completed'].get('WHEAT', 0), 0)
        self.assertEqual(out['atomic_shortfalls'],
                         [{'step': 1, 'crop': 'WHEAT', 'requested': 2, 'available': 1}])

    def test_current_market_cannot_fund_current_plant(self):
        out = c.seed_ledger([action(['PLANT', 'WHEAT'],
                                    market=[['BUY_SEED', 'WHEAT', 1]])])
        self.assertEqual(len(out['atomic_shortfalls']), 1)
        self.assertEqual(out['ending_seeds']['WHEAT'], 1)

    def test_next_callback_can_use_previous_purchase(self):
        out = c.seed_ledger([action(market=[['BUY_SEED', 'WHEAT', 1]]),
                             action(['PLANT', 'WHEAT'])])
        self.assertEqual(out['atomic_shortfalls'], [])
        self.assertEqual(out['modeled_plants_completed']['WHEAT'], 1)

    def test_dead_suffix_and_tombstones_consume_raw_cap(self):
        out = c.seed_ledger([action(market=[[], ['BUY_SEED', 'WHEAT', 9]])], cap=1)
        self.assertEqual(out['bought'], {})

    def test_different_crop_groups_are_independent(self):
        out = c.seed_ledger([action(market=[['BUY_SEED', 'CARROT', 1]]),
                             action(['PLANT', 'WHEAT'], [['PLANT', 'CARROT']])])
        self.assertEqual(out['modeled_plants_completed'], {'CARROT': 1})
        self.assertEqual(out['atomic_shortfalls'][0]['crop'], 'WHEAT')

    def test_intervention_is_after_units_and_preserves_input(self):
        rows = [action(['PLANT', 'WHEAT']), action(['PLANT', 'WHEAT'])]
        before = copy.deepcopy(rows)
        out = c.seed_ledger(rows, extra_buys={0: [('WHEAT', 1)]})
        self.assertEqual(rows, before)
        self.assertEqual([x['step'] for x in out['atomic_shortfalls']], [0])
        self.assertEqual(out['modeled_plants_completed']['WHEAT'], 1)

    def test_intervention_requires_executable_slot(self):
        with self.assertRaises(ValueError):
            c.seed_ledger([action(market=[[]])], cap=1,
                          extra_buys={0: [('WHEAT', 1)]})

    def test_bool_quantity_is_not_a_seed_count(self):
        with self.assertRaises(ValueError):
            c.seed_ledger([action(market=[['BUY_SEED', 'WHEAT', True]])])

    def test_routing_splices_frozen_boundary_plans(self):
        tapes = [[action(market=[['TAG', plan, step]]) for step in range(719)]
                 for plan in range(13)]
        rows = c.routed_actions(tapes, 10)
        for step, plan in ((143, 0), (144, 10), (647, 10), (648, 2), (717, 2)):
            self.assertIs(rows[step], tapes[plan][step])
        self.assertEqual(rows[718], action())

    def test_tape_identity_is_checked_before_parsing(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'fake.py'
            path.write_text('raise RuntimeError("must never run")')
            with self.assertRaisesRegex(ValueError, 'identity'):
                c.load_tapes(path)


if __name__ == '__main__':
    unittest.main()
