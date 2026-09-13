#!/usr/bin/env python3
"""Offline disclosure/reference registry with a host-authenticated authority root."""
from __future__ import annotations

import argparse, copy, hashlib, hmac, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SCHEMA_VERSION = "commons-reference-authority/v2"
TRUST_SCHEMA_VERSION = "commons-reference-authority-trust/v1"
RESULT_SCHEMA_VERSION = "commons-reference-authority-result/v2"
RECEIPT_SCHEMA_VERSION = "commons-reference-authority-receipt/v2"
KEY_ID = "commons-reference-authority-host-v1"
HOST_KEY_ENV = "COMMONS_REFERENCE_AUTHORITY_HMAC_KEY_HEX"
ENGAGEMENT_KINDS = {"CLIENT_ENGAGEMENT","INTERNAL_ENGINEERING","OPEN_SOURCE_CONTRIBUTION","EXTERNAL_REVIEW_PROGRAM","PROCUREMENT_PURSUIT"}
DISCLOSURE_USE_CLASSES = {"INTERNAL_ONLY","CAPABILITY_NARRATIVE","PROPOSAL_CAPABILITY"}
AUTHORITY_STATUSES = {"AUTHORIZED","REVOKED"}
CLASSIFICATION_STATUSES = {"CLASSIFIED","REVOKED"}
COMPARABILITY_STATUSES = {"COMPARABLE","NOT_COMPARABLE"}
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_HEX = re.compile(r"^[0-9a-f]+$")
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
    out={}
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

def _keys(o,names,w):
    names=set(names); got=set(o); missing=names-got; extra=got-names
    if missing: raise ReferenceAuthorityError(f"{w} missing fields: {', '.join(sorted(missing))}")
    if extra: raise ReferenceAuthorityError(f"{w} unknown fields: {', '.join(sorted(extra))}")

def _text(v,w,n=500):
    if not isinstance(v,str) or not v or len(v)>n: raise ReferenceAuthorityError(f"{w} length/type invalid")
    if v!=v.strip(): raise ReferenceAuthorityError(f"{w} must not have surrounding whitespace")
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

def _evidence(x,i=0):
    w=f"evidence[{i}]"; x=_obj(x,w); _keys(x,{"evidence_id","subject","performer","source_ref","source_sha256","observed_result","limitations","disclosure_summary"},w)
    return {"evidence_id":_id(x["evidence_id"],f"{w}.evidence_id"),"subject":_text(x["subject"],f"{w}.subject",160),"performer":_text(x["performer"],f"{w}.performer",160),"source_ref":_ref(x["source_ref"],f"{w}.source_ref"),"source_sha256":_sha(x["source_sha256"],f"{w}.source_sha256"),"observed_result":_text(x["observed_result"],f"{w}.observed_result"),"limitations":_texts(x["limitations"],f"{w}.limitations"),"disclosure_summary":_text(x["disclosure_summary"],f"{w}.disclosure_summary")}

def evidence_digest(record): return record_digest(_evidence(record))

def _opportunity(x):
    x=_obj(x,"opportunity"); _keys(x,{"opportunity_id","title"},"opportunity")
    return {"opportunity_id":_id(x["opportunity_id"],"opportunity.opportunity_id"),"title":_text(x["title"],"opportunity.title",240)}

def opportunity_digest(record): return record_digest(_opportunity(record))

def _requirement(x,i=0,opp=None):
    w=f"requirements[{i}]"; x=_obj(x,w); _keys(x,{"requirement_id","opportunity_id","label","required_count"},w)
    oid=_id(x["opportunity_id"],f"{w}.opportunity_id")
    if opp is not None and oid!=opp: raise ReferenceAuthorityError(f"{w}.opportunity_id does not match packet opportunity")
    return {"requirement_id":_id(x["requirement_id"],f"{w}.requirement_id"),"opportunity_id":oid,"label":_text(x["label"],f"{w}.label",200),"required_count":_int(x["required_count"],f"{w}.required_count",1,100)}

def requirement_digest(record): return record_digest(_requirement(record))

def normalize_packet(packet):
    p=_obj(packet,"packet"); _keys(p,{"schema_version","opportunity","requirements","evidence"},"packet")
    if p["schema_version"]!=SCHEMA_VERSION: raise ReferenceAuthorityError(f"unsupported schema_version: {p['schema_version']!r}")
    o=_opportunity(p["opportunity"]); opp=o["opportunity_id"]
    req=[_requirement(x,i,opp) for i,x in enumerate(_arr(p["requirements"],"requirements"))]
    ev=[_evidence(x,i) for i,x in enumerate(_arr(p["evidence"],"evidence"))]
    if not req or not ev: raise ReferenceAuthorityError("requirements and evidence must not be empty")
    _unique(req,"requirement_id","requirement"); _unique(ev,"evidence_id","evidence")
    return {"schema_version":SCHEMA_VERSION,"opportunity":o,"requirements":sorted(req,key=lambda x:x["requirement_id"]),"evidence":sorted(ev,key=lambda x:x["evidence_id"])}

def _classification(x,i):
    w=f"authority_registry.classifications[{i}]"; x=_obj(x,w); names={"classification_id","evidence_id","evidence_digest","engagement_id","engagement_kind","status","observed_at","expires_at","authority_ref","authority_sha256"}; _keys(x,names,w)
    kind=_text(x["engagement_kind"],f"{w}.engagement_kind",40); status=_text(x["status"],f"{w}.status",16)
    if kind not in ENGAGEMENT_KINDS: raise ReferenceAuthorityError(f"{w}.engagement_kind unsupported")
    if status not in CLASSIFICATION_STATUSES: raise ReferenceAuthorityError(f"{w}.status unsupported")
    return {"classification_id":_id(x["classification_id"],f"{w}.classification_id"),"evidence_id":_id(x["evidence_id"],f"{w}.evidence_id"),"evidence_digest":_sha(x["evidence_digest"],f"{w}.evidence_digest"),"engagement_id":_id(x["engagement_id"],f"{w}.engagement_id"),"engagement_kind":kind,"status":status,"observed_at":_ts(x["observed_at"],f"{w}.observed_at"),"expires_at":_ots(x["expires_at"],f"{w}.expires_at"),"authority_ref":_ref(x["authority_ref"],f"{w}.authority_ref",opaque=True),"authority_sha256":_sha(x["authority_sha256"],f"{w}.authority_sha256")}

def _authority(x,i,kind,reqids):
    plural={"d":"disclosures","p":"permissions","c":"comparabilities"}[kind]; w=f"authority_registry.{plural}[{i}]"; x=_obj(x,w)
    common={"evidence_id","evidence_digest","opportunity_id","opportunity_digest","expires_at"}
    if kind=="d": names=common|{"authority_id","use_class","status","observed_at","authority_ref","authority_sha256"}
    elif kind=="p": names=common|{"permission_id","requirement_id","requirement_digest","status","observed_at","permission_ref","permission_sha256"}
    else: names=common|{"assessment_id","requirement_id","requirement_digest","status","assessed_at","assessment_ref","assessment_sha256"}
    _keys(x,names,w)
    out={"evidence_id":_id(x["evidence_id"],f"{w}.evidence_id"),"evidence_digest":_sha(x["evidence_digest"],f"{w}.evidence_digest"),"opportunity_id":_id(x["opportunity_id"],f"{w}.opportunity_id"),"opportunity_digest":_sha(x["opportunity_digest"],f"{w}.opportunity_digest"),"expires_at":_ots(x["expires_at"],f"{w}.expires_at")}
    if kind=="d":
        use=_text(x["use_class"],f"{w}.use_class",32); status=_text(x["status"],f"{w}.status",16)
        if use not in DISCLOSURE_USE_CLASSES or status not in AUTHORITY_STATUSES: raise ReferenceAuthorityError(f"{w} unsupported use/status")
        out.update(authority_id=_id(x["authority_id"],f"{w}.authority_id"),use_class=use,status=status,observed_at=_ts(x["observed_at"],f"{w}.observed_at"),authority_ref=_ref(x["authority_ref"],f"{w}.authority_ref",opaque=True),authority_sha256=_sha(x["authority_sha256"],f"{w}.authority_sha256"))
    else:
        rid=_id(x["requirement_id"],f"{w}.requirement_id"); out["requirement_id"]=rid; out["requirement_digest"]=_sha(x["requirement_digest"],f"{w}.requirement_digest")
        if rid not in reqids: raise ReferenceAuthorityError(f"{w}.requirement_id unknown to authority registry generation")
        if kind=="p":
            status=_text(x["status"],f"{w}.status",16)
            if status not in AUTHORITY_STATUSES: raise ReferenceAuthorityError(f"{w}.status unsupported")
            out.update(permission_id=_id(x["permission_id"],f"{w}.permission_id"),status=status,observed_at=_ts(x["observed_at"],f"{w}.observed_at"),permission_ref=_ref(x["permission_ref"],f"{w}.permission_ref",opaque=True),permission_sha256=_sha(x["permission_sha256"],f"{w}.permission_sha256"))
        else:
            status=_text(x["status"],f"{w}.status",24)
            if status not in COMPARABILITY_STATUSES: raise ReferenceAuthorityError(f"{w}.status unsupported")
            out.update(assessment_id=_id(x["assessment_id"],f"{w}.assessment_id"),status=status,assessed_at=_ts(x["assessed_at"],f"{w}.assessed_at"),assessment_ref=_ref(x["assessment_ref"],f"{w}.assessment_ref",opaque=True),assessment_sha256=_sha(x["assessment_sha256"],f"{w}.assessment_sha256"))
    return out

def _normalize_registry_body(reg):
    r=_obj(reg,"authority_registry"); _keys(r,{"schema_version","key_id","generation_id","issued_at","requirement_ids","classifications","disclosures","permissions","comparabilities"},"authority_registry")
    if r["schema_version"]!=TRUST_SCHEMA_VERSION: raise ReferenceAuthorityError("unsupported authority registry schema")
    if r["key_id"]!=KEY_ID: raise ReferenceAuthorityError("authority registry key_id mismatch")
    reqids=[_id(x,f"authority_registry.requirement_ids[{i}]") for i,x in enumerate(_arr(r["requirement_ids"],"authority_registry.requirement_ids"))]
    if len(reqids)!=len(set(reqids)): raise ReferenceAuthorityError("duplicate authority registry requirement id")
    cls=[_classification(x,i) for i,x in enumerate(_arr(r["classifications"],"authority_registry.classifications"))]
    ds=[_authority(x,i,"d",set(reqids)) for i,x in enumerate(_arr(r["disclosures"],"authority_registry.disclosures"))]
    ps=[_authority(x,i,"p",set(reqids)) for i,x in enumerate(_arr(r["permissions"],"authority_registry.permissions"))]
    cs=[_authority(x,i,"c",set(reqids)) for i,x in enumerate(_arr(r["comparabilities"],"authority_registry.comparabilities"))]
    _unique(cls,"classification_id","classification"); _unique(ds,"authority_id","disclosure authority"); _unique(ps,"permission_id","permission"); _unique(cs,"assessment_id","comparability")
    return {"schema_version":TRUST_SCHEMA_VERSION,"key_id":KEY_ID,"generation_id":_id(r["generation_id"],"authority_registry.generation_id"),"issued_at":_ts(r["issued_at"],"authority_registry.issued_at"),"requirement_ids":sorted(reqids),"classifications":sorted(cls,key=lambda x:x["classification_id"]),"disclosures":sorted(ds,key=lambda x:x["authority_id"]),"permissions":sorted(ps,key=lambda x:x["permission_id"]),"comparabilities":sorted(cs,key=lambda x:x["assessment_id"])}

def _host_key():
    raw=os.environ.get(HOST_KEY_ENV)
    if not isinstance(raw,str) or len(raw)<64 or len(raw)%2 or not _HEX.fullmatch(raw): raise ReferenceAuthorityError(f"trusted host key unavailable/invalid in {HOST_KEY_ENV}")
    key=bytes.fromhex(raw)
    if len(key)<32: raise ReferenceAuthorityError("trusted host key must be at least 256 bits")
    return key

def _registry_mac(body,key): return hmac.new(key,canonical_bytes(body),hashlib.sha256).hexdigest()

def _sign_registry_for_tests(body,key_hex):
    key=bytes.fromhex(key_hex); norm=_normalize_registry_body(body); return {**norm,"mac":{"algorithm":"HMAC-SHA256","key_id":KEY_ID,"sha256":_registry_mac(norm,key)}}

def normalize_authority_registry(registry):
    r=_obj(registry,"authority_registry_file"); _keys(r,{"schema_version","key_id","generation_id","issued_at","requirement_ids","classifications","disclosures","permissions","comparabilities","mac"},"authority_registry_file")
    body=_normalize_registry_body({k:v for k,v in r.items() if k!="mac"}); mac=_obj(r["mac"],"authority_registry.mac"); _keys(mac,{"algorithm","key_id","sha256"},"authority_registry.mac")
    if mac["algorithm"]!="HMAC-SHA256" or mac["key_id"]!=KEY_ID: raise ReferenceAuthorityError("authority registry MAC algorithm/key mismatch")
    supplied=_sha(mac["sha256"],"authority_registry.mac.sha256"); expected=_registry_mac(body,_host_key())
    if not hmac.compare_digest(supplied,expected): raise ReferenceAuthorityError("authority registry MAC verification failed")
    return {**body,"mac":{"algorithm":"HMAC-SHA256","key_id":KEY_ID,"sha256":supplied}}

def _now(): return datetime.now(timezone.utc).replace(microsecond=0)

def _resolve(rows,digest,now,timef,statusf,good,idf,prefix,oppdig=None,reqdig=None):
    if not rows: return None,f"MISSING_{prefix}"
    if any(_dt(x[timef])>now for x in rows): return None,f"FUTURE_{prefix}"
    rows=sorted(rows,key=lambda x:(_dt(x[timef]),x[idf])); latest=_dt(rows[-1][timef]); tied=[x for x in rows if _dt(x[timef])==latest]
    if len(tied)>1 and len({canonical_bytes(x) for x in tied})>1: return None,f"AMBIGUOUS_{prefix}"
    x=rows[-1]
    if x["evidence_digest"]!=digest: return None,f"{prefix}_EVIDENCE_DIGEST_MISMATCH"
    if oppdig is not None and x["opportunity_digest"]!=oppdig: return None,f"{prefix}_OPPORTUNITY_DIGEST_MISMATCH"
    if reqdig is not None and x["requirement_digest"]!=reqdig: return None,f"{prefix}_REQUIREMENT_DIGEST_MISMATCH"
    if x[statusf]!=good: return None,f"{prefix}_{x[statusf]}"
    if x["expires_at"] is not None and _dt(x["expires_at"])<=now: return None,f"EXPIRED_{prefix}"
    return x,None

def _compile_registry_at(packet,authority_registry,now):
    p=normalize_packet(packet); a=normalize_authority_registry(authority_registry)
    if not isinstance(now,datetime) or now.tzinfo is None: raise ReferenceAuthorityError("internal evaluation time must be timezone-aware")
    now=now.astimezone(timezone.utc).replace(microsecond=0)
    if _dt(a["issued_at"])>now: raise ReferenceAuthorityError("authority registry generation is from the future")
    opp=p["opportunity"]["opportunity_id"]; oppdig=record_digest(p["opportunity"]); reqdigs={x["requirement_id"]:record_digest(x) for x in p["requirements"]}; ev={x["evidence_id"]:x for x in p["evidence"]}; digs={k:record_digest(v) for k,v in ev.items()}
    if set(reqdigs)-set(a["requirement_ids"]): raise ReferenceAuthorityError("authority registry generation does not admit every packet requirement id")
    cls={k:[] for k in ev}; ds={k:[] for k in ev}; ps={}; cs={}
    for x in a["classifications"]:
        if x["evidence_id"] in cls: cls[x["evidence_id"]].append(x)
    for x in a["disclosures"]:
        if x["evidence_id"] in ds and x["opportunity_id"]==opp: ds[x["evidence_id"]].append(x)
    for x in a["permissions"]:
        if x["evidence_id"] in ev and x["opportunity_id"]==opp: ps.setdefault((x["evidence_id"],x["requirement_id"]),[]).append(x)
    for x in a["comparabilities"]:
        if x["evidence_id"] in ev and x["opportunity_id"]==opp: cs.setdefault((x["evidence_id"],x["requirement_id"]),[]).append(x)
    cstate={}; dstate={}; caps=[]
    for eid,e in sorted(ev.items()):
        c,cwhy=_resolve(cls[eid],digs[eid],now,"observed_at","status","CLASSIFIED","classification_id","ENGAGEMENT_CLASSIFICATION"); cstate[eid]=(c,cwhy)
        d,dwhy=_resolve(ds[eid],digs[eid],now,"observed_at","status","AUTHORIZED","authority_id","DISCLOSURE_AUTHORITY",oppdig); dstate[eid]=(d,dwhy)
        if c and d and d["use_class"] in {"CAPABILITY_NARRATIVE","PROPOSAL_CAPABILITY"}: caps.append({"evidence_id":eid,"engagement_id":c["engagement_id"],"engagement_kind":c["engagement_kind"],"subject":e["subject"],"observed_result":e["observed_result"],"limitations":e["limitations"],"disclosure_summary":e["disclosure_summary"],"use_class":d["use_class"],"classification_id":c["classification_id"],"disclosure_authority_id":d["authority_id"]})
    states=[]; reqout=[]
    for r in p["requirements"]:
        rid=r["requirement_id"]; ready_by_engagement={}
        for eid,e in sorted(ev.items()):
            reasons=[]; c,cwhy=cstate[eid]; d,dwhy=dstate[eid]
            if not c: reasons.append(cwhy or "MISSING_ENGAGEMENT_CLASSIFICATION")
            elif c["engagement_kind"]!="CLIENT_ENGAGEMENT": reasons.append("NOT_CLIENT_ENGAGEMENT")
            if not d: reasons.append(dwhy or "MISSING_DISCLOSURE_AUTHORITY")
            elif d["use_class"]!="PROPOSAL_CAPABILITY": reasons.append("DISCLOSURE_NOT_PROPOSAL_CAPABILITY")
            perm,pwhy=_resolve(ps.get((eid,rid),[]),digs[eid],now,"observed_at","status","AUTHORIZED","permission_id","REFERENCE_PERMISSION",oppdig,reqdigs[rid])
            comp,cowhy=_resolve(cs.get((eid,rid),[]),digs[eid],now,"assessed_at","status","COMPARABLE","assessment_id","COMPARABILITY_AUTHORITY",oppdig,reqdigs[rid])
            if not perm: reasons.append(pwhy or "MISSING_REFERENCE_PERMISSION")
            if not comp: reasons.append(cowhy or "MISSING_COMPARABILITY_AUTHORITY")
            reasons=sorted(set(reasons)); status="REFERENCE_READY_FOR_OWNER_REVIEW" if not reasons else "HOLD"; engagement_id=c["engagement_id"] if c else None
            if not reasons: ready_by_engagement.setdefault(engagement_id,[]).append(eid)
            states.append({"evidence_id":eid,"engagement_id":engagement_id,"requirement_id":rid,"status":status,"hold_reasons":reasons,"permission_id":perm["permission_id"] if perm else None,"comparability_assessment_id":comp["assessment_id"] if comp else None})
        refs=[{"engagement_id":gid,"evidence_ids":sorted(eids)} for gid,eids in sorted(ready_by_engagement.items())]
        reqout.append({"requirement_id":rid,"label":r["label"],"required_count":r["required_count"],"eligible_references":refs,"eligible_count":len(refs),"status":"SATISFIED_FOR_OWNER_REVIEW" if len(refs)>=r["required_count"] else "HOLD_INSUFFICIENT_REFERENCES"})
    body={"schema_version":RESULT_SCHEMA_VERSION,"opportunity_id":opp,"evaluated_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"packet_sha256":sha256_hex(canonical_bytes(p)),"authority_registry_sha256":sha256_hex(canonical_bytes(a)),"authority_registry_generation_id":a["generation_id"],"capability_examples":caps,"reference_states":sorted(states,key=lambda x:(x["requirement_id"],x["evidence_id"])),"requirements":sorted(reqout,key=lambda x:x["requirement_id"]),"authority":{"customer_contact":False,"reference_contact":False,"reference_disclosure":False,"proposal_submission":False,"contract_commitment":False,"payment_or_accounting":False,"revenue_recognition":False},"truth_boundary":"REFERENCE_READY_FOR_OWNER_REVIEW is authenticated evidence state only; it does not authorize disclosure, contact, submission, or representation."}
    body["receipt"]={"schema_version":RECEIPT_SCHEMA_VERSION,"sha256":sha256_hex(canonical_bytes(body))}; return body

def compile_registry(packet,authority_registry): return _compile_registry_at(packet,authority_registry,_now())

def _result(r):
    r=_obj(r,"result"); _keys(r,{"schema_version","opportunity_id","evaluated_at","packet_sha256","authority_registry_sha256","authority_registry_generation_id","capability_examples","reference_states","requirements","authority","truth_boundary","receipt"},"result")
    if r["schema_version"]!=RESULT_SCHEMA_VERSION: raise ReferenceAuthorityError("unsupported result schema")
    _id(r["opportunity_id"],"result.opportunity_id"); _ts(r["evaluated_at"],"result.evaluated_at"); _sha(r["packet_sha256"],"result.packet_sha256"); _sha(r["authority_registry_sha256"],"result.authority_registry_sha256"); _id(r["authority_registry_generation_id"],"result.authority_registry_generation_id")
    rec=_obj(r["receipt"],"result.receipt"); _keys(rec,{"schema_version","sha256"},"result.receipt")
    if rec["schema_version"]!=RECEIPT_SCHEMA_VERSION: raise ReferenceAuthorityError("unsupported receipt schema")
    _sha(rec["sha256"],"result.receipt.sha256"); auth=_obj(r["authority"],"result.authority"); expected={"customer_contact","reference_contact","reference_disclosure","proposal_submission","contract_commitment","payment_or_accounting","revenue_recognition"}; _keys(auth,expected,"result.authority")
    if any(v is not False for v in auth.values()): raise ReferenceAuthorityError("result authority escalation detected")
    _text(r["truth_boundary"],"result.truth_boundary",300); _arr(r["capability_examples"],"result.capability_examples"); _arr(r["reference_states"],"result.reference_states"); _arr(r["requirements"],"result.requirements"); return r

def render_markdown(r):
    r=_result(r); lines=["# Reference authority review","",f"- Opportunity: `{r['opportunity_id']}`",f"- Evaluated at: `{r['evaluated_at']}`",f"- Packet SHA-256: `{r['packet_sha256']}`",f"- Trusted authority generation: `{r['authority_registry_generation_id']}`",f"- Authority registry SHA-256: `{r['authority_registry_sha256']}`",f"- Receipt SHA-256: `{r['receipt']['sha256']}`","","## Capability examples authorized for reuse"]
    lines += [f"- `{x['evidence_id']}` / engagement `{x['engagement_id']}` — **{x['engagement_kind']}** — {x['disclosure_summary']} ({x['use_class']})" for x in r["capability_examples"]] or ["- None."]
    lines += ["","## Named-reference requirements"]
    for x in r["requirements"]:
        ids=", ".join(f"`{q['engagement_id']}`" for q in x["eligible_references"]) or "none"; lines.append(f"- `{x['requirement_id']}` — **{x['status']}** — {x['eligible_count']}/{x['required_count']} distinct trusted engagements; eligible: {ids}")
    lines += ["","## Per-evidence reference disposition"]
    for x in r["reference_states"]: lines.append(f"- `{x['evidence_id']}` -> `{x['requirement_id']}` — **{x['status']}**"+(f": {', '.join(x['hold_reasons'])}" if x["hold_reasons"] else ""))
    return "\n".join(lines+["","## Authority ceiling","",r["truth_boundary"],""])

def verify_historical(packet,historical_authority_registry,result):
    r=_result(copy.deepcopy(result)); rec=r["receipt"]; body=copy.deepcopy(r); del body["receipt"]
    if sha256_hex(canonical_bytes(body))!=rec["sha256"]: raise ReferenceAuthorityError("receipt SHA-256 mismatch")
    a=normalize_authority_registry(historical_authority_registry)
    if sha256_hex(canonical_bytes(a))!=r["authority_registry_sha256"] or a["generation_id"]!=r["authority_registry_generation_id"]: raise ReferenceAuthorityError("historical authority registry generation mismatch")
    if canonical_bytes(_compile_registry_at(packet,historical_authority_registry,_dt(r["evaluated_at"])))!=canonical_bytes(r): raise ReferenceAuthorityError("result does not replay from packet + trusted authority generation at recorded evaluation time")
    return {"status":"VERIFIED_HISTORICAL_INTEGRITY_ONLY","receipt_sha256":rec["sha256"],"evaluated_at":r["evaluated_at"],"authority_registry_generation_id":a["generation_id"]}

def _verify_current_at(packet,historical_authority_registry,current_authority_registry,result,now):
    return {"status":"VERIFIED_WITH_FRESH_HOST_TIME_REASSESSMENT","historical":verify_historical(packet,historical_authority_registry,result),"current":_compile_registry_at(packet,current_authority_registry,now)}

def verify_current(packet,historical_authority_registry,current_authority_registry,result):
    return _verify_current_at(packet,historical_authority_registry,current_authority_registry,result,_now())

def _read(path):
    try: raw=path.read_bytes()
    except OSError as e: raise ReferenceAuthorityError(f"cannot read {path}: {e}") from e
    if len(raw)>2_000_000: raise ReferenceAuthorityError(f"input too large: {path}")
    return strict_json_loads(raw)

def _write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True); fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())

def _cli(argv=None):
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    c=sub.add_parser("compile"); c.add_argument("packet",type=Path); c.add_argument("authority_registry",type=Path); c.add_argument("--json-out",required=True,type=Path); c.add_argument("--markdown-out",required=True,type=Path)
    v=sub.add_parser("verify"); v.add_argument("packet",type=Path); v.add_argument("historical_authority_registry",type=Path); v.add_argument("result",type=Path); v.add_argument("--current-authority-registry",type=Path)
    a=ap.parse_args(argv)
    try:
        if a.cmd=="compile":
            if a.json_out.exists() or a.markdown_out.exists(): raise ReferenceAuthorityError("output path already exists")
            r=compile_registry(_read(a.packet),_read(a.authority_registry)); _write(a.json_out,canonical_bytes(r)+b"\n"); _write(a.markdown_out,render_markdown(r).encode()); print(json.dumps({"status":"COMPILED","receipt_sha256":r["receipt"]["sha256"]},sort_keys=True)); return 0
        hist=_read(a.historical_authority_registry); cur=_read(a.current_authority_registry) if a.current_authority_registry else hist
        print(json.dumps(verify_current(_read(a.packet),hist,cur,_read(a.result)),sort_keys=True,separators=(",",":"))); return 0
    except ReferenceAuthorityError as e: print(json.dumps({"status":"HOLD","error":str(e)},sort_keys=True),file=sys.stderr); return 2

if __name__=="__main__": raise SystemExit(_cli())
