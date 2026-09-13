from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .desk import (
    AUTHORITY_FALSE,
    DeskError,
    append_event,
    build_package,
    canonical_json,
    format_money,
    sha256_json,
    sha256_text,
    strict_json_loads,
    verify_package,
)
from .fixture import (
    DECISION_DIGEST,
    EVALUATION_TIME,
    acceptance_manifest,
    build_fixture,
    make_baseline,
    make_change,
    make_events,
)


class StrictJsonTests(unittest.TestCase):
    def test_duplicate_key_rejected(self) -> None:
        with self.assertRaisesRegex(DeskError, "DUPLICATE_JSON_KEY"):
            strict_json_loads('{"x":1,"x":2}')

    def test_float_and_nonfinite_numbers_rejected(self) -> None:
        for raw in ('{"x":1.5}', '{"x":NaN}', '{"x":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(DeskError):
                strict_json_loads(raw)

    def test_canonical_json_is_stable(self) -> None:
        self.assertEqual(canonical_json({"z": 1, "a": [2, 3]}), '{"a":[2,3],"z":1}')


class PackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = make_baseline()
        self.change = make_change(self.baseline)
        self.events = make_events(self.change)
        self.expected = sha256_json(self.baseline)

    def build(self, *, evaluation: str = EVALUATION_TIME):
        return build_package(
            self.baseline,
            self.change,
            self.events,
            expected_baseline_sha256=self.expected,
            evaluation_time=evaluation,
        )

    def test_ready_package_and_verifier(self) -> None:
        package = self.build()
        self.assertEqual(package["receipt"]["status"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(package["receipt"]["authority"], AUTHORITY_FALSE)
        self.assertIn("USD 760.00", package["markdown"])
        self.assertEqual(verify_package(package)["package_sha256"], package["package_sha256"])

    def test_deterministic_rerun(self) -> None:
        self.assertEqual(canonical_json(self.build()), canonical_json(self.build()))

    def test_baseline_commitment_mismatch_holds(self) -> None:
        package = build_package(
            self.baseline,
            self.change,
            self.events,
            expected_baseline_sha256="0" * 64,
            evaluation_time=EVALUATION_TIME,
        )
        self.assertEqual(package["receipt"]["status"], "HOLD")
        self.assertEqual(package["receipt"]["hold_codes"], ["BASELINE_COMMITMENT_MISMATCH"])
        self.assertTrue(verify_package(package)["verified"])

    def test_invalid_expected_commitment_does_not_echo_secret(self) -> None:
        package = build_package(
            self.baseline,
            self.change,
            self.events,
            expected_baseline_sha256="not-a-digest-super-secret-value",
            evaluation_time=EVALUATION_TIME,
        )
        self.assertIsNone(package["receipt"]["expected_baseline_sha256"])
        self.assertNotIn("super-secret", canonical_json(package))

    def test_expired_change_holds(self) -> None:
        package = self.build(evaluation="2026-09-21T09:00:00Z")
        self.assertEqual(package["receipt"]["hold_codes"], ["CHANGE_EXPIRED"])

    def test_money_mismatch_holds(self) -> None:
        self.change["total_delta_cents"] += 1
        package = self.build()
        self.assertEqual(package["receipt"]["hold_codes"], ["CHANGE_TOTAL_MISMATCH"])

    def test_exact_money_near_safe_integer_limit(self) -> None:
        baseline = make_baseline()
        baseline["line_items"] = [{
            "item_id": "large",
            "description": "Large exact-cent baseline",
            "quantity": 1,
            "unit_price_cents": 9_007_199_254_739_000,
        }]
        baseline["discount_cents"] = 0
        baseline["tax_cents"] = 0
        baseline["subtotal_cents"] = 9_007_199_254_739_000
        baseline["total_cents"] = 9_007_199_254_739_000
        baseline["schedule"]["milestones"] = [{
            "milestone_id": "delivery",
            "due_date": "2026-10-15",
            "amount_cents": 9_007_199_254_739_000,
        }]
        change = make_change(baseline)
        change["line_items"] = [{
            "item_id": "precision",
            "description": "Exact cent precision",
            "quantity": 1,
            "unit_delta_cents": 91,
        }]
        change["subtotal_delta_cents"] = 91
        change["discount_delta_cents"] = 0
        change["tax_delta_cents"] = 0
        change["total_delta_cents"] = 91
        change["milestones"] = [{
            "milestone_id": "delivery",
            "due_date": "2026-10-20",
            "amount_delta_cents": 91,
        }]
        events = make_events(change)
        package = build_package(
            baseline,
            change,
            events,
            expected_baseline_sha256=sha256_json(baseline),
            evaluation_time=EVALUATION_TIME,
        )
        self.assertEqual(package["receipt"]["status"], "READY_FOR_HUMAN_REVIEW")
        self.assertIn("USD 90071992547390.91", package["markdown"])

    def test_schedule_mismatch_holds(self) -> None:
        self.change["updated_end_date"] = "2026-10-19"
        self.assertEqual(self.build()["receipt"]["hold_codes"], ["UPDATED_END_DATE_MISMATCH"])

    def test_negative_updated_milestone_holds(self) -> None:
        self.change["line_items"][0]["unit_delta_cents"] = -200_000
        self.change["subtotal_delta_cents"] = -400_000
        self.change["discount_delta_cents"] = 0
        self.change["tax_delta_cents"] = 0
        self.change["total_delta_cents"] = -400_000
        self.change["milestones"][0]["amount_delta_cents"] = -400_000
        self.assertEqual(self.build()["receipt"]["hold_codes"], ["UPDATED_MILESTONE_AMOUNT_NEGATIVE"])

    def test_missing_baseline_acceptance_evidence_holds(self) -> None:
        self.baseline["evidence_refs"] = [row for row in self.baseline["evidence_refs"] if row["kind"] != "acceptance"]
        self.change = make_change(self.baseline)
        self.events = make_events(self.change)
        self.expected = sha256_json(self.baseline)
        self.assertEqual(self.build()["receipt"]["hold_codes"], ["BASELINE_ACCEPTANCE_EVIDENCE_REQUIRED"])

    def test_missing_change_scope_evidence_holds(self) -> None:
        self.change["evidence_refs"] = [row for row in self.change["evidence_refs"] if row["kind"] != "scope"]
        self.assertEqual(self.build()["receipt"]["hold_codes"], ["SCOPE_EVIDENCE_REQUIRED"])

    def test_supersession_contract(self) -> None:
        self.change["change_version"] = 2
        self.events = []
        self.assertEqual(self.build()["receipt"]["hold_codes"], ["SUPERSESSION_COMMITMENT_REQUIRED"])
        self.change["supersedes_change_sha256"] = sha256_text("change-001-v1")
        package = self.build()
        self.assertEqual(package["receipt"]["status"], "DRAFT")
        self.assertEqual(package["receipt"]["supersedes_change_sha256"], sha256_text("change-001-v1"))

    def test_unexpected_supersession_on_first_version_holds(self) -> None:
        self.change["supersedes_change_sha256"] = sha256_text("unexpected")
        self.assertEqual(self.build()["receipt"]["hold_codes"], ["UNEXPECTED_SUPERSESSION_COMMITMENT"])

    def test_unknown_field_holds(self) -> None:
        self.change["surprise"] = True
        self.assertEqual(self.build()["receipt"]["hold_codes"], ["UNKNOWN_FIELD"])

    def test_sensitive_and_pii_shaped_inputs_hold(self) -> None:
        cases = [
            ("apiSecret", "abcd", "SENSITIVE_FIELD_FORBIDDEN"),
            ("note", "reach me at person@example.com", "PII_SHAPED_VALUE_FORBIDDEN"),
            ("note", "sk-thisisasecretkeyvalue", "SECRET_SHAPED_VALUE_FORBIDDEN"),
        ]
        for key, value, code in cases:
            with self.subTest(key=key):
                baseline = make_baseline()
                change = make_change(baseline)
                change["line_items"][0][key] = value
                package = build_package(
                    baseline,
                    change,
                    make_events(change),
                    expected_baseline_sha256=sha256_json(baseline),
                    evaluation_time=EVALUATION_TIME,
                )
                self.assertEqual(package["receipt"]["hold_codes"], [code])

    def test_float_input_holds(self) -> None:
        self.change["tax_delta_cents"] = 6000.0
        self.assertEqual(self.build()["receipt"]["hold_codes"], ["FLOAT_JSON_NUMBER_FORBIDDEN"])


class EventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.change = make_change(make_baseline())

    def test_append_event_replay_is_idempotent(self) -> None:
        events = make_events(self.change)
        replayed, replay = append_event(
            events,
            change=self.change,
            evaluation_time=EVALUATION_TIME,
            event_id="event-submit-001",
            kind="SUBMIT_FOR_REVIEW",
            occurred_at="2026-09-13T09:05:00Z",
            actor_ref="operator-01",
            expected_state="DRAFT",
            expected_change_version=1,
        )
        self.assertTrue(replay)
        self.assertEqual(events, replayed)

    def test_changed_payload_same_event_id_conflicts(self) -> None:
        events = make_events(self.change)
        with self.assertRaisesRegex(DeskError, "EVENT_ID_CONFLICT"):
            append_event(
                events,
                change=self.change,
                evaluation_time=EVALUATION_TIME,
                event_id="event-submit-001",
                kind="SUBMIT_FOR_REVIEW",
                occurred_at="2026-09-13T09:06:00Z",
                actor_ref="operator-01",
                expected_state="DRAFT",
                expected_change_version=1,
            )

    def test_optimistic_state_fence(self) -> None:
        with self.assertRaisesRegex(DeskError, "EVENT_EXPECTED_STATE_MISMATCH"):
            append_event(
                [],
                change=self.change,
                evaluation_time=EVALUATION_TIME,
                event_id="event-approve-first",
                kind="APPROVE",
                occurred_at="2026-09-13T09:05:00Z",
                actor_ref="operator-01",
                expected_state="READY_FOR_HUMAN_REVIEW",
                expected_change_version=1,
                decision_ref_sha256=DECISION_DIGEST,
            )

    def test_decision_reference_must_be_bound_evidence(self) -> None:
        events = make_events(self.change)
        with self.assertRaisesRegex(DeskError, "DECISION_REFERENCE_NOT_IN_EVIDENCE"):
            append_event(
                events,
                change=self.change,
                evaluation_time=EVALUATION_TIME,
                event_id="event-approve-bad-ref",
                kind="APPROVE",
                occurred_at="2026-09-13T09:10:00Z",
                actor_ref="operator-02",
                expected_state="READY_FOR_HUMAN_REVIEW",
                expected_change_version=1,
                decision_ref_sha256=sha256_text("not-bound"),
            )

    def test_operator_recorded_approval_stays_non_authoritative(self) -> None:
        fixture = build_fixture(approved=True)
        receipt = fixture["package"]["receipt"]
        self.assertEqual(receipt["status"], "APPROVED")
        self.assertEqual(receipt["authority"], AUTHORITY_FALSE)
        self.assertFalse(fixture["verification"]["source_authority_verified"])

    def test_tampered_chain_holds(self) -> None:
        baseline = make_baseline()
        change = make_change(baseline)
        events = make_events(change)
        events[0]["prev_event_digest"] = "0" * 64
        package = build_package(
            baseline,
            change,
            events,
            expected_baseline_sha256=sha256_json(baseline),
            evaluation_time=EVALUATION_TIME,
        )
        self.assertEqual(package["receipt"]["hold_codes"], ["EVENT_PREV_DIGEST_MISMATCH"])

    def test_expired_change_preempts_event_processing(self) -> None:
        baseline = make_baseline()
        change = make_change(baseline)
        change["expires_at"] = "2026-09-13T09:03:00Z"
        events = make_events(make_change(baseline))
        package = build_package(
            baseline,
            change,
            events,
            expected_baseline_sha256=sha256_json(baseline),
            evaluation_time=EVALUATION_TIME,
        )
        self.assertEqual(package["receipt"]["hold_codes"], ["CHANGE_EXPIRED"])

    def test_wrong_change_version_holds(self) -> None:
        baseline = make_baseline()
        change = make_change(baseline)
        events = make_events(change)
        events[0]["expected_change_version"] = 2
        events[0]["event_digest"] = sha256_json({k: v for k, v in events[0].items() if k != "event_digest"})
        package = build_package(
            baseline,
            change,
            events,
            expected_baseline_sha256=sha256_json(baseline),
            evaluation_time=EVALUATION_TIME,
        )
        self.assertEqual(package["receipt"]["hold_codes"], ["EVENT_CHANGE_VERSION_MISMATCH"])


class VerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.package = build_fixture()["package"]

    def test_markdown_tamper_rejected(self) -> None:
        package = copy.deepcopy(self.package)
        package["markdown"] += "tamper"
        with self.assertRaisesRegex(DeskError, "MARKDOWN_MISMATCH"):
            verify_package(package)

    def test_unknown_receipt_field_rejected(self) -> None:
        package = copy.deepcopy(self.package)
        package["receipt"]["unexpected"] = True
        package["receipt"]["receipt_sha256"] = sha256_json({k: v for k, v in package["receipt"].items() if k != "receipt_sha256"})
        package["markdown"] = package["markdown"]
        package["package_sha256"] = sha256_json({k: v for k, v in package.items() if k != "package_sha256"})
        with self.assertRaisesRegex(DeskError, "UNKNOWN_FIELD"):
            verify_package(package)

    def test_authority_escalation_rejected_even_when_resigned(self) -> None:
        package = copy.deepcopy(self.package)
        package["receipt"]["authority"]["payment_authorized"] = True
        package["receipt"]["receipt_sha256"] = sha256_json({k: v for k, v in package["receipt"].items() if k != "receipt_sha256"})
        # The exact renderer would still expose the old digest, but authority must fail first.
        with self.assertRaisesRegex(DeskError, "AUTHORITY_CEILING_VIOLATION"):
            verify_package(package)

    def test_event_history_cannot_be_removed_and_resigned(self) -> None:
        package = copy.deepcopy(self.package)
        package["receipt"]["events"] = []
        package["receipt"]["event_count"] = 0
        package["receipt"]["events_sha256"] = sha256_json([])
        package["receipt"]["event_tip_sha256"] = "GENESIS"
        package["receipt"]["receipt_sha256"] = sha256_json({k: v for k, v in package["receipt"].items() if k != "receipt_sha256"})
        with self.assertRaises(DeskError):
            verify_package(package)

    def test_package_digest_tamper_rejected(self) -> None:
        package = copy.deepcopy(self.package)
        package["package_sha256"] = "0" * 64
        with self.assertRaisesRegex(DeskError, "PACKAGE_DIGEST_MISMATCH"):
            verify_package(package)


class AcceptanceTests(unittest.TestCase):
    def test_manifest_is_deterministic_and_authority_false(self) -> None:
        first = acceptance_manifest()
        second = acceptance_manifest()
        self.assertEqual(first, second)
        self.assertEqual(first["authority"], AUTHORITY_FALSE)
        self.assertEqual([row["status"] for row in first["cases"]], ["READY_FOR_HUMAN_REVIEW", "APPROVED"])

    def test_exact_money_formatter(self) -> None:
        self.assertEqual(format_money(9_007_199_254_740_991, "USD"), "USD 90071992547409.91")
        self.assertEqual(format_money(-1, "USD"), "-USD 0.01")

    def test_cli_fixture_and_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fixture"
            command = [
                sys.executable,
                "-m",
                "revenue.service_change_order_desk.cli",
                "fixture",
                "--output-dir",
                str(out),
            ]
            result = subprocess.run(command, cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            package_path = out / "change-order-package.json"
            self.assertTrue(package_path.is_file())
            verify = subprocess.run(
                [sys.executable, "-m", "revenue.service_change_order_desk.cli", "verify", str(package_path)],
                cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, check=False,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr)
            self.assertTrue(json.loads(verify.stdout)["verified"])


if __name__ == "__main__":
    unittest.main()
