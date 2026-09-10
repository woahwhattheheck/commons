from __future__ import annotations

import copy
import json
import unittest

from rating_gate import GateError, classify_bytes, classify_document, loads_strict


def digest(ch: str) -> str:
    return ch * 64


def experiment() -> dict:
    return {
        "control_id": "control@deadbeef",
        "candidate_id": "candidate@cafebabe",
        "engine_sha256": digest("a"),
        "evaluator_sha256": digest("b"),
        "opponent_manifest_sha256": digest("c"),
        "grid_id": "grid-v1",
    }


def arm(
    own: int,
    rival: int,
    action: str,
    *,
    state: str = "complete",
    phase: str = "finalize",
    count: int = 719,
) -> dict:
    return {
        "state": state,
        "phase": phase,
        "own_score": own,
        "rival_score": rival,
        "tested_action_sha256": digest(action),
        "action_count": count,
    }


def pair(seed: int, control: dict, candidate: dict, *, opponent="arlene", seat=0):
    return {
        "opponent": opponent,
        "seed": seed,
        "seat": seat,
        "control": control,
        "candidate": candidate,
    }


def document(*pairs: dict) -> dict:
    return {
        "schema": "titan.rating-gate.input.v1",
        "experiment": experiment(),
        "pairs": list(pairs),
    }


class RatingGateTests(unittest.TestCase):
    def classify(self, doc: dict) -> dict:
        return classify_document(doc, input_sha256=digest("d"))

    def test_cash_gain_without_outcome_movement_is_polish_only(self):
        result = self.classify(
            document(pair(1, arm(100, 50, "1"), arm(110, 50, "2")))
        )
        self.assertEqual(result["verdict"], "POLISH_ONLY")
        self.assertEqual(result["transitions"], {"W->W": 1})
        self.assertEqual(
            result["totals"]["win_point_delta"],
            {"numerator": 0, "denominator": 1},
        )

    def test_cash_gain_cannot_mask_new_loss(self):
        result = self.classify(
            document(
                pair(1, arm(100, 50, "1"), arm(110, 200, "2"), seat=0),
                pair(2, arm(100, 50, "3"), arm(10000, 0, "4"), seat=1),
            )
        )
        self.assertEqual(result["verdict"], "REJECT")
        self.assertEqual(result["counts"]["new_losses"], 1)
        self.assertGreater(float(result["totals"]["own_delta_mean"]), 0)

    def test_valid_loss_to_win_is_rating_advance_screen(self):
        result = self.classify(
            document(pair(1, arm(0, 10, "1"), arm(11, 10, "2")))
        )
        self.assertEqual(result["verdict"], "RATING_ADVANCE_SCREEN")
        self.assertEqual(result["transitions"], {"L->W": 1})
        self.assertEqual(result["counts"]["negative_outcome_cells"], 0)

    def test_valid_tie_to_win_is_rating_advance_screen(self):
        result = self.classify(
            document(pair(1, arm(10, 10, "1"), arm(11, 10, "2")))
        )
        self.assertEqual(result["verdict"], "RATING_ADVANCE_SCREEN")
        self.assertEqual(
            result["totals"]["win_point_delta"],
            {"numerator": 1, "denominator": 2},
        )

    def test_action_identity_with_score_change_is_invalid(self):
        with self.assertRaisesRegex(GateError, "action identity"):
            self.classify(
                document(pair(1, arm(0, 10, "1"), arm(11, 10, "1")))
            )

    def test_one_good_flip_cannot_mask_adverse_stratum(self):
        result = self.classify(
            document(
                pair(
                    1,
                    arm(0, 10, "1"),
                    arm(11, 10, "2"),
                    opponent="a",
                    seat=0,
                ),
                pair(
                    2,
                    arm(10, 0, "3"),
                    arm(10, 10, "4"),
                    opponent="b",
                    seat=1,
                ),
                pair(
                    3,
                    arm(0, 10, "5"),
                    arm(11, 10, "6"),
                    opponent="a",
                    seat=1,
                ),
            )
        )
        self.assertEqual(result["verdict"], "REJECT")
        self.assertEqual(result["counts"]["lost_wins"], 1)
        self.assertEqual(result["counts"]["negative_winpoint_strata"], 1)

    def test_duplicate_cell_is_invalid(self):
        row = pair(1, arm(1, 0, "1"), arm(2, 0, "2"))
        with self.assertRaisesRegex(GateError, "duplicate paired cell"):
            self.classify(document(row, copy.deepcopy(row)))

    def test_incomplete_or_wrong_phase_is_invalid(self):
        with self.assertRaisesRegex(GateError, "phase must be 'finalize'"):
            self.classify(
                document(
                    pair(
                        1,
                        arm(1, 0, "1", phase="games"),
                        arm(2, 0, "2"),
                    )
                )
            )
        with self.assertRaisesRegex(GateError, "state must be 'complete'"):
            self.classify(
                document(
                    pair(
                        1,
                        arm(1, 0, "1"),
                        arm(2, 0, "2", state="running"),
                    )
                )
            )

    def test_exact_action_lifecycle_is_required(self):
        with self.assertRaisesRegex(GateError, "action_count must be 719"):
            self.classify(
                document(
                    pair(
                        1,
                        arm(1, 0, "1", count=718),
                        arm(2, 0, "2"),
                    )
                )
            )

    def test_identical_candidate_is_no_signal(self):
        result = self.classify(
            document(pair(1, arm(100, 50, "1"), arm(100, 50, "1")))
        )
        self.assertEqual(result["verdict"], "NO_SIGNAL")

    def test_action_active_mixed_cash_is_more_evidence(self):
        result = self.classify(
            document(
                pair(1, arm(100, 50, "1"), arm(110, 50, "2"), seat=0),
                pair(2, arm(100, 50, "3"), arm(95, 50, "4"), seat=1),
            )
        )
        self.assertEqual(result["verdict"], "MORE_EVIDENCE")
        self.assertEqual(result["transitions"], {"W->W": 2})

    def test_five_positive_flips_have_exact_one_sided_p_1_over_32(self):
        rows = []
        for index in range(5):
            rows.append(
                pair(
                    index,
                    arm(0, 1, "1"),
                    arm(2, 1, "2"),
                    opponent="a" if index < 3 else "b",
                    seat=index % 2,
                )
            )
        result = self.classify(document(*rows))
        self.assertEqual(result["verdict"], "RATING_ADVANCE_SCREEN")
        self.assertEqual(
            result["paired_sign_test"]["one_sided_p_exact"],
            {"numerator": 1, "denominator": 32},
        )
        self.assertEqual(result["evidence_strength"], "BROAD_PAIRED_SIGNAL")

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(GateError, "duplicate JSON key"):
            loads_strict(b'{"schema":"x","schema":"y"}')

    def test_equal_control_candidate_identity_rejected(self):
        doc = document(pair(1, arm(1, 0, "1"), arm(2, 0, "2")))
        doc["experiment"]["candidate_id"] = doc["experiment"]["control_id"]
        with self.assertRaisesRegex(GateError, "must differ"):
            self.classify(doc)

    def test_result_receipt_is_deterministic(self):
        doc = document(pair(1, arm(0, 10, "1"), arm(11, 10, "2")))
        raw = json.dumps(doc, sort_keys=True).encode()
        first = classify_bytes(raw)
        second = classify_bytes(raw)
        self.assertEqual(first, second)
        self.assertRegex(first["receipt_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
