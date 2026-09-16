from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

OPPORTUNITY_ID="INVEST-APPALACHIA-FRAMER-LMS-20260916"
BUYER="Invest Appalachia"; DEADLINE="2026-09-22T21:00:00Z"; CAP=60000
START="2026-10-13"; END="2027-04-30"
SOURCE="https://investappalachia.org/framer-rfp/"
RFP="https://investappalachia.org/wp-content/uploads/2026/08/1.-draft2_RFP_Invest_Appalachia_Framer_Training_LMS.docx.pdf"
ZIP="https://investappalachia.org/wp-content/uploads/2026/08/Zipped-RFP-Docs.zip"
SUBJECT="RFP Proposal Submission - Invest Appalachia Framer Training LMS"
CURRENT_PACKET_SHA256="13018ee1b2fe14b3b8171acc734e0ea57a52006a5e96f095600e88bcbca63a02"
GATES=("two_lms_platform_implementations","adult_learning_packaging","start_capacity_2026_10_13","w9_available","general_liability_available","professional_liability_available","cybersecurity_insurance_available","two_relevant_project_examples","two_prior_client_references")
AUTH=("external_contact_authorized","submission_authorized","signature_authorized","contract_acceptance_authorized","spend_authorized","payment_authorized","award_or_revenue_asserted")
class PursuitError(ValueError): pass

def canon(v:Any)->bytes:
 try:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8","strict")
 except (TypeError,ValueError,UnicodeError,RecursionError,OverflowError) as e:raise PursuitError(f"cannot canonicalize packet: {e}") from e
def digest(v:Any)->str:
 try:return hashlib.sha256(canon(v)).hexdigest()
 except PursuitError:raise
 except (TypeError,ValueError,OverflowError) as e:raise PursuitError(f"cannot digest packet: {e}") from e
def exact(v:Any,keys:set[str],where:str):
 if type(v) is not dict: raise PursuitError(f"{where} must be object")
 if set(v)!=keys: raise PursuitError(f"{where} keys mismatch")
 return v

def normalize(raw:Any)->dict[str,Any]:
 # This carrier is a current retained-evidence snapshot, not a caller-authored
 # qualification form. Any evidence/status change requires a new reviewed source
 # generation and a new code-owned packet digest.
 if digest(raw)!=CURRENT_PACKET_SHA256:raise PursuitError("packet does not match retained current qualification generation")
 p=exact(raw,{"opportunity","qualification","proposal","authority"},"packet")
 o=exact(p["opportunity"],{"opportunity_id","buyer","source_url","rfp_url","attachments_zip_url","deadline_utc","budget_cap_usd","contract_start","contract_end","submission_subject","attachments_status"},"opportunity")
 expected=(OPPORTUNITY_ID,BUYER,SOURCE,RFP,ZIP,DEADLINE,CAP,START,END,SUBJECT,"PARTIAL")
 actual=(o["opportunity_id"],o["buyer"],o["source_url"],o["rfp_url"],o["attachments_zip_url"],o["deadline_utc"],o["budget_cap_usd"],o["contract_start"],o["contract_end"],o["submission_subject"],o["attachments_status"])
 if actual!=expected: raise PursuitError("official opportunity/current-attachment binding mismatch")
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
 if pr["attachments_complete"] is not False:raise PursuitError("buyer attachments are not retained complete in this generation")
 a=exact(p["authority"],set(AUTH),"authority")
 if any(type(a[k]) is not bool for k in AUTH) or any(a.values()):raise PursuitError("all external/commercial authority must remain false")
 return {"opportunity":dict(o),"qualification":nq,"proposal":dict(pr),"authority":dict(a)}

def evaluate(raw:Any)->dict[str,Any]:
 n=normalize(raw)
 missing=sorted(k for k,v in n["qualification"].items() if v["state"]!="VERIFIED")
 # Current retained generation is intentionally unpriced and lacks buyer
 # Attachment C, so it cannot truthfully assert a positive within-cap result.
 budget_status="HOLD_UNPRICED_ATTACHMENTS_INCOMPLETE"
 out={"schema":"invest_appalachia_framer_lms.pursuit_receipt.v2","opportunity_id":OPPORTUNITY_ID,"prime_status":"PRIME_HOLD","teaming_status":"TEAMING_ROUTE_OPEN_INTERNAL","unverified_or_missing_gates":missing,"attachments_status":"PARTIAL","proposal_budget_status":budget_status,"proposal_budget_within_cap":False,"submission_deadline_utc":DEADLINE,"deadline_currentness_authoritative":False,"fresh_deadline_recensus_required_before_action":True,"qualification_generation_sha256":CURRENT_PACKET_SHA256,**{k:False for k in AUTH},"normalized_input_sha256":digest(n)}
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
