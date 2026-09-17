import copy
import hashlib
import importlib.util
import inspect
import json
import subprocess
import sys
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


def legacy(blockers=()):
    return {
        "schema": "cpca-hccn-qualification-result/v1",
        "state": "TEAMING_READY",
        "reason": "named_healthcare_prime_and_support_scope_proven",
        "domain": "artificial_intelligence",
        "service_type": "technical_assistance",
        "bid_model": "healthcare_prime_subcontract",
        "gate_status": {gate_id: ("PROVEN" if gate_id not in blockers else "HOLD") for gate_id in REQUIRED},
        "blockers": list(blockers),
    }


class PartnerReadinessTests(unittest.TestCase):
    def test_raw_predecessor_helper_is_private_and_discussion_only(self):
        self.assertFalse(hasattr(p, "compile_partner_readiness"))
        result = p._compile_partner_readiness(MIN_SPEC, evidence(), legacy(["licensing_insurance"]))
        self.assertEqual("WORKSHARE_DISCUSSION_READY", result["state"])
        self.assertEqual("DISCUSSION_READY", result["workshare"]["state"])
        self.assertEqual("HOLD", result["application"]["state"])
        self.assertFalse(result["legacy_workshare_signal"]["application_authority"])

    def test_complete_caller_manifest_still_cannot_authorize_application(self):
        e = evidence()
        e["partner_application_evidence"] = complete_manifest(e)
        result = p._compile_partner_readiness(MIN_SPEC, e, legacy())
        self.assertEqual("HOLD", result["application"]["state"])
        self.assertIn("provider_authenticated_prime_application_evidence", result["application"]["blockers"])
        self.assertFalse(result["application"]["provider_authenticated_evidence_available"])
        self.assertFalse(result["application"]["caller_manifest_can_authorize_readiness"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_manifest_is_bound_to_exact_spec_and_prime(self):
        e = evidence()
        e["partner_application_evidence"] = complete_manifest(e)
        e["partner_application_evidence"]["prime_legal_name"] = "Different Prime"
        result = p._compile_partner_readiness(MIN_SPEC, e, legacy())
        self.assertIn("prime_legal_name", result["application"]["blockers"])

    def test_malformed_source_object_fails_closed(self):
        e = evidence()
        e["partner_application_evidence"] = complete_manifest(e)
        e["partner_application_evidence"]["relationship_authority_source"]["sha256"] = "not-a-digest"
        with self.assertRaisesRegex(ValueError, "lowercase 64-hex"):
            p._compile_partner_readiness(MIN_SPEC, e, legacy())

    def test_legacy_result_origin_fields_are_not_optional(self):
        bad = legacy()
        del bad["domain"]
        with self.assertRaisesRegex(ValueError, "domain mismatch"):
            p._compile_partner_readiness(MIN_SPEC, evidence(), bad)

    def test_authorizing_api_has_no_legacy_or_spec_injection_parameter(self):
        self.assertEqual(["evidence"], list(inspect.signature(p.make_receipt).parameters))
        self.assertEqual(["evidence", "receipt"], list(inspect.signature(p.verify_receipt).parameters))
        self.assertEqual(["evidence"], list(inspect.signature(p.compile_from_evidence).parameters))

    def test_receipt_tamper_cannot_verify(self):
        synthetic = p._compile_partner_readiness(MIN_SPEC, evidence(), legacy())
        synthetic["bindings"] = {"evidence_sha256": digest("one")}
        synthetic["receipt_sha256"] = p.canonical_digest(synthetic)
        forged = copy.deepcopy(synthetic)
        forged["application"]["state"] = "TEAMING_READY"
        self.assertNotEqual(
            forged["receipt_sha256"],
            p.canonical_digest({k: v for k, v in forged.items() if k != "receipt_sha256"}),
        )

    def _repository_evidence(self, prime_name="Example Qualified Health Prime"):
        spec_path = ROOT / "qualification_spec.json"
        current_path = ROOT / "current_evidence.json"
        if not (spec_path.exists() and current_path.exists()):
            self.skipTest("repository integration files unavailable")
        e = json.loads(current_path.read_text(encoding="utf-8"))
        e["bid_model"] = "healthcare_prime_subcontract"
        e["healthcare_prime"] = {
            "name": prime_name,
            "eligibility_source": "urn:test:eligibility",
            "safety_net_experience_source": "urn:test:safety-net",
            "relationship_authority": True,
        }
        e["gate_status"]["subject_matter_expertise"] = "PROVEN"
        e.setdefault("gate_sources", {})["subject_matter_expertise"] = ["urn:test:subject-matter"]
        e["tjlabs_support_gate_ids"] = ["subject_matter_expertise"]
        return e

    def test_repository_authorizing_path_binds_exact_sources(self):
        e = self._repository_evidence()
        receipt = p.make_receipt(e)
        self.assertEqual("WORKSHARE_DISCUSSION_READY", receipt["state"])
        self.assertEqual("HOLD", receipt["application"]["state"])
        self.assertTrue(p.verify_receipt(e, receipt))
        self.assertEqual(p.CANONICAL_SPEC_GIT_BLOB_SHA1, receipt["bindings"]["qualification_spec_git_blob_sha1"])
        self.assertEqual(p.CANONICAL_LEGACY_GIT_BLOB_SHA1, receipt["bindings"]["legacy_implementation_git_blob_sha1"])
        self.assertEqual(p.canonical_digest(e), receipt["bindings"]["evidence_sha256"])
        self.assertEqual("Example Qualified Health Prime", receipt["bindings"]["prime_legal_name"])
        self.assertTrue(all(value is False for value in receipt["authority"].values()))

    def test_receipt_transplant_across_distinct_primes_is_rejected(self):
        one = self._repository_evidence("Prime One")
        two = self._repository_evidence("Prime Two")
        receipt_one = p.make_receipt(one)
        receipt_two = p.make_receipt(two)
        self.assertNotEqual(receipt_one["receipt_sha256"], receipt_two["receipt_sha256"])
        self.assertNotEqual(receipt_one["bindings"]["evidence_sha256"], receipt_two["bindings"]["evidence_sha256"])
        self.assertFalse(p.verify_receipt(two, receipt_one))
        self.assertFalse(p.verify_receipt(one, receipt_two))

    def test_source_manifest_transplant_is_rejected(self):
        one = self._repository_evidence()
        two = copy.deepcopy(one)
        two["gate_sources"]["subject_matter_expertise"] = ["urn:test:different-source"]
        receipt = p.make_receipt(one)
        self.assertFalse(p.verify_receipt(two, receipt))
        self.assertNotEqual(
            receipt["bindings"]["source_manifest_sha256"],
            p.make_receipt(two)["bindings"]["source_manifest_sha256"],
        )

    def test_cli_rejects_legacy_and_spec_injection(self):
        current_path = ROOT / "current_evidence.json"
        if not current_path.exists():
            self.skipTest("repository integration files unavailable")
        for flag in ("--legacy", "--spec"):
            proc = subprocess.run(
                [sys.executable, str(ROOT / "cpca_partner_readiness.py"), str(current_path), flag, "evil"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=30,
            )
            self.assertNotEqual(0, proc.returncode)
            self.assertIn("unrecognized arguments", proc.stderr)

    def test_pinned_legacy_blob_mismatch_fails_before_execution(self):
        original = p.CANONICAL_LEGACY_GIT_BLOB_SHA1
        try:
            p.CANONICAL_LEGACY_GIT_BLOB_SHA1 = "0" * 40
            with self.assertRaisesRegex(ValueError, "reviewed source blob mismatch"):
                p.make_receipt(self._repository_evidence())
        finally:
            p.CANONICAL_LEGACY_GIT_BLOB_SHA1 = original


if __name__ == "__main__":
    unittest.main()
