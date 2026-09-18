from __future__ import annotations

import copy
import unittest
from pathlib import Path

from umissouri_27_0012 import (
    AUTHORITY_FALSE,
    CASE_SCHEMA,
    ContractError,
    compile_bundle,
    evaluate_matrix,
    evaluate_partner,
    evaluate_reconciliation_case,
    strict_load,
    strict_loads,
    validate_manifest,
    verify_bundle,
)

ROOT = Path(__file__).resolve().parent
FIXTURES = strict_load(ROOT / "fixtures.json")
AS_OF = "2026-09-18T01:45:00Z"


def manifest():
    return copy.deepcopy(FIXTURES["manifest"])


def partners():
    return copy.deepcopy(FIXTURES["partners"])


def matrix():
    return copy.deepcopy(FIXTURES["matrix"])


def base_case(**updates):
    case = {
        "schema": CASE_SCHEMA,
        "case_id": "case-base-001",
        "merchant_id": "merchant-synthetic-001",
        "settlement_file_present": True,
        "processor_total_cents": 125000,
        "erp_total_cents": 125000,
        "gl_mapping_complete": True,
        "unresolved_chargeback_count": 0,
        "payables_supplier_match": True,
        "future_erp_contract_evidenced": True,
        "audit_chain_complete": True,
        "sensitive_cardholder_data_present": False,
        "observed_at_utc": "2026-09-18T01:00:00Z",
    }
    case.update(updates)
    return case


class StrictJsonTests(unittest.TestCase):
    def test_duplicate_key_rejected(self):
        with self.assertRaises(ContractError):
            strict_loads('{"a":1,"a":2}')

    def test_nonfinite_rejected(self):
        with self.assertRaises(ContractError):
            strict_loads('{"a":NaN}')

    def test_bool_int_alias_rejected(self):
        with self.assertRaises(ContractError):
            evaluate_reconciliation_case(
                base_case(unresolved_chargeback_count=False),
                AS_OF,
            )

    def test_unknown_case_key_rejected(self):
        case = base_case()
        case["unexpected"] = True
        with self.assertRaises(ContractError):
            evaluate_reconciliation_case(case, AS_OF)


class ManifestTests(unittest.TestCase):
    def test_unretained_buyer_packet_holds_submission_authority(self):
        result = validate_manifest(manifest(), AS_OF)
        self.assertEqual(
            result["source_authority_state"],
            "HOLD_BUYER_PACKET_REQUIRED",
        )
        self.assertEqual(
            result["teaming_build_state"],
            "READY_FOR_PARTNER_REVIEW",
        )
        self.assertEqual(
            result["direct_prime_state"],
            "HOLD_PRIME_CAPABILITY_REQUIRED",
        )
        self.assertEqual(
            result["commercial_offer_state"],
            "PROPOSED_NOT_ACCEPTED",
        )
        self.assertEqual(result["fixed_fee_usd_cents"], 1_800_000)
        self.assertEqual(result["optional_cutover_usd_cents"], 600_000)
        for field in AUTHORITY_FALSE:
            self.assertFalse(result[field])

    def test_buyer_packet_cannot_be_declared_retained_without_digest(self):
        doc = manifest()
        doc["buyer_packet"]["retained"] = True
        doc["buyer_packet"]["authority"] = "BUYER_PACKET"
        with self.assertRaises(ContractError):
            validate_manifest(doc, AS_OF)

    def test_buyer_packet_cannot_self_mint_with_arbitrary_digest(self):
        doc = manifest()
        doc["buyer_packet"]["retained"] = True
        doc["buyer_packet"]["sha256"] = "a" * 64
        doc["buyer_packet"]["authority"] = "BUYER_PACKET"
        with self.assertRaises(ContractError):
            validate_manifest(doc, AS_OF)

    def test_stale_secondary_source_holds_partner_readiness(self):
        doc = manifest()
        doc["source_evidence"]["notice"]["captured_at_utc"] = (
            "2026-09-15T01:40:00Z"
        )
        result = validate_manifest(doc, AS_OF)
        self.assertEqual(
            result["source_authority_state"],
            "HOLD_BUYER_PACKET_REQUIRED",
        )
        self.assertEqual(
            result["teaming_build_state"],
            "HOLD_SOURCE_REFRESH_REQUIRED",
        )

    def test_secondary_source_cannot_be_future_dated(self):
        doc = manifest()
        doc["source_evidence"]["notice"]["captured_at_utc"] = (
            "2026-09-18T01:46:00Z"
        )
        with self.assertRaises(ContractError):
            validate_manifest(doc, AS_OF)

    def test_offer_cannot_self_accept(self):
        doc = manifest()
        doc["commercial_offer"]["state"] = "ACCEPTED"
        with self.assertRaises(ContractError):
            validate_manifest(doc, AS_OF)

    def test_offer_cannot_authorize_send(self):
        doc = manifest()
        doc["commercial_offer"]["external_send_authorized"] = True
        with self.assertRaises(ContractError):
            validate_manifest(doc, AS_OF)

    def test_authority_cannot_promote_submission(self):
        doc = manifest()
        doc["authority"]["submission_authorized"] = True
        with self.assertRaises(ContractError):
            validate_manifest(doc, AS_OF)

    def test_authority_cannot_promote_payment(self):
        doc = manifest()
        doc["authority"]["payment_authorized"] = True
        with self.assertRaises(ContractError):
            validate_manifest(doc, AS_OF)

    def test_requirements_cannot_be_weakened(self):
        doc = manifest()
        doc["requirements"]["reconciliation_reporting"] = False
        with self.assertRaises(ContractError):
            validate_manifest(doc, AS_OF)

    def test_deadline_drift_rejected(self):
        doc = manifest()
        doc["solicitation"]["due_utc"] = "2026-09-26T19:00:00Z"
        with self.assertRaises(ContractError):
            validate_manifest(doc, AS_OF)

    def test_expired_window_holds_teaming(self):
        result = validate_manifest(manifest(), "2026-09-25T19:00:00Z")
        self.assertEqual(
            result["teaming_build_state"],
            "HOLD_RESPONSE_WINDOW",
        )


class PartnerTests(unittest.TestCase):
    def test_fixture_candidates_are_research_only(self):
        bundle = compile_bundle(
            manifest(),
            partners(),
            matrix(),
            AS_OF,
        )
        results = bundle["partners"]["candidates"]
        self.assertEqual(len(results), 4)
        for row in results:
            self.assertIn(
                row["status"],
                {"HOLD_PUBLIC_FIT_GAP", "RESEARCH_ERP_INTEGRATION"},
            )
            self.assertFalse(row["contact_authorized"])
            self.assertFalse(row["selection_authorized"])
            self.assertFalse(row["external_send_authorized"])

    def test_candidate_contact_cannot_self_authorize(self):
        candidate = partners()["candidates"][0]
        candidate["contact_authorized"] = True
        with self.assertRaises(ContractError):
            evaluate_partner(candidate)

    def test_public_fit_without_erp_is_research_not_selected(self):
        candidate = partners()["candidates"][1]
        candidate["public_higher_ed_or_public_sector_fit"] = True
        result = evaluate_partner(candidate)
        self.assertEqual(result["status"], "RESEARCH_ERP_INTEGRATION")
        self.assertFalse(result["selection_authorized"])

    def test_public_fit_with_erp_is_only_human_review(self):
        candidate = partners()["candidates"][1]
        candidate["public_higher_ed_or_public_sector_fit"] = True
        candidate["peoplesoft_or_erp_fit_confirmed"] = True
        result = evaluate_partner(candidate)
        self.assertEqual(
            result["status"],
            "QUALIFIED_FOR_HUMAN_PARTNER_REVIEW",
        )
        self.assertFalse(result["selection_authorized"])
        self.assertFalse(result["external_send_authorized"])


class ReconciliationTests(unittest.TestCase):
    def test_fixture_covers_every_terminal_once(self):
        result = evaluate_matrix(matrix(), AS_OF)
        self.assertEqual(result["case_count"], 10)
        self.assertTrue(
            all(value == 1 for value in result["decision_counts"].values())
        )
        for field in AUTHORITY_FALSE:
            self.assertFalse(result[field])

    def test_exact_match_ready(self):
        result = evaluate_reconciliation_case(base_case(), AS_OF)
        self.assertEqual(result["decision"], "EVIDENCE_READY")
        self.assertEqual(result["variance_cents"], 0)

    def test_one_cent_mismatch_holds(self):
        result = evaluate_reconciliation_case(
            base_case(processor_total_cents=125001),
            AS_OF,
        )
        self.assertEqual(
            result["decision"],
            "HOLD_MERCHANT_TOTAL_MISMATCH",
        )
        self.assertEqual(result["variance_cents"], 1)

    def test_sensitive_data_rejects_before_other_evidence(self):
        result = evaluate_reconciliation_case(
            base_case(
                sensitive_cardholder_data_present=True,
                settlement_file_present=False,
            ),
            AS_OF,
        )
        self.assertEqual(result["decision"], "REJECT_SENSITIVE_DATA")

    def test_stale_evidence_holds(self):
        result = evaluate_reconciliation_case(
            base_case(observed_at_utc="2026-09-10T01:00:00Z"),
            AS_OF,
        )
        self.assertEqual(result["decision"], "HOLD_STALE_EVIDENCE")

    def test_future_evidence_rejected(self):
        with self.assertRaises(ContractError):
            evaluate_reconciliation_case(
                base_case(observed_at_utc="2026-09-18T01:46:00Z"),
                AS_OF,
            )

    def test_chargeback_count_must_be_real_integer(self):
        with self.assertRaises(ContractError):
            evaluate_reconciliation_case(
                base_case(unresolved_chargeback_count=1.0),
                AS_OF,
            )

    def test_duplicate_case_id_rejected(self):
        doc = matrix()
        doc["cases"][1]["case"]["case_id"] = (
            doc["cases"][0]["case"]["case_id"]
        )
        with self.assertRaises(ContractError):
            evaluate_matrix(doc, AS_OF)

    def test_expected_decision_mismatch_rejected(self):
        doc = matrix()
        doc["cases"][0]["expected_decision"] = "HOLD_GL_MAPPING"
        with self.assertRaises(ContractError):
            evaluate_matrix(doc, AS_OF)

    def test_missing_terminal_rejected(self):
        doc = matrix()
        doc["cases"] = [
            row
            for row in doc["cases"]
            if row["expected_decision"] != "HOLD_AUDIT_CHAIN"
        ]
        with self.assertRaises(ContractError):
            evaluate_matrix(doc, AS_OF)


class BundleTests(unittest.TestCase):
    def test_bundle_is_teaming_ready_but_send_and_submission_hold(self):
        bundle = compile_bundle(
            manifest(),
            partners(),
            matrix(),
            AS_OF,
        )
        self.assertEqual(
            bundle["partner_outreach_state"],
            "HOLD_MUSE_ARBITRATION_REQUIRED",
        )
        self.assertEqual(
            bundle["submission_state"],
            "HOLD_BUYER_PACKET_REQUIRED",
        )
        for field in AUTHORITY_FALSE:
            self.assertFalse(bundle[field])
        self.assertTrue(
            verify_bundle(
                bundle,
                manifest(),
                partners(),
                matrix(),
                AS_OF,
            )
        )

    def test_bundle_tamper_detected(self):
        bundle = compile_bundle(
            manifest(),
            partners(),
            matrix(),
            AS_OF,
        )
        forged = copy.deepcopy(bundle)
        forged["submission_state"] = "READY"
        self.assertFalse(
            verify_bundle(
                forged,
                manifest(),
                partners(),
                matrix(),
                AS_OF,
            )
        )

    def test_deterministic_recompile(self):
        one = compile_bundle(
            manifest(),
            partners(),
            matrix(),
            AS_OF,
        )
        two = compile_bundle(
            manifest(),
            partners(),
            matrix(),
            AS_OF,
        )
        self.assertEqual(one, two)


if __name__ == "__main__":
    unittest.main()
