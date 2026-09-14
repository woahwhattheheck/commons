import copy
import json
import unittest
from pathlib import Path

import cpca_qualify as q

ROOT = Path(__file__).resolve().parent
SPEC = json.loads((ROOT / "qualification_spec.json").read_text())
CURRENT = json.loads((ROOT / "current_evidence.json").read_text())


def proven_fixture():
    e = copy.deepcopy(CURRENT)
    e["gate_status"] = {g["id"]: "PROVEN" for g in SPEC["mandatory_direct_prime_gates"]}
    e["client_references"] = [
        {"name": "r1", "source": "urn:test:r1"},
        {"name": "r2", "source": "urn:test:r2"},
        {"name": "r3", "source": "urn:test:r3"}
    ]
    e["comparable_engagements"] = [
        {"state": "COMPLETED", "source": "urn:test:e1", "safety_net_primary_care": True},
        {"state": "ACTIVE", "source": "urn:test:e2", "safety_net_primary_care": False}
    ]
    return e


class QualificationTests(unittest.TestCase):
    def test_current_evidence_holds(self):
        result = q.evaluate(SPEC, CURRENT)
        self.assertEqual("HOLD", result["state"])
        self.assertIn("safety_net_experience", result["blockers"])
        self.assertIn("client_references", result["blockers"])
        self.assertFalse(result["authority"]["proposal_submitted"])

    def test_source_digest_must_match(self):
        e = copy.deepcopy(CURRENT)
        e["source_packet"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source packet mismatch"):
            q.evaluate(SPEC, e)

    def test_cannot_claim_references_without_sources(self):
        e = proven_fixture()
        e["client_references"] = [{"name": "r1", "source": "urn:test:r1"}]
        with self.assertRaisesRegex(ValueError, "client_references cannot be PROVEN"):
            q.evaluate(SPEC, e)

    def test_emerging_domain_needs_two_engagements(self):
        e = proven_fixture()
        e["comparable_engagements"] = [
            {"state": "COMPLETED", "source": "urn:test:e1", "safety_net_primary_care": True}
        ]
        with self.assertRaisesRegex(ValueError, "recent_domain_engagements cannot be PROVEN"):
            q.evaluate(SPEC, e)

    def test_full_source_bound_fixture_prime_ready(self):
        result = q.evaluate(SPEC, proven_fixture())
        self.assertEqual("PRIME_READY", result["state"])
        self.assertEqual([], result["blockers"])

    def test_deadline_passed_is_no_bid(self):
        e = proven_fixture()
        e["current_time"] = "2026-09-18T17:00:01-07:00"
        result = q.evaluate(SPEC, e)
        self.assertEqual("NO_BID", result["state"])
        self.assertEqual("deadline_passed", result["reason"])

    def test_teaming_requires_named_prime_and_support_proof(self):
        e = proven_fixture()
        e["bid_model"] = "healthcare_prime_subcontract"
        e["healthcare_prime"] = {
            "name": "Example Qualified Health Prime",
            "eligibility_source": "urn:test:eligibility",
            "safety_net_experience_source": "urn:test:safety-net",
            "relationship_authority": True
        }
        e["tjlabs_support_gate_ids"] = ["subject_matter_expertise", "technical_assistance_track_record"]
        result = q.evaluate(SPEC, e)
        self.assertEqual("TEAMING_READY", result["state"])

    def test_teaming_without_authorized_prime_holds(self):
        e = proven_fixture()
        e["bid_model"] = "healthcare_prime_subcontract"
        e["healthcare_prime"] = {}
        e["tjlabs_support_gate_ids"] = ["subject_matter_expertise"]
        result = q.evaluate(SPEC, e)
        self.assertEqual("HOLD", result["state"])
        self.assertIn("named_healthcare_prime", result["blockers"])

    def test_receipt_is_stable(self):
        result = q.evaluate(SPEC, CURRENT)
        self.assertEqual(q.canonical_digest(result), q.canonical_digest(copy.deepcopy(result)))


if __name__ == "__main__":
    unittest.main()
