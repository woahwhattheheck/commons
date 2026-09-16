from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

from revenue.ohsu_ap_ai_rfi_approof.approof import (
    APProofError,
    AUTHORITY,
    canonical_json_bytes,
    compile_packet,
    verify_projection,
)

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "revenue" / "ohsu_ap_ai_rfi_approof" / "fixture.json"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class APProofTests(unittest.TestCase):
    def test_clean_packet_shadow_ready_hard_false_authority(self):
        out = compile_packet(load_fixture())
        self.assertEqual(out["metrics"]["invoice_count"], 1)
        self.assertEqual(out["metrics"]["shadow_ready_count"], 1)
        self.assertEqual(out["invoice_results"][0]["state"], "READY_FOR_SHADOW_EXPORT")
        self.assertEqual(out["oracle_shadow_rows"][0]["mode"], "SHADOW_ONLY")
        self.assertIsNone(out["oracle_shadow_rows"][0]["oracle_ebs_transaction_id"])
        self.assertIs(out["oracle_shadow_rows"][0]["posting_authorized"], False)
        self.assertEqual(out["authority"], AUTHORITY)
        self.assertTrue(all(value is False for value in out["authority"].values()))

    def test_price_mismatch_holds(self):
        packet = load_fixture()
        packet["purchase_orders"][0]["lines"][0]["unit_price_cents"] = 9000
        out = compile_packet(packet)
        codes = {f["code"] for f in out["invoice_results"][0]["findings"]}
        self.assertIn("PRICE_MISMATCH", codes)
        self.assertEqual(out["invoice_results"][0]["state"], "HOLD_OWNER_REVIEW")

    def test_receipt_quantity_short_holds(self):
        packet = load_fixture()
        packet["receipts"][0]["quantity"] = 1
        out = compile_packet(packet)
        codes = {f["code"] for f in out["invoice_results"][0]["findings"]}
        self.assertIn("RECEIPT_QUANTITY_SHORT", codes)

    def test_non_po_requires_coding_review(self):
        packet = load_fixture()
        packet["invoices"][0]["po_id"] = None
        out = compile_packet(packet)
        codes = {f["code"] for f in out["invoice_results"][0]["findings"]}
        self.assertIn("NON_PO_CODING_REVIEW", codes)

    def test_missing_approval_holds(self):
        packet = load_fixture()
        packet["approvals"] = []
        out = compile_packet(packet)
        self.assertEqual(out["invoice_results"][0]["approval_state"], "MISSING")
        self.assertIn(
            "APPROVAL_MISSING",
            {f["code"] for f in out["invoice_results"][0]["findings"]},
        )

    def test_rejected_approval_holds(self):
        packet = load_fixture()
        packet["approvals"][0]["status"] = "REJECTED"
        out = compile_packet(packet)
        self.assertEqual(out["invoice_results"][0]["approval_state"], "REJECTED")
        self.assertIn(
            "APPROVAL_REJECTED",
            {f["code"] for f in out["invoice_results"][0]["findings"]},
        )

    def test_duplicate_economic_invoice_holds_both(self):
        packet = load_fixture()
        twin = copy.deepcopy(packet["invoices"][0])
        twin["invoice_id"] = "INV-B"
        packet["invoices"].append(twin)
        packet["approvals"].append({
            "approval_id":"A2","invoice_id":"INV-B","status":"APPROVED","source_sha256":"1"*64
        })
        out = compile_packet(packet)
        self.assertEqual(len(out["invoice_results"]), 2)
        for row in out["invoice_results"]:
            self.assertIn(
                "DUPLICATE_ECONOMIC_INVOICE_HOLD",
                {f["code"] for f in row["findings"]},
            )

    def test_statement_missing_invoice_holds(self):
        packet = load_fixture()
        packet["supplier_statements"][0]["invoice_numbers"] = []
        packet["supplier_statements"][0]["statement_total_cents"] = 0
        out = compile_packet(packet)
        self.assertIn(
            "INVOICE_NOT_ON_STATEMENT",
            {f["code"] for f in out["invoice_results"][0]["findings"]},
        )

    def test_statement_unknown_invoice_is_separate_exception(self):
        packet = load_fixture()
        packet["supplier_statements"][0]["invoice_numbers"].append("GHOST-9")
        out = compile_packet(packet)
        self.assertEqual(out["statement_exceptions"][0]["code"], "STATEMENT_INVOICE_NOT_IN_PACKET")
        self.assertEqual(out["statement_exceptions"][0]["invoice_number"], "GHOST-9")

    def test_invoice_line_total_must_equal_total(self):
        packet = load_fixture()
        packet["invoices"][0]["total_cents"] += 1
        with self.assertRaises(APProofError):
            compile_packet(packet)

    def test_bool_is_not_integer(self):
        packet = load_fixture()
        packet["invoices"][0]["total_cents"] = True
        with self.assertRaises(APProofError):
            compile_packet(packet)

    def test_unknown_keys_fail_closed(self):
        packet = load_fixture()
        packet["write_to_oracle"] = True
        with self.assertRaises(APProofError):
            compile_packet(packet)

    def test_source_sha_required(self):
        packet = load_fixture()
        packet["invoices"][0]["source_sha256"] = "not-a-sha"
        with self.assertRaises(APProofError):
            compile_packet(packet)

    def test_deterministic_under_collection_permutation(self):
        packet = load_fixture()
        # split receipt order is semantically unordered
        a = compile_packet(packet)
        packet["receipts"].reverse()
        packet["purchase_orders"].reverse()
        packet["approvals"].reverse()
        packet["supplier_statements"].reverse()
        b = compile_packet(packet)
        self.assertEqual(canonical_json_bytes(a), canonical_json_bytes(b))

    def test_projection_tamper_is_rejected(self):
        packet = load_fixture()
        out = compile_packet(packet)
        self.assertTrue(verify_projection(packet, out))
        bad = copy.deepcopy(out)
        bad["authority"]["payment_authorized"] = True
        self.assertFalse(verify_projection(packet, bad))

    def test_packet_tamper_is_rejected(self):
        packet = load_fixture()
        out = compile_packet(packet)
        changed = copy.deepcopy(packet)
        changed["invoices"][0]["invoice_date"] = "2026-09-14"
        self.assertFalse(verify_projection(changed, out))

    def test_audit_chain_is_linked(self):
        out = compile_packet(load_fixture())
        prev = "0" * 64
        for idx, row in enumerate(out["audit_chain"]):
            self.assertEqual(row["index"], idx)
            self.assertEqual(row["previous_chain_sha256"], prev)
            self.assertEqual(len(row["chain_sha256"]), 64)
            prev = row["chain_sha256"]

    def test_cli_compile_verify_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            projection = Path(td) / "projection.json"
            cmd = [
                sys.executable, "-m", "revenue.ohsu_ap_ai_rfi_approof.cli",
                "compile", str(FIXTURE),
            ]
            cp = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True)
            self.assertEqual(cp.returncode, 0, cp.stderr.decode())
            projection.write_bytes(cp.stdout)
            vp = subprocess.run(
                [
                    sys.executable, "-m", "revenue.ohsu_ap_ai_rfi_approof.cli",
                    "verify", str(FIXTURE), str(projection),
                ],
                cwd=ROOT, check=False, capture_output=True,
            )
            self.assertEqual(vp.returncode, 0, vp.stderr.decode())
            self.assertEqual(vp.stdout, b"OK\n")

    def test_cli_invalid_returns_two(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text("{}", encoding="utf-8")
            cp = subprocess.run(
                [
                    sys.executable, "-m", "revenue.ohsu_ap_ai_rfi_approof.cli",
                    "compile", str(bad),
                ],
                cwd=ROOT, check=False, capture_output=True,
            )
            self.assertEqual(cp.returncode, 2)
            self.assertIn(b"APProofError", cp.stderr)

    def test_1000_randomized_safety_packets_never_authorize_effects(self):
        rng = random.Random(20260916)
        base = load_fixture()
        for i in range(1000):
            packet = copy.deepcopy(base)
            invoice = packet["invoices"][0]
            po = packet["purchase_orders"][0]
            qty = rng.randint(1, 8)
            unit = rng.randint(1, 100000)
            invoice["lines"] = [{
                "line_id":"L1", "sku":"SKU-1", "quantity":qty,
                "unit_price_cents":unit, "cost_center":"CC-100",
            }]
            invoice["total_cents"] = qty * unit
            po_qty = rng.randint(1, 8)
            po_unit = rng.randint(1, 100000)
            po["lines"] = [{
                "line_id":"L1", "sku":"SKU-1", "quantity":po_qty,
                "unit_price_cents":po_unit, "cost_center":"CC-100",
            }]
            packet["receipts"] = [{
                "receipt_id":"R1", "po_id":"PO-1", "line_id":"L1",
                "quantity":rng.randint(1, 8), "source_sha256":"c"*64,
            }]
            packet["supplier_statements"][0]["statement_total_cents"] = invoice["total_cents"]
            packet["approvals"][0]["status"] = rng.choice(["APPROVED","PENDING","REJECTED"])
            out = compile_packet(packet)
            self.assertTrue(all(value is False for value in out["authority"].values()))
            for row in out["oracle_shadow_rows"]:
                self.assertIs(row["posting_authorized"], False)
                self.assertEqual(row["mode"], "SHADOW_ONLY")
                self.assertIsNone(row["oracle_ebs_transaction_id"])


if __name__ == "__main__":
    unittest.main()
