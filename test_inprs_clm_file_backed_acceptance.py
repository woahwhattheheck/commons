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


accept = _load("inprs_file_accept", PKG / "file_backed_acceptance.py")
builder = _load("inprs_file_builder", PKG / "build_synthetic_file_handoff.py")


class InprsFileBackedAcceptanceTest(unittest.TestCase):
    def make(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name) / "handoff"
        manifest, bundle, pin = builder.build(root)
        return tmp, root, manifest, bundle, pin

    def codes(self, receipt: dict) -> set[str]:
        return {str(row).split(":", 1)[0] for row in receipt["errors"]}

    def test_synthetic_handoff_passes_and_receipt_is_location_independent(self) -> None:
        first_tmp, first_root, first_manifest, first_bundle, first_pin = self.make()
        second_tmp, second_root, second_manifest, second_bundle, second_pin = self.make()
        self.addCleanup(first_tmp.cleanup)
        self.addCleanup(second_tmp.cleanup)
        first = accept.verify_handoff(first_manifest, first_pin, first_bundle, first_root)
        second = accept.verify_handoff(second_manifest, second_pin, second_bundle, second_root)
        self.assertTrue(first["accepted"], first)
        self.assertTrue(second["accepted"], second)
        self.assertEqual(accept.canonical_receipt_bytes(first), accept.canonical_receipt_bytes(second))
        self.assertFalse(any(first["authority"].values()))

    def test_manifest_remint_does_not_move_external_pin(self) -> None:
        tmp, root, manifest_path, bundle, pin = self.make()
        self.addCleanup(tmp.cleanup)
        manifest = json.loads(manifest_path.read_text())
        manifest["contracts"][0]["public_action"] = "withhold"
        manifest_path.write_bytes(accept.canonical_manifest_bytes(manifest))
        receipt = accept.verify_handoff(manifest_path, pin, bundle, root)
        self.assertIn("MANIFEST_PIN_MISMATCH", self.codes(receipt))

    def test_source_and_target_actual_byte_drift_fail(self) -> None:
        tmp, root, manifest, bundle, pin = self.make()
        self.addCleanup(tmp.cleanup)
        (root / "source/contracts/C-100.txt").write_bytes(b"tampered source\n")
        (root / "target/contracts/C-101.txt").write_bytes(b"tampered target\n")
        receipt = accept.verify_handoff(manifest, pin, bundle, root)
        codes = self.codes(receipt)
        self.assertIn("SOURCE_HASH_MISMATCH", codes)
        self.assertIn("TARGET_SOURCE_DRIFT", codes)

    def test_candidate_row_drop_cannot_lower_fixed_baseline(self) -> None:
        tmp, root, manifest, bundle_path, pin = self.make()
        self.addCleanup(tmp.cleanup)
        bundle = json.loads(bundle_path.read_text())
        bundle["contracts"] = [row for row in bundle["contracts"] if row["legacy_id"] != "C-200"]
        bundle["expectations"]["source_contract_count"] = 2
        bundle["expectations"]["master_count"] = 1
        bundle["expectations"]["inactive_count"] = 0
        bundle_path.write_bytes(json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode())
        receipt = accept.verify_handoff(manifest, pin, bundle_path, root)
        self.assertIn("BUNDLE_CONTRACT_SET_MISMATCH", self.codes(receipt))

    def test_source_semantic_relabel_fails_even_when_public_projection_matches(self) -> None:
        tmp, root, manifest, bundle_path, pin = self.make()
        self.addCleanup(tmp.cleanup)
        bundle = json.loads(bundle_path.read_text())
        contract = next(row for row in bundle["contracts"] if row["legacy_id"] == "C-100")
        contract["company_name"] = "Relabeled Vendor"
        public = next(row for row in bundle["public_records"] if row["legacy_id"] == "C-100")
        public["company_name"] = "Relabeled Vendor"
        public["search_terms"] = [term if term != "synthetic analytics" else "relabeled vendor" for term in public["search_terms"]]
        public["search_terms"] = sorted(public["search_terms"])
        bundle_path.write_bytes(json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode())
        receipt = accept.verify_handoff(manifest, pin, bundle_path, root)
        self.assertIn("SOURCE_RECORD_DRIFT", self.codes(receipt))

    def test_extra_public_file_and_symlink_fail_closed(self) -> None:
        tmp, root, manifest, bundle, pin = self.make()
        self.addCleanup(tmp.cleanup)
        (root / "public/contracts/EXTRA.txt").write_text("extra")
        link = root / "source/contracts/C-100.txt"
        original = link.read_bytes()
        link.unlink()
        outside = root / "outside.txt"
        outside.write_bytes(original)
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        receipt = accept.verify_handoff(manifest, pin, bundle, root)
        codes = self.codes(receipt)
        self.assertIn("PUBLIC_FILE_SET_MISMATCH", codes)
        self.assertIn("PATH_SYMLINK_REJECTED", codes)

    def test_internal_vendor_bytes_cannot_be_exposed_as_redacted_public_document(self) -> None:
        tmp, root, manifest, bundle_path, pin = self.make()
        self.addCleanup(tmp.cleanup)
        internal = (root / "source/vendor/V-1.txt").read_bytes()
        public_path = root / "public/contracts/C-101.txt"
        public_path.write_bytes(internal)
        digest = accept._sha(internal)
        bundle = json.loads(bundle_path.read_text())
        contract = next(row for row in bundle["contracts"] if row["legacy_id"] == "C-101")
        public = next(row for row in bundle["public_records"] if row["legacy_id"] == "C-101")
        contract["public_document_sha256"] = digest
        public["document_sha256"] = digest
        bundle_path.write_bytes(json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode())
        receipt = accept.verify_handoff(manifest, pin, bundle_path, root)
        self.assertIn("PUBLIC_INTERNAL_HASH_EXPOSURE", self.codes(receipt))

    def test_version_file_drift_is_bound_to_actual_bytes(self) -> None:
        tmp, root, manifest, bundle, pin = self.make()
        self.addCleanup(tmp.cleanup)
        (root / "target/versions/C-100/1.txt").write_text("wrong prior revision\n")
        receipt = accept.verify_handoff(manifest, pin, bundle, root)
        self.assertIn("VERSION_FILE_HASH_MISMATCH", self.codes(receipt))


if __name__ == "__main__":
    unittest.main()
