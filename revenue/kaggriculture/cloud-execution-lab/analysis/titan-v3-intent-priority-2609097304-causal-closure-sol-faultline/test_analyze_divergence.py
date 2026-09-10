#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "faultline_analyze_divergence", HERE / "analyze_divergence.py"
)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def h(value: object) -> str:
    return hashlib.sha256(repr(value).encode()).hexdigest()


RUNTIME = {
    "opponent_sha256": h("arlene"),
    "opponent_entry": "arlene.py",
    "loader_sha256": h("loader"),
    "engine_sha256": {name: h(name) for name in m.ENGINE_FILES},
}
CONTROL_ENTRY = h("control entry")
CANDIDATE_ENTRY = h("candidate entry")
PATCHED_EVALUATOR = h("patched evaluator")


def pair_receipt() -> dict:
    return {
        "schema_version": 1,
        "operation": m.OPERATION,
        "git_head": "cafebabe",
        "archive": {"sha256": m.ARCHIVE_SHA256, "bytes": 428158},
        "source_manifest": {"sha256": m.SOURCE_SHA256, "runtime_files": 109},
        "factor": {"source_git_blob_sha1": m.FROZEN_SELECTED_GIT_BLOB},
        "arms": {
            "control": {
                "frozen_selected_sha256": h("control frozen"),
                "frozen_selected_git_blob_sha1": m.FROZEN_SELECTED_GIT_BLOB,
                "entry_sha256": CONTROL_ENTRY,
            },
            "candidate": {
                "frozen_selected_sha256": h("candidate frozen"),
                "frozen_selected_git_blob_sha1": "1" * 40,
                "entry_sha256": CANDIDATE_ENTRY,
            },
        },
        "only_runtime_delta": ["frozen_selected.py"],
    }


def evaluator_receipt() -> dict:
    return {
        "schema_version": 1,
        "operation": m.EVALUATOR_OPERATION,
        "source": {"git_blob_sha1": m.EVALUATOR_GIT_BLOB},
        "patched": {
            "sha256": PATCHED_EVALUATOR,
            "capture_phase": "after both returned actions, before official interpreter",
        },
    }


def action(market: list | None = None) -> dict:
    return {"farmer": ["PASS"], "hands": [], "market": market or []}


def debug(mode: str, step: int, seat: int, returned: list) -> dict:
    return {
        "schema_version": 1,
        "mode": mode,
        "step": step,
        "player": seat,
        "max_market_orders": 10,
        "money": 100,
        "shed": {"EGG": 1, "MILK": 1},
        "pending_before": ["MILK"],
        "pending_after": {"EGG": 0, "MILK": 0},
        "planned_before": {},
        "baseline_order": [],
        "control_order": ["EGG", "MILK"],
        "intent_order": ["MILK", "EGG"],
        "order_changed": True,
        "base_market": [],
        "returned_market": returned,
        "chosen": {"item": "EGG" if mode == "control" else "MILK"},
    }


def game(mode: str, seed: int, seat: int) -> dict:
    active = seed == 2609097304
    divergence = 5
    timeline = []
    current_world = h((seed, seat, "initial"))
    current_bank = [100.0, 100.0]
    for step in range(m.EXPECTED_STEPS):
        if active and step == divergence:
            market = (
                [["SELL", "EGG", 1], ["SELL", "MILK", 1]]
                if mode == "control"
                else [["SELL", "MILK", 1], ["SELL", "EGG", 1]]
            )
        else:
            market = []
        tested = action(market)
        rival = action()
        if active and mode == "candidate" and step >= divergence:
            next_world = h((seed, seat, "candidate", step + 1))
            if step == divergence:
                current_bank = [94.0, 133.0] if seat == 0 else [133.0, 94.0]
        else:
            next_world = h((seed, seat, "common", step + 1))
        timeline.append({
            "step": step,
            "pre_world_sha256": current_world,
            "tested_action": tested,
            "tested_action_sha256": m.sha256_value(tested),
            "rival_action": rival,
            "rival_action_sha256": m.sha256_value(rival),
            "debug": debug(mode, step, seat, market),
            "post_world_sha256": next_world,
            "bank": list(current_bank),
        })
        current_world = next_world
    scores = list(current_bank)
    trace = h((seed, seat, "candidate" if active and mode == "candidate" else "control"))
    return {
        "opponent": m.OPPONENT,
        "seed": seed,
        "candidate_seat": seat,
        "status": "complete",
        "scores": scores,
        "bank_snapshot": scores,
        "failure": None,
        "steps": m.EXPECTED_STEPS,
        "episode_steps": 720,
        "trace_sha256": trace,
        "candidate_timeline": timeline,
    }


def report(mode: str) -> dict:
    entry = CONTROL_ENTRY if mode == "control" else CANDIDATE_ENTRY
    return {
        "schema_version": 1,
        "evaluator_sha256": PATCHED_EVALUATOR,
        "loader_sha256": RUNTIME["loader_sha256"],
        "engine_sha256": RUNTIME["engine_sha256"],
        "candidate": {"entry": f"{mode}_entry.py", "callable": "agent", "sha256": entry},
        "opponents": {
            m.OPPONENT: {
                "entry": "arlene.py",
                "callable": "agent",
                "sha256": RUNTIME["opponent_sha256"],
            }
        },
        "seeds": list(m.SEEDS),
        "progress": {"state": "complete", "planned_games": 16, "recorded_games": 16},
        "reproducibility": {"checked": True, "same_trace_and_scores": True},
        "games": [game(mode, seed, seat) for seed in m.SEEDS for seat in (0, 1)],
    }


class CausalClosureContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.control = report("control")
        cls.candidate = report("candidate")

    def test_exact_two_cell_negative_pair_retires_factor(self):
        result = m.analyze(
            self.control,
            self.candidate,
            pair_receipt(),
            evaluator_receipt(),
            "cafebabe",
            RUNTIME,
        )
        self.assertEqual(result["verdict"]["disposition"], "RETIRE_FACTOR")
        self.assertEqual(result["grid"]["action_active_cells"], 2)
        self.assertEqual(result["aggregate"]["mean_own_cash_delta"], -0.75)
        self.assertEqual(result["aggregate"]["mean_rival_cash_delta"], 4.125)
        self.assertEqual(result["aggregate"]["mean_margin_delta"], -4.875)
        active = [row for row in result["cells"] if row["action_changed"]]
        self.assertEqual({row["candidate_seat"] for row in active}, {0, 1})
        self.assertTrue(all(row["classification"] == "executable_sell_order" for row in active))
        self.assertTrue(all(row["first_divergence_step"] == 5 for row in active))
        rendered = m.markdown(result)
        self.assertIn("RETIRE_FACTOR", rendered)
        self.assertIn("2609097304", rendered)

    def test_candidate_entry_identity_mismatch_fails_closed(self):
        broken = copy.deepcopy(self.candidate)
        broken["candidate"]["sha256"] = h("wrong")
        binding = m.validate_receipts(pair_receipt(), evaluator_receipt(), "cafebabe", RUNTIME)
        with self.assertRaisesRegex(m.EvidenceError, "candidate-entry mismatch"):
            m.index_report(broken, "candidate", binding)

    def test_timeline_length_and_untreated_world_drift_fail_closed(self):
        left = [{"tested_action": action(), "pre_world_sha256": "a", "rival_action": action(),
                 "post_world_sha256": "b", "bank": [1, 1]}]
        with self.assertRaisesRegex(m.EvidenceError, "timeline lengths differ"):
            m.first_difference(left, [], (m.OPPONENT, 1, 0))
        right = copy.deepcopy(left)
        right[0]["post_world_sha256"] = "c"
        with self.assertRaisesRegex(m.EvidenceError, "without a tested-action treatment"):
            m.first_difference(left, right, (m.OPPONENT, 1, 0))


if __name__ == "__main__":
    unittest.main()
