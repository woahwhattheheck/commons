from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from revenue.scdhhs_mcde_5400030026.qualification import (
    QualificationError,
    SOURCE_CONTRACT,
    compile_qualification,
    verify_receipt,
)


def source_observation():
    return {
        "solicitation_number": SOURCE_CONTRACT["solicitation"]["number"],
        "attachment_count": len(SOURCE_CONTRACT["attachment_manifest"]),
        "attachments": copy.deepcopy(SOURCE_CONTRACT["attachment_manifest"]),
        "controlling_document": {
            "name": SOURCE_CONTRACT["controlling_document"]["name"],
            "posted_at": SOURCE_CONTRACT["controlling_document"]["posted_at"],
        },
    }


def security(value=True):
    return {
        key: {
            "ready": value,
            "evidence_refs": [f"evidence:security:{key}"] if value else [],
        }
        for key in SOURCE_CONTRACT["proposal_readiness"]["security_controls"]
    }


def entity(name):
    return {
        "entity_name": name,
        "similar_size_scope": True,
        "evidence_refs": [f"evidence:{name}"],
    }


def implementation(lives=1_000_000):
    return {
        "environment": "state-health-plan",
        "covered_lives": lives,
        "successful": True,
        "evidence_refs": ["evidence:adt-implementation"],
    }


def prime_packet():
    return {
        "route": "prime_offeror",
        "offeror": {
            "legal_name": "Evidence Test Offeror",
            "prime_contractor_months": 36,
            "prime_experience_evidence_refs": ["evidence:prime-history"],
            "similar_healthcare_entities": [entity("A"), entity("B"), entity("C")],
            "realtime_adt_months": 36,
            "healthcare_adt_months": 24,
            "adt_experience_evidence_refs": ["evidence:adt-history"],
            "adt_implementations": [implementation()],
        },
        "subcontractors": [],
        "proposal_readiness": {
            "project_manager_mcde_months": 36,
            "project_manager_healthcare_months": 24,
            "project_manager_evidence_refs": ["evidence:project-manager"],
            "security_controls": security(True),
        },
    }


class QualificationTests(unittest.TestCase):
    def test_control_prime_candidate_is_non_authoritative(self):
        receipt = compile_qualification(prime_packet(), source_observation=source_observation())
        self.assertEqual(receipt["decision"], "PRIME_QUALIFICATION_CANDIDATE")
        self.assertTrue(receipt["prime_qualification_candidate"])
        self.assertFalse(receipt["submission_authorized"])
        self.assertTrue(all(value is False for value in receipt["authority"].values()))
        self.assertTrue(verify_receipt(prime_packet(), source_observation=source_observation(), receipt=receipt))

    def test_original_rfp_cannot_replace_amendment_one(self):
        obs = source_observation()
        obs["controlling_document"] = {
            "name": "_MCDE RFP.pdf",
            "posted_at": "2026-07-31T17:34:53-04:00",
        }
        receipt = compile_qualification(prime_packet(), source_observation=obs)
        self.assertEqual(receipt["decision"], "HOLD_SOURCE_NOT_CURRENT")
        self.assertIn("SOURCE_CONTROLLING_DOCUMENT_MISMATCH", receipt["reasons"])

    def test_new_or_missing_attachment_fails_closed(self):
        for mutate in ("missing", "extra"):
            with self.subTest(mutate=mutate):
                obs = source_observation()
                if mutate == "missing":
                    obs["attachments"].pop()
                else:
                    obs["attachments"].append(
                        {"name": "Amendment 2.pdf", "posted_at": "2026-09-14T09:00:00-04:00"}
                    )
                obs["attachment_count"] = len(obs["attachments"])
                receipt = compile_qualification(prime_packet(), source_observation=obs)
                self.assertEqual(receipt["decision"], "HOLD_SOURCE_NOT_CURRENT")
                self.assertIn("SOURCE_ATTACHMENT_MANIFEST_MISMATCH", receipt["reasons"])

    def test_candidate_threshold_override_is_bound_but_has_no_authority(self):
        packet = prime_packet()
        packet["candidate_claimed_minimums"] = {
            "prime_contractor_months": 1,
            "similar_size_scope_healthcare_entities": 1,
            "successful_adt_min_lives": 1,
        }
        packet["offeror"]["prime_contractor_months"] = 1
        packet["offeror"]["similar_healthcare_entities"] = [entity("A")]
        packet["offeror"]["adt_implementations"] = [implementation(1)]
        receipt = compile_qualification(packet, source_observation=source_observation())
        self.assertEqual(receipt["decision"], "PRIME_NO_GO_MANDATORY_EXPERIENCE")
        self.assertIn("MANDATORY_PRIME_CONTRACTOR_EXPERIENCE", receipt["reasons"])
        self.assertIn("MANDATORY_THREE_SIMILAR_HEALTHCARE_ENTITIES", receipt["reasons"])
        self.assertIn("MANDATORY_SUCCESSFUL_ONE_MILLION_LIVES_ADT", receipt["reasons"])

    def test_claimed_months_without_evidence_do_not_pass(self):
        packet = prime_packet()
        packet["offeror"]["prime_experience_evidence_refs"] = []
        packet["offeror"]["adt_experience_evidence_refs"] = []
        receipt = compile_qualification(packet, source_observation=source_observation())
        self.assertEqual(receipt["decision"], "PRIME_NO_GO_MANDATORY_EXPERIENCE")
        self.assertIn("MANDATORY_PRIME_CONTRACTOR_EXPERIENCE", receipt["reasons"])
        self.assertIn("MANDATORY_REALTIME_ADT_EXPERIENCE", receipt["reasons"])
        self.assertIn("MANDATORY_HEALTHCARE_ADT_EXPERIENCE", receipt["reasons"])

    def test_partner_experience_cannot_cure_offeror_prime_history(self):
        packet = prime_packet()
        packet["offeror"]["prime_contractor_months"] = 0
        packet["subcontractors"] = [
            {
                "business_name": "Highly Qualified Partner",
                "scope": "ADT platform and interoperability",
                "cost_share_percent": 60,
                "government_information_access": True,
                "critical_services": True,
                "identification_complete": True,
                "relationship_explained": True,
                "evidence_refs": ["partner:many-prime-contracts", "partner:million-lives"],
            }
        ]
        receipt = compile_qualification(packet, source_observation=source_observation())
        self.assertEqual(receipt["decision"], "PRIME_NO_GO_MANDATORY_EXPERIENCE")
        self.assertFalse(receipt["prime_qualification_candidate"])

    def test_team_route_never_asserts_prime_qualification(self):
        packet = prime_packet()
        packet["route"] = "subcontractor_to_qualified_prime"
        packet["offeror"]["prime_contractor_months"] = 0
        packet["offeror"]["similar_healthcare_entities"] = []
        packet["offeror"]["realtime_adt_months"] = 0
        packet["offeror"]["healthcare_adt_months"] = 0
        packet["offeror"]["adt_implementations"] = []
        packet["teaming"] = {
            "qualified_prime_legal_name": "Qualified Prime Candidate",
            "relationship_explained": True,
            "prime_qualification_evidence_refs": ["prime:qualification-matrix"],
        }
        receipt = compile_qualification(packet, source_observation=source_observation())
        self.assertEqual(receipt["decision"], "TEAM_AS_SUBCONTRACTOR")
        self.assertFalse(receipt["prime_qualification_candidate"])
        self.assertFalse(receipt["submission_authorized"])

    def test_team_route_requires_relationship_and_prime_evidence(self):
        packet = prime_packet()
        packet["route"] = "subcontractor_to_qualified_prime"
        packet["teaming"] = {
            "qualified_prime_legal_name": "Partner",
            "relationship_explained": False,
            "prime_qualification_evidence_refs": [],
        }
        receipt = compile_qualification(packet, source_observation=source_observation())
        self.assertEqual(receipt["decision"], "TEAMING_DISCOVERY")

    def test_proposal_readiness_is_separate_from_mandatory_minimums(self):
        packet = prime_packet()
        packet["proposal_readiness"]["project_manager_mcde_months"] = 35
        packet["proposal_readiness"]["security_controls"]["hipaa_baa"] = {
            "ready": False,
            "evidence_refs": [],
        }
        receipt = compile_qualification(packet, source_observation=source_observation())
        self.assertEqual(receipt["decision"], "HOLD_PROPOSAL_READINESS")
        self.assertIn("READINESS_PROJECT_MANAGER_MCDE_EXPERIENCE", receipt["reasons"])
        self.assertIn("READINESS_SECURITY_HIPAA_BAA", receipt["reasons"])

    def test_security_true_without_evidence_is_not_ready(self):
        packet = prime_packet()
        packet["proposal_readiness"]["security_controls"]["hipaa_compliance"]["evidence_refs"] = []
        receipt = compile_qualification(packet, source_observation=source_observation())
        self.assertEqual(receipt["decision"], "HOLD_PROPOSAL_READINESS")
        self.assertIn("READINESS_SECURITY_HIPAA_COMPLIANCE", receipt["reasons"])

    def test_subcontractor_identification_rule_is_fail_closed(self):
        packet = prime_packet()
        packet["subcontractors"] = [
            {
                "business_name": "Critical Sub",
                "scope": "Critical exchange service",
                "cost_share_percent": 5,
                "government_information_access": False,
                "critical_services": True,
                "identification_complete": False,
                "relationship_explained": True,
                "evidence_refs": [],
            }
        ]
        receipt = compile_qualification(packet, source_observation=source_observation())
        self.assertEqual(receipt["decision"], "HOLD_PROPOSAL_READINESS")
        self.assertIn("SUBCONTRACTOR_IDENTIFICATION_INCOMPLETE", receipt["reasons"])

    def test_strict_types_reject_bool_as_months_and_string_boolean(self):
        packet = prime_packet()
        packet["offeror"]["prime_contractor_months"] = True
        with self.assertRaises(QualificationError):
            compile_qualification(packet, source_observation=source_observation())

        packet = prime_packet()
        packet["proposal_readiness"]["security_controls"]["hipaa_baa"]["ready"] = "true"
        with self.assertRaises(QualificationError):
            compile_qualification(packet, source_observation=source_observation())

    def test_duplicate_source_attachment_name_holds(self):
        obs = source_observation()
        obs["attachments"][1] = copy.deepcopy(obs["attachments"][0])
        receipt = compile_qualification(prime_packet(), source_observation=obs)
        self.assertEqual(receipt["decision"], "HOLD_SOURCE_NOT_CURRENT")
        self.assertIn("SOURCE_DUPLICATE_ATTACHMENT_NAME", receipt["reasons"])

    def test_receipt_is_deterministic_and_tamper_evident(self):
        packet = prime_packet()
        obs = source_observation()
        first = compile_qualification(packet, source_observation=obs)
        second = compile_qualification(copy.deepcopy(packet), source_observation=copy.deepcopy(obs))
        self.assertEqual(first, second)

        tampered = copy.deepcopy(first)
        tampered["decision"] = "PRIME_QUALIFICATION_CANDIDATE"
        tampered["submission_authorized"] = True
        self.assertFalse(verify_receipt(packet, source_observation=obs, receipt=tampered))

        packet["offeror"]["prime_contractor_months"] = 35
        self.assertFalse(verify_receipt(packet, source_observation=obs, receipt=first))


if __name__ == "__main__":
    unittest.main()
