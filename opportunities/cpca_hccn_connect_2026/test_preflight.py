import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import preflight

HERE = Path(__file__).parent
SOURCE = json.loads((HERE / "source_snapshot.json").read_text())


def ready_owner():
    return {
        "schema": "cpca.hccn.owner_inputs/v1",
        "organization": {
            "legal_name": "Example Qualified Vendor LLC",
            "website": "https://example.invalid",
            "point_of_contact_name": "Qualified Human",
            "point_of_contact_title": "Principal",
            "point_of_contact_email": "qualified@example.invalid",
        },
        "selected_routes": [
            {
                "domain": "artificial_intelligence",
                "service_type": "technical_assistance",
                "topics": ["AI Governance", "AI Vendor Evaluation", "AI Use Case Education"],
            }
        ],
        "comparable_engagements": [
            {
                "engagement_id": "eng-1",
                "domains": ["artificial_intelligence"],
                "status": "completed",
                "start_date": "2026-01-01",
                "end_date": "2026-06-01",
                "client_description": "qualifying safety-net client",
                "scope": "AI governance assessment and roadmap",
                "deliverables": "governance controls and decision records",
                "evidence_ref": "private:evidence/eng-1",
                "personnel_names": ["Qualified Human"],
            },
            {
                "engagement_id": "eng-2",
                "domains": ["artificial_intelligence"],
                "status": "pilot",
                "start_date": "2026-07-01",
                "end_date": "2026-09-01",
                "client_description": "second relevant client",
                "scope": "AI vendor evaluation pilot",
                "deliverables": "evaluation rubric and evidence matrix",
                "evidence_ref": "private:evidence/eng-2",
                "personnel_names": ["Qualified Human"],
            },
        ],
        "safety_net_engagements": [
            {
                "engagement_id": "eng-1",
                "client_type": "federally_qualified_health_center",
                "domains": ["artificial_intelligence"],
                "scope": "AI governance support",
                "evidence_ref": "private:evidence/eng-1",
                "personnel_names": ["Qualified Human"],
            }
        ],
        "technical_assistance_evidence": [
            {
                "engagement_id": "eng-1",
                "individualized_support": "custom readiness assessment and roadmap",
                "deliverables": "assessment, workplan, implementation roadmap",
                "evidence_ref": "private:evidence/eng-1",
            }
        ],
        "group_training_evidence": [],
        "personnel": [
            {
                "name": "Qualified Human",
                "role": "Principal / SME",
                "qualifications": "evidence-backed domain qualifications",
                "years_experience": "7",
                "evidence_ref": "private:resume/qualified-human",
            }
        ],
        "subcontractors": [],
        "references": [
            {"reference_id": "r1", "organization": "A", "relationship": "client", "private_contact_plan": "owner-held"},
            {"reference_id": "r2", "organization": "B", "relationship": "client", "private_contact_plan": "owner-held"},
            {"reference_id": "r3", "organization": "C", "relationship": "client", "private_contact_plan": "owner-held"},
        ],
        "work_samples": [
            {"title": "AI governance work sample", "domain": "artificial_intelligence", "evidence_ref": "private:sample/ai-governance"}
        ],
        "regulatory_knowledge": {
            "artificial_intelligence": {
                "narrative": "evidence-backed responsible-AI and healthcare-context standards knowledge",
                "evidence_ref": "private:evidence/reg-ai",
            }
        },
        "cultural_competency": {
            "narrative": "evidence-backed safety-net and agricultural/rural delivery practice",
            "evidence_ref": "private:evidence/cultural",
        },
        "delivery_capacity": {
            "virtual_delivery_supported": True,
            "california_presence": "virtual delivery path selected",
            "concurrent_engagement_capacity": "documented staffing capacity",
            "reporting_invoicing_oversight_capability": "documented monthly reporting/invoicing process",
        },
        "licensing_compliance": {
            "requirements_reviewed": True,
            "all_required_licenses_certifications_current": True,
            "insurance_requirements_reviewed": True,
            "insurance_supportable": True,
            "evidence_ref": "private:evidence/licenses-insurance",
        },
        "privacy_contracting": {
            "baa_obligations_reviewed": True,
            "baa_capability": "supportable under owner/legal review",
            "phi_pii_delivery_boundary": "documented least-privilege data boundary",
        },
        "pricing": {
            "technical_assistance_rates_by_role": {"Principal / Subject Matter Expert": 1},
            "group_training_rates": {},
            "fully_loaded_basis_reviewed": True,
            "owner_approved": True,
        },
        "appendix_c": {
            "reviewed_by_authorized_human": True,
            "signed_by_authorized_human": True,
            "authorized_representative_name": "Qualified Human",
            "conflict_status": "reviewed and supportable",
        },
        "packaging": {
            "single_pdf_plan_reviewed": True,
            "smartsheet_submission_mechanics_reviewed": True,
            "filename_reviewed": True,
        },
        "owner_final_review_complete": True,
    }


NOW = datetime(2026, 9, 14, 22, 0, 0, tzinfo=timezone.utc)


class PreflightTests(unittest.TestCase):
    def test_ready_fixture(self):
        receipt = preflight.evaluate(SOURCE, ready_owner(), trusted_now=NOW)
        self.assertEqual(receipt["state"], preflight.READY)
        self.assertEqual(receipt["posture"], "DIRECT_PRIME_REVIEWABLE")
        self.assertFalse(any(receipt["authority"].values()))

    def test_template_holds(self):
        template = json.loads((HERE / "owner_inputs.template.json").read_text())
        receipt = preflight.evaluate(SOURCE, template, trusted_now=NOW)
        self.assertEqual(receipt["state"], preflight.HOLD)
        self.assertTrue(receipt["blockers"])

    def test_missing_safety_net_blocks(self):
        owner = ready_owner(); owner["safety_net_engagements"] = []
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertIn("SAFETY_NET_EXPERIENCE_REQUIRED:artificial_intelligence", receipt["blockers"])
        self.assertEqual(receipt["posture"], "HOLD_HEALTHCARE_OR_DOMAIN_EXPERIENCE_GAP")

    def test_emerging_requires_two_engagements(self):
        owner = ready_owner(); owner["comparable_engagements"] = owner["comparable_engagements"][:1]
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertIn("EMERGING_DOMAIN_TWO_ENGAGEMENTS_REQUIRED:artificial_intelligence:1/2", receipt["blockers"])

    def test_emerging_requires_recent_completed(self):
        owner = ready_owner()
        for row in owner["comparable_engagements"]:
            row["status"] = "pilot"
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertIn("EMERGING_DOMAIN_RECENT_COMPLETED_REQUIRED:artificial_intelligence", receipt["blockers"])

    def test_group_training_separate_evidence_required(self):
        owner = ready_owner()
        owner["selected_routes"][0]["service_type"] = "group_training"
        owner["pricing"]["technical_assistance_rates_by_role"] = {}
        owner["pricing"]["group_training_rates"] = {"single session": 1}
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertIn("GROUP_TRAINING_COMPARABLE_EVIDENCE_REQUIRED", receipt["blockers"])

    def test_unknown_topic_blocks(self):
        owner = ready_owner(); owner["selected_routes"][0]["topics"].append("Magic")
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertTrue(any(x.startswith("ROUTE_0_UNKNOWN_TOPICS:") for x in receipt["blockers"]))

    def test_three_references_required(self):
        owner = ready_owner(); owner["references"] = owner["references"][:2]
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertIn("THREE_CLIENT_REFERENCES_REQUIRED", receipt["blockers"])

    def test_duplicate_reference_ids_block(self):
        owner = ready_owner(); owner["references"][2]["reference_id"] = "r1"
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertIn("REFERENCE_IDS_MUST_BE_UNIQUE", receipt["blockers"])

    def test_unsigned_appendix_blocks(self):
        owner = ready_owner(); owner["appendix_c"]["signed_by_authorized_human"] = False
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertIn("APPENDIX_C_HUMAN_SIGNATURE_REQUIRED", receipt["blockers"])

    def test_pricing_approval_blocks(self):
        owner = ready_owner(); owner["pricing"]["owner_approved"] = False
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertIn("PRICING_OWNER_APPROVAL_REQUIRED", receipt["blockers"])

    def test_baa_review_blocks(self):
        owner = ready_owner(); owner["privacy_contracting"]["baa_obligations_reviewed"] = False
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertIn("BAA_OBLIGATIONS_REVIEW_REQUIRED", receipt["blockers"])

    def test_source_digest_identity_is_enforced(self):
        source = copy.deepcopy(SOURCE); source["buyer_packet"]["sha256"] = "0" * 64
        with self.assertRaises(preflight.PreflightError):
            preflight.evaluate(source, ready_owner(), trusted_now=NOW)

    def test_no_guaranteed_volume_boundary_enforced(self):
        source = copy.deepcopy(SOURCE); source["marketplace"]["guaranteed_referrals_or_volume"] = True
        with self.assertRaises(preflight.PreflightError):
            preflight.evaluate(source, ready_owner(), trusted_now=NOW)

    def test_source_authority_must_remain_false(self):
        source = copy.deepcopy(SOURCE); source["authority"]["external_submission_authorized"] = True
        with self.assertRaises(preflight.PreflightError):
            preflight.evaluate(source, ready_owner(), trusted_now=NOW)

    def test_stale_source_blocks(self):
        source = copy.deepcopy(SOURCE); source["checked_at"] = "2026-09-01T00:00:00Z"
        receipt = preflight.evaluate(source, ready_owner(), trusted_now=NOW)
        self.assertEqual(receipt["state"], preflight.SOURCE_REFRESH)

    def test_deadline_passed_blocks(self):
        later = datetime(2026, 9, 19, 1, 0, 1, tzinfo=timezone.utc)
        receipt = preflight.evaluate(SOURCE, ready_owner(), trusted_now=later)
        self.assertEqual(receipt["state"], preflight.DEADLINE_PASSED)

    def test_future_checked_at_rejected(self):
        source = copy.deepcopy(SOURCE); source["checked_at"] = "2026-09-15T00:00:00Z"
        with self.assertRaises(preflight.PreflightError):
            preflight.evaluate(source, ready_owner(), trusted_now=NOW)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(preflight.PreflightError):
            preflight.load_json_bytes(b'{"a":1,"a":2}', "test")

    def test_nan_rejected(self):
        with self.assertRaises(preflight.PreflightError):
            preflight.load_json_bytes(b'{"a":NaN}', "test")

    def test_non_utf8_rejected(self):
        with self.assertRaises(preflight.PreflightError):
            preflight.load_json_bytes(b'\xff', "test")

    def test_unknown_domain_blocks(self):
        owner = ready_owner(); owner["selected_routes"][0]["domain"] = "unknown"
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertTrue(any("UNKNOWN_DOMAIN" in x for x in receipt["blockers"]))

    def test_missing_work_sample_blocks(self):
        owner = ready_owner(); owner["work_samples"] = []
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertIn("RELEVANT_WORK_SAMPLE_REQUIRED", receipt["blockers"])

    def test_missing_regulatory_evidence_blocks(self):
        owner = ready_owner(); owner["regulatory_knowledge"] = {}
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertIn("REGULATORY_STANDARDS_EVIDENCE_REQUIRED:artificial_intelligence", receipt["blockers"])

    def test_missing_ta_evidence_blocks(self):
        owner = ready_owner(); owner["technical_assistance_evidence"] = []
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertIn("TECHNICAL_ASSISTANCE_COMPARABLE_EVIDENCE_REQUIRED", receipt["blockers"])

    def test_placeholders_hold(self):
        owner = ready_owner(); owner["organization"]["legal_name"] = "OWNER_INPUT_REQUIRED"
        receipt = preflight.evaluate(SOURCE, owner, trusted_now=NOW)
        self.assertTrue(any(x.startswith("PLACEHOLDERS_REMAIN:") for x in receipt["blockers"]))

    def test_receipt_is_deterministic(self):
        a = preflight.evaluate(SOURCE, ready_owner(), trusted_now=NOW)
        b = preflight.evaluate(SOURCE, ready_owner(), trusted_now=NOW)
        self.assertEqual(a, b)
        self.assertEqual(len(a["receipt_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
