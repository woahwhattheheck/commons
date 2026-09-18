#!/usr/bin/env python3
"""Fail-closed BPHC vendor-pool completeness gate; never submits or certifies."""
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SOURCE_SCHEMA="bphc.vendor_pool.source_snapshot/v1"; OWNER_SCHEMA="bphc.vendor_pool.owner_inputs/v1"
RECEIPT_SCHEMA="bphc.vendor_pool.preflight_receipt/v1"; READY="READY_FOR_OWNER_SUBMISSION_REVIEW"
OWNER_HOLD="OWNER_INPUT_REQUIRED"; SOURCE_HOLD="SOURCE_REFRESH_REQUIRED"; DEADLINE_HOLD="DEADLINE_PASSED"
MAX_SOURCE_AGE=timedelta(days=7); ALLOWED_EXPERIENCE={"public_health","nonprofit","government_funded"}
PLACEHOLDER=re.compile(r"(?:OWNER_INPUT_REQUIRED|\bTBD\b|\bTODO\b|<[^>]+>)",re.I)
AUTHORITY={k:False for k in ("email_or_external_submission_authorized","external_contact_authorized","qualification_assertion_authorized","legal_or_compliance_certification_authorized","pricing_commitment_authorized","reference_contact_authorized","contract_or_signature_authorized","award_or_revenue_claim_authorized")}
class PreflightError(ValueError): pass

def _bad(v:str): raise PreflightError(f"non-finite JSON number {v!r} is forbidden")
def _pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise PreflightError(f"duplicate JSON key: {k}")
        out[k]=v
    return out

def load_json_bytes(raw:bytes,label:str):
    try: text=raw.decode("utf-8")
    except UnicodeDecodeError as e: raise PreflightError(f"{label} must be UTF-8") from e
    try: value=json.loads(text,object_pairs_hook=_pairs,parse_constant=_bad)
    except PreflightError: raise
    except json.JSONDecodeError as e: raise PreflightError(f"{label} is invalid JSON") from e
    if not isinstance(value,dict): raise PreflightError(f"{label} must be an object")
    return value

def canonical_bytes(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def digest(v): return hashlib.sha256(v if isinstance(v,bytes) else canonical_bytes(v)).hexdigest()
def parse_utc(v,label):
    if not isinstance(v,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",v): raise PreflightError(f"{label} must be canonical UTC YYYY-MM-DDTHH:MM:SSZ")
    try: return datetime.strptime(v,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as e: raise PreflightError(f"{label} is not a valid UTC timestamp") from e
def trusted_time(v):
    if not isinstance(v,datetime) or v.tzinfo is None or v.utcoffset() is None: raise PreflightError("trusted_now must be timezone-aware")
    return v.astimezone(timezone.utc).replace(microsecond=0)
def _int(v): return isinstance(v,int) and not isinstance(v,bool)
def _text(v): return isinstance(v,str) and bool(v.strip()) and not PLACEHOLDER.search(v)
def _placeholders(v,path="owner"):
    if isinstance(v,str): return [path] if PLACEHOLDER.search(v) else []
    if isinstance(v,dict): return sum((_placeholders(x,f"{path}.{k}") for k,x in v.items()),[])
    if isinstance(v,list): return sum((_placeholders(x,f"{path}[{i}]") for i,x in enumerate(v)),[])
    return []

def _source(s):
    if s.get("schema")!=SOURCE_SCHEMA or s.get("buyer")!="Boston Public Health Commission": raise PreflightError("source identity mismatch")
    tracks=s.get("tracks"); qs=s.get("track_questions")
    if not isinstance(tracks,list) or len(tracks)!=4 or not all(_text(x) for x in tracks): raise PreflightError("source tracks are malformed")
    if not isinstance(qs,dict) or set(qs)!=set(tracks) or not all(isinstance(x,list) and len(x)==4 and all(_text(q) for q in x) for x in qs.values()): raise PreflightError("source track questions are malformed")
    pdf=s.get("rfp_pdf_sha256")
    if pdf is not None and (not isinstance(pdf,str) or not re.fullmatch(r"[0-9a-f]{64}",pdf)): raise PreflightError("rfp_pdf_sha256 must be null or canonical SHA-256")
    if s.get("rfp_pdf_bytes_locally_acquired") is not False and pdf is None: raise PreflightError("source cannot claim local PDF bytes without a digest")
    parse_utc(s.get("checked_at"),"source.checked_at")
    try: datetime.strptime(s.get("proposal_due_date",""),"%Y-%m-%d")
    except (TypeError,ValueError) as e: raise PreflightError("proposal_due_date must be YYYY-MM-DD") from e
    if s.get("inclusion_guarantees_work") is not False: raise PreflightError("source must preserve no-guaranteed-work statement")
    if not isinstance(s.get("authority"),dict) or any(x is not False for x in s["authority"].values()): raise PreflightError("source authority must remain entirely false")

def _owner(o):
    if o.get("schema")!=OWNER_SCHEMA: raise PreflightError("unsupported owner-input schema")
    types=(("organization",dict),("selected_tracks",list),("qualifying_experience",list),("references",list),("team",list),("pricing",dict),("track_answers",dict),("page_plan",dict))
    for k,t in types:
        if not isinstance(o.get(k),t): raise PreflightError(f"{k} must be {t.__name__}")

def evaluate(s,o,*,trusted_now):
    _source(s); _owner(o); now=trusted_time(trusted_now); checked=parse_utc(s["checked_at"],"source.checked_at")
    if checked>now: raise PreflightError("source checked_at cannot be in the future")
    blockers=[]; warnings=[]; state=OWNER_HOLD
    if now-checked>MAX_SOURCE_AGE: state=SOURCE_HOLD; blockers.append("SOURCE_SNAPSHOT_OLDER_THAN_7_DAYS")
    ph=_placeholders(o)
    if ph: blockers.append("PLACEHOLDERS_REMAIN:"+",".join(sorted(ph)))
    org=o["organization"]
    for k in ("legal_name","mission","website"):
        if not _text(org.get(k)): blockers.append(f"ORGANIZATION_{k.upper()}_REQUIRED")
    if not _text(org.get("boston_community_knowledge")): warnings.append("BOSTON_COMMUNITY_KNOWLEDGE_NOT_SUPPORTED_OR_NOT_SUPPLIED")
    selected=o["selected_tracks"]; allowed=set(s["tracks"])
    if not selected: blockers.append("SELECT_AT_LEAST_ONE_TRACK")
    elif len(selected)!=len(set(selected)): blockers.append("DUPLICATE_SELECTED_TRACK")
    unknown=sorted(str(x) for x in selected if x not in allowed)
    if unknown: blockers.append("UNKNOWN_SELECTED_TRACK:"+",".join(unknown))
    if o.get("track_count_ambiguity_reviewed") is not True: blockers.append("REVIEW_FOUR_TRACKS_VS_ALL_THREE_SOURCE_AMBIGUITY")
    if o.get("deadline_time_label_reviewed") is not True: blockers.append("REVIEW_SOURCE_EST_TIMEZONE_LABEL")
    qualifying=[]
    for i,row in enumerate(o["qualifying_experience"]):
        if not isinstance(row,dict): blockers.append(f"EXPERIENCE_{i}_MALFORMED"); continue
        req=("engagement_name","category","client_type","scope","outcomes","evidence_ref")
        if not all(_text(row.get(k)) for k in req): blockers.append(f"EXPERIENCE_{i}_INCOMPLETE"); continue
        if row["category"] in ALLOWED_EXPERIENCE: qualifying.append(row)
    if not qualifying: blockers.append("QUALIFYING_PUBLIC_HEALTH_NONPROFIT_OR_GOVERNMENT_EXPERIENCE_REQUIRED")
    refs=o["references"]
    if len(refs)<2: blockers.append("TWO_PROFESSIONAL_REFERENCES_REQUIRED")
    ids=[]
    for i,row in enumerate(refs):
        if not isinstance(row,dict) or not all(_text(row.get(k)) for k in ("reference_id","organization","relationship","contact_delivery_plan")): blockers.append(f"REFERENCE_{i}_INCOMPLETE")
        else: ids.append(row["reference_id"])
    if len(ids)!=len(set(ids)): blockers.append("REFERENCE_IDS_MUST_BE_UNIQUE")
    if not o["team"]: blockers.append("TEAM_AND_STAFFING_REQUIRED")
    for i,row in enumerate(o["team"]):
        if not isinstance(row,dict) or not all(_text(row.get(k)) for k in ("role","staffing_summary","evidence_ref")): blockers.append(f"TEAM_{i}_INCOMPLETE")
    p=o["pricing"]
    if not _text(p.get("basis")) or not _text(p.get("schedule")): blockers.append("PRICING_REQUIRED")
    if p.get("owner_approved") is not True: blockers.append("PRICING_OWNER_APPROVAL_REQUIRED")
    if not _text(o.get("dei_approach")): blockers.append("DEI_APPROACH_REQUIRED")
    if not _text(o.get("service_request_tracking")): warnings.append("SERVICE_REQUEST_TRACKING_PREFERENCE_NOT_ADDRESSED")
    if o.get("living_wage_obligation_reviewed") is not True: blockers.append("LIVING_WAGE_OBLIGATION_REVIEW_REQUIRED")
    if o.get("sam_exclusion_requirement_reviewed") is not True: blockers.append("SAM_EXCLUSION_REQUIREMENT_REVIEW_REQUIRED")
    answers=o["track_answers"]
    for track in selected:
        if track in allowed:
            v=answers.get(track); n=len(s["track_questions"][track])
            if not isinstance(v,list) or len(v)!=n or not all(_text(x) for x in v): blockers.append(f"TRACK_ANSWERS_INCOMPLETE:{track}")
    stray=sorted(set(answers)-allowed)
    if stray: blockers.append("UNKNOWN_TRACK_ANSWER_SET:"+",".join(stray))
    plan=o["page_plan"]; lim=s["format"]["page_limits"]
    for k in ("organizational_overview_and_mission","experience_and_qualifications","dei_approach","team_and_staffing","pricing"):
        v=plan.get(k)
        if not _int(v) or v<1: blockers.append(f"PAGE_PLAN_{k.upper()}_REQUIRED")
        elif v>lim[k]: blockers.append(f"PAGE_LIMIT_EXCEEDED:{k}")
    tp=plan.get("selected_track_answers")
    if not isinstance(tp,dict): blockers.append("TRACK_PAGE_PLAN_REQUIRED")
    else:
        for track in selected:
            if track in allowed:
                v=tp.get(track)
                if not _int(v) or v<1: blockers.append(f"TRACK_PAGE_PLAN_REQUIRED:{track}")
                elif v>lim["selected_track_answers_per_track"]: blockers.append(f"TRACK_PAGE_LIMIT_EXCEEDED:{track}")
    deadline=datetime.strptime(s["proposal_due_date"]+"T17:00:00","%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone(timedelta(hours=-5)))
    if now>deadline.astimezone(timezone.utc): state=DEADLINE_HOLD; blockers.append("PROPOSAL_DEADLINE_PASSED_USING_SOURCE_EST_LABEL")
    if state not in (SOURCE_HOLD,DEADLINE_HOLD): state=READY if not blockers else OWNER_HOLD
    r={"schema":RECEIPT_SCHEMA,"state":state,"evaluated_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"source_snapshot_sha256":digest(s),"owner_input_sha256":digest(o),"selected_tracks":selected,"qualifying_experience_count":len(qualifying),"reference_count":len(ids),"blockers":sorted(set(blockers)),"warnings":sorted(set(warnings)),"source_ambiguities":list(s.get("source_ambiguities",[])),"authority":dict(AUTHORITY)}
    r["receipt_sha256"]=digest(dict(r)); return r

def parse_trusted_now(text): return parse_utc(text,"trusted-now")
def main():
    p=argparse.ArgumentParser(); p.add_argument("--source",required=True); p.add_argument("--owner",required=True); p.add_argument("--trusted-now",required=True); a=p.parse_args()
    s=load_json_bytes(Path(a.source).read_bytes(),"source"); o=load_json_bytes(Path(a.owner).read_bytes(),"owner")
    print(json.dumps(evaluate(s,o,trusted_now=parse_trusted_now(a.trusted_now)),indent=2,sort_keys=True))
if __name__=="__main__": main()
