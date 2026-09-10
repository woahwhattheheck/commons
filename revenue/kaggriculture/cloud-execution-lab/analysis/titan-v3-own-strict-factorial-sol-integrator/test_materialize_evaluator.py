# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import materialize_evaluator as materializer


SOURCE = b'''import hashlib
import json

def encoded(value):
    return json.dumps(value, sort_keys=True).encode()

def play(candidate_seat=0):
    actors, trace = [], hashlib.sha256()
    result = {"steps": 1}
    actions = [{"x": 1}, {"x": 2}]
    state = [type("S", (), {})(), type("S", (), {})()]
    step = 0
    if True:
        if True:
            for seat in range(2):
                state[seat].action = actions[seat]
    finalization_errors = []
    if True:
        if False:
            pass
        else:
            result["trace_sha256"] = trace.hexdigest()
        if finalization_errors:
            result["status"] = "failed"
    return result
'''


class EvaluatorMaterializationTests(unittest.TestCase):
    def test_exact_source_gets_pre_interpreter_candidate_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "evaluate.py"
            output = root / "patched.py"
            source.write_bytes(SOURCE)
            receipt = materializer.materialize_evaluator(
                source,
                output,
                expected_blob=materializer.git_blob_sha1(SOURCE),
            )
            patched = output.read_bytes()
            self.assertIn(b"candidate_trace.update", patched)
            self.assertIn(b"candidate_action_sha256", patched)
            self.assertEqual(
                receipt["patched"]["capture_phase"],
                "after both returned actions, before interpreter",
            )
            namespace = {}
            exec(compile(patched, str(output), "exec"), namespace)
            result = namespace["play"]()
            self.assertEqual(result["candidate_action_count"], 1)
            self.assertEqual(len(result["candidate_action_sha256"]), 64)

    def test_source_blob_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "evaluate.py"
            source.write_bytes(SOURCE + b"# drift\n")
            with self.assertRaisesRegex(
                materializer.EvaluatorMaterializeError, "blob mismatch"
            ):
                materializer.materialize_evaluator(
                    source,
                    root / "patched.py",
                    expected_blob=materializer.git_blob_sha1(SOURCE),
                )

    def test_missing_patch_anchor_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "evaluate.py"
            broken = SOURCE.replace(b"    actors, trace = [], hashlib.sha256()\n", b"")
            source.write_bytes(broken)
            with self.assertRaisesRegex(
                materializer.EvaluatorMaterializeError, "cardinality mismatch"
            ):
                materializer.materialize_evaluator(
                    source,
                    root / "patched.py",
                    expected_blob=materializer.git_blob_sha1(broken),
                )

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "evaluate.py"
            output = root / "patched.py"
            source.write_bytes(SOURCE)
            output.write_text("sentinel", encoding="utf-8")
            with self.assertRaisesRegex(
                materializer.EvaluatorMaterializeError, "already exists"
            ):
                materializer.materialize_evaluator(
                    source,
                    output,
                    expected_blob=materializer.git_blob_sha1(SOURCE),
                )
            self.assertEqual(output.read_text(encoding="utf-8"), "sentinel")


if __name__ == "__main__":
    unittest.main()
