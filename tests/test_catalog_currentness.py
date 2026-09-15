import copy
import hashlib
import unittest

from revenue.catalog_currentness.audit import (
    CatalogCurrentnessError, canonical_json, compile_currentness, render_csv, render_markdown, verify_receipt,
)

AS_OF = "2026-09-13T10:15:00Z"
A64, B64, C64, D64, E64, F64 = (c * 64 for c in "abcdef")
A40, B40, C40 = (c * 40 for c in "abc")


def fixture():
    return {
        "schema": "commons-catalog-currentness-input/v1",
        "catalogs": [
            {"catalogId": "products", "family": "PRODUCT", "catalogDigestSha256": A64, "entries": [
                {"entryId": "product-v1", "artifactId": "product", "repository": "org/product", "releaseCommitSha": A40,
                 "sourcePath": "src/product.py", "sourceContentSha256": B64, "sourceEvidenceSha256": C64, "version": "1.0.0", "currentnessPolicy": "FOLLOW_DEFAULT_BRANCH"},
            ]},
            {"catalogId": "services", "family": "SERVICE", "catalogDigestSha256": D64, "entries": [
                {"entryId": "service-v2", "artifactId": "service", "repository": "org/service", "releaseCommitSha": B40,
                 "sourcePath": "service/core.py", "sourceContentSha256": E64, "sourceEvidenceSha256": F64, "version": "2.0.0", "currentnessPolicy": "PINNED_RELEASE"},
            ]},
        ],
        "providerSnapshots": [
            {"snapshotId": "product-main", "repository": "org/product", "defaultBranch": "main", "defaultBranchHeadSha": C40,
             "capturedAt": "2026-09-13T10:00:00Z", "complete": True, "providerEvidenceSha256": A64,
             "paths": [{"sourcePath": "src/product.py", "contentSha256": B64}]},
            {"snapshotId": "service-main", "repository": "org/service", "defaultBranch": "main", "defaultBranchHeadSha": C40,
             "capturedAt": "2026-09-13T10:00:00Z", "complete": True, "providerEvidenceSha256": B64,
             "paths": [{"sourcePath": "service/core.py", "contentSha256": E64}]},
        ],
    }


class CatalogCurrentnessTests(unittest.TestCase):
    def test_all_current_ready(self):
        r = compile_currentness(fixture(), as_of=AS_OF)
        self.assertEqual(r["state"], "READY_FOR_HUMAN_CATALOG_CURRENTNESS_REVIEW")
        self.assertEqual(r["counts"]["current"], 2)
        self.assertFalse(any(r["authority"].values()))
        self.assertTrue(verify_receipt(fixture(), as_of=AS_OF, receipt=r))

    def test_deterministic_reordering(self):
        x, y = fixture(), fixture(); y["catalogs"].reverse(); y["providerSnapshots"].reverse()
        self.assertEqual(canonical_json(compile_currentness(x, as_of=AS_OF)), canonical_json(compile_currentness(y, as_of=AS_OF)))

    def test_pinned_drift_review_required(self):
        x = fixture(); x["providerSnapshots"][1]["paths"][0]["contentSha256"] = A64
        r = compile_currentness(x, as_of=AS_OF)
        self.assertEqual(r["state"], "REVIEW_REQUIRED")
        self.assertEqual(next(z for z in r["entries"] if z["entryId"] == "service-v2")["entryState"], "REVIEW_REQUIRED")

    def test_follow_default_drift_holds(self):
        x = fixture(); x["providerSnapshots"][0]["paths"][0]["contentSha256"] = A64
        r = compile_currentness(x, as_of=AS_OF)
        self.assertEqual(r["state"], "HOLD")
        self.assertIn("FOLLOW_DEFAULT_BRANCH_SOURCE_DRIFT", {z["code"] for z in r["findings"]})

    def test_missing_source_holds(self):
        x = fixture(); x["providerSnapshots"][0]["paths"] = []
        r = compile_currentness(x, as_of=AS_OF)
        self.assertIn("SOURCE_PATH_MISSING", {z["code"] for z in r["findings"]})

    def test_missing_repository_snapshot_holds(self):
        x = fixture(); x["providerSnapshots"] = x["providerSnapshots"][1:]
        r = compile_currentness(x, as_of=AS_OF)
        self.assertIn("MISSING_REPOSITORY_SNAPSHOT", {z["code"] for z in r["findings"]})

    def test_ambiguous_snapshot_holds(self):
        x = fixture(); extra = copy.deepcopy(x["providerSnapshots"][0]); extra["snapshotId"] = "product-main-two"; x["providerSnapshots"].append(extra)
        r = compile_currentness(x, as_of=AS_OF)
        self.assertIn("AMBIGUOUS_REPOSITORY_SNAPSHOT", {z["code"] for z in r["findings"]})

    def test_stale_snapshot_holds(self):
        x = fixture(); x["providerSnapshots"][0]["capturedAt"] = "2026-09-11T10:00:00Z"
        r = compile_currentness(x, as_of=AS_OF)
        self.assertIn("SNAPSHOT_STALE", {z["code"] for z in r["findings"]})

    def test_future_snapshot_holds(self):
        x = fixture(); x["providerSnapshots"][0]["capturedAt"] = "2026-09-14T10:00:00Z"
        r = compile_currentness(x, as_of=AS_OF)
        self.assertIn("SNAPSHOT_FROM_FUTURE", {z["code"] for z in r["findings"]})

    def test_incomplete_snapshot_holds(self):
        x = fixture(); x["providerSnapshots"][0]["complete"] = False
        r = compile_currentness(x, as_of=AS_OF)
        self.assertIn("SNAPSHOT_INCOMPLETE", {z["code"] for z in r["findings"]})

    def test_bool_int_alias_rejected(self):
        x = fixture(); x["providerSnapshots"][0]["complete"] = 1
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_unknown_top_key_rejected(self):
        x = fixture(); x["surprise"] = True
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_unknown_entry_key_rejected(self):
        x = fixture(); x["catalogs"][0]["entries"][0]["price"] = 29
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_unknown_snapshot_key_rejected(self):
        x = fixture(); x["providerSnapshots"][0]["provider"] = "github"
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_mutable_release_ref_rejected(self):
        x = fixture(); x["catalogs"][0]["entries"][0]["releaseCommitSha"] = "main"
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_uppercase_commit_rejected(self):
        x = fixture(); x["catalogs"][0]["entries"][0]["releaseCommitSha"] = "A" * 40
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_bad_digest_rejected(self):
        x = fixture(); x["catalogs"][0]["entries"][0]["sourceContentSha256"] = "0" * 63
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_path_traversal_rejected(self):
        x = fixture(); x["catalogs"][0]["entries"][0]["sourcePath"] = "src/../secret"
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_backslash_path_rejected(self):
        x = fixture(); x["catalogs"][0]["entries"][0]["sourcePath"] = "src\\product.py"
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_duplicate_snapshot_path_rejected(self):
        x = fixture(); x["providerSnapshots"][0]["paths"].append(copy.deepcopy(x["providerSnapshots"][0]["paths"][0]))
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_duplicate_global_entry_id_rejected(self):
        x = fixture(); x["catalogs"][1]["entries"][0]["entryId"] = "product-v1"
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_conflicting_repo_path_identity_rejected(self):
        x = fixture(); extra = copy.deepcopy(x["catalogs"][0]["entries"][0]); extra["entryId"] = "other-v1"; extra["artifactId"] = "other"; x["catalogs"][0]["entries"].append(extra)
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_same_artifact_repo_path_across_catalog_not_conflict(self):
        x = fixture(); extra = copy.deepcopy(x["catalogs"][0]); extra["catalogId"] = "products-second"; extra["catalogDigestSha256"] = F64; extra["entries"][0]["entryId"] = "product-v1-secondary"; x["catalogs"].append(extra)
        r = compile_currentness(x, as_of=AS_OF)
        self.assertEqual(r["state"], "READY_FOR_HUMAN_CATALOG_CURRENTNESS_REVIEW")

    def test_same_artifact_conflicting_binding_rejected(self):
        x = fixture(); extra = copy.deepcopy(x["catalogs"][0]); extra["catalogId"] = "products-second"; extra["catalogDigestSha256"] = F64; extra["entries"][0]["entryId"] = "product-v1-secondary"; extra["entries"][0]["version"] = "1.0.1"; x["catalogs"].append(extra)
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_unsupported_family_rejected(self):
        x = fixture(); x["catalogs"][0]["family"] = "OTHER"
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_unsupported_policy_rejected(self):
        x = fixture(); x["catalogs"][0]["entries"][0]["currentnessPolicy"] = "AUTO_UPDATE"
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_timezone_less_snapshot_rejected(self):
        x = fixture(); x["providerSnapshots"][0]["capturedAt"] = "2026-09-13T10:00:00"
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_timezone_less_as_of_rejected(self):
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(fixture(), as_of="2026-09-13T10:15:00")

    def test_email_shaped_metadata_rejected(self):
        x = fixture(); x["catalogs"][0]["entries"][0]["artifactId"] = "buyer@example.com"
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_secret_shaped_metadata_rejected(self):
        x = fixture(); x["providerSnapshots"][0]["defaultBranch"] = "token=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        with self.assertRaises(CatalogCurrentnessError): compile_currentness(x, as_of=AS_OF)

    def test_receipt_self_hash_forgery_rejected(self):
        x = fixture(); r = compile_currentness(x, as_of=AS_OF); r["state"] = "HOLD"
        body = dict(r); body.pop("receiptSha256", None); r["receiptSha256"] = hashlib.sha256(canonical_json(body).encode()).hexdigest()
        self.assertFalse(verify_receipt(x, as_of=AS_OF, receipt=r))

    def test_changed_input_rejects_old_receipt(self):
        x = fixture(); r = compile_currentness(x, as_of=AS_OF); x["catalogs"][0]["entries"][0]["version"] = "1.0.1"
        self.assertFalse(verify_receipt(x, as_of=AS_OF, receipt=r))

    def test_changed_trusted_clock_rejects_old_receipt(self):
        x = fixture(); r = compile_currentness(x, as_of=AS_OF)
        self.assertFalse(verify_receipt(x, as_of="2026-09-13T10:15:01Z", receipt=r))

    def test_csv_deterministic(self):
        r = compile_currentness(fixture(), as_of=AS_OF)
        self.assertEqual(render_csv(r), render_csv(r))
        self.assertIn("sourceEvidenceSha256", render_csv(r))

    def test_markdown_authority_boundary(self):
        r = compile_currentness(fixture(), as_of=AS_OF); text = render_markdown(r)
        self.assertIn("human catalog-currentness review only", text)
        self.assertIn("never publishes", text)

    def test_catalog_set_digest_changes_with_catalog_digest(self):
        a = compile_currentness(fixture(), as_of=AS_OF); x = fixture(); x["catalogs"][0]["catalogDigestSha256"] = F64
        b = compile_currentness(x, as_of=AS_OF)
        self.assertNotEqual(a["catalogSetDigest"], b["catalogSetDigest"])

    def test_snapshot_set_digest_changes_with_provider_evidence(self):
        a = compile_currentness(fixture(), as_of=AS_OF); x = fixture(); x["providerSnapshots"][0]["providerEvidenceSha256"] = F64
        b = compile_currentness(x, as_of=AS_OF)
        self.assertNotEqual(a["providerSnapshotSetDigest"], b["providerSnapshotSetDigest"])


if __name__ == "__main__":
    unittest.main()
