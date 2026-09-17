from __future__ import annotations
from copy import deepcopy
import json
import unittest
from tools.provider_cost_truth import engine, gate
from tools.provider_cost_truth._test_support import NOW,event,request,snapshot

class ProviderCostTruthTests(unittest.TestCase):
    def evaluate(self,snap):return engine._evaluate_snapshot(snap,NOW)

    def test_exact_model_zero_allows_free_only_advisory(self):
        r=self.evaluate(snapshot([event("a-zero")]))
        self.assertEqual(r["state"],"ZERO_COST_VERIFIED");self.assertTrue(r["free_only_satisfied"]);self.assertFalse(r["provider_session_authorized"]);self.assertFalse(r["spend_authorized"])

    def test_account_charge_does_not_become_model_price(self):
        r=self.evaluate(snapshot([event("b-paid",scope="ACCOUNT",kind="CHARGE_PAID",amount=2160)]))
        self.assertEqual(r["state"],"FREE_UNPROVEN_ACCOUNT_BILLING_PRESENT");self.assertFalse(r["free_only_satisfied"]);self.assertEqual(r["controlling_event_ids"],[]);self.assertEqual(r["account_billing_event_ids"],["b-paid"])

    def test_exact_model_charge_is_billable_verified(self):
        r=self.evaluate(snapshot([event("c-paid",kind="CHARGE_PAID",amount=2160)]));self.assertEqual(r["state"],"BILLABLE_VERIFIED");self.assertFalse(r["free_only_satisfied"])

    def test_failed_exact_charge_is_nonzero_billing_evidence(self):
        self.assertEqual(self.evaluate(snapshot([event("d-fail",kind="CHARGE_FAILED",amount=2160)]))["state"],"BILLABLE_VERIFIED")

    def test_session_evidence_cannot_transfer(self):
        self.assertEqual(self.evaluate(snapshot([event("e-sess",scope="SESSION",session_id="session-A")],request(session_id="session-B")))["state"],"COST_UNKNOWN")

    def test_later_paid_supersedes_older_zero(self):
        old=event("a-old",event_at="2026-09-17T18:00:00Z",observed_at="2026-09-17T18:01:00Z")
        new=event("b-new",kind="CHARGE_PAID",amount=100,event_at="2026-09-17T18:40:00Z",observed_at="2026-09-17T18:41:00Z")
        r=self.evaluate(snapshot([old,new]));self.assertEqual(r["state"],"BILLABLE_VERIFIED");self.assertEqual(r["controlling_event_ids"],["b-new"])

    def test_same_generation_zero_and_paid_is_contradictory(self):
        paid=event("b-paid",kind="CHARGE_PAID",amount=100,valid_until=None)
        self.assertEqual(self.evaluate(snapshot([event("a-zero"),paid]))["state"],"CONTRADICTORY")

    def test_stale_and_future_zero_hold(self):
        stale=event("a-stale",event_at="2026-09-01T18:30:00Z",observed_at="2026-09-01T18:31:00Z",valid_until="2026-10-01T18:30:00Z")
        r=self.evaluate(snapshot([stale]));self.assertEqual(r["state"],"COST_UNKNOWN");self.assertIn("IGNORED_STALE_EVIDENCE:a-stale",r["reasons"])
        future=event("a-future",event_at="2026-09-17T19:01:00Z",observed_at="2026-09-17T19:01:00Z",valid_until="2026-09-18T19:01:00Z")
        r=self.evaluate(snapshot([future]));self.assertEqual(r["state"],"COST_UNKNOWN");self.assertIn("IGNORED_FUTURE_EVIDENCE:a-future",r["reasons"])

    def test_marketing_free_claim_cannot_mint_zero(self):
        claim=event("a-marketing",authority="MARKETING_MATERIAL");r=self.evaluate(snapshot([claim]));self.assertEqual(r["state"],"COST_UNKNOWN");self.assertIn("IGNORED_NON_PROVIDER_AUTHORITY:a-marketing",r["reasons"])

    def test_marketing_free_plus_account_charge_is_free_unproven(self):
        claim=event("a-marketing",authority="MARKETING_MATERIAL");paid=event("b-paid",scope="ACCOUNT",kind="CHARGE_PAID",amount=2160)
        self.assertEqual(self.evaluate(snapshot([claim,paid]))["state"],"FREE_UNPROVEN_ACCOUNT_BILLING_PRESENT")

    def test_duplicate_event_and_json_keys_rejected(self):
        with self.assertRaisesRegex(gate.GateError,"duplicate evidence event_id"):self.evaluate(snapshot([event("a-dupe"),event("a-dupe")]))
        with self.assertRaisesRegex(gate.GateError,"duplicate JSON key"):gate.loads_strict_json('{"a":1,"a":2}')

    def test_nonfinite_bool_hash_scope_and_identity_rejected(self):
        with self.assertRaisesRegex(gate.GateError,"non-finite"):gate.loads_strict_json('{"x":NaN}')
        bad=event("a-bool");bad["amount_minor"]=False
        with self.assertRaisesRegex(gate.GateError,"non-negative integer"):self.evaluate(snapshot([bad]))
        bad=event("a-hash");bad["source_sha256"]="ABC"
        with self.assertRaisesRegex(gate.GateError,"lowercase SHA-256"):self.evaluate(snapshot([bad]))
        bad=event("a-scope",scope="SESSION",session_id="s");bad["model"]=None
        with self.assertRaisesRegex(gate.GateError,"SESSION scope identity"):self.evaluate(snapshot([bad]))
        bad=event("a-x");bad["account_id"]="other-account"
        with self.assertRaisesRegex(gate.GateError,"identity transplant"):self.evaluate(snapshot([bad]))

    def test_current_receipt_tamper_and_snapshot_replay_detected(self):
        snap=snapshot([event("a-zero")]);r=gate.compile_current(snap);self.assertTrue(gate.verify_receipt(snap,r))
        bad=deepcopy(r);bad["state"]="COST_UNKNOWN"
        with self.assertRaises(gate.GateError):gate.verify_receipt(snap,bad)
        changed=snapshot([event("a-zero"),event("b-paid",scope="ACCOUNT",kind="CHARGE_PAID",amount=10)])
        with self.assertRaisesRegex(gate.GateError,"semantic replay mismatch|snapshot_sha256"):gate.verify_receipt(changed,r)

    def test_permutation_determinism(self):
        a=event("a-zero");b=event("b-billing",scope="ACCOUNT",kind="CHARGE_PAID",amount=2160,event_at="2026-09-17T18:20:00Z",observed_at="2026-09-17T18:21:00Z")
        self.assertEqual(self.evaluate(snapshot([a,b])),self.evaluate(snapshot([b,a])))

    def test_strict_roundtrip_loader(self):
        snap=snapshot([event("a-zero")]);loaded=gate.loads_strict_json(json.dumps(snap,separators=(",",":")));self.assertEqual(gate.validate_snapshot(loaded),snap)

if __name__=="__main__":unittest.main()
