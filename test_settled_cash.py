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
AUTHORITY_PATH = ROOT / "revenue" / "right_now" / "settled_cash_authority.json"


class SettledCashTests(unittest.TestCase):
    def ledger(self):
        return settled.read_ledger(LEDGER_PATH)

    def authority(self):
        return settled.read_authority(AUTHORITY_PATH)

    def test_canonical_receipt_validates_and_summarizes_under_pinned_authority(self):
        summary = settled.summarize_ledger(self.ledger())
        self.assertEqual(summary["settled_receipts"], 1)
        self.assertEqual(summary["settled_usd"], "1")
        self.assertEqual(summary["authority_state"], "PINNED_RETAINED_PROVIDER_EVIDENCE")
        self.assertEqual(summary["authority_root_sha256"], settled.TRUSTED_AUTHORITY_ROOT)
        self.assertIs(summary["bank_availability_asserted"], False)
        self.assertIs(summary["withdrawability_asserted"], False)
        receipt = summary["receipts"][0]
        self.assertEqual(receipt["payment_state"], "PAID")
        self.assertEqual(receipt["provider_url"], "https://gofrantic.com/")
        self.assertEqual(receipt["bounty_number"], 120)
        self.assertEqual(receipt["provider_receipt_id"], "r/ef2f247c")
        self.assertEqual(receipt["source_evidence_ref"], "https://gofrantic.com/a/agent-df56d0")
        self.assertEqual(receipt["collection_action"], "NONE_DO_NOT_RESEND")
        self.assertNotIn("idempotency_key", receipt)
        self.assertNotIn("provider_claim_id", receipt)

    def test_fully_fabricated_paid_row_is_not_settled_cash(self):
        value = self.ledger()
        row = value["receipts"][0]
        row.update(
            {
                "cash_id": "fabricated-paid-row",
                "provider_claim_id": "11111111-1111-1111-1111-111111111111",
                "provider_receipt_id": "r/deadbeef",
                "result_url": "https://github.com/example/example/pull/1",
                "claimant": "fabricator",
                "amount_usd": "999999",
                "idempotency_key": "fabricated-paid-row",
            }
        )
        settled.validate_ledger(value)
        inspection = settled.inspect_ledger(value)
        self.assertEqual(inspection["candidate_usd"], "999999")
        self.assertIs(inspection["settled_cash_asserted"], False)
        with self.assertRaisesRegex(settled.CashSettlementError, "authority universe"):
            settled.summarize_ledger(value)

    def test_candidate_field_transplants_fail_authority(self):
        mutations = {
            "amount_usd": "2",
            "result_url": "https://github.com/sourcey/startup-credits/pull/1424",
            "claimant": "sourcey",
            "provider_receipt_id": "r/deadbeef",
            "program": "Frantic bounty #120 / Other delivery",
        }
        for field, replacement in mutations.items():
            with self.subTest(field=field):
                value = self.ledger()
                value["receipts"][0][field] = replacement
                settled.validate_ledger(value)
                with self.assertRaises(settled.CashSettlementError):
                    settled.summarize_ledger(value)

    def test_coupled_candidate_and_authority_mutation_fails_stale_pin(self):
        ledger = self.ledger()
        authority = self.authority()
        ledger["receipts"][0]["amount_usd"] = "2"
        authority["records"][0]["amount_usd"] = "2"
        authority["records"][0]["source_evidence_sha256"] = settled.source_evidence_sha256(
            authority["records"][0]
        )
        with self.assertRaisesRegex(settled.CashSettlementError, "trusted pinned root"):
            settled.reconcile_authority(ledger, authority, settled.TRUSTED_AUTHORITY_ROOT)

    def test_authority_expansion_and_omission_fail_closed(self):
        authority = self.authority()
        extra = copy.deepcopy(authority["records"][0])
        extra.update(
            {
                "provider_claim_id": "11111111-1111-1111-1111-111111111111",
                "provider_receipt_id": "r/deadbeef",
                "result_url": "https://github.com/sourcey/startup-credits/pull/1424",
                "source_evidence_ref": "https://gofrantic.com/a/agent-second",
            }
        )
        extra["source_evidence_sha256"] = settled.source_evidence_sha256(extra)
        expanded = copy.deepcopy(authority)
        expanded["records"].append(extra)
        expanded["records"].sort(key=lambda row: (row["evidenced_at"], row["provider_receipt_id"]))
        with self.assertRaisesRegex(settled.CashSettlementError, "trusted pinned root"):
            settled.reconcile_authority(self.ledger(), expanded, settled.TRUSTED_AUTHORITY_ROOT)

        omitted = copy.deepcopy(authority)
        omitted["records"] = []
        with self.assertRaisesRegex(settled.CashSettlementError, "non-empty"):
            settled.reconcile_authority(self.ledger(), omitted, settled.TRUSTED_AUTHORITY_ROOT)

    def test_source_evidence_digest_drift_fails_closed(self):
        authority = self.authority()
        authority["records"][0]["source_evidence_sha256"] = "0" * 64
        with self.assertRaisesRegex(settled.CashSettlementError, "does not bind"):
            settled.validate_authority(authority)

    def test_duplicate_authority_claim_receipt_and_source_fail_closed(self):
        for field, replacement, pattern in (
            (
                "provider_claim_id",
                "04ef83a2-ba34-4a0b-8678-84eac9f00a96",
                "duplicate authority provider_claim_id",
            ),
            ("provider_receipt_id", "r/ef2f247c", "duplicate authority provider_receipt_id"),
            (
                "source_evidence_ref",
                "https://gofrantic.com/a/agent-df56d0",
                "duplicate authority source_evidence_ref",
            ),
        ):
            with self.subTest(field=field):
                authority = self.authority()
                other = copy.deepcopy(authority["records"][0])
                other.update(
                    {
                        "provider_claim_id": "11111111-1111-1111-1111-111111111111",
                        "provider_receipt_id": "r/deadbeef",
                        "result_url": "https://github.com/sourcey/startup-credits/pull/1424",
                        "source_evidence_ref": "https://gofrantic.com/a/agent-second",
                    }
                )
                other[field] = replacement
                other["source_evidence_sha256"] = settled.source_evidence_sha256(other)
                authority["records"].append(other)
                authority["records"].sort(
                    key=lambda row: (row["evidenced_at"], row["provider_receipt_id"])
                )
                with self.assertRaisesRegex(settled.CashSettlementError, pattern):
                    settled.validate_authority(authority)

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

    def test_provider_root_result_and_evidence_urls_are_allowlisted(self):
        for url in (
            "http://gofrantic.com/",
            "https://example.com/",
            "https://gofrantic.com/bounties/120",
            "https://gofrantic.com/?secret=x",
        ):
            with self.subTest(url=url):
                value = self.ledger()
                value["receipts"][0]["provider_url"] = url
                with self.assertRaisesRegex(settled.CashSettlementError, "canonical Frantic root"):
                    settled.validate_ledger(value)
        for url in (
            "https://github.com/sourcey/startup-credits/issues/1423",
            "https://github.com/sourcey/startup-credits/pull/1423#x",
            "http://github.com/sourcey/startup-credits/pull/1423",
        ):
            with self.subTest(url=url):
                value = self.ledger()
                value["receipts"][0]["result_url"] = url
                with self.assertRaisesRegex(settled.CashSettlementError, "clean public HTTPS URL"):
                    settled.validate_ledger(value)
        authority = self.authority()
        authority["records"][0]["source_evidence_ref"] = "https://example.com/a/agent-df56d0"
        authority["records"][0]["source_evidence_sha256"] = settled.source_evidence_sha256(
            authority["records"][0]
        )
        with self.assertRaisesRegex(settled.CashSettlementError, "clean public HTTPS URL"):
            settled.validate_authority(authority)

    def test_bounty_number_must_be_positive_integer(self):
        for number in (0, -1, "120", True, 1.5):
            with self.subTest(number=number):
                value = self.ledger()
                value["receipts"][0]["bounty_number"] = number
                with self.assertRaisesRegex(settled.CashSettlementError, "positive integer"):
                    settled.validate_ledger(value)

    def test_evidence_time_cannot_be_future_of_artifact(self):
        value = self.ledger()
        value["receipts"][0]["evidenced_at"] = "2026-09-13T15:34:34Z"
        with self.assertRaisesRegex(settled.CashSettlementError, "later than"):
            settled.validate_ledger(value)

    def test_private_fields_fail_exact_schema(self):
        value = self.ledger()
        value["receipts"][0]["private_payout_address"] = "secret"
        with self.assertRaisesRegex(settled.CashSettlementError, "fields differ"):
            settled.validate_ledger(value)
        authority = self.authority()
        authority["records"][0]["private_provider_token"] = "secret"
        with self.assertRaisesRegex(settled.CashSettlementError, "fields differ"):
            settled.validate_authority(authority)

    def test_duplicate_json_key_and_nonfinite_fail_closed(self):
        with self.assertRaisesRegex(settled.CashSettlementError, "duplicate JSON key"):
            settled.loads_strict('{"schema_version":"a","schema_version":"b"}')
        with self.assertRaisesRegex(settled.CashSettlementError, "non-finite"):
            settled.loads_strict('{"x":NaN}')

    def test_cli_validate_summary_and_inspect_are_deterministic(self):
        script = ROOT / "host" / "settled_cash.py"
        validate = subprocess.run(
            [sys.executable, str(script), "validate", str(LEDGER_PATH)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("AUTHORIZED", validate.stdout)
        self.assertIn("USD 1 PAID", validate.stdout)
        self.assertIn(settled.TRUSTED_AUTHORITY_ROOT, validate.stdout)
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
        inspected = subprocess.run(
            [sys.executable, str(script), "inspect", str(LEDGER_PATH)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        inspection = json.loads(inspected.stdout)
        self.assertEqual(inspection["authority_state"], "UNVERIFIED_FORMAT_ONLY")
        self.assertIs(inspection["settled_cash_asserted"], False)

    def test_cli_forged_well_shaped_ledger_returns_nonzero_for_authoritative_commands(self):
        forged = self.ledger()
        forged["receipts"][0].update(
            {
                "cash_id": "fake",
                "provider_claim_id": "11111111-1111-1111-1111-111111111111",
                "provider_receipt_id": "r/deadbeef",
                "amount_usd": "9000",
                "idempotency_key": "fake-paid",
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "fake.json")
            path.write_text(settled.canonical_text(forged), encoding="utf-8")
            for command in ("validate", "summary"):
                with self.subTest(command=command):
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "host" / "settled_cash.py"), command, str(path)],
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("INVALID:", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
            inspect = subprocess.run(
                [sys.executable, str(ROOT / "host" / "settled_cash.py"), "inspect", str(path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(json.loads(inspect.stdout)["candidate_usd"], "9000")

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
