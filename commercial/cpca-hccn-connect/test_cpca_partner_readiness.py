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


def load_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


p = load_module("cpca_partner_readiness_test_target", ROOT / "cpca_partner_readiness.py")


def digest(label):
    return hashlib.sha256(label.encode()).hexdigest()


def source(label):
    return {"source_id": f"urn:test:{label}", "sha256": digest(label)}


def teaming_case():
    spec = load_json("qualification_spec.json")
    evidence = load_json("current_evidence.json")
    evidence["bid_model"] = "healthcare_prime_subcontract"
    evidence["healthcare_prime"] = {
        "name": "Example Qualified Health Prime",
        "eligibility_source": "urn:test:eligibility",
        "safety_net_experience_source": "urn:test:safety-net",
        "relationship_authority": True,
    }
    evidence["gate_status"]["subject_matter_expertise"] = "PROVEN"
    evidence.setdefault("gate_sources", {})["subject_matter_expertise"] = ["urn:test:subject-matter"]
    evidence["tjlabs_support_gate_ids"] = ["subject_matter_expertise"]
    return spec, evidence


def required_gate_ids(spec, service_type):
    specific = set(spec["service_type_specific_gate_ids"][service_type])
    track = {"technical_assistance_track_record", "group_training_track_record"}
    return [
        row["id"]
        for row in spec["mandatory_direct_prime_gates"]
        if row["id"] not in track or row["id"] in specific
    ]


def complete_manifest(spec, evidence):
    required = required_gate_ids(spec, evidence["service_type"])
    return {
        "qualification_spec_sha256": p.canonical_digest(spec),
        "prime_legal_name": evidence["healthcare_prime"]["name"],
        "domain": evidence["domain"],
        "service_type": evidence["service_type"],
        "prime_identity_source": source("prime"),
        "relationship_authority_source": source("relationship"),
        "submission_authority_source": source("submission"),
        "application_package_source": source("package"),
        "gate_sources": {gate_id: [source(gate_id)] for gate_id in required},
    }


def fake_legacy(blockers=()):
    return {
        "state": "TEAMING_READY",
        "reason": "caller_fabricated_teaming_ready",
        "gate_status": {"subject_matter_expertise": "PROVEN"},
        "blockers": list(blockers),
    }


class PartnerReadinessTests(unittest.TestCase):
    def test_code_owned_predecessor_teaming_signal_is_discussion_only(self):
        spec, evidence = teaming_case()
        receipt = p.make_receipt(spec, evidence)
        self.assertEqual("WORKSHARE_DISCUSSION_READY", receipt["state"])
        self.assertEqual("DISCUSSION_READY", receipt["workshare"]["state"])
        self.assertTrue(receipt["workshare"]["source_bound"])
        self.assertEqual("HOLD", receipt["application"]["state"])
        self.assertIn("provider_authenticated_prime_application_evidence", receipt["application"]["blockers"])
        self.assertFalse(receipt["legacy_workshare_signal"]["application_authority"])
        self.assertTrue(all(value is False for value in receipt["authority"].values()))

    def test_complete_caller_manifest_still_cannot_authorize_application(self):
        spec, evidence = teaming_case()
        evidence["partner_application_evidence"] = complete_manifest(spec, evidence)
        receipt = p.make_receipt(spec, evidence)
        self.assertEqual("WORKSHARE_DISCUSSION_READY", receipt["state"])
        self.assertEqual("HOLD", receipt["application"]["state"])
        self.assertIn("provider_authenticated_prime_application_evidence", receipt["application"]["blockers"])
        self.assertFalse(receipt["application"]["provider_authenticated_evidence_available"])
        self.assertFalse(receipt["application"]["caller_manifest_can_authorize_readiness"])
        self.assertTrue(receipt["binding"]["application_manifest"]["present"])
        self.assertGreater(len(receipt["binding"]["application_manifest"]["sources"]), 4)

    def test_public_raw_legacy_result_is_non_authorizing(self):
        spec, evidence = teaming_case()
        result = p.compile_partner_readiness(spec, evidence, fake_legacy())
        self.assertEqual("HOLD", result["state"])
        self.assertEqual("HOLD", result["workshare"]["state"])
        self.assertFalse(result["workshare"]["source_bound"])
        self.assertFalse(result["legacy_workshare_signal"]["trusted_origin"])
        self.assertEqual(["trusted_legacy_predecessor_required"], result["application"]["blockers"])
        self.assertIsNone(result["binding"])

    def test_noncanonical_spec_substitution_fails_closed(self):
        spec, evidence = teaming_case()
        forged_spec = copy.deepcopy(spec)
        forged_spec["receipt_test_marker"] = "weaker-caller-spec"
        with self.assertRaisesRegex(ValueError, "code-owned canonical specification"):
            p.make_receipt(forged_spec, evidence)

    def test_cross_prime_receipt_transplant_is_rejected_even_when_state_collides(self):
        spec, evidence = teaming_case()
        receipt = p.make_receipt(spec, evidence)
        other = copy.deepcopy(evidence)
        other["healthcare_prime"]["name"] = "Different Qualified Health Prime"
        other_receipt = p.make_receipt(spec, other)
        self.assertEqual(receipt["state"], other_receipt["state"])
        self.assertNotEqual(receipt["binding"]["prime"], other_receipt["binding"]["prime"])
        self.assertFalse(p.verify_receipt(spec, other, receipt))

    def test_cross_evidence_receipt_transplant_is_rejected_even_when_state_collides(self):
        spec, evidence = teaming_case()
        receipt = p.make_receipt(spec, evidence)
        other = copy.deepcopy(evidence)
        other.setdefault("evidence_notes", []).append("different retained note generation")
        other_receipt = p.make_receipt(spec, other)
        self.assertEqual(receipt["state"], other_receipt["state"])
        self.assertNotEqual(receipt["binding"]["evidence_sha256"], other_receipt["binding"]["evidence_sha256"])
        self.assertFalse(p.verify_receipt(spec, other, receipt))

    def test_cross_source_manifest_receipt_transplant_is_rejected(self):
        spec, evidence = teaming_case()
        evidence["partner_application_evidence"] = complete_manifest(spec, evidence)
        receipt = p.make_receipt(spec, evidence)
        other = copy.deepcopy(evidence)
        other["partner_application_evidence"]["prime_identity_source"] = source("different-prime-source")
        other_receipt = p.make_receipt(spec, other)
        self.assertEqual(receipt["state"], other_receipt["state"])
        self.assertNotEqual(
            receipt["binding"]["application_manifest"]["sha256"],
            other_receipt["binding"]["application_manifest"]["sha256"],
        )
        self.assertFalse(p.verify_receipt(spec, other, receipt))

    def test_legacy_implementation_is_code_owned_and_digest_bound(self):
        spec, evidence = teaming_case()
        receipt = p.make_receipt(spec, evidence)
        expected = hashlib.sha256((ROOT / "cpca_qualify.py").read_bytes()).hexdigest()
        self.assertEqual(expected, receipt["binding"]["legacy_implementation"]["sha256"])
        self.assertEqual("cpca_qualify.py", receipt["binding"]["legacy_implementation"]["path"])
        with self.assertRaises(TypeError):
            p.make_receipt(spec, evidence, ROOT / "replacement_legacy.py")
        with self.assertRaises(TypeError):
            p.verify_receipt(spec, evidence, receipt, ROOT / "replacement_legacy.py")

    def test_rehashed_forged_application_state_fails_semantic_verify(self):
        spec, evidence = teaming_case()
        receipt = p.make_receipt(spec, evidence)
        forged = copy.deepcopy(receipt)
        forged["application"]["state"] = "TEAMING_READY"
        unsigned = dict(forged)
        unsigned.pop("receipt_sha256")
        forged["receipt_sha256"] = p.canonical_digest(unsigned)
        self.assertFalse(p.verify_receipt(spec, evidence, forged))

    def test_malformed_application_source_object_fails_closed(self):
        spec, evidence = teaming_case()
        evidence["partner_application_evidence"] = complete_manifest(spec, evidence)
        evidence["partner_application_evidence"]["relationship_authority_source"]["sha256"] = "not-a-digest"
        with self.assertRaisesRegex(ValueError, "lowercase 64-hex"):
            p.make_receipt(spec, evidence)

    def test_exact_receipt_verifies_and_binds_canonical_spec_file(self):
        spec, evidence = teaming_case()
        receipt = p.make_receipt(spec, evidence)
        self.assertTrue(p.verify_receipt(spec, evidence, receipt))
        self.assertEqual(p.canonical_digest(spec), receipt["binding"]["qualification_spec_sha256"])
        self.assertEqual(
            hashlib.sha256((ROOT / "qualification_spec.json").read_bytes()).hexdigest(),
            receipt["binding"]["qualification_spec_file_sha256"],
        )
        self.assertEqual(
            spec["source_packet"]["sha256"],
            receipt["binding"]["qualification_source_packet"]["sha256"],
        )

    def test_receipt_binds_exact_predecessor_result(self):
        spec, evidence = teaming_case()
        receipt = p.make_receipt(spec, evidence)
        q = load_module("cpca_qualify_reference_for_digest", ROOT / "cpca_qualify.py")
        legacy_result = q.evaluate(copy.deepcopy(spec), copy.deepcopy(evidence))
        self.assertEqual("TEAMING_READY", legacy_result["state"])
        self.assertEqual(p.canonical_digest(legacy_result), receipt["binding"]["legacy_result_sha256"])

    def test_cli_rejects_removed_legacy_override(self):
        spec, evidence = teaming_case()
        temp = ROOT / ".cpca_partner_readiness_test_evidence.json"
        try:
            temp.write_text(json.dumps(evidence), encoding="utf-8")
            with self.assertRaises(SystemExit) as raised:
                p.main([str(temp), "--legacy", str(ROOT / "cpca_qualify.py")])
            self.assertNotEqual(0, raised.exception.code)
        finally:
            temp.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
