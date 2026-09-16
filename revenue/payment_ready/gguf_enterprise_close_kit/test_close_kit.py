from __future__ import annotations

import copy
import unittest
from pathlib import Path

from close_kit import (
    ACCEPTANCE_IDS,
    AUTHORITY_FALSE,
    ContractError,
    canonical_json,
    compile_close_packet,
    evaluate_acceptance,
    load_authority,
    sha256_hex,
    strict_load,
    strict_loads,
    validate_authority_docs,
    validate_intake,
    verify_close_packet,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
INTAKE = HERE / "fixtures" / "synthetic_intake.json"
EVIDENCE = HERE / "fixtures" / "synthetic_delivery_evidence.json"
OPERATING = HERE / "operating_manifest.json"
PACK = REPO / "revenue" / "payment_ready" / "pack.json"
RECOVERY = REPO / "revenue" / "payment_ready" / "recovery.json"


def intake():
    return strict_load(INTAKE)


def evidence():
    return strict_load(EVIDENCE)


def authority():
    return load_authority(REPO)


class AuthorityTests(unittest.TestCase):
    def test_current_main_offer_is_bound(self):
        result = authority()
        self.assertEqual(result["offer_id"], "gguf-diagnostic-10d-12k")
        self.assertEqual(result["fixed_amount_usd"], 12000)
        self.assertEqual(result["term_calendar_days"], 10)
        self.assertEqual(result["m1_amount_usd"], 6000)
        self.assertEqual(result["m2_amount_usd"], 6000)
        self.assertEqual(result["m2_due"], "on AT1-AT6 acceptance")
        self.assertEqual(result["currency"], "USD")
        self.assertEqual(result["acceptance_ids"], list(ACCEPTANCE_IDS))
        self.assertEqual(result["public_surface_kind"], "PURCHASE_INTENT_ONLY")
        self.assertFalse(result["payment_collection_on_public_surface"])
        for field in AUTHORITY_FALSE:
            self.assertFalse(result[field])

    def test_price_drift_fails_closed(self):
        pack = strict_load(PACK)
        recovery = strict_load(RECOVERY)
        pack["offer"]["fixed_amount"] = 11999
        with self.assertRaises(ContractError):
            validate_authority_docs(pack, recovery)

    def test_m1_boundary_drift_fails_closed(self):
        pack = strict_load(PACK)
        recovery = strict_load(RECOVERY)
        pack["offer"]["milestones"][0]["due"] = "after file transfer"
        with self.assertRaises(ContractError):
            validate_authority_docs(pack, recovery)

    def test_at_set_drift_fails_closed(self):
        pack = strict_load(PACK)
        recovery = strict_load(RECOVERY)
        recovery["offer"]["acceptance_tests"][-1] = "AT7"
        with self.assertRaises(ContractError):
            validate_authority_docs(pack, recovery)

    def test_m2_due_term_is_bound(self):
        pack = strict_load(PACK)
        recovery = strict_load(RECOVERY)
        pack["offer"]["milestones"][1]["due"] = "on metric lift"
        with self.assertRaises(ContractError):
            validate_authority_docs(pack, recovery)

    def test_currency_drift_fails_closed(self):
        pack = strict_load(PACK)
        recovery = strict_load(RECOVERY)
        pack["offer"]["currency"] = "EUR"
        with self.assertRaises(ContractError):
            validate_authority_docs(pack, recovery)

    def test_public_surface_cannot_become_checkout_by_drift(self):
        pack = strict_load(PACK)
        recovery = strict_load(RECOVERY)
        pack["offer"]["payment_collection"] = "STRIPE_LINK"
        with self.assertRaises(ContractError):
            validate_authority_docs(pack, recovery)


class IntakeTests(unittest.TestCase):
    def test_synthetic_intake_is_metadata_only_and_review_ready(self):
        result = validate_intake(intake())
        self.assertEqual(result["qualification_state"], "READY_FOR_OWNER_PRIVATE_REVIEW")
        self.assertEqual(result["gguf_size_bytes"], 4294967296)
        self.assertTrue(all(result["external_prerequisite_receipts_present"].values()))
        for field in AUTHORITY_FALSE:
            self.assertFalse(result[field])

    def test_missing_external_prerequisites_holds_before_file_transfer(self):
        doc = intake()
        doc["external_evidence"] = {
            "nda_receipt_sha256": "NONE",
            "sow_receipt_sha256": "NONE",
            "m1_payment_receipt_sha256": "NONE",
        }
        result = validate_intake(doc)
        self.assertEqual(result["qualification_state"], "HOLD")
        self.assertEqual(
            result["holds"],
            ["HOLD_NDA_EXTERNAL_EVIDENCE", "HOLD_SOW_EXTERNAL_EVIDENCE", "HOLD_M1_EXTERNAL_EVIDENCE"],
        )
        self.assertFalse(result["private_file_transfer_authorized"])

    def test_control_attestation_must_be_real_bool(self):
        doc = intake()
        doc["gguf"]["control_attested"] = 1
        with self.assertRaises(ContractError):
            validate_intake(doc)

    def test_metric_lift_guarantee_is_term_conflict(self):
        doc = intake()
        doc["scope"]["metric_lift_guaranteed"] = True
        with self.assertRaises(ContractError):
            validate_intake(doc)

    def test_public_contact_url_cannot_hide_query_data(self):
        doc = intake()
        doc["security"]["public_contact_url"] = "https://example.com/contact?email=private@example.com"
        with self.assertRaises(ContractError):
            validate_intake(doc)

    def test_retention_is_bounded_to_30_days(self):
        doc = intake()
        doc["security"]["retention_days"] = 31
        with self.assertRaises(ContractError):
            validate_intake(doc)

    def test_credentials_required_false_is_a_valid_boundary_flag(self):
        doc = intake()
        self.assertFalse(doc["security"]["credentials_required"])
        result = validate_intake(doc)
        self.assertEqual(result["qualification_state"], "READY_FOR_OWNER_PRIVATE_REVIEW")

    def test_raw_model_public_allowed_false_is_a_valid_boundary_flag(self):
        doc = intake()
        self.assertFalse(doc["security"]["raw_model_public_allowed"])
        result = validate_intake(doc)
        self.assertEqual(result["qualification_state"], "READY_FOR_OWNER_PRIVATE_REVIEW")

    def test_raw_model_field_is_rejected_as_sensitive(self):
        doc = intake()
        doc["gguf"]["raw_model"] = "do-not-store-this"
        with self.assertRaises(ContractError):
            validate_intake(doc)

    def test_raw_sensitive_field_is_rejected_before_schema_use(self):
        doc = intake()
        doc["password"] = "do-not-store-this"
        with self.assertRaises(ContractError):
            validate_intake(doc)


class AcceptanceTests(unittest.TestCase):
    def test_synthetic_evidence_covers_at1_through_at6(self):
        result = evaluate_acceptance(intake(), evidence())
        self.assertEqual(result["failed_tests"], [])
        self.assertTrue(all(result["tests"].values()))
        self.assertEqual(result["verdict"], "AT1_AT6_EVIDENCE_READY_FOR_CUSTOMER_REVIEW")
        self.assertFalse(result["payment_reference_proves_acceptance"])
        self.assertFalse(result["AT4_verified_receipt_binding"])
        self.assertFalse(result["AT6_verified_receipt_binding"])
        for field in AUTHORITY_FALSE:
            self.assertFalse(result[field])

    def test_restore_sha_mismatch_holds_at3(self):
        doc = evidence()
        doc["artifacts"]["restored"]["sha256"] = "7777777777777777777777777777777777777777777777777777777777777777"
        doc["delivery_receipt"]["artifact_hashes"][-1] = "7777777777777777777777777777777777777777777777777777777777777777"
        result = evaluate_acceptance(intake(), doc)
        self.assertFalse(result["tests"]["AT3"])
        self.assertEqual(result["verdict"], "HOLD_ACCEPTANCE_EVIDENCE")

    def test_same_ablation_hash_holds_at2(self):
        doc = evidence()
        doc["artifacts"]["ablated"]["sha256"] = doc["artifacts"]["original"]["sha256"]
        result = evaluate_acceptance(intake(), doc)
        self.assertFalse(result["tests"]["AT2"])
        self.assertEqual(result["verdict"], "HOLD_ACCEPTANCE_EVIDENCE")

    def test_delivery_receipt_must_bind_report_hash(self):
        doc = evidence()
        doc["delivery_receipt"]["artifact_hashes"][-2] = "7777777777777777777777777777777777777777777777777777777777777777"
        result = evaluate_acceptance(intake(), doc)
        self.assertFalse(result["tests"]["AT6"])

    def test_random_delivery_receipt_hash_is_not_verified_binding(self):
        doc = evidence()
        doc["delivery_receipt"]["receipt_sha256"] = "7777777777777777777777777777777777777777777777777777777777777777"
        result = evaluate_acceptance(intake(), doc)
        self.assertFalse(result["tests"]["AT6"])
        self.assertFalse(result["AT6_verified_receipt_binding"])
        self.assertEqual(result["verdict"], "HOLD_ACCEPTANCE_EVIDENCE")

    def test_engagement_identity_cannot_cross_contaminate(self):
        doc = evidence()
        doc["engagement_id"] = "other-engagement"
        with self.assertRaises(ContractError):
            evaluate_acceptance(intake(), doc)

    def test_payment_reference_presence_does_not_accept(self):
        doc = evidence()
        doc["payment_reference_sha256"] = "7777777777777777777777777777777777777777777777777777777777777777"
        result = evaluate_acceptance(intake(), doc)
        self.assertTrue(result["payment_reference_present"])
        self.assertFalse(result["payment_reference_proves_acceptance"])
        self.assertFalse(result["customer_acceptance_recorded"])


class ClosePacketTests(unittest.TestCase):
    def test_complete_synthetic_packet_stops_at_customer_review(self):
        auth = authority()
        packet = compile_close_packet(auth, intake(), evidence())
        self.assertEqual(packet["state"], "READY_FOR_CUSTOMER_ACCEPTANCE_REVIEW")
        self.assertTrue(packet["customer_acceptance_required"])
        self.assertTrue(packet["customer_acceptance_is_external_event"])
        for field in AUTHORITY_FALSE:
            self.assertFalse(packet[field])
        self.assertTrue(verify_close_packet(packet, auth, intake(), evidence()))

    def test_close_packet_tamper_is_detected(self):
        auth = authority()
        packet = compile_close_packet(auth, intake(), evidence())
        packet["state"] = "ACCEPTED"
        self.assertFalse(verify_close_packet(packet, auth, intake(), evidence()))

    def test_forged_authority_terms_fail_even_with_recomputed_receipt(self):
        auth = authority()
        auth["fixed_amount_usd"] = 1
        unsigned = dict(auth)
        unsigned.pop("receipt_sha256", None)
        auth["receipt_sha256"] = sha256_hex(canonical_json(unsigned))
        with self.assertRaises(ContractError):
            compile_close_packet(auth, intake(), evidence())

    def test_forged_source_digests_and_truth_fail_even_with_recomputed_receipt(self):
        auth = authority()
        auth["pack_sha256"] = "7777777777777777777777777777777777777777777777777777777777777777"
        auth["canonical_collected_cash_usd"] = 12000
        unsigned = dict(auth)
        unsigned.pop("receipt_sha256", None)
        auth["receipt_sha256"] = sha256_hex(canonical_json(unsigned))
        with self.assertRaises(ContractError):
            compile_close_packet(auth, intake(), evidence())

    def test_incomplete_intake_never_authorizes_transfer(self):
        doc = intake()
        doc["external_evidence"]["m1_payment_receipt_sha256"] = "NONE"
        packet = compile_close_packet(authority(), doc, evidence())
        self.assertEqual(packet["state"], "HOLD")
        self.assertFalse(packet["private_file_transfer_authorized"])


class SerializationAndManifestTests(unittest.TestCase):
    def test_duplicate_json_key_is_rejected(self):
        with self.assertRaises(ContractError):
            strict_loads('{"a":1,"a":2}')

    def test_nonfinite_json_is_rejected(self):
        with self.assertRaises(ContractError):
            strict_loads('{"a":NaN}')

    def test_operating_manifest_keeps_10_day_and_authority_boundaries(self):
        manifest = strict_load(OPERATING)
        self.assertEqual(manifest["offer_id"], "gguf-diagnostic-10d-12k")
        self.assertEqual(manifest["commercial_terms"]["fixed_amount_usd"], 12000)
        self.assertEqual(manifest["commercial_terms"]["term_calendar_days"], 10)
        self.assertEqual(len(manifest["days"]), 10)
        self.assertEqual([row["day"] for row in manifest["days"]], list(range(1, 11)))
        self.assertGreaterEqual(len(manifest["hard_stops"]), 8)
        self.assertEqual(manifest["security"]["private_transfer"], "OWNER_PRIVATE_EXTERNAL")
        for field in AUTHORITY_FALSE:
            self.assertFalse(manifest["authority"][field])


if __name__ == "__main__":
    unittest.main()
