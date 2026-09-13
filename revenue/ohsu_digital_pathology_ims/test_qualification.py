# SPDX-License-Identifier: Apache-2.0
import copy
import unittest

from qualification import (
    AUTHORITY, OPPORTUNITY_ID, PUBLIC_CAPABILITIES, PUBLIC_SOURCE,
    QualificationError, evaluate, verify,
)

NOW = "2026-09-13T09:30:00Z"
HEX_A = "a" * 64
HEX_B = "b" * 64


def base_payload():
    return {
        "opportunity": {
            "id": OPPORTUNITY_ID,
            "public_source": PUBLIC_SOURCE,
            "issue_date": "2026-09-11",
            "due_date": "2026-10-11",
        },
        "captured_at": "2026-09-13T09:00:00Z",
        "full_rfp": {"captured": False},
        "minimum_qualifications": [],
        "public_capability_claims": list(PUBLIC_CAPABILITIES),
        "evidence": [],
    }


def qualified_payload():
    p = base_payload()
    p["full_rfp"] = {"captured": True, "source": "supplier-package://rfp-2027-2012", "sha256": HEX_A}
    p["minimum_qualifications"] = [
        {"id": "mq-1", "mandatory": True, "text": "Synthetic captured minimum one"},
        {"id": "mq-2", "mandatory": True, "text": "Synthetic captured minimum two"},
    ]
    p["evidence"] = [
        {"requirement_id": "mq-1", "result": "PASS", "reference": "artifact://one", "sha256": HEX_A},
        {"requirement_id": "mq-2", "result": "PASS", "reference": "artifact://two", "sha256": HEX_B},
    ]
    return p


class QualificationTests(unittest.TestCase):
    def test_public_listing_alone_holds(self):
        r = evaluate(base_payload(), evaluated_at=NOW)
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("FULL_RFP_PACKAGE_NOT_CAPTURED", r["holds"])
        self.assertIn("MINIMUM_QUALIFICATIONS_NOT_CAPTURED", r["holds"])

    def test_complete_captured_minimums_ready_for_internal_review_only(self):
        r = evaluate(qualified_payload(), evaluated_at=NOW)
        self.assertEqual(r["decision"], "READY_FOR_INTERNAL_BID_REVIEW")
        self.assertEqual(r["authority"], AUTHORITY)
        self.assertFalse(r["outreach_authorized"])
        self.assertFalse(r["intent_to_bid_authorized"])
        self.assertFalse(r["proposal_submission_authorized"])
        self.assertFalse(r["clinical_use_authorized"])

    def test_missing_mandatory_proof_holds(self):
        p = qualified_payload(); p["evidence"].pop()
        r = evaluate(p, evaluated_at=NOW)
        self.assertIn("MANDATORY_EVIDENCE_MISSING", r["holds"])
        self.assertEqual(r["missing_mandatory_evidence"], ["mq-2"])

    def test_failed_minimum_holds(self):
        p = qualified_payload(); p["evidence"][1]["result"] = "FAIL"
        r = evaluate(p, evaluated_at=NOW)
        self.assertIn("MANDATORY_QUALIFICATION_FAILED", r["holds"])
        self.assertEqual(r["failed_mandatory_qualifications"], ["mq-2"])

    def test_unknown_public_claim_rejected(self):
        p = qualified_payload(); p["public_capability_claims"].append("made_up_capability")
        with self.assertRaisesRegex(QualificationError, "unknown public capability"):
            evaluate(p, evaluated_at=NOW)

    def test_incomplete_public_matrix_holds(self):
        p = qualified_payload(); p["public_capability_claims"].pop()
        r = evaluate(p, evaluated_at=NOW)
        self.assertIn("PUBLIC_CAPABILITY_MATRIX_INCOMPLETE", r["holds"])

    def test_wrong_public_source_rejected(self):
        p = qualified_payload(); p["opportunity"]["public_source"] = "https://example.invalid"
        with self.assertRaisesRegex(QualificationError, "wrong public source"):
            evaluate(p, evaluated_at=NOW)

    def test_wrong_dates_rejected(self):
        p = qualified_payload(); p["opportunity"]["due_date"] = "2026-10-12"
        with self.assertRaisesRegex(QualificationError, "date mismatch"):
            evaluate(p, evaluated_at=NOW)

    def test_future_capture_rejected(self):
        p = qualified_payload(); p["captured_at"] = "2026-09-13T10:00:00Z"
        with self.assertRaisesRegex(QualificationError, "future"):
            evaluate(p, evaluated_at=NOW)

    def test_deadline_passed_holds(self):
        r = evaluate(qualified_payload(), evaluated_at="2026-10-12T00:00:00Z")
        self.assertIn("OPPORTUNITY_DEADLINE_PASSED", r["holds"])

    def test_duplicate_minimum_id_rejected(self):
        p = qualified_payload(); p["minimum_qualifications"].append(copy.deepcopy(p["minimum_qualifications"][0]))
        with self.assertRaisesRegex(QualificationError, "duplicate id"):
            evaluate(p, evaluated_at=NOW)

    def test_duplicate_evidence_id_rejected(self):
        p = qualified_payload(); p["evidence"].append(copy.deepcopy(p["evidence"][0]))
        with self.assertRaisesRegex(QualificationError, "duplicate requirement_id"):
            evaluate(p, evaluated_at=NOW)

    def test_non_boolean_mandatory_rejected(self):
        p = qualified_payload(); p["minimum_qualifications"][0]["mandatory"] = 1
        with self.assertRaisesRegex(QualificationError, "mandatory must be boolean"):
            evaluate(p, evaluated_at=NOW)

    def test_invalid_evidence_digest_rejected(self):
        p = qualified_payload(); p["evidence"][0]["sha256"] = "abc"
        with self.assertRaisesRegex(QualificationError, "lowercase hex"):
            evaluate(p, evaluated_at=NOW)

    def test_invalid_full_rfp_digest_holds_not_ready(self):
        p = qualified_payload(); p["full_rfp"]["sha256"] = "ABC"
        r = evaluate(p, evaluated_at=NOW)
        self.assertIn("FULL_RFP_DIGEST_INVALID", r["holds"])

    def test_receipt_deterministic(self):
        p = qualified_payload()
        self.assertEqual(evaluate(p, evaluated_at=NOW), evaluate(copy.deepcopy(p), evaluated_at=NOW))

    def test_verify_exact_receipt(self):
        p = qualified_payload(); r = evaluate(p, evaluated_at=NOW)
        self.assertTrue(verify(p, r, evaluated_at=NOW))
        bad = copy.deepcopy(r); bad["decision"] = "HOLD"
        self.assertFalse(verify(p, bad, evaluated_at=NOW))

    def test_bad_timestamp_rejected(self):
        with self.assertRaisesRegex(QualificationError, "ending in Z"):
            evaluate(qualified_payload(), evaluated_at="2026-09-13T09:30:00+00:00")


if __name__ == "__main__":
    unittest.main()
