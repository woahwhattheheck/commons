# SPDX-License-Identifier: Apache-2.0
import unittest

from fourth_quadrant import FourthQuadrant


OBS = {
    'step': 264,
    'player': 0,
    'farms': [{'hands': []}],
}


def proposal():
    return {
        'start': 264,
        'crop': 'CARROT',
        'tiles': [(5, 5), (6, 5), (5, 6)],
        'workers': 1,
        'cost': 4123,
    }


def row(market):
    return {'farmer': ['PASS'], 'hands': [], 'market': market}


class FourthQuadrantCommitGateTests(unittest.TestCase):
    def finish(self, selected_market, returned_market):
        gate = FourthQuadrant(None, None)
        pending = proposal()
        gate.pending = pending
        gate.selected = row(selected_market)
        gate.finish(OBS, row(returned_market))
        return gate, pending

    def test_exact_current_purchase_commitment_can_publish_plan(self):
        market = [['BUY_LAND'], ['BUY_SEED', 'CARROT', 6], ['HIRE']]
        gate, pending = self.finish(market, market)
        self.assertIs(gate.plan, pending)
        self.assertEqual(gate.generation, 1)
        self.assertEqual(gate.events[-1]['kind'], 'bundle_admitted')

    def test_dropped_current_land_purchase_rejects_plan(self):
        selected = [['BUY_LAND'], ['BUY_SEED', 'CARROT', 6], ['HIRE']]
        returned = [['BUY_SEED', 'CARROT', 6], ['HIRE']]
        gate, _ = self.finish(selected, returned)
        self.assertIsNone(gate.plan)
        self.assertEqual(gate.generation, 0)
        self.assertIsNone(gate.pending)
        self.assertIsNone(gate.selected)

    def test_reduced_current_seed_quantity_rejects_plan(self):
        selected = [['BUY_LAND'], ['BUY_SEED', 'CARROT', 6], ['HIRE']]
        returned = [['BUY_LAND'], ['BUY_SEED', 'CARROT', 5], ['HIRE']]
        gate, _ = self.finish(selected, returned)
        self.assertIsNone(gate.plan)
        self.assertEqual(gate.generation, 0)

    def test_split_seed_orders_preserve_equivalent_quantity(self):
        selected = [['BUY_LAND'], ['BUY_SEED', 'CARROT', 6], ['HIRE']]
        returned = [
            ['BUY_LAND'],
            ['BUY_SEED', 'CARROT', 2],
            ['BUY_SEED', 'CARROT', 4],
            ['HIRE'],
        ]
        gate, pending = self.finish(selected, returned)
        self.assertIs(gate.plan, pending)

    def test_future_dated_purchases_are_not_required_at_admission_step(self):
        # A proposal can schedule its first land/seed purchase later in the day.
        # When the producer selected no current purchase, finish must preserve
        # the incumbent admission semantics instead of requiring future orders.
        selected = [['HIRE']]
        gate, pending = self.finish(selected, selected)
        self.assertIs(gate.plan, pending)


if __name__ == '__main__':
    unittest.main()
