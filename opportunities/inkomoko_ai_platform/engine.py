from __future__ import annotations
from datetime import datetime,timedelta,timezone
from .core import AUTH,CarrierError,digest,timestamp,validate_reference
from .candidate import validate_candidate

PACKET_SCHEMA="inkomoko-ai-platform-readiness/v1"
RECEIPT_SCHEMA="inkomoko-ai-platform-receipt/v1"

def requirement_rows(r,c):
    by={e["requirement_id"]:e for e in c["evidence"]};rows=[]
    for q in sorted(r["requirements"],key=lambda x:x["id"]):
        e=by.get(q["id"])
        rows.append({**q,"evidence_state":e["state"] if e else "MISSING","evidence_authority":e["authority"] if e else None,"evidence_ref":e["evidence_ref"] if e else None})
    return rows

def readiness_status(r,rows,now):
    o=r["opportunity"];deadline=datetime.strptime(o["submission_deadline_date"],"%Y-%m-%d").date();today=now.date()
    if today>deadline:return "HOLD_DEADLINE_PASSED",["submission deadline date has passed"]
    if today==deadline and not o["submission_deadline_time_known"]:return "HOLD_DEADLINE_TIME_UNKNOWN",["deadline time is unknown on the deadline date"]
    reasons=[] if o["source_authority"]=="BUYER_FIRST_PARTY" else ["controlling buyer-domain source bytes are not retained"]
    mandatory=[x for x in rows if x["mandatory"]]
    non=[x["id"] for x in mandatory if x["evidence_state"] not in {"PROVEN","PARTNER_PROVEN"} and not x["partner_curable"]]
    partner=[x["id"] for x in mandatory if x["evidence_state"] not in {"PROVEN","PARTNER_PROVEN"} and x["partner_curable"]]
    if non:reasons.append("non-curable mandatory evidence missing: "+",".join(non))
    if partner:reasons.append("partner-curable mandatory evidence missing: "+",".join(partner))
    if reasons:return ("HOLD_TEAMING_EVIDENCE_REQUIRED" if partner and not non else "HOLD"),reasons
    if all(x["evidence_state"]=="PROVEN" for x in mandatory):return "PRIME_CANDIDATE",[]
    if all(x["evidence_state"] in {"PROVEN","PARTNER_PROVEN"} for x in mandatory):return "TEAMING_CANDIDATE",[]
    return "HOLD",["mandatory evidence unresolved"]

def workshare(c):
    return {"state":"PROPOSED_NOT_ACCEPTED","price_state":"UNPRICED","currency":None,"amount_minor":None,
      "capabilities":sorted(c["specialist_capabilities"],key=lambda x:x["id"]),
      "explicit_exclusions":["buyer or partner acceptance","live customer records","external system access or configuration","messaging account ownership","legal or regulatory compliance certification","round-the-clock staffing commitment","reference or past-performance substitution","proposal submission or price commitment"]}

def _compile_at(reference,candidate,now):
    if not isinstance(now,datetime) or now.tzinfo is None:raise CarrierError("internal clock must be timezone-aware")
    now=now.astimezone(timezone.utc);r=validate_reference(reference);observed=timestamp(r["opportunity"]["observed_at"],"opportunity.observed_at")
    if observed>now:raise CarrierError("future opportunity source observation refused")
    if (now-observed).total_seconds()>30*86400:raise CarrierError("stale opportunity source observation refused")
    c=validate_candidate(candidate,r,now);rows=requirement_rows(r,c);status,reasons=readiness_status(r,rows,now);o=r["opportunity"]
    packet={"schema":PACKET_SCHEMA,
      "opportunity":{k:o[k] for k in ("id","buyer","title","submission_deadline_date","submission_deadline_time_known","submission_route","mandatory_subject_template","source_authority","source_url")},
      "candidate":{"candidate_id":c["candidate_id"],"generation":c["generation"],"vendor_name":c["vendor_name"],"candidate_digest":digest(c)},
      "compiled_at":now.replace(microsecond=0).isoformat().replace("+00:00","Z"),"status":status,"hold_reasons":reasons,"requirements":rows,"specialist_workshare":workshare(c),"authority":{k:False for k in sorted(AUTH)}}
    packet["opportunity"]["source_observed_at"]=o["observed_at"];packet["opportunity"]["reference_digest"]=digest(r)
    receipt={"schema":RECEIPT_SCHEMA,"packet_digest":digest(packet),"reference_digest":digest(r),"candidate_digest":digest(c),"status":status}
    packet["receipt"]={**receipt,"receipt_sha256":digest(receipt)}
    return packet

def compile_packet(reference,candidate):return _compile_at(reference,candidate,datetime.now(timezone.utc))

def _verify_at(packet,reference,candidate,now,max_age_seconds=21600):
    if type(packet) is not dict:raise CarrierError("packet must be object")
    if not isinstance(now,datetime) or now.tzinfo is None:raise CarrierError("internal verifier clock must be timezone-aware")
    now=now.astimezone(timezone.utc);made=timestamp(packet.get("compiled_at"),"packet.compiled_at")
    if made>now+timedelta(seconds=300):raise CarrierError("future packet generation refused")
    if (now-made).total_seconds()>max_age_seconds:raise CarrierError("stale packet generation refused")
    if packet!=_compile_at(reference,candidate,made):raise CarrierError("packet does not recompute exactly")
    return True
def verify_packet(packet,reference,candidate):return _verify_at(packet,reference,candidate,datetime.now(timezone.utc))
