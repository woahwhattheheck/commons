"""Execution-free, deterministic evidence gate for agent tool calls."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib, json, re
from typing import Any, Iterable, Mapping

SCHEMA="travelers-agent-toolcall-evidence/v1"; RECEIPT="travelers-agent-toolcall-evidence-receipt/v1"
AUTHORITY="EVIDENCE_ONLY_NO_PRODUCTION_TOOL_AUTHORITY"
KINDS={"REQUEST","APPROVE","DISPATCH","OBSERVE","COMPLETE"}; EFFECTS={"READ_ONLY","EXTERNAL_MUTATION"}
ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"); HEX=re.compile(r"^[0-9a-f]{64}$")
class EvidenceError(ValueError): pass

def canon(x:Any)->bytes:
    try:return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    except (TypeError,ValueError) as e:raise EvidenceError("canonical JSON required") from e
def sha(x:Any)->str:return hashlib.sha256(canon(x)).hexdigest()
def exact(x:Any,keys:set[str],f:str)->dict:
    if not isinstance(x,dict) or set(x)!=keys:raise EvidenceError(f"{f} keys")
    return x
def text(x:Any,f:str,n:int=128)->str:
    if not isinstance(x,str) or not x or len(x.encode())>n or any(ord(c)<32 or ord(c)==127 for c in x):raise EvidenceError(f"{f} string")
    return x
def ident(x:Any,f:str)->str:
    x=text(x,f)
    if not ID.fullmatch(x):raise EvidenceError(f"{f} id")
    return x
def h(x:Any,f:str)->str:
    x=text(x,f,64)
    if not HEX.fullmatch(x):raise EvidenceError(f"{f} sha256")
    return x
def nid(x:Any,f:str):return None if x is None else ident(x,f)
def nh(x:Any,f:str):return None if x is None else h(x,f)
def ts(x:Any,f:str)->datetime:
    s=text(x,f,40)
    if not s.endswith("Z"):raise EvidenceError(f"{f} UTC")
    try:return datetime.fromisoformat(s[:-1]+"+00:00").astimezone(timezone.utc)
    except ValueError as e:raise EvidenceError(f"{f} RFC3339") from e
def fmt(x:datetime)->str:return x.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def integer(x:Any,f:str,lo:int,hi:int)->int:
    if isinstance(x,bool) or not isinstance(x,int) or not lo<=x<=hi:raise EvidenceError(f"{f} integer")
    return x

def policy(raw:Mapping[str,Any])->dict:
    p=exact(dict(raw) if isinstance(raw,Mapping) else raw,{"schema","policy_id","version","valid_from","valid_until","max_age_s","max_approval_age_s","skew_s","tools","approver_roles"},"policy")
    if p["schema"]!=SCHEMA:raise EvidenceError("policy schema")
    a,b=ts(p["valid_from"],"valid_from"),ts(p["valid_until"],"valid_until")
    if b<=a:raise EvidenceError("policy window")
    if not isinstance(p["tools"],dict) or not p["tools"] or len(p["tools"])>64:raise EvidenceError("tools")
    tools={}
    for name,row in p["tools"].items():
        name=ident(name,"tool name"); row=exact(row,{"version","effect"},"tool")
        effect=text(row["effect"],"effect",32)
        if effect not in EFFECTS:raise EvidenceError("effect")
        tools[name]={"version":text(row["version"],"tool version"),"effect":effect}
    roles=p["approver_roles"]
    if not isinstance(roles,list) or not roles or len(roles)>32:raise EvidenceError("roles")
    roles=sorted(text(x,"role") for x in roles)
    if len(roles)!=len(set(roles)):raise EvidenceError("duplicate roles")
    return {"schema":SCHEMA,"policy_id":ident(p["policy_id"],"policy_id"),"version":text(p["version"],"version"),"valid_from":fmt(a),"valid_until":fmt(b),"max_age_s":integer(p["max_age_s"],"max_age_s",1,31536000),"max_approval_age_s":integer(p["max_approval_age_s"],"max_approval_age_s",1,604800),"skew_s":integer(p["skew_s"],"skew_s",0,3600),"tools":tools,"approver_roles":roles}
def policy_hash(raw:Mapping[str,Any])->str:return sha(policy(raw))

def event(raw:Any)->dict:
    e=exact(raw,{"id","run","call","kind","at","data"},"event")
    if len(canon(e))>65536:raise EvidenceError("event bytes")
    kind=text(e["kind"],"kind",16)
    if kind not in KINDS:raise EvidenceError("kind")
    d=e["data"]
    if kind=="REQUEST":
        d=exact(d,{"tool","version","args_hash","policy_hash","idem"},"request")
        out={"tool":ident(d["tool"],"tool"),"version":text(d["version"],"version"),"args_hash":h(d["args_hash"],"args_hash"),"policy_hash":h(d["policy_hash"],"policy_hash"),"idem":nid(d["idem"],"idem")}
    elif kind=="APPROVE":
        d=exact(d,{"request_id","role","tool","version","args_hash","policy_hash","approved_at","expires_at"},"approve")
        aa,ex=ts(d["approved_at"],"approved_at"),ts(d["expires_at"],"expires_at")
        if ex<=aa:raise EvidenceError("approval window")
        out={"request_id":ident(d["request_id"],"request_id"),"role":text(d["role"],"role"),"tool":ident(d["tool"],"tool"),"version":text(d["version"],"version"),"args_hash":h(d["args_hash"],"args_hash"),"policy_hash":h(d["policy_hash"],"policy_hash"),"approved_at":fmt(aa),"expires_at":fmt(ex)}
    elif kind=="DISPATCH":
        d=exact(d,{"request_id","approval_id","args_hash","idem","dispatch_key"},"dispatch")
        out={"request_id":ident(d["request_id"],"request_id"),"approval_id":nid(d["approval_id"],"approval_id"),"args_hash":h(d["args_hash"],"args_hash"),"idem":nid(d["idem"],"idem"),"dispatch_key":ident(d["dispatch_key"],"dispatch_key")}
    elif kind=="OBSERVE":
        d=exact(d,{"dispatch_id","outcome","effect","output_hash","effect_hash","idem"},"observe")
        outcome=text(d["outcome"],"outcome",16); effect=text(d["effect"],"effect",16)
        if outcome not in {"SUCCESS","FAILURE","UNKNOWN"} or effect not in {"NONE","APPLIED","UNKNOWN"}:raise EvidenceError("observation enum")
        if outcome=="UNKNOWN" and effect!="UNKNOWN":raise EvidenceError("unknown effect")
        out={"dispatch_id":ident(d["dispatch_id"],"dispatch_id"),"outcome":outcome,"effect":effect,"output_hash":nh(d["output_hash"],"output_hash"),"effect_hash":nh(d["effect_hash"],"effect_hash"),"idem":nid(d["idem"],"idem")}
    else:
        d=exact(d,{"observation_id","status","output_hash","effect_hash"},"complete")
        status=text(d["status"],"status",16)
        if status not in {"SUCCEEDED","FAILED","HELD"}:raise EvidenceError("status")
        out={"observation_id":ident(d["observation_id"],"observation_id"),"status":status,"output_hash":nh(d["output_hash"],"output_hash"),"effect_hash":nh(d["effect_hash"],"effect_hash")}
    return {"id":ident(e["id"],"id"),"run":ident(e["run"],"run"),"call":ident(e["call"],"call"),"kind":kind,"at":fmt(ts(e["at"],"at")),"data":out}

def normalize(events:Iterable[Any]):
    rows=list(events)
    if not 1<=len(rows)<=256:raise EvidenceError("event count")
    variants={}
    for raw in rows:
        e=event(raw); variants.setdefault(e["id"],{})[canon(e)]=e
    out=[]; conflicts=set()
    for eid in sorted(variants):
        group=variants[eid]
        if len(group)>1:conflicts.add(eid)
        out.append(group[min(group)])
    return out,conflicts

def call_review(rows:list[dict],conflicts:set[str],p:dict,ph:str,now:datetime)->dict:
    reasons=set(); by={k:[e for e in rows if e["kind"]==k] for k in KINDS}; cid=rows[0]["call"]
    if any(e["id"] in conflicts for e in rows):reasons.add("EVENT_IDENTITY_CONFLICT")
    for k,want in (("REQUEST",1),("COMPLETE",1)):
        if len(by[k])!=want:reasons.add(k+"_COUNT")
    if not 1<=len(by["DISPATCH"])<=8:reasons.add("DISPATCH_COUNT")
    if len(by["OBSERVE"])!=len(by["DISPATCH"]):reasons.add("OBSERVE_COUNT")
    for e in rows:
        at=ts(e["at"],"at")
        if at>now+timedelta(seconds=p["skew_s"]):reasons.add("FUTURE_EVENT")
        if now-at>timedelta(seconds=p["max_age_s"]):reasons.add("STALE_EVENT")
    req=by["REQUEST"][0] if len(by["REQUEST"])==1 else None; comp=by["COMPLETE"][0] if len(by["COMPLETE"])==1 else None
    tool=version=effect=""; result="HELD"
    if req:
        q=req["data"]; tool=q["tool"]; version=q["version"]
        spec=p["tools"].get(tool)
        if not spec or spec["version"]!=version:reasons.add("TOOL_NOT_ALLOWED"); effect=spec["effect"] if spec else ""
        else:effect=spec["effect"]
        if q["policy_hash"]!=ph:reasons.add("POLICY_HASH_MISMATCH")
        approvals=by["APPROVE"]
        if effect=="EXTERNAL_MUTATION":
            if q["idem"] is None:reasons.add("IDEMPOTENCY_REQUIRED")
            if len(approvals)!=1:reasons.add("APPROVAL_COUNT")
        elif approvals:reasons.add("UNEXPECTED_APPROVAL")
        app=approvals[0] if len(approvals)==1 else None
        if app:
            a=app["data"]
            if effect!="EXTERNAL_MUTATION":reasons.add("APPROVAL_ON_READ_ONLY")
            if a["request_id"]!=req["id"]:reasons.add("APPROVAL_REQUEST_MISMATCH")
            if (a["tool"],a["version"],a["args_hash"],a["policy_hash"])!=(tool,version,q["args_hash"],ph):reasons.add("APPROVAL_BINDING_MISMATCH")
            if a["role"] not in p["approver_roles"]:reasons.add("APPROVER_ROLE")
            aa,ex=ts(a["approved_at"],"approved_at"),ts(a["expires_at"],"expires_at")
            if aa<ts(req["at"],"request at") or ts(app["at"],"approval at")<aa:reasons.add("APPROVAL_TIME")
            if now>ex or now-aa>timedelta(seconds=p["max_approval_age_s"]):reasons.add("APPROVAL_STALE")
        dispatches=sorted(by["DISPATCH"],key=lambda e:(e["at"],e["id"])); obsmap={}
        for o in by["OBSERVE"]:obsmap.setdefault(o["data"]["dispatch_id"],[]).append(o)
        seen=set(); resolved=[]
        for d in dispatches:
            x=d["data"]
            if x["dispatch_key"] in seen:reasons.add("DISPATCH_KEY_REUSED")
            seen.add(x["dispatch_key"])
            if x["request_id"]!=req["id"] or x["args_hash"]!=q["args_hash"]:reasons.add("DISPATCH_BINDING_MISMATCH")
            if ts(d["at"],"dispatch at")<ts(req["at"],"request at"):reasons.add("DISPATCH_BEFORE_REQUEST")
            if effect=="EXTERNAL_MUTATION":
                if app is None or x["approval_id"]!=app["id"]:reasons.add("DISPATCH_APPROVAL_MISMATCH")
                if x["idem"]!=q["idem"]:reasons.add("IDEMPOTENCY_MISMATCH")
            elif x["approval_id"] is not None or x["idem"] is not None:reasons.add("READ_ONLY_DISPATCH_METADATA")
            os=obsmap.get(d["id"],[])
            if len(os)!=1:reasons.add("OBSERVATION_LINK_COUNT");continue
            o=os[0]; z=o["data"]
            if ts(o["at"],"observe at")<ts(d["at"],"dispatch at"):reasons.add("OBSERVE_BEFORE_DISPATCH")
            if effect=="READ_ONLY":
                if z["effect"]!="NONE" or z["effect_hash"] is not None or z["idem"] is not None:reasons.add("READ_ONLY_EFFECT_INVALID")
            else:
                if z["idem"]!=q["idem"]:reasons.add("OBSERVATION_IDEMPOTENCY_MISMATCH")
                if z["outcome"]=="SUCCESS" and (z["effect"]!="APPLIED" or z["effect_hash"] is None):reasons.add("SUCCESS_EFFECT_EVIDENCE")
                if z["outcome"]=="FAILURE" and (z["effect"]!="NONE" or z["effect_hash"] is None):reasons.add("FAILURE_NO_EFFECT_EVIDENCE")
                if z["outcome"]=="UNKNOWN":reasons.add("UNKNOWN_MUTATION_OUTCOME")
            if z["outcome"]=="UNKNOWN":reasons.add("UNKNOWN_OUTCOME")
            if z["outcome"]=="SUCCESS" and z["output_hash"] is None:reasons.add("SUCCESS_OUTPUT_MISSING")
            resolved.append(o)
        dids={d["id"] for d in dispatches}
        if any(o["data"]["dispatch_id"] not in dids for o in by["OBSERVE"]):reasons.add("ORPHAN_OBSERVATION")
        if effect=="EXTERNAL_MUTATION" and len(resolved)>1:
            if any(o["data"]["effect"]=="UNKNOWN" for o in resolved[:-1]):reasons.add("RETRY_AFTER_UNKNOWN")
            applied=[o["data"]["effect_hash"] for o in resolved if o["data"]["effect"]=="APPLIED"]
            if len(set(applied))>1:reasons.add("EFFECT_RECEIPT_CONFLICT")
        if comp and resolved:
            m={o["id"]:o for o in resolved}; o=m.get(comp["data"]["observation_id"])
            if not o:reasons.add("COMPLETION_OBSERVATION_MISMATCH")
            else:
                z=o["data"]; expected="SUCCEEDED" if z["outcome"]=="SUCCESS" else "FAILED" if z["outcome"]=="FAILURE" else "HELD"
                if ts(comp["at"],"complete at")<ts(o["at"],"observe at"):reasons.add("COMPLETE_BEFORE_OBSERVE")
                if (comp["data"]["status"],comp["data"]["output_hash"],comp["data"]["effect_hash"])!=(expected,z["output_hash"],z["effect_hash"]):reasons.add("COMPLETION_BINDING_MISMATCH")
                result=expected
    return {"call":cid,"tool":tool,"version":version,"effect":effect,"review":"HOLD" if reasons else "PASS","result":result,"reasons":sorted(reasons),"event_ids":[e["id"] for e in sorted(rows,key=lambda e:(e["at"],e["id"]))],"events_hash":sha(sorted(rows,key=lambda e:e["id"]))}

def evaluate(events:Iterable[Any],raw_policy:Mapping[str,Any],*,evaluated_at:str)->dict:
    now=ts(evaluated_at,"evaluated_at"); p=policy(raw_policy); ph=sha(p); reasons=set()
    if not ts(p["valid_from"],"valid_from")<=now<=ts(p["valid_until"],"valid_until"):reasons.add("POLICY_NOT_CURRENT")
    rows,conflicts=normalize(events); runs=sorted({e["run"] for e in rows})
    if len(runs)!=1:reasons.add("RUN_IDENTITY_CONFLICT")
    groups={}
    for e in rows:groups.setdefault(e["call"],[]).append(e)
    calls=[call_review(v,conflicts,p,ph,now) for _,v in sorted(groups.items())]
    if any(c["review"]=="HOLD" for c in calls):reasons.add("CALL_HOLD")
    out={"schema":RECEIPT,"authority":AUTHORITY,"evaluated_at":fmt(now),"policy_hash":ph,"run":runs[0] if len(runs)==1 else "MULTIPLE","status":"HOLD" if reasons else "PASS","reasons":sorted(reasons),"counts":{"calls":len(calls),"passed":sum(c["review"]=="PASS" for c in calls),"held":sum(c["review"]=="HOLD" for c in calls),"events":len(rows),"conflicts":len(conflicts)},"calls":calls,"evidence_hash":sha(rows),"authority_flags":{"production_tool_execution":False,"provider_mutation":False,"credential_use":False,"customer_data_access":False,"deployment":False,"insurance_or_financial_decision":False,"payment":False,"recognized_revenue":False}}
    out["receipt_hash"]=sha(out);return out
def verify(events,raw_policy,*,evaluated_at:str,receipt:Mapping[str,Any])->bool:
    return isinstance(receipt,Mapping) and canon(dict(receipt))==canon(evaluate(events,raw_policy,evaluated_at=evaluated_at))
def markdown(r:Mapping[str,Any])->str:
    if r.get("schema")!=RECEIPT:raise EvidenceError("receipt schema")
    lines=["# Agent Tool-Call Evidence Review","",f"- Status: **{r['status']}**",f"- Authority: `{r['authority']}`",f"- Run: `{r['run']}`",f"- Receipt: `{r['receipt_hash']}`","","| Call | Tool | Effect | Evidence | Result | Reasons |","| --- | --- | --- | --- | --- | --- |"]
    for c in r["calls"]:lines.append(f"| `{c['call']}` | `{c['tool']}@{c['version']}` | {c['effect']} | {c['review']} | {c['result']} | {', '.join(c['reasons']) or '—'} |")
    lines += ["","Evidence-only. No production execution, provider mutation, credential use, customer-data access, deployment, financial/insurance decision, payment, or revenue authority.",""]
    return "\n".join(lines)
