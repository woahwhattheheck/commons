#!/usr/bin/env python3
"""Fail-closed qualification compiler for NASPO SW1045.

This module performs no network call, buyer/prime contact, supplier registration,
portal login, proposal submission, representation, pricing commitment, signature,
spend, contract acceptance, payment, or revenue-recognition action.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SOURCE_SCHEMA="naspo.sw1045.source_snapshot/v1"
ATTACH_SCHEMA="naspo.sw1045.attachment_manifest/v1"
REQ_SCHEMA="naspo.sw1045.requirements/v1"
OWNER_SCHEMA="naspo.sw1045.owner_inputs/v1"
RECEIPT_SCHEMA="naspo.sw1045.qualification_receipt/v1"
MAX_BYTES=2_000_000
MAX_SAFE_INT=9_007_199_254_740_991
MAX_SOURCE_AGE=timedelta(days=7)
SHA1_RE=re.compile(r"[0-9a-f]{40}")
SHA256_RE=re.compile(r"[0-9a-f]{64}")
UTC_RE=re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
HTTPS_RE=re.compile(r"https://[^\s]+")
PLACEHOLDER=re.compile(r"(?:OWNER_INPUT_REQUIRED|\bTBD\b|\bTODO\b|<[^>]+>)",re.I)

PRIME_READY="PRIME_READY_FOR_OWNER_REVIEW"
HOLD_PACKET="HOLD_OFFICIAL_PACKET_REQUIRED"
HOLD="HOLD"
TEAM_DRAFT="TEAMING_DRAFT_READY_FOR_OWNER_REVIEW"
TEAM_READY="TEAMING_SUBCONTRACT_READY_FOR_OWNER_REVIEW"

AUTHORITY_KEYS={
 "agency_contact_authorized","naspo_contact_authorized","prime_contact_authorized",
 "supplier_registration_authorized","portal_login_authorized","proposal_submission_authorized",
 "past_performance_representation_authorized","named_person_commitment_authorized",
 "pricing_commitment_authorized","certification_or_signature_authorized","spend_authorized",
 "contract_acceptance_authorized","revenue_recognition_authorized"
}
SOURCE_KEYS={"schema","opportunity_id","title","lead_state","solicitation_number","alternate_event_id",
 "release_date","close_at","checked_at","status","phase","purpose","eligible_use","official_sources",
 "mirror_sources","packet_access","award_status","authority"}
PACKET_KEYS={"official_packet_acquired","official_packet_sha256","official_packet_attachment_count",
 "official_addenda_inventory_confirmed","observation"}
ATTACH_KEYS={"schema","complete_inventory_confirmed","official_addenda_inventory_confirmed","documents","note"}
DOC_KEYS={"document_id","name","discovery_authority","status","official_url","sha256"}
REQ_KEYS={"schema","source_authority","evaluation_model_status","categories","noncontrolling_observations","qualification_rule"}
CAT_KEYS={"category_id","label","independently_evaluated","observed_scope","mandatory_requirements"}
OBS_KEYS={"observation_id","applies_to","text","authority"}
OWNER_KEYS={"schema","organization","bid_intent","public_sector_references","personnel_evidence","technical_evidence",
 "mandatory_requirement_evidence","prime_partner","teaming_scope","pricing","claims"}
ORG_KEYS={"public_name","website","legal_entity_evidence_ref","legal_entity_evidence_sha256"}
INTENT_KEYS={"categories","teaming_subcontract"}
REF_KEYS={"reference_id","client_class","project_summary","period_start","period_end","evidence_ref","evidence_sha256","externally_supportable"}
PERSON_KEYS={"person_id","role","years_relevant","evidence_ref","evidence_sha256","commitment_status"}
TECH_KEYS={"evidence_id","path","blob_sha","capability","public_sector_past_performance"}
MREQ_KEYS={"requirement_id","category_id","status","evidence_ref","evidence_sha256"}
PARTNER_KEYS={"status","organization_ref","commitment_evidence_ref","commitment_evidence_sha256",
 "public_sector_prime_track_record","cooperative_contract_admin_evidence_ref","cooperative_contract_admin_evidence_sha256"}
TEAM_KEYS={"summary","deliverables","staffing_roles","acceptance_evidence","responsible_ai","data_boundary"}
PRICE_KEYS={"status","currency","unit_model","evidence_ref","evidence_sha256"}
CLAIM_KEYS={"claim_id","kind","text","evidence_ref","evidence_sha256","support_level"}

class QualificationError(ValueError): pass

def _pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise QualificationError(f"duplicate JSON key: {k}")
        out[k]=v
    return out

def _bad_constant(v): raise QualificationError(f"non-finite JSON value forbidden: {v}")

def _graph(v,path="$"):
    if v is None or isinstance(v,(str,bool)): return
    if type(v) is int:
        if abs(v)>MAX_SAFE_INT: raise QualificationError(f"unsafe integer at {path}")
        return
    if isinstance(v,float): raise QualificationError(f"floats forbidden at {path}")
    if isinstance(v,list):
        if len(v)>1000: raise QualificationError(f"array too large at {path}")
        for i,x in enumerate(v): _graph(x,f"{path}[{i}]")
        return
    if isinstance(v,dict):
        if len(v)>1000: raise QualificationError(f"object too large at {path}")
        for k,x in v.items():
            if not isinstance(k,str): raise QualificationError(f"non-string key at {path}")
            _graph(x,f"{path}.{k}")
        return
    raise QualificationError(f"unsupported JSON type at {path}")

def load_json_bytes(raw:bytes,label:str)->dict:
    if not isinstance(raw,bytes) or len(raw)>MAX_BYTES: raise QualificationError(f"{label} invalid/too large")
    try: text=raw.decode("utf-8")
    except UnicodeDecodeError as exc: raise QualificationError(f"{label} must be UTF-8") from exc
    try: obj=json.loads(text,object_pairs_hook=_pairs,parse_constant=_bad_constant)
    except QualificationError: raise
    except json.JSONDecodeError as exc: raise QualificationError(f"{label} invalid JSON") from exc
    if not isinstance(obj,dict): raise QualificationError(f"{label} must be object")
    _graph(obj); return obj

def canonical_bytes(v:Any)->bytes:
    _graph(v)
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def digest(v:Any)->str:
    raw=v if isinstance(v,bytes) else canonical_bytes(v)
    return hashlib.sha256(raw).hexdigest()

def _keys(v,expected,label):
    if not isinstance(v,dict): raise QualificationError(f"{label} must be object")
    got=set(v)
    if got!=expected: raise QualificationError(f"{label} key mismatch missing={sorted(expected-got)} extra={sorted(got-expected)}")

def _text(v): return isinstance(v,str) and 0<len(v.strip())<=10000 and not PLACEHOLDER.search(v)
def _sha1(v): return isinstance(v,str) and bool(SHA1_RE.fullmatch(v))
def _sha256(v): return isinstance(v,str) and bool(SHA256_RE.fullmatch(v))
def _date(v,label):
    if not isinstance(v,str): raise QualificationError(f"{label} must be date")
    try: return datetime.strptime(v,"%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc: raise QualificationError(f"{label} invalid date") from exc
def _utc(v,label):
    if not isinstance(v,str) or not UTC_RE.fullmatch(v): raise QualificationError(f"{label} must be canonical UTC")
    try: return datetime.strptime(v,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc: raise QualificationError(f"{label} invalid UTC") from exc
def _trusted(v):
    if not isinstance(v,datetime) or v.tzinfo is None or v.utcoffset() is None: raise QualificationError("trusted_now must be aware")
    return v.astimezone(timezone.utc).replace(microsecond=0)

def validate_source(s):
    _keys(s,SOURCE_KEYS,"source")
    if s["schema"]!=SOURCE_SCHEMA: raise QualificationError("source schema")
    if s["solicitation_number"]!="SW1045" or s["lead_state"]!="Oklahoma": raise QualificationError("solicitation identity drift")
    if s["status"]!="OPEN" or s["phase"]!="Public Posting Activities": raise QualificationError("source status/phase drift")
    if s["award_status"]!="NO_AWARD_YET": raise QualificationError("award truth drift")
    _date(s["release_date"],"release_date"); _utc(s["close_at"],"close_at"); _utc(s["checked_at"],"checked_at")
    if not isinstance(s["official_sources"],list) or len(s["official_sources"])<1: raise QualificationError("official sources required")
    for i,row in enumerate(s["official_sources"]):
        _keys(row,{"authority","label","url"},f"official_sources[{i}]")
        if row["authority"] not in {"OFFICIAL_SUMMARY","OFFICIAL_INDEX"}: raise QualificationError("invalid official authority")
        if not _text(row["label"]) or not isinstance(row["url"],str) or not row["url"].startswith("https://www.naspovaluepoint.org/"): raise QualificationError("official source origin")
    if not isinstance(s["mirror_sources"],list): raise QualificationError("mirror sources")
    for i,row in enumerate(s["mirror_sources"]):
        _keys(row,{"authority","label","url"},f"mirror_sources[{i}]")
        if row["authority"]!="PUBLIC_MIRROR_DISCOVERY" or not _text(row["label"]) or not isinstance(row["url"],str) or not HTTPS_RE.fullmatch(row["url"]):
            raise QualificationError("mirror source malformed")
    _keys(s["packet_access"],PACKET_KEYS,"packet_access")
    pa=s["packet_access"]
    if type(pa["official_packet_acquired"]) is not bool or type(pa["official_addenda_inventory_confirmed"]) is not bool:
        raise QualificationError("packet bools exact")
    if pa["official_packet_acquired"]:
        if not _sha256(pa["official_packet_sha256"]): raise QualificationError("official packet digest required")
        if type(pa["official_packet_attachment_count"]) is not int or pa["official_packet_attachment_count"]<=0: raise QualificationError("packet count required")
    else:
        if pa["official_packet_sha256"] is not None or pa["official_packet_attachment_count"] is not None:
            raise QualificationError("do not invent packet digest/count")
    if not _text(pa["observation"]): raise QualificationError("packet observation required")
    if not isinstance(s["authority"],dict) or set(s["authority"])!=AUTHORITY_KEYS or any(v is not False for v in s["authority"].values()):
        raise QualificationError("authority ceiling drift")

def validate_attachments(a):
    _keys(a,ATTACH_KEYS,"attachments")
    if a["schema"]!=ATTACH_SCHEMA: raise QualificationError("attachment schema")
    if type(a["complete_inventory_confirmed"]) is not bool or type(a["official_addenda_inventory_confirmed"]) is not bool:
        raise QualificationError("attachment booleans exact")
    if not _text(a["note"]): raise QualificationError("attachment note required")
    if not isinstance(a["documents"],list): raise QualificationError("documents must list")
    seen=set()
    for i,d in enumerate(a["documents"]):
        _keys(d,DOC_KEYS,f"documents[{i}]")
        if not _text(d["document_id"]) or d["document_id"] in seen: raise QualificationError("document id invalid/duplicate")
        seen.add(d["document_id"])
        if not _text(d["name"]): raise QualificationError("document name")
        if d["discovery_authority"] not in {"PUBLIC_MIRROR_DISCOVERY","OFFICIAL_PACKET"}: raise QualificationError("document authority")
        if d["status"] not in {"MIRROR_NAME_ONLY","OFFICIAL_EXACT"}: raise QualificationError("document status")
        if d["status"]=="OFFICIAL_EXACT":
            if d["discovery_authority"]!="OFFICIAL_PACKET" or not _sha256(d["sha256"]) or not isinstance(d["official_url"],str) or not HTTPS_RE.fullmatch(d["official_url"]):
                raise QualificationError("official exact document requires authority/url/digest")
        else:
            if d["sha256"] is not None or d["official_url"] is not None: raise QualificationError("mirror name cannot carry official digest/url")

def validate_requirements(r):
    _keys(r,REQ_KEYS,"requirements")
    if r["schema"]!=REQ_SCHEMA: raise QualificationError("requirements schema")
    if r["source_authority"] not in {"PUBLIC_MIRROR_DISCOVERY","CONTROLLING_PACKET"}: raise QualificationError("requirements authority")
    if r["evaluation_model_status"] not in {"NOT_CONTROLLING_SOURCE_CAPTURED","EXACT_CAPTURED"}: raise QualificationError("evaluation status")
    if not isinstance(r["categories"],list) or len(r["categories"])!=2: raise QualificationError("two categories required")
    ids=[]
    for i,c in enumerate(r["categories"]):
        _keys(c,CAT_KEYS,f"categories[{i}]")
        if c["category_id"] not in {"CATEGORY_1_CONSULTING","CATEGORY_2_SERVICES"}: raise QualificationError("category id")
        ids.append(c["category_id"])
        if type(c["independently_evaluated"]) is not bool or c["independently_evaluated"] is not True: raise QualificationError("category independence")
        if not isinstance(c["observed_scope"],list) or not all(_text(x) for x in c["observed_scope"]): raise QualificationError("observed scope")
        if not isinstance(c["mandatory_requirements"],list): raise QualificationError("mandatory req list")
        for j,m in enumerate(c["mandatory_requirements"]):
            _keys(m,{"requirement_id","text","source_document_id","source_sha256"},f"mandatory[{i}][{j}]")
            if not all(_text(m[k]) for k in ("requirement_id","text","source_document_id")) or not _sha256(m["source_sha256"]): raise QualificationError("mandatory req evidence")
    if set(ids)!={"CATEGORY_1_CONSULTING","CATEGORY_2_SERVICES"} or len(ids)!=len(set(ids)): raise QualificationError("category set")
    if r["source_authority"]=="CONTROLLING_PACKET" and r["evaluation_model_status"]!="EXACT_CAPTURED": raise QualificationError("controlling requirements require exact evaluation model")
    if r["source_authority"]!="CONTROLLING_PACKET" and any(c["mandatory_requirements"] for c in r["categories"]): raise QualificationError("mirror cannot define mandatory requirements")
    if not isinstance(r["noncontrolling_observations"],list): raise QualificationError("observations list")
    for i,o in enumerate(r["noncontrolling_observations"]):
        _keys(o,OBS_KEYS,f"observations[{i}]")
        if o["authority"] not in {"PUBLIC_MIRROR_DISCOVERY","OFFICIAL_SUMMARY"}: raise QualificationError("observation authority")
        if not _text(o["observation_id"]) or not _text(o["text"]) or not isinstance(o["applies_to"],list): raise QualificationError("observation malformed")
    if not _text(r["qualification_rule"]): raise QualificationError("qualification rule")

def validate_owner(o):
    _keys(o,OWNER_KEYS,"owner")
    if o["schema"]!=OWNER_SCHEMA: raise QualificationError("owner schema")
    for key,ks in [("organization",ORG_KEYS),("bid_intent",INTENT_KEYS),("prime_partner",PARTNER_KEYS),("teaming_scope",TEAM_KEYS),("pricing",PRICE_KEYS)]:
        _keys(o[key],ks,key)
    for key in ("public_sector_references","personnel_evidence","technical_evidence","mandatory_requirement_evidence","claims"):
        if not isinstance(o[key],list): raise QualificationError(f"{key} must list")

def _support_records(o,blockers):
    ref_count=0
    ids=set()
    for i,r in enumerate(o["public_sector_references"]):
        _keys(r,REF_KEYS,f"public_sector_references[{i}]")
        rid=r["reference_id"]
        if not _text(rid) or rid in ids: blockers.append("PUBLIC_SECTOR_REFERENCE_ID_INVALID_OR_DUPLICATE")
        ids.add(rid)
        for k in ("client_class","project_summary","evidence_ref"):
            if not _text(r[k]): blockers.append(f"PUBLIC_SECTOR_REFERENCE_{i}_{k.upper()}_REQUIRED")
        if not _sha256(r["evidence_sha256"]): blockers.append(f"PUBLIC_SECTOR_REFERENCE_{i}_EVIDENCE_SHA256_REQUIRED")
        st=_date(r["period_start"],f"reference[{i}].period_start"); en=_date(r["period_end"],f"reference[{i}].period_end")
        if en<st: blockers.append(f"PUBLIC_SECTOR_REFERENCE_{i}_PERIOD_INVERTED")
        if type(r["externally_supportable"]) is not bool: raise QualificationError("externally_supportable exact bool")
        if r["externally_supportable"] and _text(r["evidence_ref"]) and _sha256(r["evidence_sha256"]): ref_count+=1

    staff_count=0
    ids=set()
    for i,r in enumerate(o["personnel_evidence"]):
        _keys(r,PERSON_KEYS,f"personnel_evidence[{i}]")
        pid=r["person_id"]
        if not _text(pid) or pid in ids: blockers.append("PERSON_ID_INVALID_OR_DUPLICATE")
        ids.add(pid)
        if not _text(r["role"]): blockers.append(f"PERSON_{i}_ROLE_REQUIRED")
        if type(r["years_relevant"]) is not int or r["years_relevant"]<0 or r["years_relevant"]>100: blockers.append(f"PERSON_{i}_YEARS_INVALID")
        if not _text(r["evidence_ref"]) or not _sha256(r["evidence_sha256"]): blockers.append(f"PERSON_{i}_EVIDENCE_REQUIRED")
        if r["commitment_status"] not in {"UNCOMMITTED","OWNER_AUTHORIZED_COMMITMENT"}: blockers.append(f"PERSON_{i}_COMMITMENT_STATUS_INVALID")
        if r["commitment_status"]=="OWNER_AUTHORIZED_COMMITMENT": staff_count+=1
    return ref_count,staff_count

def _tech(o,blockers):
    ids=set(); n=0
    for i,t in enumerate(o["technical_evidence"]):
        _keys(t,TECH_KEYS,f"technical_evidence[{i}]")
        if not _text(t["evidence_id"]) or t["evidence_id"] in ids: blockers.append("TECH_EVIDENCE_ID_INVALID_OR_DUPLICATE")
        ids.add(t["evidence_id"])
        if not _text(t["path"]) or not _sha1(t["blob_sha"]) or not _text(t["capability"]): blockers.append(f"TECH_EVIDENCE_{i}_INCOMPLETE")
        if type(t["public_sector_past_performance"]) is not bool: raise QualificationError("public_sector_past_performance exact bool")
        if t["public_sector_past_performance"] is True: blockers.append(f"TECH_EVIDENCE_{i}_CANNOT_ASSERT_PUBLIC_SECTOR_PAST_PERFORMANCE")
        if _text(t["path"]) and _sha1(t["blob_sha"]) and _text(t["capability"]): n+=1
    return n

def _claims(o,blockers):
    ids=set(); supported=0
    for i,c in enumerate(o["claims"]):
        _keys(c,CLAIM_KEYS,f"claims[{i}]")
        cid=c["claim_id"]
        if not _text(cid) or cid in ids: blockers.append("CLAIM_ID_INVALID_OR_DUPLICATE")
        ids.add(cid)
        if c["kind"] not in {"TECHNICAL_CAPABILITY","PUBLIC_SECTOR_PAST_PERFORMANCE","PERSONNEL","PARTNER_COMMITMENT","PRICING"}: blockers.append(f"CLAIM_{i}_KIND_INVALID")
        if c["support_level"] not in {"SUPPORTED","UNSUPPORTED"}: blockers.append(f"CLAIM_{i}_SUPPORT_INVALID")
        if not _text(c["text"]): blockers.append(f"CLAIM_{i}_TEXT_REQUIRED")
        if c["support_level"]=="SUPPORTED":
            if not _text(c["evidence_ref"]) or not _sha256(c["evidence_sha256"]): blockers.append(f"CLAIM_{i}_SUPPORTED_WITHOUT_EVIDENCE")
            else: supported+=1
        else: blockers.append(f"UNSUPPORTED_CLAIM:{cid}")
    return supported

def packet_ready(s,a,r):
    pa=s["packet_access"]
    if not pa["official_packet_acquired"] or not pa["official_addenda_inventory_confirmed"]: return False
    if not a["complete_inventory_confirmed"] or not a["official_addenda_inventory_confirmed"]: return False
    if not a["documents"] or any(d["status"]!="OFFICIAL_EXACT" for d in a["documents"]): return False
    if r["source_authority"]!="CONTROLLING_PACKET" or r["evaluation_model_status"]!="EXACT_CAPTURED": return False
    return True

def evaluate(s,a,r,o,*,trusted_now:datetime)->dict:
    validate_source(s); validate_attachments(a); validate_requirements(r); validate_owner(o)
    now=_trusted(trusted_now); checked=_utc(s["checked_at"],"checked_at"); close=_utc(s["close_at"],"close_at")
    if checked>now: raise QualificationError("checked_at future")
    blockers=[]; warnings=[]
    if now-checked>MAX_SOURCE_AGE: blockers.append("SOURCE_SNAPSHOT_OLDER_THAN_7_DAYS")
    if now>=close: blockers.append("SOLICITATION_CLOSED_OR_DEADLINE_REACHED")
    if s["award_status"]!="NO_AWARD_YET": blockers.append("AWARD_TRUTH_DRIFT")

    org=o["organization"]
    if not _text(org["public_name"]): blockers.append("ORGANIZATION_PUBLIC_NAME_REQUIRED")
    if not isinstance(org["website"],str) or not _text(org["website"]) or not HTTPS_RE.fullmatch(org["website"]): blockers.append("ORGANIZATION_HTTPS_WEBSITE_REQUIRED")
    if (bool(org["legal_entity_evidence_ref"]) or bool(org["legal_entity_evidence_sha256"])) and not (_text(org["legal_entity_evidence_ref"]) and _sha256(org["legal_entity_evidence_sha256"])):
        blockers.append("LEGAL_ENTITY_EVIDENCE_PAIR_INVALID")

    intent=o["bid_intent"]
    cats=intent["categories"]
    if not isinstance(cats,list) or len(cats)!=len(set(cats)) or any(x not in {"CATEGORY_1_CONSULTING","CATEGORY_2_SERVICES"} for x in cats):
        blockers.append("BID_CATEGORIES_INVALID")
    if type(intent["teaming_subcontract"]) is not bool: raise QualificationError("teaming_subcontract exact bool")

    ref_count,staff_count=_support_records(o,blockers)
    tech_count=_tech(o,blockers)
    supported_claims=_claims(o,blockers)

    team=o["teaming_scope"]
    team_complete=True
    for k in ("summary","acceptance_evidence","responsible_ai","data_boundary"):
        if not _text(team[k]): blockers.append(f"TEAMING_{k.upper()}_REQUIRED"); team_complete=False
    for k in ("deliverables","staffing_roles"):
        if not isinstance(team[k],list) or not team[k] or not all(_text(x) for x in team[k]): blockers.append(f"TEAMING_{k.upper()}_REQUIRED"); team_complete=False

    pricing=o["pricing"]
    if pricing["status"] not in {"NOT_COMMITTED","OWNER_AUTHORIZED_DRAFT"}: blockers.append("PRICING_STATUS_INVALID")
    if pricing["currency"]!="USD": blockers.append("PRICING_CURRENCY_MUST_BE_USD")
    if not _text(pricing["unit_model"]): blockers.append("PRICING_UNIT_MODEL_REQUIRED")
    if pricing["status"]=="OWNER_AUTHORIZED_DRAFT" and not (_text(pricing["evidence_ref"]) and _sha256(pricing["evidence_sha256"])):
        blockers.append("OWNER_AUTHORIZED_PRICING_REQUIRES_EVIDENCE")

    partner=o["prime_partner"]
    if partner["status"] not in {"NONE","PROSPECTIVE","COMMITTED"}: blockers.append("PRIME_PARTNER_STATUS_INVALID")
    partner_committed=False
    if partner["status"]=="PROSPECTIVE": warnings.append("PROSPECTIVE_PRIME_IS_NOT_A_COMMITMENT")
    if partner["status"]=="COMMITTED":
        required=(partner["organization_ref"],partner["commitment_evidence_ref"],partner["cooperative_contract_admin_evidence_ref"])
        digests=(partner["commitment_evidence_sha256"],partner["cooperative_contract_admin_evidence_sha256"])
        if not all(_text(x) for x in required) or not all(_sha256(x) for x in digests):
            blockers.append("COMMITTED_PRIME_EVIDENCE_INCOMPLETE")
        if not isinstance(partner["public_sector_prime_track_record"],list) or not partner["public_sector_prime_track_record"]:
            blockers.append("COMMITTED_PRIME_TRACK_RECORD_REQUIRED")
        elif not all(_text(x) for x in partner["public_sector_prime_track_record"]):
            blockers.append("COMMITTED_PRIME_TRACK_RECORD_INVALID")
        else:
            partner_committed=all(_text(x) for x in required) and all(_sha256(x) for x in digests)

    evidence_by_cat={}
    seen_req=set()
    for i,e in enumerate(o["mandatory_requirement_evidence"]):
        _keys(e,MREQ_KEYS,f"mandatory_requirement_evidence[{i}]")
        key=(e["category_id"],e["requirement_id"])
        if key in seen_req: blockers.append("MANDATORY_REQUIREMENT_EVIDENCE_DUPLICATE")
        seen_req.add(key)
        if e["category_id"] not in {"CATEGORY_1_CONSULTING","CATEGORY_2_SERVICES"}: blockers.append("MANDATORY_REQUIREMENT_CATEGORY_INVALID")
        if e["status"] not in {"PROVEN","PARTNER_CURABLE","MISSING","NOT_APPLICABLE"}: blockers.append("MANDATORY_REQUIREMENT_STATUS_INVALID")
        if e["status"]=="PROVEN" and not (_text(e["evidence_ref"]) and _sha256(e["evidence_sha256"])):
            blockers.append("PROVEN_MANDATORY_REQUIREMENT_REQUIRES_EVIDENCE")
        evidence_by_cat.setdefault(e["category_id"],{})[e["requirement_id"]]=e

    pkt=packet_ready(s,a,r)
    route_states={}
    category_blockers={}
    req_by_cat={c["category_id"]:c["mandatory_requirements"] for c in r["categories"]}
    for cat in ("CATEGORY_1_CONSULTING","CATEGORY_2_SERVICES"):
        cb=[]
        if not pkt: cb.append("OFFICIAL_PACKET_REQUIRED")
        if cat in cats and pkt:
            for req in req_by_cat[cat]:
                ev=evidence_by_cat.get(cat,{}).get(req["requirement_id"])
                if ev is None: cb.append(f"REQUIREMENT_UNMAPPED:{req['requirement_id']}")
                elif ev["status"]!="PROVEN": cb.append(f"REQUIREMENT_NOT_PROVEN:{req['requirement_id']}:{ev['status']}")
        if cat in cats and pkt and ref_count==0: cb.append("NO_SUPPORTABLE_PUBLIC_SECTOR_REFERENCE_INVENTORY")
        if cat in cats and pkt and staff_count==0: cb.append("NO_OWNER_AUTHORIZED_PERSONNEL_COMMITMENT")
        category_blockers[cat]=sorted(set(cb))
        if cat not in cats:
            route_states[f"PRIME_{cat}"]="NOT_SELECTED"
        elif cb or blockers:
            route_states[f"PRIME_{cat}"]=HOLD_PACKET if (not pkt and not blockers) else HOLD
        else:
            route_states[f"PRIME_{cat}"]=PRIME_READY

    if intent["teaming_subcontract"]:
        team_hard=[b for b in blockers if not b.startswith("ORGANIZATION_LEGAL")]
        if not team_hard and tech_count>0 and team_complete:
            route_states["TEAMING_SUBCONTRACT"]=TEAM_READY if (pkt and partner_committed) else TEAM_DRAFT
        else:
            route_states["TEAMING_SUBCONTRACT"]=HOLD
    else:
        route_states["TEAMING_SUBCONTRACT"]="NOT_SELECTED"

    recommended="NONE"
    if route_states["TEAMING_SUBCONTRACT"] in {TEAM_READY,TEAM_DRAFT}: recommended="TEAMING_SUBCONTRACT"
    else:
        for cat in ("CATEGORY_1_CONSULTING","CATEGORY_2_SERVICES"):
            if route_states[f"PRIME_{cat}"]==PRIME_READY: recommended=f"PRIME_{cat}"; break

    state=route_states["TEAMING_SUBCONTRACT"] if recommended=="TEAMING_SUBCONTRACT" else (
        PRIME_READY if recommended.startswith("PRIME_") else (HOLD_PACKET if any(v==HOLD_PACKET for v in route_states.values()) else HOLD)
    )
    receipt={
      "schema":RECEIPT_SCHEMA,
      "state":state,
      "recommended_route":recommended,
      "evaluated_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),
      "source_sha256":digest(s),
      "attachment_manifest_sha256":digest(a),
      "requirements_sha256":digest(r),
      "owner_input_sha256":digest(o),
      "official_packet_ready":pkt,
      "route_states":route_states,
      "category_blockers":category_blockers,
      "global_blockers":sorted(set(blockers)),
      "warnings":sorted(set(warnings)),
      "supportable_public_sector_reference_count":ref_count,
      "owner_authorized_personnel_count":staff_count,
      "technical_evidence_count":tech_count,
      "supported_claim_count":supported_claims,
      "award_status":"NO_AWARD_YET",
      "authority":{k:False for k in sorted(AUTHORITY_KEYS)}
    }
    receipt["receipt_sha256"]=digest(receipt)
    return receipt

def verify(s,a,r,o,receipt,*,trusted_now):
    return isinstance(receipt,dict) and canonical_bytes(evaluate(s,a,r,o,trusted_now=trusted_now))==canonical_bytes(receipt)

def read_plain_file(path,label):
    flags=os.O_RDONLY | (getattr(os,"O_NOFOLLOW",0))
    try: fd=os.open(os.fspath(path),flags)
    except OSError as exc: raise QualificationError(f"{label} must be ordinary readable non-symlink file") from exc
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size>MAX_BYTES: raise QualificationError(f"{label} invalid file")
        chunks=[]; remaining=MAX_BYTES+1
        while remaining:
            c=os.read(fd,min(131072,remaining))
            if not c: break
            chunks.append(c); remaining-=len(c)
        raw=b"".join(chunks)
        if len(raw)>MAX_BYTES: raise QualificationError(f"{label} too large")
        return raw
    finally: os.close(fd)

def publish_exclusive(path,raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_BYTES: raise QualificationError("invalid output")
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0)
    try: fd=os.open(os.fspath(path),flags,0o600)
    except OSError as exc: raise QualificationError("refusing overwrite/symlink output") from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode): raise QualificationError("output must be regular")
        view=memoryview(raw)
        while view:
            n=os.write(fd,view); view=view[n:]
        os.fsync(fd)
    finally: os.close(fd)

def _load(path,label): return load_json_bytes(read_plain_file(path,label),label)

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    cp=sub.add_parser("compile")
    for x in ("source","attachments","requirements","owner"): cp.add_argument(f"--{x}",required=True)
    cp.add_argument("--trusted-now",required=True); cp.add_argument("--out")
    vp=sub.add_parser("verify")
    for x in ("source","attachments","requirements","owner","receipt"): vp.add_argument(f"--{x}",required=True)
    vp.add_argument("--trusted-now",required=True)
    ns=ap.parse_args(); now=_utc(ns.trusted_now,"trusted-now")
    s=_load(ns.source,"source"); a=_load(ns.attachments,"attachments"); r=_load(ns.requirements,"requirements"); o=_load(ns.owner,"owner")
    if ns.cmd=="compile":
        rec=evaluate(s,a,r,o,trusted_now=now); raw=json.dumps(rec,indent=2,sort_keys=True).encode()+b"\n"
        if ns.out: publish_exclusive(ns.out,raw)
        else: os.write(1,raw)
        return 0 if rec["state"] in {PRIME_READY,TEAM_READY,TEAM_DRAFT} else 3
    rec=_load(ns.receipt,"receipt"); ok=verify(s,a,r,o,rec,trusted_now=now)
    os.write(1,(json.dumps({"verified":ok},sort_keys=True)+"\n").encode()); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
