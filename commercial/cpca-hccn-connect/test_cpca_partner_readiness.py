import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = load_module("cpca_partner_readiness_test_target", ROOT / "cpca_partner_readiness.py")

MIN_SPEC = {
    "mandatory_direct_prime_gates": [
        {"id": "licensing_insurance"},
        {"id": "client_references"},
        {"id": "technical_assistance_track_record"},
        {"id": "group_training_track_record"},
        {"id": "submission_authority"},
    ],
    "service_type_specific_gate_ids": {
        "technical_assistance": ["technical_assistance_track_record"],
        "group_training": ["group_training_track_record"],
        "both": ["technical_assistance_track_record", "group_training_track_record"],
    },
}
REQUIRED = ["licensing_insurance", "client_references", "technical_assistance_track_record", "submission_authority"]


def digest(label):
    return hashlib.sha256(label.encode()).hexdigest()


def source(label):
    return {"source_id": f"urn:test:{label}", "sha256": digest(label)}


def evidence():
    return {
        "domain": "artificial_intelligence",
        "service_type": "technical_assistance",
        "bid_model": "healthcare_prime_subcontract",
        "healthcare_prime": {
            "name": "Example Qualified Health Prime",
            "eligibility_source": "urn:test:eligibility",
            "safety_net_experience_source": "urn:test:safety-net",
            "relationship_authority": True,
        },
        "tjlabs_support_gate_ids": ["technical_assistance_track_record"],
    }


def complete_manifest(e):
    return {
        "qualification_spec_sha256": p.canonical_digest(MIN_SPEC),
        "prime_legal_name": e["healthcare_prime"]["name"],
        "domain": e["domain"],
        "service_type": e["service_type"],
        "prime_identity_source": source("prime"),
        "relationship_authority_source": source("relationship"),
        "submission_authority_source": source("submission"),
        "application_package_source": source("package"),
        "gate_sources": {gate_id: [source(gate_id)] for gate_id in REQUIRED},
    }


def legacy(blockers):
    return {
        "state": "TEAMING_READY",
        "reason": "named_healthcare_prime_and_support_scope_proven",
        "gate_status": {gate_id: ("PROVEN" if gate_id not in blockers else "HOLD") for gate_id in REQUIRED},
        "blockers": list(blockers),
    }


class PartnerReadinessTests(unittest.TestCase):
    def test_bug_shaped_teaming_ready_becomes_discussion_only(self):
        e = evidence()
        result = p.compile_partner_readiness(MIN_SPEC, e, legacy(["licensing_insurance", "client_references"]))
        self.assertEqual("WORKSHARE_DISCUSSION_READY", result["state"])
        self.assertEqual("DISCUSSION_READY", result["workshare"]["state"])
        self.assertEqual("HOLD", result["application"]["state"])
        self.assertIn("licensing_insurance", result["application"]["blockers"])
        self.assertFalse(result["legacy_workshare_signal"]["application_authority"])

    def test_complete_legacy_gates_without_manifest_still_hold(self):
        e = evidence()
        result = p.compile_partner_readiness(MIN_SPEC, e, legacy([]))
        self.assertEqual("WORKSHARE_DISCUSSION_READY", result["state"])
        self.assertEqual("HOLD", result["application"]["state"])
        self.assertIn("partner_application_evidence", result["application"]["blockers"])

    def test_complete_caller_manifest_still_cannot_authorize_application(self):
        e = evidence()
        e["partner_application_evidence"] = complete_manifest(e)
        result = p.compile_partner_readiness(MIN_SPEC, e, legacy([]))
        self.assertEqual("WORKSHARE_DISCUSSION_READY", result["state"])
        self.assertEqual("HOLD", result["application"]["state"])
        self.assertIn("provider_authenticated_prime_application_evidence", result["application"]["blockers"])
        self.assertFalse(result["application"]["provider_authenticated_evidence_available"])
        self.assertFalse(result["application"]["caller_manifest_can_authorize_readiness"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_two_arbitrary_prime_strings_never_prove_application(self):
        e = evidence()
        result = p.compile_partner_readiness(MIN_SPEC, e, legacy(["submission_authority"]))
        self.assertNotEqual("APPLICATION_TEAMING_READY", result["state"])
        self.assertEqual("HOLD", result["application"]["state"])

    def test_manifest_is_bound_to_exact_spec_and_prime(self):
        e = evidence()
        e["partner_application_evidence"] = complete_manifest(e)
        e["partner_application_evidence"]["prime_legal_name"] = "Different Prime"
        result = p.compile_partner_readiness(MIN_SPEC, e, legacy([]))
        self.assertIn("prime_legal_name", result["application"]["blockers"])
        self.assertEqual("HOLD", result["application"]["state"])

    def test_malformed_source_object_fails_closed(self):
        e = evidence()
        e["partner_application_evidence"] = complete_manifest(e)
        e["partner_application_evidence"]["relationship_authority_source"]["sha256"] = "not-a-digest"
        with self.assertRaisesRegex(ValueError, "lowercase 64-hex"):
            p.compile_partner_readiness(MIN_SPEC, e, legacy([]))

    def test_receipt_tamper_cannot_verify(self):
        e = evidence()
        e["partner_application_evidence"] = complete_manifest(e)
        result = p.compile_partner_readiness(MIN_SPEC, e, legacy([]))
        result["receipt_sha256"] = p.canonical_digest(result)
        forged = copy.deepcopy(result)
        forged["application"]["state"] = "TEAMING_READY"
        self.assertNotEqual(forged["receipt_sha256"], p.canonical_digest({k: v for k, v in forged.items() if k != "receipt_sha256"}))

    def test_real_legacy_predecessor_cannot_promote_application(self):
        legacy_path = ROOT / "cpca_qualify.py"
        spec_path = ROOT / "qualification_spec.json"
        current_path = ROOT / "current_evidence.json"
        if not (legacy_path.exists() and spec_path.exists() and current_path.exists()):
            self.skipTest("repository integration files unavailable")
        q = load_module("cpca_qualify_real_predecessor", legacy_path)
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        e = json.loads(current_path.read_text(encoding="utf-8"))
        e["bid_model"] = "healthcare_prime_subcontract"
        e["healthcare_prime"] = {
            "name": "Example Qualified Health Prime",
            "eligibility_source": "urn:test:eligibility",
            "safety_net_experience_source": "urn:test:safety-net",
            "relationship_authority": True,
        }
        e["gate_status"]["subject_matter_expertise"] = "PROVEN"
        e.setdefault("gate_sources", {})["subject_matter_expertise"] = ["urn:test:subject-matter"]
        e["tjlabs_support_gate_ids"] = ["subject_matter_expertise"]
        old = q.evaluate(spec, e)
        self.assertEqual("TEAMING_READY", old["state"])
        self.assertTrue(old["blockers"])
        result = p.compile_partner_readiness(spec, e, old)
        self.assertEqual("WORKSHARE_DISCUSSION_READY", result["state"])
        self.assertEqual("HOLD", result["application"]["state"])
        self.assertTrue(result["application"]["blockers"])


if __name__ == "__main__":
    unittest.main()
