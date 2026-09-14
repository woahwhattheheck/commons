import tempfile
import unittest
from pathlib import Path

import qualify


def packet(route="PRIME"):
    return {
        "schema": qualify.SCHEMA,
        "as_of": "2026-09-14T04:00:00Z",
        "source": {
            "first_party_event_observed_at": "2026-09-14T03:50:00Z",
            "first_party_event_open": True,
            "first_party_packet_bytes_retained": True,
            "all_addenda_retained": True,
            "packet_mirror_only": False,
        },
        "organization": {
            "legal_entity": "OWNER-VERIFIED-ENTITY",
            "texas_comptroller_current": True,
            "franchise_tax_evidence": True,
            "vet_hub_plan_complete": True,
            "execution_of_offer_signed": True,
            "addenda_checklist_signed": True,
            "insurance_evidence": True,
            "prohibited_entity_certifications_reviewed": True,
        },
        "references": [
            {"reference_id":"r1","similar_scope":True,"current_or_recent":True,"reachable_contact":True,"entity_type":"PRIME"},
            {"reference_id":"r2","similar_scope":True,"current_or_recent":True,"reachable_contact":True,"entity_type":"PRIME"},
            {"reference_id":"r3","similar_scope":True,"current_or_recent":True,"reachable_contact":True,"entity_type":"PRIME"},
        ],
        "team": {
            "project_lead_named": True,
            "team_qualifications_evidenced": True,
            "time_commitments_defined": True,
            "subconsultants_identified_if_used": True,
            "delivery_capacity_for_six_deliverables": True,
        },
        "security": {
            "tx_ramp_status_resolved": True,
            "hipaa_ferpa_boundary_reviewed": True,
            "institutional_data_no_training": True,
            "rbac": True,
            "sso": True,
            "tls_1_3": True,
            "aes_256_at_rest": True,
            "unsupported_compliance_claims_absent": True,
        },
        "proposal": {
            "section_5_response_complete": True,
            "scope_of_work_exhibit_a_complete": True,
            "project_schedule_complete": True,
            "pricing_schedule_signed": True,
            "techbid_package_complete": True,
            "proposal_valid_90_days": True,
            "all_six_deliverables_covered": True,
            "oral_presentation_ready": True,
        },
        "commercial": {
            "fixed_fee_nte_present": True,
            "loe_schedule_present": True,
            "rate_card_present_through_2027_08_31": True,
            "final_price_owner_approved": True,
            "contract_exceptions_reviewed": True,
        },
        "route": route,
    }


class QualificationTests(unittest.TestCase):
    def test_complete_prime_internal_ready_never_submission_authority(self):
        result = qualify.evaluate(packet())
        self.assertEqual(result["decision"], "PRIME_READY")
        self.assertFalse(result["external_submission_authorized"])

    def test_team_route_accepts_named_team_reference(self):
        p = packet("TEAM")
        p["references"][0]["entity_type"] = "TEAMING_PARTNER"
        self.assertEqual(qualify.evaluate(p)["decision"], "TEAMING_READY")

    def test_prime_cannot_borrow_team_reference(self):
        p = packet()
        p["references"][0]["entity_type"] = "SUBCONSULTANT"
        self.assertIn("PRIME_ROUTE_DEPENDS_ON_NON_PRIME_REFERENCE", qualify.evaluate(p)["reason_codes"])

    def test_team_route_needs_team_reference(self):
        self.assertIn("TEAM_ROUTE_HAS_NO_TEAM_REFERENCE", qualify.evaluate(packet("TEAM"))["reason_codes"])

    def test_deadline_expiry_is_no_bid(self):
        p = packet()
        p["as_of"] = "2026-09-21T21:30:00Z"
        self.assertEqual(qualify.evaluate(p)["decision"], "NO_BID")

    def test_mirror_only_source_holds(self):
        p = packet()
        p["source"]["packet_mirror_only"] = True
        self.assertIn("MIRROR_ONLY_SOURCE_CANNOT_AUTHORIZE", qualify.evaluate(p)["reason_codes"])

    def test_first_party_bytes_required(self):
        p = packet()
        p["source"]["first_party_packet_bytes_retained"] = False
        self.assertIn("FIRST_PARTY_PACKET_BYTES_MISSING", qualify.evaluate(p)["reason_codes"])

    def test_addenda_required(self):
        p = packet()
        p["source"]["all_addenda_retained"] = False
        self.assertIn("ADDENDA_GENERATION_INCOMPLETE", qualify.evaluate(p)["reason_codes"])

    def test_future_source_observation_holds(self):
        p = packet()
        p["source"]["first_party_event_observed_at"] = "2026-09-14T04:01:00Z"
        self.assertIn("SOURCE_OBSERVATION_FROM_FUTURE", qualify.evaluate(p)["reason_codes"])

    def test_hsp_required(self):
        p = packet()
        p["organization"]["vet_hub_plan_complete"] = False
        self.assertIn("VETHUB_PLAN_INCOMPLETE", qualify.evaluate(p)["reason_codes"])

    def test_execution_signature_required(self):
        p = packet()
        p["organization"]["execution_of_offer_signed"] = False
        self.assertIn("EXECUTION_OF_OFFER_UNSIGNED", qualify.evaluate(p)["reason_codes"])

    def test_three_references_required(self):
        p = packet()
        p["references"].pop()
        self.assertIn("THREE_VALID_REFERENCES_REQUIRED", qualify.evaluate(p)["reason_codes"])

    def test_unreachable_reference_does_not_count(self):
        p = packet()
        p["references"][0]["reachable_contact"] = False
        self.assertEqual(qualify.evaluate(p)["valid_reference_count"], 2)

    def test_duplicate_reference_id_holds(self):
        p = packet()
        p["references"][1]["reference_id"] = "r1"
        self.assertIn("DUPLICATE_REFERENCE_ID", qualify.evaluate(p)["reason_codes"])

    def test_tx_ramp_status_must_be_resolved_not_claimed_by_omission(self):
        p = packet()
        p["security"]["tx_ramp_status_resolved"] = False
        self.assertIn("TX_RAMP_STATUS_UNRESOLVED", qualify.evaluate(p)["reason_codes"])

    def test_data_training_prohibition_is_mandatory(self):
        p = packet()
        p["security"]["institutional_data_no_training"] = False
        self.assertIn("INSTITUTIONAL_DATA_TRAINING_PROHIBITION_NOT_BOUND", qualify.evaluate(p)["reason_codes"])

    def test_each_required_security_control_holds(self):
        for key, code in [
            ("rbac","RBAC_CONTROL_MISSING"), ("sso","SSO_CONTROL_MISSING"),
            ("tls_1_3","TLS_1_3_CONTROL_MISSING"), ("aes_256_at_rest","AES_256_AT_REST_CONTROL_MISSING")
        ]:
            with self.subTest(key=key):
                p = packet()
                p["security"][key] = False
                self.assertIn(code, qualify.evaluate(p)["reason_codes"])

    def test_unsupported_compliance_claim_holds(self):
        p = packet()
        p["security"]["unsupported_compliance_claims_absent"] = False
        self.assertIn("UNSUPPORTED_COMPLIANCE_CLAIM_PRESENT", qualify.evaluate(p)["reason_codes"])

    def test_six_deliverables_required(self):
        p = packet()
        p["proposal"]["all_six_deliverables_covered"] = False
        self.assertIn("SIX_DELIVERABLE_COVERAGE_INCOMPLETE", qualify.evaluate(p)["reason_codes"])

    def test_scope_exhibit_required(self):
        p = packet()
        p["proposal"]["scope_of_work_exhibit_a_complete"] = False
        self.assertIn("EXHIBIT_A_SCOPE_MISSING", qualify.evaluate(p)["reason_codes"])

    def test_rate_card_and_owner_price_required(self):
        p = packet()
        p["commercial"]["rate_card_present_through_2027_08_31"] = False
        p["commercial"]["final_price_owner_approved"] = False
        codes = qualify.evaluate(p)["reason_codes"]
        self.assertIn("RATE_CARD_MISSING", codes)
        self.assertIn("FINAL_PRICE_NOT_OWNER_APPROVED", codes)

    def test_bool_int_alias_rejected(self):
        p = packet()
        p["organization"]["vet_hub_plan_complete"] = 1
        with self.assertRaises(qualify.QualificationError):
            qualify.evaluate(p)

    def test_duplicate_json_key_rejected(self):
        raw = '{"schema":"a","schema":"b"}'
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "dup.json"
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(qualify.QualificationError):
                qualify.load_json(path)


if __name__ == "__main__":
    unittest.main()
