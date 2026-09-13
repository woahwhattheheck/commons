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
    "settled_awards", ROOT / "host" / "settled_awards.py"
)
assert SPEC and SPEC.loader
settled = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(settled)
LEDGER_PATH = ROOT / "revenue" / "right_now" / "settled_awards.json"


class SettledAwardsTests(unittest.TestCase):
    def ledger(self):
        return settled.read_ledger(LEDGER_PATH)

    def test_canonical_ledger_validates_and_summarizes(self):
        summary = settled.summarize_ledger(self.ledger())
        self.assertEqual(summary["paid_awards"], 1)
        self.assertEqual(
            summary["totals_by_currency"],
            [{"currency": "RTC", "amount": "25"}],
        )
        self.assertIsNone(summary["usd_equivalent"])
        self.assertIs(summary["usd_conversion_asserted"], False)
        self.assertIs(summary["bank_availability_asserted"], False)
        self.assertIs(summary["withdrawability_asserted"], False)
        self.assertEqual(summary["awards"][0]["collection_action"], "NONE_DO_NOT_RESEND")
        self.assertNotIn("receipt", summary["awards"][0])
        self.assertNotIn("idempotency_key", summary["awards"][0])

    def test_private_receipt_locator_is_not_published(self):
        text = LEDGER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("gmail", text.lower())
        self.assertNotIn("thread", text.lower())
        self.assertNotIn("message_id", text.lower())
        self.assertIn('"reference_visibility": "PRIVATE_REDACTED"', text)

    def test_duplicate_json_key_fails_closed(self):
        with self.assertRaisesRegex(settled.SettlementError, "duplicate JSON key"):
            settled.loads_strict('{"schema_version":"a","schema_version":"b"}')

    def test_nonfinite_json_number_fails_closed(self):
        with self.assertRaisesRegex(settled.SettlementError, "non-finite"):
            settled.loads_strict('{"x":NaN}')

    def test_duplicate_award_id_fails_closed(self):
        value = self.ledger()
        value["awards"].append(copy.deepcopy(value["awards"][0]))
        value["awards"][1]["idempotency_key"] += "-two"
        value["awards"][1]["receipt"]["public_receipt_id"] += "-two"
        with self.assertRaisesRegex(settled.SettlementError, "duplicate award_id"):
            settled.validate_ledger(value)

    def test_duplicate_idempotency_key_fails_closed(self):
        value = self.ledger()
        other = copy.deepcopy(value["awards"][0])
        other["award_id"] += "-two"
        other["receipt"]["public_receipt_id"] += "-two"
        value["awards"].append(other)
        with self.assertRaisesRegex(settled.SettlementError, "duplicate idempotency_key"):
            settled.validate_ledger(value)

    def test_noncanonical_amounts_fail_closed(self):
        for amount in (25, "025", "25.0", "0", "-1", "1e2", "NaN"):
            with self.subTest(amount=amount):
                value = self.ledger()
                value["awards"][0]["amount"] = amount
                with self.assertRaises(settled.SettlementError):
                    settled.validate_ledger(value)

    def test_invented_usd_conversion_fails_closed(self):
        value = self.ledger()
        value["awards"][0]["usd_equivalent"] = "1.25"
        with self.assertRaisesRegex(settled.SettlementError, "usd_equivalent"):
            settled.validate_ledger(value)

    def test_withdrawability_or_bank_availability_cannot_be_promoted(self):
        value = self.ledger()
        value["awards"][0]["hold"]["availability_state"] = "AVAILABLE"
        with self.assertRaisesRegex(settled.SettlementError, "NOT_ASSERTED"):
            settled.validate_ledger(value)

    def test_duplicate_collection_is_forbidden(self):
        value = self.ledger()
        value["awards"][0]["collection_action"] = "REQUEST_AGAIN"
        with self.assertRaisesRegex(settled.SettlementError, "NONE_DO_NOT_RESEND"):
            settled.validate_ledger(value)

    def test_private_locator_field_fails_exact_schema(self):
        value = self.ledger()
        value["awards"][0]["receipt"]["private_email_thread_id"] = "secret"
        with self.assertRaisesRegex(settled.SettlementError, "fields differ"):
            settled.validate_ledger(value)

    def test_paid_date_after_as_of_fails_closed(self):
        value = self.ledger()
        value["awards"][0]["paid_at"] = "2026-09-14"
        with self.assertRaisesRegex(settled.SettlementError, "later than"):
            settled.validate_ledger(value)

    def test_public_urls_are_clean_github_issue_urls(self):
        for url in (
            "http://github.com/Scottcjn/Rustchain/issues/8395",
            "https://user@github.com/Scottcjn/Rustchain/issues/8395",
            "https://github.com/Scottcjn/Rustchain/issues/8395?token=x",
            "https://github.com/Scottcjn/Rustchain/issues/8395#private",
            "https://github.com:bad/Scottcjn/Rustchain/issues/8395",
            "https://[github.com/Scottcjn/Rustchain/issues/8395",
            "https://example.com/Scottcjn/Rustchain/issues/8395",
            "https://github.com/Scottcjn/Rustchain/commit/abc",
        ):
            with self.subTest(url=url):
                value = self.ledger()
                value["awards"][0]["result_url"] = url
                with self.assertRaisesRegex(settled.SettlementError, "clean public GitHub"):
                    settled.validate_ledger(value)

    def test_claimant_and_hosted_destination_must_match(self):
        value = self.ledger()
        value["awards"][0]["destination_reference"] = "other-handle"
        with self.assertRaisesRegex(settled.SettlementError, "match the public claimant"):
            settled.validate_ledger(value)

    def test_award_order_is_deterministic(self):
        value = self.ledger()
        later = copy.deepcopy(value["awards"][0])
        later["award_id"] = "aaa-later"
        later["idempotency_key"] += "-later"
        later["receipt"]["public_receipt_id"] += "-later"
        later["paid_at"] = "2026-09-12"
        value["awards"].insert(0, later)
        with self.assertRaisesRegex(settled.SettlementError, "ordered"):
            settled.validate_ledger(value)

    def test_cli_validate_and_summary_are_deterministic(self):
        script = ROOT / "host" / "settled_awards.py"
        validate = subprocess.run(
            [sys.executable, str(script), "validate", str(LEDGER_PATH)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("25 RTC", validate.stdout)
        self.assertIn("no USD conversion", validate.stdout)
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
                [sys.executable, str(ROOT / "host" / "settled_awards.py"), "validate", str(path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("INVALID:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
