# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import summarize_activation as audit


def game(seed: int, seat: int, own: float, rival: float, trace: str) -> dict:
    scores = [own, rival] if seat == 0 else [rival, own]
    return {
        "seed": seed,
        "candidate_seat": seat,
        "opponent": "arlene",
        "status": "complete",
        "failure": None,
        "scores": scores,
        "trace_sha256": trace,
        "steps": 719,
        "episode_steps": 720,
    }


def report(seed: int, rows: list[dict], candidate: str) -> dict:
    return {
        "schema_version": 1,
        "engine_ref": audit.ENGINE_REF,
        "engine_sha256": {"engine": "same"},
        "loader_sha256": "loader",
        "evaluator_sha256": "evaluator",
        "candidate": {"entry": candidate},
        "opponents": {"arlene": {"entry": "arlene.py"}},
        "seeds": [seed],
        "agent_rng_seed": 7,
        "limits": {"action_rpc_seconds": 1.0},
        "games": rows,
    }


class ActivationAuditTests(unittest.TestCase):
    def fixture(self, *, candidate_delta: float = 0.0, eligible: int = 0):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        results = root / "results"
        telemetry = root / "telemetry"
        results.mkdir()
        telemetry.mkdir()
        seed = 100
        zero = "0" * 64
        one = "1" * 64
        control_rows = [game(seed, seat, 20.0, 10.0, zero) for seat in (0, 1)]
        candidate_rows = [
            game(
                seed,
                seat,
                20.0 + candidate_delta,
                10.0,
                one if candidate_delta else zero,
            )
            for seat in (0, 1)
        ]
        (results / f"control-{seed}.json").write_text(
            json.dumps(report(seed, control_rows, "control.py")), encoding="utf-8"
        )
        (results / f"candidate-{seed}.json").write_text(
            json.dumps(report(seed, candidate_rows, "instrumented_candidate.py")),
            encoding="utf-8",
        )
        for seat in (0, 1):
            row = {
                "schema_version": 1,
                "seed": seed,
                "player": seat,
                "complete": True,
                "calls": 719,
                "last_step": 718,
                "episode_steps": 720,
                "certificate_calls": eligible,
                "eligible_certificates": eligible,
                "malformed_certificates": 0,
                "reason_counts": {"next_pre_market_growth_zero": eligible},
                "joint_producer_busy_true_steps": 0,
                "joint_producer_busy_false_steps": 719,
                "joint_producer_busy_other_steps": 0,
                "first_eligible": [],
            }
            (telemetry / f"telemetry-{seed}-{seat}.json").write_text(
                json.dumps(row), encoding="utf-8"
            )
        return temporary, results, telemetry, seed

    def test_unreached_requires_no_trace_change(self):
        temporary, results, telemetry, seed = self.fixture()
        with temporary:
            value = audit.compare(results, telemetry, [seed])
        self.assertEqual(value["verdict"], "UNREACHED")
        self.assertEqual(value["exit_code"], 4)

    def test_positive_changed_cells_advance(self):
        temporary, results, telemetry, seed = self.fixture(candidate_delta=5.0, eligible=1)
        with temporary:
            value = audit.compare(results, telemetry, [seed])
        self.assertEqual(value["verdict"], "ADVANCE")
        self.assertEqual(value["overall"]["changed_cells"], 2)

    def test_trace_change_without_eligibility_is_invalid(self):
        temporary, results, telemetry, seed = self.fixture(candidate_delta=5.0, eligible=0)
        with temporary:
            value = audit.compare(results, telemetry, [seed])
        self.assertEqual(value["verdict"], "INVALID")
        self.assertEqual(value["exit_code"], 2)


if __name__ == "__main__":
    unittest.main()
