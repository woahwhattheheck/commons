"""Fail-closed pursuit compiler for Indiana IOT RFP 27-87814.

The carrier separates official public notice observations, the unretained controlling
bid package, discovery mirrors, and internal commercial hypotheses. Nothing in a
mirror or internal file can mint buyer requirements, qualification, submission
authority, or a positive prime/teaming decision.
"""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

OPPORTUNITY_ID = "27-87814"
EVENT_ID = "000670000087814"
AUTHORITIES = {"OFFICIAL_PUBLIC_NOTICE","OFFICIAL_CONTROLLING_PACKAGE","DISCOVERY_MIRROR","VENDOR_PUBLIC","INTERNAL"}
CONTROLLING_FIELDS = {"submission_mechanics","question_deadline","prebid","teaming_rules","mandatory_requirements","evaluation_criteria","security_compliance","pricing_forms","insurance","contract_terms"}
ALLOWED_REQUIREMENT_STATES = {"UNKNOWN","PROVEN","GAP","NOT_APPLICABLE","PROPOSED"}

class GateError(ValueError):
    pass

def _pairs_no_dupes(pairs):
    out={}
    for k,v in pairs:
        if k in out:
            raise GateError(f"duplicate JSON key: {k}")
        out[k]=v
    return out

def _reject_constant(v):
    raise GateError(f"non-finite JSON number: {v}")

def loads_strict(text:str)->Any:
    try:
        return json.loads(text, object_pairs_hook=_pairs_no_dupes, parse_constant=_reject_constant)
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError(str(exc)) from exc

def _str(v:Any,label:str)->str:
    if type(v) is not str or not v.strip() or v != v.strip():
        raise GateError(f"{label} must be a trimmed non-empty string")
    return v

def _bool(v:Any,label:str)->bool:
    if type(v) is not bool:
        raise GateError(f"{label} must be a JSON boolean")
    return v

def _time(v:Any,label:str)->datetime:
    s=_str(v,label)
    try:
        dt=datetime.fromisoformat(s.replace("Z","+00:00"))
    except ValueError as exc:
        raise GateError(f"{label} must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise GateError(f"{label} must include timezone")
    return dt.astimezone(timezone.utc)

def _sources(ledger:Mapping[str,Any]):
    if type(ledger) is not dict or ledger.get("opportunity_id") != OPPORTUNITY_ID or ledger.get("event_id") != EVENT_ID:
        raise GateError("source ledger identity mismatch")
    rows=ledger.get("sources")
    if type(rows) is not list:
        raise GateError("sources must be array")
    out={}
    for i,row in enumerate(rows):
        if type(row) is not dict:
            raise GateError(f"sources[{i}] must be object")
        sid=_str(row.get("id"),f"sources[{i}].id")
        if sid in out:
            raise GateError(f"duplicate source id: {sid}")
        authority=_str(row.get("authority"),f"{sid}.authority")
        if authority not in AUTHORITIES:
            raise GateError(f"unsupported authority: {authority}")
        retained=_bool(row.get("retained"),f"{sid}.retained")
        _str(row.get("url"),f"{sid}.url")
        claims=row.get("claims",{})
        controls=row.get("controls",[])
        if type(claims) is not dict or type(controls) is not list or any(type(x) is not str for x in controls):
            raise GateError(f"{sid} claims/controls malformed")
        if len(controls) != len(set(controls)):
            raise GateError(f"{sid}.controls duplicates")
        if authority != "OFFICIAL_CONTROLLING_PACKAGE" and CONTROLLING_FIELDS.intersection(controls):
            raise GateError(f"{sid} cannot control package-only fields")
        if not retained and controls:
            raise GateError(f"{sid} cannot control fields without retained bytes")
        out[sid]=row
    return out

def _requirements(doc:Mapping[str,Any]):
    if type(doc) is not dict or doc.get("opportunity_id") != OPPORTUNITY_ID:
        raise GateError("requirements identity mismatch")
    rows=doc.get("requirements")
    if type(rows) is not list:
        raise GateError("requirements must be array")
    out={}
    for i,row in enumerate(rows):
        if type(row) is not dict:
            raise GateError(f"requirements[{i}] must be object")
        rid=_str(row.get("id"),f"requirements[{i}].id")
        if rid in out:
            raise GateError(f"duplicate requirement id: {rid}")
        state=_str(row.get("state"),f"{rid}.state")
        if state not in ALLOWED_REQUIREMENT_STATES:
            raise GateError(f"{rid}.state unsupported")
        ev=row.get("evidence")
        if type(ev) is not list or any(type(x) is not str or not x for x in ev):
            raise GateError(f"{rid}.evidence must be string array")
        if state=="PROVEN" and not ev:
            raise GateError(f"{rid} PROVEN requires retained evidence ids")
        if state!="PROVEN" and ev:
            raise GateError(f"{rid} non-PROVEN cannot carry positive evidence")
        out[rid]=row
    return out

def compile_pursuit(ledger:Mapping[str,Any], requirements:Mapping[str,Any], partners:Mapping[str,Any], scope:Mapping[str,Any], *, now:str):
    now_dt=_time(now,"now")
    sources=_sources(ledger)
    reqs=_requirements(requirements)
    if type(partners) is not dict or partners.get("opportunity_id") != OPPORTUNITY_ID:
        raise GateError("partner targets identity mismatch")
    targets=partners.get("targets")
    if type(targets) is not list:
        raise GateError("partner targets must be array")
    for i,target in enumerate(targets):
        if type(target) is not dict:
            raise GateError(f"targets[{i}] malformed")
        _str(target.get("name"),f"targets[{i}].name")
        if target.get("status") != "RESEARCH_TARGET_NO_CONTACT":
            raise GateError("partner target may not claim contact or selection")
        if target.get("contact_authority") is not False:
            raise GateError("partner contact authority must remain false")
    if type(scope) is not dict or scope.get("opportunity_id") != OPPORTUNITY_ID or scope.get("status") != "TEMPLATE_NOT_OFFER":
        raise GateError("paid specialist scope must remain a non-offer template")
    if scope.get("price_usd") is not None:
        raise GateError("template price must remain unset before partner discovery")
    package=next((s for s in sources.values() if s["authority"]=="OFFICIAL_CONTROLLING_PACKAGE"),None)
    package_retained=bool(package and package["retained"])
    proven={rid for rid,row in reqs.items() if row["state"]=="PROVEN"}
    decision="HOLD"
    reasons=[]
    if not package_retained:
        reasons.append("CONTROLLING_PACKAGE_NOT_RETAINED")
    required_prime={"controlling_package","submission_mechanics","questions_and_prebid","teaming_rules","prime_platform_qualification","security_compliance","staffing_capacity","pricing_forms"}
    if package_retained and required_prime.issubset(proven):
        decision="PRIME_REVIEW_READY"
    else:
        reasons.append("PRIME_QUALIFICATION_NOT_PROVEN")
    if package_retained and {"teaming_rules","paid_specialist_workshare"}.issubset(proven):
        decision="TEAMING_REVIEW_READY"
    mirror_intelligence=[{"source_id":sid,"claims":src.get("claims",{}),"authority":"DISCOVERY_ONLY"} for sid,src in sorted(sources.items()) if src["authority"]=="DISCOVERY_MIRROR"]
    work_orders=[]
    if not package_retained:
        work_orders.append({"id":"RETAIN_CONTROLLING_STATE_ZIP","priority":1})
        work_orders.append({"id":"BIND_QUESTION_PREBID_SUBMISSION_TIMELINE","priority":2})
        work_orders.append({"id":"BIND_TEAMING_SECURITY_PRICING_EVALUATION_TERMS","priority":3})
    work_orders.append({"id":"QUALIFY_PLATFORM_OR_PRIME_PARTNER","priority":4})
    work_orders.append({"id":"PACKAGE_PAID_SPECIALIST_WORKSHARE","priority":5})
    external_authority={"buyer_contact":False,"vendor_contact":False,"partner_contact":False,"prebid_registration":False,"question_submission":False,"proposal_submission":False,"pricing_commitment":False,"signature":False,"award":False,"payment":False,"revenue":False}
    return {"schema":"indiana-iot-observability-pursuit/v1","opportunity_id":OPPORTUNITY_ID,"event_id":EVENT_ID,"evaluation_time":now_dt.isoformat().replace("+00:00","Z"),"decision":decision,"reasons":sorted(set(reasons)),"package_retained":package_retained,"mirror_intelligence":mirror_intelligence,"partner_research_targets":[t["name"] for t in targets],"work_orders":work_orders,"external_authority":external_authority}

def _read(path:Path):
    return loads_strict(path.read_text(encoding="utf-8"))

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--ledger",type=Path,required=True)
    ap.add_argument("--requirements",type=Path,required=True)
    ap.add_argument("--partners",type=Path,required=True)
    ap.add_argument("--scope",type=Path,required=True)
    ap.add_argument("--now",required=True)
    ns=ap.parse_args(argv)
    packet=compile_pursuit(_read(ns.ledger),_read(ns.requirements),_read(ns.partners),_read(ns.scope),now=ns.now)
    print(json.dumps(packet,sort_keys=True,separators=(",",":")))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
