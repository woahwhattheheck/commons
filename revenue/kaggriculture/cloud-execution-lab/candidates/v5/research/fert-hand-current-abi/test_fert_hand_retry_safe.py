# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import unittest

from fert_hand_current_safe import FertHandCurrentABI
from test_fert_hand_current import observation, route_tail, selected


class FertHandRetrySafetyTests(unittest.TestCase):
    def test_clean_same_step_retry_replays_identically(self):
        adapter = FertHandCurrentABI()
        obs = observation()
        parent = selected(market=[["SELL", "WOOL", 1]])
        tail = route_tail(obs["step"])

        first, first_report = adapter.transform_selected(
            obs, {}, parent, future_actions=tail
        )
        retry, retry_report = adapter.transform_selected(
            obs, {}, parent, future_actions=tail
        )

        self.assertEqual(first_report["reason"], "admit_fertilizer_hand")
        self.assertEqual(retry_report["reason"], "reapply_hire_plan")
        self.assertEqual(retry, first)

    def test_future_parent_hire_on_retry_retires_candidate_plan(self):
        adapter = FertHandCurrentABI()
        obs = observation()
        parent = selected(market=[["SELL", "WOOL", 1]])
        clean = route_tail(obs["step"])
        first, report = adapter.transform_selected(
            obs, {}, parent, future_actions=clean
        )
        self.assertTrue(report["changed"])
        self.assertIn(["HIRE"], first["market"])

        changed = deepcopy(clean)
        changed[0]["market"] = [["HIRE"]]
        retry, retry_report = adapter.transform_selected(
            obs, {}, parent, future_actions=changed
        )
        self.assertFalse(retry_report["changed"])
        self.assertEqual(retry_report["reason"], "future_parent_hire_retry")
        self.assertEqual(retry, parent)

        # Once refreshed parent authority conflicts, a later same-step view may
        # not resurrect the cached candidate HIRE.
        third, third_report = adapter.transform_selected(
            obs, {}, parent, future_actions=clean
        )
        self.assertFalse(third_report["changed"])
        self.assertEqual(third_report["reason"], "hire_window_closed")
        self.assertEqual(third, parent)

    def test_current_parent_hire_on_retry_retires_candidate_plan(self):
        adapter = FertHandCurrentABI()
        obs = observation()
        clean = route_tail(obs["step"])
        adapter.transform_selected(
            obs, {}, selected(), future_actions=clean
        )

        parent_hire = selected(market=[["HIRE"]])
        retry, report = adapter.transform_selected(
            obs, {}, parent_hire, future_actions=clean
        )
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "parent_hire_collision_retry")
        self.assertIs(retry, parent_hire)

        third_parent = selected(market=[["SELL", "MILK", 1]])
        third, third_report = adapter.transform_selected(
            obs, {}, third_parent, future_actions=clean
        )
        self.assertFalse(third_report["changed"])
        self.assertEqual(third_report["reason"], "hire_window_closed")
        self.assertEqual(third, third_parent)

    def test_malformed_retry_market_retires_without_throwing(self):
        adapter = FertHandCurrentABI()
        obs = observation()
        clean = route_tail(obs["step"])
        adapter.transform_selected(
            obs, {}, selected(), future_actions=clean
        )

        malformed = {"farmer": ["PASS"], "hands": [], "market": ["bad-row"]}
        result, report = adapter.transform_selected(
            obs, {}, malformed, future_actions=clean
        )
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "malformed_market_retry")
        self.assertIs(result, malformed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
