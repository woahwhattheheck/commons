from __future__ import annotations

import copy
import hashlib
import json
import unittest

from revenue.streaming_rendition_qa_pilot.demo import build_demo_intake
from revenue.streaming_rendition_qa_pilot.pilot import (
    DIAGNOSTIC,
    INTEGRATION,
    IntakeError,
    SCHEMA,
    canonical_report_bytes,
    compile_pilot,
    compile_receipt,
    validate_intake,
)
from revenue.streaming_rendition_release_gate.fixture import build_fixture


class StreamingRenditionQaPilotTest(unittest.TestCase):
    def test_demo_has_one_hold_per_required_fault_class(self) -> None:
        report = compile_pilot(build_demo_intake())
        self.assertEqual(report["summary"], {"total": 12, "release_ready": 5, "hold": 7})
        self.assertEqual(report["decision"], "REMEDIATE_METADATA")
        self.assertEqual(report["commercial"]["fixed_price_usd"], 2500)
        self.assertEqual(report["reason_counts"]["NONE"], 5)
        holds = {reason: count for reason, count in report["reason_counts"].items() if reason != "NONE"}
        self.assertEqual(len(holds), 7)
        self.assertEqual(set(holds.values()), {1})

    def test_clean_packets_pass_to_media_ops_without_claiming_publish_authority(self) -> None:
        packets, _ = build_fixture()
        intake = build_demo_intake()
        intake["packets"] = packets[:9]
        report = compile_pilot(intake)
        self.assertEqual(report["decision"], "PASS_TO_MEDIA_OPS")
        self.assertEqual(report["summary"], {"total": 9, "release_ready": 9, "hold": 0})
        self.assertIn("retain", report["authority"])
        self.assertIn("publishing authority", report["authority"])

    def test_integration_tier_is_7500(self) -> None:
        intake = build_demo_intake()
        intake["tier"] = INTEGRATION
        report = compile_pilot(intake)
        self.assertEqual(report["commercial"]["fixed_price_usd"], 7500)
        self.assertIn("integration", report["commercial"]["scope"])

    def test_receipt_is_byte_deterministic(self) -> None:
        intake = build_demo_intake()
        first = compile_receipt(copy.deepcopy(intake))
        second = compile_receipt(copy.deepcopy(intake))
        self.assertEqual(first["report_bytes"], second["report_bytes"])
        self.assertEqual(first["report_sha256"], second["report_sha256"])
        self.assertEqual(first["report_sha256"], hashlib.sha256(first["report_bytes"]).hexdigest())
        self.assertTrue(first["report_bytes"].endswith(b"\n"))

    def test_canonical_report_round_trip(self) -> None:
        report = compile_pilot(build_demo_intake())
        parsed = json.loads(canonical_report_bytes(report))
        self.assertEqual(parsed, report)

    def test_unknown_intake_key_fails_closed(self) -> None:
        intake = build_demo_intake()
        intake["publish_now"] = True
        with self.assertRaises(IntakeError):
            validate_intake(intake)

    def test_empty_packets_fail_closed(self) -> None:
        intake = build_demo_intake()
        intake["packets"] = []
        with self.assertRaises(IntakeError):
            compile_pilot(intake)

    def test_invalid_refs_fail_closed(self) -> None:
        intake = build_demo_intake()
        intake["customer_ref"] = "has spaces"
        with self.assertRaises(IntakeError):
            compile_pilot(intake)

    def test_unknown_string_tier_fails_closed(self) -> None:
        intake = build_demo_intake()
        intake["tier"] = "FREE"
        with self.assertRaises(IntakeError):
            compile_pilot(intake)

    def test_unhashable_tier_fails_closed(self) -> None:
        intake = build_demo_intake()
        intake["tier"] = {"name": "DIAGNOSTIC"}
        with self.assertRaises(IntakeError):
            compile_pilot(intake)

    def test_gate_schema_failure_becomes_hold_not_exception(self) -> None:
        packets, _ = build_fixture()
        broken = copy.deepcopy(packets[0])
        broken["extra"] = "not-allowed"
        intake = {
            "schema": SCHEMA,
            "pilot_id": "hostile-001",
            "customer_ref": "synthetic-buyer",
            "tier": DIAGNOSTIC,
            "packets": [broken],
        }
        report = compile_pilot(intake)
        self.assertEqual(report["summary"], {"total": 1, "release_ready": 0, "hold": 1})
        self.assertEqual(report["reason_counts"], {"INVALID_SCHEMA": 1})

    def test_payment_expectation_is_explicit_but_route_is_not_invented(self) -> None:
        report = compile_pilot(build_demo_intake())
        expectation = report["commercial"]["payment_expectation"]
        self.assertIn("paid kickoff", expectation)
        self.assertIn("seller-approved", expectation)
        self.assertNotIn("http", expectation)


if __name__ == "__main__":
    unittest.main()
