import tempfile
import unittest
from pathlib import Path

import qualify


def packet(route="PRIME"):
    return {
        "schema": qualify.SCHEMA,
        "as_of": "2026-09-14T03:45:00Z",
        "source_generation": {
            "buyer_page_checked_at": "2026-09-14T03:40:00Z",
            "complete_package_observed": True,
            "controlling_rfp_bytes_retained": True,
            "bid_sheet_bytes_retained": True,
            "confidentiality_agreement_bytes_retained": True,
            "q_and_a_bytes_retained": True,
        },
        "organization": {
            "uei": "OWNER-VERIFIED-UEI",
            "sam_active": True,
            "authorized_signer_available": True,
            "terms_reviewed_by_counsel": True,
            "confidentiality_agreement_executable": True,
            "insurance_evidence_available": True,
            "conflict_review_complete": True,
        },
        "key_personnel": [
            {"person_id": "kp-ai", "role": "AI_SME", "employer_type": "PRIME", "employed_at_submission": True},
            {"person_id": "kp-gov", "role": "ADDITIONAL_KEY", "employer_type": "PRIME", "employed_at_submission": True},
        ],
        "past_performance": [
            {
                "engagement_id": "eng-1",
                "entity_type": "PRIME",
                "similar_scope": True,
                "reference_reachable": True,
                "currently_performing": False,
                "completed_on": "2025-05-01",
            },
            {
                "engagement_id": "eng-2",
                "entity_type": "PRIME",
                "similar_scope": True,
                "reference_reachable": True,
                "currently_performing": True,
                "completed_on": "",
            },
        ],
        "proposal": {
            "page_counts": {
                "volume_1_corporate": 4,
                "volume_2_technical": 12,
                "volume_3_past_performance": 5,
                "volume_4_price": 4,
            },
            "with_ai_bid_sheet": True,
            "without_ai_bid_sheet": True,
            "confidentiality_agreement_signed": True,
            "legal_review_statement_included": True,
            "cover_requirements_complete": True,
            "final_price_present": True,
            "price_owner_approved": True,
            "no_unsupported_claims": True,
        },
        "route": route,
    }


class QualificationTests(unittest.TestCase):
    def test_complete_prime_packet_is_internal_ready_but_never_submission_authority(self):
        result = qualify.evaluate(packet())
        self.assertEqual(result["decision"], "PRIME_READY")
        self.assertFalse(result["external_submission_authorized"])

    def test_teaming_route_can_use_partner_reference_and_key_person(self):
        p = packet("TEAM")
        p["key_personnel"][1]["employer_type"] = "TEAMING_PARTNER"
        p["past_performance"][0]["entity_type"] = "TEAMING_PARTNER"
        result = qualify.evaluate(p)
        self.assertEqual(result["decision"], "TEAMING_READY")
        self.assertEqual(result["team_reference_count"], 1)

    def test_prime_cannot_masquerade_team_dependency_as_pure_prime(self):
        p = packet("PRIME")
        p["key_personnel"][1]["employer_type"] = "SUBCONTRACTOR"
        self.assertIn("PRIME_ROUTE_DEPENDS_ON_TEAM_PERSONNEL", qualify.evaluate(p)["reason_codes"])

    def test_missing_second_bid_sheet_holds(self):
        p = packet()
        p["proposal"]["without_ai_bid_sheet"] = False
        self.assertIn("WITHOUT_AI_BID_SHEET_MISSING", qualify.evaluate(p)["reason_codes"])

    def test_only_one_reference_holds(self):
        p = packet()
        p["past_performance"].pop()
        self.assertIn("TWO_TO_THREE_VALID_REFERENCES_REQUIRED", qualify.evaluate(p)["reason_codes"])

    def test_stale_reference_does_not_count(self):
        p = packet()
        p["past_performance"][0]["completed_on"] = "2022-01-01"
        result = qualify.evaluate(p)
        self.assertEqual(result["valid_reference_count"], 1)
        self.assertEqual(result["decision"], "HOLD")

    def test_unreachable_reference_does_not_count(self):
        p = packet()
        p["past_performance"][0]["reference_reachable"] = False
        self.assertEqual(qualify.evaluate(p)["decision"], "HOLD")

    def test_key_person_must_already_be_employed(self):
        p = packet()
        p["key_personnel"][0]["employed_at_submission"] = False
        self.assertIn("KEY_PERSON_NOT_EMPLOYED_AT_SUBMISSION", qualify.evaluate(p)["reason_codes"])

    def test_ai_sme_plus_one_additional_required(self):
        p = packet()
        p["key_personnel"] = p["key_personnel"][:1]
        self.assertIn("ADDITIONAL_KEY_PERSONNEL_COUNT_INVALID", qualify.evaluate(p)["reason_codes"])

    def test_page_overflow_holds(self):
        p = packet()
        p["proposal"]["page_counts"]["volume_2_technical"] = 13
        self.assertIn("VOLUME_2_TECHNICAL_PAGE_LIMIT_EXCEEDED", qualify.evaluate(p)["reason_codes"])

    def test_missing_sam_holds(self):
        p = packet()
        p["organization"]["sam_active"] = False
        self.assertIn("SAM_REGISTRATION_NOT_ACTIVE", qualify.evaluate(p)["reason_codes"])

    def test_incomplete_buyer_generation_holds(self):
        p = packet()
        p["source_generation"]["complete_package_observed"] = False
        self.assertIn("CONTROLLING_PACKAGE_INCOMPLETE", qualify.evaluate(p)["reason_codes"])

    def test_missing_bid_sheet_bytes_holds(self):
        p = packet()
        p["source_generation"]["bid_sheet_bytes_retained"] = False
        self.assertIn("BID_SHEET_BYTES_MISSING", qualify.evaluate(p)["reason_codes"])

    def test_missing_any_other_controlling_bytes_holds(self):
        for key, code in (
            ("controlling_rfp_bytes_retained", "CONTROLLING_RFP_BYTES_MISSING"),
            ("confidentiality_agreement_bytes_retained", "CONFIDENTIALITY_AGREEMENT_BYTES_MISSING"),
            ("q_and_a_bytes_retained", "Q_AND_A_BYTES_MISSING"),
        ):
            with self.subTest(key=key):
                p = packet()
                p["source_generation"][key] = False
                self.assertIn(code, qualify.evaluate(p)["reason_codes"])

    def test_future_source_observation_holds(self):
        p = packet()
        p["source_generation"]["buyer_page_checked_at"] = "2026-09-14T04:00:00Z"
        self.assertIn("SOURCE_OBSERVATION_FROM_FUTURE", qualify.evaluate(p)["reason_codes"])

    def test_deadline_expiry_is_no_bid(self):
        p = packet()
        p["as_of"] = "2026-09-30T15:00:00Z"
        result = qualify.evaluate(p)
        self.assertEqual(result["decision"], "NO_BID")
        self.assertEqual(result["reason_codes"], ["PROPOSAL_DEADLINE_EXPIRED"])

    def test_int_cannot_alias_boolean(self):
        p = packet()
        p["organization"]["sam_active"] = 1
        with self.assertRaises(qualify.QualificationError):
            qualify.evaluate(p)

    def test_duplicate_json_keys_are_rejected(self):
        raw = '{"schema":"a","schema":"b"}'
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "dup.json"
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(qualify.QualificationError):
                qualify.load_json(path)

    def test_duplicate_engagement_id_holds(self):
        p = packet()
        p["past_performance"][1]["engagement_id"] = p["past_performance"][0]["engagement_id"]
        self.assertIn("DUPLICATE_PAST_PERFORMANCE_ID", qualify.evaluate(p)["reason_codes"])

    def test_final_price_requires_owner_approval(self):
        p = packet()
        p["proposal"]["price_owner_approved"] = False
        self.assertIn("FINAL_PRICE_NOT_OWNER_APPROVED", qualify.evaluate(p)["reason_codes"])

    def test_unsupported_claim_holds(self):
        p = packet()
        p["proposal"]["no_unsupported_claims"] = False
        self.assertIn("UNSUPPORTED_CLAIM_PRESENT", qualify.evaluate(p)["reason_codes"])


if __name__ == "__main__":
    unittest.main()
