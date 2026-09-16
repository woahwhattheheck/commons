import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from revenue.finished_work_cash_closeout.closeout import (
    CloseoutError,
    SCHEMA,
    build_closeout,
    compile_ledger,
    compile_to_dir,
    normalize_ledger,
    verify_dir,
)


def base_item(**overrides):
    item = {
        "work_id": "frantic-120-pr-1423",
        "payer_key": "frantic",
        "opportunity_key": "bounty-120",
        "payment_unit_key": "pylon-1423",
        "route_key": "github:frantic/bounty-120",
        "currency": "USD",
        "advertised_amount_minor": 100,
        "advertised_reward_evidence": ["reward-source"],
        "eligibility_state": "ELIGIBLE",
        "eligibility_evidence": ["eligibility-source"],
        "completion_kind": "MERGED",
        "completion_receipts": ["merge-receipt"],
        "provider_state": "MERGED",
        "provider_state_evidence": ["provider-state-receipt"],
        "payment_state": "UNPAID",
        "payment_state_evidence": ["unpaid-state-receipt"],
        "payment_receipts": [],
        "prior_payment_request_receipts": [],
        "muse_owner": None,
        "dnr": False,
    }
    item.update(overrides)
    return item


def ledger(*items):
    return {"schema": SCHEMA, "items": list(items)}


class CashCloseoutTests(unittest.TestCase):
    def status(self, item):
        return build_closeout(ledger(item))["groups"][0]

    def test_ready_requires_muse_and_never_authorizes_send(self):
        group = self.status(base_item())
        self.assertEqual(group["status"], "READY_FOR_MUSE_ELECTION")
        self.assertTrue(all(value is False for value in group["authority"].values()))

    def test_paid_requires_payment_receipt(self):
        with self.assertRaises(CloseoutError):
            normalize_ledger(ledger(base_item(payment_state="PAID", payment_state_evidence=[], payment_receipts=[])))
        group = self.status(
            base_item(
                payment_state="PAID",
                payment_state_evidence=["paid-state"],
                payment_receipts=["stripe-receipt"],
            )
        )
        self.assertEqual(group["status"], "PAYMENT_CONFIRMED")

    def test_non_paid_cannot_carry_payment_receipt(self):
        with self.assertRaises(CloseoutError):
            normalize_ledger(ledger(base_item(payment_receipts=["not-allowed"])))

    def test_prior_request_blocks_repeat(self):
        group = self.status(base_item(prior_payment_request_receipts=["gmail-sent-id"]))
        self.assertEqual(group["status"], "WAIT_EXISTING_REQUEST")

    def test_muse_owner_blocks_request_ready(self):
        group = self.status(base_item(muse_owner="z-other"))
        self.assertEqual(group["status"], "COLLISION_RECONCILE")
        self.assertIn("MUSE_OWNER_PRESENT", group["reason_codes"])

    def test_dnr_dominates_contact_path(self):
        group = self.status(base_item(dnr=True, prior_payment_request_receipts=["old-send"]))
        self.assertEqual(group["status"], "DNR_NO_SEND")

    def test_missing_evidence_is_gap(self):
        group = self.status(
            base_item(
                advertised_reward_evidence=[],
                eligibility_evidence=[],
                completion_receipts=[],
                provider_state_evidence=[],
                payment_state_evidence=[],
            )
        )
        self.assertEqual(group["status"], "EVIDENCE_GAP")
        self.assertIn("MISSING_ADVERTISED_REWARD_EVIDENCE", group["reason_codes"])
        self.assertIn("MISSING_COMPLETION_RECEIPT", group["reason_codes"])
        self.assertIn("MISSING_UNPAID_EVIDENCE", group["reason_codes"])

    def test_provider_review_waits(self):
        self.assertEqual(self.status(base_item(provider_state="REVIEW"))["status"], "WAIT_PROVIDER")

    def test_payment_pending_waits(self):
        self.assertEqual(self.status(base_item(payment_state="PENDING"))["status"], "WAIT_PROVIDER")

    def test_unknown_payment_state_is_gap(self):
        group = self.status(base_item(payment_state="UNKNOWN", payment_state_evidence=[]))
        self.assertEqual(group["status"], "EVIDENCE_GAP")
        self.assertIn("PAYMENT_STATE_UNKNOWN", group["reason_codes"])

    def test_ineligible_and_rejected_are_terminal(self):
        self.assertEqual(self.status(base_item(eligibility_state="INELIGIBLE"))["status"], "INELIGIBLE")
        self.assertEqual(self.status(base_item(provider_state="REJECTED"))["status"], "INELIGIBLE")

    def test_duplicate_work_id_rejected(self):
        first = base_item()
        with self.assertRaises(CloseoutError):
            normalize_ledger(ledger(first, deepcopy(first)))

    def test_duplicate_payment_slot_reconciles_once(self):
        packet = build_closeout(ledger(base_item(), base_item(work_id="frantic-120-pr-1424")))
        self.assertEqual(packet["summary"]["payment_slots"], 1)
        group = packet["groups"][0]
        self.assertEqual(group["status"], "COLLISION_RECONCILE")
        self.assertEqual(group["work_ids"], ["frantic-120-pr-1423", "frantic-120-pr-1424"])

    def test_duplicate_slot_with_dnr_stays_no_send(self):
        packet = build_closeout(
            ledger(base_item(), base_item(work_id="frantic-120-pr-1424", dnr=True))
        )
        self.assertEqual(packet["groups"][0]["status"], "DNR_NO_SEND")

    def test_duplicate_slot_all_paid_is_confirmed_not_requestable(self):
        first = base_item(
            payment_state="PAID",
            payment_state_evidence=["paid-state-a"],
            payment_receipts=["receipt-a"],
        )
        second = base_item(
            work_id="frantic-120-pr-1424",
            payment_state="PAID",
            payment_state_evidence=["paid-state-b"],
            payment_receipts=["receipt-b"],
        )
        group = build_closeout(ledger(first, second))["groups"][0]
        self.assertEqual(group["status"], "PAYMENT_CONFIRMED")
        self.assertTrue(all(value is False for value in group["authority"].values()))

    def test_deterministic_under_input_order(self):
        a = base_item(work_id="a", payment_unit_key="a-unit")
        b = base_item(work_id="b", payment_unit_key="b-unit")
        self.assertEqual(compile_ledger(ledger(a, b)), compile_ledger(ledger(b, a)))

    def test_strict_schema_rejects_unknown_key(self):
        item = base_item()
        item["send_authorized"] = True
        with self.assertRaises(CloseoutError):
            normalize_ledger(ledger(item))

    def test_boolean_amount_rejected(self):
        with self.assertRaises(CloseoutError):
            normalize_ledger(ledger(base_item(advertised_amount_minor=True)))

    def test_bundle_verify_detects_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "ledger.json"
            input_path.write_text(json.dumps(ledger(base_item())), encoding="utf-8")
            out = root / "out"
            compile_to_dir(input_path, out)
            verify_dir(input_path, out)
            (out / "closeout.md").write_text("tampered\n", encoding="utf-8")
            with self.assertRaises(CloseoutError):
                verify_dir(input_path, out)

    def test_compile_refuses_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "ledger.json"
            input_path.write_text(json.dumps(ledger(base_item())), encoding="utf-8")
            out = root / "out"
            out.mkdir()
            with self.assertRaises(CloseoutError):
                compile_to_dir(input_path, out)

    def test_cli_roundtrip_then_tamper_returns_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "ledger.json"
            input_path.write_text(json.dumps(ledger(base_item())), encoding="utf-8")
            out = root / "bundle"
            script = Path("revenue/finished_work_cash_closeout/closeout.py")
            compile_run = subprocess.run(
                [sys.executable, str(script), "compile", str(input_path), str(out)],
                text=True, capture_output=True, check=False, timeout=10,
            )
            self.assertEqual(compile_run.returncode, 0, compile_run.stderr)
            verify_run = subprocess.run(
                [sys.executable, str(script), "verify", str(input_path), str(out)],
                text=True, capture_output=True, check=False, timeout=10,
            )
            self.assertEqual(verify_run.returncode, 0, verify_run.stderr)
            (out / "receipt.json").write_text("{}\n", encoding="utf-8")
            bad_run = subprocess.run(
                [sys.executable, str(script), "verify", str(input_path), str(out)],
                text=True, capture_output=True, check=False, timeout=10,
            )
            self.assertEqual(bad_run.returncode, 2)


if __name__ == "__main__":
    unittest.main()
