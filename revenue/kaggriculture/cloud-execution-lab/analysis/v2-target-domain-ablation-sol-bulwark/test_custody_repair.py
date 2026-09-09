# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import bind_execution
import compare
import compare_bound
import materialize
import materialize_evaluator
import materialize_ordered


PREFIX = """PRODUCTS = ('MILK', 'EGG')\n\nclass Probe:\n    def __init__(self, pending):\n        self.pending = pending\n\n    def targets(self, shed, baseline_q):\n"""
SUFFIX = """        return targets\n\n_INSTANCE = Probe({})\ndef agent(obs, configuration=None):\n    return {'market': [], 'farmer': ['PASS'], 'hands': []}\n"""


def write_tree(root: Path, expression: str) -> Path:
    root.mkdir(parents=True)
    (root / "scheduler.py").write_text(PREFIX + expression + SUFFIX, encoding="utf-8")
    (root / "candidate.py").write_text(
        "from scheduler import agent\n", encoding="utf-8"
    )
    (root / "reference.txt").write_text("unchanged\n", encoding="utf-8")
    return root


def ordered_materialization(root: Path):
    source = write_tree(root / "v2", materialize.OLD)
    v1 = write_tree(root / "v1", materialize_ordered.V1_TARGET_EXPRESSION)
    source_blob = materialize.git_blob_sha1((source / "scheduler.py").read_bytes())
    v1_blob = materialize.git_blob_sha1((v1 / "scheduler.py").read_bytes())
    output = root / "ablation"
    with mock.patch.object(
        materialize_ordered, "EXPECTED_V1_SCHEDULER_BLOB", v1_blob
    ):
        receipt = materialize_ordered.materialize_ordered(
            source,
            output,
            v1 / "scheduler.py",
            expected_scheduler_blob=source_blob,
        )
    return source, output, v1, receipt


class OrderedMaterializationTests(unittest.TestCase):
    def test_policy_map_matches_v1_but_products_order_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, output, _v1, receipt = ordered_materialization(root)
            self.assertEqual(receipt["ablation"]["target_iteration_order"], "PRODUCTS")
            self.assertEqual(receipt["ablation"]["changed_files"], ["scheduler.py"])
            self.assertEqual(
                (source / "scheduler.py").read_text(encoding="utf-8").count(
                    materialize.OLD
                ),
                1,
            )
            spec = importlib.util.spec_from_file_location(
                "ordered_scheduler_test", output / "scheduler.py"
            )
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            targets = module.Probe({"EGG": 3}).targets(
                {"MILK": 7, "EGG": 5}, {"MILK": 2}
            )
            self.assertEqual(targets, {"MILK": 2, "EGG": 3})
            self.assertEqual(list(targets), ["MILK", "EGG"])

    def test_wrong_v1_blob_fails_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = write_tree(root / "v2", materialize.OLD)
            v1 = write_tree(root / "v1", materialize_ordered.V1_TARGET_EXPRESSION)
            source_blob = materialize.git_blob_sha1(
                (source / "scheduler.py").read_bytes()
            )
            with self.assertRaisesRegex(
                materialize_ordered.OrderedMaterializeError, "V1 scheduler blob"
            ):
                materialize_ordered.materialize_ordered(
                    source,
                    root / "out",
                    v1 / "scheduler.py",
                    expected_scheduler_blob=source_blob,
                )
            self.assertFalse((root / "out").exists())


class EvaluatorMaterializationTests(unittest.TestCase):
    def evaluator_source(self) -> bytes:
        return b'''import hashlib\nimport json\n\ndef encoded(value):\n    return json.dumps(value, sort_keys=True).encode()\n\nclass State:\n    def __init__(self):\n        self.action = None\n\ndef probe(actions, candidate_seat, state, finalization_errors):\n    actors, trace = [], hashlib.sha256()\n    step = 0\n    result = {"steps": 1}\n    if True:\n        candidate_trace.update(b"") if False else None\n        for action in actions:\n            trace.update(encoded(action))\n        if True:\n            for seat in range(2):\n                state[seat].action = actions[seat]\n        try:\n            trace.update(b"done")\n        except Exception:\n            pass\n        else:\n            result["trace_sha256"] = trace.hexdigest()\n        if finalization_errors:\n            result["failed"] = True\n    return result\n'''

    def test_exact_patch_emits_candidate_only_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "evaluate.py"
            output = root / "patched.py"
            data = self.evaluator_source()
            source.write_bytes(data)
            receipt = materialize_evaluator.materialize_evaluator(
                source,
                output,
                expected_blob=materialize.git_blob_sha1(data),
            )
            self.assertEqual(len(receipt["patched"]["patches"]), 3)
            spec = importlib.util.spec_from_file_location("patched_eval_test", output)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            actions = [{"farmer": ["PASS"]}, {"farmer": ["NORTH"]}]
            value = module.probe(actions, 1, [module.State(), module.State()], [])
            expected = hashlib.sha256(
                module.encoded({"step": 0, "action": actions[1]})
            ).hexdigest()
            self.assertEqual(value["candidate_action_sha256"], expected)
            self.assertEqual(value["candidate_action_count"], 1)

    def test_duplicate_patch_needle_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "evaluate.py"
            data = self.evaluator_source() + materialize_evaluator.NEEDLES[0][0]
            source.write_bytes(data)
            with self.assertRaisesRegex(
                materialize_evaluator.EvaluatorMaterializeError,
                "cardinality mismatch",
            ):
                materialize_evaluator.materialize_evaluator(
                    source,
                    root / "out.py",
                    expected_blob=materialize.git_blob_sha1(data),
                )


class BindingTests(unittest.TestCase):
    def test_wrappers_bind_distinct_payload_closures_and_detect_tamper(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, ablation, _v1, receipt = ordered_materialization(root)
            entry_sha = hashlib.sha256((source / "candidate.py").read_bytes()).hexdigest()
            receipt_path = root / "MATERIALIZATION.json"
            receipt_path.write_text(
                json.dumps(receipt, sort_keys=True), encoding="utf-8"
            )
            with mock.patch.object(
                bind_execution, "EXPECTED_ENTRY_SHA256", entry_sha
            ):
                bound = bind_execution.bind_execution(
                    source,
                    ablation,
                    receipt_path,
                    root / "arms",
                )
            self.assertNotEqual(
                bound["arms"]["control"]["wrapper_sha256"],
                bound["arms"]["ablation"]["wrapper_sha256"],
            )
            for arm in ("control", "ablation"):
                wrapper = root / "arms" / arm / "bound_entry.py"
                completed = subprocess.run(
                    [sys.executable, "-c", (
                        "import importlib.util;"
                        f"p={str(wrapper)!r};"
                        "s=importlib.util.spec_from_file_location('x',p);"
                        "m=importlib.util.module_from_spec(s);"
                        "s.loader.exec_module(m);"
                        "assert callable(m.agent)"
                    )],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
            tampered = root / "arms" / "ablation" / "payload" / "scheduler.py"
            tampered.write_text(tampered.read_text() + "\n# tamper\n")
            wrapper = root / "arms" / "ablation" / "bound_entry.py"
            completed = subprocess.run(
                [sys.executable, str(wrapper)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("closure mismatch", completed.stderr)


def game(opponent, seed, seat, own, rival, whole, candidate_action):
    scores = [own, rival] if seat == 0 else [rival, own]
    return {
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "status": "complete",
        "failure": None,
        "steps": 719,
        "episode_steps": 720,
        "scores": scores,
        "trace_sha256": whole,
        "candidate_action_sha256": candidate_action,
        "candidate_action_count": 719,
        "daily_bank": [
            {"step": 23, "bank": [10.0, 10.0]},
            {"step": 718, "bank": scores},
        ],
    }


def report(wrapper_sha, *, own_shift=0.0, whole="0" * 64, action="1" * 64):
    games = []
    for opponent in ("arlene", "v1"):
        for seat in (0, 1):
            games.append(
                game(
                    opponent,
                    7,
                    seat,
                    100.0 + own_shift,
                    90.0,
                    whole,
                    action,
                )
            )
    return {
        "schema_version": 1,
        "engine_ref": compare.ENGINE_REF,
        "engine_sha256": {"kaggriculture.py": "engine"},
        "loader_sha256": "loader",
        "evaluator_sha256": "e" * 64,
        "candidate": {
            "entry": "bound_entry.py",
            "callable": "agent",
            "sha256": wrapper_sha,
        },
        "opponents": {
            "arlene": {"entry": "arlene.py", "sha256": "a"},
            "v1": {"entry": "candidate.py", "sha256": "b"},
        },
        "seeds": [7],
        "agent_rng_seed": 20260909,
        "limits": {"action_rpc_seconds": 1.0},
        "method": "paired",
        "python": "3.11",
        "games": games,
    }


def evidence(root: Path):
    materialization = {
        "schema_version": 2,
        "repair": "sol-vector-execution-custody-and-order-v1",
        "source": {
            "scheduler_git_blob_sha1": compare.V2_SCHEDULER_BLOB,
            "scheduler_sha256": "3" * 64,
            "closure_sha256": "1" * 64,
        },
        "v1_reference": {
            "scheduler_git_blob_sha1": compare_bound.EXPECTED_V1_SCHEDULER_BLOB
        },
        "ablation": {
            "changed_files": ["scheduler.py"],
            "scheduler_git_blob_sha1": "f" * 40,
            "scheduler_sha256": "4" * 64,
            "closure_sha256": "2" * 64,
            "old_occurrences_before": 1,
            "old_occurrences_after": 0,
            "v1_expression_occurrences_after": 0,
            "ordered_policy_occurrences_after": 1,
            "target_iteration_order": "PRODUCTS",
        },
    }
    materialization_path = root / "MATERIALIZATION.json"
    materialization_path.write_text(
        json.dumps(materialization, sort_keys=True), encoding="utf-8"
    )
    binding = {
        "schema_version": 1,
        "repair": "sol-vector-bound-arm-entrypoints-v1",
        "materialization_receipt_sha256": hashlib.sha256(
            materialization_path.read_bytes()
        ).hexdigest(),
        "arms": {
            "control": {
                "payload_closure_sha256": "1" * 64,
                "scheduler_sha256": "3" * 64,
                "payload_entry_sha256": compare.V2_ENTRY_SHA256,
                "wrapper_sha256": "5" * 64,
                "wrapper_git_blob_sha1": "a" * 40,
                "wrapper": "control/bound_entry.py::agent",
            },
            "ablation": {
                "payload_closure_sha256": "2" * 64,
                "scheduler_sha256": "4" * 64,
                "payload_entry_sha256": compare.V2_ENTRY_SHA256,
                "wrapper_sha256": "6" * 64,
                "wrapper_git_blob_sha1": "b" * 40,
                "wrapper": "ablation/bound_entry.py::agent",
            },
        },
    }
    evaluator = {
        "schema_version": 1,
        "repair": "sol-vector-candidate-action-digest-v1",
        "source": {"git_blob_sha1": compare_bound.EXPECTED_EVALUATOR_BLOB},
        "patched": {
            "sha256": "e" * 64,
            "candidate_action_field": "candidate_action_sha256",
            "candidate_action_count_field": "candidate_action_count",
            "capture_phase": "after both returned actions, before interpreter",
            "patches": [
                {
                    "old_occurrences_before": 1,
                    "old_occurrences_after": 0,
                    "new_occurrences_after": 1,
                }
                for _ in range(3)
            ],
        },
    }
    return materialization_path, materialization, binding, evaluator


class BoundCompareTests(unittest.TestCase):
    def call(self, root, control, candidate):
        path, mat, binding, evaluator = evidence(root)
        return compare_bound.compare_bound(
            control,
            candidate,
            mat,
            binding,
            evaluator,
            materialization_path=path,
            git_head="c" * 40,
        )

    def test_candidate_action_change_with_own_cash_upside_advances(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self.call(
                root,
                report("5" * 64, action="1" * 64),
                report(
                    "6" * 64,
                    own_shift=5.0,
                    whole="9" * 64,
                    action="2" * 64,
                ),
            )
            self.assertEqual(value["verdict"], "UPSIDE_SCREEN")
            self.assertEqual(
                value["overall"]["candidate_action_changed_cells"], 4
            )

    def test_rival_or_bank_only_trace_change_is_not_candidate_activation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self.call(
                root,
                report("5" * 64, action="1" * 64),
                report(
                    "6" * 64,
                    own_shift=5.0,
                    whole="9" * 64,
                    action="1" * 64,
                ),
            )
            self.assertEqual(value["verdict"], "NO_ACTION_SIGNAL")
            self.assertEqual(
                value["overall"]["candidate_action_changed_cells"], 0
            )
            self.assertTrue(all(row["whole_trace_changed"] for row in value["rows"]))

    def test_swapped_report_wrapper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(
                compare_bound.BoundCompareError, "control report"
            ):
                self.call(
                    root,
                    report("6" * 64),
                    report("5" * 64, action="2" * 64),
                )

    def test_boolean_seat_and_short_episode_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control = report("5" * 64)
            candidate = report("6" * 64, action="2" * 64)
            control["games"][0]["candidate_seat"] = False
            with self.assertRaisesRegex(
                compare_bound.BoundCompareError, "seat is invalid"
            ):
                self.call(root, control, candidate)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control = report("5" * 64)
            candidate = report("6" * 64, action="2" * 64)
            candidate["games"][0]["episode_steps"] = 24
            candidate["games"][0]["steps"] = 23
            candidate["games"][0]["candidate_action_count"] = 23
            with self.assertRaisesRegex(
                compare_bound.BoundCompareError, "official episode"
            ):
                self.call(root, control, candidate)


if __name__ == "__main__":
    unittest.main()
