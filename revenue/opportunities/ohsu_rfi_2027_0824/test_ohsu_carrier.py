from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ap_acceptance import AcceptanceError, SCHEMA as CASE_SCHEMA, evaluate
from ohsu_ap_rfi import ContractError, canonical_json, strict_load, strict_loads, validate_manifest

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "fixtures" / "manifest.json"
AS_OF = "2026-09-14T04:00:00Z"


def manifest():
    return strict_load(MANIFEST)


def base_case(**updates):
    row = {
        "schema": CASE_SCHEMA,
        "case_id": "case-001",
        "invoice_id": "inv-001",
        "po_required": True,
        "po_present": True,
        "vendor_match": True,
        "invoice_total_cents": 10000,
        "po_total_cents": 10000,
        "tolerance_cents": 50,
        "duplicate": False,
        "approval_required": False,
        "approval_present": False,
        "statement_balance_cents": 10000,
        "ledger_balance_cents": 10000,
    }
    row.update(updates)
    return row


class AcceptanceTests(unittest.TestCase):
    def test_happy_stp(self):
        r = evaluate(base_case())
        self.assertEqual(r["decision"], "ACCEPT_STP")
        self.assertFalse(r["oracle_write_authorized"])
        self.assertFalse(r["payment_authorized"])

    def test_duplicate(self):
        self.assertEqual(evaluate(base_case(duplicate=True))["decision"], "REJECT_DUPLICATE")

    def test_missing_po(self):
        self.assertEqual(evaluate(base_case(po_present=False))["decision"], "HOLD_MISSING_PO")

    def test_vendor_mismatch(self):
        self.assertEqual(evaluate(base_case(vendor_match=False))["decision"], "HOLD_VENDOR_MISMATCH")

    def test_variance_boundary_passes(self):
        self.assertEqual(evaluate(base_case(invoice_total_cents=10050))["decision"], "ACCEPT_STP")

    def test_variance_over_boundary_holds(self):
        self.assertEqual(evaluate(base_case(invoice_total_cents=10051))["decision"], "HOLD_AMOUNT_VARIANCE")

    def test_approval(self):
        self.assertEqual(evaluate(base_case(approval_required=True, approval_present=False))["decision"], "HOLD_APPROVAL")

    def test_reconciliation(self):
        self.assertEqual(evaluate(base_case(statement_balance_cents=9999))["decision"], "HOLD_RECONCILIATION")

    def test_nonpo_ignores_po_variance(self):
        self.assertEqual(evaluate(base_case(po_required=False, po_present=False, invoice_total_cents=20000))["decision"], "ACCEPT_STP")

    def test_bool_int_alias_rejected(self):
        with self.assertRaises(AcceptanceError):
            evaluate(base_case(duplicate=0))

    def test_negative_money_rejected(self):
        with self.assertRaises(AcceptanceError):
            evaluate(base_case(tolerance_cents=-1))

    def test_unknown_key_rejected(self):
        c = base_case(); c["x"] = 1
        with self.assertRaises(AcceptanceError): evaluate(c)

    def test_deterministic(self):
        self.assertEqual(evaluate(base_case()), evaluate(dict(reversed(list(base_case().items())))))


class ManifestTests(unittest.TestCase):
    def test_fixture_holds_direct_but_teaming_ready(self):
        p = validate_manifest(manifest(), AS_OF, local_root=ROOT)
        self.assertEqual(p["direct_response"]["state"], "HOLD")
        self.assertEqual(p["teaming"]["state"], "READY")
        self.assertIn("oracle_transaction_processing:PARTNER_REQUIRED", p["direct_response"]["blockers"])
        self.assertFalse(p["authority"]["partner_contact_authorized"])

    def test_evidenced_requires_verified_evidence(self):
        m = manifest()
        for evidence in m["evidence"]:
            if evidence["id"] == "local_acceptance_harness":
                evidence["state"] = "UNVERIFIED"
        m["claims"][0]["status"] = "EVIDENCED"
        with self.assertRaises(ContractError): validate_manifest(m, AS_OF, local_root=ROOT)

    def test_cannot_claim_partner_credentials(self):
        m = manifest()
        for row in m["claims"]:
            if row["capability"] == "oracle_transaction_processing":
                row["status"] = "EVIDENCED"; row["evidence_refs"] = []
        with self.assertRaises(ContractError): validate_manifest(m, AS_OF, local_root=ROOT)

    def test_future_source_rejected(self):
        m = manifest(); m["source"]["captured_at_utc"] = "2026-09-15T00:00:00Z"
        with self.assertRaises(ContractError): validate_manifest(m, AS_OF, local_root=ROOT)

    def test_deadline_drift_rejected(self):
        m = manifest(); m["solicitation"]["response_due_utc"] = "2026-09-25T00:00:00Z"
        with self.assertRaises(ContractError): validate_manifest(m, AS_OF, local_root=ROOT)

    def test_title_drift_rejected(self):
        m = manifest(); m["solicitation"]["title"] = "AI AP Automation"
        m["source"]["facts"]["title"] = "AI AP Automation"
        with self.assertRaises(ContractError): validate_manifest(m, AS_OF, local_root=ROOT)

    def test_intent_drift_rejected(self):
        m = manifest(); m["solicitation"]["intent_required"] = True
        with self.assertRaises(ContractError): validate_manifest(m, AS_OF, local_root=ROOT)

    def test_offer_cannot_authorize_send(self):
        m = manifest(); m["commercial_offer"]["external_send_authorized"] = True
        with self.assertRaises(ContractError): validate_manifest(m, AS_OF, local_root=ROOT)

    def test_offer_state_fixed(self):
        m = manifest(); m["commercial_offer"]["state"] = "ACCEPTED"
        with self.assertRaises(ContractError): validate_manifest(m, AS_OF, local_root=ROOT)

    def test_expired_response_holds_teaming(self):
        p = validate_manifest(manifest(), "2026-09-24T00:00:00Z", local_root=ROOT)
        self.assertEqual(p["teaming"]["state"], "HOLD")
        self.assertIn("response_window:EXPIRED", p["direct_response"]["blockers"])

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ContractError): strict_loads('{"a":1,"a":2}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ContractError): strict_loads('{"a":NaN}')

    def test_unknown_claim_rejected(self):
        m = manifest(); m["claims"][0]["capability"] = "magic"
        with self.assertRaises(ContractError): validate_manifest(m, AS_OF, local_root=ROOT)

    def test_missing_claim_rejected(self):
        m = manifest(); m["claims"].pop()
        with self.assertRaises(ContractError): validate_manifest(m, AS_OF, local_root=ROOT)

    def test_secret_shaped_statement_rejected(self):
        m = manifest(); m["claims"][0]["statement"] = "password: hunter2"
        with self.assertRaises(ContractError): validate_manifest(m, AS_OF, local_root=ROOT)

    def test_deterministic_packet(self):
        a = validate_manifest(manifest(), AS_OF, local_root=ROOT)
        b = validate_manifest(manifest(), AS_OF, local_root=ROOT)
        self.assertEqual(canonical_json(a), canonical_json(b))

    def test_cli_create_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            j = Path(td)/"out.json"; md = Path(td)/"out.md"
            cmd = [sys.executable, str(ROOT/"build_packet.py"), str(MANIFEST), "--as-of", AS_OF, "--json-out", str(j), "--md-out", str(md)]
            subprocess.run(cmd, check=True, cwd=ROOT, capture_output=True, text=True)
            self.assertTrue(j.exists() and md.exists())
            again = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)

    def test_cli_symlink_refusal(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); target = td/"target"; target.write_text("x")
            j = td/"out.json"; j.symlink_to(target); md = td/"out.md"
            cmd = [sys.executable, str(ROOT/"build_packet.py"), str(MANIFEST), "--as-of", AS_OF, "--json-out", str(j), "--md-out", str(md)]
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(target.read_text(), "x")


# Matrix-level contract checks are intentionally separate from individual rule tests.
from run_acceptance_matrix import evaluate_matrix


class AcceptanceMatrixTests(unittest.TestCase):
    def matrix(self):
        return strict_load(ROOT / "fixtures" / "ap_cases.json")

    def test_shipped_matrix_has_at_least_twenty_and_all_dispositions(self):
        result = evaluate_matrix(self.matrix())
        self.assertGreaterEqual(result["case_count"], 20)
        self.assertTrue(all(n > 0 for n in result["decision_counts"].values()))
        self.assertFalse(result["oracle_write_authorized"])
        self.assertFalse(result["payment_authorized"])

    def test_shipped_matrix_is_deterministic(self):
        self.assertEqual(evaluate_matrix(self.matrix()), evaluate_matrix(self.matrix()))

    def test_matrix_expected_decision_mismatch_fails_closed(self):
        doc = self.matrix()
        doc["cases"][0]["expected_decision"] = "HOLD_APPROVAL"
        with self.assertRaises(ContractError):
            evaluate_matrix(doc)

    def test_matrix_duplicate_case_id_fails_closed(self):
        doc = self.matrix()
        doc["cases"][1]["case"]["case_id"] = doc["cases"][0]["case"]["case_id"]
        with self.assertRaises(ContractError):
            evaluate_matrix(doc)

    def test_matrix_requires_full_terminal_coverage(self):
        doc = self.matrix()
        # Keep >=20 rows while eliminating one disposition entirely.
        doc["cases"] = [r for r in doc["cases"] if r["expected_decision"] != "HOLD_RECONCILIATION"]
        while len(doc["cases"]) < 20:
            doc["cases"].append(copy.deepcopy(doc["cases"][0]))
            n = len(doc["cases"])
            doc["cases"][-1]["case"]["case_id"] = f"padding-{n}"
            doc["cases"][-1]["case"]["invoice_id"] = f"padding-inv-{n}"
        with self.assertRaises(ContractError):
            evaluate_matrix(doc)


class EvidenceBindingTests(unittest.TestCase):
    def test_source_fact_digest_tamper_rejected(self):
        m = manifest()
        m["source"]["facts"]["erp_context"] = "Oracle EBS R12 maybe"
        with self.assertRaises(ContractError):
            validate_manifest(m, AS_OF, local_root=ROOT)

    def test_source_evidence_digest_must_match_fact_digest(self):
        m = manifest()
        for evidence in m["evidence"]:
            if evidence["kind"] == "OFFICIAL_SOURCE":
                evidence["digest"] = "f" * 64
        with self.assertRaises(ContractError):
            validate_manifest(m, AS_OF, local_root=ROOT)

    def test_local_verified_evidence_requires_exact_carrier_digest(self):
        m = manifest()
        for evidence in m["evidence"]:
            if evidence["id"] == "local_acceptance_harness":
                evidence["digest"] = "e" * 64
        with self.assertRaises(ContractError):
            validate_manifest(m, AS_OF, local_root=ROOT)

    def test_local_verified_evidence_requires_root(self):
        with self.assertRaises(ContractError):
            validate_manifest(manifest(), AS_OF)


if __name__ == "__main__":
    unittest.main()
