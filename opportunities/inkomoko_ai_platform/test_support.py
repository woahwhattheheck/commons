from __future__ import annotations
import copy
from datetime import datetime,timezone
from pathlib import Path
from opportunities.inkomoko_ai_platform.core import loads_strict

HERE=Path(__file__).resolve().parent
NOW=datetime(2026,9,17,4,30,tzinfo=timezone.utc)
def fixture(name):return loads_strict((HERE/name).read_text())
def proof(rid,state="PROVEN",authority="OWNER_RETAINED"):
    return {"requirement_id":rid,"state":state,"authority":authority,"evidence_ref":f"receipt:{rid.lower()}","source_url":"https://example.org/evidence","source_sha256":"a"*64,"observed_at":"2026-09-17T03:00:00Z"}
def buyer(ref):
    r=copy.deepcopy(ref);r["opportunity"]["source_authority"]="BUYER_FIRST_PARTY";r["opportunity"]["source_url"]="https://inkomoko.com/procurement/rfp";return r
def all_evidence(ref,candidate,partner_ids=()):
    c=copy.deepcopy(candidate);partner_ids=set(partner_ids);c["evidence"]=[]
    for q in ref["requirements"]:
        if q["mandatory"]:
            c["evidence"].append(proof(q["id"],"PARTNER_PROVEN","PARTNER_FIRST_PARTY") if q["id"] in partner_ids else proof(q["id"]))
    return c
