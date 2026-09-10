# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import unittest

import compare_panel


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def report(*, entry_sha: str, changed: set[tuple[str, int, int]] | None = None,
           deltas: dict[tuple[str, int, int], tuple[float, float]] | None = None):
    changed = changed or set()
    deltas = deltas or {}
    games = []
    for opponent, seed, seat in sorted(compare_panel.expected_grid()):
        rival_seat = 1 - seat
        scores = [0.0, 0.0]
        scores[seat] = 1_000.0
        scores[rival_seat] = 900.0
        own_delta, rival_delta = deltas.get((opponent, seed, seat), (0.0, 0.0))
        scores[seat] += own_delta
        scores[rival_seat] += rival_delta
        base_label = f"{opponent}/{seed}/{seat}"
        action_label = base_label + (
            "/candidate" if (opponent, seed, seat) in changed else "/control"
        )
        games.append(
            {
                "seed": seed,
                "candidate_seat": seat,
                "status": "complete",
                "scores": scores,
                "failure": None,
                "steps": 719,
                "episode_steps": 720,
                "daily_bank": [
                    {"step": 23, "bank": [24.0, 24.0]},
                    {"step": 718, "bank": scores},
                ],
                "trace_sha256": digest(action_label + "/trace"),
                "candidate_action_sha256": digest(action_label + "/action"),
                "candidate_action_count": 719,
                "opponent": opponent,
            }
        )
    opponents = {
        name: {
            "entry": f"{name}.py",
            "callable": "agent",
            "sha256": digest(name),
        }
        for name in compare_panel.EXPECTED_OPPONENTS
    }
    return {
        "schema_version": 1,
        "engine_ref": "engine-ref",
        "engine_sha256": {"kaggriculture.py": digest("engine")},
        "loader_sha256": digest("loader"),
        "evaluator_sha256": compare_panel.EXPECTED_EVALUATOR_PATCH_SHA256,
        "candidate": {
            "entry": "bound.py",
            "callable": "agent",
            "sha256": entry_sha,
        },
        "opponents": opponents,
        "seeds": list(compare_panel.EXPECTED_SEEDS),
        "agent_rng_seed": 20260909,
        "python": "3.11",
        "platform": "linux",
        "limits": {
            "action_rpc_seconds": 1.0,
            "startup_seconds": 15.0,
            "game_seconds_between_steps": 180.0,
            "remaining_overage_time": 0,
        },
        "method": "synthetic contract fixture",
        "progress": {
            "state": "complete",
            "planned_games": 32,
            "recorded_games": 32,
        },
        "games": games,
    }


class ComparePanelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.control_entry = digest("control-entry")
        self.candidate_entry = digest("candidate-entry")
        self.control = report(entry_sha=self.control_entry)
        key = ("arlene", 2609097301, 0)
        self.candidate = report(
            entry_sha=self.candidate_entry,
            changed={key},
            deltas={key: (10.0, 0.0)},
        )

    def test_positive_known_seed_factor_is_admitted(self) -> None:
        result = compare_panel.compare_reports(
            self.control,
            self.candidate,
            control_entry_sha256=self.control_entry,
            candidate_entry_sha256=self.candidate_entry,
            evaluator_sha256=compare_panel.EXPECTED_EVALUATOR_PATCH_SHA256,
        )
        self.assertEqual(result["verdict"], "ADMIT")
        self.assertEqual(
            result["overall"]["candidate_action_changed_cells"], 1
        )
        self.assertEqual(
            result["overall"]["known_seed_action_changed_cells"], 1
        )
        self.assertEqual(result["overall"]["negative_cells"], 0)
        self.assertEqual(result["overall"]["new_losses"], 0)
        self.assertGreater(result["overall"]["mean_own_delta"], 0)

    def test_negative_cell_and_lost_win_are_rejected(self) -> None:
        key = ("v1", 1834999074, 1)
        candidate = report(
            entry_sha=self.candidate_entry,
            changed={key},
            deltas={key: (-200.0, 0.0)},
        )
        result = compare_panel.compare_reports(
            self.control,
            candidate,
            control_entry_sha256=self.control_entry,
            candidate_entry_sha256=self.candidate_entry,
            evaluator_sha256=compare_panel.EXPECTED_EVALUATOR_PATCH_SHA256,
        )
        self.assertEqual(result["verdict"], "REJECT")
        self.assertEqual(result["overall"]["negative_cells"], 1)
        self.assertEqual(result["overall"]["new_losses"], 1)
        self.assertEqual(result["overall"]["lost_wins"], 1)
        self.assertFalse(result["gates"]["no_negative_own_cash_cells"])

    def test_action_and_whole_trace_activation_must_agree(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        key = ("arlene", 2609097301, 0)
        game = next(
            row
            for row in candidate["games"]
            if (row["opponent"], row["seed"], row["candidate_seat"]) == key
        )
        control_game = next(
            row
            for row in self.control["games"]
            if (row["opponent"], row["seed"], row["candidate_seat"]) == key
        )
        game["trace_sha256"] = control_game["trace_sha256"]
        with self.assertRaisesRegex(
            compare_panel.CompareError,
            "activation disagree",
        ):
            compare_panel.compare_reports(
                self.control,
                candidate,
                control_entry_sha256=self.control_entry,
                candidate_entry_sha256=self.candidate_entry,
                evaluator_sha256=(
                    compare_panel.EXPECTED_EVALUATOR_PATCH_SHA256
                ),
            )

    def test_incomplete_grid_fails_closed(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["games"].pop()
        candidate["progress"]["recorded_games"] = 31
        with self.assertRaisesRegex(
            compare_panel.CompareError,
            "did not complete exact grid",
        ):
            compare_panel.compare_reports(
                self.control,
                candidate,
                control_entry_sha256=self.control_entry,
                candidate_entry_sha256=self.candidate_entry,
                evaluator_sha256=(
                    compare_panel.EXPECTED_EVALUATOR_PATCH_SHA256
                ),
            )

    def test_entry_hash_is_bound(self) -> None:
        with self.assertRaisesRegex(
            compare_panel.CompareError,
            "entry hash mismatch",
        ):
            compare_panel.compare_reports(
                self.control,
                self.candidate,
                control_entry_sha256=digest("wrong"),
                candidate_entry_sha256=self.candidate_entry,
                evaluator_sha256=(
                    compare_panel.EXPECTED_EVALUATOR_PATCH_SHA256
                ),
            )


if __name__ == "__main__":
    unittest.main()
