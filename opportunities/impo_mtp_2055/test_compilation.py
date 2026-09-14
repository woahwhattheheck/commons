"""Readiness compilation and rendering tests."""

import copy
import json
import unittest

from .engine import compile_packet
from .test_support import load_owner_fixture, ready_fixture

class CompilationTests(unittest.TestCase):
    def test_owner_fixture_is_source_hold(self) -> None:
        receipt, _ = compile_packet(load_owner_fixture())
        self.assertEqual(receipt["status"], "SOURCE_HOLD")
        self.assertFalse(receipt["submission_ready"])

    def test_ready_evidence_without_authority_is_owner_review_ready(self) -> None:
        receipt, _ = compile_packet(ready_fixture())
        self.assertEqual(receipt["status"], "OWNER_REVIEW_READY")
        self.assertFalse(receipt["submission_ready"])

    def test_explicit_owner_authority_can_make_submission_ready(self) -> None:
        receipt, _ = compile_packet(ready_fixture(authority=True))
        self.assertEqual(receipt["status"], "SUBMISSION_READY")
        self.assertTrue(receipt["submission_ready"])

    def test_missing_qualification_is_qualification_hold(self) -> None:
        value = ready_fixture()
        value["organization"]["sam_uei"] = None
        receipt, _ = compile_packet(value)
        self.assertEqual(receipt["status"], "QUALIFICATION_HOLD")

    def test_missing_commercial_approval_is_commercial_hold(self) -> None:
        value = ready_fixture()
        value["pricing"]["commercial_approval"] = {
            "state": "MISSING",
            "reference": None,
            "note": "Owner has not approved price.",
        }
        receipt, _ = compile_packet(value)
        self.assertEqual(receipt["status"], "COMMERCIAL_HOLD")

    def test_zero_pricing_is_commercial_hold(self) -> None:
        value = ready_fixture()
        for task in value["pricing"]["tasks"]:
            task["rate_minor"] = 0
            task["hours"] = 0
            task["other_cost_minor"] = 0
        value["pricing"]["stated_total_minor"] = 0
        receipt, _ = compile_packet(value)
        self.assertEqual(receipt["status"], "COMMERCIAL_HOLD")

    def test_budget_over_cap_is_commercial_hold(self) -> None:
        value = ready_fixture()
        value["pricing"]["tasks"][0]["other_cost_minor"] += 2_000_000
        value["pricing"]["stated_total_minor"] += 2_000_000
        receipt, _ = compile_packet(value)
        self.assertEqual(receipt["status"], "COMMERCIAL_HOLD")

    def test_stale_source_is_source_hold(self) -> None:
        value = ready_fixture()
        value["source_checks"]["last_checked_at"] = "2026-09-01T00:00:00-04:00"
        receipt, _ = compile_packet(value)
        self.assertEqual(receipt["status"], "SOURCE_HOLD")

    def test_one_day_source_is_at_risk_not_blocked(self) -> None:
        value = ready_fixture()
        value["source_checks"]["last_checked_at"] = "2026-09-12T23:59:59-04:00"
        receipt, _ = compile_packet(value)
        src = next(row for row in receipt["gates"] if row["id"] == "SRC-002")
        self.assertEqual(src["disposition"], "AT_RISK")
        self.assertEqual(receipt["status"], "OWNER_REVIEW_READY")

    def test_unsigned_addendum_blocks(self) -> None:
        value = ready_fixture()
        value["source_checks"]["addenda"] = [
            {
                "id": "ADD-01",
                "sha256": "c" * 64,
                "published_at": "2026-09-13T12:00:00-04:00",
                "signed_acknowledgement": False,
            }
        ]
        receipt, _ = compile_packet(value)
        self.assertEqual(receipt["status"], "SOURCE_HOLD")

    def test_questions_addendum_blocks_after_deadline(self) -> None:
        value = ready_fixture()
        value["as_of"] = "2026-09-17T00:00:00-04:00"
        value["source_checks"]["last_checked_at"] = value["as_of"]
        value["source_checks"]["questions_addendum"] = {
            "state": "MISSING",
            "reference": None,
            "note": None,
        }
        receipt, _ = compile_packet(value)
        self.assertEqual(receipt["status"], "SOURCE_HOLD")

    def test_expired_deadline_blocks(self) -> None:
        value = ready_fixture(authority=True)
        value["as_of"] = "2026-10-06T17:00:00-04:00"
        value["source_checks"]["last_checked_at"] = value["as_of"]
        receipt, _ = compile_packet(value)
        self.assertEqual(receipt["status"], "SOURCE_HOLD")

    def test_impo_project_does_not_count(self) -> None:
        value = ready_fixture()
        value["projects"][0]["is_impo_client"] = True
        receipt, _ = compile_packet(value)
        self.assertEqual(receipt["status"], "QUALIFICATION_HOLD")

    def test_duplicate_reference_routes_block(self) -> None:
        value = ready_fixture()
        value["projects"][1]["reference_email"] = value["projects"][0]["reference_email"]
        receipt, _ = compile_packet(value)
        row = next(item for item in receipt["gates"] if item["id"] == "EXP-002")
        self.assertEqual(row["disposition"], "BLOCKED")

    def test_partner_without_commitment_blocks(self) -> None:
        value = ready_fixture()
        value["team"]["partners"][0]["commitment_evidence"] = {
            "state": "UNKNOWN",
            "reference": None,
            "note": None,
        }
        receipt, _ = compile_packet(value)
        self.assertEqual(receipt["status"], "QUALIFICATION_HOLD")

    def test_missing_insurance_is_deferred_not_submission_block(self) -> None:
        value = ready_fixture()
        value["organization"]["liability_insurance"] = {
            "state": "UNKNOWN",
            "reference": None,
            "note": None,
        }
        receipt, _ = compile_packet(value)
        row = next(item for item in receipt["gates"] if item["id"] == "ORG-004")
        self.assertEqual(row["disposition"], "DEFERRED")
        self.assertEqual(receipt["status"], "OWNER_REVIEW_READY")

    def test_missing_vendor_profile_is_at_risk_not_blocked(self) -> None:
        value = ready_fixture()
        value["organization"]["marion_county_vendor_profile"] = {
            "state": "MISSING",
            "reference": None,
            "note": None,
        }
        value["documents"]["vendor_profile_evidence"] = {
            "state": "MISSING",
            "reference": None,
            "note": None,
        }
        receipt, _ = compile_packet(value)
        self.assertEqual(receipt["status"], "OWNER_REVIEW_READY")
        self.assertGreaterEqual(receipt["counts"]["AT_RISK"], 1)

    def test_not_applicable_mandatory_capability_blocks(self) -> None:
        value = ready_fixture()
        value["capabilities"]["quality_assurance"] = {
            "state": "NOT_APPLICABLE",
            "reference": None,
            "note": "Incorrectly waived.",
        }
        receipt, _ = compile_packet(value)
        self.assertEqual(receipt["status"], "QUALIFICATION_HOLD")

    def test_receipt_is_deterministic(self) -> None:
        value = ready_fixture()
        first = compile_packet(value)
        second = compile_packet(copy.deepcopy(value))
        self.assertEqual(first, second)

    def test_caller_mutation_after_compile_does_not_change_receipt(self) -> None:
        value = ready_fixture()
        receipt, markdown = compile_packet(value)
        value["projects"][0]["client"] = "MUTATED"
        self.assertNotIn("MUTATED", json.dumps(receipt))
        self.assertNotIn("MUTATED", markdown)

    def test_hidden_unicode_controls_are_escaped(self) -> None:
        value = ready_fixture()
        value["owner_notes"].append("safe\u202ehidden\u202c")
        _, markdown = compile_packet(value)
        self.assertNotIn("\u202e", markdown)
        self.assertNotIn("\u202c", markdown)
        self.assertIn("\\\\u202E", markdown)
        self.assertIn("\\\\u202C", markdown)

    def test_html_entity_is_not_reconstructed(self) -> None:
        value = ready_fixture()
        value["owner_notes"].append("entity &rlm; remains visible")
        _, markdown = compile_packet(value)
        self.assertIn("&amp;rlm;", markdown)
        self.assertNotIn("\u200f", markdown)

    def test_receipt_canonical_json_escapes_hidden_controls(self) -> None:
        from .engine import canonical_json_bytes

        value = ready_fixture()
        value["owner_notes"].append("safe\u202ehidden\u202c")
        receipt, _ = compile_packet(value)
        encoded = canonical_json_bytes(receipt)
        self.assertNotIn("\u202e".encode("utf-8"), encoded)
        self.assertNotIn("\u202c".encode("utf-8"), encoded)
        self.assertIn(b"\\u202e", encoded.lower())
        self.assertIn(b"\\u202c", encoded.lower())

    def test_markdown_metacharacters_are_escaped(self) -> None:
        value = ready_fixture()
        value["owner_notes"].append("pipe | and `code`")
        _, markdown = compile_packet(value)
        self.assertIn("\\|", markdown)
        self.assertIn("\\`code\\`", markdown)


