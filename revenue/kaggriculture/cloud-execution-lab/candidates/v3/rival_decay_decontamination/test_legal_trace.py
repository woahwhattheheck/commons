# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

import witness


class LegalInterpreterTraceTests(unittest.TestCase):
    def test_reachable_predecessor_changes_returned_sell_action(self):
        payload = witness.run()

        self.assertEqual(payload["legal_trace"]["action_count"], 96)
        self.assertEqual(payload["legal_trace"]["derived"]["step"], 96)
        self.assertEqual(payload["legal_trace"]["derived"]["own_carrot_shed"], 6)
        self.assertEqual(payload["legal_trace"]["derived"]["market_carrot_inventory"], 9996)
        self.assertEqual(
            payload["legal_trace"]["derived"]["rival_predecessor_actor_positions"],
            {"farmer": [5, 4], "hands": []},
        )
        self.assertEqual(
            payload["legal_trace"]["derived"]["rival_before"],
            {
                "kind": "PLANT",
                "crop": "CARROT",
                "planted_day": 0,
                "max_lifespan_step": 96,
                "yield_units": 1,
                "watered_today": False,
                "consecutive_unwatered": 1,
                "fertilized_until_day": -1,
            },
        )
        self.assertEqual(payload["legal_trace"]["derived"]["rival_after"], {"kind": "WEED"})
        self.assertEqual(payload["observer"]["control_ledger"], {"CARROT": [(96, 1)]})
        self.assertEqual(payload["observer"]["candidate_ledger"], {})
        self.assertEqual(
            [payload["observer"]["control_supply"], payload["observer"]["candidate_supply"]],
            [1, 0],
        )
        self.assertEqual(payload["optimizer"]["dates"], [96, 97, 104])
        self.assertEqual(payload["optimizer"]["control_plan"], [[96, 6]])
        self.assertEqual(payload["optimizer"]["candidate_plan"], [[96, 5]])
        self.assertEqual(payload["optimizer"]["control_gain"], 0.0)
        self.assertEqual(payload["optimizer"]["candidate_gain"], 1.0)
        self.assertEqual(payload["caller"]["control_carrot_sold"], 6)
        self.assertEqual(payload["caller"]["candidate_carrot_sold"], 5)
        self.assertNotEqual(payload["caller"]["control_action"], payload["caller"]["candidate_action"])


if __name__ == "__main__":
    unittest.main()
