from __future__ import annotations

import copy
import unittest

from revenue.lawrence_youth_ai_training import gate

SHA = "a" * 64
OTHER = "b" * 64
NOW = "2026-09-13T10:00:00Z"
OBSERVED = "2026-09-13T09:00:00Z"
VERIFY_NOW = "2026-09-13T10:30:00Z"


def ready_doc():
    return {"status": "READY", "evidence_sha256": SHA, "observed_at": OBSERVED, "expires_at": None}


def snapshot():
    contract = gate._load_source_contract()
    return {
        "schema": gate.SNAPSHOT_SCHEMA,
        "source_capture": {
            "bid_id": contract["bid_id"],
            "document_url": contract["official_rfp_url"],
            "document_sha256": SHA,
            "captured_at": "2026-09-13T08:00:00Z",
            "updates_checked_at": "2026-09-13T09:30:00Z",
            "addenda_complete": True,
            "questions_answers_complete": False,
        },
        "bidder": {
            "bidder_id": "tokenjunkielabs",
            "organization_type": "CORPORATE",
            "hard_constraints": [],
            "documents": {doc: ready_doc() for doc in contract["mandatory_document_requirements"]},
        },
        "partners": [],
        "capability_evidence": [{
            "evidence_id": "bidder-all",
            "provider_id": "tokenjunkielabs",
            "covers": list(contract["capability_requirements"]),
            "status": "VERIFIED",
            "evidence_sha256": SHA,
            "observed_at": OBSERVED,
            "expires_at": None,
        }],
    }


def evaluate(snap=None, *, now=NOW, expected=SHA):
    return gate.evaluate(snap or snapshot(), evaluated_at=now, expected_rfp_sha256=expected)


class QualificationGateTests(unittest.TestCase):
    def test_prime_ready_on_complete_bidder_evidence(self):
        receipt = evaluate()["receipt"]
        self.assertEqual(receipt["decision"], gate.PRIME_READY)
        self.assertEqual(receipt["missing_documents"], [])
        self.assertEqual(receipt["missing_capabilities"], [])

    def test_collaborative_ready_for_committed_load_bearing_partner(self):
        snap = snapshot()
        cap = gate._load_source_contract()["capability_requirements"][0]
        snap["capability_evidence"][0]["covers"].remove(cap)
        snap["partners"] = [{
            "partner_id": "partner-1", "commitment_status": "COMMITTED",
            "commitment_evidence_sha256": OTHER, "observed_at": OBSERVED, "expires_at": None,
        }]
        snap["capability_evidence"].append({
            "evidence_id": "partner-cap", "provider_id": "partner-1", "covers": [cap],
            "status": "VERIFIED", "evidence_sha256": OTHER, "observed_at": OBSERVED, "expires_at": None,
        })
        self.assertEqual(evaluate(snap)["receipt"]["decision"], gate.COLLABORATIVE_READY)

    def test_prospective_load_bearing_partner_holds(self):
        snap = snapshot()
        cap = gate._load_source_contract()["capability_requirements"][0]
        snap["capability_evidence"][0]["covers"].remove(cap)
        snap["partners"] = [{
            "partner_id": "prospect", "commitment_status": "PROSPECTIVE",
            "commitment_evidence_sha256": None, "observed_at": OBSERVED, "expires_at": None,
        }]
        snap["capability_evidence"].append({
            "evidence_id": "prospect-cap", "provider_id": "prospect", "covers": [cap],
            "status": "VERIFIED", "evidence_sha256": OTHER, "observed_at": OBSERVED, "expires_at": None,
        })
        receipt = evaluate(snap)["receipt"]
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("PARTNER_NOT_COMMITTED:prospect", receipt["holds"])

    def test_non_load_bearing_prospective_partner_does_not_hold(self):
        snap = snapshot()
        cap = gate._load_source_contract()["capability_requirements"][0]
        snap["partners"] = [{
            "partner_id": "optional", "commitment_status": "PROSPECTIVE",
            "commitment_evidence_sha256": None, "observed_at": OBSERVED, "expires_at": None,
        }]
        snap["capability_evidence"].append({
            "evidence_id": "optional-cap", "provider_id": "optional", "covers": [cap],
            "status": "VERIFIED", "evidence_sha256": OTHER, "observed_at": OBSERVED, "expires_at": None,
        })
        self.assertEqual(evaluate(snap)["receipt"]["decision"], gate.PRIME_READY)

    def test_qa_confirmation_required_after_posting_deadline(self):
        snap = snapshot()
        snap["source_capture"]["captured_at"] = "2026-09-29T19:30:00Z"
        snap["source_capture"]["updates_checked_at"] = "2026-09-29T20:00:00Z"
        receipt = evaluate(snap, now="2026-09-29T20:01:00Z")["receipt"]
        self.assertIn("RFP_QA_NOT_CONFIRMED_COMPLETE", receipt["holds"])

    def test_qa_confirmation_clears_hold(self):
        snap = snapshot()
        snap["source_capture"]["captured_at"] = "2026-09-29T19:30:00Z"
        snap["source_capture"]["updates_checked_at"] = "2026-09-29T20:00:00Z"
        snap["source_capture"]["questions_answers_complete"] = True
        self.assertEqual(evaluate(snap, now="2026-09-29T20:01:00Z")["receipt"]["decision"], gate.PRIME_READY)

    def test_missing_required_document_holds(self):
        snap = snapshot()
        doc = gate._load_source_contract()["mandatory_document_requirements"][0]
        snap["bidder"]["documents"][doc] = {
            "status": "MISSING", "evidence_sha256": None, "observed_at": OBSERVED, "expires_at": None,
        }
        self.assertIn(f"DOCUMENT_NOT_READY:{doc}", evaluate(snap)["receipt"]["holds"])

    def test_document_set_must_be_exact(self):
        snap = snapshot()
        snap["bidder"]["documents"].pop(next(iter(snap["bidder"]["documents"])))
        with self.assertRaises(gate.QualificationInputError):
            evaluate(snap)

    def test_missing_capability_holds(self):
        snap = snapshot()
        cap = gate._load_source_contract()["capability_requirements"][0]
        snap["capability_evidence"][0]["covers"].remove(cap)
        self.assertIn(f"CAPABILITY_NOT_COVERED:{cap}", evaluate(snap)["receipt"]["holds"])

    def test_undeclared_provider_rejected(self):
        snap = snapshot()
        snap["capability_evidence"][0]["provider_id"] = "mystery"
        with self.assertRaises(gate.QualificationInputError):
            evaluate(snap)

    def test_out_of_band_rfp_hash_mismatch_holds(self):
        self.assertIn("RFP_SHA256_MISMATCH", evaluate(expected=OTHER)["receipt"]["holds"])

    def test_stale_update_check_holds(self):
        snap = snapshot()
        snap["source_capture"]["captured_at"] = "2026-09-11T08:00:00Z"
        snap["source_capture"]["updates_checked_at"] = "2026-09-12T08:00:00Z"
        self.assertIn("RFP_UPDATE_CHECK_STALE", evaluate(snap)["receipt"]["holds"])

    def test_addenda_incomplete_holds(self):
        snap = snapshot()
        snap["source_capture"]["addenda_complete"] = False
        self.assertIn("RFP_UPDATES_NOT_CONFIRMED_COMPLETE", evaluate(snap)["receipt"]["holds"])

    def test_hard_constraint_is_no_bid(self):
        snap = snapshot()
        snap["bidder"]["hard_constraints"] = ["CANNOT_DELIVER_12_MONTH_FOLLOWUP"]
        self.assertEqual(evaluate(snap)["receipt"]["decision"], gate.NO_BID)

    def test_deadline_exact_boundary_is_no_bid(self):
        self.assertEqual(evaluate(now="2026-10-01T11:00:00-04:00")["receipt"]["decision"], gate.NO_BID)

    def test_external_authorities_are_always_false(self):
        receipt = evaluate()["receipt"]
        for field in gate._AUTHORITY_FALSE_FIELDS:
            self.assertIs(receipt[field], False)

    def test_fresh_receipt_verifies(self):
        snap = snapshot()
        result = evaluate(snap)
        self.assertTrue(gate.verify(result, snapshot=snap, expected_rfp_sha256=SHA, verified_at=VERIFY_NOW))

    def test_tampered_receipt_fails(self):
        snap = snapshot()
        result = evaluate(snap)
        result["receipt"]["decision"] = gate.COLLABORATIVE_READY
        self.assertFalse(gate.verify(result, snapshot=snap, expected_rfp_sha256=SHA, verified_at=VERIFY_NOW))

    def test_different_trusted_rfp_hash_fails_verifier(self):
        snap = snapshot()
        result = evaluate(snap)
        self.assertFalse(gate.verify(result, snapshot=snap, expected_rfp_sha256=OTHER, verified_at=VERIFY_NOW))

    def test_receipt_replay_expires(self):
        snap = snapshot()
        result = evaluate(snap)
        self.assertFalse(gate.verify(result, snapshot=snap, expected_rfp_sha256=SHA, verified_at="2026-09-13T11:00:01Z"))

    def test_snapshot_mutation_fails_verifier(self):
        snap = snapshot()
        result = evaluate(snap)
        changed = copy.deepcopy(snap)
        changed["bidder"]["organization_type"] = "NON_CORPORATE"
        self.assertFalse(gate.verify(result, snapshot=changed, expected_rfp_sha256=SHA, verified_at=VERIFY_NOW))

    def test_source_contract_digest_is_bound(self):
        contract = gate._load_source_contract()
        self.assertEqual(gate.digest(contract), gate.EXPECTED_SOURCE_CONTRACT_SHA256)


if __name__ == "__main__":
    unittest.main()
