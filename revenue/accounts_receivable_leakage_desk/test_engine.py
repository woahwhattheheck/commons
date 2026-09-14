from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from . import cli
from .engine import InputError, PILOT_MAX_INVOICES, PILOT_PRICE_USD_MINOR, canonical_bytes, compile_report, loads_strict, render_markdown, verify_report

HERE = Path(__file__).resolve().parent


def packet():
    return loads_strict((HERE / "example.json").read_text(encoding="utf-8"))


def sha(ch: str) -> str:
    return ch * 64


class ARLeakageTests(unittest.TestCase):
    def test_synthetic_acceptance_states_and_totals(self):
        report=compile_report(packet()); states={row["invoice_id"]:row["status"] for row in report["invoices"]}
        self.assertEqual(states,{"inv-conflict":"CONFLICT","inv-disputed":"DISPUTED_HOLD","inv-open":"OPEN","inv-overdue":"PARTIAL_OVERDUE","inv-paid":"PAID","inv-partial":"PARTIAL","inv-partial-overdue":"PARTIAL_OVERDUE","inv-void":"VOID"})
        s=report["summary"]
        self.assertEqual(s["known_outstanding_minor"],10000+15000+25000+30000+50000)
        self.assertEqual(s["recovery_candidate_minor"],25000+30000)
        self.assertEqual(s["disputed_outstanding_minor"],50000)
        self.assertEqual(s["unapplied_payment_minor"],12500)
        self.assertEqual(s["conflict_count"],1)

    def test_order_invariant(self):
        p=packet(); expected=canonical_bytes(compile_report(p))
        for key in ("invoices","payments","credits","disputes"): p[key].reverse()
        self.assertEqual(canonical_bytes(compile_report(p)),expected)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(InputError): loads_strict('{"schema":"x","schema":"y"}')

    def test_nonfinite_rejected(self):
        with self.assertRaises(InputError): loads_strict('{"x":NaN}')

    def test_bool_never_amount(self):
        p=packet(); p["invoices"][0]["amount_minor"]=True
        with self.assertRaises(InputError): compile_report(p)

    def test_unknown_root_field_rejected(self):
        p=packet(); p["owner_says_ready"]=True
        with self.assertRaises(InputError): compile_report(p)

    def test_email_like_account_id_rejected(self):
        p=packet(); p["invoices"][0]["account_id"]="person@example.com"
        with self.assertRaises(InputError): compile_report(p)

    def test_evidence_replay_rejected(self):
        p=packet(); p["payments"][1]["evidence_sha256"]=p["payments"][0]["evidence_sha256"]
        with self.assertRaises(InputError): compile_report(p)

    def test_cross_account_payment_conflicts_invoice(self):
        p=packet(); p["payments"][0]["account_id"]="acct-other"; r=compile_report(p)
        row=next(x for x in r["invoices"] if x["invoice_id"]=="inv-partial")
        self.assertEqual(row["status"],"CONFLICT"); self.assertIn("PAYMENT_ACCOUNT_MISMATCH",{x["code"] for x in r["integrity_conflicts"]})

    def test_cross_currency_payment_conflicts_invoice(self):
        p=packet(); p["payments"][0]["currency"]="EUR"; r=compile_report(p)
        self.assertEqual(next(x for x in r["invoices"] if x["invoice_id"]=="inv-partial")["status"],"CONFLICT")

    def test_unknown_invoice_payment_is_conflict_not_allocation(self):
        p=packet(); p["payments"][0]["invoice_id"]="inv-missing"; r=compile_report(p)
        self.assertIn("PAYMENT_UNKNOWN_INVOICE",{x["code"] for x in r["integrity_conflicts"]})
        self.assertEqual(next(x for x in r["invoices"] if x["invoice_id"]=="inv-partial")["applied_payment_minor"],0)

    def test_future_payment_conflicts_target(self):
        p=packet(); p["payments"][0]["observed_at"]="2026-09-15T00:00:00Z"; r=compile_report(p)
        self.assertEqual(next(x for x in r["invoices"] if x["invoice_id"]=="inv-partial")["status"],"CONFLICT")

    def test_overapplication_conflict(self):
        r=compile_report(packet()); row=next(x for x in r["invoices"] if x["invoice_id"]=="inv-conflict")
        self.assertEqual(row["status"],"CONFLICT"); self.assertEqual(row["balance_minor"],0)

    def test_void_invoice_allocation_conflict(self):
        p=packet(); p["payments"].append({"payment_id":"pay-void","account_id":"acct-g","invoice_id":"inv-void","amount_minor":1,"currency":"USD","observed_at":"2026-09-10T00:00:00Z","evidence_sha256":sha("0")})
        r=compile_report(p); self.assertEqual(next(x for x in r["invoices"] if x["invoice_id"]=="inv-void")["status"],"CONFLICT")

    def test_unapplied_not_guessed(self):
        r=compile_report(packet()); self.assertEqual(r["unapplied_payments"][0]["payment_id"],"pay-unapplied"); self.assertEqual(r["unapplied_payments"][0]["review"],"RECONCILE_UNAPPLIED_PAYMENT")

    def test_open_dispute_holds_recovery(self):
        r=compile_report(packet()); row=next(x for x in r["invoices"] if x["invoice_id"]=="inv-disputed")
        self.assertEqual(row["status"],"DISPUTED_HOLD"); self.assertNotEqual(row["balance_minor"],0)

    def test_resolved_dispute_releases_hold(self):
        p=packet(); p["disputes"].append({"event_id":"disp-resolved","dispute_id":"case-1","account_id":"acct-e","invoice_id":"inv-disputed","state":"RESOLVED","observed_at":"2026-09-03T12:00:00Z","evidence_sha256":sha("0")})
        r=compile_report(p); self.assertEqual(next(x for x in r["invoices"] if x["invoice_id"]=="inv-disputed")["status"],"OVERDUE")

    def test_same_time_dispute_fork_conflicts(self):
        p=packet(); p["disputes"].append({"event_id":"disp-fork","dispute_id":"case-1","account_id":"acct-e","invoice_id":"inv-disputed","state":"RESOLVED","observed_at":"2026-09-02T12:00:00Z","evidence_sha256":sha("0")})
        r=compile_report(p); self.assertEqual(next(x for x in r["invoices"] if x["invoice_id"]=="inv-disputed")["status"],"CONFLICT")

    def test_grace_boundary(self):
        p=packet(); p["analysis_date"]="2026-09-02"; p["grace_days"]=2; r=compile_report(p)
        self.assertEqual(next(x for x in r["invoices"] if x["invoice_id"]=="inv-overdue")["status"],"PARTIAL")

    def test_exact_grace_plus_one_is_overdue(self):
        p=packet(); p["analysis_date"]="2026-09-03"; p["grace_days"]=2; r=compile_report(p)
        self.assertEqual(next(x for x in r["invoices"] if x["invoice_id"]=="inv-overdue")["status"],"PARTIAL_OVERDUE")

    def test_paid_invoice(self):
        r=compile_report(packet()); row=next(x for x in r["invoices"] if x["invoice_id"]=="inv-paid")
        self.assertEqual(row["status"],"PAID"); self.assertEqual(row["balance_minor"],0)

    def test_report_tamper_fails_verify(self):
        p=packet(); r=compile_report(p); r["summary"]["recovery_candidate_minor"]+=1; self.assertFalse(verify_report(p,r))

    def test_source_change_fails_verify(self):
        p=packet(); r=compile_report(p); p["analysis_date"]="2026-09-13"; self.assertFalse(verify_report(p,r))

    def test_exact_report_verifies(self):
        p=packet(); r=compile_report(p); self.assertTrue(verify_report(p,r))

    def test_authority_always_false(self):
        r=compile_report(packet()); self.assertTrue(r["authority"]); self.assertTrue(all(value is False for value in r["authority"].values()))

    def test_commercial_reference_is_not_acceptance(self):
        r=compile_report(packet()); self.assertEqual(r["commercial_reference"]["pilot_price_usd_minor"],PILOT_PRICE_USD_MINOR); self.assertEqual(r["commercial_reference"]["pilot_max_invoices"],PILOT_MAX_INVOICES); self.assertEqual(r["commercial_reference"]["state"],"REFERENCE_NOT_ACCEPTED")

    def test_markdown_preserves_truth_boundary(self):
        text=render_markdown(compile_report(packet())); self.assertIn("not legal debt",text); self.assertIn("$2,500 fixed diagnostic",text); self.assertNotIn("customer_contact_authorized: true",text.lower())

    def test_too_many_invoices_rejected(self):
        p=packet(); base=p["invoices"][0]; p["invoices"]=[]
        for i in range(PILOT_MAX_INVOICES+1):
            row=dict(base); row["invoice_id"]=f"i{i}"; row["evidence_sha256"]=f"{i:064x}"; p["invoices"].append(row)
        with self.assertRaises(InputError): compile_report(p)

    def test_cli_compile_verify_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/"in.json"; out=root/"report.json"; md=root/"report.md"; inp.write_bytes((HERE/"example.json").read_bytes())
            self.assertEqual(cli.main(["compile","--input",str(inp),"--report",str(out),"--markdown",str(md)]),0)
            self.assertEqual(cli.main(["verify","--input",str(inp),"--report",str(out)]),0)
            self.assertEqual(cli.main(["compile","--input",str(inp),"--report",str(out),"--markdown",str(md)]),2)

    def test_cli_input_symlink_refused_where_supported(self):
        import os
        if not hasattr(os,"O_NOFOLLOW"): self.skipTest("O_NOFOLLOW unavailable")
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); real=root/"real.json"; link=root/"link.json"; real.write_bytes((HERE/"example.json").read_bytes()); link.symlink_to(real)
            self.assertEqual(cli.main(["compile","--input",str(link),"--report",str(root/"r.json"),"--markdown",str(root/"r.md")]),2)

    def test_receipt_is_64_lower_hex(self):
        self.assertRegex(compile_report(packet())["receipt_sha256"],r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
