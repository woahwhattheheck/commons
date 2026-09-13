from copy import deepcopy
import unittest
from .acceptance import H,NOW,POLICY,fixture
from .gate import EvidenceError,evaluate,event,markdown,policy,policy_hash,verify
class GateTests(unittest.TestCase):
 def C(self,r,c):return next(x for x in r["calls"] if x["call"]==c)
 def test_pass(self):
  r=evaluate(fixture(),POLICY,evaluated_at=NOW);self.assertEqual("PASS",r["status"]);self.assertEqual(2,r["counts"]["passed"]);self.assertTrue(all(v is False for v in r["authority_flags"].values()))
 def test_order_independent(self):self.assertEqual(evaluate(fixture(),POLICY,evaluated_at=NOW),evaluate(list(reversed(fixture())),POLICY,evaluated_at=NOW))
 def test_exact_duplicate_dedupes(self):
  v=fixture();v.append(deepcopy(v[0]));self.assertEqual("PASS",evaluate(v,POLICY,evaluated_at=NOW)["status"])
 def test_conflict_holds(self):
  v=fixture();x=deepcopy(v[0]);x["at"]="2026-09-13T13:50:01Z";v.append(x);self.assertIn("EVENT_IDENTITY_CONFLICT",self.C(evaluate(v,POLICY,evaluated_at=NOW),"read")["reasons"])
 def test_missing_approval(self):
  v=[e for e in fixture() if e["id"]!="m-a"];self.assertIn("APPROVAL_COUNT",self.C(evaluate(v,POLICY,evaluated_at=NOW),"mutate")["reasons"])
 def test_approval_binding(self):
  v=fixture();next(e for e in v if e["id"]=="m-a")["data"]["args_hash"]=H("x");self.assertIn("APPROVAL_BINDING_MISMATCH",self.C(evaluate(v,POLICY,evaluated_at=NOW),"mutate")["reasons"])
 def test_policy_hash(self):
  v=fixture();next(e for e in v if e["id"]=="r-q")["data"]["policy_hash"]=H("x");self.assertIn("POLICY_HASH_MISMATCH",self.C(evaluate(v,POLICY,evaluated_at=NOW),"read")["reasons"])
 def test_tool_version(self):
  v=fixture();next(e for e in v if e["id"]=="r-q")["data"]["version"]="9";self.assertIn("TOOL_NOT_ALLOWED",self.C(evaluate(v,POLICY,evaluated_at=NOW),"read")["reasons"])
 def test_unknown_holds(self):
  v=fixture();o=next(e for e in v if e["id"]=="m-o");o["data"].update(outcome="UNKNOWN",effect="UNKNOWN");next(e for e in v if e["id"]=="m-c")["data"]["status"]="HELD";self.assertIn("UNKNOWN_MUTATION_OUTCOME",self.C(evaluate(v,POLICY,evaluated_at=NOW),"mutate")["reasons"])
 def test_success_effect_receipt(self):
  v=fixture();next(e for e in v if e["id"]=="m-o")["data"]["effect_hash"]=None;next(e for e in v if e["id"]=="m-c")["data"]["effect_hash"]=None;self.assertIn("SUCCESS_EFFECT_EVIDENCE",self.C(evaluate(v,POLICY,evaluated_at=NOW),"mutate")["reasons"])
 def test_failure_no_effect_receipt(self):
  v=fixture();o=next(e for e in v if e["id"]=="m-o");o["data"].update(outcome="FAILURE",effect="NONE",output_hash=None,effect_hash=None);c=next(e for e in v if e["id"]=="m-c");c["data"].update(status="FAILED",output_hash=None,effect_hash=None);self.assertIn("FAILURE_NO_EFFECT_EVIDENCE",self.C(evaluate(v,POLICY,evaluated_at=NOW),"mutate")["reasons"])
 def test_failure_with_receipt_passes(self):
  v=fixture();z=H("none");o=next(e for e in v if e["id"]=="m-o");o["data"].update(outcome="FAILURE",effect="NONE",output_hash=None,effect_hash=z);c=next(e for e in v if e["id"]=="m-c");c["data"].update(status="FAILED",output_hash=None,effect_hash=z);self.assertEqual("PASS",evaluate(v,POLICY,evaluated_at=NOW)["status"])
 def test_read_only_effect(self):
  v=fixture();o=next(e for e in v if e["id"]=="r-o");o["data"].update(effect="APPLIED",effect_hash=H("x"));self.assertIn("READ_ONLY_EFFECT_INVALID",self.C(evaluate(v,POLICY,evaluated_at=NOW),"read")["reasons"])
 def test_idem_drift(self):
  v=fixture();next(e for e in v if e["id"]=="m-d")["data"]["idem"]="idem-2";self.assertIn("IDEMPOTENCY_MISMATCH",self.C(evaluate(v,POLICY,evaluated_at=NOW),"mutate")["reasons"])
 def test_safe_retry(self):
  v=fixture();d=deepcopy(next(e for e in v if e["id"]=="m-d"));d.update(id="m-d2",at="2026-09-13T13:51:08Z");d["data"]["dispatch_key"]="md2";o=deepcopy(next(e for e in v if e["id"]=="m-o"));o.update(id="m-o2",at="2026-09-13T13:51:09Z");o["data"]["dispatch_id"]="m-d2";c=next(e for e in v if e["id"]=="m-c");c.update(at="2026-09-13T13:51:10Z");c["data"]["observation_id"]="m-o2";v.extend([d,o]);self.assertEqual("PASS",evaluate(v,POLICY,evaluated_at=NOW)["status"])
 def test_retry_effect_conflict(self):
  v=fixture();d=deepcopy(next(e for e in v if e["id"]=="m-d"));d.update(id="m-d2",at="2026-09-13T13:51:08Z");d["data"]["dispatch_key"]="md2";o=deepcopy(next(e for e in v if e["id"]=="m-o"));o.update(id="m-o2",at="2026-09-13T13:51:09Z");o["data"].update(dispatch_id="m-d2",effect_hash=H("other"));c=next(e for e in v if e["id"]=="m-c");c.update(at="2026-09-13T13:51:10Z");c["data"].update(observation_id="m-o2",effect_hash=H("other"));v.extend([d,o]);self.assertIn("EFFECT_RECEIPT_CONFLICT",self.C(evaluate(v,POLICY,evaluated_at=NOW),"mutate")["reasons"])
 def test_completion_tamper(self):
  v=fixture();next(e for e in v if e["id"]=="r-c")["data"]["output_hash"]=H("x");self.assertIn("COMPLETION_BINDING_MISMATCH",self.C(evaluate(v,POLICY,evaluated_at=NOW),"read")["reasons"])
 def test_future(self):
  v=fixture();next(e for e in v if e["id"]=="r-q")["at"]="2026-09-13T14:55:00Z";self.assertIn("FUTURE_EVENT",self.C(evaluate(v,POLICY,evaluated_at=NOW),"read")["reasons"])
 def test_stale(self):
  v=fixture();next(e for e in v if e["id"]=="r-q")["at"]="2026-09-13T10:00:00Z";self.assertIn("STALE_EVENT",self.C(evaluate(v,POLICY,evaluated_at=NOW),"read")["reasons"])
 def test_policy_current(self):self.assertIn("POLICY_NOT_CURRENT",evaluate(fixture(),POLICY,evaluated_at="2026-09-15T13:55:00Z")["reasons"])
 def test_schema_strict(self):
  p=deepcopy(POLICY);p["extra"]=1
  with self.assertRaises(EvidenceError):policy(p)
 def test_bool_integer_rejected(self):
  p=deepcopy(POLICY);p["skew_s"]=True
  with self.assertRaises(EvidenceError):policy(p)
 def test_event_control_rejected(self):
  e=deepcopy(fixture()[0]);e["data"]["tool"]="bad\nname"
  with self.assertRaises(EvidenceError):event(e)
 def test_verify_tamper(self):
  v=fixture();r=evaluate(v,POLICY,evaluated_at=NOW);self.assertTrue(verify(v,POLICY,evaluated_at=NOW,receipt=r));r=deepcopy(r);r["counts"]["calls"]=99;self.assertFalse(verify(v,POLICY,evaluated_at=NOW,receipt=r))
 def test_markdown_authority(self):self.assertIn("No production execution",markdown(evaluate(fixture(),POLICY,evaluated_at=NOW)))
if __name__=="__main__":unittest.main()
