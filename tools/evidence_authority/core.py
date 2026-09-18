"""Source-bound authority compiler.

Candidate claims are untrusted. Positive authority is derived only from exact
retained source bytes admitted by a separately pinned manifest root.
"""
from __future__ import annotations
from datetime import datetime as _DateTime, timezone as _Timezone
import re
from typing import Any, Mapping
from .codec import (
    AuthorityError, MAX_TOTAL_SOURCE_BYTES, SHA256_RE, canonical_bytes,
    loads_strict_json_bytes, sha256_bytes, sha256_value, strict_int, strict_text,
)

MANIFEST_SCHEMA="evidence-authority/manifest/v1"
SOURCE_SCHEMA="evidence-authority/source-record/v1"
CANDIDATE_SCHEMA="evidence-authority/candidate/v1"
RECEIPT_SCHEMA="evidence-authority/receipt/v1"
IMPLEMENTATION_CONTRACT="source-bound-authority-kernel/v1"
AUTHORITY_CLASSES=frozenset({"PROVIDER_AUTHENTICATED","BUYER_AUTHENTICATED","ISSUER_AUTHENTICATED"})
SCOPES=frozenset({"ACCOUNT","PRODUCT","MODEL","SESSION","OPPORTUNITY","DOCUMENT","CUSTOM"})
_PATH_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


def _exact(obj:Any,keys:set[str],label:str)->dict[str,Any]:
    if not isinstance(obj,dict): raise AuthorityError(f"{label} must be an object")
    got=set(obj)
    if got!=keys:
        missing=sorted(keys-got);extra=sorted(got-keys)
        raise AuthorityError(f"{label} keys mismatch missing={missing} extra={extra}")
    return obj

def _path(value:Any,label:str,_text=strict_text,_pattern=_PATH_RE)->str:
    value=_text(value,label)
    if not _pattern.fullmatch(value) or value.startswith("/") or "\\" in value:
        raise AuthorityError(f"{label} is not a canonical relative path")
    parts=value.split("/")
    if any(part in("",".","..") for part in parts): raise AuthorityError(f"{label} contains path aliasing")
    return value

def _sha(value:Any,label:str,_text=strict_text,_pattern=SHA256_RE)->str:
    value=_text(value,label)
    if not _pattern.fullmatch(value): raise AuthorityError(f"{label} must be lowercase SHA-256 hex")
    return value

def _timestamp(value:Any,label:str,_dt=_DateTime,_utc=_Timezone.utc,_text=strict_text,_pattern=re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"))->_DateTime:
    value=_text(value,label)
    if not _pattern.fullmatch(value):
        raise AuthorityError(f"{label} must be canonical UTC seconds")
    try: parsed=_dt.fromisoformat(value[:-1]+"+00:00")
    except ValueError as exc: raise AuthorityError(f"{label} is invalid UTC") from exc
    return parsed.astimezone(_utc)
def _format_ts(value:_DateTime,_utc=_Timezone.utc)->str: return value.astimezone(_utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_manifest(raw:bytes,pinned_root_sha256:str,_sha_check=_sha,_digest=sha256_bytes,_loads=loads_strict_json_bytes,_canon=canonical_bytes,_exact_keys=_exact,_int=strict_int,_path_check=_path,_schema=MANIFEST_SCHEMA):
    root=_sha_check(pinned_root_sha256,"pinned_root_sha256")
    if _digest(raw)!=root: raise AuthorityError("authority manifest does not match out-of-band pinned root")
    obj=_loads(raw,label="authority manifest")
    if _canon(obj)!=raw: raise AuthorityError("authority manifest bytes are not canonical JSON")
    _exact_keys(obj,{"schema","max_age_seconds","sources"},"authority manifest")
    if obj["schema"]!=_schema: raise AuthorityError("unsupported authority manifest schema")
    max_age=_int(obj["max_age_seconds"],"manifest.max_age_seconds",minimum=1,maximum=315_576_000)
    rows=obj["sources"]
    if not isinstance(rows,list) or not rows or len(rows)>64: raise AuthorityError("manifest.sources must contain 1..64 entries")
    normalized=[];seen=set()
    for i,row in enumerate(rows):
        _exact_keys(row,{"path","sha256"},f"manifest.sources[{i}]")
        path=_path_check(row["path"],f"manifest.sources[{i}].path")
        digest=_sha_check(row["sha256"],f"manifest.sources[{i}].sha256")
        if path in seen: raise AuthorityError("duplicate manifest source path")
        seen.add(path);normalized.append({"path":path,"sha256":digest})
    if normalized!=sorted(normalized,key=lambda x:x["path"]): raise AuthorityError("manifest.sources must be sorted by canonical path")
    return {"schema":_schema,"max_age_seconds":max_age,"sources":normalized},root


def _validate_source(raw:bytes,*,path:str,expected_sha256:str,_digest=sha256_bytes,_loads=loads_strict_json_bytes,_canon=canonical_bytes,_exact_keys=_exact,_text=strict_text,_int=strict_int,_ts=_timestamp,_schema=SOURCE_SCHEMA,_authorities=AUTHORITY_CLASSES,_scopes=SCOPES):
    if _digest(raw)!=expected_sha256: raise AuthorityError(f"source digest mismatch: {path}")
    obj=_loads(raw,label=f"source {path}")
    if _canon(obj)!=raw: raise AuthorityError(f"source bytes are not canonical JSON: {path}")
    keys={"schema","record_id","authority_class","issuer","subject","claim_kind","scope","generation","issued_at_utc","observed_at_utc","valid_until_utc","claim_payload"}
    _exact_keys(obj,keys,f"source {path}")
    if obj["schema"]!=_schema: raise AuthorityError(f"unsupported source schema: {path}")
    record_id=_text(obj["record_id"],f"source {path}.record_id")
    authority=_text(obj["authority_class"],f"source {path}.authority_class")
    if authority not in _authorities: raise AuthorityError(f"source {path}.authority_class is unsupported")
    issuer=_text(obj["issuer"],f"source {path}.issuer")
    subject=_text(obj["subject"],f"source {path}.subject")
    kind=_text(obj["claim_kind"],f"source {path}.claim_kind")
    scope=_text(obj["scope"],f"source {path}.scope")
    if scope not in _scopes: raise AuthorityError(f"source {path}.scope is unsupported")
    generation=_int(obj["generation"],f"source {path}.generation",minimum=1)
    issued=_ts(obj["issued_at_utc"],f"source {path}.issued_at_utc")
    observed=_ts(obj["observed_at_utc"],f"source {path}.observed_at_utc")
    if observed<issued: raise AuthorityError(f"source {path} observed_at precedes issued_at")
    valid_raw=obj["valid_until_utc"]
    valid=None if valid_raw is None else _ts(valid_raw,f"source {path}.valid_until_utc")
    if valid is not None and valid<issued: raise AuthorityError(f"source {path} valid_until precedes issued_at")
    payload=obj["claim_payload"]
    if not isinstance(payload,dict): raise AuthorityError(f"source {path}.claim_payload must be an object")
    _canon(payload)
    return {
        "record_id":record_id,"authority_class":authority,"issuer":issuer,"subject":subject,
        "claim_kind":kind,"scope":scope,"generation":generation,"issued_at":issued,"observed_at":observed,
        "valid_until":valid,"claim_payload":payload,"source_path":path,"source_sha256":expected_sha256,
    }


def _validate_candidate(candidate:Any,_exact_keys=_exact,_text=strict_text,_int=strict_int,_canon=canonical_bytes,_schema=CANDIDATE_SCHEMA,_scopes=SCOPES)->dict[str,Any]:
    keys={"schema","record_id","issuer","subject","claim_kind","scope","generation","claim_payload"}
    _exact_keys(candidate,keys,"candidate")
    if candidate["schema"]!=_schema: raise AuthorityError("unsupported candidate schema")
    out={"schema":_schema}
    for key in("record_id","issuer","subject","claim_kind"):
        out[key]=_text(candidate[key],f"candidate.{key}")
    out["scope"]=_text(candidate["scope"],"candidate.scope")
    if out["scope"] not in _scopes: raise AuthorityError("candidate.scope is unsupported")
    out["generation"]=_int(candidate["generation"],"candidate.generation",minimum=1)
    if not isinstance(candidate["claim_payload"],dict): raise AuthorityError("candidate.claim_payload must be an object")
    _canon(candidate["claim_payload"]);out["claim_payload"]=candidate["claim_payload"]
    return out


def _load_context(candidate:Any,manifest_bytes:bytes,sources:Mapping[str,bytes],pinned_root_sha256:str,_manifest=_validate_manifest,_source=_validate_source,_candidate=_validate_candidate,_path_check=_path,_canon=canonical_bytes,_value_hash=sha256_value,_max_total=MAX_TOTAL_SOURCE_BYTES):
    manifest,root=_manifest(manifest_bytes,pinned_root_sha256)
    if not isinstance(sources,Mapping): raise AuthorityError("sources must be a path->bytes mapping")
    expected=[row["path"] for row in manifest["sources"]]
    actual=sorted(sources.keys())
    for key in actual: _path_check(key,"source mapping path")
    if actual!=expected: raise AuthorityError("retained source inventory is not exactly the pinned manifest inventory")
    total=0;records={};source_set=[]
    expected_sha={row["path"]:row["sha256"] for row in manifest["sources"]}
    for path in expected:
        raw=sources[path]
        if not isinstance(raw,bytes): raise AuthorityError(f"source {path} must be exact bytes")
        total+=len(raw)
        if total>_max_total: raise AuthorityError("retained source byte bound exceeded")
        rec=_source(raw,path=path,expected_sha256=expected_sha[path])
        if rec["record_id"] in records: raise AuthorityError("duplicate authority record_id across retained sources")
        records[rec["record_id"]]=rec
        source_set.append({"path":path,"sha256":expected_sha[path]})
    cand=_candidate(candidate)
    rec=records.get(cand["record_id"])
    match=False
    if rec is not None:
        match=(cand["issuer"]==rec["issuer"] and cand["subject"]==rec["subject"] and cand["claim_kind"]==rec["claim_kind"] and cand["scope"]==rec["scope"] and cand["generation"]==rec["generation"] and _canon(cand["claim_payload"])==_canon(rec["claim_payload"]))
    fact=None if rec is None else {
        "record_id":rec["record_id"],"authority_class":rec["authority_class"],"issuer":rec["issuer"],"subject":rec["subject"],
        "claim_kind":rec["claim_kind"],"scope":rec["scope"],"generation":rec["generation"],
        "claim_payload_sha256":_value_hash(rec["claim_payload"]),"source_path":rec["source_path"],"source_sha256":rec["source_sha256"],
    }
    return {"manifest":manifest,"root":root,"source_set":source_set,"candidate":cand,"record":rec,"claim_match":match,"authority_fact":fact}


def _base_receipt(ctx:dict[str,Any],*,mode:str,evaluated_at_utc:str|None,state:str,current:bool,_hash=sha256_value,_schema=RECEIPT_SCHEMA,_contract=IMPLEMENTATION_CONTRACT)->dict[str,Any]:
    cand=ctx["candidate"]
    receipt={
        "schema":_schema,"implementation_contract":_contract,"evaluation_mode":mode,
        "evaluated_at_utc":evaluated_at_utc,"state":state,"candidate_sha256":_hash(cand),
        "authority_root_sha256":ctx["root"],"manifest_sha256":ctx["root"],"source_set_sha256":_hash(ctx["source_set"]),
        "claim_match":ctx["claim_match"],"authority_fact":ctx["authority_fact"] if ctx["claim_match"] else None,
        "current_authority":bool(current),"external_side_effects_authorized":False,
    }
    receipt["receipt_sha256"]=_hash(receipt)
    return receipt


def compile_integrity(candidate:Any,manifest_bytes:bytes,sources:Mapping[str,bytes],pinned_root_sha256:str,_load=_load_context,_base=_base_receipt)->dict[str,Any]:
    ctx=_load(candidate,manifest_bytes,sources,pinned_root_sha256)
    state="HISTORICAL_AUTHORITY_FACT" if ctx["claim_match"] else ("HOLD_RECORD_NOT_FOUND" if ctx["record"] is None else "HOLD_CLAIM_MISMATCH")
    return _base(ctx,mode="HISTORICAL_INTEGRITY_ONLY",evaluated_at_utc=None,state=state,current=False)


def _current_state(ctx:dict[str,Any],now:_DateTime)->str:
    if ctx["record"] is None: return "HOLD_RECORD_NOT_FOUND"
    if not ctx["claim_match"]: return "HOLD_CLAIM_MISMATCH"
    rec=ctx["record"]
    if rec["issued_at"]>now or rec["observed_at"]>now: return "HOLD_FUTURE"
    if rec["valid_until"] is not None and rec["valid_until"]<now: return "HOLD_EXPIRED"
    if (now-rec["observed_at"]).total_seconds()>ctx["manifest"]["max_age_seconds"]: return "HOLD_STALE"
    return "CURRENT_AUTHORITY"


def _validate_receipt(receipt:Any,_exact_keys=_exact,_ts=_timestamp,_sha_check=_sha,_hash=sha256_value,_schema=RECEIPT_SCHEMA,_contract=IMPLEMENTATION_CONTRACT)->dict[str,Any]:
    keys={"schema","implementation_contract","evaluation_mode","evaluated_at_utc","state","candidate_sha256","authority_root_sha256","manifest_sha256","source_set_sha256","claim_match","authority_fact","current_authority","external_side_effects_authorized","receipt_sha256"}
    _exact_keys(receipt,keys,"receipt")
    if receipt["schema"]!=_schema or receipt["implementation_contract"]!=_contract: raise AuthorityError("unsupported receipt contract")
    if receipt["evaluation_mode"] not in {"CURRENT_PROCESS_UTC","HISTORICAL_INTEGRITY_ONLY"}: raise AuthorityError("unsupported receipt evaluation mode")
    if receipt["evaluation_mode"]=="CURRENT_PROCESS_UTC": _ts(receipt["evaluated_at_utc"],"receipt.evaluated_at_utc")
    elif receipt["evaluated_at_utc"] is not None: raise AuthorityError("historical receipt must not claim evaluation time")
    for key in("candidate_sha256","authority_root_sha256","manifest_sha256","source_set_sha256","receipt_sha256"): _sha_check(receipt[key],f"receipt.{key}")
    if not isinstance(receipt["claim_match"],bool) or not isinstance(receipt["current_authority"],bool) or not isinstance(receipt["external_side_effects_authorized"],bool): raise AuthorityError("receipt booleans are malformed")
    if receipt["external_side_effects_authorized"]: raise AuthorityError("receipt authority ceiling violated")
    unsigned=dict(receipt);claimed=unsigned.pop("receipt_sha256")
    if _hash(unsigned)!=claimed: raise AuthorityError("receipt_sha256 mismatch")
    return dict(receipt)


def _construct_current_api(_clock_cls:type[_DateTime]=_DateTime,_utc=_Timezone.utc,_load=_load_context,_state=_current_state,_base=_base_receipt,_validate=_validate_receipt,_parse=_timestamp,_format=_format_ts,_integrity=compile_integrity):
    def _receipt_at(candidate,manifest_bytes,sources,pinned_root_sha256,now):
        now=now.astimezone(_utc).replace(microsecond=0)
        ctx=_load(candidate,manifest_bytes,sources,pinned_root_sha256)
        state=_state(ctx,now)
        return _base(ctx,mode="CURRENT_PROCESS_UTC",evaluated_at_utc=_format(now),state=state,current=(state=="CURRENT_AUTHORITY"))
    def compile_current(candidate,manifest_bytes,sources,pinned_root_sha256):
        return _receipt_at(candidate,manifest_bytes,sources,pinned_root_sha256,_clock_cls.now(_utc))
    def verify_receipt(candidate,manifest_bytes,sources,pinned_root_sha256,receipt):
        checked=_validate(receipt)
        if checked["evaluation_mode"]=="HISTORICAL_INTEGRITY_ONLY": expected=_integrity(candidate,manifest_bytes,sources,pinned_root_sha256)
        else: expected=_receipt_at(candidate,manifest_bytes,sources,pinned_root_sha256,_parse(checked["evaluated_at_utc"],"receipt.evaluated_at_utc"))
        if expected!=checked: raise AuthorityError("receipt semantic replay mismatch")
        return {"integrity_valid":True,"current_authority":False,"external_side_effects_authorized":False}
    return compile_current,verify_receipt

compile_current,verify_receipt=_construct_current_api()
del _construct_current_api
