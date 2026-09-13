from copy import deepcopy
import hashlib, json
from .gate import evaluate, policy_hash, verify

def H(s):return hashlib.sha256(s.encode()).hexdigest()
NOW="2026-09-13T13:55:00Z"
POLICY={"schema":"travelers-agent-toolcall-evidence/v1","policy_id":"travelers-synthetic","version":"1","valid_from":"2026-09-13T12:00:00Z","valid_until":"2026-09-14T12:00:00Z","max_age_s":7200,"max_approval_age_s":3600,"skew_s":30,"tools":{"policy.lookup":{"version":"1","effect":"READ_ONLY"},"claim.update":{"version":"3","effect":"EXTERNAL_MUTATION"}},"approver_roles":["claims-supervisor"]}
PH=policy_hash(POLICY)
def fixture():
 return [
 {"id":"r-q","run":"run-1","call":"read","kind":"REQUEST","at":"2026-09-13T13:50:00Z","data":{"tool":"policy.lookup","version":"1","args_hash":H("ra"),"policy_hash":PH,"idem":None}},
 {"id":"r-d","run":"run-1","call":"read","kind":"DISPATCH","at":"2026-09-13T13:50:01Z","data":{"request_id":"r-q","approval_id":None,"args_hash":H("ra"),"idem":None,"dispatch_key":"rd1"}},
 {"id":"r-o","run":"run-1","call":"read","kind":"OBSERVE","at":"2026-09-13T13:50:02Z","data":{"dispatch_id":"r-d","outcome":"SUCCESS","effect":"NONE","output_hash":H("ro"),"effect_hash":None,"idem":None}},
 {"id":"r-c","run":"run-1","call":"read","kind":"COMPLETE","at":"2026-09-13T13:50:03Z","data":{"observation_id":"r-o","status":"SUCCEEDED","output_hash":H("ro"),"effect_hash":None}},
 {"id":"m-q","run":"run-1","call":"mutate","kind":"REQUEST","at":"2026-09-13T13:51:00Z","data":{"tool":"claim.update","version":"3","args_hash":H("ma"),"policy_hash":PH,"idem":"idem-1"}},
 {"id":"m-a","run":"run-1","call":"mutate","kind":"APPROVE","at":"2026-09-13T13:51:05Z","data":{"request_id":"m-q","role":"claims-supervisor","tool":"claim.update","version":"3","args_hash":H("ma"),"policy_hash":PH,"approved_at":"2026-09-13T13:51:04Z","expires_at":"2026-09-13T14:10:00Z"}},
 {"id":"m-d","run":"run-1","call":"mutate","kind":"DISPATCH","at":"2026-09-13T13:51:06Z","data":{"request_id":"m-q","approval_id":"m-a","args_hash":H("ma"),"idem":"idem-1","dispatch_key":"md1"}},
 {"id":"m-o","run":"run-1","call":"mutate","kind":"OBSERVE","at":"2026-09-13T13:51:07Z","data":{"dispatch_id":"m-d","outcome":"SUCCESS","effect":"APPLIED","output_hash":H("mo"),"effect_hash":H("effect-1"),"idem":"idem-1"}},
 {"id":"m-c","run":"run-1","call":"mutate","kind":"COMPLETE","at":"2026-09-13T13:51:08Z","data":{"observation_id":"m-o","status":"SUCCEEDED","output_hash":H("mo"),"effect_hash":H("effect-1")}},]
def acceptance():
 base=fixture(); good=evaluate(base,POLICY,evaluated_at=NOW); checks={"base":good["status"]=="PASS" and good["counts"]["passed"]==2,"replay":verify(base,POLICY,evaluated_at=NOW,receipt=good)}
 variants={}
 v=deepcopy(base);next(e for e in v if e["id"]=="m-a")["data"]["args_hash"]=H("tamper");variants["approval_tamper"]=v
 v=deepcopy(base);o=next(e for e in v if e["id"]=="m-o");o["data"].update(outcome="UNKNOWN",effect="UNKNOWN");next(e for e in v if e["id"]=="m-c")["data"]["status"]="HELD";variants["unknown_effect"]=v
 v=deepcopy(base);x=deepcopy(next(e for e in v if e["id"]=="m-d"));x["data"]["args_hash"]=H("conflict");v.append(x);variants["event_conflict"]=v
 v=deepcopy(base);next(e for e in v if e["id"]=="m-d")["data"]["idem"]="idem-2";variants["idem_drift"]=v
 v=deepcopy(base);next(e for e in v if e["id"]=="m-c")["data"]["output_hash"]=H("tamper");variants["completion_tamper"]=v
 for name,v in variants.items():checks[name]=evaluate(v,POLICY,evaluated_at=NOW)["status"]=="HOLD"
 return {"pass":all(checks.values()),"checks":checks,"receipt_hash":good["receipt_hash"]}
def main():
 r=acceptance();print(json.dumps(r,sort_keys=True,separators=(",",":")));return 0 if r["pass"] else 2
if __name__=="__main__":raise SystemExit(main())
