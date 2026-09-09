# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import compare_bound as subject


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
WORKFLOW = (
    REPO
    / ".github"
    / "workflows"
    / "titan-v2-forced-feasibility-ablation-sol-keel.yml"
)


def action_game(opponent: str, seed: int, seat: int) -> dict:
    scores = [100.0, 90.0] if seat == 0 else [90.0, 100.0]
    return {
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "status": "complete",
        "failure": None,
        "steps": 719,
        "episode_steps": 720,
        "scores": scores,
        "trace_sha256": "1" * 64,
        "candidate_action_sha256": "2" * 64,
        "candidate_action_count": 719,
    }


def exact_games() -> list[dict]:
    return [
        action_game(opponent, seed, seat)
        for opponent in subject.EXPECTED_OPPONENTS
        for seed in subject.EXPECTED_SEEDS
        for seat in (0, 1)
    ]


class WorkflowWiringContracts(unittest.TestCase):
    def test_hosted_carrier_invokes_every_repair_and_bound_entry(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        required = (
            '"$CASE/materialize_evaluator.py"',
            '"$CASE/bind_execution.py"',
            '"$CASE/compare_bound.py"',
            '"$OUT/bound/control/bound_entry.py::agent"',
            '"$OUT/bound/ablation/bound_entry.py::agent"',
            '--binding-receipt "$OUT/EXECUTION-BINDING.json"',
            '--evaluator-receipt "$OUT/EVALUATOR-MATERIALIZATION.json"',
            '--bound-root "$OUT/bound"',
            '--source-root "$LAB/runtime/variants/v2"',
            '--ablation-root "$OUT/candidate"',
        )
        for needle in required:
            with self.subTest(needle=needle):
                self.assertIn(needle, workflow)
        forbidden = (
            '--candidate "$LAB/runtime/variants/v2/candidate.py::agent"',
            '--candidate "$OUT/candidate/candidate.py::agent"',
            'python -B "$KAG/cloud-eval/evaluate.py"',
        )
        for needle in forbidden:
            with self.subTest(forbidden=needle):
                self.assertNotIn(needle, workflow)

    def test_new_carrier_modules_are_compiled_and_hash_pinned(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for filename in (
            "bind_execution.py",
            "materialize_evaluator.py",
            "compare_bound.py",
            "test_carrier_wiring.py",
        ):
            with self.subTest(filename=filename):
                self.assertIn(f'git hash-object "$CASE/{filename}"', workflow)
                self.assertIn(filename, workflow.split("py_compile", 1)[1])


class ExactGridContracts(unittest.TestCase):
    def test_exact_four_seed_two_opponent_two_seat_grid_passes(self):
        subject.validate_game_grid({"games": exact_games()}, "probe")

    def test_truncated_grid_fails_closed(self):
        games = exact_games()
        games.pop()
        with self.assertRaisesRegex(subject.BoundCompareError, "exact grid"):
            subject.validate_game_grid({"games": games}, "probe")

    def test_boolean_seat_fails_closed(self):
        games = exact_games()
        games[0]["candidate_seat"] = False
        with self.assertRaisesRegex(subject.BoundCompareError, "not an integer"):
            subject.validate_game_grid({"games": games}, "probe")


class OpponentSeatGateContracts(unittest.TestCase):
    @staticmethod
    def result(seat_one_delta: float) -> dict:
        rows = []
        for opponent in subject.EXPECTED_OPPONENTS:
            for seed in subject.EXPECTED_SEEDS:
                rows.append(
                    {
                        "opponent": opponent,
                        "seed": seed,
                        "seat": 0,
                        "own_delta": 10.0,
                    }
                )
                rows.append(
                    {
                        "opponent": opponent,
                        "seed": seed,
                        "seat": 1,
                        "own_delta": seat_one_delta,
                    }
                )
        return {
            "verdict": "UPSIDE_SCREEN",
            "reason": "aggregate pass",
            "exit_code": 0,
            "rows": rows,
        }

    def test_aggregate_upside_cannot_hide_one_seat_regression(self):
        result = self.result(-1.0)
        subject.apply_opponent_seat_gate(result)
        self.assertEqual(result["verdict"], "SEAT_STRATUM_REGRESSION")
        self.assertEqual(result["exit_code"], 1)
        self.assertIn("arlene/seat-1", result["reason"])
        self.assertIn("v1/seat-1", result["reason"])

    def test_nonnegative_means_preserve_upside(self):
        result = self.result(0.0)
        subject.apply_opponent_seat_gate(result)
        self.assertEqual(result["verdict"], "UPSIDE_SCREEN")
        self.assertEqual(result["exit_code"], 0)


class EvaluatorCustodyContracts(unittest.TestCase):
    def receipt(self, source: bytes, patched: bytes) -> dict:
        patches = [
            {
                "old_occurrences_before": 1,
                "old_occurrences_after": 0,
                "new_occurrences_after": 1,
            }
            for _ in range(3)
        ]
        return {
            "schema_version": 1,
            "operation": subject.OPERATION,
            "repair": subject.EXPECTED_EVALUATOR_REPAIR,
            "source": {
                "git_blob_sha1": subject.git_blob_sha1(source),
                "sha256": hashlib.sha256(source).hexdigest(),
                "bytes": len(source),
            },
            "patched": {
                "git_blob_sha1": subject.git_blob_sha1(patched),
                "sha256": hashlib.sha256(patched).hexdigest(),
                "bytes": len(patched),
                "candidate_action_field": "candidate_action_sha256",
                "candidate_action_count_field": "candidate_action_count",
                "capture_phase": "after both returned actions, before interpreter",
                "patches": patches,
            },
        }

    def test_post_materialization_evaluator_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source.py"
            patched_path = root / "patched.py"
            source = b"print('source')\n"
            patched = b"print('patched')\n"
            source_path.write_bytes(source)
            patched_path.write_bytes(patched)
            receipt = self.receipt(source, patched)
            with mock.patch.object(
                subject,
                "EXPECTED_EVALUATOR_BLOB",
                subject.git_blob_sha1(source),
            ):
                subject.validate_evaluator(
                    receipt,
                    source_path=source_path,
                    patched_path=patched_path,
                )
                patched_path.write_bytes(patched + b"# drift\n")
                with self.assertRaisesRegex(
                    subject.BoundCompareError, "patched evaluator"
                ):
                    subject.validate_evaluator(
                        receipt,
                        source_path=source_path,
                        patched_path=patched_path,
                    )


class PostGameClosureContracts(unittest.TestCase):
    @staticmethod
    def write_payload(root: Path, scheduler: bytes) -> None:
        root.mkdir(parents=True)
        (root / "candidate.py").write_bytes(b"from scheduler import agent\n")
        (root / "scheduler.py").write_bytes(scheduler)

    def test_bound_payload_tamper_after_play_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            ablation = root / "ablation"
            bound = root / "bound"
            self.write_payload(source, b"def agent(*args): return {}\n")
            self.write_payload(ablation, b"def agent(*args): return {'x': 1}\n")
            source_inventory = subject.inventory(source)
            ablation_inventory = subject.inventory(ablation)
            expected = {
                "source_closure": subject.closure_sha256(source_inventory),
                "ablation_closure": subject.closure_sha256(ablation_inventory),
                "source_scheduler": source_inventory["scheduler.py"]["sha256"],
                "ablation_scheduler": ablation_inventory["scheduler.py"]["sha256"],
            }
            materialization_path = root / "MATERIALIZATION.json"
            materialization_path.write_text("{}\n", encoding="utf-8")
            arms = {}
            for arm, payload_source, inventory in (
                ("control", source, source_inventory),
                ("ablation", ablation, ablation_inventory),
            ):
                arm_root = bound / arm
                shutil.copytree(payload_source, arm_root / "payload")
                wrapper = (
                    f"# {arm}\nfrom payload.candidate import agent\n".encode()
                )
                (arm_root / "bound_entry.py").write_bytes(wrapper)
                arms[arm] = {
                    "payload_closure_sha256": subject.closure_sha256(inventory),
                    "scheduler_sha256": inventory["scheduler.py"]["sha256"],
                    "payload_entry_sha256": inventory["candidate.py"]["sha256"],
                    "wrapper_sha256": hashlib.sha256(wrapper).hexdigest(),
                    "wrapper_git_blob_sha1": subject.git_blob_sha1(wrapper),
                    "wrapper": f"{arm}/bound_entry.py::agent",
                }
            binding = {
                "schema_version": 1,
                "operation": subject.OPERATION,
                "repair": subject.EXPECTED_BINDING_REPAIR,
                "materialization_receipt_sha256": hashlib.sha256(
                    materialization_path.read_bytes()
                ).hexdigest(),
                "arms": arms,
            }
            entry_sha = source_inventory["candidate.py"]["sha256"]
            with (
                mock.patch.object(subject, "EXPECTED_ENTRY_SHA256", entry_sha),
                mock.patch.object(
                    subject,
                    "validate_materialization",
                    return_value=expected,
                ),
            ):
                subject.validate_binding(
                    binding,
                    {},
                    materialization_path=materialization_path,
                    bound_root=bound,
                    source_root=source,
                    ablation_root=ablation,
                )
                target = bound / "ablation" / "payload" / "scheduler.py"
                target.write_bytes(target.read_bytes() + b"# post-game drift\n")
                with self.assertRaisesRegex(
                    subject.BoundCompareError, "inventory drifted"
                ):
                    subject.validate_binding(
                        binding,
                        {},
                        materialization_path=materialization_path,
                        bound_root=bound,
                        source_root=source,
                        ablation_root=ablation,
                    )


if __name__ == "__main__":
    unittest.main()
