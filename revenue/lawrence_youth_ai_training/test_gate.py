from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from revenue.lawrence_youth_ai_training import gate

SHA = "a" * 64
OTHER_SHA = "b" * 64
NOW = "2026-09-13T10:00:00Z"
VERIFY_NOW = "2026-09-13T10:30:00Z"
OBSERVED = "2026-09-13T09:00:00Z"

DOCS = [
    "price_contents_checklist",
    "signed_price_cover_sheet",
    "minimum_qualifying_document",
    "signatory_authorization",
    "debarment_certification",
    "drug_free_workplace_certification",
    "non_collusion_certificate",
    "audit_assurance_certification",
    "eeo_aa_nondiscrimination_commitment",
    "certificate_good_standing",
    "completed_budget",
    "completed_budget_narrative",
]
CAPS = [
    "recruitment_outreach",
    "assessment_enrollment",
    "intensive_case_management",
    "ai_training_delivery",
    "career_readiness",
    "work_based_learning",
    "industry_credentials",
    "job_placement",
    "twelve_month_followup",
    "employer_engagement",
    "participant_records_reporting",
    "fiscal_performance_reporting",
]


def ready_document():
    return {
        "status": "READY",
        "evidence_sha256": SHA,
        "observed_at": OBSERVED,
        "expires_at": None,
    }


def base_snapshot():
    return {
        "schema": gate.SNAPSHOT_SCHEMA,
        "source_capture": {
            "bid_id": "BD-27-1412-LAW26-LAW85-132652",
            "document_url": (
                "https://www.masshiremvwb.org/wp-content/uploads/"
                "FY27-COL-Youth-AI-Workforce-Training-RFP-8.19.26.pdf"
            ),
            "document_sha256": SHA,
            "captured_at": "2026-09-13T08:00:00Z",
            "updates_checked_at": "2026-09-13T09:30:00Z",
            "addenda_complete": True,
        },
        "bidder": {
            "bidder_id": "tokenjunkielabs",
            "organization_type": "CORPORATE",
            "hard_constraints": [],
            "documents": {doc: ready_document() for doc in DOCS},
        },
        "partners": [],
        "capability_evidence": [
            {
                "evidence_id": "bidder-all",
                "provider_id": "tokenjunkielabs",
                "covers": list(CAPS),
                "status": "VERIFIED",
                "evidence_sha256": SHA,
                "observed_at": OBSERVED,
                "expires_at": None,
            }
        ],
    }


def evaluate(snapshot=None, *, now=NOW, expected=SHA):
    return gate.evaluate(snapshot or base_snapshot(), evaluated_at=now, expected_rfp_sha256=expected)


class LawrenceQualificationTests(unittest.TestCase):
    def test_prime_ready_requires_complete_bidder_coverage(self):
        result = evaluate()
        self.assertEqual(result["receipt"]["decision"], gate.PRIME_READY)
        self.assertEqual(result["receipt"]["missing_capabilities"], [])
        self.assertEqual(result["receipt"]["missing_documents"], [])
        self.assertEqual(result["receipt"]["partner_coverage"], {})

    def test_collaborative_ready_when_committed_partner_is_load_bearing(self):
        snap = base_snapshot()
        snap["capability_evidence"][0]["covers"] = [c for c in CAPS if c != "employer_engagement"]
        snap["partners"] = [{
            "partner_id": "lawrence-cbo",
            "commitment_status": "COMMITTED",
            "commitment_evidence_sha256": OTHER_SHA,
            "observed_at": OBSERVED,
            "expires_at": None,
        }]
        snap["capability_evidence"].append({
            "evidence_id": "partner-employer",
            "provider_id": "lawrence-cbo",
            "covers": ["employer_engagement"],
            "status": "VERIFIED",
            "evidence_sha256": OTHER_SHA,
            "observed_at": OBSERVED,
            "expires_at": None,
        })
        receipt = evaluate(snap)["receipt"]
        self.assertEqual(receipt["decision"], gate.COLLABORATIVE_READY)
        self.assertEqual(receipt["partner_coverage"], {"lawrence-cbo": ["employer_engagement"]})

    def test_prospective_partner_does_not_authorize_coverage(self):
        snap = base_snapshot()
        snap["capability_evidence"][0]["covers"] = [c for c in CAPS if c != "job_placement"]
        snap["partners"] = [{
            "partner_id": "placement-partner",
            "commitment_status": "PROSPECTIVE",
            "commitment_evidence_sha256": None,
            "observed_at": OBSERVED,
            "expires_at": None,
        }]
        snap["capability_evidence"].append({
            "evidence_id": "placement",
            "provider_id": "placement-partner",
            "covers": ["job_placement"],
            "status": "VERIFIED",
            "evidence_sha256": OTHER_SHA,
            "observed_at": OBSERVED,
            "expires_at": None,
        })
        receipt = evaluate(snap)["receipt"]
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("PARTNER_NOT_COMMITTED:placement-partner", receipt["holds"])
        self.assertIn("CAPABILITY_NOT_COVERED:job_placement", receipt["holds"])

    def test_missing_document_holds(self):
        snap = base_snapshot()
        snap["bidder"]["documents"]["certificate_good_standing"] = {
            "status": "MISSING",
            "evidence_sha256": None,
            "observed_at": OBSERVED,
            "expires_at": None,
        }
        receipt = evaluate(snap)["receipt"]
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("DOCUMENT_NOT_READY:certificate_good_standing", receipt["holds"])

    def test_pending_document_holds(self):
        snap = base_snapshot()
        snap["bidder"]["documents"]["audit_assurance_certification"] = {
            "status": "PENDING",
            "evidence_sha256": None,
            "observed_at": OBSERVED,
            "expires_at": None,
        }
        self.assertEqual(evaluate(snap)["receipt"]["decision"], gate.HOLD)

    def test_expired_document_holds(self):
        snap = base_snapshot()
        snap["bidder"]["documents"]["certificate_good_standing"]["expires_at"] = "2026-09-13T09:30:00Z"
        receipt = evaluate(snap)["receipt"]
        self.assertEqual(receipt["document_states"]["certificate_good_standing"], "EXPIRED")
        self.assertEqual(receipt["decision"], gate.HOLD)

    def test_missing_exact_document_key_rejected(self):
        snap = base_snapshot()
        del snap["bidder"]["documents"]["completed_budget"]
        with self.assertRaises(gate.QualificationInputError):
            evaluate(snap)

    def test_unknown_document_key_rejected(self):
        snap = base_snapshot()
        snap["bidder"]["documents"]["invented"] = ready_document()
        with self.assertRaises(gate.QualificationInputError):
            evaluate(snap)

    def test_uncovered_capability_holds(self):
        snap = base_snapshot()
        snap["capability_evidence"][0]["covers"] = [c for c in CAPS if c != "twelve_month_followup"]
        receipt = evaluate(snap)["receipt"]
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("twelve_month_followup", receipt["missing_capabilities"])

    def test_expired_capability_evidence_holds_and_names_expiry(self):
        snap = base_snapshot()
        snap["capability_evidence"][0]["expires_at"] = "2026-09-13T09:30:00Z"
        receipt = evaluate(snap)["receipt"]
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("CAPABILITY_EVIDENCE_EXPIRED:ai_training_delivery", receipt["holds"])

    def test_pending_capability_does_not_count(self):
        snap = base_snapshot()
        snap["capability_evidence"][0]["status"] = "PENDING"
        snap["capability_evidence"][0]["evidence_sha256"] = None
        self.assertEqual(evaluate(snap)["receipt"]["decision"], gate.HOLD)

    def test_unknown_capability_rejected(self):
        snap = base_snapshot()
        snap["capability_evidence"][0]["covers"].append("invented_requirement")
        with self.assertRaises(gate.QualificationInputError):
            evaluate(snap)

    def test_undeclared_provider_rejected(self):
        snap = base_snapshot()
        snap["capability_evidence"][0]["provider_id"] = "mystery"
        with self.assertRaises(gate.QualificationInputError):
            evaluate(snap)

    def test_duplicate_evidence_id_rejected(self):
        snap = base_snapshot()
        snap["capability_evidence"].append(copy.deepcopy(snap["capability_evidence"][0]))
        with self.assertRaises(gate.QualificationInputError):
            evaluate(snap)

    def test_duplicate_partner_rejected(self):
        snap = base_snapshot()
        p = {
            "partner_id": "p1",
            "commitment_status": "COMMITTED",
            "commitment_evidence_sha256": OTHER_SHA,
            "observed_at": OBSERVED,
            "expires_at": None,
        }
        snap["partners"] = [copy.deepcopy(p), copy.deepcopy(p)]
        with self.assertRaises(gate.QualificationInputError):
            evaluate(snap)

    def test_expired_partner_commitment_cannot_cover(self):
        snap = base_snapshot()
        snap["capability_evidence"][0]["covers"] = [c for c in CAPS if c != "job_placement"]
        snap["partners"] = [{
            "partner_id": "p1",
            "commitment_status": "COMMITTED",
            "commitment_evidence_sha256": OTHER_SHA,
            "observed_at": "2026-09-12T00:00:00Z",
            "expires_at": "2026-09-13T09:00:00Z",
        }]
        snap["capability_evidence"].append({
            "evidence_id": "p1-placement",
            "provider_id": "p1",
            "covers": ["job_placement"],
            "status": "VERIFIED",
            "evidence_sha256": OTHER_SHA,
            "observed_at": OBSERVED,
            "expires_at": None,
        })
        receipt = evaluate(snap)["receipt"]
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("PARTNER_NOT_COMMITTED:p1", receipt["holds"])

    def test_out_of_band_rfp_hash_mismatch_holds(self):
        receipt = evaluate(expected=OTHER_SHA)["receipt"]
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("RFP_SHA256_MISMATCH", receipt["holds"])

    def test_addenda_not_confirmed_holds(self):
        snap = base_snapshot()
        snap["source_capture"]["addenda_complete"] = False
        self.assertIn("RFP_UPDATES_NOT_CONFIRMED_COMPLETE", evaluate(snap)["receipt"]["holds"])

    def test_stale_update_check_holds(self):
        snap = base_snapshot()
        snap["source_capture"]["captured_at"] = "2026-09-11T08:00:00Z"
        snap["source_capture"]["updates_checked_at"] = "2026-09-12T08:00:00Z"
        receipt = evaluate(snap)["receipt"]
        self.assertIn("RFP_UPDATE_CHECK_STALE", receipt["holds"])

    def test_future_source_capture_rejected(self):
        snap = base_snapshot()
        snap["source_capture"]["updates_checked_at"] = "2026-09-13T11:00:00Z"
        with self.assertRaises(gate.QualificationInputError):
            evaluate(snap)

    def test_wrong_bid_id_rejected(self):
        snap = base_snapshot()
        snap["source_capture"]["bid_id"] = "other"
        with self.assertRaises(gate.QualificationInputError):
            evaluate(snap)

    def test_wrong_url_rejected(self):
        snap = base_snapshot()
        snap["source_capture"]["document_url"] = "https://example.test/rfp.pdf"
        with self.assertRaises(gate.QualificationInputError):
            evaluate(snap)

    def test_naive_time_rejected(self):
        with self.assertRaises(gate.QualificationInputError):
            evaluate(now="2026-09-13T10:00:00")

    def test_explicit_offset_time_is_deterministic(self):
        a = evaluate(now="2026-09-13T10:00:00Z")
        b = evaluate(now="2026-09-13T06:00:00-04:00")
        self.assertEqual(a["receipt"]["decision"], b["receipt"]["decision"])
        self.assertNotEqual(a["receipt"]["receipt_sha256"], b["receipt"]["receipt_sha256"])

    def test_hard_constraint_is_no_bid(self):
        snap = base_snapshot()
        snap["bidder"]["hard_constraints"] = ["CANNOT_DELIVER_12_MONTH_FOLLOWUP"]
        receipt = evaluate(snap)["receipt"]
        self.assertEqual(receipt["decision"], gate.NO_BID)
        self.assertEqual(receipt["hard_constraints"], ["CANNOT_DELIVER_12_MONTH_FOLLOWUP"])

    def test_deadline_passed_is_no_bid(self):
        receipt = evaluate(now="2026-10-01T15:00:00Z")["receipt"]
        self.assertEqual(receipt["decision"], gate.NO_BID)
        self.assertIn("PROPOSAL_DEADLINE_PASSED", receipt["hard_constraints"])

    def test_deadline_exact_boundary_is_no_bid(self):
        receipt = evaluate(now="2026-10-01T11:00:00-04:00")["receipt"]
        self.assertEqual(receipt["decision"], gate.NO_BID)

    def test_authority_is_always_false_for_external_actions(self):
        receipt = evaluate()["receipt"]
        for field in gate._AUTHORITY_FALSE_FIELDS:
            self.assertIs(receipt[field], False)

    def test_receipt_hash_tamper_fails_verifier(self):
        snap = base_snapshot()
        result = evaluate(snap)
        result["receipt"]["decision"] = gate.COLLABORATIVE_READY
        self.assertFalse(gate.verify(
            result, snapshot=snap, expected_rfp_sha256=SHA, verified_at=VERIFY_NOW
        ))

    def test_fresh_receipt_verifies(self):
        snap = base_snapshot()
        result = evaluate(snap)
        self.assertTrue(gate.verify(
            result, snapshot=snap, expected_rfp_sha256=SHA, verified_at=VERIFY_NOW
        ))

    def test_verifier_rejects_different_trusted_rfp_hash(self):
        snap = base_snapshot()
        result = evaluate(snap)
        self.assertFalse(gate.verify(
            result, snapshot=snap, expected_rfp_sha256=OTHER_SHA, verified_at=VERIFY_NOW
        ))

    def test_verifier_rejects_replay_after_receipt_max_age(self):
        snap = base_snapshot()
        result = evaluate(snap)
        self.assertFalse(gate.verify(
            result,
            snapshot=snap,
            expected_rfp_sha256=SHA,
            verified_at="2026-09-13T11:00:01Z",
        ))

    def test_verifier_rejects_after_submission_deadline(self):
        snap = base_snapshot()
        result = evaluate(snap)
        self.assertFalse(gate.verify(
            result,
            snapshot=snap,
            expected_rfp_sha256=SHA,
            verified_at="2026-10-01T15:00:00Z",
        ))

    def test_verifier_rejects_snapshot_mutation(self):
        snap = base_snapshot()
        result = evaluate(snap)
        changed = copy.deepcopy(snap)
        changed["bidder"]["organization_type"] = "NON_CORPORATE"
        self.assertFalse(gate.verify(
            result, snapshot=changed, expected_rfp_sha256=SHA, verified_at=VERIFY_NOW
        ))

    def test_evidence_order_does_not_change_receipt(self):
        snap = base_snapshot()
        first = snap["capability_evidence"][0]
        first["covers"] = CAPS[:6]
        second = {
            "evidence_id": "second",
            "provider_id": "tokenjunkielabs",
            "covers": CAPS[6:],
            "status": "VERIFIED",
            "evidence_sha256": OTHER_SHA,
            "observed_at": OBSERVED,
            "expires_at": None,
        }
        snap["capability_evidence"].append(second)
        a = evaluate(snap)
        snap["capability_evidence"].reverse()
        b = evaluate(snap)
        self.assertEqual(a["receipt"]["decision"], b["receipt"]["decision"])
        self.assertEqual(a["receipt"]["bidder_coverage"], b["receipt"]["bidder_coverage"])

    def test_bool_cannot_replace_addenda_boolean_string_or_status(self):
        snap = base_snapshot()
        snap["source_capture"]["addenda_complete"] = 1
        with self.assertRaises(gate.QualificationInputError):
            evaluate(snap)

    def test_non_ready_document_cannot_smuggle_sha(self):
        snap = base_snapshot()
        snap["bidder"]["documents"]["completed_budget"]["status"] = "MISSING"
        with self.assertRaises(gate.QualificationInputError):
            evaluate(snap)

    def test_source_contract_tamper_rejected(self):
        real_path = Path(gate.__file__).with_name("source_contract.json")
        original = real_path.read_text()
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "source_contract.json"
            data = json.loads(original)
            data["anticipated_total_award_usd"] = 999999
            fake.write_text(json.dumps(data))
            class FakePath(type(real_path)):
                pass
        with patch("pathlib.Path.read_bytes", return_value=json.dumps(
            {**json.loads(original), "anticipated_total_award_usd": 999999}
        ).encode()):
            with self.assertRaises(gate.QualificationInputError):
                gate._load_source_contract()


if __name__ == "__main__":
    unittest.main()
