from __future__ import annotations

import json
from pathlib import Path
import unittest

from revenue.tt_one_lab_lims_consultant.carrier import (
    CarrierError,
    compile_packet,
    example_owner_input,
    loads_strict,
    source_manifest_digest,
    verify_packet,
)

DIGESTS = [f"{i:064x}"[-64:] for i in range(1, 10)]
SOURCE = json.loads(
    Path(__file__).with_name("source_manifest.json").read_text(encoding="utf-8")
)


def complete_input():
    payload = example_owner_input()
    payload["candidate"].update(
        {
            "degree_evidence_digest": DIGESTS[0],
            "experience_years": 7,
            "experience_evidence_digest": DIGESTS[1],
            "reference_evidence_digests": DIGESTS[2:5],
            "nine_month_availability": True,
            "in_country_availability": True,
            "availability_evidence_digest": DIGESTS[5],
            "lims_health_system_evidence_digest": DIGESTS[6],
            "cross_sector_integration_evidence_digest": DIGESTS[7],
            "training_evidence_digest": DIGESTS[8],
            "conflict_disclosure": "NO_KNOWN_CONFLICT",
        }
    )
    payload["commercial"]["currency"] = "TTD"
    payload["commercial"]["all_inclusive_owner_confirmed"] = True
    for index, key in enumerate(payload["commercial"]["price_rows_minor"], start=1):
        payload["commercial"]["price_rows_minor"][key] = index * 100_000
    return payload


class CarrierTest(unittest.TestCase):
    def test_source_contract_keeps_price_rows_distinct_from_six_milestones(self):
        buyer = SOURCE["buyer_facts"]
        self.assertEqual(len(buyer["price_rows"]), 7)
        self.assertEqual(len(buyer["deliverables"]), 6)
        self.assertEqual(sum(buyer["evaluation_weights"].values()), 100)
        combined = buyer["deliverables"][2]
        self.assertEqual(combined["due"], "month 4")
        self.assertIn("Cross-Sector SOPs", combined["name"])
        self.assertIn("Recommendation for Adapting Existing LIMS", combined["name"])
        self.assertEqual(buyer["deliverables"][3]["due"], "month 7")
        self.assertEqual(buyer["deliverables"][4]["due"], "month 8")
        self.assertEqual(buyer["deliverables"][5]["due"], "month 9")

    def test_empty_owner_profile_holds_without_inventing(self):
        owner = example_owner_input()
        packet = compile_packet(owner)
        self.assertEqual(packet["posture"], "HOLD_OWNER_EVIDENCE")
        self.assertIn("OWNER_CREDENTIAL_EVIDENCE_INCOMPLETE", packet["blockers"])
        self.assertIn("OWNER_PRICING_INCOMPLETE", packet["blockers"])
        self.assertIn("CONFLICT_DISCLOSURE_UNRESOLVED", packet["blockers"])
        self.assertTrue(all(value is False for value in packet["authority"].values()))
        self.assertTrue(verify_packet(packet, owner))

    def test_complete_internal_packet_never_becomes_submission_authority(self):
        owner = complete_input()
        packet = compile_packet(owner)
        self.assertEqual(
            packet["posture"], "OWNER_REVIEW_PACKET_COMPLETE_NOT_SUBMISSION_AUTHORITY"
        )
        self.assertEqual(packet["blockers"], [])
        self.assertFalse(packet["authority"]["submission_authorized"])
        self.assertFalse(packet["authority"]["pricing_commitment_authorized"])
        self.assertFalse(packet["authority"]["buyer_contact_authorized"])

    def test_three_distinct_reference_evidence_receipts_required(self):
        owner = complete_input()
        owner["candidate"]["reference_evidence_digests"] = DIGESTS[2:4]
        packet = compile_packet(owner)
        self.assertFalse(
            packet["readiness"]["essential_owner_evidence_present"]["three_references"]
        )
        owner = complete_input()
        owner["candidate"]["reference_evidence_digests"] = [DIGESTS[2]] * 3
        with self.assertRaises(CarrierError):
            compile_packet(owner)

    def test_experience_bool_alias_rejected(self):
        owner = complete_input()
        owner["candidate"]["experience_years"] = True
        with self.assertRaises(CarrierError):
            compile_packet(owner)

    def test_price_bool_alias_rejected(self):
        owner = complete_input()
        first = next(iter(owner["commercial"]["price_rows_minor"]))
        owner["commercial"]["price_rows_minor"][first] = True
        with self.assertRaises(CarrierError):
            compile_packet(owner)

    def test_all_seven_price_rows_are_mandatory(self):
        owner = complete_input()
        owner["commercial"]["price_rows_minor"].pop(
            "End-User Training and Training Report"
        )
        with self.assertRaises(CarrierError):
            compile_packet(owner)

    def test_currency_and_extra_rows_fail_closed(self):
        owner = complete_input()
        owner["commercial"]["currency"] = "ttd"
        with self.assertRaises(CarrierError):
            compile_packet(owner)
        owner = complete_input()
        owner["commercial"]["price_rows_minor"]["Travel"] = 1
        with self.assertRaises(CarrierError):
            compile_packet(owner)

    def test_submission_route_typo_is_not_normalized(self):
        owner = complete_input()
        owner["submission"]["email"] = "procurement@heath.gov.tt"
        packet = compile_packet(owner)
        self.assertEqual(packet["posture"], "HOLD_OWNER_EVIDENCE")
        self.assertIn("SUBMISSION_METADATA_MISMATCH", packet["blockers"])
        self.assertEqual(
            packet["buyer"]["clarification_email_as_printed_in_pdf"],
            "procurement@heath.gov.tt",
        )
        self.assertTrue(packet["buyer"]["clarification_route_conflict"])

    def test_submission_subject_drift_holds(self):
        owner = complete_input()
        owner["submission"]["subject"] = "LIMS Consultant Proposal"
        packet = compile_packet(owner)
        self.assertIn("SUBMISSION_METADATA_MISMATCH", packet["blockers"])

    def test_ninety_day_validity_is_floor(self):
        owner = complete_input()
        owner["submission"]["validity_days"] = 89
        packet = compile_packet(owner)
        self.assertIn("SUBMISSION_METADATA_MISMATCH", packet["blockers"])

    def test_deadline_passed_is_terminal_internal_posture(self):
        owner = complete_input()
        owner["evaluated_at"] = "2026-10-01T10:00:01-04:00"
        packet = compile_packet(owner)
        self.assertEqual(packet["posture"], "NO_BID_DEADLINE_PASSED")
        self.assertIn("PROPOSAL_DEADLINE_PASSED", packet["blockers"])
        self.assertFalse(packet["authority"]["submission_authorized"])

    def test_offset_conversion_is_real_not_string_compare(self):
        owner = complete_input()
        owner["evaluated_at"] = "2026-10-01T13:59:59+00:00"
        packet = compile_packet(owner)
        self.assertNotIn("PROPOSAL_DEADLINE_PASSED", packet["blockers"])
        owner["evaluated_at"] = "2026-10-01T14:00:01+00:00"
        packet = compile_packet(owner)
        self.assertIn("PROPOSAL_DEADLINE_PASSED", packet["blockers"])

    def test_source_manifest_digest_is_required(self):
        owner = complete_input()
        owner["source_manifest_digest"] = "0" * 64
        with self.assertRaises(CarrierError):
            compile_packet(owner)
        self.assertEqual(len(source_manifest_digest()), 64)

    def test_transplanted_packet_does_not_verify(self):
        first = complete_input()
        packet = compile_packet(first)
        second = complete_input()
        second["candidate"]["experience_years"] = 8
        self.assertFalse(verify_packet(packet, second))

    def test_packet_tamper_does_not_verify(self):
        owner = complete_input()
        packet = compile_packet(owner)
        packet["posture"] = "SUBMISSION_READY"
        self.assertFalse(verify_packet(packet, owner))

    def test_duplicate_json_keys_fail_closed(self):
        with self.assertRaises(CarrierError):
            loads_strict('{"candidate": {}, "candidate": {}}')

    def test_nonfinite_json_fails_closed(self):
        with self.assertRaises(CarrierError):
            loads_strict('{"x": NaN}')

    def test_exact_key_contract_rejects_extra_authority_claim(self):
        owner = complete_input()
        owner["submission"]["send_authorized"] = True
        with self.assertRaises(CarrierError):
            compile_packet(owner)

    def test_availability_requires_evidence_receipt_not_boolean_only(self):
        owner = complete_input()
        owner["candidate"]["availability_evidence_digest"] = None
        packet = compile_packet(owner)
        essential = packet["readiness"]["essential_owner_evidence_present"]
        self.assertFalse(essential["nine_month_availability"])
        self.assertFalse(essential["in_country_availability"])

    def test_candidate_receipts_do_not_embed_reference_contacts(self):
        owner = complete_input()
        packet = compile_packet(owner)
        candidate = json.dumps(packet["candidate_evidence"], sort_keys=True)
        self.assertNotIn("@", candidate)
        self.assertNotIn("http", candidate)


if __name__ == "__main__":
    unittest.main()
