# SPDX-License-Identifier: Apache-2.0
"""E05 pure joint market composition contracts; no engine or game execution."""
import unittest
from selected_sell_core import joint_plan_metrics, shared_slot_ledger


def info(a,b):
    return {'scenarios':{'no_rival':{'reference_relative_value':0,'relative_value':a},
                         'observed_paired':{'reference_relative_value':0,'relative_value':b}}}

class JointMarketCompositionTests(unittest.TestCase):
    def test_two_products_share_scenario_value(self):
        out=joint_plan_metrics([info(3,2),info(5,1)])
        self.assertEqual(out['scenario_deltas'],{'no_rival':8.0,'observed_paired':3.0})
        self.assertEqual(out['worst_relative_gain'],3.0)

    def test_mismatched_scenarios_decline(self):
        self.assertIsNone(joint_plan_metrics([info(1,1),{'scenarios':{'x':{}}}]))

    def test_two_extras_fit_last_two_slots(self):
        inherited=[['HIRE'] for _ in range(8)]
        plans={'MILK':((4,2),),'EGG':((4,3),)}
        ledger=shared_slot_ledger(plans,lambda _t:inherited,10)
        self.assertEqual(ledger[4]['extra_items'],['EGG','MILK'])
        self.assertEqual(ledger[4]['total_slots'],10)

    def test_pair_rejected_when_only_one_slot_remains(self):
        inherited=[['HIRE'] for _ in range(9)]
        plans={'MILK':((4,2),),'EGG':((4,3),)}
        self.assertIsNone(shared_slot_ledger(plans,lambda _t:inherited,10))

    def test_existing_sell_capacity_needs_no_extra_slot(self):
        inherited=[['SELL','MILK',2]]+[['HIRE'] for _ in range(8)]
        plans={'MILK':((4,2),),'EGG':((4,3),)}
        ledger=shared_slot_ledger(plans,lambda _t:inherited,10)
        self.assertEqual(ledger[4]['extra_items'],['EGG'])

    def test_different_future_dates_allocate_independently(self):
        plans={'MILK':((5,2),),'EGG':((6,3),)}
        ledger=shared_slot_ledger(plans,lambda _t:[['HIRE'] for _ in range(9)],10)
        self.assertEqual(ledger[5]['total_slots'],10)
        self.assertEqual(ledger[6]['total_slots'],10)

if __name__=='__main__':unittest.main()
