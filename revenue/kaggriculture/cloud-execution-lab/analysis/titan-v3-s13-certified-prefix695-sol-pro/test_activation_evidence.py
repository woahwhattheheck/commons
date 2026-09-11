# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

from activation_capture import (
    DIAGNOSTIC_NAME,
    DIAGNOSTIC_SCHEMA,
    MARKER_NAME,
    build,
)
from certified_evaluate import install_capture


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ActivationEvidenceTests(unittest.TestCase):
    def test_wrapper_preserves_action_and_emits_policy_diagnostics_only_with_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate.py"
            candidate.write_text(
                "SOURCE_SEAT=0\n"
                "ARM_ID='fixture-arm'\n"
                "def agent(obs, configuration=None):\n"
                "    return {'farmer':['PASS'],'hands':[],'market':[]}\n"
                "def diagnostics():\n"
                "    return {'source_seat':0,'start_step':24,'active':True,"
                "'handoff_step':None,'handoff_reason':None,'certificate_checks':1,"
                "'certificate_matches':1,'activation_count':1,'activation_steps':[24]}\n"
            )
            candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
            wrapper = root / "captured.py"
            receipt = root / "receipt.json"
            result = build(candidate, wrapper, receipt, candidate_sha)
            self.assertEqual(result["candidate_sha256"], candidate_sha)
            self.assertEqual(
                json.loads(receipt.read_text())["wrapper_sha256"],
                hashlib.sha256(wrapper.read_bytes()).hexdigest(),
            )
            module = load("activation_capture_fixture", wrapper)

            prior = Path.cwd()
            os.chdir(root)
            try:
                action = module.agent({}, {})
                self.assertEqual(
                    action,
                    {"farmer": ["PASS"], "hands": [], "market": []},
                )
                self.assertFalse((root / DIAGNOSTIC_NAME).exists())
                (root / MARKER_NAME).write_text(DIAGNOSTIC_SCHEMA + "\n")
                self.assertEqual(module.agent({}, {}), action)
                evidence = json.loads((root / DIAGNOSTIC_NAME).read_text())
            finally:
                os.chdir(prior)
            self.assertEqual(evidence["schema"], DIAGNOSTIC_SCHEMA)
            self.assertEqual(evidence["target_sha256"], candidate_sha)
            self.assertEqual(evidence["policy"]["activation_steps"], [24])

    def test_evaluator_adapter_captures_before_actor_directory_cleanup(self):
        class FakeActor:
            def __init__(self):
                self.directory = tempfile.TemporaryDirectory()
                self.stats = {}
            def close(self):
                self.directory.cleanup()

        module = types.SimpleNamespace(Actor=FakeActor)
        install_capture(module)
        actor = module.Actor()
        root = Path(actor.directory.name)
        self.assertTrue((root / MARKER_NAME).is_file())
        payload = {
            "schema": DIAGNOSTIC_SCHEMA,
            "target_name": "candidate.py",
            "target_sha256": "a" * 64,
            "source_seat": 0,
            "arm_id": "fixture",
            "policy": {
                "source_seat": 0,
                "start_step": 24,
                "certificate_checks": 1,
                "certificate_matches": 1,
                "activation_count": 1,
                "activation_steps": [24],
            },
        }
        raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
        (root / DIAGNOSTIC_NAME).write_bytes(raw)
        actor.close()
        self.assertEqual(actor.stats["candidate_diagnostics"], payload)
        self.assertEqual(
            actor.stats["candidate_diagnostics_sha256"],
            hashlib.sha256(raw).hexdigest(),
        )
        self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
