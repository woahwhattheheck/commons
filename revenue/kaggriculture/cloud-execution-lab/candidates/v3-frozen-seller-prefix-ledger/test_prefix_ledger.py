# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
import unittest

import prefix_ledger as p


def market(*rows):
    return list(rows)


class PrefixSalesTests(unittest.TestCase):
    def test_tail_sale_is_not_executable(self):
        rows = [[] for _ in range(10)] + [["SELL", "CARROT", 4]]
        self.assertEqual(p.executable_sales(rows, {"CARROT": 4}, 10), {})

    def test_active_duplicate_sales_share_one_stock_budget(self):
        rows = [["SELL", "CARROT", 3], ["SELL", "CARROT", 5]]
        self.assertEqual(p.executable_sales(rows, {"CARROT": 6}, 10), {"CARROT": 6})

    def test_nonpositive_and_malformed_rows_do_not_invent_fill(self):
        rows = [["SELL", "CARROT", 0], ["SELL", "CARROT", "x"], ["HIRE"]]
        self.assertEqual(p.executable_sales(rows, {"CARROT": 7}, 10), {})

    def test_official_numeric_string_quantity_is_matched(self):
        self.assertEqual(
            p.executable_sales([["SELL", "CARROT", "2"]], {"CARROT": 3}, 10),
            {"CARROT": 2},
        )

    def test_invalid_limit_fails_closed(self):
        with self.assertRaises(ValueError):
            p.executable_sales([], {}, 0)


class ReconcileTests(unittest.TestCase):
    def test_restores_preexisting_plan_erased_by_tail_phantom(self):
        rows = [[] for _ in range(10)] + [["SELL", "CARROT", 4]]
        planned, pending, report = p.reconcile_prefix_ledger(
            planned_before={"CARROT": [(11, 4)]},
            planned_after={},
            pending_after={"CARROT": 0},
            diagnostics={},
            shed={"CARROT": 4},
            market=rows,
            step=10,
            max_orders=10,
        )
        self.assertTrue(report["changed"])
        self.assertEqual(pending["CARROT"], 4)
        self.assertEqual(planned["CARROT"], [(11, 4)])
        self.assertEqual(report["changes"][0]["phantom_suffix_units"], 4)
        self.assertFalse(report["action_changed"])

    def test_uses_newly_chosen_plan_instead_of_stale_preplan(self):
        rows = [[] for _ in range(10)] + [["SELL", "CARROT", 2]]
        planned, _, report = p.reconcile_prefix_ledger(
            planned_before={"CARROT": [(12, 2)]},
            planned_after={},
            pending_after={"CARROT": 0},
            diagnostics={"chosen": {"item": "CARROT", "plan": [(10, 2), (14, 3)]}},
            shed={"CARROT": 5}, market=rows, step=10, max_orders=10,
        )
        self.assertEqual(planned["CARROT"], [(14, 3)])
        self.assertEqual(report["changes"][0]["plan_source"], "chosen")

    def test_preserves_post_transform_plan_when_present(self):
        rows = [[] for _ in range(10)] + [["SELL", "CARROT", 2]]
        planned, pending, _ = p.reconcile_prefix_ledger(
            planned_before={"CARROT": [(12, 5)]},
            planned_after={"CARROT": [(13, 3)]},
            pending_after={"CARROT": 0}, diagnostics={},
            shed={"CARROT": 5}, market=rows, step=10, max_orders=10,
        )
        self.assertEqual(planned["CARROT"], [(13, 3)])
        self.assertEqual(pending["CARROT"], 5)

    def test_no_change_when_tail_has_no_additional_fill(self):
        rows = [["SELL", "CARROT", 4]] + [[] for _ in range(9)] + [["SELL", "CARROT", 4]]
        planned, pending, report = p.reconcile_prefix_ledger(
            planned_before={"CARROT": [(11, 4)]}, planned_after={},
            pending_after={"CARROT": 0}, diagnostics={}, shed={"CARROT": 4},
            market=rows, step=10, max_orders=10,
        )
        self.assertFalse(report["changed"])
        self.assertEqual(planned, {})
        self.assertEqual(pending, {"CARROT": 0})

    def test_partial_active_fill_repairs_only_unsold_stock(self):
        rows = [["SELL", "CARROT", 2]] + [[] for _ in range(9)] + [["SELL", "CARROT", 9]]
        planned, pending, report = p.reconcile_prefix_ledger(
            planned_before={"CARROT": [(11, 9)]}, planned_after={},
            pending_after={"CARROT": 0}, diagnostics={}, shed={"CARROT": 9},
            market=rows, step=10, max_orders=10,
        )
        self.assertEqual(pending["CARROT"], 7)
        self.assertEqual(planned["CARROT"], [(11, 7)])
        self.assertEqual(report["changes"][0]["active_sold"], 2)

    def test_multiple_products_commit_atomically_in_pure_copies(self):
        rows = [[] for _ in range(10)] + [
            ["SELL", "CARROT", 2], ["SELL", "MILK", 3]
        ]
        before = {"CARROT": [(11, 2)], "MILK": [(12, 3)]}
        original = deepcopy(before)
        planned, pending, report = p.reconcile_prefix_ledger(
            planned_before=before, planned_after={},
            pending_after={"CARROT": 0, "MILK": 0}, diagnostics={},
            shed={"CARROT": 2, "MILK": 3}, market=rows, step=10, max_orders=10,
        )
        self.assertEqual(before, original)
        self.assertEqual(planned, original)
        self.assertEqual(pending, {"CARROT": 2, "MILK": 3})
        self.assertEqual(len(report["changes"]), 2)

    def test_malformed_owned_plan_rejects_whole_transaction(self):
        rows = [[] for _ in range(10)] + [["SELL", "CARROT", 2]]
        with self.assertRaises(ValueError):
            p.reconcile_prefix_ledger(
                planned_before={"CARROT": ["bad"]}, planned_after={},
                pending_after={"CARROT": 0}, diagnostics={}, shed={"CARROT": 2},
                market=rows, step=10, max_orders=10,
            )

    def test_observation_step_supports_day_hour(self):
        self.assertEqual(p.observation_step({"day": 2, "hour": 3}, {"turnsPerDay": 24}), 51)


class InstallTests(unittest.TestCase):
    class Consumer:
        def __init__(self):
            self.planned = {"CARROT": [(11, 4)]}
            self.pending = {}
            self.diagnostics = {}
            self.capture_post_units = False
            self.selected_post_units = None
            self.selected_post_units_binding = None

        def transform(self, observation, configuration, selected):
            self.planned = {}
            self.pending = {"CARROT": 0}
            self.selected_post_units = ({}, {"shed": {"CARROT": 4}})
            self.selected_post_units_binding = (
                int(observation["step"]), int(observation["player"]),
                deepcopy(selected["farmer"]), deepcopy(selected["hands"])
            )
            return deepcopy(selected)

    class Agent:
        def __init__(self):
            self.consumer = None
            self.diagnostics = {}

        def _initialize(self):
            self.consumer = InstallTests.Consumer()

    def test_install_is_idempotent_and_survives_reinitialize(self):
        agent = self.Agent()
        self.assertIs(p.install(agent), agent)
        self.assertIs(p.install(agent), agent)
        selected = {
            "farmer": ["PASS"], "hands": [],
            "market": [[] for _ in range(10)] + [["SELL", "CARROT", 4]],
        }
        for _ in range(2):
            agent._initialize()
            returned = agent.consumer.transform(
                {"step": 10, "player": 0}, {"maxMarketOrdersPerTurn": 10}, selected
            )
            self.assertEqual(returned, selected)
            self.assertEqual(agent.consumer.pending["CARROT"], 4)
            self.assertEqual(agent.consumer.planned["CARROT"], [(11, 4)])
        self.assertEqual(agent._prefix_ledger_state["repaired_turns"], 2)

    def test_no_tail_candidate_does_not_request_snapshot_capture(self):
        agent = self.Agent()
        p.install(agent)
        agent._initialize()
        selected = {"farmer": ["PASS"], "hands": [],
                    "market": [["SELL", "CARROT", 4]]}
        agent.consumer.transform({"step": 10, "player": 0},
                                 {"episodeSteps": 720, "maxMarketOrdersPerTurn": 10},
                                 selected)
        self.assertFalse(agent.consumer.capture_post_units)
        self.assertEqual(agent._prefix_ledger_state["last_report"]["reason"],
                         "no_owned_tail_plan_candidate")
        self.assertEqual(agent._prefix_ledger_state["repaired_turns"], 0)

    def test_terminal_state_is_left_canonical(self):
        agent = self.Agent()
        p.install(agent)
        agent._initialize()
        selected = {"farmer": ["PASS"], "hands": [],
                    "market": [[] for _ in range(10)] + [["SELL", "CARROT", 4]]}
        agent.consumer.transform({"step": 718, "player": 0},
                                 {"episodeSteps": 720, "maxMarketOrdersPerTurn": 10},
                                 selected)
        self.assertEqual(agent.consumer.pending["CARROT"], 0)
        self.assertEqual(agent.consumer.planned, {})
        self.assertEqual(agent._prefix_ledger_state["repaired_turns"], 0)
        self.assertEqual(agent._prefix_ledger_state["last_report"]["reason"],
                         "terminal_state_unchanged")

    def test_binding_mismatch_fails_closed_to_canonical_state(self):
        class MismatchConsumer(self.Consumer):
            def transform(inner, observation, configuration, selected):
                returned = super(MismatchConsumer, inner).transform(
                    observation, configuration, selected
                )
                inner.selected_post_units_binding = (99, 0, ["PASS"], [])
                return returned

        agent = self.Agent()
        p.install(agent)
        agent.consumer = MismatchConsumer()
        p._wrap_consumer(agent, agent._prefix_ledger_state)
        selected = {"farmer": ["PASS"], "hands": [],
                    "market": [[] for _ in range(10)] + [["SELL", "CARROT", 4]]}
        agent.consumer.transform({"step": 10, "player": 0},
                                 {"maxMarketOrdersPerTurn": 10}, selected)
        self.assertEqual(agent.consumer.pending["CARROT"], 0)
        self.assertEqual(agent.consumer.planned, {})
        self.assertEqual(agent._prefix_ledger_state["repaired_turns"], 0)


if __name__ == "__main__":
    unittest.main()
