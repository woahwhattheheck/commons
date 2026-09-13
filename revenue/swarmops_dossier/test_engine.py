from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from revenue.swarmops_dossier.acceptance import fixture
from revenue.swarmops_dossier.cli import main as cli_main
from revenue.swarmops_dossier.engine import DossierError, compile_dossier, render_markdown, strict_json_loads, verify_dossier

AS_OF = "2026-09-13T14:00:00Z"


def h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.policy = fixture()

    def compile(self):
        return compile_dossier(self.packet, self.policy, AS_OF)

    def test_mixed_acceptance_truth(self):
        out = self.compile()
        self.assertEqual(out["status"], "READY_FOR_OWNER_REVIEW")
        self.assertEqual(out["summary"]["DEMONSTRATED"], 2)
        self.assertEqual(out["summary"]["LIMITED"], 2)
        self.assertEqual(out["external_truth"], {"buyer_accepted":False,"paid":False,"revenue_recognized":False})
        self.assertEqual({r["capability_id"] for r in out["what_we_can_show_now"]}, {"guarded-shipping","deterministic-verification"})

    def test_queued_ci_never_demonstrated(self):
        out = self.compile()
        ci = next(r for r in out["evidence"] if r["capability_id"] == "hosted-ci")
        self.assertEqual(ci["classification"], "LIMITED")

    def test_sent_never_accepted(self):
        out = self.compile()
        self.assertFalse(out["external_truth"]["buyer_accepted"])

    def test_checkout_or_provider_cannot_claim_paid(self):
        row = self.packet["evidence"][3]
        row["observed_state"] = "PAID"
        with self.assertRaises(DossierError):
            self.compile()

    def test_paid_requires_payment_receipt_and_is_explicit(self):
        self.packet["evidence"].append({"capability_id":"commercial-payment","source_id":"payment-1","source_kind":"PAYMENT_RECEIPT","source_ref":"processor:receipt1","source_sha256":h("pay"),"observed_state":"PAID","observed_at":"2026-09-13T13:05:00Z","freshness_seconds":86400,"prospect_class":"PROSPECT_SAFE","required":False,"claim":"A payment receipt was independently retained for one commercial event."})
        out = self.compile()
        self.assertTrue(out["external_truth"]["paid"])
        self.assertFalse(out["external_truth"]["buyer_accepted"])
        self.assertFalse(out["external_truth"]["revenue_recognized"])

    def test_buyer_acceptance_requires_buyer_receipt(self):
        self.packet["evidence"].append({"capability_id":"acceptance","source_id":"a1","source_kind":"PROVIDER_RECEIPT","source_ref":"provider:a1","source_sha256":h("a"),"observed_state":"BUYER_ACCEPTED","observed_at":"2026-09-13T13:05:00Z","freshness_seconds":86400,"prospect_class":"PUBLIC","required":False,"claim":"Buyer accepted."})
        with self.assertRaises(DossierError): self.compile()

    def test_revenue_recognition_requires_accounting_receipt(self):
        self.packet["evidence"].append({"capability_id":"revenue","source_id":"r1","source_kind":"PAYMENT_RECEIPT","source_ref":"payment:r1","source_sha256":h("r"),"observed_state":"REVENUE_RECOGNIZED","observed_at":"2026-09-13T13:05:00Z","freshness_seconds":86400,"prospect_class":"PUBLIC","required":False,"claim":"Revenue recognized."})
        with self.assertRaises(DossierError): self.compile()

    def test_future_required_holds(self):
        self.packet["evidence"][0]["observed_at"] = "2026-09-13T15:00:00Z"
        out = self.compile()
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("guarded-shipping", out["summary"]["missing_required_capabilities"])

    def test_stale_required_holds(self):
        self.packet["evidence"][0]["observed_at"] = "2026-09-10T00:00:00Z"
        self.packet["evidence"][0]["freshness_seconds"] = 60
        out = self.compile()
        self.assertEqual(out["status"], "HOLD")

    def test_internal_required_holds_and_is_not_projected(self):
        self.packet["evidence"][0]["prospect_class"] = "INTERNAL_ONLY"
        out = self.compile()
        self.assertEqual(out["status"], "HOLD")
        self.assertFalse(any(r["source_id"] == "merge-receipt-1" for r in out["evidence"]))

    def test_owner_approval_required_does_not_project_as_demonstrated(self):
        self.packet["evidence"][0]["prospect_class"] = "OWNER_APPROVAL_REQUIRED"
        out = self.compile()
        self.assertEqual(out["status"], "HOLD")

    def test_changed_duplicate_source_fails(self):
        dup = copy.deepcopy(self.packet["evidence"][0]); dup["claim"] = "Changed bytes"
        self.packet["evidence"].append(dup)
        with self.assertRaises(DossierError): self.compile()

    def test_exact_duplicate_cap_source_fails(self):
        self.packet["evidence"].append(copy.deepcopy(self.packet["evidence"][0]))
        with self.assertRaises(DossierError): self.compile()

    def test_bad_hash_fails(self):
        self.packet["evidence"][0]["source_sha256"] = "0"*63
        with self.assertRaises(DossierError): self.compile()

    def test_bad_time_fails(self):
        self.packet["evidence"][0]["observed_at"] = "2026-09-13 13:00:00"
        with self.assertRaises(DossierError): self.compile()

    def test_bool_is_not_integer(self):
        self.packet["evidence"][0]["freshness_seconds"] = True
        with self.assertRaises(DossierError): self.compile()

    def test_unsafe_prospect_text_fails(self):
        self.packet["evidence"][0]["claim"] = "claim=value-not-prospect-safe"
        with self.assertRaises(DossierError): self.compile()

    def test_duplicate_json_keys_fail(self):
        with self.assertRaises(DossierError): strict_json_loads('{"a":1,"a":2}')

    def test_nonfinite_json_fails(self):
        with self.assertRaises(DossierError): strict_json_loads('{"a":NaN}')

    def test_order_invariant(self):
        a = self.compile()
        self.packet["evidence"].reverse()
        b = self.compile()
        self.assertEqual(a, b)

    def test_markdown_deterministic(self):
        out = self.compile()
        self.assertEqual(render_markdown(out), render_markdown(out))
        self.assertIn("Buyer accepted: false", render_markdown(out))

    def test_verifier_tamper(self):
        out = self.compile()
        self.assertTrue(verify_dossier(self.packet, self.policy, AS_OF, out))
        out["summary"]["DEMONSTRATED"] += 1
        self.assertFalse(verify_dossier(self.packet, self.policy, AS_OF, out))

    def test_missing_policy_required_capability_holds(self):
        self.policy["required_capabilities"].append("not-present")
        out = self.compile()
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("not-present", out["summary"]["missing_required_capabilities"])

    def test_unknown_is_not_demonstrated(self):
        self.packet["evidence"].append({"capability_id":"future-capability","source_id":"u1","source_kind":"TEST_RECEIPT","source_ref":"receipt:u1","source_sha256":h("u"),"observed_state":"UNVERIFIED","observed_at":"2026-09-13T13:05:00Z","freshness_seconds":86400,"prospect_class":"PUBLIC","required":False,"claim":"This capability remains unverified."})
        out = self.compile()
        row = next(r for r in out["evidence"] if r["source_id"] == "u1")
        self.assertEqual(row["classification"], "UNKNOWN")

    def test_cli_compile_verify_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            packet = Path(td,"packet.json"); policy = Path(td,"policy.json")
            out = Path(td,"out.json"); md = Path(td,"out.md")
            packet.write_text(json.dumps(self.packet), encoding="utf-8")
            policy.write_text(json.dumps(self.policy), encoding="utf-8")
            self.assertEqual(cli_main(["compile",str(packet),str(policy),"--as-of",AS_OF,"--json-out",str(out),"--markdown-out",str(md)]), 0)
            self.assertEqual(cli_main(["verify",str(packet),str(policy),str(out),"--as-of",AS_OF]), 0)
            self.assertEqual(cli_main(["compile",str(packet),str(policy),"--as-of",AS_OF,"--json-out",str(out),"--markdown-out",str(Path(td,'other.md'))]), 4)

    def test_cli_rejects_symlink_input(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td,"real.json"); target.write_text("{}")
            link = Path(td,"link.json"); os.symlink(target, link)
            self.assertEqual(cli_main(["verify",str(link),str(target),str(target),"--as-of",AS_OF]), 4)


if __name__ == "__main__":
    unittest.main()
