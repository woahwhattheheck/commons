# SPDX-License-Identifier: Apache-2.0
"""Synthetic fail-closed tests for the paired development gate."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import compare_panel as panel


def digest(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def report(entry: str, games: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "engine_ref": panel.ENGINE_REF,
        "engine_sha256": {"kaggriculture.py": digest("engine")},
        "loader_sha256": digest("loader"),
        "evaluator_sha256": digest("evaluator"),
        "candidate": {"entry": entry, "callable": "agent", "sha256": digest(entry)},
        "opponents": {
            "arlene": {
                "entry": "arlene.py",
                "callable": "agent",
                "sha256": digest("arlene"),
            }
        },
        "seeds": [7],
        "games": games,
    }


def game(*, seat: int, scores: tuple[int, int], trace: str) -> dict:
    return {
        "opponent": "arlene",
        "seed": 7,
        "candidate_seat": seat,
        "status": "complete",
        "failure": None,
        "scores": list(scores),
        "trace_sha256": digest(trace),
    }


class PairedGateTests(unittest.TestCase):
    def setUp(self):
        self.control_games = [
            game(seat=0, scores=(100, 90), trace="control-0"),
            game(seat=1, scores=(90, 100), trace="control-1"),
        ]
        self.control = report("control.py", self.control_games)
        self.candidate = report(
            "candidate.py", copy.deepcopy(self.control_games)
        )
        self.candidate["candidate"]["sha256"] = digest("candidate.py")

    def compare(self):
        real = panel.sha256_file

        def fake(path: Path) -> str:
            if path.name in ("control.py", "candidate.py"):
                return digest(path.name)
            if not path.exists():
                return digest(str(path))
            return real(path)

        with tempfile.TemporaryDirectory() as directory:
            lab = Path(directory)
            for name in (
                "main.py",
                "titan_runtime.py",
                "frozen_selected.py",
                "scheduler.py",
                "TITAN-CONFIG.json",
            ):
                (lab / name).write_text(name, encoding="utf-8")
            with (
                mock.patch.object(panel, "LAB", lab),
                mock.patch.object(panel, "sha256_file", side_effect=fake),
            ):
                return panel.compare(
                    self.control, self.candidate, expected_head="abc"
                )

    def test_no_signal_requires_complete_equal_cell_sets(self):
        result = self.compare()
        self.assertEqual(result["verdict"], "NO_SIGNAL")
        self.assertEqual(result["overall"]["changed_cells"], 0)
        self.assertEqual(result["cells"], 2)

    def test_uniform_positive_margin_advances(self):
        self.candidate["games"][0]["scores"] = [105, 90]
        self.candidate["games"][0]["trace_sha256"] = digest("candidate-0")
        self.candidate["games"][1]["scores"] = [90, 105]
        self.candidate["games"][1]["trace_sha256"] = digest("candidate-1")
        result = self.compare()
        self.assertEqual(result["verdict"], "ADVANCE")
        self.assertEqual(result["overall"]["negative_cells"], 0)
        self.assertEqual(result["overall"]["mean_margin_delta"], 5)

    def test_any_negative_cell_holds(self):
        self.candidate["games"][0]["scores"] = [99, 90]
        self.candidate["games"][0]["trace_sha256"] = digest("candidate-0")
        self.candidate["games"][1]["scores"] = [90, 110]
        self.candidate["games"][1]["trace_sha256"] = digest("candidate-1")
        result = self.compare()
        self.assertEqual(result["verdict"], "HOLD")
        self.assertEqual(result["overall"]["negative_cells"], 1)

    def test_missing_duplicate_failed_and_nonfinite_cells_fail_closed(self):
        variants = []

        missing = copy.deepcopy(self.candidate)
        missing["games"].pop()
        variants.append(missing)

        duplicate = copy.deepcopy(self.candidate)
        duplicate["games"].append(copy.deepcopy(duplicate["games"][0]))
        variants.append(duplicate)

        failed = copy.deepcopy(self.candidate)
        failed["games"][0]["status"] = "failed"
        failed["games"][0]["failure"] = {"kind": "timeout"}
        variants.append(failed)

        nonfinite = copy.deepcopy(self.candidate)
        nonfinite["games"][0]["scores"][0] = float("inf")
        variants.append(nonfinite)

        for candidate in variants:
            with self.subTest(candidate=candidate["games"]):
                self.candidate = candidate
                with self.assertRaises(panel.PanelError):
                    self.compare()

    def test_entrypoint_digest_and_provenance_drift_fail_closed(self):
        self.candidate["candidate"]["sha256"] = digest("wrong")
        with self.assertRaisesRegex(panel.PanelError, "entrypoint digest"):
            self.compare()

        self.candidate["candidate"]["sha256"] = digest("candidate.py")
        self.candidate["loader_sha256"] = digest("other-loader")
        with self.assertRaisesRegex(panel.PanelError, "drift"):
            self.compare()


if __name__ == "__main__":
    unittest.main()
