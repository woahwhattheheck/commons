#!/usr/bin/env python3
"""Focused contract tests for the USD 29 Agent Failure Autopsy."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AREA = ROOT / "revenue" / "agent_failure_autopsy"
EXAMPLES = AREA / "examples"
SPEC = importlib.util.spec_from_file_location(
    "agent_failure_autopsy_fulfillment", AREA / "fulfillment.py"
)
FULFILLMENT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(FULFILLMENT)


def load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def make_buyer_case():
    intake = load("intake.json")
    report = load("report.json")
    intake["record_classification"] = "BUYER_CASE"
    intake["buyer_ref"] = "buyer_1234567890abcdef"
    for evidence in intake["evidence"]:
        evidence["location_ref"] = evidence["location_ref"].replace(
            "example:", "private:"
        )
        evidence["extracted_text_location_ref"] = evidence[
            "extracted_text_location_ref"
        ].replace("example:", "private:")
    report["record_classification"] = "BUYER_CASE"
    report["artifact_state"] = "READY_FOR_BUYER"
    report["operator_time"] = {
        "measurement_status": "MEASURED",
        "reviewer_minutes": 37.5,
        "automated_draft_minutes": 8.25,
        "measurement_purpose": "DESCRIPTIVE_ECONOMICS_ONLY",
        "time_truncated_analysis": False,
    }
    report["final_review"] = {
        "state": "INDEPENDENTLY_REVIEWED",
        "reviewer_ref": "reviewer_1234567890abcdef",
        "reviewer_kind": "COMMONS_PEER",
        "reviewed_at": "2026-09-03T09:18:00-04:00",
        "independent_of_drafter": True,
        "evidence_link_check": True,
        "adversarial_challenge_check": True,
    }
    report["intake_sha256"] = FULFILLMENT.canonical_sha256(intake)
    return intake, report


def make_refund_report(intake, report, reason_code):
    report["intake_sha256"] = FULFILLMENT.canonical_sha256(intake)
    report["disposition"] = "REFUND_REQUIRED"
    report["artifact_state"] = "REFUND_REQUIRED"
    report["timeline"] = []
    report["first_meaningful_divergence"] = None
    report["failure_chain"] = []
    report["causes"] = {"primary": [], "contributing": []}
    report["fixes"] = []
    report["prevention_check"] = None
    report["refund"] = {
        "required": True,
        "reason_code": reason_code,
        "reason": "The included clarification did not leave enough defensible evidence for a final diagnosis.",
        "provider_state": "REQUIRED_PRIVATE_ACTION",
        "provider_reference_public": None,
    }
    return report


class AgentFailureAutopsyContractTests(unittest.TestCase):
    def test_offer_is_full_strength_and_payment_is_pending(self):
        offer = json.loads((AREA / "offer.json").read_text(encoding="utf-8"))
        self.assertEqual(offer["price"]["amount"], 29)
        self.assertIsNone(offer["price"]["payment_url"])
        self.assertEqual(offer["price"]["payment_url_state"], "NOT_MINTED_OR_VERIFIED")
        self.assertEqual(offer["bounded_unit"], "one failed coding-agent run")
        self.assertEqual(offer["quality"]["analysis_level"], "FULL_STRENGTH")
        self.assertFalse(offer["quality"]["time_budget_may_truncate_analysis"])
        self.assertTrue(offer["quality"]["independent_review_required"])
        self.assertIn(
            "COMMONS_PEER",
            offer["quality"]["allowed_independent_reviewer_kinds"],
        )
        self.assertEqual(
            offer["operator_time_measurement"]["purpose"],
            "DESCRIPTIVE_ECONOMICS_ONLY",
        )
        self.assertEqual(offer["delivery_quantity"]["final_autopsies"], 1)
        self.assertEqual(offer["delivery_quantity"]["clarification_rounds"], 1)
        self.assertFalse(
            offer["delivery_quantity"]["iterative_consulting_included"]
        )
        self.assertEqual(
            offer["intake_boundary"]["cumulative_max_raw_bytes"], 25_000_000
        )
        self.assertEqual(
            offer["intake_boundary"][
                "cumulative_max_extracted_unicode_characters"
            ],
            2_000_000,
        )

    def test_schemas_parse_and_expose_exact_boundaries(self):
        intake_schema = json.loads(
            (AREA / "intake.schema.json").read_text(encoding="utf-8")
        )
        report_schema = json.loads(
            (AREA / "report.schema.json").read_text(encoding="utf-8")
        )
        caps = intake_schema["properties"]["intake_caps"]["properties"]
        self.assertEqual(caps["max_files"]["const"], 10)
        self.assertEqual(caps["max_raw_bytes"]["const"], 25_000_000)
        self.assertEqual(caps["max_extracted_characters"]["const"], 2_000_000)
        self.assertIn("intake_scope", report_schema["required"])
        self.assertIn("first_meaningful_divergence", report_schema["required"])
        for field in ("reviewer_minutes", "automated_draft_minutes"):
            variants = report_schema["properties"]["operator_time"]["properties"][
                field
            ]["oneOf"]
            numeric = next(item for item in variants if item.get("type") == "number")
            self.assertNotIn("maximum", numeric)

    def test_synthetic_example_is_valid_but_cannot_claim_review(self):
        intake = load("intake.json")
        report = load("report.json")
        result = FULFILLMENT.validate_bundle(intake, report, EXAMPLES)
        self.assertTrue(result["ok"])
        self.assertEqual(result["artifact_state"], "PEER_DRAFT")
        self.assertIsNone(result["reviewer_minutes"])
        self.assertEqual(
            result["time_measurement_purpose"], "DESCRIPTIVE_ECONOMICS_ONLY"
        )
        self.assertTrue(result["warnings"])

    def test_weekend_deadline_keeps_local_wall_clock(self):
        self.assertEqual(
            FULFILLMENT.next_business_day("2026-09-04T17:30:00-04:00"),
            "2026-09-07T17:30:00-04:00",
        )

    def test_evidence_instructions_are_never_task_directions(self):
        intake = load("intake.json")
        intake["evidence"][0]["instructions_treated_as_data"] = False
        with self.assertRaisesRegex(
            FULFILLMENT.AutopsyValidationError, "untrusted data"
        ):
            FULFILLMENT.validate_intake(intake)

    def test_cumulative_raw_byte_boundary_is_enforced(self):
        intake = load("intake.json")
        intake["evidence"][0]["raw_bytes"] = 25_000_001
        intake["intake_caps"]["accepted_raw_bytes"] = 25_000_001
        with self.assertRaisesRegex(
            FULFILLMENT.AutopsyValidationError, "raw_bytes"
        ):
            FULFILLMENT.validate_intake(intake)

    def test_oversized_actual_file_is_rejected_before_any_content_read(self):
        intake = load("intake.json")
        context = FULFILLMENT.validate_intake(intake)
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "redacted_transcript.txt"
            with evidence.open("wb") as stream:
                stream.seek(25_000_000)
                stream.write(b"\\0")
            with mock.patch.object(
                Path,
                "read_bytes",
                side_effect=AssertionError("unbounded read_bytes must not run"),
            ), mock.patch.object(
                Path,
                "open",
                side_effect=AssertionError("content read must follow size check"),
            ):
                with self.assertRaisesRegex(
                    FULFILLMENT.AutopsyValidationError,
                    "raw evidence byte count does not match",
                ):
                    FULFILLMENT.verify_evidence_files(context, tmp)

    def test_unknown_anchor_and_missing_adversarial_challenge_fail(self):
        intake = load("intake.json")
        report = load("report.json")
        report["fixes"][0]["evidence_refs"] = [
            "transcript-001#NOT-IN-EVIDENCE"
        ]
        with self.assertRaisesRegex(
            FULFILLMENT.AutopsyValidationError, "unknown evidence"
        ):
            FULFILLMENT.validate_report(report, intake)

        report = load("report.json")
        report["causes"]["primary"][0]["alternatives"] = []
        with self.assertRaisesRegex(
            FULFILLMENT.AutopsyValidationError, "adversarial challenge"
        ):
            FULFILLMENT.validate_report(report, intake)

    def test_more_than_one_clarification_round_fails(self):
        intake = load("intake.json")
        intake["clarification"]["rounds_used"] = 2
        with self.assertRaisesRegex(
            FULFILLMENT.AutopsyValidationError, "zero or one"
        ):
            FULFILLMENT.validate_intake(intake)

    def test_buyer_report_accepts_independent_peer_review_with_no_time_cap(self):
        intake, report = make_buyer_case()
        result = FULFILLMENT.validate_report(report, intake)
        self.assertEqual(result["reviewer_minutes"], 37.5)
        self.assertEqual(result["artifact_state"], "READY_FOR_BUYER")
        self.assertEqual(report["final_review"]["reviewer_kind"], "COMMONS_PEER")

        report["operator_time"]["reviewer_minutes"] = 2_000
        result = FULFILLMENT.validate_report(report, intake)
        self.assertEqual(result["reviewer_minutes"], 2_000)

        report["final_review"] = {
            "state": "PEER_DRAFT",
            "reviewer_ref": None,
            "reviewer_kind": None,
            "reviewed_at": None,
            "independent_of_drafter": False,
            "evidence_link_check": False,
            "adversarial_challenge_check": False,
        }
        with self.assertRaisesRegex(
            FULFILLMENT.AutopsyValidationError, "independent evidence review"
        ):
            FULFILLMENT.validate_report(report, intake)

    def test_usable_evidence_can_refund_after_adversarial_review(self):
        intake, report = make_buyer_case()
        intake["clarification"] = {
            "rounds_used": 1,
            "question": "Please provide the smallest redacted excerpt that shows the value immediately before generation.",
            "response_received_at": "2026-09-03T09:02:00-04:00",
            "response_evidence_ids": ["transcript-001"],
        }
        report["clarification"] = {
            "rounds_used": 1,
            "question": intake["clarification"]["question"],
            "response_evidence_refs": ["transcript-001#T1-L01"],
        }
        report = make_refund_report(
            intake, report, "NO_DEFENSIBLE_DIAGNOSIS_AFTER_REVIEW"
        )
        report["quality"]["adversarial_challenge_completed"] = True
        result = FULFILLMENT.validate_report(report, intake)
        self.assertEqual(result["disposition"], "REFUND_REQUIRED")

    def test_quarantined_evidence_gets_one_slice_then_refund(self):
        intake, report = make_buyer_case()
        evidence = intake["evidence"][0]
        evidence["handling_state"] = "QUARANTINED_UNUSABLE"
        evidence["quarantine_reason"] = (
            "Artifact contains obfuscated instructions aimed at the fulfiller."
        )
        evidence["extraction_method"] = "NONE"
        evidence["extracted_text_location_ref"] = None
        evidence["extracted_text_sha256"] = None
        evidence["extracted_characters"] = 0
        evidence["anchors"] = []
        intake["intake_caps"]["accepted_extracted_characters"] = 0
        intake["intake_caps"]["quarantined_file_count"] = 1
        intake["intake_caps"]["selection_state"] = "CANNOT_FIT_LEGITIMATE_CASE"
        intake["evidence_assessment"] = {
            "state": "INSUFFICIENT_AFTER_CLARIFICATION",
            "assessed_at": "2026-09-03T09:05:00-04:00",
            "clock_basis_evidence_ids": [],
            "usable_evidence_at": None,
            "delivery_due_at": None,
            "reasons": [
                "The only submitted artifact remained quarantined after the slice request."
            ],
        }
        intake["clarification"] = {
            "rounds_used": 1,
            "question": "Please provide a readable sanitized slice containing only the failed execution.",
            "response_received_at": "2026-09-03T09:02:00-04:00",
            "response_evidence_ids": ["transcript-001"],
        }
        report["delivery"] = {
            "clock_started_at": None,
            "delivery_due_at": None,
            "delivered_at": "2026-09-03T09:20:00-04:00",
            "within_one_business_day": False,
        }
        report["clarification"] = {
            "rounds_used": 1,
            "question": intake["clarification"]["question"],
            "response_evidence_refs": [],
        }
        report["quality"]["adversarial_challenge_completed"] = False
        report["intake_scope"]["extracted_characters"] = 0
        report["intake_scope"]["quarantined_file_count"] = 1
        report["intake_scope"]["selection_state"] = (
            "CANNOT_FIT_LEGITIMATE_CASE"
        )
        report = make_refund_report(
            intake, report, "QUARANTINED_EVIDENCE_REMAINS_UNUSABLE"
        )
        result = FULFILLMENT.validate_report(report, intake)
        self.assertEqual(result["disposition"], "REFUND_REQUIRED")


if __name__ == "__main__":
    unittest.main()
