from __future__ import annotations
from .core import *

EVIDENCE_STATES={"PROVEN","PARTNER_PROVEN","MISSING","HOLD"}
EVIDENCE_AUTHORITIES={"OWNER_RETAINED","PARTNER_FIRST_PARTY","PUBLIC_FIRST_PARTY","SYNTHETIC_TEST_ONLY"}

def validate_candidate(c,r,now):
    keys(c,CAND,"candidate");integer(c["schema_version"],"candidate.schema_version",1,1)
    if not IDENT.fullmatch(text(c["candidate_id"],"candidate_id",128)):raise CarrierError("candidate_id has invalid shape")
    integer(c["generation"],"candidate.generation",1);text(c["vendor_name"],"vendor_name",200)
    ids={q["id"] for q in r["requirements"]};seen=set()
    if type(c["evidence"]) is not list or len(c["evidence"])>400:raise CarrierError("evidence must be a bounded list")
    for i,e in enumerate(c["evidence"]):
        keys(e,EVID,f"evidence[{i}]");rid=text(e["requirement_id"],"requirement_id",128)
        if rid not in ids:raise CarrierError(f"unknown requirement_id: {rid}")
        if rid in seen:raise CarrierError(f"duplicate evidence requirement_id: {rid}")
        seen.add(rid)
        if e["state"] not in EVIDENCE_STATES:raise CarrierError("invalid evidence state")
        if e["authority"] not in EVIDENCE_AUTHORITIES:raise CarrierError("invalid evidence authority")
        if not REF.fullmatch(text(e["evidence_ref"],"evidence_ref",256)):raise CarrierError("unsafe evidence_ref")
        url(e["source_url"],"evidence.source_url")
        if not HEX.fullmatch(text(e["source_sha256"],"source_sha256",64)):raise CarrierError("invalid evidence sha256")
        observed=timestamp(e["observed_at"],"evidence.observed_at")
        if observed>now:raise CarrierError(f"future evidence refused for {rid}")
        if (now-observed).total_seconds()>180*86400:raise CarrierError(f"stale evidence refused for {rid}")
        if e["state"]=="PARTNER_PROVEN" and e["authority"]!="PARTNER_FIRST_PARTY":raise CarrierError(f"PARTNER_PROVEN requires PARTNER_FIRST_PARTY for {rid}")
        if e["state"]=="PROVEN" and e["authority"]=="SYNTHETIC_TEST_ONLY":raise CarrierError(f"synthetic evidence cannot prove {rid}")
    if type(c["specialist_capabilities"]) is not list or len(c["specialist_capabilities"])>30:raise CarrierError("specialist_capabilities must be a bounded list")
    seen=set()
    for i,x in enumerate(c["specialist_capabilities"]):
        keys(x,CAP,f"specialist_capability[{i}]");cid=text(x["id"],"capability.id",128)
        if cid not in CAPS:raise CarrierError(f"unsupported specialist capability: {cid}")
        if cid in seen:raise CarrierError(f"duplicate specialist capability: {cid}")
        seen.add(cid);text(x["description"],"capability.description",500)
        if not REF.fullmatch(text(x["evidence_ref"],"capability.evidence_ref",256)):raise CarrierError("unsafe capability evidence_ref")
    return c
