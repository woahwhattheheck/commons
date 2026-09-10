#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "faultline_materialize_evaluator", HERE / "materialize_evaluator.py"
)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def source_fixture() -> bytes:
    return b'''import hashlib
import json
import sys
import time

def usage():
    return {}

def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def worker(function, obs, cfg, takes_config, send):
    if True:
        if True:
            try:
                action = function(obs, cfg) if takes_config else function(obs)
                seconds, cpu_seconds = time.perf_counter() - start, time.process_time() - cpu
                send({"kind": "action", "action": action, "call_seconds": seconds,
                      "call_cpu_seconds": cpu_seconds, **usage()})
            except Exception:
                raise

def play(engine, actors, env, cfg, seed, candidate_seat):
    result = {"seed": seed, "candidate_seat": candidate_seat, "status": "failed", "scores": None,
              "failure": None, "steps": 0, "episode_steps": cfg.episodeSteps, "daily_bank": []}
    try:
        for step in range(cfg.episodeSteps):
            actions = []
            for seat, actor in enumerate(actors):
                response = actor.exchange(state[seat].observation, cfg)
                actions.append(response["action"])
            for seat in range(2):
                state[seat].action = actions[seat]
            engine.interpreter(state, env)
            result["steps"] += 1
            bank = [float(state[0].observation.farms[i]["money"]) for i in range(2)]
    except Exception:
        raise
    return result
'''


class EvaluatorInstrumentationContracts(unittest.TestCase):
    def test_patch_is_exact_observability_only_and_compiles(self):
        original = source_fixture()
        with mock.patch.object(m, "EXPECTED_GIT_BLOB", m.git_blob_sha1(original)):
            patched, receipt = m.patch_source(original)
        text = patched.decode()
        compile(text, "instrumented_evaluate.py", "exec")
        self.assertIn('"candidate_timeline": []', text)
        self.assertIn("actions, responses = [], []", text)
        self.assertIn('responses.append(response)', text)
        self.assertIn('"tested_action": json.loads(encoded(actions[candidate_seat]))', text)
        self.assertIn('"rival_action": json.loads(encoded(actions[1 - candidate_seat]))', text)
        self.assertIn('"debug": json.loads(encoded(responses[candidate_seat].get("debug")))', text)
        self.assertLess(
            text.index("seconds, cpu_seconds = time.perf_counter()"),
            text.index("debug_provider = getattr"),
        )
        self.assertEqual(
            receipt["capture_phase"],
            "after both returned actions, before official interpreter",
        )

    def test_materialization_preserves_source_and_binds_receipt(self):
        original = source_fixture()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "evaluate.py"
            output = root / "instrumented.py"
            receipt = root / "receipt.json"
            source.write_bytes(original)
            with mock.patch.object(m, "EXPECTED_GIT_BLOB", m.git_blob_sha1(original)):
                result = m.materialize(source, output, receipt)
            self.assertEqual(source.read_bytes(), original)
            self.assertNotEqual(output.read_bytes(), original)
            self.assertEqual(result["source"]["git_blob_sha1"], m.git_blob_sha1(original))
            self.assertEqual(result["semantic_boundary"],
                             "observability only; actions and interpreter inputs are unchanged")
            self.assertTrue(receipt.is_file())

    def test_all_anchors_are_singletons_and_source_drift_fails_closed(self):
        original = source_fixture()
        duplicated = original + original
        with mock.patch.object(m, "EXPECTED_GIT_BLOB", m.git_blob_sha1(duplicated)):
            with self.assertRaisesRegex(m.EvaluatorError, "anchor count is 2"):
                m.patch_source(duplicated)
        with mock.patch.object(m, "EXPECTED_GIT_BLOB", "0" * 40):
            with self.assertRaisesRegex(m.EvaluatorError, "source drift"):
                m.patch_source(original)


if __name__ == "__main__":
    unittest.main()
