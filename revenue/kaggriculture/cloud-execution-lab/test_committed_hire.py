# SPDX-License-Identifier: Apache-2.0
import copy
import unittest

from committed_hire import CommittedHireReconciler, hire_cost


def obs(step=25, money=6, hands=0, hires_today=0):
    farm = {
        "money": money,
        "hands": [[4, 4] for _ in range(hands)],
        "hires_today": hires_today,
    }
    return {
        "step": step,
        "player": 0,
        "farms": [farm, {"money": 0, "hands": [], "hires_today": 0}],
    }


def action(*, hands=0, market=None, missing_nonpass=True):
    rows = [
        ["NORTH"] if (missing_nonpass or i < 3) else ["PASS"]
        for i in range(hands)
    ]
    return {
        "farmer": ["PASS"],
        "hands": rows,
        "market": copy.deepcopy(market or []),
    }


class CostTests(unittest.TestCase):
    def test_official_fibonacci_schedule(self):
        self.assertEqual([hire_cost(i) for i in range(7)], [1, 1, 2, 3, 5, 8, 13])

    def test_multiplier(self):
        self.assertEqual(hire_cost(3, 4), 12)


class ReconcilerTests(unittest.TestCase):
    CFG = {
        "turnsPerDay": 24,
        "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1,
    }

    def setUp(self):
        self.r = CommittedHireReconciler()

    def record_four(self):
        selected, report = self.r.transform(
            obs(),
            self.CFG,
            action(market=[["HIRE"]] * 4),
            route_id="R",
            commit=True,
        )
        self.assertEqual(selected["market"], [["HIRE"]] * 4)
        self.assertEqual(report["target_hands"], 4)

    def test_witness_records_four_requested_hands(self):
        self.record_four()
        self.assertEqual(self.r.intent.target_hands, 4)

    def test_three_observed_hands_and_two_dollars_reserve_paid_order(self):
        self.record_four()
        selected, report = self.r.transform(
            obs(26, money=2, hands=3, hires_today=3),
            self.CFG,
            action(
                hands=4,
                market=[["SELL", "CARROT", 2], ["BUY_SEED", "WHEAT", 1]],
            ),
            route_id="R",
            commit=True,
        )
        self.assertEqual(selected["market"][0], ["SELL", "CARROT", 2])
        self.assertEqual(selected["market"][1], ["SELL", "WHEAT", 0])
        self.assertEqual(report["reason"], "reserved_observed_cash")
        self.assertEqual(report["hire_cost"], 3)

    def test_three_dollars_inserts_before_paid_but_after_sales(self):
        self.record_four()
        selected, report = self.r.transform(
            obs(26, money=3, hands=3, hires_today=3),
            self.CFG,
            action(
                hands=4,
                market=[["SELL", "CARROT", 2], ["BUY_SEED", "WHEAT", 1]],
            ),
            route_id="R",
            commit=True,
        )
        self.assertEqual(
            selected["market"],
            [["SELL", "CARROT", 2], ["HIRE"], ["BUY_SEED", "WHEAT", 1]],
        )
        self.assertEqual(report["reason"], "inserted_missing_hire")
        self.assertEqual(report["target_hands"], 4)

    def test_existing_hire_is_not_duplicated(self):
        self.record_four()
        selected, report = self.r.transform(
            obs(26, money=3, hands=3, hires_today=3),
            self.CFG,
            action(hands=4, market=[["SELL", "CARROT", 1], ["HIRE"]]),
            route_id="R",
            commit=True,
        )
        self.assertEqual(sum(row == ["HIRE"] for row in selected["market"]), 1)
        self.assertEqual(report["reason"], "existing_hire_certified")

    def test_existing_hire_moves_before_paid(self):
        self.record_four()
        selected, report = self.r.transform(
            obs(26, money=3, hands=3, hires_today=3),
            self.CFG,
            action(hands=4, market=[["BUY_SEED", "WHEAT", 1], ["HIRE"]]),
            route_id="R",
            commit=True,
        )
        self.assertEqual(
            selected["market"], [["HIRE"], ["BUY_SEED", "WHEAT", 1]]
        )
        self.assertTrue(report["changed"])

    def test_full_queue_replaces_paid_not_sale(self):
        self.record_four()
        market = [["SELL", "CARROT", 1]] * 9 + [["BUY_SEED", "WHEAT", 1]]
        selected, report = self.r.transform(
            obs(26, money=3, hands=3, hires_today=3),
            self.CFG,
            action(hands=4, market=market),
            route_id="R",
            commit=True,
        )
        self.assertEqual(selected["market"][:9], market[:9])
        self.assertEqual(selected["market"][9], ["HIRE"])
        self.assertEqual(report["reason"], "replaced_paid_order_with_hire")

    def test_full_sale_queue_is_unchanged(self):
        self.record_four()
        market = [["SELL", "CARROT", 1]] * 10
        selected, report = self.r.transform(
            obs(26, money=3, hands=3, hires_today=3),
            self.CFG,
            action(hands=4, market=market),
            route_id="R",
            commit=True,
        )
        self.assertEqual(selected["market"], market)
        self.assertEqual(report["reason"], "full_sale_queue")

    def test_no_nonpass_phantom_command_does_not_spend(self):
        self.record_four()
        selected, report = self.r.transform(
            obs(26, money=3, hands=3, hires_today=3),
            self.CFG,
            action(
                hands=4,
                market=[["BUY_SEED", "WHEAT", 1]],
                missing_nonpass=False,
            ),
            route_id="R",
            commit=True,
        )
        self.assertEqual(selected["market"], [["BUY_SEED", "WHEAT", 1]])
        self.assertEqual(report["reason"], "no_nonpass_missing_command")

    def test_route_switch_clears_intent(self):
        self.record_four()
        selected, report = self.r.transform(
            obs(26, money=3, hands=3, hires_today=3),
            self.CFG,
            action(hands=4, market=[]),
            route_id="OTHER",
            commit=True,
        )
        self.assertEqual(selected["market"], [])
        self.assertFalse(report["pending"])
        self.assertEqual(report["reason"], "route_changed")

    def test_observed_target_clears_without_new_hire(self):
        self.record_four()
        selected, report = self.r.transform(
            obs(26, money=100, hands=4, hires_today=4),
            self.CFG,
            action(hands=4, market=[]),
            route_id="R",
            commit=True,
        )
        self.assertEqual(selected["market"], [])
        self.assertFalse(report["pending"])
        self.assertEqual(report["reason"], "target_observed")

    def test_new_hire_after_observed_target_binds_new_target(self):
        self.record_four()
        _, report = self.r.transform(
            obs(26, money=100, hands=4, hires_today=4),
            self.CFG,
            action(hands=4, market=[["HIRE"]]),
            route_id="R",
            commit=True,
        )
        self.assertTrue(report["pending"])
        self.assertEqual(report["target_hands"], 5)

    def test_pending_target_absorbs_new_producer_hires_without_double_counting_retry(self):
        self.record_four()
        _, report = self.r.transform(
            obs(26, money=100, hands=3, hires_today=3),
            self.CFG,
            action(hands=4, market=[["HIRE"], ["HIRE"]]),
            route_id="R",
            commit=True,
        )
        self.assertEqual(report["target_hands"], 5)

    def test_deadline_fallback_is_byte_exact_and_state_inert(self):
        self.record_four()
        before = copy.deepcopy(self.r.intent)
        selected_input = action(
            hands=4,
            market=[["BUY_SEED", "WHEAT", 1]],
        )
        selected, report = self.r.transform(
            obs(26, money=2, hands=3, hires_today=3),
            self.CFG,
            selected_input,
            route_id="R",
            commit=False,
        )
        self.assertEqual(selected, selected_input)
        self.assertEqual(self.r.intent, before)
        self.assertEqual(report["reason"], "uncommitted_fallback")

    def test_same_step_retry_does_not_infer_underfill(self):
        self.record_four()
        _, report = self.r.transform(
            obs(25, money=6, hands=0, hires_today=0),
            self.CFG,
            action(hands=0, market=[["HIRE"]] * 4),
            route_id="R",
            commit=True,
        )
        self.assertEqual(report["target_hands"], 4)
        self.assertEqual(report["actual_hands"], 0)

    def test_step_rewind_discards_old_intent(self):
        self.record_four()
        _, report = self.r.transform(
            obs(24, money=3, hands=3, hires_today=0),
            self.CFG,
            action(hands=4),
            route_id="R",
            commit=True,
        )
        self.assertFalse(report["pending"])
        self.assertEqual(report["reason"], "step_rewind")

    def test_intent_expires_after_one_day(self):
        self.record_four()
        _, report = self.r.transform(
            obs(50, money=3, hands=3, hires_today=0),
            self.CFG,
            action(hands=4),
            route_id="R",
            commit=True,
        )
        self.assertFalse(report["pending"])
        self.assertEqual(report["reason"], "expired")

    def test_gap_larger_than_one_does_not_hoard(self):
        _, _ = self.r.transform(
            obs(money=20),
            self.CFG,
            action(market=[["HIRE"]] * 5),
            route_id="R",
            commit=True,
        )
        selected, report = self.r.transform(
            obs(26, money=1, hands=4, hires_today=4),
            self.CFG,
            action(hands=5, market=[["BUY_SEED", "WHEAT", 1]]),
            route_id="R",
            commit=True,
        )
        self.assertEqual(selected["market"], [["BUY_SEED", "WHEAT", 1]])
        self.assertEqual(report["reason"], "cash_gap_too_large")

    def test_zero_multiplier_inserts_free_hire(self):
        cfg = dict(self.CFG, farmHandCostMult=0)
        self.record_four()
        selected, report = self.r.transform(
            obs(26, money=0, hands=3, hires_today=3),
            cfg,
            action(hands=4),
            route_id="R",
            commit=True,
        )
        self.assertEqual(selected["market"], [["HIRE"]])
        self.assertEqual(report["hire_cost"], 0)


if __name__ == "__main__":
    unittest.main()
