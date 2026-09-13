from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from revenue.ohsu_oracle_ebs_ap_acceptance.cli import main
from revenue.ohsu_oracle_ebs_ap_acceptance.io import load_json_object
from revenue.ohsu_oracle_ebs_ap_acceptance.model import AcceptanceInputError
from revenue.ohsu_oracle_ebs_ap_acceptance.validate import evaluate_matrix


def receipt(source: str, kind: str) -> dict[str, str]:
    return {
        "source_id": source,
        "sha256": hashlib.sha256(source.encode()).hexdigest(),
        "captured_at": "2026-09-13T09:30:00Z",
        "kind": kind,
    }


def attempt(aid: str, intent: str, outcome: str, txn: str | None = None) -> dict:
    return {
        "attempt_id": aid,
        "posting_intent_id": intent,
        "outcome": outcome,
        "oracle_txn_id": txn,
    }


def case(
    cid: str,
    scenario: str,
    invoice_key: str,
    terminal: str,
    trace: list[str],
    attempts: list[dict],
    kind: str,
) -> dict:
    return {
        "case_id": cid,
        "scenario": scenario,
        "invoice_key": invoice_key,
        "expected_terminal": terminal,
        "state_trace": trace,
        "attempts": attempts,
        "evidence": receipt(cid + "-evidence", kind),
    }


def ready_matrix() -> dict:
    return {
        "opportunity_id": "OHSU-RFI-2027-0824",
        "oracle_target": "EBS_R12",
        "evaluated_at": "2026-09-13T09:30:00Z",
        "cases": [
            case(
                "C01", "po_2way_match", "INV-PO2", "POSTED",
                ["RECEIVED", "VALIDATED", "MATCHED", "APPROVED", "POST_INTENT", "POSTED"],
                [attempt("A01", "PI-PO2", "posted", "TX-PO2")],
                "oracle_posting_receipt",
            ),
            case(
                "C02", "po_3way_match", "INV-PO3", "POSTED",
                ["RECEIVED", "VALIDATED", "MATCHED", "APPROVED", "POST_INTENT", "POSTED"],
                [attempt("A02", "PI-PO3", "posted", "TX-PO3")],
                "oracle_posting_receipt",
            ),
            case(
                "C03", "non_po_coding_approval", "INV-NPO", "POSTED",
                ["RECEIVED", "VALIDATED", "CODED", "APPROVED", "POST_INTENT", "POSTED"],
                [attempt("A03", "PI-NPO", "posted", "TX-NPO")],
                "oracle_posting_receipt",
            ),
            case(
                "C04", "duplicate_invoice", "INV-DUP", "HOLD",
                ["RECEIVED", "DUPLICATE_DETECTED", "HOLD"], [], "duplicate_detection",
            ),
            case(
                "C05", "posting_retry", "INV-RETRY", "POSTED",
                [
                    "RECEIVED", "VALIDATED", "MATCHED", "APPROVED", "POST_INTENT",
                    "RETRYABLE_FAILURE", "POST_INTENT", "POSTED",
                ],
                [
                    attempt("A05a", "PI-RETRY", "failed"),
                    attempt("A05b", "PI-RETRY", "posted", "TX-RETRY"),
                ],
                "oracle_posting_receipt",
            ),
            case(
                "C06", "supplier_inquiry", "SUP-INQ", "INQUIRY_RESOLVED",
                ["INQUIRY_RECEIVED", "INQUIRY_RESOLVED"], [], "inquiry_resolution",
            ),
            case(
                "C07", "statement_reconciliation", "STMT-001", "RECONCILED",
                ["STATEMENT_RECEIVED", "RECONCILED"], [], "reconciliation",
            ),
            case(
                "C08", "exception_routing", "INV-EXC", "HOLD",
                ["RECEIVED", "VALIDATED", "EXCEPTION", "HOLD"], [], "exception_route",
            ),
            case(
                "C09", "reporting_audit", "AUDIT-001", "REPORTED",
                ["AUDIT_REQUESTED", "REPORTED"], [], "audit_report",
            ),
        ],
    }


def by_scenario(bundle: dict, scenario: str) -> dict:
    return next(item for item in bundle["cases"] if item["scenario"] == scenario)


class OhsuAcceptanceTests(unittest.TestCase):
    def test_ready_matrix_passes_without_external_authority(self):
        report = evaluate_matrix(ready_matrix())
        self.assertEqual(report["decision"], "ACCEPTANCE_MATRIX_READY")
        self.assertTrue(all(item["status"] == "PASS" for item in report["case_results"]))
        self.assertEqual(report["evidence_receipt_count"], 9)
        self.assertTrue(all(value is False for value in report["authority"].values()))

    def test_missing_scenario_holds(self):
        bundle = ready_matrix()
        bundle["cases"].pop()
        report = evaluate_matrix(bundle)
        self.assertEqual(report["decision"], "HOLD_ACCEPTANCE_EVIDENCE")
        self.assertEqual(report["coverage"]["missing_scenarios"], ["reporting_audit"])

    def test_duplicate_scenario_holds(self):
        bundle = ready_matrix()
        extra = copy.deepcopy(bundle["cases"][0])
        extra["case_id"] = "C10"
        extra["invoice_key"] = "INV-PO2B"
        extra["attempts"][0]["attempt_id"] = "A10"
        extra["attempts"][0]["posting_intent_id"] = "PI-PO2B"
        extra["attempts"][0]["oracle_txn_id"] = "TX-PO2B"
        extra["evidence"] = receipt("C10-evidence", "oracle_posting_receipt")
        bundle["cases"].append(extra)
        report = evaluate_matrix(bundle)
        self.assertEqual(report["decision"], "HOLD_ACCEPTANCE_EVIDENCE")
        self.assertEqual(report["coverage"]["duplicate_scenarios"], ["po_2way_match"])

    def test_duplicate_case_id_rejected(self):
        bundle = ready_matrix()
        bundle["cases"][1]["case_id"] = "C01"
        with self.assertRaises(AcceptanceInputError):
            evaluate_matrix(bundle)

    def test_unknown_scenario_rejected(self):
        bundle = ready_matrix()
        bundle["cases"][0]["scenario"] = "magic"
        with self.assertRaises(AcceptanceInputError):
            evaluate_matrix(bundle)

    def test_expected_terminal_is_scenario_bound(self):
        bundle = ready_matrix()
        bundle["cases"][0]["expected_terminal"] = "HOLD"
        with self.assertRaises(AcceptanceInputError):
            evaluate_matrix(bundle)

    def test_invalid_transition_holds_case(self):
        bundle = ready_matrix()
        by_scenario(bundle, "po_2way_match")["state_trace"] = ["RECEIVED", "VALIDATED", "POSTED"]
        report = evaluate_matrix(bundle)
        result = next(x for x in report["case_results"] if x["scenario"] == "po_2way_match")
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("invalid transition", result["detail"])

    def test_posting_requires_post_intent_state(self):
        bundle = ready_matrix()
        item = by_scenario(bundle, "po_2way_match")
        item["state_trace"] = ["RECEIVED", "VALIDATED", "MATCHED", "APPROVED", "EXCEPTION", "HOLD"]
        report = evaluate_matrix(bundle)
        result = next(x for x in report["case_results"] if x["scenario"] == "po_2way_match")
        self.assertEqual(result["status"], "HOLD")

    def test_retry_requires_retryable_failure_state(self):
        bundle = ready_matrix()
        item = by_scenario(bundle, "posting_retry")
        item["state_trace"] = ["RECEIVED", "VALIDATED", "MATCHED", "APPROVED", "POST_INTENT", "POSTED"]
        report = evaluate_matrix(bundle)
        result = next(x for x in report["case_results"] if x["scenario"] == "posting_retry")
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("RETRYABLE_FAILURE", result["detail"])

    def test_retry_must_keep_logical_intent(self):
        bundle = ready_matrix()
        item = by_scenario(bundle, "posting_retry")
        item["attempts"][1]["posting_intent_id"] = "PI-RETRY-CHANGED"
        report = evaluate_matrix(bundle)
        result = next(x for x in report["case_results"] if x["scenario"] == "posting_retry")
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("changed logical posting_intent_id", result["detail"])

    def test_retry_two_oracle_transactions_holds(self):
        bundle = ready_matrix()
        item = by_scenario(bundle, "posting_retry")
        item["attempts"] = [
            attempt("A05a", "PI-RETRY", "posted", "TX-1"),
            attempt("A05b", "PI-RETRY", "posted", "TX-2"),
        ]
        report = evaluate_matrix(bundle)
        result = next(x for x in report["case_results"] if x["scenario"] == "posting_retry")
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("multiple Oracle transaction identities", result["detail"])

    def test_repeat_success_same_oracle_txn_is_idempotent(self):
        bundle = ready_matrix()
        item = by_scenario(bundle, "posting_retry")
        item["attempts"] = [
            attempt("A05a", "PI-RETRY", "failed"),
            attempt("A05b", "PI-RETRY", "posted", "TX-RETRY"),
            attempt("A05c", "PI-RETRY", "posted", "TX-RETRY"),
        ]
        report = evaluate_matrix(bundle)
        result = next(x for x in report["case_results"] if x["scenario"] == "posting_retry")
        self.assertEqual(result["status"], "PASS")

    def test_failure_after_success_holds(self):
        bundle = ready_matrix()
        item = by_scenario(bundle, "posting_retry")
        item["attempts"] = [
            attempt("A05a", "PI-RETRY", "posted", "TX-RETRY"),
            attempt("A05b", "PI-RETRY", "failed"),
        ]
        report = evaluate_matrix(bundle)
        result = next(x for x in report["case_results"] if x["scenario"] == "posting_retry")
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("failure after successful posting", result["detail"])

    def test_non_posting_case_with_attempts_holds(self):
        bundle = ready_matrix()
        item = by_scenario(bundle, "duplicate_invoice")
        item["attempts"] = [attempt("ADUP", "PI-DUP", "posted", "TX-DUP")]
        report = evaluate_matrix(bundle)
        result = next(x for x in report["case_results"] if x["scenario"] == "duplicate_invoice")
        self.assertEqual(result["status"], "HOLD")

    def test_duplicate_invoice_needs_duplicate_state(self):
        bundle = ready_matrix()
        item = by_scenario(bundle, "duplicate_invoice")
        item["state_trace"] = ["RECEIVED", "EXCEPTION", "HOLD"]
        report = evaluate_matrix(bundle)
        result = next(x for x in report["case_results"] if x["scenario"] == "duplicate_invoice")
        self.assertEqual(result["status"], "HOLD")

    def test_exception_route_needs_exception_state(self):
        bundle = ready_matrix()
        item = by_scenario(bundle, "exception_routing")
        item["state_trace"] = ["RECEIVED", "DUPLICATE_DETECTED", "HOLD"]
        report = evaluate_matrix(bundle)
        result = next(x for x in report["case_results"] if x["scenario"] == "exception_routing")
        self.assertEqual(result["status"], "HOLD")

    def test_evidence_kind_bound_to_scenario(self):
        bundle = ready_matrix()
        by_scenario(bundle, "statement_reconciliation")["evidence"]["kind"] = "audit_report"
        with self.assertRaises(AcceptanceInputError):
            evaluate_matrix(bundle)

    def test_duplicate_evidence_receipt_rejected(self):
        bundle = ready_matrix()
        bundle["cases"][1]["evidence"]["sha256"] = bundle["cases"][0]["evidence"]["sha256"]
        with self.assertRaises(AcceptanceInputError):
            evaluate_matrix(bundle)

    def test_receipt_sha_must_be_lowercase_sha256(self):
        bundle = ready_matrix()
        bundle["cases"][0]["evidence"]["sha256"] = "A" * 64
        with self.assertRaises(AcceptanceInputError):
            evaluate_matrix(bundle)

    def test_timestamp_requires_timezone(self):
        bundle = ready_matrix()
        bundle["evaluated_at"] = "2026-09-13T09:30:00"
        with self.assertRaises(AcceptanceInputError):
            evaluate_matrix(bundle)

    def test_oracle_target_is_exact(self):
        bundle = ready_matrix()
        bundle["oracle_target"] = "Oracle Cloud"
        with self.assertRaises(AcceptanceInputError):
            evaluate_matrix(bundle)

    def test_unknown_top_field_rejected(self):
        bundle = ready_matrix()
        bundle["proposal_authorized"] = True
        with self.assertRaises(AcceptanceInputError):
            evaluate_matrix(bundle)

    def test_duplicate_attempt_id_rejected(self):
        bundle = ready_matrix()
        item = by_scenario(bundle, "posting_retry")
        item["attempts"][1]["attempt_id"] = item["attempts"][0]["attempt_id"]
        with self.assertRaises(AcceptanceInputError):
            evaluate_matrix(bundle)

    def test_failed_attempt_cannot_claim_oracle_txn(self):
        bundle = ready_matrix()
        item = by_scenario(bundle, "posting_retry")
        item["attempts"][0]["oracle_txn_id"] = "TX-IMPOSSIBLE"
        with self.assertRaises(AcceptanceInputError):
            evaluate_matrix(bundle)

    def test_global_oracle_txn_reuse_by_distinct_intents_holds(self):
        bundle = ready_matrix()
        by_scenario(bundle, "po_3way_match")["attempts"][0]["oracle_txn_id"] = "TX-PO2"
        report = evaluate_matrix(bundle)
        result = next(x for x in report["case_results"] if x["scenario"] == "po_3way_match")
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("reused", result["detail"])

    def test_retry_without_failed_attempt_holds(self):
        bundle = ready_matrix()
        item = by_scenario(bundle, "posting_retry")
        item["attempts"] = [
            attempt("A05a", "PI-RETRY", "posted", "TX-RETRY"),
            attempt("A05b", "PI-RETRY", "posted", "TX-RETRY"),
        ]
        report = evaluate_matrix(bundle)
        result = next(x for x in report["case_results"] if x["scenario"] == "posting_retry")
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("lacks a failed attempt", result["detail"])

    def test_non_retry_posting_case_cannot_hide_retry(self):
        bundle = ready_matrix()
        item = by_scenario(bundle, "po_2way_match")
        item["attempts"] = [
            attempt("A01a", "PI-PO2", "failed"),
            attempt("A01b", "PI-PO2", "posted", "TX-PO2"),
        ]
        report = evaluate_matrix(bundle)
        result = next(x for x in report["case_results"] if x["scenario"] == "po_2way_match")
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("exactly one successful attempt", result["detail"])

    def test_evidence_cannot_postdate_evaluation(self):
        bundle = ready_matrix()
        bundle["cases"][0]["evidence"]["captured_at"] = "2026-09-13T09:31:00Z"
        with self.assertRaises(AcceptanceInputError):
            evaluate_matrix(bundle)

    def test_report_is_deterministic(self):
        bundle = ready_matrix()
        first = evaluate_matrix(bundle, input_sha256="1" * 64)
        second = evaluate_matrix(json.loads(json.dumps(bundle)), input_sha256="1" * 64)
        self.assertEqual(first, second)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "matrix.json"
            path.write_text('{"oracle_target":"EBS_R12","oracle_target":"bad"}', encoding="utf-8")
            with self.assertRaises(AcceptanceInputError):
                load_json_object(path)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unsupported")
    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target.json"
            target.write_text(json.dumps(ready_matrix()), encoding="utf-8")
            alias = root / "alias.json"
            try:
                alias.symlink_to(target)
            except OSError:
                self.skipTest("symlink unavailable")
            with self.assertRaises(AcceptanceInputError):
                load_json_object(alias)

    def test_cli_hold_exit_2_and_atomic_output(self):
        bundle = ready_matrix()
        bundle["cases"].pop()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "in.json"
            dst = root / "out.json"
            src.write_text(json.dumps(bundle), encoding="utf-8")
            self.assertEqual(main([str(src), "--output", str(dst)]), 2)
            report = json.loads(dst.read_text(encoding="utf-8"))
            self.assertEqual(report["decision"], "HOLD_ACCEPTANCE_EVIDENCE")
            self.assertEqual(report["input_sha256"], hashlib.sha256(src.read_bytes()).hexdigest())

    def test_cli_rejects_hardlink_alias(self):
        if not hasattr(os, "link"):
            self.skipTest("hardlinks unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "in.json"
            src.write_text(json.dumps(ready_matrix()), encoding="utf-8")
            dst = root / "same.json"
            try:
                os.link(src, dst)
            except OSError:
                self.skipTest("hardlinks unavailable")
            self.assertEqual(main([str(src), "--output", str(dst)]), 3)


if __name__ == "__main__":
    unittest.main()
