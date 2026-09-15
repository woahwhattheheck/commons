import copy
import unittest

from revenue.product_catalog_bridge.bridge import (
    CatalogBridgeError,
    canonical_json,
    compile_catalog_bridge,
    render_csv,
    render_markdown,
    verify_receipt,
)

AS_OF = "2026-09-13T10:00:00Z"
A40 = "a" * 40
B40 = "b" * 40
D64 = "d" * 64
E64 = "e" * 64
F64 = "f" * 64
C64 = "c" * 64


def fixture():
    return {
        "schema": "commons-product-catalog-bridge-input/v1",
        "artifacts": [
            {
                "artifactId": "autopsy-cli",
                "repository": "woahwhattheheck/commons",
                "commitSha": A40,
                "sourcePath": "revenue/autopsy/cli.py",
                "contentSha256": D64,
                "version": "1.4.5",
                "licenseId": "MIT",
                "licenseEvidenceSha256": E64,
                "transferBoundary": "SOURCE_ARCHIVE",
                "catalogListingId": "autopsy-product",
            },
            {
                "artifactId": "receipt-tool",
                "repository": "woahwhattheheck/commons",
                "commitSha": B40,
                "sourcePath": "tools/receipts/verify.py",
                "contentSha256": F64,
                "version": "2.0.0",
                "licenseId": "Apache-2.0",
                "licenseEvidenceSha256": C64,
                "transferBoundary": "LOCAL_APPLICATION",
                "catalogListingId": "receipt-product",
            },
        ],
        "listings": [
            {
                "listingId": "autopsy-product",
                "title": "Autopsy CLI",
                "family": "PRODUCT",
                "status": "INTERNAL_READY",
                "version": "1.4.5",
                "artifactIds": ["autopsy-cli"],
            },
            {
                "listingId": "receipt-product",
                "title": "Receipt Verifier",
                "family": "PRODUCT",
                "status": "DRAFT",
                "version": "2.0.0",
                "artifactIds": ["receipt-tool"],
            },
        ],
        "evidence": [
            {
                "evidenceId": "ev-autopsy",
                "artifactId": "autopsy-cli",
                "contentSha256": D64,
                "verificationKind": "SOURCE_TEST",
                "outcome": "PASS",
                "capturedAt": "2026-09-12T10:00:00Z",
                "sourceSha256": E64,
            },
            {
                "evidenceId": "ev-receipt",
                "artifactId": "receipt-tool",
                "contentSha256": F64,
                "verificationKind": "PACKAGE_TEST",
                "outcome": "PASS",
                "capturedAt": "2026-09-12T11:00:00Z",
                "sourceSha256": D64,
            },
        ],
    }


class ProductCatalogBridgeTests(unittest.TestCase):
    def test_ready_fixture(self):
        receipt = compile_catalog_bridge(fixture(), as_of=AS_OF)
        self.assertEqual(receipt["state"], "READY_FOR_HUMAN_CATALOG_PUBLICATION")
        self.assertEqual(receipt["counts"], {"artifacts": 2, "listings": 2, "evidence": 2, "holds": 0})
        self.assertFalse(any(receipt["authority"].values()))
        self.assertTrue(verify_receipt(fixture(), as_of=AS_OF, receipt=receipt))

    def test_deterministic_under_input_reordering(self):
        left = fixture()
        right = fixture()
        right["artifacts"].reverse(); right["listings"].reverse(); right["evidence"].reverse()
        self.assertEqual(canonical_json(compile_catalog_bridge(left, as_of=AS_OF)), canonical_json(compile_catalog_bridge(right, as_of=AS_OF)))

    def test_receipt_self_hash_forgery_rejected(self):
        raw = fixture(); receipt = compile_catalog_bridge(raw, as_of=AS_OF)
        receipt["state"] = "HOLD"
        body = dict(receipt); body.pop("receiptSha256", None)
        import hashlib
        receipt["receiptSha256"] = hashlib.sha256(canonical_json(body).encode()).hexdigest()
        self.assertFalse(verify_receipt(raw, as_of=AS_OF, receipt=receipt))

    def test_missing_listing_holds(self):
        raw = fixture(); raw["listings"] = raw["listings"][1:]
        receipt = compile_catalog_bridge(raw, as_of=AS_OF)
        self.assertEqual(receipt["state"], "HOLD")
        self.assertIn("MISSING_LISTING", {x["code"] for x in receipt["holds"]})

    def test_listing_backref_mismatch_holds(self):
        raw = fixture(); raw["listings"][0]["artifactIds"] = ["receipt-tool"]
        receipt = compile_catalog_bridge(raw, as_of=AS_OF)
        codes = {x["code"] for x in receipt["holds"]}
        self.assertIn("LISTING_BACKREF_MISMATCH", codes)
        self.assertIn("LISTING_COVERAGE_MISMATCH", codes)

    def test_unknown_artifact_in_listing_holds(self):
        raw = fixture(); raw["listings"][0]["artifactIds"].append("ghost")
        receipt = compile_catalog_bridge(raw, as_of=AS_OF)
        self.assertIn("LISTING_NAMES_UNKNOWN_ARTIFACT", {x["code"] for x in receipt["holds"]})

    def test_orphan_evidence_holds(self):
        raw = fixture(); extra = copy.deepcopy(raw["evidence"][0]); extra["evidenceId"] = "ev-orphan"; extra["artifactId"] = "ghost"; raw["evidence"].append(extra)
        receipt = compile_catalog_bridge(raw, as_of=AS_OF)
        self.assertIn("ORPHAN_EVIDENCE", {x["code"] for x in receipt["holds"]})

    def test_content_digest_mismatch_holds(self):
        raw = fixture(); raw["evidence"][0]["contentSha256"] = F64
        receipt = compile_catalog_bridge(raw, as_of=AS_OF)
        codes = {x["code"] for x in receipt["holds"]}
        self.assertIn("EVIDENCE_CONTENT_MISMATCH", codes)
        self.assertIn("NO_CURRENT_PASSING_EVIDENCE", codes)

    def test_failed_evidence_holds(self):
        raw = fixture(); raw["evidence"][0]["outcome"] = "FAIL"
        receipt = compile_catalog_bridge(raw, as_of=AS_OF)
        self.assertIn("VERIFICATION_FAILED", {x["code"] for x in receipt["holds"]})

    def test_future_evidence_holds(self):
        raw = fixture(); raw["evidence"][0]["capturedAt"] = "2026-09-14T10:00:00Z"
        receipt = compile_catalog_bridge(raw, as_of=AS_OF)
        self.assertIn("EVIDENCE_FROM_FUTURE", {x["code"] for x in receipt["holds"]})

    def test_stale_evidence_holds(self):
        raw = fixture(); raw["evidence"][0]["capturedAt"] = "2026-07-01T10:00:00Z"
        receipt = compile_catalog_bridge(raw, as_of=AS_OF)
        self.assertIn("EVIDENCE_STALE", {x["code"] for x in receipt["holds"]})

    def test_timezone_less_as_of_rejected(self):
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(fixture(), as_of="2026-09-13T10:00:00")

    def test_timezone_less_evidence_rejected(self):
        raw = fixture(); raw["evidence"][0]["capturedAt"] = "2026-09-12T10:00:00"
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_unknown_top_level_key_rejected(self):
        raw = fixture(); raw["surprise"] = True
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_unknown_artifact_key_rejected(self):
        raw = fixture(); raw["artifacts"][0]["approved"] = True
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_unknown_listing_key_rejected(self):
        raw = fixture(); raw["listings"][0]["priceCents"] = 2900
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_unknown_evidence_key_rejected(self):
        raw = fixture(); raw["evidence"][0]["runner"] = "hosted"
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_mutable_commit_ref_rejected(self):
        raw = fixture(); raw["artifacts"][0]["commitSha"] = "main"
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_uppercase_commit_sha_rejected(self):
        raw = fixture(); raw["artifacts"][0]["commitSha"] = "A" * 40
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_path_traversal_rejected(self):
        raw = fixture(); raw["artifacts"][0]["sourcePath"] = "revenue/../secret.txt"
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_backslash_path_rejected(self):
        raw = fixture(); raw["artifacts"][0]["sourcePath"] = "revenue\\artifact.py"
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_unknown_license_rejected(self):
        raw = fixture(); raw["artifacts"][0]["licenseId"] = "UNKNOWN"
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_unsupported_transfer_boundary_rejected(self):
        raw = fixture(); raw["artifacts"][0]["transferBoundary"] = "WHATEVER"
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_non_product_listing_rejected(self):
        raw = fixture(); raw["listings"][0]["family"] = "SERVICE"
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_email_shaped_metadata_rejected(self):
        raw = fixture(); raw["listings"][0]["title"] = "Send to buyer@example.com"
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_secret_shaped_metadata_rejected(self):
        raw = fixture(); raw["listings"][0]["title"] = "token=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_duplicate_artifact_id_rejected(self):
        raw = fixture(); extra = copy.deepcopy(raw["artifacts"][0]); raw["artifacts"].append(extra)
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_duplicate_listing_artifact_ids_rejected(self):
        raw = fixture(); raw["listings"][0]["artifactIds"] = ["autopsy-cli", "autopsy-cli"]
        with self.assertRaises(CatalogBridgeError): compile_catalog_bridge(raw, as_of=AS_OF)

    def test_conflicting_repo_path_identity_holds(self):
        raw = fixture(); extra = copy.deepcopy(raw["artifacts"][0]); extra["artifactId"] = "autopsy-cli-two"; extra["catalogListingId"] = "autopsy-product"; raw["artifacts"].append(extra); raw["listings"][0]["artifactIds"].append("autopsy-cli-two")
        ev = copy.deepcopy(raw["evidence"][0]); ev["evidenceId"] = "ev-autopsy-two"; ev["artifactId"] = "autopsy-cli-two"; raw["evidence"].append(ev)
        receipt = compile_catalog_bridge(raw, as_of=AS_OF)
        self.assertIn("CONFLICTING_ARTIFACT_IDENTITY", {x["code"] for x in receipt["holds"]})

    def test_tampered_input_rejects_old_receipt(self):
        raw = fixture(); receipt = compile_catalog_bridge(raw, as_of=AS_OF)
        raw["artifacts"][0]["version"] = "1.4.6"
        self.assertFalse(verify_receipt(raw, as_of=AS_OF, receipt=receipt))

    def test_changed_trusted_clock_rejects_old_receipt(self):
        raw = fixture(); receipt = compile_catalog_bridge(raw, as_of=AS_OF)
        self.assertFalse(verify_receipt(raw, as_of="2026-09-13T10:00:01Z", receipt=receipt))

    def test_csv_is_deterministic_and_contains_no_evidence_source(self):
        receipt = compile_catalog_bridge(fixture(), as_of=AS_OF)
        left = render_csv(receipt); right = render_csv(receipt)
        self.assertEqual(left, right)
        self.assertIn("artifactId,catalogListingId", left)
        self.assertNotIn("sourceSha256", left)

    def test_markdown_authority_boundary(self):
        receipt = compile_catalog_bridge(fixture(), as_of=AS_OF)
        text = render_markdown(receipt)
        self.assertIn("human catalog publication review", text)
        self.assertIn("never publishes a catalog listing", text)
        self.assertNotIn("buyer@example.com", text)


if __name__ == "__main__":
    unittest.main()
