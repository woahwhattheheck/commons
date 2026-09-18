import copy
import hashlib
import importlib.util
import json
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("mcc_gate", HERE / "pursuit_gate.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

NOW = "2026-09-17T21:25:00-04:00"


class MCCPursuitGateTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads(
            (HERE / "current_packet.json").read_text(encoding="utf-8")
        )

    def test_current_packet_is_fail_closed_and_partner_first(self):
        out = gate.compile_packet(self.packet, evaluated_at=NOW)
        self.assertEqual(out["state"], "HOLD_MISSING_BUYER_PACKAGE")
        self.assertFalse(out["buyer_package_present"])
        self.assertFalse(out["prime_evidence_present"])
        self.assertFalse(out["direct_prime_ready"])
        self.assertEqual(out["partner_candidates"][0]["status"], "PUBLIC_FIT_ONLY")
        self.assertEqual(out["workshare"]["amount_cents"], 2_400_000)
        self.assertEqual(out["workshare"]["status"], "PROPOSED_NOT_ACCEPTED")
        self.assertTrue(out["question_window_open"])
        self.assertTrue(out["response_window_open"])
        self.assertTrue(all(v is False for v in out["authority"].values()))
        self.assertTrue(gate.verify_packet(self.packet, out, evaluated_at=NOW))

    def test_snapshot_digests_match_exact_files(self):
        root = HERE.parents[1]
        for row in self.packet["secondary_sources"]:
            path = row["locator"].removeprefix("file:")
            data = (root / path).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])
        for candidate in self.packet["partner_candidates"]:
            for row in candidate["public_fit_sources"]:
                path = row["locator"].removeprefix("file:")
                data = (root / path).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])

    def test_secondary_discovery_cannot_masquerade_as_buyer_package(self):
        packet = copy.deepcopy(self.packet)
        packet["buyer_authoritative_sources"] = packet["secondary_sources"]
        packet["secondary_sources"] = []
        with self.assertRaises(gate.GateError):
            gate.compile_packet(packet, evaluated_at=NOW)

    def test_public_partner_fit_is_not_solicitation_qualification(self):
        out = gate.compile_packet(copy.deepcopy(self.packet), evaluated_at=NOW)
        self.assertEqual(out["partner_candidates"][0]["status"], "PUBLIC_FIT_ONLY")
        self.assertEqual(
            out["partner_candidates"][0]["solicitation_qualification_count"], 0
        )

    def test_prime_evidence_cannot_override_missing_buyer_package(self):
        packet = copy.deepcopy(self.packet)
        packet["prime_evidence"]["experience_evidence"] = [
            {
                "kind": "RELEVANT_EXPERIENCE",
                "subject": "five-year evidence",
                "sha256": "a" * 64,
                "locator": "file:experience.json",
            }
        ]
        packet["prime_evidence"]["higher_ed_reference_evidence"] = [
            {
                "kind": "HIGHER_ED_REFERENCE",
                "subject": f"school-{i}",
                "sha256": str(i) * 64,
                "locator": f"file:ref-{i}.json",
            }
            for i in range(1, 4)
        ]
        out = gate.compile_packet(packet, evaluated_at=NOW)
        self.assertTrue(out["prime_evidence_present"])
        self.assertFalse(out["direct_prime_ready"])
        self.assertEqual(out["state"], "HOLD_MISSING_BUYER_PACKAGE")

    def test_buyer_package_without_prime_evidence_still_holds(self):
        packet = copy.deepcopy(self.packet)
        packet["buyer_authoritative_sources"] = [
            {
                "kind": "BUYER_PACKAGE",
                "locator": "file:buyer.docx",
                "sha256": "b" * 64,
                "captured_at": NOW,
            }
        ]
        out = gate.compile_packet(packet, evaluated_at=NOW)
        self.assertTrue(out["buyer_package_present"])
        self.assertEqual(out["state"], "HOLD_PRIME_QUALIFICATION")
        self.assertFalse(out["direct_prime_ready"])

    def test_duplicate_reference_subjects_do_not_satisfy_three_reference_gate(self):
        packet = copy.deepcopy(self.packet)
        packet["buyer_authoritative_sources"] = [
            {
                "kind": "BUYER_PACKAGE",
                "locator": "file:buyer.docx",
                "sha256": "b" * 64,
                "captured_at": NOW,
            }
        ]
        packet["prime_evidence"]["experience_evidence"] = [
            {
                "kind": "RELEVANT_EXPERIENCE",
                "subject": "experience",
                "sha256": "c" * 64,
                "locator": "file:exp.json",
            }
        ]
        packet["prime_evidence"]["higher_ed_reference_evidence"] = [
            {
                "kind": "HIGHER_ED_REFERENCE",
                "subject": "same-school",
                "sha256": str(i) * 64,
                "locator": f"file:r{i}.json",
            }
            for i in range(1, 4)
        ]
        out = gate.compile_packet(packet, evaluated_at=NOW)
        self.assertFalse(out["prime_evidence_present"])
        self.assertEqual(out["state"], "HOLD_PRIME_QUALIFICATION")

    def test_bool_is_not_integer_price(self):
        packet = copy.deepcopy(self.packet)
        packet["workshare"]["amount_cents"] = True
        with self.assertRaises(gate.GateError):
            gate.compile_packet(packet, evaluated_at=NOW)

    def test_deadline_requires_timezone_and_order(self):
        packet = copy.deepcopy(self.packet)
        packet["deadlines"]["questions_due"] = "2026-09-25T17:00:00"
        with self.assertRaises(gate.GateError):
            gate.compile_packet(packet, evaluated_at=NOW)

        packet = copy.deepcopy(self.packet)
        packet["deadlines"]["questions_due"] = "2026-10-06T17:00:00-05:00"
        with self.assertRaises(gate.GateError):
            gate.compile_packet(packet, evaluated_at=NOW)

    def test_external_authority_is_not_an_input_surface(self):
        packet = copy.deepcopy(self.packet)
        packet["authority"] = {"proposal_submission_authorized": True}
        with self.assertRaises(gate.GateError):
            gate.compile_packet(packet, evaluated_at=NOW)

    def test_compiled_tamper_fails_verification(self):
        out = gate.compile_packet(self.packet, evaluated_at=NOW)
        tampered = copy.deepcopy(out)
        tampered["authority"]["partner_contact_authorized"] = True
        tampered["receipt_sha256"] = "0" * 64
        self.assertFalse(gate.verify_packet(self.packet, tampered, evaluated_at=NOW))

    def test_strict_json_duplicate_key_rejected(self):
        with self.assertRaises(gate.GateError):
            gate.loads_strict('{"x":1,"x":2}')


if __name__ == "__main__":
    unittest.main()
