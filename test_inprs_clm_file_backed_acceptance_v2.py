#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
PKG = ROOT / "revenue" / "inprs_clm_migration_gate"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


accept = _load("inprs_file_accept_v2_test", PKG / "file_backed_acceptance.py")
builder = _load("inprs_file_builder_v2_test", PKG / "build_synthetic_file_handoff.py")


class InprsFileBackedAcceptanceV2Test(unittest.TestCase):
    def make(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name) / "handoff"
        manifest, bundle, pin = builder.build(root)
        return tmp, root, manifest, bundle, pin

    @staticmethod
    def codes(receipt: dict) -> set[str]:
        return {str(row).split(":", 1)[0] for row in receipt["errors"]}

    def test_manifest_roots_every_historical_version(self) -> None:
        tmp, root, manifest_path, bundle, pin = self.make()
        self.addCleanup(tmp.cleanup)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 2)
        for row in manifest["contracts"]:
            roots = row["version_roots"]
            self.assertEqual(row["version_paths"], [item["path"] for item in roots])
            self.assertEqual([item["revision"] for item in roots], list(range(1, len(roots) + 1)))
            self.assertEqual(roots[-1]["sha256"], row["source_sha256"])
        receipt = accept.verify_handoff(manifest_path, pin, bundle, root)
        self.assertTrue(receipt["accepted"], receipt)
        self.assertGreater(receipt["version_roots_verified"], 0)
        self.assertGreater(receipt["version_bytes_verified"], 0)

    def test_paired_historical_file_and_candidate_hash_rewrite_fails(self) -> None:
        tmp, root, manifest_path, bundle_path, pin = self.make()
        self.addCleanup(tmp.cleanup)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        contract_manifest = manifest["contracts"][0]
        contract = next(row for row in bundle["contracts"] if row["legacy_id"] == contract_manifest["legacy_id"])
        rel = contract_manifest["version_roots"][0]["path"]
        tampered = b"PAIRED CALLER REWRITE OF HISTORICAL VERSION\n"
        (root / rel).write_bytes(tampered)
        contract["version_history"][0]["sha256"] = accept._sha(tampered)
        bundle_path.write_bytes(json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode())
        receipt = accept.verify_handoff(manifest_path, pin, bundle_path, root)
        codes = self.codes(receipt)
        self.assertFalse(receipt["accepted"])
        self.assertIn("VERSION_ROOT_FILE_HASH_MISMATCH", codes)
        self.assertIn("VERSION_ROOT_CANDIDATE_HASH_MISMATCH", codes)

    def test_manifest_root_remint_without_external_pin_fails(self) -> None:
        tmp, root, manifest_path, bundle_path, pin = self.make()
        self.addCleanup(tmp.cleanup)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        contract_manifest = manifest["contracts"][0]
        contract = next(row for row in bundle["contracts"] if row["legacy_id"] == contract_manifest["legacy_id"])
        rel = contract_manifest["version_roots"][0]["path"]
        rewritten = b"NEW HISTORY GENERATION\n"
        digest = accept._sha(rewritten)
        (root / rel).write_bytes(rewritten)
        contract_manifest["version_roots"][0]["sha256"] = digest
        contract["version_history"][0]["sha256"] = digest
        manifest_path.write_bytes(accept.canonical_manifest_bytes(manifest))
        bundle_path.write_bytes(json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode())
        receipt = accept.verify_handoff(manifest_path, pin, bundle_path, root)
        self.assertFalse(receipt["accepted"])
        self.assertIn("MANIFEST_PIN_MISMATCH", self.codes(receipt))

    def test_bundle_generation_is_snapshotted_before_legacy_delegation(self) -> None:
        tmp, root, manifest_path, bundle_path, pin = self.make()
        self.addCleanup(tmp.cleanup)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        contract_manifest = next(
            row for row in manifest["contracts"] if len(row["version_roots"]) > 1
        )
        rel = contract_manifest["version_roots"][0]["path"]
        rewritten = b"SECOND BUNDLE GENERATION HISTORICAL VERSION\n"
        original_validate = accept._validate_version_roots

        def mutate_after_root_check(manifest_obj, bundle_obj, root_obj):
            result = original_validate(manifest_obj, bundle_obj, root_obj)
            later = json.loads(bundle_path.read_text(encoding="utf-8"))
            contract = next(
                row
                for row in later["contracts"]
                if row["legacy_id"] == contract_manifest["legacy_id"]
            )
            (root / rel).write_bytes(rewritten)
            contract["version_history"][0]["sha256"] = accept._sha(rewritten)
            bundle_path.write_bytes(
                json.dumps(later, sort_keys=True, separators=(",", ":")).encode()
            )
            return result

        accept._validate_version_roots = mutate_after_root_check
        self.addCleanup(setattr, accept, "_validate_version_roots", original_validate)
        receipt = accept.verify_handoff(manifest_path, pin, bundle_path, root)
        self.assertFalse(receipt["accepted"], receipt)
        self.assertIn("VERSION_FILE_HASH_MISMATCH", self.codes(receipt))

    def test_bundle_duplicate_key_fails_before_legacy_projection(self) -> None:
        tmp, root, manifest_path, bundle_path, pin = self.make()
        self.addCleanup(tmp.cleanup)
        raw = bundle_path.read_text(encoding="utf-8")
        self.assertTrue(raw.startswith("{"))
        bundle_path.write_text('{"contracts":[],' + raw[1:], encoding="utf-8")
        receipt = accept.verify_handoff(manifest_path, pin, bundle_path, root)
        self.assertFalse(receipt["accepted"])
        self.assertIn("BUNDLE_DUPLICATE_KEY", self.codes(receipt))


if __name__ == "__main__":
    unittest.main()
