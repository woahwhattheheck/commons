import copy
import json
import tempfile
import unittest
from pathlib import Path

import cash_realization_ledger as crl


def claim_digest(claim):
    return crl._sha256(claim)


def packet():
    claim = {
        "id": "claim-lily-267",
        "kind": "BOUNTY",
        "counterparty_ref": "counterparty-lily",
        "currency": "USD",
        "reference_amount_minor": 9000,
        "created_at": "2026-09-06T12:00:00Z",
        "source_ref": "github://issue/267",
        "source_sha256": "1" * 64,
    }
    digest = claim_digest(claim)
    return {
        "schema_version": 1,
        "portfolio": {"name": "Synthetic Funded Work"},
        "claims": [claim],
        "events": [
            {
                "id": "ev-award",
                "claim_id": claim["id"],
                "claim_sha256": digest,
                "kind": "AWARD_EVIDENCE",
                "occurred_at": "2026-09-06T13:00:00Z",
                "evidence_id": "e-award",
                "amount_minor": 9000,
            }
        ],
        "evidence": [
            {
                "id": "e-award",
                "status": "verified",
                "authority": "sponsor_evidence",
                "captured_at": "2026-09-06T13:01:00Z",
                "reference": "synthetic://sponsor/award",
                "sha256": "2" * 64,
            }
        ],
    }


def add_event(p, *, event_id, kind, time, evidence_id, authority, amount=9000, status="verified"):
    p["events"].append({
        "id": event_id,
        "claim_id": p["claims"][0]["id"],
        "claim_sha256": claim_digest(p["claims"][0]),
        "kind": kind,
        "occurred_at": time,
        "evidence_id": evidence_id,
        **({"amount_minor": amount} if kind != "OPPORTUNITY_RECORDED" else {}),
    })
    p["evidence"].append({
        "id": evidence_id,
        "status": status,
        "authority": authority,
        "captured_at": time,
        "reference": f"synthetic://evidence/{evidence_id}",
        "sha256": (format(len(p["evidence"]) + 3, "x")[-1] or "a") * 64,
    })
    return p


class CashRealizationLedgerTests(unittest.TestCase):
    def test_award_is_not_cash(self):
        out = crl.compile_ledger(packet())
        row = out["claims"][0]
        self.assertEqual(row["state"], "AWARDED")
        self.assertEqual(row["net_received_minor"], 0)
        self.assertFalse(out["summary"]["accounting_revenue_recognized"])

    def test_invoice_and_pending_are_not_cash(self):
        p = packet()
        add_event(p, event_id="ev-request", kind="REQUESTED_OR_INVOICED_EVIDENCE", time="2026-09-07T12:00:00Z", evidence_id="e-request", authority="internal_record")
        add_event(p, event_id="ev-pending", kind="PAYMENT_PENDING_EVIDENCE", time="2026-09-07T13:00:00Z", evidence_id="e-pending", authority="payment_provider_evidence")
        row = crl.compile_ledger(p)["claims"][0]
        self.assertEqual(row["state"], "PAYMENT_PENDING")
        self.assertEqual(row["net_received_minor"], 0)

    def test_wrong_authority_cannot_mint_cash(self):
        p = packet()
        add_event(p, event_id="ev-cash", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-cash", authority="owner_approved")
        row = crl.compile_ledger(p)["claims"][0]
        self.assertEqual(row["state"], "HOLD")
        self.assertIn("ev-cash:AUTHORITY_MISMATCH", row["blockers"])
        self.assertEqual(row["net_received_minor"], 0)

    def test_full_receipt_requires_payment_or_bank_authority(self):
        p = packet()
        add_event(p, event_id="ev-cash", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-cash", authority="payment_provider_evidence")
        row = crl.compile_ledger(p)["claims"][0]
        self.assertEqual(row["state"], "RECEIVED")
        self.assertEqual(row["net_received_minor"], 9000)

    def test_partial_receipt(self):
        p = packet()
        add_event(p, event_id="ev-cash", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-cash", authority="bank_record", amount=4000)
        row = crl.compile_ledger(p)["claims"][0]
        self.assertEqual(row["state"], "PARTIALLY_RECEIVED")
        self.assertEqual(row["outstanding_reference_minor"], 5000)

    def test_reversal_knocks_state_back(self):
        p = packet()
        add_event(p, event_id="ev-cash", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-cash", authority="bank_record")
        add_event(p, event_id="ev-rev", kind="PAYMENT_REVERSED_EVIDENCE", time="2026-09-09T12:00:00Z", evidence_id="e-rev", authority="bank_record", amount=2500)
        row = crl.compile_ledger(p)["claims"][0]
        self.assertEqual(row["state"], "REVERSED")
        self.assertEqual(row["net_received_minor"], 6500)

    def test_reversal_cannot_exceed_prior_receipt(self):
        p = packet()
        add_event(p, event_id="ev-cash", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-cash", authority="bank_record", amount=2000)
        add_event(p, event_id="ev-rev", kind="PAYMENT_REVERSED_EVIDENCE", time="2026-09-09T12:00:00Z", evidence_id="e-rev", authority="bank_record", amount=2500)
        row = crl.compile_ledger(p)["claims"][0]
        self.assertEqual(row["state"], "HOLD")
        self.assertIn("ev-rev:REVERSAL_EXCEEDS_RECEIVED", row["blockers"])

    def test_reconciliation_requires_owner_and_exact_net(self):
        p = packet()
        add_event(p, event_id="ev-cash", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-cash", authority="bank_record", amount=4000)
        add_event(p, event_id="ev-rec", kind="RECONCILED_EVIDENCE", time="2026-09-08T13:00:00Z", evidence_id="e-rec", authority="owner_approved", amount=4000)
        row = crl.compile_ledger(p)["claims"][0]
        self.assertEqual(row["state"], "RECONCILED")
        p2 = copy.deepcopy(p)
        p2["events"][-1]["amount_minor"] = 3999
        row2 = crl.compile_ledger(p2)["claims"][0]
        self.assertEqual(row2["state"], "HOLD")
        self.assertIn("ev-rec:RECONCILE_AMOUNT_MISMATCH", row2["blockers"])

    def test_new_cash_after_reconciliation_makes_old_reconcile_stale(self):
        p = packet()
        add_event(p, event_id="ev-cash1", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-cash1", authority="bank_record", amount=4000)
        add_event(p, event_id="ev-rec", kind="RECONCILED_EVIDENCE", time="2026-09-08T13:00:00Z", evidence_id="e-rec", authority="owner_approved", amount=4000)
        add_event(p, event_id="ev-cash2", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-09T12:00:00Z", evidence_id="e-cash2", authority="bank_record", amount=5000)
        row = crl.compile_ledger(p)["claims"][0]
        self.assertEqual(row["state"], "HOLD")
        self.assertIn("ev-rec:STALE_RECONCILIATION", row["blockers"])

    def test_cumulative_receipt_above_reference_holds(self):
        p = packet()
        add_event(p, event_id="ev-cash1", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-cash1", authority="bank_record", amount=6000)
        add_event(p, event_id="ev-cash2", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-09T12:00:00Z", evidence_id="e-cash2", authority="bank_record", amount=4000)
        row = crl.compile_ledger(p)["claims"][0]
        self.assertEqual(row["state"], "HOLD")
        self.assertIn("ev-cash2:CUMULATIVE_RECEIPT_EXCEEDS_REFERENCE", row["blockers"])

    def test_pending_or_rejected_evidence_cannot_advance(self):
        p = packet()
        add_event(p, event_id="ev-cash", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-cash", authority="bank_record", status="pending")
        row = crl.compile_ledger(p)["claims"][0]
        self.assertEqual(row["state"], "HOLD")
        self.assertIn("ev-cash:EVIDENCE_NOT_VERIFIED", row["blockers"])

    def test_event_claim_digest_transplant_rejected(self):
        p = packet()
        p["events"][0]["claim_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "claim digest mismatch"):
            crl.compile_ledger(p)

    def test_chronology_capture_before_event_holds(self):
        p = packet()
        add_event(p, event_id="ev-cash", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-cash", authority="bank_record")
        p["evidence"][-1]["captured_at"] = "2026-09-08T11:59:59Z"
        row = crl.compile_ledger(p)["claims"][0]
        self.assertEqual(row["state"], "HOLD")
        self.assertIn("ev-cash:CHRONOLOGY_HOLD", row["blockers"])

    def test_bool_and_float_money_rejected(self):
        for bad in (True, 90.0):
            p = packet()
            p["claims"][0]["reference_amount_minor"] = bad
            with self.assertRaisesRegex(ValueError, "integer minor-unit"):
                crl.compile_ledger(p)

    def test_multicurrency_partition_no_cross_total(self):
        p = packet()
        eur_claim = copy.deepcopy(p["claims"][0])
        eur_claim.update({"id": "claim-eur", "currency": "EUR", "reference_amount_minor": 5000, "source_sha256": "a" * 64})
        p["claims"].append(eur_claim)
        add_event(p, event_id="ev-usd-cash", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-usd-cash", authority="bank_record", amount=9000)
        out = crl.compile_ledger(p)
        self.assertEqual(set(out["summary"]["currency_buckets"]), {"EUR", "USD"})
        self.assertTrue(out["summary"]["cross_currency_total_prohibited"])

    def test_semantic_duplicate_event_holds_double_count(self):
        p = packet()
        add_event(p, event_id="ev-cash-a", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-cash", authority="bank_record", amount=4500)
        p["events"].append({**p["events"][-1], "id": "ev-cash-b"})
        row = crl.compile_ledger(p)["claims"][0]
        self.assertEqual(row["state"], "HOLD")
        self.assertIn("ev-cash-b:DUPLICATE_SEMANTIC_EVENT", row["blockers"])

    def test_deterministic_order_and_verifier(self):
        p = packet()
        add_event(p, event_id="ev-cash", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-cash", authority="bank_record")
        first = crl.compile_ledger(p)
        q = copy.deepcopy(p)
        q["events"] = list(reversed(q["events"]))
        q["evidence"] = list(reversed(q["evidence"]))
        second = crl.compile_ledger(q)
        self.assertEqual(first, second)
        ok, _ = crl.verify_ledger(p, first)
        self.assertTrue(ok)
        tampered = copy.deepcopy(first)
        tampered["claims"][0]["state"] = "RECONCILED"
        ok, _ = crl.verify_ledger(p, tampered)
        self.assertFalse(ok)

    def test_cli_strict_duplicate_json_key_and_create_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inp = root / "in.json"
            out = root / "out.json"
            inp.write_text(json.dumps(packet()), encoding="utf-8")
            self.assertEqual(crl.main(["compile", "--input", str(inp), "--json-out", str(out)]), 0)
            with self.assertRaises(FileExistsError):
                crl.main(["compile", "--input", str(inp), "--json-out", str(out)])
            dup = root / "dup.json"
            dup.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                crl._load_json_strict(dup)

    def test_cli_round_trip_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inp, out, md, csvp = root / "in.json", root / "out.json", root / "out.md", root / "out.csv"
            inp.write_text(json.dumps(packet()), encoding="utf-8")
            self.assertEqual(crl.main(["compile", "--input", str(inp), "--json-out", str(out), "--markdown-out", str(md), "--csv-out", str(csvp)]), 0)
            self.assertEqual(crl.main(["verify", "--input", str(inp), "--ledger", str(out)]), 0)
            loaded = json.loads(out.read_text(encoding="utf-8"))
            loaded["claims"][0]["state"] = "RECONCILED"
            out2 = root / "tampered.json"
            out2.write_text(json.dumps(loaded), encoding="utf-8")
            self.assertEqual(crl.main(["verify", "--input", str(inp), "--ledger", str(out2)]), 3)

    def test_fail_on_hold_exit_code_and_csv(self):
        p = packet()
        add_event(p, event_id="ev-cash", kind="PAYMENT_RECEIVED_EVIDENCE", time="2026-09-08T12:00:00Z", evidence_id="e-cash", authority="owner_approved")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inp, out, csvp = root / "in.json", root / "out.json", root / "out.csv"
            inp.write_text(json.dumps(p), encoding="utf-8")
            self.assertEqual(crl.main(["compile", "--input", str(inp), "--json-out", str(out), "--csv-out", str(csvp), "--fail-on-hold"]), 2)
            self.assertIn("claim_id,claim_kind,currency", csvp.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
