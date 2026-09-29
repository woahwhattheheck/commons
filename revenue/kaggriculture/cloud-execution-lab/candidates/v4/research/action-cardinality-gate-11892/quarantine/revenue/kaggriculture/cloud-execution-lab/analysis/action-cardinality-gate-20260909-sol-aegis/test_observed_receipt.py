from __future__ import annotations

import json
import unittest
from pathlib import Path

import action_cardinality_gate as gate


class ObservedReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = json.loads(
            (Path(__file__).with_name("OBSERVED-107140666.json")).read_text(
                encoding="utf-8"
            )
        )

    def test_receipt_seal(self) -> None:
        self.assertEqual(gate.verify_receipt(self.receipt), (True, "receipt hash verified"))

    def test_exact_submitted_replay_witness(self) -> None:
        receipt = self.receipt
        self.assertEqual(receipt["verdict"], "REJECT")
        self.assertEqual(receipt["input"]["raw_sha256"], "120f9a62911e897adb085d7397f1f3a67100bf8c241065e4e424adb540bdf916")
        analysis = receipt["analysis"]
        self.assertEqual(analysis["episode_id"], 107140666)
        self.assertEqual(analysis["seat"], 1)
        self.assertEqual(analysis["agent_name"], "Bryce Muhlnickel")
        self.assertEqual(analysis["transition_count"], 720)
        self.assertEqual(analysis["over_cardinality_transition_count"], 22)
        self.assertEqual(
            analysis["violation_ranges"],
            [
                {
                    "start_step": 123,
                    "end_step": 144,
                    "count": 22,
                    "observable_hands": 4,
                    "submitted_hand_rows": 5,
                    "start_day": 5,
                    "start_hour": 2,
                    "end_day": 5,
                    "end_hour": 23,
                }
            ],
        )

    def test_no_same_step_false_pass(self) -> None:
        analysis = self.receipt["analysis"]
        columns = analysis["violation_witness_columns"]
        first = dict(zip(columns, analysis["violation_witnesses"][0], strict=True))
        self.assertEqual(first["step"], 123)
        self.assertEqual(first["pre_observation_step"], 122)
        self.assertEqual(first["observable_hands"], 4)
        self.assertEqual(first["submitted_hand_rows"], 5)
        self.assertEqual(len(analysis["violation_witnesses"]), 22)


if __name__ == "__main__":
    unittest.main()
