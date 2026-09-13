#!/usr/bin/env python3
"""Offline, evidence-bound disclosure and customer-reference authority registry."""
from __future__ import annotations

import argparse, copy, hashlib, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SCHEMA_VERSION = "commons-reference-authority/v1"
RESULT_SCHEMA_VERSION = "commons-reference-authority-result/v1"
RECEIPT_SCHEMA_VERSION = "commons-reference-authority-receipt/v1"
ENGAGEMENT_KINDS = {"CLIENT_ENGAGEMENT","INTERNAL_ENGINEERING","OPEN_SOURCE_CONTRIBUTION","EXTERNAL_REVIEW_PROGRAM","PROCUREMENT_PURSUIT"}
DISCLOSURE_USE_CLASSES = {"INTERNAL_ONLY","CAPABILITY_NARRATIVE","PROPOSAL_CAPABILITY"}
AUTHORITY_STATUSES = {"AUTHORIZED","REVOKED"}
COMPARABILITY_STATUSES = {"COMPARABLE","NOT_COMPARABLE"}
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_EMAIL = re.compile(r"(?i)(?<![\w.%+-])[\w.%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.%+-])")
_PHONE = re.compile(r"(?<!\w)(?:\+?1[ .-]?)?(?:\(?\d{3}\)?[ .-]?)\d{3}[ .-]\d{4}(?!\w)")
_SECRET = re.compile(r"(?i)(?:bearer\s+[A-Za-z0-9._~-]{8,}|(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|passwd|private[_-]?key)\s*[:=])")
_PATH = re.compile(r"(?:^|\s)(?:[A-Za-z]:[\\/]|/home/|/Users/|/mnt/|\\\\|\.\.[\\/])")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")

class ReferenceAuthorityError(ValueError): pass

def canonical_bytes(v: Any) -> bytes:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode()

def sha256_hex(v: bytes) -> str: return hashlib.sha256(v).hexdigest()
def record_digest(v: dict[str,Any]) -> str: return sha256_hex(canonical_bytes(v))

def _nodup(pairs):
    out = {}
    for k,v in pairs:
        if k in out: raise ReferenceAuthorityError(f"duplicate JSON key: {k}")
        out[k]=v
    return out

def strict_json_loads(raw):
    try: return json.loads(raw, object_pairs_hook=_nodup)
    except ReferenceAuthorityError: raise
    except (json.JSONDecodeError,UnicodeDecodeError) as e: raise ReferenceAuthorityError(f"invalid JSON: {e}") from e

def _obj(v,w):
    if not isinstance(v,dict): raise ReferenceAuthorityError(f"{w} must be an object")
    return v

def _arr(v,w):
    if not isinstance(v,list): raise ReferenceAuthorityError(f"{w} must be an array")
    return v

def _keys(o, names, w):
    names=set(names); got=set(o); missing=names-got; extra=got-names
    if missing: raise ReferenceAuthorityError(f"{w} missing fields: {', '.join(sorted(missing))}")
    if extra: raise ReferenceAuthorityError(f"{w} unknown fields: {', '.join(sorted(extra))}")

def _text(v,w,n=500):
    if not isinstance(v,str) or not v or len(v)>n: raise ReferenceAuthorityError(f"{w} length/type invalid")
    if v != v.strip(): raise ReferenceAuthorityError(f"{w} must not have surrounding whitespace")
    if _CONTROL.search(v): raise ReferenceAuthorityError(f"{w} contains control characters")
    if _EMAIL.search(v): raise ReferenceAuthorityError(f"{w} contains email/contact PII")
    if _PHONE.search(v): raise ReferenceAuthorityError(f"{w} contains phone/contact PII")
    if _SECRET.search(v): raise ReferenceAuthorityError(f"{w} contains credential-shaped text")
    if _PATH.search(v): raise ReferenceAuthorityError(f"{w} contains path-shaped text")
    return v

def _id(v,w):
    v=_text(v,w,128)
    if not _ID.fullmatch(v): raise ReferenceAuthorityError(f"{w} has invalid id syntax")
    return v

def _sha(v,w):
    if not isinstance(v,str) or not _SHA.fullmatch(v): raise ReferenceAuthorityError(f"{w} must be lowercase SHA-256 hex")
    return v

def _ref(v,w,*,opaque=False):
    v=_text(v,w,512)
    if opaque and v.startswith("opaque:"):
        if not _ID.fullmatch(v[7:]): raise ReferenceAuthorityError(f"{w} has invalid opaque authority handle")
        return v
    p=urlsplit(v)
    if p.scheme!="https" or not p.netloc or p.username or p.password: raise ReferenceAuthorityError(f"{w} must be a public https URL without embedded credentials")
    if _SECRET.search(p.query) or _SECRET.search(p.fragment): raise ReferenceAuthorityError(f"{w} has secret-shaped query/fragment")
    return v

def _ts(v,w):
    v=_text(v,w,20)
    try: d=datetime.strptime(v,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as e: raise ReferenceAuthorityError(f"{w} must be UTC YYYY-MM-DDTHH:MM:SSZ") from e
    if d.strftime("%Y-%m-%dT%H:%M:%SZ")!=v: raise ReferenceAuthorityError(f"{w} is not canonical UTC")
    return v

def _ots(v,w): return None if v is None else _ts(v,w)
def _dt(v): return datetime.strptime(v,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
def _int(v,w,lo=0,hi=1000):
    if isinstance(v,bool) or not isinstance(v,int): raise ReferenceAuthorityError(f"{w} must be an integer (bool forbidden)")
    if not lo<=v<=hi: raise ReferenceAuthorityError(f"{w} outside [{lo}, {hi}]")
    return v

def _texts(v,w):
    a=[_text(x,f"{w}[{i}]",300) for i,x in enumerate(_arr(v,w))]
    if len(a)>32: raise ReferenceAuthorityError(f"{w} has too many items")
    if len(a)!=len(set(a)): raise ReferenceAuthorityError(f"{w} contains duplicates")
    return sorted(a)

def _unique(rows,key,w):
    vals=[x[key] for x in rows]
    if len(vals)!=len(set(vals)): raise ReferenceAuthorityError(f"duplicate {w} id")

def _evidence(x,i):
    w=f"evidence[{i}]"; x=_obj(x,w); names={"evidence_id","engagement_kind","subject","performer","source_ref","source_sha256","observed_result","limitations","disclosure_summary"}; _keys(x,names,w)
    kind=_text(x["engagement_kind"],f"{w}.engagement_kind",40)
    if kind not in ENGAGEMENT_KINDS: raise ReferenceAuthorityError(f"{w}.engagement_kind unsupported")
    return {"evidence_id":_id(x["evidence_id"],f"{w}.evidence_id"),"engagement_kind":kind,"subject":_text(x["subject"],f"{w}.subject",160),"performer":_text(x["performer"],f"{w}.performer",160),"source_ref":_ref(x["source_ref"],f"{w}.source_ref"),"source_sha256":_sha(x["source_sha256"],f"{w}.source_sha256"),"observed_result":_text(x["observed_result"],f"{w}.observed_result"),"limitations":_texts(x["limitations"],f"{w}.limitations"),"disclosure_summary":_text(x["disclosure_summary"],f"{w}.disclosure_summary")}

def evidence_digest(record): return record_digest(_evidence(record,0))

def _requirement(x,i,opp):
    w=f"requirements[{i}]"; x=_obj(x,w); _keys(x,{"requirement_id","opportunity_id","label","required_count"},w)
    oid=_id(x["opportunity_id"],f"{w}.opportunity_id")
    if oid!=opp: raise ReferenceAuthorityError(f"{w}.opportunity_id does not match packet opportunity")
    return {"requirement_id":_id(x["requirement_id"],f"{w}.requirement_id"),"opportunity_id":oid,"label":_text(x["label"],f"{w}.label",200),"required_count":_int(x["required_count"],f"{w}.required_count",1,100)}

def _authority(x,i,opp,kind,reqs):
    # kind: disclosure / permission / comparison
    w={"d":"disclosure_authorities","p":"reference_permissions","c":"comparability_authorities"}[kind]+f"[{i}]"; x=_obj(x,w)
    common={"evidence_id","evidence_digest","opportunity_id","expires_at"}
    if kind=="d": names=common|{"authority_id","use_class","status","observed_at","authority_ref","authority_sha256"}
    elif kind=="p": names=common|{"permission_id","requirement_id","status","observed_at","permission_ref","permission_sha256"}
    else: names=common|{"assessment_id","requirement_id","status","assessed_at","assessment_ref","assessment_sha256"}
    _keys(x,names,w); oid=_id(x["opportunity_id"],f"{w}.opportunity_id")
    if oid!=opp: raise ReferenceAuthorityError(f"{w}.opportunity_id does not match packet opportunity")
    out={"evidence_id":_id(x["evidence_id"],f"{w}.evidence_id"),"evidence_digest":_sha(x["evidence_digest"],f"{w}.evidence_digest"),"opportunity_id":oid,"expires_at":_ots(x["expires_at"],f"{w}.expires_at")}
    if kind=="d":
        use=_text(x["use_class"],f"{w}.use_class",32); status=_text(x["status"],f"{w}.status",16)
        if use not in DISCLOSURE_USE_CLASSES or status not in AUTHORITY_STATUSES: raise ReferenceAuthorityError(f"{w} unsupported use/status")
        out.update(authority_id=_id(x["authority_id"],f"{w}.authority_id"),use_class=use,status=status,observed_at=_ts(x["observed_at"],f"{w}.observed_at"),authority_ref=_ref(x["authority_ref"],f"{w}.authority_ref",opaque=True),authority_sha256=_sha(x["authority_sha256"],f"{w}.authority_sha256"))
    else:
        rid=_id(x["requirement_id"],f"{w}.requirement_id")
        if rid not in reqs: raise ReferenceAuthorityError(f"{w}.requirement_id unknown")
        out["requirement_id"]=rid
        if kind=="p":
            status=_text(x["status"],f"{w}.status",16)
            if status not in AUTHORITY_STATUSES: raise ReferenceAuthorityError(f"{w}.status unsupported")
            out.update(permission_id=_id(x["permission_id"],f"{w}.permission_id"),status=status,observed_at=_ts(x["observed_at"],f"{w}.observed_at"),permission_ref=_ref(x["permission_ref"],f"{w}.permission_ref",opaque=True),permission_sha256=_sha(x["permission_sha256"],f"{w}.permission_sha256"))
        else:
            status=_text(x["status"],f"{w}.status",24)
            if status not in COMPARABILITY_STATUSES: raise ReferenceAuthorityError(f"{w}.status unsupported")
            out.update(assessment_id=_id(x["assessment_id"],f"{w}.assessment_id"),status=status,assessed_at=_ts(x["assessed_at"],f"{w}.assessed_at"),assessment_ref=_ref(x["assessment_ref"],f"{w}.assessment_ref",opaque=True),assessment_sha256=_sha(x["assessment_sha256"],f"{w}.assessment_sha256"))
    return out

def normalize_packet(packet):
    p=_obj(packet,"packet"); _keys(p,{"schema_version","opportunity","requirements","evidence","disclosure_authorities","reference_permissions","comparability_authorities"},"packet")
    if p["schema_version"]!=SCHEMA_VERSION: raise ReferenceAuthorityError(f"unsupported schema_version: {p['schema_version']!r}")
    o=_obj(p["opportunity"],"opportunity"); _keys(o,{"opportunity_id","title"},"opportunity"); opp=_id(o["opportunity_id"],"opportunity.opportunity_id")
    req=[_requirement(x,i,opp) for i,x in enumerate(_arr(p["requirements"],"requirements"))]
    ev=[_evidence(x,i) for i,x in enumerate(_arr(p["evidence"],"evidence"))]
    if not req or not ev: raise ReferenceAuthorityError("requirements and evidence must not be empty")
    _unique(req,"requirement_id","requirement"); _unique(ev,"evidence_id","evidence"); reqs={x["requirement_id"] for x in req}; eids={x["evidence_id"] for x in ev}
    ds=[_authority(x,i,opp,"d",reqs) for i,x in enumerate(_arr(p["disclosure_authorities"],"disclosure_authorities"))]
    ps=[_authority(x,i,opp,"p",reqs) for i,x in enumerate(_arr(p["reference_permissions"],"reference_permissions"))]
    cs=[_authority(x,i,opp,"c",reqs) for i,x in enumerate(_arr(p["comparability_authorities"],"comparability_authorities"))]
    _unique(ds,"authority_id","disclosure authority"); _unique(ps,"permission_id","reference permission"); _unique(cs,"assessment_id","comparability authority")
    for rows,name in ((ds,"disclosure authority"),(ps,"reference permission"),(cs,"comparability authority")):
        for r in rows:
            if r["evidence_id"] not in eids: raise ReferenceAuthorityError(f"{name} references unknown evidence_id {r['evidence_id']}")
    return {"schema_version":SCHEMA_VERSION,"opportunity":{"opportunity_id":opp,"title":_text(o["title"],"opportunity.title",240)},"requirements":sorted(req,key=lambda x:x["requirement_id"]),"evidence":sorted(ev,key=lambda x:x["evidence_id"]),"disclosure_authorities":sorted(ds,key=lambda x:x["authority_id"]),"reference_permissions":sorted(ps,key=lambda x:x["permission_id"]),"comparability_authorities":sorted(cs,key=lambda x:x["assessment_id"])}

def _now(v=None):
    d=v if v is not None else datetime.now(timezone.utc)
    if not isinstance(d,datetime) or d.tzinfo is None: raise ReferenceAuthorityError("trusted_now must be timezone-aware datetime")
    return d.astimezone(timezone.utc).replace(microsecond=0)

def _resolve(rows,digest,now,timef,statusf,good,idf,prefix):
    if not rows: return None,f"MISSING_{prefix}"
    if any(_dt(x[timef])>now for x in rows): return None,f"FUTURE_{prefix}"
    rows=sorted(rows,key=lambda x:(_dt(x[timef]),x[idf])); t=_dt(rows[-1][timef]); tied=[x for x in rows if _dt(x[timef])==t]
    if len(tied)>1 and len({canonical_bytes(x) for x in tied})>1: return None,f"AMBIGUOUS_{prefix}"
    x=rows[-1]
    if x["evidence_digest"]!=digest: return None,f"{prefix}_EVIDENCE_DIGEST_MISMATCH"
    if x[statusf]!=good: return None,f"{prefix}_{x[statusf]}"
    if x["expires_at"] is not None and _dt(x["expires_at"])<=now: return None,f"EXPIRED_{prefix}"
    return x,None

def compile_registry(packet,*,trusted_now=None):
    p=normalize_packet(packet); now=_now(trusted_now); opp=p["opportunity"]["opportunity_id"]; ev={x["evidence_id"]:x for x in p["evidence"]}; digs={k:record_digest(v) for k,v in ev.items()}
    ds={k:[] for k in ev}; ps={}; cs={}
    for x in p["disclosure_authorities"]: ds[x["evidence_id"]].append(x)
    for x in p["reference_permissions"]: ps.setdefault((x["evidence_id"],x["requirement_id"]),[]).append(x)
    for x in p["comparability_authorities"]: cs.setdefault((x["evidence_id"],x["requirement_id"]),[]).append(x)
    dstate={}; caps=[]
    for eid,e in sorted(ev.items()):
        d,why=_resolve(ds[eid],digs[eid],now,"observed_at","status","AUTHORIZED","authority_id","DISCLOSURE_AUTHORITY"); dstate[eid]=(d,why)
        if d and d["use_class"] in {"CAPABILITY_NARRATIVE","PROPOSAL_CAPABILITY"}: caps.append({"evidence_id":eid,"engagement_kind":e["engagement_kind"],"subject":e["subject"],"observed_result":e["observed_result"],"limitations":e["limitations"],"disclosure_summary":e["disclosure_summary"],"use_class":d["use_class"],"disclosure_authority_id":d["authority_id"]})
    states=[]; reqout=[]
    for r in p["requirements"]:
        rid=r["requirement_id"]; ready=[]
        for eid,e in sorted(ev.items()):
            reasons=[]; d,dwhy=dstate[eid]
            if e["engagement_kind"]!="CLIENT_ENGAGEMENT": reasons.append("NOT_CLIENT_ENGAGEMENT")
            if not d: reasons.append(dwhy or "MISSING_DISCLOSURE_AUTHORITY")
            elif d["use_class"]!="PROPOSAL_CAPABILITY": reasons.append("DISCLOSURE_NOT_PROPOSAL_CAPABILITY")
            perm,pwhy=_resolve(ps.get((eid,rid),[]),digs[eid],now,"observed_at","status","AUTHORIZED","permission_id","REFERENCE_PERMISSION")
            comp,cwhy=_resolve(cs.get((eid,rid),[]),digs[eid],now,"assessed_at","status","COMPARABLE","assessment_id","COMPARABILITY_AUTHORITY")
            if not perm: reasons.append(pwhy or "MISSING_REFERENCE_PERMISSION")
            if not comp: reasons.append(cwhy or "MISSING_COMPARABILITY_AUTHORITY")
            reasons=sorted(set(reasons)); status="REFERENCE_READY_FOR_OWNER_REVIEW" if not reasons else "HOLD"
            if not reasons: ready.append(eid)
            states.append({"evidence_id":eid,"requirement_id":rid,"status":status,"hold_reasons":reasons,"permission_id":perm["permission_id"] if perm else None,"comparability_assessment_id":comp["assessment_id"] if comp else None})
        ready=sorted(set(ready)); reqout.append({"requirement_id":rid,"label":r["label"],"required_count":r["required_count"],"eligible_reference_ids":ready,"eligible_count":len(ready),"status":"SATISFIED_FOR_OWNER_REVIEW" if len(ready)>=r["required_count"] else "HOLD_INSUFFICIENT_REFERENCES"})
    body={"schema_version":RESULT_SCHEMA_VERSION,"opportunity_id":opp,"evaluated_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"packet_sha256":sha256_hex(canonical_bytes(p)),"capability_examples":caps,"reference_states":sorted(states,key=lambda x:(x["requirement_id"],x["evidence_id"])),"requirements":sorted(reqout,key=lambda x:x["requirement_id"]),"authority":{"customer_contact":False,"reference_contact":False,"reference_disclosure":False,"proposal_submission":False,"contract_commitment":False,"payment_or_accounting":False,"revenue_recognition":False},"truth_boundary":"REFERENCE_READY_FOR_OWNER_REVIEW is evidence state only; it does not authorize disclosure, contact, submission, or representation."}
    body["receipt"]={"schema_version":RECEIPT_SCHEMA_VERSION,"sha256":sha256_hex(canonical_bytes(body))}; return body

def _result(r):
    r=_obj(r,"result"); _keys(r,{"schema_version","opportunity_id","evaluated_at","packet_sha256","capability_examples","reference_states","requirements","authority","truth_boundary","receipt"},"result")
    if r["schema_version"]!=RESULT_SCHEMA_VERSION: raise ReferenceAuthorityError("unsupported result schema")
    _id(r["opportunity_id"],"result.opportunity_id"); _ts(r["evaluated_at"],"result.evaluated_at"); _sha(r["packet_sha256"],"result.packet_sha256")
    rec=_obj(r["receipt"],"result.receipt"); _keys(rec,{"schema_version","sha256"},"result.receipt")
    if rec["schema_version"]!=RECEIPT_SCHEMA_VERSION: raise ReferenceAuthorityError("unsupported receipt schema")
    _sha(rec["sha256"],"result.receipt.sha256"); auth=_obj(r["authority"],"result.authority"); expected={"customer_contact","reference_contact","reference_disclosure","proposal_submission","contract_commitment","payment_or_accounting","revenue_recognition"}; _keys(auth,expected,"result.authority")
    if any(v is not False for v in auth.values()): raise ReferenceAuthorityError("result authority escalation detected")
    _text(r["truth_boundary"],"result.truth_boundary",300); _arr(r["capability_examples"],"result.capability_examples"); _arr(r["reference_states"],"result.reference_states"); _arr(r["requirements"],"result.requirements"); return r

def render_markdown(r):
    r=_result(r); lines=["# Reference authority review","",f"- Opportunity: `{r['opportunity_id']}`",f"- Evaluated at: `{r['evaluated_at']}`",f"- Packet SHA-256: `{r['packet_sha256']}`",f"- Receipt SHA-256: `{r['receipt']['sha256']}`","","## Capability examples authorized for reuse"]
    lines += [f"- `{x['evidence_id']}` — **{x['engagement_kind']}** — {x['disclosure_summary']} ({x['use_class']})" for x in r["capability_examples"]] or ["- None."]
    lines += ["","## Named-reference requirements"]+[f"- `{x['requirement_id']}` — **{x['status']}** — {x['eligible_count']}/{x['required_count']} ready-for-owner-review; eligible: {', '.join(f'`{i}`' for i in x['eligible_reference_ids']) or 'none'}" for x in r["requirements"]]+["","## Per-evidence reference disposition"]
    for x in r["reference_states"]: lines.append(f"- `{x['evidence_id']}` -> `{x['requirement_id']}` — **{x['status']}**"+(f": {', '.join(x['hold_reasons'])}" if x["hold_reasons"] else ""))
    return "\n".join(lines+["","## Authority ceiling","",r["truth_boundary"],""])

def verify_historical(packet,result):
    r=_result(copy.deepcopy(result)); rec=r["receipt"]; body=copy.deepcopy(r); del body["receipt"]
    if sha256_hex(canonical_bytes(body))!=rec["sha256"]: raise ReferenceAuthorityError("receipt SHA-256 mismatch")
    if canonical_bytes(compile_registry(packet,trusted_now=_dt(r["evaluated_at"])))!=canonical_bytes(r): raise ReferenceAuthorityError("result does not replay from packet at recorded evaluation time")
    return {"status":"VERIFIED_HISTORICAL_INTEGRITY_ONLY","receipt_sha256":rec["sha256"],"evaluated_at":r["evaluated_at"]}

def verify_current(packet,result,*,trusted_now=None):
    return {"status":"VERIFIED_WITH_FRESH_CURRENT_REASSESSMENT","historical":verify_historical(packet,result),"current":compile_registry(packet,trusted_now=trusted_now)}

def _read(path):
    try: raw=path.read_bytes()
    except OSError as e: raise ReferenceAuthorityError(f"cannot read {path}: {e}") from e
    if len(raw)>2_000_000: raise ReferenceAuthorityError(f"input too large: {path}")
    return strict_json_loads(raw)

def _write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True); fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
    except Exception:
        try: path.unlink()
        except OSError: pass
        raise

def _cli(argv=None):
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True); c=sub.add_parser("compile"); c.add_argument("packet",type=Path); c.add_argument("--json-out",required=True,type=Path); c.add_argument("--markdown-out",required=True,type=Path); v=sub.add_parser("verify"); v.add_argument("packet",type=Path); v.add_argument("result",type=Path); a=ap.parse_args(argv)
    try:
        if a.cmd=="compile":
            r=compile_registry(_read(a.packet)); _write(a.json_out,canonical_bytes(r)+b"\n"); _write(a.markdown_out,render_markdown(r).encode()); print(json.dumps({"status":"COMPILED","receipt_sha256":r["receipt"]["sha256"]},sort_keys=True)); return 0
        print(json.dumps(verify_current(_read(a.packet),_read(a.result)),sort_keys=True,separators=(",",":"))); return 0
    except ReferenceAuthorityError as e: print(json.dumps({"status":"HOLD","error":str(e)},sort_keys=True),file=sys.stderr); return 2

if __name__=="__main__": raise SystemExit(_cli())
