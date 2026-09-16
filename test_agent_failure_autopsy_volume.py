from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from revenue.agent_failure_autopsy.fulfillment import canonical_bytes, canonical_sha256, load_json
from revenue.agent_failure_autopsy.volume import (
    FACTS_VERSION,
    PAYMENT_VERSION,
    VolumeValidationError,
    compile_volume,
    main as volume_main,
    verify_compiled_volume,
)

ROOT = Path(__file__).resolve().parent
AUTOPSY = ROOT / "revenue" / "agent_failure_autopsy"
PAYMENT_KEY = b"autopsy-volume-test-payment-authority-key"
FACTS_KEY = b"autopsy-volume-test-facts-authority-key!!"


def base_intake(case_id: str = "case-volume-001") -> dict:
    intake = load_json(AUTOPSY / "examples" / "intake.json")
    intake["record_classification"] = "BUYER_CASE"
    intake["case_id"] = case_id
    intake["buyer_ref"] = "buyer_1111111111111111"
    # Canonical fulfillment binds BUYER_CASE evidence to private: locations.
    # The synthetic example uses example:; rewrite so volume tests exercise
    # the live validator instead of a weaker fixture.
    for evidence in intake["evidence"]:
        evidence["location_ref"] = evidence["location_ref"].replace(
            "example:", "private:"
        )
        extracted = evidence.get("extracted_text_location_ref")
        if isinstance(extracted, str):
            evidence["extracted_text_location_ref"] = extracted.replace(
                "example:", "private:"
            )
    return intake


def delivered_report(intake: dict) -> dict:
    report = load_json(AUTOPSY / "examples" / "report.json")
    report["record_classification"] = "BUYER_CASE"
    report["case_id"] = intake["case_id"]
    report["intake_sha256"] = canonical_sha256(intake)
    report["artifact_state"] = "READY_FOR_BUYER"
    report["operator_time"] = {
        "measurement_status": "MEASURED",
        "automated_draft_minutes": 12,
        "measurement_purpose": "DESCRIPTIVE_ECONOMICS_ONLY",
        "time_truncated_analysis": False,
        "reviewer_minutes": 8,
    }
    report["final_review"] = {
        "state": "INDEPENDENTLY_REVIEWED",
        "reviewer_ref": "reviewer_2222222222222222",
        "reviewer_kind": "COMMONS_PEER",
        "reviewed_at": "2026-09-03T09:18:00-04:00",
        "independent_of_drafter": True,
        "evidence_link_check": True,
        "adversarial_challenge_check": True,
    }
    return report


def payment_fields(
    case_id: str = "case-volume-001",
    *,
    payment_ref: str = "pay_aaaaaaaaaaaaaaaa",
    state: str = "PAID_CONFIRMED",
    observed_at: str = "2026-09-03T13:00:00Z",
) -> dict:
    return {
        "schema_version": PAYMENT_VERSION,
        "offer_id": "agent-failure-autopsy-29",
        "case_id": case_id,
        "provider": "STRIPE",
        "provider_payment_ref": payment_ref,
        "payment_state": state,
        "amount_cents": 2900,
        "currency": "USD",
        "observed_at": observed_at,
        "provider_receipt_sha256": "a" * 64,
    }


def _sign(fields: dict, key: bytes) -> dict:
    tag = hmac.new(key, canonical_bytes(fields), hashlib.sha256).hexdigest()
    return {**fields, "authority_tag": tag}


def payment(case_id: str = "case-volume-001", **kwargs) -> dict:
    return _sign(payment_fields(case_id, **kwargs), PAYMENT_KEY)


def facts_fields(
    case_id: str = "case-volume-001",
    *,
    basis: str = "SECOND_FAILED_RUN_OBSERVED",
    count: int = 2,
    observed_at: str = "2026-09-03T13:30:00Z",
) -> dict:
    return {
        "schema_version": FACTS_VERSION,
        "case_id": case_id,
        "basis": basis,
        "observed_at": observed_at,
        "evidence_sha256": "b" * 64,
        "related_failed_run_count": count,
    }


def facts(case_id: str = "case-volume-001", **kwargs) -> dict:
    return _sign(facts_fields(case_id, **kwargs), FACTS_KEY)


def case_record(
    case_id: str = "case-volume-001",
    *,
    payment_receipt: dict | None = None,
    intake: dict | None = None,
    report: dict | None = None,
    next_offer_facts: dict | None = None,
    coordinator: str = "peer_coordinator_alpha",
    backup: str = "peer_backup_beta",
) -> dict:
    return {
        "case_id": case_id,
        "payment_receipt": payment_receipt or payment(case_id),
        "intake": intake,
        "report": report,
        "coordinator_ref": coordinator,
        "backup_ref": backup,
        "next_offer_facts": next_offer_facts,
    }


def compile_cases(records, *, as_of="2026-09-03T14:00:00Z", max_active=4):
    now = datetime.strptime(as_of, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    with patch("revenue.agent_failure_autopsy.volume._trusted_now", return_value=now):
        return compile_volume(
            records,
            payment_authority_key=PAYMENT_KEY,
            facts_authority_key=FACTS_KEY,
            max_active_cases=max_active,
        )


class AutopsyVolumeEngineTests(unittest.TestCase):
    def test_paid_case_without_intake_waits_and_never_schedules_analysis_from_intent(self):
        result = compile_cases([case_record()])
        row = result["private"]["queue"][0]
        self.assertEqual(row["work_state"], "WAITING_FOR_SANITIZED_INTAKE")
        self.assertEqual(row["sla_state"], "CLOCK_NOT_STARTED")
        self.assertEqual(row["next_offer"], "NONE")
        self.assertFalse(row["external_action_authorized"])

    def test_structural_paid_claim_with_wrong_auth_key_is_rejected(self):
        forged = _sign(
            payment_fields(),
            b"other-payment-authority-key-32bytes",
        )
        with self.assertRaisesRegex(VolumeValidationError, "authentication failed"):
            compile_cases([case_record(payment_receipt=forged)])

    def test_post_signature_payment_tamper_is_rejected(self):
        receipt = payment()
        receipt["amount_cents"] = 2901
        with self.assertRaises(VolumeValidationError):
            compile_cases([case_record(payment_receipt=receipt)])

    def test_noncanonical_amount_currency_provider_and_intent_state_rejected(self):
        variants = [
            {"amount_cents": 3000},
            {"currency": "EUR"},
            {"provider": "OTHER"},
            {"payment_state": "PURCHASE_INTENT"},
        ]
        for change in variants:
            raw = payment_fields()
            raw.update(change)
            signed = _sign(raw, PAYMENT_KEY)
            with self.subTest(change=change), self.assertRaises(VolumeValidationError):
                compile_cases([case_record(payment_receipt=signed)])

    def test_future_payment_receipt_rejected(self):
        with self.assertRaisesRegex(VolumeValidationError, "future"):
            compile_cases([
                case_record(payment_receipt=payment(observed_at="2099-01-01T00:00:00Z"))
            ])

    def test_duplicate_case_rejected(self):
        row = case_record()
        with self.assertRaisesRegex(VolumeValidationError, "duplicate case_id"):
            compile_cases([row, deepcopy(row)])

    def test_payment_ref_reuse_across_cases_rejected(self):
        first = case_record("case-volume-001")
        second = case_record(
            "case-volume-002",
            payment_receipt=payment(
                "case-volume-002",
                payment_ref="pay_aaaaaaaaaaaaaaaa",
            ),
        )
        with self.assertRaisesRegex(VolumeValidationError, "payment ref reused"):
            compile_cases([first, second])

    def test_cross_case_authenticated_payment_rejected(self):
        with self.assertRaisesRegex(VolumeValidationError, "does not match"):
            compile_cases([
                case_record("case-volume-001", payment_receipt=payment("case-volume-002"))
            ])

    def test_coordinator_and_backup_must_be_distinct(self):
        with self.assertRaisesRegex(VolumeValidationError, "distinct"):
            compile_cases([
                case_record(coordinator="peer_same_operator", backup="peer_same_operator")
            ])

    def test_buyer_case_example_location_is_rejected_by_canonical_intake(self):
        intake = load_json(AUTOPSY / "examples" / "intake.json")
        intake["record_classification"] = "BUYER_CASE"
        intake["case_id"] = "case-volume-001"
        intake["buyer_ref"] = "buyer_1111111111111111"
        with self.assertRaisesRegex(
            VolumeValidationError, "canonical intake validation failed"
        ):
            compile_cases([case_record(intake=intake)])

    def test_usable_intake_before_deadline_is_analysis_due(self):
        intake = base_intake()
        result = compile_cases([case_record(intake=intake)])
        row = result["private"]["queue"][0]
        self.assertEqual(row["work_state"], "ANALYSIS_DUE")
        self.assertEqual(row["sla_state"], "ON_CLOCK")
        self.assertEqual(row["due_at"], "2026-09-04T13:02:00Z")
        self.assertEqual(result["private"]["capacity"]["analysis_due_cases"], 1)

    def test_due_soon_is_derived_from_clock(self):
        intake = base_intake()
        result = compile_cases(
            [case_record(intake=intake)],
            as_of="2026-09-04T10:00:00Z",
        )
        self.assertEqual(result["private"]["queue"][0]["sla_state"], "DUE_SOON")

    def test_missing_report_after_deadline_becomes_refund_due(self):
        intake = base_intake()
        result = compile_cases(
            [case_record(intake=intake)],
            as_of="2026-09-04T13:02:01Z",
        )
        row = result["private"]["queue"][0]
        self.assertEqual(row["work_state"], "REFUND_DUE")
        self.assertEqual(row["next_offer"], "NONE")
        self.assertFalse(row["automatic_charge_or_refund_authorized"])

    def test_provider_confirmed_refund_is_terminal_and_excluded_from_analysis(self):
        intake = base_intake()
        receipt = payment(state="REFUNDED_CONFIRMED")
        result = compile_cases([case_record(payment_receipt=receipt, intake=intake)])
        row = result["private"]["queue"][0]
        self.assertEqual(row["work_state"], "REFUNDED_CLOSED")
        self.assertEqual(result["private"]["capacity"]["analysis_due_cases"], 0)
        self.assertEqual(row["next_offer"], "NONE")

    def test_report_without_intake_rejected(self):
        intake = base_intake()
        with self.assertRaisesRegex(VolumeValidationError, "report cannot exist"):
            compile_cases([case_record(report=delivered_report(intake))])

    def test_canonical_delivered_report_closes_case(self):
        intake = base_intake()
        report = delivered_report(intake)
        result = compile_cases([case_record(intake=intake, report=report)])
        row = result["private"]["queue"][0]
        self.assertEqual(row["work_state"], "DELIVERED")
        self.assertEqual(row["sla_state"], "CLOSED_DELIVERED")
        self.assertRegex(row["fulfillment_receipt_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(row["next_offer"], "OWNER_REVIEW")

    def test_canonical_report_drift_is_rejected_not_counted_delivered(self):
        intake = base_intake()
        report = delivered_report(intake)
        report["failure_sentence"] = "This is deliberately inconsistent with intake."
        with self.assertRaisesRegex(VolumeValidationError, "canonical report validation failed"):
            compile_cases([case_record(intake=intake, report=report)])

    def test_second_run_fact_can_mark_199_eligibility_only_after_delivery(self):
        intake = base_intake()
        report = delivered_report(intake)
        result = compile_cases([
            case_record(
                intake=intake,
                report=report,
                next_offer_facts=facts(basis="SECOND_FAILED_RUN_OBSERVED", count=2),
            )
        ])
        self.assertEqual(result["private"]["queue"][0]["next_offer"], "$199_DIAGNOSTIC")

    def test_implementation_request_never_invents_unverified_high_ticket_offer(self):
        intake = base_intake()
        report = delivered_report(intake)
        result = compile_cases([
            case_record(
                intake=intake,
                report=report,
                next_offer_facts=facts(
                    basis="IMPLEMENTATION_REQUEST_OBSERVED",
                    count=1,
                ),
            )
        ])
        self.assertEqual(result["private"]["queue"][0]["next_offer"], "OWNER_REVIEW")
        self.assertNotIn("$2500_SURVIVAL", result["private"]["next_offer_eligibility_counts"])

    def test_same_follow_on_fact_on_open_case_does_not_trigger_offer(self):
        intake = base_intake()
        result = compile_cases([
            case_record(
                intake=intake,
                next_offer_facts=facts(
                    basis="IMPLEMENTATION_REQUEST_OBSERVED",
                    count=1,
                ),
            )
        ])
        self.assertEqual(result["private"]["queue"][0]["next_offer"], "NONE")

    def test_forged_next_offer_fact_rejected(self):
        forged = _sign(
            facts_fields(),
            b"other-facts-authority-key-32bytes!!",
        )
        intake = base_intake()
        report = delivered_report(intake)
        with self.assertRaisesRegex(VolumeValidationError, "authentication failed"):
            compile_cases([
                case_record(
                    intake=intake,
                    report=report,
                    next_offer_facts=forged,
                )
            ])

    def test_future_next_offer_fact_rejected(self):
        intake = base_intake()
        report = delivered_report(intake)
        with self.assertRaisesRegex(VolumeValidationError, "future"):
            compile_cases([
                case_record(
                    intake=intake,
                    report=report,
                    next_offer_facts=facts(observed_at="2099-01-01T00:00:00Z"),
                )
            ])

    def test_second_run_basis_requires_two_runs(self):
        intake = base_intake()
        report = delivered_report(intake)
        weak = _sign(
            facts_fields(basis="SECOND_FAILED_RUN_OBSERVED", count=1),
            FACTS_KEY,
        )
        with self.assertRaisesRegex(VolumeValidationError, "at least two"):
            compile_cases([
                case_record(
                    intake=intake,
                    report=report,
                    next_offer_facts=weak,
                )
            ])

    def test_capacity_and_backlog_are_truthful(self):
        first = base_intake("case-volume-001")
        second = base_intake("case-volume-002")
        result = compile_cases(
            [
                case_record("case-volume-001", intake=first),
                case_record(
                    "case-volume-002",
                    intake=second,
                    payment_receipt=payment(
                        "case-volume-002",
                        payment_ref="pay_bbbbbbbbbbbbbbbb",
                    ),
                    coordinator="peer_coordinator_beta",
                    backup="peer_backup_gamma",
                ),
            ],
            max_active=1,
        )
        capacity = result["private"]["capacity"]
        self.assertTrue(capacity["over_capacity"])
        self.assertEqual(capacity["backlog_cases"], 1)
        self.assertEqual(capacity["analysis_slots_available"], 0)

    def test_public_summary_redacts_case_payment_coordinator_and_amount_details(self):
        intake = base_intake()
        result = compile_cases([case_record(intake=intake)])
        rendered = json.dumps(result["public"], sort_keys=True)
        for forbidden in (
            "case-volume-001",
            "pay_aaaaaaaaaaaaaaaa",
            "peer_coordinator_alpha",
            "2900",
            "provider_receipt_sha256",
        ):
            self.assertNotIn(forbidden, rendered)
        self.assertFalse(result["public"]["buyer_identifiers_included"])
        self.assertFalse(result["public"]["provider_payment_refs_included"])
        self.assertFalse(result["public"]["payment_amount_totals_included"])
        self.assertFalse(result["public"]["cash_or_revenue_recognized"])

    def test_outputs_never_authorize_outreach_charge_refund_or_revenue_recognition(self):
        result = compile_cases([case_record()])
        for surface in (result["private"], result["public"]):
            self.assertFalse(surface["automatic_outreach_authorized"])
            self.assertFalse(surface["automatic_charge_or_refund_authorized"])
            self.assertFalse(surface["cash_or_revenue_recognized"])

    def test_queue_orders_refund_before_analysis_before_waiting_intake(self):
        active_intake = base_intake("case-active-001")
        active_intake["submitted_at"] = "2026-09-04T09:00:00-04:00"
        active_intake["evidence"][0]["received_at"] = "2026-09-04T09:02:00-04:00"
        active_intake["evidence_assessment"]["assessed_at"] = "2026-09-04T09:05:00-04:00"
        active_intake["evidence_assessment"]["usable_evidence_at"] = "2026-09-04T09:02:00-04:00"
        active_intake["evidence_assessment"]["delivery_due_at"] = "2026-09-07T09:02:00-04:00"
        overdue_intake = base_intake("case-overdue-001")
        wait = case_record(
            "case-wait-001",
            payment_receipt=payment(
                "case-wait-001", payment_ref="pay_cccccccccccccccc"
            ),
        )
        active = case_record(
            "case-active-001",
            payment_receipt=payment(
                "case-active-001", payment_ref="pay_dddddddddddddddd"
            ),
            intake=active_intake,
            coordinator="peer_active_coord",
            backup="peer_active_backup",
        )
        overdue = case_record(
            "case-overdue-001",
            payment_receipt=payment(
                "case-overdue-001", payment_ref="pay_eeeeeeeeeeeeeeee"
            ),
            intake=overdue_intake,
            coordinator="peer_overdue_coord",
            backup="peer_overdue_backup",
        )
        result = compile_cases(
            [wait, active, overdue],
            as_of="2026-09-04T13:02:01Z",
        )
        states = [row["work_state"] for row in result["private"]["queue"]]
        self.assertEqual(
            states,
            ["REFUND_DUE", "ANALYSIS_DUE", "WAITING_FOR_SANITIZED_INTAKE"],
        )

    def test_compiled_receipts_verify_and_detect_tamper(self):
        result = compile_cases([case_record()])
        self.assertTrue(verify_compiled_volume(result))
        tampered = deepcopy(result)
        tampered["public"]["case_count"] = 99
        with self.assertRaisesRegex(VolumeValidationError, "receipt mismatch"):
            verify_compiled_volume(tampered)

    def test_measured_fulfillment_economics_are_private_and_never_quality_caps(self):
        intake = base_intake()
        report = delivered_report(intake)
        result = compile_cases([case_record(intake=intake, report=report)])
        economics = result["private"]["fulfillment_economics"]
        self.assertEqual(economics["measured_case_count"], 1)
        self.assertEqual(economics["automated_draft_minutes"], 12)
        self.assertEqual(economics["reviewer_minutes"], 8)
        self.assertFalse(economics["quality_truncation_authorized"])
        self.assertNotIn("fulfillment_economics", result["public"])

    def test_operational_clock_cannot_be_supplied_by_caller(self):
        with self.assertRaises(TypeError):
            compile_volume(
                [case_record()],
                as_of="2000-01-01T00:00:00Z",
                payment_authority_key=PAYMENT_KEY,
                facts_authority_key=FACTS_KEY,
                max_active_cases=4,
            )

    def test_bool_capacity_is_rejected(self):
        with self.assertRaises(VolumeValidationError):
            compile_volume(
                [case_record()],
                payment_authority_key=PAYMENT_KEY,
                facts_authority_key=FACTS_KEY,
                max_active_cases=True,
            )

    def test_cli_uses_env_keys_and_create_exclusive_outputs(self):
        records = [case_record()]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cases = root / "cases.json"
            private = root / "private.json"
            public = root / "public.json"
            cases.write_text(json.dumps(records), encoding="utf-8")
            env = {
                "AUTOPSY_PAYMENT_AUTH_KEY_HEX": PAYMENT_KEY.hex(),
                "AUTOPSY_FACTS_AUTH_KEY_HEX": FACTS_KEY.hex(),
            }
            with patch.dict(os.environ, env, clear=False):
                self.assertEqual(
                    volume_main(
                        [
                            str(cases),
                            "--max-active-cases",
                            "4",
                            "--private-output",
                            str(private),
                            "--public-output",
                            str(public),
                        ]
                    ),
                    0,
                )
                private_before = private.read_bytes()
                public_before = public.read_bytes()
                self.assertEqual(
                    volume_main(
                        [
                            str(cases),
                            "--max-active-cases",
                            "4",
                            "--private-output",
                            str(private),
                            "--public-output",
                            str(public),
                        ]
                    ),
                    2,
                )
                self.assertEqual(private.read_bytes(), private_before)
                self.assertEqual(public.read_bytes(), public_before)


if __name__ == "__main__":
    unittest.main()
