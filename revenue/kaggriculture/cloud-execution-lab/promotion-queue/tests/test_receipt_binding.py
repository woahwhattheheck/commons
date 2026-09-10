# SPDX-License-Identifier: Apache-2.0
"""Predecessor killers for outcome-to-submission receipt binding."""
from __future__ import annotations

import copy
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pq.executable_pins import ExecutablePinError, slot_input_name  # noqa: E402
from pq.receipt_binding import require_outcome_input_binding  # noqa: E402


def _record(digest: str) -> dict:
    return {"sha256": digest, "bytes": 1}


class ReceiptBindingTests(unittest.TestCase):
    def setUp(self):
        self.candidate_games = "1" * 64
        self.games = "2" * 64
        self.artifact = "3" * 64
        self.contract = "4" * 64
        self.evidence = "5" * 64
        self.config = {
            "slots": {
                "control": {
                    "name": "frozen-control",
                    "games": "/live/control.GAMES.jsonl",
                    "artifact_file": "/live/control.bin",
                }
            }
        }
        self.pin_manifest = {
            "inputs": {
                "candidate_games": _record(self.candidate_games),
                slot_input_name("control", "games"): _record(self.games),
                slot_input_name("control", "artifact_file"): _record(self.artifact),
            }
        }
        self.outcome = {
            "predecessor_identity": {
                "control": {
                    "name": "frozen-control",
                    "games_sha256": self.games,
                    "artifact_sha256": self.artifact,
                    "contract_sha256": self.contract,
                    "evidence_sha256": self.evidence,
                    "panel_id": "pq-example-vs-control",
                }
            },
            "comparisons": [
                {
                    "slot": "control",
                    "panel_id": "pq-example-vs-control",
                    "input_sha256": {
                        "baseline_games": self.games,
                        "candidate_games": self.candidate_games,
                        "contract": self.contract,
                        "evidence": self.evidence,
                    },
                }
            ],
        }

    def _require(self, outcome=None):
        require_outcome_input_binding(
            pin_manifest=self.pin_manifest,
            config=self.config,
            outcome=outcome or self.outcome,
        )

    def test_accepts_paired_outcome_bound_to_submitted_inputs(self):
        self._require()

    def test_accepts_dual_summary_without_redundant_input_map(self):
        outcome = copy.deepcopy(self.outcome)
        outcome["comparisons"][0].pop("input_sha256")
        outcome["comparisons"][0].pop("panel_id")
        self._require(outcome)

    def test_rejects_predecessor_games_digest_substitution(self):
        outcome = copy.deepcopy(self.outcome)
        outcome["predecessor_identity"]["control"]["games_sha256"] = "a" * 64
        with self.assertRaisesRegex(ExecutablePinError, "receipt games digest differs"):
            self._require(outcome)

    def test_rejects_predecessor_artifact_digest_substitution(self):
        outcome = copy.deepcopy(self.outcome)
        outcome["predecessor_identity"]["control"]["artifact_sha256"] = "b" * 64
        with self.assertRaisesRegex(ExecutablePinError, "receipt artifact digest differs"):
            self._require(outcome)

    def test_rejects_missing_predecessor_slot(self):
        outcome = copy.deepcopy(self.outcome)
        outcome["predecessor_identity"] = {}
        with self.assertRaisesRegex(ExecutablePinError, "predecessor slot set differs"):
            self._require(outcome)

    def test_rejects_duplicate_comparison_slot(self):
        outcome = copy.deepcopy(self.outcome)
        outcome["comparisons"].append(copy.deepcopy(outcome["comparisons"][0]))
        with self.assertRaisesRegex(ExecutablePinError, "duplicate slot"):
            self._require(outcome)

    def test_rejects_paired_candidate_digest_substitution(self):
        outcome = copy.deepcopy(self.outcome)
        outcome["comparisons"][0]["input_sha256"]["candidate_games"] = "c" * 64
        with self.assertRaisesRegex(ExecutablePinError, "candidate digest differs"):
            self._require(outcome)


if __name__ == "__main__":
    unittest.main()
