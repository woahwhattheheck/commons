from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "settled_cash", ROOT / "host" / "settled_cash.py"
)
assert SPEC and SPEC.loader
settled = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(settled)
LEDGER_PATH = ROOT / "revenue" / "right_now" / "settled_cash.json"


class SettledCashTests(unittest.TestCase):
    def ledger(self):
        return settled.read_ledger(LEDGER_PATH)

    def test_canonical_receipt_validates_and_summarizes(self):
        summary = settled.summarize_ledger(self.ledger())
        self.assertEqual(summary["settled_receipts"], 1)
        self.assertEqual(summary["settled_usd"], "1")
        self.assertIs(summary["bank_availability_asserted"], False)
        self.assertIs(summary["withdrawability_asserted"], False)
        receipt = summary["receipts"][0]
        self.assertEqual(receipt["payment_state"], "PAID")
        self.assertEqual(receipt["provider_receipt_id"], "r/ef2f247c")
        self.assertEqual(receipt["collection_action"], "NONE_DO_NOT_RESEND")
        self.assertNotIn("idempotency_key", receipt)
        self.assertNotIn("provider_claim_id", receipt)

    def test_only_paid_rows_can_enter_cash_truth(self):
        for state in ("SENT", "MERGED", "ACCEPTED", "DELIVERED", "FUNDED", "PENDING"):
            with self.subTest(state=state):
                value = self.ledger()
                value["receipts"][0]["payment_state"] = state
                with self.assertRaisesRegex(settled.CashSettlementError, "must be PAID"):
                    settled.validate_ledger(value)

    def test_noncanonical_amounts_fail_closed(self):
        for amount in (1, "01", "1.0", "0", "-1", "1e2", "NaN"):
            with self.subTest(amount=amount):
                value = self.ledger()
                value["receipts"][0]["amount_usd"] = amount
                with self.assertRaises(settled.CashSettlementError):
                    settled.validate_ledger(value)

    def test_duplicate_receipt_claim_and_idempotency_fail_closed(self):
        for field, pattern in (
            ("provider_receipt_id", "duplicate provider_receipt_id"),
            ("provider_claim_id", "duplicate provider_claim_id"),
            ("idempotency_key", "duplicate idempotency_key"),
        ):
            with self.subTest(field=field):
                value = self.ledger()
                other = copy.deepcopy(value["receipts"][0])
                other["cash_id"] += "-two"
                if field != "provider_receipt_id":
                    other["provider_receipt_id"] = "r/deadbeef"
                if field != "provider_claim_id":
                    other["provider_claim_id"] = "11111111-1111-1111-1111-111111111111"
                if field != "idempotency_key":
                    other["idempotency_key"] += "-two"
                value["receipts"].append(other)
                with self.assertRaisesRegex(settled.CashSettlementError, pattern):
                    settled.validate_ledger(value)

    def test_bank_or_withdrawability_promotion_fails_closed(self):
        for field in ("bank_availability_state", "withdrawability_state"):
            with self.subTest(field=field):
                value = self.ledger()
                value["receipts"][0][field] = "AVAILABLE"
                with self.assertRaisesRegex(settled.CashSettlementError, "NOT_ASSERTED"):
                    settled.validate_ledger(value)

    def test_duplicate_collection_request_fails_closed(self):
        value = self.ledger()
        value["receipts"][0]["collection_action"] = "REQUEST_AGAIN"
        with self.assertRaisesRegex(settled.CashSettlementError, "NONE_DO_NOT_RESEND"):
            settled.validate_ledger(value)

    def test_urls_are_allowlisted_and_clean(self):
        cases = (
            ("bounty_url", "http://gofrantic.com/bounties/120"),
            ("bounty_url", "https://example.com/bounties/120"),
            ("bounty_url", "https://gofrantic.com/bounties/120?secret=x"),
            ("result_url", "https://github.com/sourcey/startup-credits/issues/1423"),
            ("result_url", "https://github.com/sourcey/startup-credits/pull/1423#x"),
        )
        for field, url in cases:
            with self.subTest(field=field, url=url):
                value = self.ledger()
                value["receipts"][0][field] = url
                with self.assertRaisesRegex(settled.CashSettlementError, "clean public HTTPS URL"):
                    settled.validate_ledger(value)

    def test_evidence_time_cannot_be_future_of_ledger(self):
        value = self.ledger()
        value["receipts"][0]["evidenced_at"] = "2026-09-13T15:34:34Z"
        with self.assertRaisesRegex(settled.CashSettlementError, "later than"):
            settled.validate_ledger(value)

    def test_private_fields_fail_exact_schema(self):
        value = self.ledger()
        value["receipts"][0]["private_payout_address"] = "secret"
        with self.assertRaisesRegex(settled.CashSettlementError, "fields differ"):
            settled.validate_ledger(value)

    def test_duplicate_json_key_and_nonfinite_fail_closed(self):
        with self.assertRaisesRegex(settled.CashSettlementError, "duplicate JSON key"):
            settled.loads_strict('{"schema_version":"a","schema_version":"b"}')
        with self.assertRaisesRegex(settled.CashSettlementError, "non-finite"):
            settled.loads_strict('{"x":NaN}')

    def test_cli_validate_and_summary_are_deterministic(self):
        script = ROOT / "host" / "settled_cash.py"
        validate = subprocess.run(
            [sys.executable, str(script), "validate", str(LEDGER_PATH)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("USD 1 PAID", validate.stdout)
        self.assertIn("not asserted", validate.stdout)
        first = subprocess.run(
            [sys.executable, str(script), "summary", str(LEDGER_PATH)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        second = subprocess.run(
            [sys.executable, str(script), "summary", str(LEDGER_PATH)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout), settled.summarize_ledger(self.ledger()))

    def test_invalid_file_returns_nonzero_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "bad.json")
            path.write_text('{"x":NaN}', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "host" / "settled_cash.py"), "validate", str(path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("INVALID:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
