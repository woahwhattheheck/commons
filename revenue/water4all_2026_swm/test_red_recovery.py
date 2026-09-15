"""Regression hostiles for the five STOP-MERGE RED authority findings."""

from .test_support import *  # noqa: F401,F403


class RedRecoveryTests(unittest.TestCase):
    def test_current_mode_refuses_caller_owned_time(self):
        with self.assertRaisesRegex(ReadinessError, "process-owned UTC"):
            compile_at(base_valid(), T0, "CURRENT")

    def test_resealed_caller_source_cannot_mint_current_authority(self):
        value = load_json("example_input.json")
        national = next(s for s in value["official_sources"] if s["authority_class"] == "OFFICIAL_NATIONAL_REGULATIONS")
        national["preproposal_deadline_at"] = "2026-11-10T14:00:00Z"
        reseal(national)
        bundle = compile_current_at(value)
        self.assertIn("SOURCE_TRUST_ROOT_MISMATCH", reason_codes(bundle))
        self.assertEqual(bundle["packet"]["decision"]["status"], "HOLD_SOURCE_AUTHORITY")
        self.assertIsNone(bundle["packet"]["deadline_authority"]["controlling_preproposal_deadline_at"])

    def test_caller_verified_technical_descriptor_is_not_live_evidence(self):
        value = base_valid()
        self.assertTrue(value["technical_evidence"][0]["verified"])
        bundle = compile_current_at(value)
        self.assertIn("TECHNICAL_EVIDENCE_NOT_TRUSTED", reason_codes(bundle))
        self.assertEqual(bundle["packet"]["concept_and_evidence"]["verified_capability_tags"], [])

    def test_water4all_beneficiary_cap_for_small_consortium(self):
        value = base_valid()
        for member in value["consortium"]["members"]:
            member["water4all_partnership_beneficiary"] = True
        bundle = compile_valid(value)
        self.assertIn("WATER4ALL_BENEFICIARY_ENTITY_CAP", reason_codes(bundle))
        self.assertEqual(bundle["packet"]["consortium"]["water4all_beneficiary_cap"], 2)
        self.assertEqual(bundle["packet"]["consortium"]["water4all_beneficiary_count"], 3)

    def test_current_requires_coordinator_pi_cross_proposal_evidence(self):
        value = load_json("example_input.json")
        for member in value["consortium"]["members"]:
            member["water4all_partnership_beneficiary"] = False
        bundle = compile_current_at(value)
        self.assertIn("COORDINATOR_PI_CROSS_PROPOSAL_EVIDENCE_MISSING", reason_codes(bundle))

    def test_caller_minted_pi_evidence_cannot_clear_live_gate(self):
        value = load_json("example_input.json")
        for member in value["consortium"]["members"]:
            member["water4all_partnership_beneficiary"] = False
        coordinator_id = next(m["partner_id"] for m in value["consortium"]["members"] if m["coordinator"])
        value["consortium"]["coordinator_pi_evidence"] = {
            "evidence_id": "caller-minted-pi-evidence",
            "coordinator_partner_id": coordinator_id,
            "pi_id": "synthetic-pi",
            "other_coordinating_proposal_count": 0,
            "source_url": "https://www.water4all-partnership.eu/joint-activities/water4all-2026-joint-transnational-call",
            "content_sha256": "0" * 64,
            "observed_at": "2026-09-14T03:50:00Z",
        }
        bundle = compile_current_at(value)
        self.assertIn("COORDINATOR_PI_CROSS_PROPOSAL_EVIDENCE_NOT_TRUSTED", reason_codes(bundle))

    def test_partner_profile_url_rejects_userinfo_query_and_encoded_path(self):
        bad_urls = [
            "https://user@proposals.etag.ee/water4all/2026/partner-search-entry/858",
            "https://proposals.etag.ee/water4all/2026/partner-search-entry/858?contact=1",
            "https://proposals.etag.ee/water4all/2026/partner-search-entry/%38%35%38",
        ]
        for bad_url in bad_urls:
            with self.subTest(url=bad_url):
                value = base_valid()
                value["partner_shortlist"][0]["public_profile_url"] = bad_url
                with self.assertRaises(ReadinessError):
                    compile_valid(value)

    def test_partner_research_rejects_generic_contact_payload(self):
        value = base_valid()
        value["partner_shortlist"][0]["contact"] = {"body": "hello"}
        with self.assertRaisesRegex(ReadinessError, "forbidden contact"):
            compile_valid(value)

    def test_partner_research_rejects_embedded_email_route(self):
        value = base_valid()
        value["partner_shortlist"][0]["public_fit_summary"] = "Write person@example.invalid for access"
        with self.assertRaisesRegex(ReadinessError, "contact-route semantics"):
            compile_valid(value)
