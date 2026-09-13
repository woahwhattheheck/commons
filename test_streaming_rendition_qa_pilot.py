from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from revenue.streaming_rendition_qa_pilot import pilot


class StreamingRenditionQaPilotTests(unittest.TestCase):
    def test_canonical_proof_is_source_recomputed_and_verified(self) -> None:
        receipt = pilot.build_proof_receipt()
        self.assertTrue(pilot.verify_proof_receipt(receipt))
        self.assertEqual(receipt["canonical_proof"]["total"], 168)
        self.assertEqual(receipt["canonical_proof"]["release_ready"], 140)
        self.assertEqual(receipt["canonical_proof"]["hold"], 28)
        self.assertEqual(
            set(receipt["canonical_proof"]["fault_counts"]),
            set(pilot.REQUIRED_FAULT_CLASSES),
        )
        self.assertEqual(set(receipt["canonical_proof"]["fault_counts"].values()), {4})
        self.assertEqual(receipt["commercial_terms"]["diagnostic"]["fixed_price_cents"], 250_000)
        self.assertEqual(receipt["commercial_terms"]["diagnostic"]["max_asset_packets"], 250)
        self.assertEqual(receipt["commercial_terms"]["integration_expansion"]["fixed_price_cents"], 750_000)

    def test_tampered_receipt_is_rejected(self) -> None:
        receipt = pilot.build_proof_receipt()
        altered = json.loads(json.dumps(receipt))
        altered["canonical_proof"]["hold"] = 27
        self.assertFalse(pilot.verify_proof_receipt(altered))
        altered = json.loads(json.dumps(receipt))
        altered["commercial_terms"]["diagnostic"]["fixed_price_cents"] = 1
        self.assertFalse(pilot.verify_proof_receipt(altered))
        altered = json.loads(json.dumps(receipt))
        altered["external_authority"]["publishing"] = True
        self.assertFalse(pilot.verify_proof_receipt(altered))

    def test_source_truth_drift_fails_closed(self) -> None:
        with patch.object(pilot, "EXPECTED_PROJECTION_SHA256", "0" * 64):
            with self.assertRaisesRegex(pilot.PilotProofError, "projection digest drift"):
                pilot.build_proof_receipt()

    def test_buyer_facing_documents_preserve_authority_ceiling(self) -> None:
        receipt = pilot.build_proof_receipt()
        diagnostic = pilot.render_synthetic_diagnostic(receipt)
        scope = pilot.render_scope_markdown(receipt)
        self.assertIn("$2,500 fixed", diagnostic)
        self.assertIn("$7,500 integration sprint", diagnostic)
        self.assertIn("MISSING_RENDITION", diagnostic)
        self.assertIn("PUBLICATION_WINDOW_CONFLICT", diagnostic)
        self.assertIn("No customer media", diagnostic)
        self.assertIn("<= 250 asset packets", scope)
        self.assertIn("no free speculative adapter work", scope)
        self.assertIn("does not determine rights", scope)
        self.assertNotIn("revenue recognized", diagnostic.lower())

    def test_bundle_manifest_binds_every_deliverable(self) -> None:
        files = pilot.build_bundle()
        self.assertEqual(
            set(files),
            {"synthetic-diagnostic.md", "scope-and-price.md", "proof-receipt.json", "bundle-manifest.json"},
        )
        manifest = json.loads(files["bundle-manifest.json"])
        self.assertTrue(all(value is False for value in manifest["external_authority"].values()))
        for name, expected in manifest["files"].items():
            self.assertEqual(hashlib.sha256(files[name].encode("utf-8")).hexdigest(), expected)
        receipt = json.loads(files["proof-receipt.json"])
        self.assertTrue(pilot.verify_proof_receipt(receipt))
        self.assertEqual(manifest["proof_receipt_sha256"], receipt["receipt_sha256"])

    def test_write_bundle_is_create_exclusive_and_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "pilot-a"
            second = Path(temp) / "pilot-b"
            hashes_a = pilot.write_bundle(first)
            hashes_b = pilot.write_bundle(second)
            self.assertEqual(hashes_a, hashes_b)
            for name in hashes_a:
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            with self.assertRaises(FileExistsError):
                pilot.write_bundle(first)

    def test_final_component_symlink_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            real = root / "real"
            real.mkdir()
            linked = root / "linked"
            linked.symlink_to(real, target_is_directory=True)
            with self.assertRaises(FileExistsError):
                pilot.write_bundle(linked)

    def test_checked_in_samples_match_live_renderer(self) -> None:
        root = Path(__file__).resolve().parent
        receipt = pilot.build_proof_receipt()
        sample_root = root / "revenue" / "streaming_rendition_qa_pilot" / "sample"
        self.assertEqual(
            (sample_root / "SYNTHETIC_DIAGNOSTIC.md").read_text(encoding="utf-8"),
            pilot.render_synthetic_diagnostic(receipt),
        )
        self.assertEqual(
            (sample_root / "PILOT_SCOPE.md").read_text(encoding="utf-8"),
            pilot.render_scope_markdown(receipt),
        )
        self.assertEqual(
            json.loads((sample_root / "PROOF_RECEIPT.json").read_text(encoding="utf-8")),
            receipt,
        )


if __name__ == "__main__":
    unittest.main()
