# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from compare_panel import PanelError, classify


def report(entry_sha, deltas=(0, 0), *, trace_prefix="a", complete=True):
    games = []
    for seat in (0, 1):
        base = 100 + seat
        own = base + deltas[seat]
        scores = [own, 90] if seat == 0 else [90, own]
        games.append(
            {
                "opponent": "arlene",
                "seed": 7,
                "candidate_seat": seat,
                "status": "complete" if complete else "failed",
                "scores": scores if complete else None,
                "trace_sha256": (trace_prefix + str(seat)).ljust(64, "0"),
                "failure": None if complete else {"seat": seat},
            }
        )
    return {
        "engine_ref": "engine",
        "engine_sha256": {"x": "1"},
        "loader_sha256": "loader",
        "evaluator_sha256": "eval",
        "seeds": [7],
        "agent_rng_seed": 9,
        "limits": {"action": 1},
        "opponents": {"arlene": {"sha256": "rival"}},
        "candidate": {"sha256": entry_sha},
        "games": games,
    }


class ComparePanelTests(unittest.TestCase):
    def write(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def event(self, directory, changed=True):
        directory.mkdir()
        (directory / "worker-1.jsonl").write_text(
            json.dumps(
                {
                    "schema": "titan-day10-fertilizer-liquidity-event/v1",
                    "step": 240,
                    "player": 0,
                    "changed": changed,
                    "reason": "certified_fertilizer_liquidity_sale" if changed else "declined",
                    "quantity": 4,
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def classify(self, control, candidate, changed=True):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.write(root / "control.json", control)
        self.write(root / "candidate.json", candidate)
        self.event(root / "events", changed=changed)
        return classify(root / "control.json", root / "candidate.json", root / "events")

    def test_positive_both_seats_advances(self):
        result = self.classify(report("c", trace_prefix="a"), report("n", (10, 5), trace_prefix="b"))
        self.assertEqual(result["verdict"], "ADVANCE")
        self.assertEqual(result["trace_changed_cells"], 2)

    def test_negative_seat_stratum_regresses(self):
        result = self.classify(report("c", trace_prefix="a"), report("n", (10, -1), trace_prefix="b"))
        self.assertEqual(result["verdict"], "REGRESSION")

    def test_no_changed_event_is_no_action_signal(self):
        result = self.classify(report("c", trace_prefix="a"), report("n", (10, 10), trace_prefix="b"), changed=False)
        self.assertEqual(result["verdict"], "NO_ACTION_SIGNAL")

    def test_entry_alias_is_rejected(self):
        with self.assertRaisesRegex(PanelError, "control_candidate_entry_alias"):
            self.classify(report("same"), report("same", (1, 1), trace_prefix="b"))

    def test_incomplete_game_is_rejected(self):
        with self.assertRaisesRegex(PanelError, "incomplete_game"):
            self.classify(report("c"), report("n", complete=False))

    def test_identity_drift_is_rejected(self):
        candidate = report("n", (1, 1), trace_prefix="b")
        candidate["engine_ref"] = "other"
        with self.assertRaisesRegex(PanelError, "execution_identity_mismatch"):
            self.classify(report("c"), candidate)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "control.json").write_text('{"engine_ref":"a","engine_ref":"b"}', encoding="utf-8")
            self.write(root / "candidate.json", report("n"))
            (root / "events").mkdir()
            with self.assertRaisesRegex(PanelError, "duplicate_json_key"):
                classify(root / "control.json", root / "candidate.json", root / "events")


if __name__ == "__main__":
    unittest.main()
