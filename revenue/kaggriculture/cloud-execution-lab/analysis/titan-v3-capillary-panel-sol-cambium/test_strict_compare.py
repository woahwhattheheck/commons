# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

import compare
import strict_compare
from test_compare import (
    CANDIDATE_SHA,
    CONTROL_SHA,
    audit_fixture,
    evaluator_receipt_fixture,
    report_fixture,
)


def add_score(game, seat, delta):
    game["scores"][seat] += delta
    game["bank_snapshot"][seat] += delta


class OutcomeGateTests(unittest.TestCase):
    def setUp(self):
        self.audit = audit_fixture()
        self.receipt = evaluator_receipt_fixture()
        self.control = report_fixture(
            CONTROL_SHA, own_delta=0.0, changed=False
        )

    def inherited(self, candidate):
        return compare.classify(
            self.control, candidate, self.audit, self.receipt
        )

    def strict(self, candidate):
        return strict_compare.classify(
            self.control, candidate, self.audit, self.receipt
        )

    def test_positive_inherited_panel_remains_advance(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=5.0, changed=True
        )

        result = self.strict(candidate)

        self.assertTrue(result["advance"])
        self.assertEqual(result["metrics"]["new_losses"], 0)
        self.assertEqual(result["metrics"]["lost_wins"], 0)
        self.assertEqual(result["metrics"]["outcome_regressions"], 0)
        self.assertEqual(result["metrics"]["outcome_improvements"], 16)
        self.assertEqual(
            result["outcome_binding"]["transitions"], {"tie->win": 16}
        )

    def test_masked_new_loss_parent_advances_strict_rejects(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=10.0, changed=True
        )
        game = candidate["games"][0]
        # Replace this cell's +10 with -1. The cell's four-member stratum
        # still averages +7.25 own cash and margin; every inherited gate passes.
        add_score(game, game["candidate_seat"], -11.0)

        inherited = self.inherited(candidate)
        result = self.strict(candidate)

        self.assertTrue(inherited["advance"])
        self.assertTrue(
            inherited["criteria"][
                "all_opponent_seat_own_cash_strata_nonnegative"
            ]
        )
        self.assertTrue(
            inherited["criteria"][
                "all_opponent_seat_margin_strata_nonnegative"
            ]
        )
        self.assertEqual(result["metrics"]["new_losses"], 1)
        self.assertEqual(result["metrics"]["lost_wins"], 0)
        self.assertEqual(result["metrics"]["outcome_regressions"], 1)
        self.assertFalse(result["criteria"]["no_new_losses"])
        self.assertFalse(result["criteria"]["no_wtl_outcome_regressions"])
        self.assertFalse(result["advance"])

    def test_masked_lost_win_parent_advances_strict_rejects(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=10.0, changed=True
        )
        control_game = self.control["games"][0]
        candidate_game = candidate["games"][0]
        seat = control_game["candidate_seat"]
        # Control wins 110-100. Candidate ties 100-100. The remaining three
        # cells in this stratum are +10, so inherited own and margin means are
        # still +5 and the aggregate classifier advances.
        add_score(control_game, seat, 10.0)
        add_score(candidate_game, seat, -10.0)

        inherited = self.inherited(candidate)
        result = self.strict(candidate)

        self.assertTrue(inherited["advance"])
        self.assertTrue(
            inherited["criteria"][
                "all_opponent_seat_own_cash_strata_nonnegative"
            ]
        )
        self.assertTrue(
            inherited["criteria"][
                "all_opponent_seat_margin_strata_nonnegative"
            ]
        )
        self.assertEqual(result["metrics"]["new_losses"], 0)
        self.assertEqual(result["metrics"]["lost_wins"], 1)
        self.assertEqual(result["metrics"]["outcome_regressions"], 1)
        self.assertFalse(result["criteria"]["no_lost_wins"])
        self.assertFalse(result["criteria"]["no_wtl_outcome_regressions"])
        self.assertFalse(result["advance"])

    def test_gate_binds_all_executable_evidence_sources(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=5.0, changed=True
        )

        result = self.strict(candidate)

        for name in (
            "inherited_classifier_sha256",
            "outcome_classifier_sha256",
            "outcome_contracts_sha256",
            "outcome_workflow_sha256",
        ):
            self.assertRegex(result["identity"][name], r"^[0-9a-f]{64}$")
        self.assertEqual(
            result["outcome_binding"]["operation"], strict_compare.OPERATION
        )

    def test_input_reports_are_not_mutated(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=5.0, changed=True
        )
        before_control = copy.deepcopy(self.control)
        before_candidate = copy.deepcopy(candidate)

        self.strict(candidate)

        self.assertEqual(self.control, before_control)
        self.assertEqual(candidate, before_candidate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
