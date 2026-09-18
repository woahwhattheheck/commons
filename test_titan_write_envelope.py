#!/usr/bin/env python3
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import subprocess
import sys
import unittest

from host.titan_write_envelope import EnvelopeError, SCHEMA, compile_envelope


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixture() -> dict:
    new = b"ABCD"
    old = b"WXYZ"
    return {
        "schema": SCHEMA,
        "target": "models/titan.gguf",
        "expected_preimage": {"size": 100, "sha256": "1" * 64},
        "expected_postimage": {"size": 100, "sha256": "2" * 64},
        "operations": [{
            "offset": 8,
            "length": 4,
            "content_base64": b64(new),
            "sha256": sha(new),
            "rollback_base64": b64(old),
            "rollback_sha256": sha(old),
        }],
        "reversible": True,
        "reason": "Replace one bounded synthetic span after live preimage verification.",
    }


class TitanWriteEnvelopeTests(unittest.TestCase):
    def test_valid_is_deterministic_and_content_free(self):
        first = compile_envelope(fixture())
        second = compile_envelope(fixture())
        self.assertEqual(first, second)
        self.assertFalse(first["mutation_performed"])
        self.assertEqual(first["total_write_bytes"], 4)
        encoded = json.dumps(first)
        self.assertNotIn(b64(b"ABCD"), encoded)
        self.assertNotIn(b64(b"WXYZ"), encoded)

    def test_supplied_matching_intent_is_accepted(self):
        payload = fixture()
        payload["intent_id"] = compile_envelope(payload)["intent_id"]
        self.assertEqual(compile_envelope(payload)["intent_id"], payload["intent_id"])

    def test_wrong_intent_is_rejected(self):
        payload = fixture()
        payload["intent_id"] = "wrong"
        with self.assertRaisesRegex(EnvelopeError, "intent_id"):
            compile_envelope(payload)

    def test_unknown_field_is_rejected(self):
        payload = fixture(); payload["authorize"] = True
        with self.assertRaisesRegex(EnvelopeError, "unknown"):
            compile_envelope(payload)

    def test_traversal_absolute_backslash_and_noncanonical_targets_rejected(self):
        for target in ("../titan.gguf", "/tmp/titan.gguf", "models\\titan.gguf", "models/./titan.gguf"):
            payload = fixture(); payload["target"] = target
            with self.subTest(target=target), self.assertRaises(EnvelopeError):
                compile_envelope(payload)

    def test_booleans_are_not_integers(self):
        for field in ("offset", "length"):
            payload = fixture(); payload["operations"][0][field] = True
            with self.subTest(field=field), self.assertRaises(EnvelopeError):
                compile_envelope(payload)
        payload = fixture(); payload["expected_preimage"]["size"] = True
        with self.assertRaises(EnvelopeError):
            compile_envelope(payload)

    def test_payload_and_rollback_are_both_required(self):
        for field in ("content_base64", "rollback_base64"):
            payload = fixture(); del payload["operations"][0][field]
            with self.subTest(field=field), self.assertRaises(EnvelopeError):
                compile_envelope(payload)

    def test_hash_and_length_mismatches_rejected(self):
        mutations = [
            lambda p: p["operations"][0].update(sha256="0" * 64),
            lambda p: p["operations"][0].update(rollback_sha256="0" * 64),
            lambda p: p["operations"][0].update(length=3),
        ]
        for mutate in mutations:
            payload = fixture(); mutate(payload)
            with self.assertRaises(EnvelopeError):
                compile_envelope(payload)

    def test_out_of_bounds_and_size_changing_rejected(self):
        payload = fixture(); payload["operations"][0]["offset"] = 98
        with self.assertRaises(EnvelopeError):
            compile_envelope(payload)
        payload = fixture(); payload["expected_postimage"]["size"] = 101
        with self.assertRaises(EnvelopeError):
            compile_envelope(payload)

    def test_overlap_rejected(self):
        payload = fixture()
        other = copy.deepcopy(payload["operations"][0]); other["offset"] = 10
        payload["operations"].append(other)
        with self.assertRaisesRegex(EnvelopeError, "overlap"):
            compile_envelope(payload)

    def test_identical_pre_post_digest_rejected(self):
        payload = fixture(); payload["expected_postimage"]["sha256"] = "1" * 64
        with self.assertRaises(EnvelopeError):
            compile_envelope(payload)

    def test_cli_success_and_failure(self):
        root = os.path.dirname(os.path.abspath(__file__))
        command = [sys.executable, os.path.join(root, "host", "titan_write_envelope.py")]
        success = subprocess.run(command, input=json.dumps(fixture()), text=True, capture_output=True, check=False)
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertTrue(json.loads(success.stdout)["ok"])
        failure = subprocess.run(command, input="{}", text=True, capture_output=True, check=False)
        self.assertEqual(failure.returncode, 2)
        self.assertFalse(json.loads(failure.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
