# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import candidate_action_evidence as evidence
import materialize_evaluator


def synthetic_evaluator_source() -> bytes:
    return b'''import hashlib
import json

def encoded(value):
    return json.dumps(value, sort_keys=True).encode()

class State:
    def __init__(self):
        self.action = None

def probe(actions, candidate_seat, state, finalization_errors):
    actors, trace = [], hashlib.sha256()
    step = 0
    result = {"steps": 1}
    if True:
        for action in actions:
            trace.update(encoded(action))
        if True:
            for seat in range(2):
                state[seat].action = actions[seat]
        try:
            trace.update(b"done")
        except Exception:
            pass
        else:
            result["trace_sha256"] = trace.hexdigest()
        if finalization_errors:
            result["failed"] = True
    return result
'''


def game(opponent: str, seed: int, seat: int, whole: str, action: str) -> dict:
    return {
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "status": "complete",
        "steps": 719,
        "episode_steps": 720,
        "trace_sha256": whole,
        "candidate_action_sha256": action,
        "candidate_action_count": 719,
    }


def report(*, whole: str, action: str) -> dict:
    return {
        "schema_version": 1,
        "games": [
            game("arlene", 11, 0, whole, action),
            game("arlene", 11, 1, whole, action),
            game("v1", 11, 0, whole, action),
            game("v1", 11, 1, whole, action),
        ],
    }


def evaluator_fixture(root: Path) -> tuple[Path, Path, dict, str]:
    source = root / "evaluate.py"
    patched = root / "evaluate-candidate-actions.py"
    source_bytes = synthetic_evaluator_source()
    source.write_bytes(source_bytes)
    source_blob = materialize_evaluator.git_blob_sha1(source_bytes)
    receipt = materialize_evaluator.materialize_evaluator(
        source,
        patched,
        expected_blob=source_blob,
    )
    return source, patched, receipt, source_blob


class EvaluatorMaterializationTests(unittest.TestCase):
    def test_exact_patch_captures_candidate_action_before_interpreter(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, patched, receipt, _ = evaluator_fixture(root)
            self.assertTrue(source.is_file())
            rows = receipt["patched"]["patches"]
            self.assertEqual(len(rows), 3)
            self.assertEqual(
                [row["old_occurrences_retained_in_replacement"] for row in rows],
                [0, 1, 0],
            )
            self.assertEqual(
                [row["old_occurrences_after"] for row in rows],
                [0, 1, 0],
            )
            self.assertEqual(
                [row["unconsumed_old_occurrences_after"] for row in rows],
                [0, 0, 0],
            )
            self.assertEqual(
                receipt["patched"]["capture_phase"],
                "after both returned actions, before interpreter",
            )
            spec = importlib.util.spec_from_file_location("patched_eval_test", patched)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            actions = [{"farmer": ["PASS"]}, {"farmer": ["NORTH"]}]
            result = module.probe(
                actions,
                1,
                [module.State(), module.State()],
                [],
            )
            expected = hashlib.sha256(
                module.encoded({"step": 0, "action": actions[1]})
            ).hexdigest()
            self.assertEqual(result["candidate_action_sha256"], expected)
            self.assertEqual(result["candidate_action_count"], 1)

    def test_duplicate_patch_needle_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "evaluate.py"
            data = synthetic_evaluator_source() + materialize_evaluator.NEEDLES[0][0]
            source.write_bytes(data)
            with self.assertRaisesRegex(
                materialize_evaluator.EvaluatorMaterializeError,
                "cardinality mismatch",
            ):
                materialize_evaluator.materialize_evaluator(
                    source,
                    root / "patched.py",
                    expected_blob=materialize_evaluator.git_blob_sha1(data),
                )


class CandidateActionEvidenceTests(unittest.TestCase):
    def prepare(self, root: Path, control: dict, candidate: dict):
        source, patched, receipt, source_blob = evaluator_fixture(root)
        with mock.patch.object(evidence, "EXPECTED_EVALUATOR_BLOB", source_blob):
            return evidence.prepare_pair(
                control,
                candidate,
                receipt,
                source_evaluator=source,
                patched_evaluator=patched,
            )

    def test_real_materializer_receipt_is_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, patched, receipt, source_blob = evaluator_fixture(root)
            with mock.patch.object(evidence, "EXPECTED_EVALUATOR_BLOB", source_blob):
                binding = evidence.validate_evaluator_materialization(
                    receipt,
                    source_evaluator=source,
                    patched_evaluator=patched,
                )
            self.assertFalse(binding["whole_trace_is_activation"])

    def test_whole_trace_change_with_same_candidate_actions_normalizes_to_no_action_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control = report(whole="0" * 64, action="a" * 64)
            candidate = report(whole="9" * 64, action="a" * 64)
            normalized_control, normalized_candidate, custody = self.prepare(
                root, control, candidate
            )
            self.assertEqual(
                [game["trace_sha256"] for game in normalized_control["games"]],
                [game["trace_sha256"] for game in normalized_candidate["games"]],
            )
            self.assertTrue(all(custody["whole_trace_changed"].values()))
            self.assertFalse(custody["binding"]["whole_trace_is_activation"])
            self.assertEqual(control["games"][0]["trace_sha256"], "0" * 64)
            self.assertEqual(candidate["games"][0]["trace_sha256"], "9" * 64)

    def test_candidate_action_change_survives_normalization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control = report(whole="0" * 64, action="a" * 64)
            candidate = report(whole="0" * 64, action="b" * 64)
            normalized_control, normalized_candidate, custody = self.prepare(
                root, control, candidate
            )
            self.assertNotEqual(
                normalized_control["games"][0]["trace_sha256"],
                normalized_candidate["games"][0]["trace_sha256"],
            )
            self.assertFalse(any(custody["whole_trace_changed"].values()))

    def test_wrong_candidate_action_count_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control = report(whole="0" * 64, action="a" * 64)
            candidate = report(whole="1" * 64, action="b" * 64)
            candidate["games"][0]["candidate_action_count"] = 718
            with self.assertRaisesRegex(
                evidence.CandidateActionEvidenceError,
                "candidate action count/episode",
            ):
                self.prepare(root, control, candidate)

    def test_bool_seat_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control = report(whole="0" * 64, action="a" * 64)
            candidate = report(whole="1" * 64, action="b" * 64)
            candidate["games"][0]["candidate_seat"] = True
            with self.assertRaisesRegex(
                evidence.CandidateActionEvidenceError,
                "candidate_seat is invalid",
            ):
                self.prepare(root, control, candidate)

    def test_detached_evaluator_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, patched, receipt, source_blob = evaluator_fixture(root)
            bad = deepcopy(receipt)
            bad["patched"]["sha256"] = "0" * 64
            with mock.patch.object(evidence, "EXPECTED_EVALUATOR_BLOB", source_blob):
                with self.assertRaisesRegex(
                    evidence.CandidateActionEvidenceError,
                    "patched evaluator SHA-256 is detached",
                ):
                    evidence.validate_evaluator_materialization(
                        bad,
                        source_evaluator=source,
                        patched_evaluator=patched,
                    )

    def test_annotate_report_keeps_whole_trace_separate_from_activation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control = report(whole="0" * 64, action="a" * 64)
            candidate = report(whole="9" * 64, action="a" * 64)
            _, _, custody = self.prepare(root, control, candidate)
            comparison = {
                "schema_version": 1,
                "rows": [
                    {
                        "opponent": opponent,
                        "seed": 11,
                        "seat": seat,
                        "trace_changed": False,
                    }
                    for opponent in ("arlene", "v1")
                    for seat in (0, 1)
                ],
                "overall": {"changed_cells": 0},
            }
            annotated = evidence.annotate_report(comparison, custody)
            self.assertTrue(all(row["whole_trace_changed"] for row in annotated["rows"]))
            self.assertTrue(
                all(not row["candidate_action_changed"] for row in annotated["rows"])
            )
            self.assertEqual(
                annotated["overall"]["candidate_action_changed_cells"], 0
            )


if __name__ == "__main__":
    unittest.main()
