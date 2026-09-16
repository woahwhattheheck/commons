from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OPPORTUNITY_ID="INVEST-APPALACHIA-FRAMER-LMS-20260916"
BUYER="Invest Appalachia"; DEADLINE="2026-09-22T21:00:00Z"; CAP=60000
START="2026-10-13"; END="2027-04-30"
SOURCE="https://investappalachia.org/framer-rfp/"
RFP="https://investappalachia.org/wp-content/uploads/2026/08/1.-draft2_RFP_Invest_Appalachia_Framer_Training_LMS.docx.pdf"
ZIP="https://investappalachia.org/wp-content/uploads/2026/08/Zipped-RFP-Docs.zip"
SUBJECT="RFP Proposal Submission - Invest Appalachia Framer Training LMS"
GATES=("two_lms_platform_implementations","adult_learning_packaging","start_capacity_2026_10_13","w9_available","general_liability_available","professional_liability_available","cybersecurity_insurance_available","two_relevant_project_examples","two_prior_client_references")
AUTH=("external_contact_authorized","submission_authorized","signature_authorized","contract_acceptance_authorized","spend_authorized","payment_authorized","award_or_revenue_asserted")
class PursuitError(ValueError): pass

def canon(v:Any)->bytes:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def digest(v:Any)->str:return hashlib.sha256(canon(v)).hexdigest()
def exact(v:Any,keys:set[str],where:str):
 if type(v) is not dict: raise PursuitError(f"{where} must be object")
 if set(v)!=keys: raise PursuitError(f"{where} keys mismatch")
 return v

def normalize(raw:Any)->dict[str,Any]:
 p=exact(raw,{"opportunity","qualification","proposal","authority"},"packet")
 o=exact(p["opportunity"],{"opportunity_id","buyer","source_url","rfp_url","attachments_zip_url","deadline_utc","budget_cap_usd","contract_start","contract_end","submission_subject","attachments_status"},"opportunity")
 expected=(OPPORTUNITY_ID,BUYER,SOURCE,RFP,ZIP,DEADLINE,CAP,START,END,SUBJECT)
 actual=(o["opportunity_id"],o["buyer"],o["source_url"],o["rfp_url"],o["attachments_zip_url"],o["deadline_utc"],o["budget_cap_usd"],o["contract_start"],o["contract_end"],o["submission_subject"])
 if actual!=expected: raise PursuitError("official opportunity binding mismatch")
 if o["attachments_status"] not in {"COMPLETE","PARTIAL","UNAVAILABLE"}:raise PursuitError("bad attachments status")
 q=exact(p["qualification"],set(GATES),"qualification"); nq={}
 for name in GATES:
  g=exact(q[name],{"state","evidence_refs","note"},name)
  if g["state"] not in {"VERIFIED","MISSING","HOLD"}:raise PursuitError(f"{name}: bad state")
  if type(g["evidence_refs"]) is not list or any(type(x) is not str or not x for x in g["evidence_refs"]):raise PursuitError(f"{name}: bad evidence")
  if g["state"]=="VERIFIED" and not g["evidence_refs"]:raise PursuitError(f"{name}: VERIFIED requires retained evidence")
  if type(g["note"]) is not str or not g["note"]:raise PursuitError(f"{name}: note required")
  nq[name]={"state":g["state"],"evidence_refs":sorted(set(g["evidence_refs"])),"note":g["note"]}
 pr=exact(p["proposal"],{"proposed_total_usd","year1_license_usd","post_year1_recurring_usd","platform_recommendation","attachments_complete"},"proposal")
 for k in ("proposed_total_usd","year1_license_usd","post_year1_recurring_usd"):
  if type(pr[k]) is not int or pr[k]<0:raise PursuitError(f"{k}: nonnegative integer required")
 if pr["proposed_total_usd"]>CAP:raise PursuitError("budget cap exceeded")
 if type(pr["platform_recommendation"]) is not str or not pr["platform_recommendation"]:raise PursuitError("platform recommendation required")
 if type(pr["attachments_complete"]) is not bool:raise PursuitError("attachments_complete must be bool")
 a=exact(p["authority"],set(AUTH),"authority")
 if any(type(a[k]) is not bool for k in AUTH) or any(a.values()):raise PursuitError("all external/commercial authority must remain false")
 return {"opportunity":dict(o),"qualification":nq,"proposal":dict(pr),"authority":dict(a)}

def evaluate(raw:Any,*,now:datetime|None=None)->dict[str,Any]:
 n=normalize(raw); now=now or datetime.now(timezone.utc)
 if now.tzinfo is None:raise PursuitError("timezone-aware now required")
 missing=sorted(k for k,v in n["qualification"].items() if v["state"]!="VERIFIED")
 expired=now>=datetime.fromisoformat(DEADLINE.replace("Z","+00:00"))
 complete=(not missing and n["opportunity"]["attachments_status"]=="COMPLETE" and n["proposal"]["attachments_complete"])
 prime="DEADLINE_PASSED" if expired else ("PRIME_QUALIFICATION_EVIDENCED_INTERNAL_REVIEW" if complete else "PRIME_HOLD")
 teaming="DEADLINE_PASSED" if expired else ("TEAMING_PACKAGE_READY_INTERNAL" if prime=="PRIME_HOLD" else "TEAMING_OPTIONAL_INTERNAL")
 out={"schema":"invest_appalachia_framer_lms.pursuit_receipt.v1","opportunity_id":OPPORTUNITY_ID,"prime_status":prime,"teaming_status":teaming,"unverified_or_missing_gates":missing,"attachments_status":n["opportunity"]["attachments_status"],"proposal_budget_within_cap":True,"submission_deadline_utc":DEADLINE,**{k:False for k in AUTH},"normalized_input_sha256":digest(n)}
 out["receipt_sha256"]=digest(out);return out

def load_json(path:Path)->Any:
 def pairs(items):
  d={}
  for k,v in items:
   if k in d:raise PursuitError(f"duplicate JSON key: {k}")
   d[k]=v
  return d
 try:return json.loads(path.read_text(encoding="utf-8"),object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(PursuitError(f"non-finite JSON: {x}")))
 except PursuitError:raise
 except (OSError,UnicodeError,json.JSONDecodeError,RecursionError,ValueError,TypeError) as e:raise PursuitError(f"invalid packet: {e}") from e
