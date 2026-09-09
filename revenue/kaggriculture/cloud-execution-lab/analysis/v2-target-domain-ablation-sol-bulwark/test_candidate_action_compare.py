# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import bind_execution
import candidate_action_compare
import execution_test_support as support
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


def build_fixture(root: Path) -> dict:
    fixture = support.make_fixture(root)
    source_evaluator = root / "canonical-evaluate.py"
    patched_evaluator = root / "candidate-action-evaluate.py"
    source_bytes = synthetic_evaluator_source()
    source_evaluator.write_bytes(source_bytes)
    source_blob = materialize_evaluator.git_blob_sha1(source_bytes)
    evaluator_receipt = materialize_evaluator.materialize_evaluator(
        source_evaluator,
        patched_evaluator,
        expected_blob=source_blob,
    )

    bound = root / "bound-action"
    binding = bind_execution.build_binding(
        control_root=fixture["control_root"],
        candidate_root=fixture["candidate_root"],
        materialization_receipt=fixture["receipt"],
        engine_dir=fixture["engine_dir"],
        loader=fixture["loader"],
        evaluator=patched_evaluator,
        opponents=fixture["opponents"],
        output_dir=bound,
        git_head=support.HEAD,
    )
    fixture.update(
        {
            "binding": binding,
            "output_dir": bound,
            "control_wrapper": bound / "control_bound.py",
            "candidate_wrapper": bound / "candidate_bound.py",
            "evaluator": patched_evaluator,
            "source_evaluator": source_evaluator,
            "source_evaluator_blob": source_blob,
            "evaluator_receipt": evaluator_receipt,
        }
    )
    return fixture


def with_actions(report: dict, action_sha256: str) -> dict:
    value = deepcopy(report)
    for game in value["games"]:
        game["candidate_action_sha256"] = action_sha256
        game["candidate_action_count"] = game["steps"]
    return value


class EvaluatorMaterializationTests(unittest.TestCase):
    def test_exact_patch_captures_candidate_before_interpreter(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "evaluate.py"
            output = root / "patched.py"
            data = synthetic_evaluator_source()
            source.write_bytes(data)
            receipt = materialize_evaluator.materialize_evaluator(
                source,
                output,
                expected_blob=materialize_evaluator.git_blob_sha1(data),
            )
            self.assertEqual(len(receipt["patched"]["patches"]), 3)
            self.assertEqual(
                receipt["patched"]["capture_phase"],
                "after both returned actions, before interpreter",
            )
            spec = importlib.util.spec_from_file_location("patched_eval_test", output)
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


class CandidateActionAdmissionTests(unittest.TestCase):
    def call(self, fixture: dict, control: dict, candidate: dict):
        kwargs = support.compare_kwargs(fixture)
        with mock.patch.object(
            candidate_action_compare,
            "EXPECTED_EVALUATOR_BLOB",
            fixture["source_evaluator_blob"],
        ):
            return candidate_action_compare.compare_action_bound(
                control,
                candidate,
                fixture["receipt"],
                fixture["binding"],
                fixture["evaluator_receipt"],
                source_evaluator=fixture["source_evaluator"],
                **kwargs,
            )

    def test_whole_trace_change_without_candidate_action_change_cannot_advance(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = build_fixture(Path(temporary))
            control = with_actions(
                support.report(fixture, "control", changed=False),
                "a" * 64,
            )
            candidate = with_actions(
                support.report(
                    fixture,
                    "candidate",
                    seat_deltas={0: 5.0, 1: 5.0},
                    changed=True,
                ),
                "a" * 64,
            )
            result = self.call(fixture, control, candidate)
            self.assertEqual(result["verdict"], "NO_ACTION_SIGNAL")
            self.assertEqual(
                result["overall"]["candidate_action_changed_cells"], 0
            )
            self.assertTrue(
                all(row["whole_trace_changed"] for row in result["rows"])
            )

    def test_candidate_action_change_with_broad_own_cash_upside_can_advance(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = build_fixture(Path(temporary))
            control = with_actions(
                support.report(fixture, "control", changed=False),
                "a" * 64,
            )
            candidate = with_actions(
                support.report(
                    fixture,
                    "candidate",
                    seat_deltas={0: 5.0, 1: 5.0},
                    changed=True,
                ),
                "b" * 64,
            )
            result = self.call(fixture, control, candidate)
            self.assertEqual(result["verdict"], "UPSIDE_SCREEN")
            self.assertEqual(
                result["overall"]["candidate_action_changed_cells"],
                len(candidate["games"]),
            )
            self.assertFalse(
                result["activation_binding"]["whole_trace_is_activation"]
            )

    def test_wrong_candidate_action_count_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = build_fixture(Path(temporary))
            control = with_actions(
                support.report(fixture, "control", changed=False),
                "a" * 64,
            )
            candidate = with_actions(
                support.report(fixture, "candidate", changed=True),
                "b" * 64,
            )
            candidate["games"][0]["candidate_action_count"] = 718
            with self.assertRaisesRegex(
                candidate_action_compare.CandidateActionCompareError,
                "candidate action count/episode",
            ):
                self.call(fixture, control, candidate)

    def test_detached_evaluator_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = build_fixture(Path(temporary))
            bad = deepcopy(fixture["evaluator_receipt"])
            bad["patched"]["sha256"] = "0" * 64
            with mock.patch.object(
                candidate_action_compare,
                "EXPECTED_EVALUATOR_BLOB",
                fixture["source_evaluator_blob"],
            ):
                with self.assertRaisesRegex(
                    candidate_action_compare.CandidateActionCompareError,
                    "patched evaluator SHA-256 is detached",
                ):
                    candidate_action_compare.validate_evaluator_materialization(
                        bad,
                        source_evaluator=fixture["source_evaluator"],
                        patched_evaluator=fixture["evaluator"],
                    )


if __name__ == "__main__":
    unittest.main()
