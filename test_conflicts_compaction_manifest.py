#!/usr/bin/env python3
"""Canary: regenerated compaction manifest matches current conflict blobs.

Proves every named before_sha256 equals the current blob. Apply stays
refuse-only while the manifest is invalid, and still refuses to write
conflict jsonl bodies when hashes match but compaction is unapproved.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "conflicts_compaction_manifest",
    ROOT / "host" / "conflicts_compaction_manifest.py",
)
helper = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(helper)


class ConflictsCompactionManifestTests(unittest.TestCase):
    def test_live_before_sha256_matches_current_blobs(self):
        manifest = helper.load_manifest(ROOT / "conflicts_compaction_manifest.json")
        conflicts = ROOT / "conflicts"
        check = helper.validate_manifest(manifest, conflicts)
        self.assertFalse(manifest.get("invalid"), manifest.get("invalid_reason"))
        self.assertFalse(manifest.get("applied"))
        self.assertGreater(check["named"], 0)
        self.assertEqual(check["missing"], [])
        self.assertEqual(check["stale"], 0, check["mismatches"][:3])
        self.assertTrue(check["hash_match"])
        self.assertTrue(check["ok"])
        for entry in manifest["files"]:
            path = conflicts / entry["file"]
            self.assertTrue(path.is_file(), entry["file"])
            self.assertEqual(helper.file_sha256(path), entry["before_sha256"], entry["file"])

    def test_invalid_manifest_forbids_compact_and_leaves_jsonl_untouched(self):
        raw = b'{"id":"one"}\n{"id":"one"}\n{"id":"two"}\n'
        with tempfile.TemporaryDirectory() as tmp:
            conflicts = Path(tmp) / "conflicts"
            conflicts.mkdir()
            path = conflicts / "one.jsonl"
            path.write_bytes(raw)
            before = path.read_bytes()
            before_hash = hashlib.sha256(before).hexdigest()
            manifest = {
                "invalid": True,
                "applied": False,
                "compaction_status": "UNAPPROVED",
                "files": [
                    {
                        "file": "one.jsonl",
                        "before_sha256": "deadbeef" * 8,
                        "before_bytes": len(raw),
                        "lines": 3,
                        "unique": 2,
                    }
                ],
            }
            check = helper.validate_manifest(manifest, conflicts)
            self.assertFalse(check["ok"])
            self.assertEqual(check["stale"], 1)
            self.assertTrue(check["invalid_flag"])
            decision = helper.apply_compaction(manifest, conflicts)
            self.assertEqual(decision["status"], "REFUSED_INVALID")
            self.assertTrue(decision["refused"])
            self.assertEqual(decision["wrote"], [])
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before_hash)

    def test_matching_unapproved_manifest_still_does_not_write(self):
        raw = b'{"id":"one"}\n{"id":"one"}\n'
        with tempfile.TemporaryDirectory() as tmp:
            conflicts = Path(tmp) / "conflicts"
            conflicts.mkdir()
            path = conflicts / "one.jsonl"
            path.write_bytes(raw)
            manifest = helper.regenerate_manifest(conflicts, "head", "tree")
            self.assertTrue(helper.validate_manifest(manifest, conflicts)["ok"])
            decision = helper.apply_compaction(manifest, conflicts)
            self.assertEqual(decision["status"], "REFUSED_UNAPPROVED")
            self.assertEqual(decision["wrote"], [])
            self.assertEqual(path.read_bytes(), raw)

    def test_helper_self_test(self):
        self.assertTrue(helper._self_test())


if __name__ == "__main__":
    unittest.main()
