"""Deterministic AIDT EWDS specialist-workshare receipts; no network transport."""
import hashlib, json, re

SOLICITATION_ID="SRC0000036381"
BUYER="Alabama Industrial Development Training (AIDT)"
QUESTION_DEADLINE="2026-10-01T17:00:00-05:00"
PROPOSAL_DEADLINE="2026-10-15T16:30:00-05:00"
PUBLIC_PACKET_FILENAME="AIDT_RFP_-_Enterprise_Workforce_Development_System_FINAL.pdf"
REQUIRED_WORKSHARE_EVIDENCE=(
 "requirements_matrix","migration_reconciliation_plan",
 "salesforce_adobe_lms_integration_plan","workflow_acceptance_plan",
 "prime_qualification_matrix","economics_stop_ledger")
PRIME_GATE_EVIDENCE=(
 "three_relevant_references","two_relevant_state_or_local_case_studies",
 "salesforce_platform_compatibility","hosting_security_and_support_sla",
 "alabama_everify_and_required_compliance","alabama_buys_registration_for_submission",
 "complete_prime_pricing")
REQUIREMENTS=(
 ("historical_data_import",1,"migration_reconciliation"),
 ("workflow_automation",2,"acceptance_harness"),
 ("salesforce_interoperability",1,"integration_contract"),
 ("adobe_lms_sync",2,"integration_contract"),
 ("secure_role_based_access",1,"acceptance_harness"),
 ("reporting_and_dashboards",2,"acceptance_harness"),
 ("credential_tracking",2,"acceptance_harness"))
_ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,191}$")
_HEX=re.compile(r"^[0-9a-f]{64}$")
_SYSTEMS={"salesforce","adobe_lms","ewds"}
_OPS={"upsert_applicant","upsert_class","enroll","credential_update","attendance_update"}

class WorkshareError(ValueError): pass

def _obj(v,n):
 if type(v) is not dict: raise WorkshareError(f"{n}: plain object required")
 return v
def _exact(v,fields,n):
 if set(v)!=set(fields): raise WorkshareError(f"{n}: exact fields required")
def _id(v,n):
 if not isinstance(v,str) or not v.isascii() or not _ID.fullmatch(v): raise WorkshareError(f"{n}: bounded ASCII identifier required")
 return v
def _sha(v,n):
 if not isinstance(v,str) or not _HEX.fullmatch(v): raise WorkshareError(f"{n}: lowercase SHA-256 required")
 return v
def _canon(v):
 try:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")
 except Exception as e: raise WorkshareError("noncanonical JSON") from e
def _digest(v): return hashlib.sha256(_canon(v)).hexdigest()
def _seal(v):
 out=dict(v); out["receipt_sha256"]=_digest(out); return out
def _check_seal(v):
 claimed=_sha(v["receipt_sha256"],"receipt_sha256"); m=dict(v); m.pop("receipt_sha256")
 if _digest(m)!=claimed: raise WorkshareError("receipt digest mismatch")

def _records(rows,name):
 if isinstance(rows,(str,bytes)) or not isinstance(rows,(list,tuple)): raise WorkshareError(f"{name}: sequence required")
 out={}
 for i,row in enumerate(rows):
  row=_obj(row,f"{name}[{i}]"); _exact(row,{"record_id","record_sha256"},f"{name}[{i}]")
  rid=_id(row["record_id"],"record_id"); dig=_sha(row["record_sha256"],"record_sha256")
  if rid in out: raise WorkshareError(f"{name}: duplicate record_id {rid}")
  out[rid]=dig
 return out

def reconcile_migration(source_records,target_records):
 s,t=_records(source_records,"source_records"),_records(target_records,"target_records")
 si,ti=set(s),set(t)
 missing,extra=sorted(si-ti),sorted(ti-si)
 mismatch=sorted(k for k in si&ti if s[k]!=t[k])
 ok=not(missing or extra or mismatch)
 return _seal({
  "schema":"aidt-ewds-migration/v1","solicitation_id":SOLICITATION_ID,
  "source_count":len(s),"target_count":len(t),
  "source_manifest_sha256":_digest(sorted(s.items())),
  "target_manifest_sha256":_digest(sorted(t.items())),
  "missing_record_ids":missing,"extra_record_ids":extra,"mismatched_record_ids":mismatch,
  "decision":"MIGRATION_RECONCILED" if ok else "HOLD_MIGRATION_RECONCILIATION",
  "contains_live_pii":False,"external_submission_authorized":False})

def verify_migration_receipt(r):
 r=_obj(r,"migration")
 fields={"schema","solicitation_id","source_count","target_count","source_manifest_sha256","target_manifest_sha256",
 "missing_record_ids","extra_record_ids","mismatched_record_ids","decision","contains_live_pii",
 "external_submission_authorized","receipt_sha256"}
 _exact(r,fields,"migration")
 if r["schema"]!="aidt-ewds-migration/v1" or r["solicitation_id"]!=SOLICITATION_ID: raise WorkshareError("migration identity mismatch")
 for k in ("source_count","target_count"):
  if type(r[k]) is not int or r[k]<0: raise WorkshareError("migration count invalid")
 for k in ("source_manifest_sha256","target_manifest_sha256"): _sha(r[k],k)
 for k in ("missing_record_ids","extra_record_ids","mismatched_record_ids"):
  if type(r[k]) is not list or r[k]!=sorted(set(r[k])): raise WorkshareError("migration findings noncanonical")
  for v in r[k]: _id(v,k)
 clear=not(r["missing_record_ids"] or r["extra_record_ids"] or r["mismatched_record_ids"])
 if r["decision"]!=("MIGRATION_RECONCILED" if clear else "HOLD_MIGRATION_RECONCILIATION"): raise WorkshareError("migration decision inconsistent")
 if r["contains_live_pii"] is not False or r["external_submission_authorized"] is not False: raise WorkshareError("migration authority invalid")
 _check_seal(r); return True

def compile_sync_receipt(event,observed):
 event,observed=_obj(event,"event"),_obj(observed,"observed")
 ef={"source_system","target_system","event_id","entity_ref","operation","payload_sha256"}
 of={"accepted","target_ref","target_payload_sha256"}
 _exact(event,ef,"event"); _exact(observed,of,"observed")
 ss,ts=_id(event["source_system"],"source_system"),_id(event["target_system"],"target_system")
 if ss not in _SYSTEMS or ts not in _SYSTEMS or ss==ts: raise WorkshareError("unsupported system pair")
 eid,eref,op=_id(event["event_id"],"event_id"),_id(event["entity_ref"],"entity_ref"),_id(event["operation"],"operation")
 if op not in _OPS: raise WorkshareError("unsupported operation")
 pay=_sha(event["payload_sha256"],"payload_sha256")
 if type(observed["accepted"]) is not bool: raise WorkshareError("accepted: bool required")
 tr=_id(observed["target_ref"],"target_ref"); tp=_sha(observed["target_payload_sha256"],"target_payload_sha256")
 em={"source_system":ss,"target_system":ts,"event_id":eid,"entity_ref":eref,"operation":op,"payload_sha256":pay}
 ok=observed["accepted"] and pay==tp
 return _seal({"schema":"aidt-ewds-sync/v1","solicitation_id":SOLICITATION_ID,**em,
  "idempotency_key":_digest(em),"observed_accepted":observed["accepted"],
  "observed_target_ref":tr,"observed_target_payload_sha256":tp,
  "decision":"SYNC_ACCEPTED_EXACT" if ok else "HOLD_SYNC_ACCEPTANCE",
  "transport_performed_by_compiler":False,"external_submission_authorized":False})

def verify_sync_receipt(r):
 r=_obj(r,"sync")
 fields={"schema","solicitation_id","source_system","target_system","event_id","entity_ref","operation","payload_sha256",
 "idempotency_key","observed_accepted","observed_target_ref","observed_target_payload_sha256","decision",
 "transport_performed_by_compiler","external_submission_authorized","receipt_sha256"}
 _exact(r,fields,"sync")
 event={k:r[k] for k in ("source_system","target_system","event_id","entity_ref","operation","payload_sha256")}
 obs={"accepted":r["observed_accepted"],"target_ref":r["observed_target_ref"],"target_payload_sha256":r["observed_target_payload_sha256"]}
 if compile_sync_receipt(event,obs)!=r: raise WorkshareError("sync semantic or digest mismatch")
 return True

def compile_readiness(evidence,migrations,syncs):
 evidence=_obj(evidence,"evidence"); allowed=set(REQUIRED_WORKSHARE_EVIDENCE)
 if set(evidence)-allowed: raise WorkshareError("unknown keys in workshare evidence")
 ev={k:_sha(v,k) for k,v in evidence.items()}
 ms=[]
 for r in migrations: verify_migration_receipt(r); ms.append(dict(r))
 ss=[]
 for r in syncs: verify_sync_receipt(r); ss.append(dict(r))
 ms.sort(key=lambda x:x["receipt_sha256"]); ss.sort(key=lambda x:x["receipt_sha256"])
 missing=sorted(allowed-set(ev))
 ready=(not missing and any(x["decision"]=="MIGRATION_RECONCILED" for x in ms)
        and any(x["decision"]=="SYNC_ACCEPTED_EXACT" for x in ss))
 return _seal({
  "schema":"aidt-ewds-readiness/v1","solicitation_id":SOLICITATION_ID,"buyer":BUYER,
  "question_deadline":QUESTION_DEADLINE,"proposal_deadline":PROPOSAL_DEADLINE,
  "public_packet_filename":PUBLIC_PACKET_FILENAME,
  "source_authority":"PUBLIC_PACKET_COPY_REQUIRES_ALABAMA_BUYS_RECHECK",
  "controlling_source_recheck_required":True,
  "requirement_evidence":{k:ev[k] for k in sorted(ev)},"missing_workshare_evidence":missing,
  "migration_receipts":ms,"sync_receipts":ss,
  "state":"WORKSHARE_READY_FOR_PRIME_REVIEW" if ready else "HOLD_WORKSHARE_INCOMPLETE",
  "prime_gate_evidence_required":list(PRIME_GATE_EVIDENCE),"prime_qualified":False,
  "alabama_buys_registered":False,"external_outbound_authorized":False,
  "proposal_submission_authorized":False,"buyer_acceptance_claim_authorized":False,
  "award_claim_authorized":False,"payment_claim_authorized":False,"revenue_claim_authorized":False})

def verify_readiness(r):
 r=_obj(r,"readiness")
 authority=("prime_qualified","alabama_buys_registered","external_outbound_authorized","proposal_submission_authorized",
 "buyer_acceptance_claim_authorized","award_claim_authorized","payment_claim_authorized","revenue_claim_authorized")
 fields={"schema","solicitation_id","buyer","question_deadline","proposal_deadline","public_packet_filename","source_authority",
 "controlling_source_recheck_required","requirement_evidence","missing_workshare_evidence","migration_receipts","sync_receipts",
 "state","prime_gate_evidence_required",*authority,"receipt_sha256"}
 _exact(r,fields,"readiness")
 if (r["schema"],r["solicitation_id"],r["buyer"])!=("aidt-ewds-readiness/v1",SOLICITATION_ID,BUYER): raise WorkshareError("readiness identity mismatch")
 if (r["question_deadline"],r["proposal_deadline"],r["public_packet_filename"])!=(QUESTION_DEADLINE,PROPOSAL_DEADLINE,PUBLIC_PACKET_FILENAME): raise WorkshareError("readiness pinned facts mismatch")
 if r["source_authority"]!="PUBLIC_PACKET_COPY_REQUIRES_ALABAMA_BUYS_RECHECK" or r["controlling_source_recheck_required"] is not True: raise WorkshareError("source recheck disabled")
 ev=_obj(r["requirement_evidence"],"requirement_evidence"); allowed=set(REQUIRED_WORKSHARE_EVIDENCE)
 if set(ev)-allowed: raise WorkshareError("unknown keys in workshare evidence")
 for k,v in ev.items(): _sha(v,k)
 missing=sorted(allowed-set(ev))
 if r["missing_workshare_evidence"]!=missing: raise WorkshareError("missing evidence mismatch")
 ms,ss=r["migration_receipts"],r["sync_receipts"]
 if type(ms) is not list or type(ss) is not list: raise WorkshareError("child receipts must be lists")
 for child in ms: verify_migration_receipt(child)
 for child in ss: verify_sync_receipt(child)
 if ms!=sorted(ms,key=lambda x:x["receipt_sha256"]) or ss!=sorted(ss,key=lambda x:x["receipt_sha256"]): raise WorkshareError("child receipt order invalid")
 if r["prime_gate_evidence_required"]!=list(PRIME_GATE_EVIDENCE): raise WorkshareError("prime gates changed")
 for k in authority:
  if r[k] is not False: raise WorkshareError("repository evidence cannot mint external authority")
 ready=(not missing and any(x["decision"]=="MIGRATION_RECONCILED" for x in ms)
        and any(x["decision"]=="SYNC_ACCEPTED_EXACT" for x in ss))
 if r["state"]!=("WORKSHARE_READY_FOR_PRIME_REVIEW" if ready else "HOLD_WORKSHARE_INCOMPLETE"): raise WorkshareError("readiness state inconsistent")
 _check_seal(r); return True
