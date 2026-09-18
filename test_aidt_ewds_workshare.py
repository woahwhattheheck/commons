from __future__ import annotations

import copy
import hashlib
import json
import unittest

from revenue.aidt_ewds_workshare.core import (
    PRIME_GATE_EVIDENCE,
    REQUIRED_WORKSHARE_EVIDENCE,
    REQUIREMENTS,
    SOLICITATION_ID,
    WorkshareError,
    compile_readiness,
    compile_sync_receipt,
    reconcile_migration,
    verify_migration_receipt,
    verify_readiness,
    verify_sync_receipt,
)


def h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record(record_id: str, payload: str) -> dict[str, str]:
    return {"record_id": record_id, "record_sha256": h(payload)}


def sync_event() -> dict[str, str]:
    return {
        "source_system": "salesforce",
        "target_system": "adobe_lms",
        "event_id": "evt-001",
        "entity_ref": "applicant-001",
        "operation": "enroll",
        "payload_sha256": h("enrollment-v1"),
    }


def sync_observed(*, digest: str | None = None, accepted: bool = True) -> dict[str, object]:
    return {
        "accepted": accepted,
        "target_ref": "adobe-enrollment-42",
        "target_payload_sha256": digest or h("enrollment-v1"),
    }


class AIDTEWDSWorkshareTests(unittest.TestCase):
    def test_exact_migration_reconciles(self):
        rows = [record("a-1", "alpha"), record("a-2", "beta")]
        receipt = reconcile_migration(rows, list(reversed(rows)))
        self.assertEqual(receipt["decision"], "MIGRATION_RECONCILED")
        self.assertFalse(receipt["contains_live_pii"])
        self.assertFalse(receipt["external_submission_authorized"])
        self.assertTrue(verify_migration_receipt(receipt))

    def test_duplicate_record_id_rejected(self):
        rows = [record("a-1", "alpha"), record("a-1", "beta")]
        with self.assertRaisesRegex(WorkshareError, "duplicate record_id"):
            reconcile_migration(rows, [])

    def test_migration_mismatch_holds(self):
        source = [record("a-1", "alpha"), record("a-2", "beta")]
        target = [record("a-1", "changed"), record("a-3", "gamma")]
        receipt = reconcile_migration(source, target)
        self.assertEqual(receipt["decision"], "HOLD_MIGRATION_RECONCILIATION")
        self.assertEqual(receipt["missing_record_ids"], ["a-2"])
        self.assertEqual(receipt["extra_record_ids"], ["a-3"])
        self.assertEqual(receipt["mismatched_record_ids"], ["a-1"])
        self.assertTrue(verify_migration_receipt(receipt))

    def test_migration_receipt_decision_cannot_be_flipped(self):
        receipt = reconcile_migration([record("a-1", "alpha")], [])
        hostile = copy.deepcopy(receipt)
        hostile["decision"] = "MIGRATION_RECONCILED"
        material = dict(hostile)
        material.pop("receipt_sha256")
        hostile["receipt_sha256"] = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        ).hexdigest()
        with self.assertRaisesRegex(WorkshareError, "decision inconsistent"):
            verify_migration_receipt(hostile)

    def test_sync_exact_acceptance_is_deterministic(self):
        first = compile_sync_receipt(sync_event(), sync_observed())
        second = compile_sync_receipt(sync_event(), sync_observed())
        self.assertEqual(first, second)
        self.assertEqual(first["decision"], "SYNC_ACCEPTED_EXACT")
        self.assertFalse(first["transport_performed_by_compiler"])
        self.assertFalse(first["external_submission_authorized"])
        self.assertTrue(verify_sync_receipt(first))

    def test_sync_payload_drift_holds(self):
        receipt = compile_sync_receipt(sync_event(), sync_observed(digest=h("tampered")))
        self.assertEqual(receipt["decision"], "HOLD_SYNC_ACCEPTANCE")
        self.assertTrue(verify_sync_receipt(receipt))

    def test_sync_unknown_operation_rejected(self):
        event = sync_event()
        event["operation"] = "delete_everything"
        with self.assertRaisesRegex(WorkshareError, "unsupported operation"):
            compile_sync_receipt(event, sync_observed())

    def test_sync_unknown_field_rejected(self):
        event = sync_event()
        event["recipient_email"] = "nobody@example.invalid"
        with self.assertRaisesRegex(WorkshareError, "exact fields required"):
            compile_sync_receipt(event, sync_observed())

    def test_readiness_requires_every_internal_evidence_class(self):
        migration = reconcile_migration([record("a-1", "alpha")], [record("a-1", "alpha")])
        sync = compile_sync_receipt(sync_event(), sync_observed())
        evidence = {key: h(key) for key in REQUIRED_WORKSHARE_EVIDENCE[:-1]}
        receipt = compile_readiness(evidence, [migration], [sync])
        self.assertEqual(receipt["state"], "HOLD_WORKSHARE_INCOMPLETE")
        self.assertEqual(receipt["missing_workshare_evidence"], ["economics_stop_ledger"])
        self.assertTrue(verify_readiness(receipt))

    def test_readiness_requires_verified_green_child_receipts(self):
        evidence = {key: h(key) for key in REQUIRED_WORKSHARE_EVIDENCE}
        migration = reconcile_migration([record("a-1", "alpha")], [record("a-1", "changed")])
        sync = compile_sync_receipt(sync_event(), sync_observed())
        receipt = compile_readiness(evidence, [migration], [sync])
        self.assertEqual(receipt["state"], "HOLD_WORKSHARE_INCOMPLETE")
        self.assertTrue(verify_readiness(receipt))

    def test_ready_for_prime_review_never_mints_prime_or_external_authority(self):
        evidence = {key: h(key) for key in REQUIRED_WORKSHARE_EVIDENCE}
        migration = reconcile_migration([record("a-1", "alpha")], [record("a-1", "alpha")])
        sync = compile_sync_receipt(sync_event(), sync_observed())
        receipt = compile_readiness(evidence, [migration], [sync])
        self.assertEqual(receipt["state"], "WORKSHARE_READY_FOR_PRIME_REVIEW")
        self.assertEqual(receipt["solicitation_id"], SOLICITATION_ID)
        self.assertEqual(receipt["prime_gate_evidence_required"], list(PRIME_GATE_EVIDENCE))
        for field in (
            "prime_qualified",
            "alabama_buys_registered",
            "external_outbound_authorized",
            "proposal_submission_authorized",
            "buyer_acceptance_claim_authorized",
            "award_claim_authorized",
            "payment_claim_authorized",
            "revenue_claim_authorized",
        ):
            self.assertFalse(receipt[field], field)
        self.assertTrue(receipt["controlling_source_recheck_required"])
        self.assertTrue(verify_readiness(receipt))

    def test_readiness_rejects_caller_invented_prime_gate(self):
        evidence = {key: h(key) for key in REQUIRED_WORKSHARE_EVIDENCE}
        evidence["prime_qualified"] = h("self-attested")
        with self.assertRaisesRegex(WorkshareError, "unknown keys"):
            compile_readiness(evidence, [], [])

    def test_nested_receipt_tamper_cannot_be_hidden_by_rehashing_parent(self):
        evidence = {key: h(key) for key in REQUIRED_WORKSHARE_EVIDENCE}
        migration = reconcile_migration([record("a-1", "alpha")], [record("a-1", "alpha")])
        sync = compile_sync_receipt(sync_event(), sync_observed())
        receipt = compile_readiness(evidence, [migration], [sync])
        hostile = copy.deepcopy(receipt)
        hostile["sync_receipts"][0]["observed_target_payload_sha256"] = h("forged")
        parent = dict(hostile)
        parent.pop("receipt_sha256")
        hostile["receipt_sha256"] = hashlib.sha256(
            json.dumps(parent, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        ).hexdigest()
        with self.assertRaisesRegex(WorkshareError, "semantic or digest mismatch"):
            verify_readiness(hostile)

    def test_requirement_ledger_covers_owned_integration_and_migration_scope(self):
        ids = {row[0] for row in REQUIREMENTS}
        self.assertIn("historical_data_import", ids)
        self.assertIn("salesforce_interoperability", ids)
        self.assertIn("adobe_lms_sync", ids)
        self.assertIn("workflow_automation", ids)


if __name__ == "__main__":
    unittest.main()
