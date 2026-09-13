from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from revenue.stl_print_mail_api_acceptance.validator import (
    FixtureError,
    evaluate_fixture,
    verify_receipt_integrity,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "revenue" / "stl_print_mail_api_acceptance" / "example_fixture.json"


def fixture():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


class PrintMailAcceptanceTests(unittest.TestCase):
    def test_clean_controls_hold_for_missing_packet(self):
        receipt = evaluate_fixture(fixture())
        self.assertEqual("PASS", receipt["technical_status"])
        self.assertEqual("PACKET_REQUIRED", receipt["procurement_status"])
        self.assertEqual("HOLD_PACKET_REQUIRED", receipt["overall_status"])
        self.assertTrue(verify_receipt_integrity(receipt))

    def test_packet_bound_never_auto_submits(self):
        data = fixture()
        data["contract"]["product_spec_bound"] = True
        data["contract"]["product_spec_sha256"] = "e" * 64
        receipt = evaluate_fixture(data)
        self.assertEqual("PACKET_BOUND_OWNER_REVIEW", receipt["procurement_status"])
        self.assertEqual("OWNER_REVIEW", receipt["overall_status"])
        self.assertFalse(receipt["authority"]["bid_submission"])
        self.assertFalse(receipt["authority"]["compliance_claim"])

    def test_packet_flag_must_match_hash(self):
        data = fixture()
        data["contract"]["product_spec_bound"] = True
        with self.assertRaises(FixtureError):
            evaluate_fixture(data)

    def test_wrong_bid_id_rejected(self):
        data = fixture()
        data["contract"]["bid_id"] = "OTHER"
        with self.assertRaises(FixtureError):
            evaluate_fixture(data)

    def test_non_city_source_rejected(self):
        data = fixture()
        data["contract"]["source_url"] = "https://example.com/procurement?id=1"
        with self.assertRaises(FixtureError):
            evaluate_fixture(data)

    def test_duplicate_job_id_holds(self):
        data = fixture()
        clone = copy.deepcopy(data["mail_jobs"][0])
        clone["submission"]["idempotency_key"] = "other"
        data["mail_jobs"].append(clone)
        receipt = evaluate_fixture(data)
        self.assertEqual("HOLD_CONTROL_FAILURE", receipt["overall_status"])
        self.assertIn("test-proof-001: duplicate job id", receipt["errors"])

    def test_duplicate_idempotency_key_holds(self):
        data = fixture()
        data["mail_jobs"][1]["submission"]["idempotency_key"] = "idem-test-001"
        receipt = evaluate_fixture(data)
        self.assertTrue(any("duplicate idempotency key" in e for e in receipt["errors"]))

    def test_test_physical_effect_holds(self):
        data = fixture()
        data["mail_jobs"][0]["submission"]["physical_effect"] = True
        receipt = evaluate_fixture(data)
        self.assertTrue(any("TEST environment" in e for e in receipt["errors"]))

    def test_live_without_approval_holds(self):
        data = fixture()
        data["mail_jobs"][1]["authorization"]["approved"] = False
        receipt = evaluate_fixture(data)
        self.assertTrue(any("lacks affirmative authorization" in e for e in receipt["errors"]))

    def test_unlisted_live_authorizer_holds(self):
        data = fixture()
        data["mail_jobs"][1]["authorization"]["authorizer_id"] = "intruder"
        receipt = evaluate_fixture(data)
        self.assertTrue(any("not permitted" in e for e in receipt["errors"]))

    def test_proof_artifact_mismatch_holds(self):
        data = fixture()
        data["mail_jobs"][1]["proof"]["artifact_sha256"] = "f" * 64
        receipt = evaluate_fixture(data)
        self.assertTrue(any("proof artifact" in e for e in receipt["errors"]))

    def test_authorization_render_mismatch_holds(self):
        data = fixture()
        data["mail_jobs"][1]["authorization"]["render_sha256"] = "f" * 64
        receipt = evaluate_fixture(data)
        self.assertTrue(any("authorization is not bound" in e for e in receipt["errors"]))

    def test_authorization_before_proof_holds(self):
        data = fixture()
        data["mail_jobs"][1]["authorization"]["authorized_at"] = "2026-09-13T13:59:59Z"
        receipt = evaluate_fixture(data)
        self.assertTrue(any("authorization predates proof" in e for e in receipt["errors"]))

    def test_submission_before_authorization_holds(self):
        data = fixture()
        data["mail_jobs"][1]["submission"]["submitted_at"] = "2026-09-13T14:01:00Z"
        receipt = evaluate_fixture(data)
        self.assertTrue(any("submission predates authorization" in e for e in receipt["errors"]))

    def test_unknown_effect_holds(self):
        data = fixture()
        data["mail_jobs"][1]["submission"]["effect_state"] = "UNKNOWN_EFFECT"
        receipt = evaluate_fixture(data)
        self.assertTrue(any("effect is unknown" in e for e in receipt["errors"]))

    def test_live_submitted_requires_physical_effect_flag(self):
        data = fixture()
        data["mail_jobs"][1]["submission"]["physical_effect"] = False
        receipt = evaluate_fixture(data)
        self.assertTrue(any("must explicitly record intended physical effect" in e for e in receipt["errors"]))

    def test_budget_overrun_holds(self):
        data = fixture()
        data["departments"]["SYNTH-ITSA"]["budget_cents"] = 100
        receipt = evaluate_fixture(data)
        self.assertTrue(any("exceeds budget" in e for e in receipt["errors"]))

    def test_bool_is_not_accepted_as_money(self):
        data = fixture()
        data["mail_jobs"][1]["expected_cost_cents"] = True
        with self.assertRaises(FixtureError):
            evaluate_fixture(data)

    def test_provider_event_must_match_request(self):
        data = fixture()
        data["mail_jobs"][1]["provider_events"][0]["provider_request_id"] = "other"
        receipt = evaluate_fixture(data)
        self.assertTrue(any("not bound to the submission request" in e for e in receipt["errors"]))

    def test_provider_event_before_submission_holds(self):
        data = fixture()
        data["mail_jobs"][1]["provider_events"][0]["observed_at"] = "2026-09-13T14:02:30Z"
        receipt = evaluate_fixture(data)
        self.assertTrue(any("provider event predates submission" in e for e in receipt["errors"]))

    def test_duplicate_provider_event_holds(self):
        data = fixture()
        data["mail_jobs"][1]["provider_events"].append(copy.deepcopy(data["mail_jobs"][1]["provider_events"][0]))
        receipt = evaluate_fixture(data)
        self.assertTrue(any("duplicate provider event id" in e for e in receipt["errors"]))

    def test_event_after_terminal_holds(self):
        data = fixture()
        events = data["mail_jobs"][1]["provider_events"]
        events[0]["type"] = "DELIVERED"
        later = copy.deepcopy(events[0])
        later["event_id"] = "later"
        later["type"] = "IN_TRANSIT"
        later["observed_at"] = "2026-09-13T14:05:00Z"
        events.append(later)
        receipt = evaluate_fixture(data)
        self.assertTrue(any("after terminal provider state" in e for e in receipt["errors"]))

    def test_provider_events_without_submission_hold(self):
        data = fixture()
        job = data["mail_jobs"][0]
        job["provider_events"] = [{
            "event_id": "orphan",
            "type": "ACCEPTED",
            "provider_request_id": "orphan-request",
            "observed_at": "2026-09-13T14:05:00Z"
        }]
        receipt = evaluate_fixture(data)
        self.assertTrue(any("without a submission" in e for e in receipt["errors"]))

    def test_invalid_hash_rejected(self):
        data = fixture()
        data["mail_jobs"][0]["artifact_sha256"] = "xyz"
        with self.assertRaises(FixtureError):
            evaluate_fixture(data)

    def test_unknown_keys_rejected(self):
        data = fixture()
        data["mail_jobs"][0]["surprise"] = 1
        with self.assertRaises(FixtureError):
            evaluate_fixture(data)

    def test_input_not_mutated(self):
        data = fixture()
        before = copy.deepcopy(data)
        evaluate_fixture(data)
        self.assertEqual(before, data)

    def test_receipt_is_deterministic(self):
        self.assertEqual(evaluate_fixture(fixture()), evaluate_fixture(fixture()))

    def test_receipt_tamper_detected(self):
        receipt = evaluate_fixture(fixture())
        receipt["overall_status"] = "OWNER_REVIEW"
        self.assertFalse(verify_receipt_integrity(receipt))

    def test_no_authority_can_be_minted_by_clean_fixture(self):
        receipt = evaluate_fixture(fixture())
        self.assertTrue(receipt["authority"])
        self.assertTrue(all(value is False for value in receipt["authority"].values()))


if __name__ == "__main__":
    unittest.main()
