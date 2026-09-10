# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import verify_panel


class SupplementalPanelGateTests(unittest.TestCase):
    @staticmethod
    def _digest(label: str, key: tuple[str, int, int]) -> str:
        return hashlib.sha256(f"{label}:{key}".encode("utf-8")).hexdigest()

    @staticmethod
    def _outcome(scores: list[float], seat: int) -> str:
        margin = scores[seat] - scores[1 - seat]
        return "W" if margin > 0 else "L" if margin < 0 else "T"

    @classmethod
    def _set_delta(
        cls, row: dict, own_delta: float, margin_delta: float
    ) -> None:
        seat = row["candidate_seat"]
        baseline = [float(value) for value in row["baseline_scores"]]
        candidate = list(baseline)
        candidate[seat] += own_delta
        candidate[1 - seat] += own_delta - margin_delta
        row["candidate_scores"] = candidate
        row["own_delta"] = float(own_delta)
        row["margin_delta"] = float(margin_delta)
        row["baseline_outcome"] = cls._outcome(baseline, seat)
        row["candidate_outcome"] = cls._outcome(candidate, seat)

    @classmethod
    def _report(cls) -> dict:
        cells = []
        for opponent in verify_panel.EXPECTED_OPPONENTS:
            for seed in verify_panel.EXPECTED_SEEDS:
                for seat in verify_panel.EXPECTED_SEATS:
                    key = (opponent, seed, seat)
                    baseline_scores = [100.0, 90.0]
                    row = {
                        "opponent": opponent,
                        "seed": seed,
                        "candidate_seat": seat,
                        "baseline_scores": baseline_scores,
                        "candidate_scores": list(baseline_scores),
                        "baseline_candidate_action_sha256": cls._digest("base-action", key),
                        "candidate_candidate_action_sha256": cls._digest("candidate-action", key),
                        "candidate_action_changed": True,
                        "baseline_trace_sha256": cls._digest("base-trace", key),
                        "candidate_trace_sha256": cls._digest("candidate-trace", key),
                        "trace_changed": True,
                    }
                    cls._set_delta(row, 1.0, 1.0)
                    cells.append(row)
        return {
            "schema_version": 1,
            "status": "complete",
            "cells": cells,
            "verdict": {"decision": "ADVANCE", "checks": {"parent_gate": True}},
        }

    def test_clean_complete_grid_preserves_advance(self):
        report = self._report()
        gate = verify_panel.apply(report)
        self.assertEqual(gate["decision"], "PASS")
        self.assertEqual(report["verdict"]["decision"], "ADVANCE")
        self.assertTrue(all(gate["checks"].values()))
        self.assertEqual(len(gate["per_opponent_seat_mean_own_delta"]), 8)

    def test_action_identity_rejects_trace_only_contamination(self):
        report = self._report()
        row = report["cells"][0]
        row["candidate_candidate_action_sha256"] = row[
            "baseline_candidate_action_sha256"
        ]
        row["candidate_action_changed"] = False
        self._set_delta(row, 0.0, 0.0)
        gate = verify_panel.apply(report)
        self.assertEqual(report["verdict"]["decision"], "REJECT")
        self.assertFalse(
            gate["checks"]["action_identity_implies_trace_and_score_identity"]
        )
        self.assertEqual(len(gate["action_identity_violations"]), 1)

    def test_marginal_means_cannot_mask_opponent_seat_regression(self):
        report = self._report()
        for row in report["cells"]:
            if row["opponent"] == "arlene" and row["candidate_seat"] == 0:
                value = -1.0
            elif row["opponent"] == "arlene":
                value = 3.0
            else:
                value = 2.0
            self._set_delta(row, value, value)
        gate = verify_panel.apply(report)
        self.assertEqual(report["verdict"]["decision"], "REJECT")
        self.assertFalse(
            gate["checks"]["no_opponent_seat_mean_own_regression"]
        )
        self.assertGreater(
            gate["per_opponent_seat_mean_own_delta"]["arlene|seat=1"], 0.0
        )
        self.assertLess(
            gate["per_opponent_seat_mean_own_delta"]["arlene|seat=0"], 0.0
        )

    def test_positive_stratum_mean_cannot_hide_new_loss(self):
        report = self._report()
        target = None
        for row in report["cells"]:
            if row["opponent"] == "arlene" and row["candidate_seat"] == 0:
                if target is None:
                    target = row
                    self._set_delta(row, -11.0, -11.0)
                else:
                    self._set_delta(row, 4.0, 4.0)
        self.assertIsNotNone(target)
        gate = verify_panel.apply(report)
        self.assertTrue(
            gate["checks"]["no_opponent_seat_mean_own_regression"]
        )
        self.assertFalse(gate["checks"]["no_new_losses"])
        self.assertEqual(len(gate["new_losses"]), 1)
        self.assertEqual(report["verdict"]["decision"], "REJECT")

    def test_cell_arithmetic_is_rederived_from_scores(self):
        report = self._report()
        report["cells"][0]["own_delta"] = 999.0
        with self.assertRaisesRegex(ValueError, "own delta disagrees"):
            verify_panel.apply(report)

    def test_file_rewrite_is_deterministic_and_idempotent(self):
        report = self._report()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            panel = root / "PANEL.json"
            markdown = root / "PANEL.md"
            panel.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            markdown.write_text(
                "# Test panel\n\nVerdict: **ADVANCE**\n",
                encoding="utf-8",
            )
            first = verify_panel.verify_files(panel, markdown)
            first_panel = panel.read_bytes()
            first_markdown = markdown.read_bytes()
            second = verify_panel.verify_files(panel, markdown)
            self.assertEqual(first, second)
            self.assertEqual(first_panel, panel.read_bytes())
            self.assertEqual(first_markdown, markdown.read_bytes())
            self.assertEqual(first["decision"], "ADVANCE")


if __name__ == "__main__":
    unittest.main()
