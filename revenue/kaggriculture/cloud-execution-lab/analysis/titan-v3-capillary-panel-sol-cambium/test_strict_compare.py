# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
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


def game_key(game):
    return (game["opponent"], game["seed"], game["candidate_seat"])


def indexed(report):
    return {game_key(game): game for game in report["games"]}


def make_action_changed(game, token):
    game["candidate_action_sha256"] = hashlib.sha256(
        f"action:{token}".encode()
    ).hexdigest()
    game["trace_sha256"] = hashlib.sha256(
        f"trace:{token}".encode()
    ).hexdigest()


def add_score(game, player, delta):
    game["scores"][player] += delta
    game["bank_snapshot"][player] += delta


class StrictClassifyTests(unittest.TestCase):
    def setUp(self):
        self.audit = audit_fixture()
        self.receipt = evaluator_receipt_fixture()
        self.control = report_fixture(CONTROL_SHA, delta=0.0, changed=False)

    def classify(self, candidate):
        return strict_compare.classify(
            self.control, candidate, self.audit, self.receipt
        )

    def test_valid_sparse_causal_upside_advances(self):
        candidate = report_fixture(CANDIDATE_SHA, delta=0.0, changed=False)
        game = candidate["games"][0]
        make_action_changed(game, "sparse-upside")
        add_score(game, game["candidate_seat"], 8.0)

        result = self.classify(candidate)

        self.assertTrue(result["advance"])
        self.assertEqual(result["metrics"]["action_changed_cells"], 1)
        self.assertEqual(result["metrics"]["score_changed_cells"], 1)
        self.assertEqual(result["metrics"]["new_losses"], 0)
        self.assertTrue(result["criteria"]["per_cell_causal_binding_valid"])
        self.assertRegex(
            result["identity"]["strict_classifier_sha256"], r"^[0-9a-f]{64}$"
        )
        self.assertRegex(
            result["identity"]["inherited_classifier_sha256"], r"^[0-9a-f]{64}$"
        )
        self.assertRegex(
            result["identity"]["strict_contracts_sha256"], r"^[0-9a-f]{64}$"
        )

    def test_cross_cell_activation_laundering_fails_closed(self):
        candidate = report_fixture(CANDIDATE_SHA, delta=0.0, changed=False)
        make_action_changed(candidate["games"][0], "harmless-activation")
        score_game = candidate["games"][1]
        add_score(score_game, score_game["candidate_seat"], 8.0)

        with self.assertRaisesRegex(
            compare.CompareError, "action-identical cell changed terminal scores"
        ):
            self.classify(candidate)

    def test_action_identity_with_trace_drift_fails_closed(self):
        candidate = report_fixture(CANDIDATE_SHA, delta=0.0, changed=False)
        candidate["games"][0]["trace_sha256"] = "f" * 64

        with self.assertRaisesRegex(
            compare.CompareError, "candidate-action/full-trace causal mismatch"
        ):
            self.classify(candidate)

    def test_action_change_without_trace_change_fails_closed(self):
        candidate = report_fixture(CANDIDATE_SHA, delta=0.0, changed=False)
        candidate["games"][0]["candidate_action_sha256"] = "e" * 64

        with self.assertRaisesRegex(
            compare.CompareError, "candidate-action/full-trace causal mismatch"
        ):
            self.classify(candidate)

    def test_own_cash_gain_that_helps_rival_more_rejects(self):
        candidate = report_fixture(CANDIDATE_SHA, delta=1.0, changed=True)
        for game in candidate["games"]:
            add_score(game, 1 - game["candidate_seat"], 900.0)

        result = self.classify(candidate)

        self.assertGreater(result["metrics"]["mean_own_cash_delta"], 0)
        self.assertLess(result["metrics"]["mean_margin_delta"], 0)
        self.assertFalse(result["criteria"]["global_mean_margin_nonnegative"])
        self.assertFalse(result["advance"])

    def test_negative_margin_stratum_rejects_despite_global_upside(self):
        candidate = report_fixture(CANDIDATE_SHA, delta=10.0, changed=True)
        control_by_key = indexed(self.control)
        candidate_by_key = indexed(candidate)
        for key, left in control_by_key.items():
            opponent, _seed, seat = key
            if opponent == "arlene" and seat == 0:
                # Keep both arms as wins so the margin-stratum gate is the
                # discriminating criterion rather than the new-loss gate.
                add_score(left, 1, -100.0)
                right = candidate_by_key[key]
                add_score(right, 1, -89.0)  # rival delta +11, own delta +10

        result = self.classify(candidate)

        self.assertGreater(result["metrics"]["mean_margin_delta"], 0)
        self.assertEqual(result["metrics"]["new_losses"], 0)
        self.assertFalse(
            result["criteria"][
                "all_opponent_seat_margin_strata_nonnegative"
            ]
        )
        self.assertFalse(result["advance"])

    def test_new_loss_rejects_even_when_all_mean_gates_pass(self):
        candidate = report_fixture(CANDIDATE_SHA, delta=10.0, changed=True)
        game = candidate["games"][0]
        seat = game["candidate_seat"]
        # Replace +10 with -1 for one cell. Fifteen +10 cells keep global and
        # four-cell stratum means positive, but a prior tie becomes a loss.
        add_score(game, seat, -11.0)

        result = self.classify(candidate)

        self.assertGreater(result["metrics"]["mean_own_cash_delta"], 0)
        self.assertGreaterEqual(result["metrics"]["mean_margin_delta"], 0)
        self.assertTrue(
            result["criteria"]["all_opponent_seat_strata_nonnegative"]
        )
        self.assertTrue(
            result["criteria"][
                "all_opponent_seat_margin_strata_nonnegative"
            ]
        )
        self.assertEqual(result["metrics"]["new_losses"], 1)
        self.assertFalse(result["criteria"]["no_new_losses"])
        self.assertFalse(result["advance"])

    def test_zero_activation_exact_identity_rejects_not_invalid(self):
        candidate = report_fixture(CANDIDATE_SHA, delta=0.0, changed=False)

        result = self.classify(candidate)

        self.assertFalse(result["advance"])
        self.assertFalse(result["criteria"]["candidate_actions_changed"])
        self.assertEqual(result["metrics"]["score_changed_cells"], 0)

    def test_input_reports_are_not_mutated(self):
        candidate = report_fixture(CANDIDATE_SHA, delta=0.0, changed=False)
        game = candidate["games"][0]
        make_action_changed(game, "nonmutation")
        add_score(game, game["candidate_seat"], 5.0)
        before_control = copy.deepcopy(self.control)
        before_candidate = copy.deepcopy(candidate)

        self.classify(candidate)

        self.assertEqual(self.control, before_control)
        self.assertEqual(candidate, before_candidate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
