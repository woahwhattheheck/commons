#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from host import artifact_registry as ar  # noqa: E402

A = "a" * 64
B = "b" * 64
COMMIT = "c" * 40
BLOB = "d" * 40


class ArtifactRegistryTests(unittest.TestCase):
    def test_add_is_deterministic_and_idempotent(self):
        source = {"kind": "git_blob", "repo": "o/r", "blob_sha": BLOB.upper()}
        one = ar.add_artifact(ar.empty_registry(), A.upper(), source, size_bytes=12, labels=["proof"])
        two = ar.add_artifact(one, A, source, size_bytes=12, labels=["proof"])
        self.assertEqual(one, two)
        self.assertEqual(one["artifacts"][A]["sources"][0]["blob_sha"], BLOB)
        self.assertEqual(ar.dump_registry(one), ar.dump_registry(two))

    def test_workflow_artifact_requires_producing_job_conclusion(self):
        source = {"kind": "workflow_artifact", "repo": "o/r", "run_id": 11,
                  "job_id": 22, "artifact_id": 33, "name": "receipt"}
        with self.assertRaisesRegex(ValueError, "job_conclusion"):
            ar.add_artifact(ar.empty_registry(), A, source)
        source["job_conclusion"] = "success"
        row = ar.add_artifact(ar.empty_registry(), A, source)["artifacts"][A]
        self.assertEqual(row["sources"][0]["job_conclusion"], "success")

    def test_bool_ids_are_not_integers(self):
        source = {"kind": "workflow_artifact", "repo": "o/r", "run_id": True,
                  "job_id": 22, "artifact_id": 33, "name": "receipt",
                  "job_conclusion": "success"}
        with self.assertRaisesRegex(ValueError, "run_id"):
            ar.add_artifact(ar.empty_registry(), A, source)

    def test_same_durable_locator_cannot_claim_two_digests(self):
        source = {"kind": "path", "repo": "o/r", "commit_sha": COMMIT,
                  "path": "out/receipt.json"}
        registry = ar.add_artifact(ar.empty_registry(), A, source)
        with self.assertRaisesRegex(ValueError, "already belongs"):
            ar.add_artifact(registry, B, source)

    def test_same_workflow_artifact_cannot_change_metadata(self):
        source = {"kind": "workflow_artifact", "repo": "o/r", "run_id": 11,
                  "job_id": 22, "artifact_id": 33, "name": "receipt",
                  "job_conclusion": "success"}
        registry = ar.add_artifact(ar.empty_registry(), A, source)
        poisoned = dict(source, job_conclusion="failure")
        with self.assertRaisesRegex(ValueError, "metadata conflicts"):
            ar.add_artifact(registry, A, poisoned)

    def test_size_conflict_fails_closed(self):
        source = {"kind": "git_commit", "repo": "o/r", "commit_sha": COMMIT}
        registry = ar.add_artifact(ar.empty_registry(), A, source, size_bytes=8)
        with self.assertRaisesRegex(ValueError, "size_bytes conflicts"):
            ar.add_artifact(registry, A, source, size_bytes=9)

    def test_strict_loader_rejects_duplicate_json_keys_and_nonfinite(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            ar.loads_strict('{"schema":"x","schema":"y"}')
        with self.assertRaisesRegex(ValueError, "non-finite"):
            ar.loads_strict('{"x":NaN}')

    def test_registry_row_key_must_match_sha(self):
        value = {"schema": ar.SCHEMA, "artifacts": {A: {
            "sha256": B,
            "sources": [{"kind": "git_blob", "repo": "o/r", "blob_sha": BLOB}],
        }}}
        with self.assertRaisesRegex(ValueError, "match its key"):
            ar.validate_registry(value)

    def test_hash_file_reports_exact_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.bin")
            with open(path, "wb") as fh:
                fh.write(b"abc\x00\n")
            digest, size = ar.sha256_file(path)
            self.assertEqual(size, 5)
            import hashlib
            self.assertEqual(digest, hashlib.sha256(b"abc\x00\n").hexdigest())

    def test_cli_add_validate_get_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            source = json.dumps({"kind": "slack_file", "channel_id": "C123", "file_id": "F456"})
            base = [sys.executable, os.path.join(os.path.dirname(__file__), "host", "artifact_registry.py")]
            add = subprocess.run(base + ["add", path, A, "--source-json", source, "--size-bytes", "7"],
                                 text=True, capture_output=True)
            self.assertEqual(add.returncode, 0, add.stderr)
            validate = subprocess.run(base + ["validate", path], text=True, capture_output=True)
            self.assertEqual(validate.returncode, 0, validate.stderr)
            get = subprocess.run(base + ["get", path, A], text=True, capture_output=True)
            self.assertEqual(get.returncode, 0, get.stderr)
            self.assertEqual(json.loads(get.stdout)["size_bytes"], 7)


if __name__ == "__main__":
    unittest.main()
