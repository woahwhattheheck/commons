from __future__ import annotations

import copy
import json
import unittest
from datetime import timedelta

from .fixture import AS_OF, TOTAL, TOTAL_CLEAN, TOTAL_DEFECT, build_synthetic_case
from .gate import build_gate_artifacts, verify_gate_artifacts
from .model import (
    ACCESSIBILITY,
    ACCESSIBILITY_EVIDENCE_FAILURE,
    DEFECT_CODES,
    HOLD,
    MIGRATION,
    PACKET_READY_FOR_HUMAN_UAT,
    PASS,
    canonical_bytes,
    digest,
)


class MunicipalWebsiteAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows, self.expected = build_synthetic_case()

    def build(self, rows=None):
        return build_gate_artifacts(self.rows if rows is None else rows, as_of=AS_OF)

    def test_exact_acceptance_contract(self) -> None:
        artifacts = self.build()
        summary = artifacts.manifest["summary"]
        self.assertEqual(TOTAL, 168)
        self.assertEqual(TOTAL_CLEAN, 140)
        self.assertEqual(TOTAL_DEFECT, 28)
        self.assertEqual(summary["check_count"], 168)
        self.assertEqual(summary["pass_count"], 140)
        self.assertEqual(summary["hold_count"], 28)
        self.assertEqual(summary["defect_counts"], {code: 4 for code in DEFECT_CODES})
        self.assertEqual(summary["release_state"], HOLD)

    def test_exact_planted_ids_and_codes(self) -> None:
        held = {
            record["evidence_id"]: record["codes"]
            for record in self.build().manifest["records"]
            if record["decision"] == HOLD
        }
        self.assertEqual(len(held), 28)
        for code, ids in self.expected.items():
            self.assertEqual(len(ids), 4)
            for evidence_id in ids:
                self.assertEqual(held[evidence_id], [code])

    def test_zero_planted_defects_pass(self) -> None:
        defective = {eid for ids in self.expected.values() for eid in ids}
        for record in self.build().manifest["records"]:
            if record["evidence_id"] in defective:
                self.assertEqual(record["decision"], HOLD)
            else:
                self.assertEqual(record["decision"], PASS)

    def test_clean_subset_reaches_human_uat_only(self) -> None:
        artifacts = self.build(self.rows[:140])
        self.assertEqual(artifacts.manifest["summary"]["release_state"], PACKET_READY_FOR_HUMAN_UAT)
        authority = artifacts.manifest["authority"]
        self.assertTrue(authority["human_uat_required"])
        self.assertFalse(authority["accessibility_certification_authorized"])
        self.assertFalse(authority["production_release_authorized"])
        self.assertFalse(authority["buyer_acceptance_claimed"])
        self.assertFalse(authority["payment_authority"])
        self.assertFalse(authority["revenue_claimed"])

    def test_reruns_are_byte_identical(self) -> None:
        first = self.build()
        second = self.build()
        self.assertEqual(first.json_bytes, second.json_bytes)
        self.assertEqual(first.markdown_bytes, second.markdown_bytes)
        self.assertEqual(first.manifest_sha256, second.manifest_sha256)
        self.assertEqual(first.markdown_sha256, second.markdown_sha256)

    def test_reversed_input_is_byte_identical(self) -> None:
        forward = self.build()
        reverse = build_gate_artifacts(reversed(self.rows), as_of=AS_OF)
        self.assertEqual(forward.json_bytes, reverse.json_bytes)
        self.assertEqual(forward.markdown_bytes, reverse.markdown_bytes)

    def test_exact_duplicate_collapses(self) -> None:
        duplicated = self.rows + [copy.deepcopy(self.rows[0])]
        artifacts = self.build(duplicated)
        self.assertEqual(artifacts.manifest["summary"]["check_count"], 168)

    def test_conflicting_duplicate_fails_closed(self) -> None:
        rows = copy.deepcopy(self.rows)
        duplicate = copy.deepcopy(rows[0])
        duplicate["resource_id"] = "CHANGED"
        rows.append(duplicate)
        with self.assertRaisesRegex(ValueError, "conflicting duplicate evidence_id"):
            self.build(rows)

    def test_duplicate_sequence_fails_closed(self) -> None:
        rows = copy.deepcopy(self.rows)
        rows[1]["sequence"] = rows[0]["sequence"]
        with self.assertRaisesRegex(ValueError, "duplicate sequence"):
            self.build(rows)

    def test_future_evidence_fails_closed(self) -> None:
        rows = copy.deepcopy(self.rows[:1])
        rows[0]["observed_at"] = (AS_OF + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
        with self.assertRaisesRegex(ValueError, "future evidence"):
            self.build(rows)

    def test_stale_accessibility_evidence_holds(self) -> None:
        row = next(copy.deepcopy(row) for row in self.rows if row["kind"] == ACCESSIBILITY)
        row["sequence"] = 1
        row["evidence_id"] = "STALE-A11Y"
        row["observed_at"] = (AS_OF - timedelta(days=31)).isoformat().replace("+00:00", "Z")
        artifacts = self.build([row])
        self.assertEqual(artifacts.manifest["records"][0]["codes"], [ACCESSIBILITY_EVIDENCE_FAILURE])

    def test_secret_shaped_source_ref_refused(self) -> None:
        rows = copy.deepcopy(self.rows[:1])
        rows[0]["source_ref"] = "synthetic://x?api_key=supersecret"
        with self.assertRaisesRegex(ValueError, "secret-shaped"):
            self.build(rows)

    def test_email_shaped_pii_refused(self) -> None:
        rows = copy.deepcopy(self.rows[:1])
        rows[0]["resource_id"] = "resident@example.org"
        with self.assertRaisesRegex(ValueError, "PII-shaped"):
            self.build(rows)

    def test_unknown_field_refused(self) -> None:
        rows = copy.deepcopy(self.rows[:1])
        rows[0]["customer_name"] = "no"
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            self.build(rows)

    def test_noncanonical_permissions_refused(self) -> None:
        row = next(copy.deepcopy(row) for row in self.rows if row["kind"] == "ROLE_PERMISSION")
        row["sequence"] = 1
        row["evidence_id"] = "ROLE-NONCANON"
        row["details"]["expected_permissions"] = ["CONTENT_VIEW", "CONTENT_EDIT"]
        with self.assertRaisesRegex(ValueError, "unique sorted"):
            self.build([row])

    def test_malformed_sha_refused(self) -> None:
        rows = copy.deepcopy(self.rows[:1])
        rows[0]["source_snapshot_sha256"] = "abc"
        with self.assertRaisesRegex(ValueError, "sha256"):
            self.build(rows)

    def test_migration_digest_defect_isolated(self) -> None:
        row = next(copy.deepcopy(row) for row in self.rows[140:] if row["kind"] == MIGRATION)
        row["sequence"] = 1
        artifacts = self.build([row])
        self.assertEqual(artifacts.manifest["records"][0]["codes"], ["MIGRATION_DIGEST_MISMATCH"])

    def test_verifier_accepts_exact_artifacts(self) -> None:
        artifacts = self.build()
        self.assertTrue(verify_gate_artifacts(
            artifacts.json_bytes,
            artifacts.markdown_bytes,
            manifest_sha256=artifacts.manifest_sha256,
            markdown_sha256=artifacts.markdown_sha256,
        ))

    def test_verifier_rejects_json_tamper(self) -> None:
        artifacts = self.build()
        tampered = bytearray(artifacts.json_bytes)
        tampered[-2] = ord(" ")
        self.assertFalse(verify_gate_artifacts(
            bytes(tampered), artifacts.markdown_bytes,
            manifest_sha256=artifacts.manifest_sha256,
            markdown_sha256=artifacts.markdown_sha256,
        ))

    def test_verifier_rejects_markdown_tamper(self) -> None:
        artifacts = self.build()
        tampered = artifacts.markdown_bytes + b"tamper\n"
        self.assertFalse(verify_gate_artifacts(
            artifacts.json_bytes, tampered,
            manifest_sha256=artifacts.manifest_sha256,
            markdown_sha256=artifacts.markdown_sha256,
        ))

    def test_hash_chain_links_every_record(self) -> None:
        artifacts = self.build()
        previous = "0" * 64
        for record in artifacts.manifest["records"]:
            self.assertEqual(record["previous_record_sha256"], previous)
            previous = record["record_sha256"]
        self.assertEqual(previous, artifacts.manifest["summary"]["last_record_sha256"])

    def test_manifest_is_canonical_json(self) -> None:
        artifacts = self.build()
        decoded = json.loads(artifacts.json_bytes)
        self.assertEqual(canonical_bytes(decoded), artifacts.json_bytes)
        self.assertEqual(digest(artifacts.json_bytes), artifacts.manifest_sha256)


if __name__ == "__main__":
    unittest.main()
