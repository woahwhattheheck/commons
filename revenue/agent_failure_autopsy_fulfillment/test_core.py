from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from revenue.agent_failure_autopsy_fulfillment.core import (  # noqa: E402
    FulfillmentError,
    compile_batch,
    strict_json_loads,
    verify_packet,
)

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64


def case(ref="CASE-001", payment="VERIFIED_PAID"):
    return {
        "case_ref": ref,
        "payment": {"state": payment, "receipt_sha256": D1 if payment != "UNVERIFIED" else None},
        "intake": {
            "intended_outcome": "Update owned files and publish one pull request.",
            "observed_failure": "The publish step retried and duplicated a side effect.",
            "stack": "GitHub Actions and local agent harness",
            "first_error": "A retry resumed from stale state after the first publish attempt.",
            "evidence_items": [{"kind": "redacted_log", "sha256": D2, "bytes": 1200}],
            "redaction_confirmed": True,
        },
        "operator": {"delivery_receipt_sha256": None, "refund_receipt_sha256": None, "refund_reason": ""},
    }


def batch(*cases):
    return {"schema": "agent-autopsy-fulfillment-batch/v1", "cases": list(cases)}


class CoreTests(unittest.TestCase):
    def test_ready(self):
        packet = compile_batch(batch(case()))
        self.assertEqual(packet["cases"][0]["state"], "READY_FOR_ANALYSIS")
        self.assertTrue(verify_packet(packet))

    def test_unverified_payment_holds(self):
        packet = compile_batch(batch(case(payment="UNVERIFIED")))
        self.assertEqual(packet["cases"][0]["state"], "HOLD_PAYMENT_UNVERIFIED")

    def test_unverified_cannot_carry_receipt(self):
        c = case(payment="UNVERIFIED")
        c["payment"]["receipt_sha256"] = D1
        with self.assertRaises(FulfillmentError): compile_batch(batch(c))

    def test_verified_requires_receipt(self):
        c = case()
        c["payment"]["receipt_sha256"] = None
        with self.assertRaises(FulfillmentError): compile_batch(batch(c))

    def test_incomplete_intake_holds(self):
        c = case()
        c["intake"]["first_error"] = ""
        packet = compile_batch(batch(c))
        self.assertEqual(packet["cases"][0]["state"], "HOLD_INTAKE_INCOMPLETE")

    def test_evidence_required(self):
        c = case()
        c["intake"]["evidence_items"] = []
        self.assertEqual(compile_batch(batch(c))["cases"][0]["state"], "HOLD_INTAKE_INCOMPLETE")

    def test_delivery_requires_verified_complete_case(self):
        c = case()
        c["operator"]["delivery_receipt_sha256"] = D3
        self.assertEqual(compile_batch(batch(c))["cases"][0]["state"], "DELIVERED")
        c2 = case(payment="UNVERIFIED")
        c2["operator"]["delivery_receipt_sha256"] = D3
        self.assertEqual(compile_batch(batch(c2))["cases"][0]["state"], "HOLD_PAYMENT_UNVERIFIED")

    def test_refund_required_and_satisfied(self):
        c = case()
        c["operator"]["refund_reason"] = "Evidence cannot support a defensible diagnosis after clarification."
        p = compile_batch(batch(c))
        self.assertEqual(p["cases"][0]["state"], "REFUND_REQUIRED")
        self.assertFalse(p["cases"][0]["refund_satisfied"])
        c["operator"]["refund_receipt_sha256"] = D3
        self.assertTrue(compile_batch(batch(c))["cases"][0]["refund_satisfied"])

    def test_refunded_payment_is_refund_state(self):
        c = case(payment="REFUNDED")
        p = compile_batch(batch(c))
        self.assertEqual(p["cases"][0]["state"], "REFUND_REQUIRED")
        self.assertTrue(p["cases"][0]["refund_satisfied"])

    def test_delivery_and_refund_conflict(self):
        c = case()
        c["operator"]["delivery_receipt_sha256"] = D3
        c["operator"]["refund_reason"] = "refund"
        with self.assertRaises(FulfillmentError): compile_batch(batch(c))

    def test_secret_and_pii_text_refused(self):
        for bad in ("send to jane@example.com", "https://private.invalid/x", "password abc", "555-123-4567", "ghp_abcdefghijklmnopqrstuvwxyz"):
            c = case()
            c["intake"]["first_error"] = bad
            with self.subTest(bad=bad):
                with self.assertRaises(FulfillmentError): compile_batch(batch(c))

    def test_bool_is_not_byte_count(self):
        c = case()
        c["intake"]["evidence_items"][0]["bytes"] = True
        with self.assertRaises(FulfillmentError): compile_batch(batch(c))

    def test_duplicate_evidence_digest_refused(self):
        c = case()
        c["intake"]["evidence_items"].append({"kind": "screenshot", "sha256": D2, "bytes": 1})
        with self.assertRaises(FulfillmentError): compile_batch(batch(c))

    def test_duplicate_case_ref_refused(self):
        with self.assertRaises(FulfillmentError): compile_batch(batch(case(), case()))

    def test_unknown_keys_refused(self):
        c = case(); c["payment"]["buyer_says_paid"] = True
        with self.assertRaises(FulfillmentError): compile_batch(batch(c))

    def test_duplicate_json_key_refused(self):
        with self.assertRaises(FulfillmentError): strict_json_loads('{"schema":"a","schema":"b"}')

    def test_nonfinite_json_refused(self):
        with self.assertRaises(FulfillmentError): strict_json_loads('{"x":NaN}')

    def test_packet_tamper_refused(self):
        p = compile_batch(batch(case()))
        p["cases"][0]["state"] = "DELIVERED"
        self.assertFalse(verify_packet(p))

    def test_receipt_recompute_does_not_authorize_tamper(self):
        p = compile_batch(batch(case()))
        p["authority"]["cash_received_claim"] = True
        semantic = {k: v for k, v in p.items() if k != "receipt_sha256"}
        from revenue.agent_failure_autopsy_fulfillment.core import sha256_value
        p["receipt_sha256"] = sha256_value(semantic)
        self.assertFalse(verify_packet(p))

    def test_queue_is_deterministic_and_priority_sorted(self):
        a = case("CASE-A", payment="UNVERIFIED")
        b = case("CASE-B")
        c = case("CASE-C"); c["operator"]["refund_reason"] = "refund required"
        first = compile_batch(batch(a, b, c))
        second = compile_batch(batch(c, a, b))
        self.assertEqual(first["receipt_sha256"], second["receipt_sha256"])
        self.assertEqual([r["case_ref"] for r in first["queue"]], ["CASE-C", "CASE-B", "CASE-A"])

    def test_case_reference_is_opaque(self):
        for bad in ("person@example.com", "https://x", "payment-token-1", ""):
            c = case(); c["case_ref"] = bad
            with self.subTest(bad=bad):
                with self.assertRaises(FulfillmentError): compile_batch(batch(c))

    def test_public_sample_binds_canonical_offer_without_reminting_checkout(self):
        page = (ROOT / "agent-autopsy-sample.html").read_text(encoding="utf-8")
        self.assertIn('href="./agent-rescue.html"', page)
        self.assertIn("SYNTHETIC / UNPAID SAMPLE", page)
        self.assertNotIn("buy.stripe.com", page)

    def test_cli_compile_verify_and_create_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "input.json"
            src.write_text(json.dumps(batch(case())), encoding="utf-8")
            out = td / "out"
            cmd = [sys.executable, str(HERE / "core.py"), "compile", str(src), str(out)]
            run = subprocess.run(cmd, text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue((out / "packet.json").is_file())
            self.assertTrue((out / "report.md").is_file())
            verify = subprocess.run([sys.executable, str(HERE / "core.py"), "verify", str(out / "packet.json")], text=True, capture_output=True)
            self.assertEqual(verify.returncode, 0, verify.stderr)
            self.assertEqual(verify.stdout.strip(), "VERIFIED")
            again = subprocess.run(cmd, text=True, capture_output=True)
            self.assertEqual(again.returncode, 2)
            self.assertIn("already exists", again.stderr)


if __name__ == "__main__":
    unittest.main()
