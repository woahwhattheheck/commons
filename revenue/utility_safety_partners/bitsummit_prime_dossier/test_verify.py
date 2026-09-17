from __future__ import annotations

import json
import unittest
from pathlib import Path

from revenue.utility_safety_partners.bitsummit_prime_dossier.verify import VerificationError, verify_payload

ROOT = Path(__file__).with_name("evidence.json")


def load():
    return json.loads(ROOT.read_text(encoding="utf-8"))


class DossierVerifierTests(unittest.TestCase):
    def test_valid_ledger(self):
        result = verify_payload(load())
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["item_count"], 15)
        for status in ("SUPPORTED", "PARTNER_CONFIRMATION_REQUIRED", "OWNER_INPUT", "GAP"):
            self.assertGreater(result["status_counts"][status], 0)

    def test_self_marketing_cannot_promote_to_supported(self):
        p = load()
        target = next(x for x in p["items"] if x["id"] == "microsoft_data_ai_designation")
        target["status"] = "SUPPORTED"
        with self.assertRaises(VerificationError):
            verify_payload(p)

    def test_marketing_flag_cannot_supported(self):
        p = load()
        target = next(x for x in p["items"] if x["id"] == "public_contact_route")
        target["marketing_claim"] = True
        with self.assertRaises(VerificationError):
            verify_payload(p)

    def test_stale_public_evidence_rejected(self):
        p = load()
        target = next(x for x in p["items"] if x["id"] == "ibm_partner_directory_identity")
        target["observed_at"] = "2026-01-01"
        with self.assertRaises(VerificationError):
            verify_payload(p)

    def test_missing_url_rejected_for_public_claim(self):
        p = load()
        target = next(x for x in p["items"] if x["id"] == "shell_energy_case")
        target["url"] = None
        with self.assertRaises(VerificationError):
            verify_payload(p)

    def test_conflicting_public_cannot_be_supported(self):
        p = load()
        target = next(x for x in p["items"] if x["id"] == "legal_name_and_address_conflict")
        target["status"] = "SUPPORTED"
        with self.assertRaises(VerificationError):
            verify_payload(p)

    def test_owner_input_cannot_be_recast_as_public(self):
        p = load()
        target = next(x for x in p["items"] if x["id"] == "pricing_and_commercial_terms")
        target["source_class"] = "PARTNER_SELF"
        target["url"] = "https://www.bitsummit.com/"
        with self.assertRaises(VerificationError):
            verify_payload(p)

    def test_authority_promotion_rejected(self):
        p = load()
        p["authority"]["partner_contact"] = True
        with self.assertRaises(VerificationError):
            verify_payload(p)

    def test_authority_field_deletion_rejected(self):
        p = load()
        del p["authority"]["pricing"]
        with self.assertRaises(VerificationError):
            verify_payload(p)

    def test_no_public_source_must_remain_gap(self):
        p = load()
        target = next(x for x in p["items"] if x["id"] == "exact_bid_eligibility_and_buyer_acceptance")
        target["status"] = "PARTNER_CONFIRMATION_REQUIRED"
        with self.assertRaises(VerificationError):
            verify_payload(p)

    def test_iso42001_alignment_not_certification(self):
        p = load()
        target = next(x for x in p["items"] if x["id"] == "ai_governance_capability")
        target["claim"] = "BITSUMMIT is ISO/IEC 42001 certified."
        with self.assertRaises(VerificationError):
            verify_payload(p)

    def test_soc_iso_self_claim_requires_confirmation(self):
        p = load()
        target = next(x for x in p["items"] if x["id"] == "security_managed_service_claims")
        target["status"] = "SUPPORTED"
        with self.assertRaises(VerificationError):
            verify_payload(p)

    def test_operation_tamper_rejected(self):
        p = load()
        p["operation"] = "DIFFERENT"
        with self.assertRaises(VerificationError):
            verify_payload(p)

    def test_canonical_issue_tamper_rejected(self):
        p = load()
        p["canonical_issue"] = "woahwhattheheck/commons#0"
        with self.assertRaises(VerificationError):
            verify_payload(p)


if __name__ == "__main__":
    unittest.main()
