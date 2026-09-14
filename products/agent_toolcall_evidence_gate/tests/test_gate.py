from __future__ import annotations
from copy import deepcopy
import unittest
from products.agent_toolcall_evidence_gate.acceptance import policy_fixture, request_fixture, run_acceptance
from products.agent_toolcall_evidence_gate.engine import GateError, Policy, approval_intent_sha256, empty_ledger, evaluate, loads_strict, verify_transition

class GateTests(unittest.TestCase):
    def setUp(self):
        self.policy=policy_fixture(); self.ledger=empty_ledger(Policy.parse(self.policy))
    def gate(self,r): return evaluate(self.policy,r,self.ledger)
    def test_golden_240(self):
        report=run_acceptance(); self.assertEqual((report["allowed"],report["held"]),(192,48)); self.assertTrue(report["zero_defective_allowed"])
    def test_allow_appends_and_verifies(self):
        req=request_fixture(1); receipt,nxt=self.gate(req); self.assertEqual(receipt["decision"],"EXECUTE_ALLOWED"); self.assertEqual(len(nxt["entries"]),1); self.assertTrue(verify_transition(self.policy,req,self.ledger,receipt,nxt))
    def test_hold_does_not_append(self):
        req=request_fixture(2); req["tool_call"]["action"]="delete"; receipt,nxt=self.gate(req); self.assertEqual(receipt["decision"],"HOLD"); self.assertEqual(nxt,self.ledger)
    def test_agent_version(self):
        r=request_fixture(3); r["agent"]["version"]="9.9.9"; self.assertIn("AGENT_VERSION_NOT_ALLOWED",self.gate(r)[0]["reason_codes"])
    def test_resource_and_role(self):
        r=request_fixture(4); r["tool_call"]["target_resource"]="other/4"; self.assertIn("ROLE_RESOURCE_MISMATCH",self.gate(r)[0]["reason_codes"])
    def test_restricted(self):
        r=request_fixture(5); r["tool_call"]["data_class"]="secret"; self.assertIn("RESTRICTED_DATA_EXPOSURE",self.gate(r)[0]["reason_codes"])
    def test_approval_required(self):
        r=request_fixture(6,payment=True); r["approval"]=None; self.assertIn("HUMAN_APPROVAL_REQUIRED",self.gate(r)[0]["reason_codes"])
    def test_approval_wrong_role(self):
        r=request_fixture(7,payment=True); r["approval"]["approver_role"]="agent"; self.assertIn("HUMAN_APPROVAL_REQUIRED",self.gate(r)[0]["reason_codes"])
    def test_approval_intent_transplant_holds(self):
        r=request_fixture(70,payment=True); stale=r["approval"]["intent_sha256"]; r["tool_call"]["target_resource"]="payment/other"; self.assertEqual(r["approval"]["intent_sha256"],stale); self.assertIn("HUMAN_APPROVAL_REQUIRED",self.gate(r)[0]["reason_codes"])
    def test_duplicate_request_id_is_replay_even_with_new_idempotency(self):
        a=request_fixture(71); _,led=evaluate(self.policy,a,self.ledger); b=request_fixture(72); b["request_id"]=a["request_id"]; receipt,nxt=evaluate(self.policy,b,led); self.assertIn("IDEMPOTENCY_REPLAY",receipt["reason_codes"]); self.assertEqual(nxt,led)
    def test_request_budget(self):
        r=request_fixture(8,payment=True); r["budget_cents"]=5001; r["approval"]["intent_sha256"]=approval_intent_sha256(r); self.assertIn("BUDGET_OR_RATE_LIMIT",self.gate(r)[0]["reason_codes"])
    def test_rate_limit_from_authoritative_ledger(self):
        p=deepcopy(self.policy); p["rules"][0]["max_calls_per_window"]=1; led=empty_ledger(Policy.parse(p)); a=request_fixture(10); _,led=evaluate(p,a,led); b=request_fixture(11); receipt,_=evaluate(p,b,led); self.assertIn("BUDGET_OR_RATE_LIMIT",receipt["reason_codes"])
    def test_window_budget_accumulates(self):
        p=deepcopy(self.policy); p["rules"][0]["max_window_budget_cents"]=75; led=empty_ledger(Policy.parse(p)); _,led=evaluate(p,request_fixture(12),led); r=request_fixture(13); receipt,_=evaluate(p,r,led); self.assertIn("BUDGET_OR_RATE_LIMIT",receipt["reason_codes"])
    def test_replay(self):
        r=request_fixture(14); _,led=evaluate(self.policy,r,self.ledger); r2=request_fixture(15); r2["idempotency_key"]=r["idempotency_key"]; receipt,nxt=evaluate(self.policy,r2,led); self.assertIn("IDEMPOTENCY_REPLAY",receipt["reason_codes"]); self.assertEqual(nxt,led)
    def test_trace_zero_digest_holds(self):
        r=request_fixture(16); r["trace"]["evidence_sha256"]="0"*64; self.assertIn("TRACE_INCOMPLETE",self.gate(r)[0]["reason_codes"])
    def test_policy_digest_stale_ledger_fails(self):
        p=deepcopy(self.policy); p["revision"]=2
        with self.assertRaisesRegex(GateError,"LEDGER_POLICY_MISMATCH"): evaluate(p,request_fixture(17),self.ledger)
    def test_ledger_digest_tamper_fails(self):
        bad=deepcopy(self.ledger); bad["ledger_sha256"]="f"*64
        with self.assertRaisesRegex(GateError,"LEDGER_DIGEST_MISMATCH"): evaluate(self.policy,request_fixture(18),bad)
    def test_request_schema_extra_field_fails(self):
        r=request_fixture(19); r["recipient"]="smuggled"
        with self.assertRaisesRegex(GateError,"keys mismatch"): self.gate(r)
    def test_policy_overlap_duplicate_action_fails(self):
        p=deepcopy(self.policy); p["rules"].append(deepcopy(p["rules"][0]))
        with self.assertRaisesRegex(GateError,"duplicate tool/action"): Policy.parse(p)
    def test_nonapproval_rule_cannot_smuggle_approval_roles(self):
        p=deepcopy(self.policy); p["rules"][0]["approval_roles"]=["supervisor"]
        with self.assertRaisesRegex(GateError,"non-approval"): Policy.parse(p)
    def test_duplicate_json_rejected(self):
        with self.assertRaisesRegex(GateError,"duplicate JSON key"): loads_strict('{"a":1,"a":2}')
    def test_float_and_nan_rejected(self):
        for raw in ('{"x":1.5}','{"x":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(GateError): loads_strict(raw)
    def test_receipt_transplant_fails_verify(self):
        req=request_fixture(20); receipt,nxt=self.gate(req); other=request_fixture(21); self.assertFalse(verify_transition(self.policy,other,self.ledger,receipt,nxt))
    def test_reason_codes_sorted(self):
        r=request_fixture(22,payment=True); r["agent"]["version"]="bad"; r["actor"]["role"]="intern"; r["tool_call"]["data_class"]="restricted"; r["approval"]=None; r["budget_cents"]=9000; receipt,_=self.gate(r); self.assertEqual(receipt["reason_codes"],sorted(receipt["reason_codes"]))
    def test_deterministic_same_input(self):
        r=request_fixture(23); self.assertEqual(self.gate(r),self.gate(deepcopy(r)))

if __name__=="__main__": unittest.main(verbosity=2)
