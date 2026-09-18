from __future__ import annotations
import hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCHEMA="tjlabs.columbia-ca-rfp27-05-workshare/v1"
CASE_SCHEMA="tjlabs.erp-migration-acceptance-case/v1"
MATRIX_SCHEMA="tjlabs.erp-migration-acceptance-matrix/v1"
RESULT_SCHEMA="tjlabs.erp-migration-acceptance-result/v1"
BUNDLE_SCHEMA="tjlabs.columbia-ca-rfp27-05-evidence-bundle/v1"
SOLICITATION_ID="27-05"; BUYER="Columbia Association"
TITLE="Enterprise Resource Planning (ERP) Software and Services"
ISSUED_DATE="2026-09-08"; QUESTIONS_DUE_UTC="2026-10-16T20:00:00Z"
PROPOSAL_DUE_UTC="2026-10-27T18:00:00Z"; TARGET_GO_LIVE_DATE="2027-05-01"
PORTAL_URL="https://vendors.planetbids.com/portal/77636/portal-home"
RFP_MIRROR_URL="https://govtribe.com/file/government-file/rfp-27-05-erp-software-and-services-9-dot-8-dot-26-dot-pdf"
OPPORTUNITY_URL="https://govtribe.com/opportunity/state-local-contract-opportunity/enterprise-resource-planning-erp-software-and-services-142927"
OFFER_NAME="ERP Migration & Financial Reconciliation Acceptance Workshare"
BASE_PRICE_USD_CENTS=1800000; EXTENSION_PRICE_USD_CENTS=600000
RETAINED_INTEGRATIONS=("Dayforce","Club Automation","Smartsheet","ESRI","8x8/Diagenix IVR")
AUTHORITY_FALSE={
 "buyer_contact_authorized":False,"partner_contact_authorized":False,
 "portal_registration_authorized":False,"portal_submission_authorized":False,
 "contract_acceptance_authorized":False,"production_erp_write_authorized":False,
 "payment_authorized":False,"certification_assertion_authorized":False,
 "revenue_recognized":False,
}
TERMINAL_DECISIONS=(
 "ACCEPT_OWNER_REVIEW_READY","HOLD_RECORD_COUNT","HOLD_GL_CONTROL_TOTAL",
 "HOLD_AP_CONTROL_TOTAL","HOLD_AR_CONTROL_TOTAL","HOLD_ASSESSMENT_ACCOUNT_COUNT",
 "HOLD_ASSESSMENT_AMOUNT","HOLD_RETAINED_INTEGRATION","HOLD_CUTOVER_REHEARSAL",
 "HOLD_FIRST_CLOSE_READINESS",
)
CASE_KEYS={
 "schema","case_id","batch_id","source_record_count","target_record_count",
 "source_gl_debit_cents","source_gl_credit_cents","target_gl_debit_cents","target_gl_credit_cents",
 "source_ap_cents","target_ap_cents","source_ar_cents","target_ar_cents",
 "assessment_accounts_expected","assessment_accounts_loaded",
 "assessment_amount_expected_cents","assessment_amount_loaded_cents",
 "retained_integrations_expected","retained_integrations_evidenced",
 "cutover_rehearsal_complete","first_close_exception_register_present",
}
ID_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
class ContractError(ValueError): pass

def _pairs(pairs):
 out={}
 for k,v in pairs:
  if k in out: raise ContractError(f"duplicate JSON key: {k}")
  out[k]=v
 return out
def strict_loads(text):
 return json.loads(text,object_pairs_hook=_pairs,parse_constant=lambda x:(_ for _ in ()).throw(ContractError(f"non-finite number: {x}")))
def strict_load(path): return strict_loads(Path(path).read_text(encoding="utf-8"))
def canonical_json(v): return (json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
def _receipt(p):
 out=dict(p); out["receipt_sha256"]=hashlib.sha256(canonical_json(p)).hexdigest(); return out
def _keys(v,keys,w):
 if type(v) is not dict or set(v)!=keys:
  actual=set(v) if type(v) is dict else set()
  raise ContractError(f"{w}: key mismatch missing={sorted(keys-actual)} extra={sorted(actual-keys)}")
 return v
def _text(v,w,n=512):
 if type(v) is not str or not v or len(v)>n: raise ContractError(f"{w}: bounded string required")
 return v
def _ident(v,w):
 v=_text(v,w,96)
 if not ID_RE.fullmatch(v): raise ContractError(f"{w}: safe identifier required")
 return v
def _bool(v,w):
 if type(v) is not bool: raise ContractError(f"{w}: bool required")
 return v
def _int(v,w,lo=0,hi=10**18):
 if type(v) is not int or not lo<=v<=hi: raise ContractError(f"{w}: bounded int required")
 return v
def _utc(v,w):
 v=_text(v,w,32)
 if not v.endswith("Z"): raise ContractError(f"{w}: UTC Z required")
 try: d=datetime.fromisoformat(v[:-1]+"+00:00")
 except ValueError as e: raise ContractError(f"{w}: invalid timestamp") from e
 if d.tzinfo!=timezone.utc: raise ContractError(f"{w}: UTC required")
 return d
def _https(v,w):
 v=_text(v,w,600); p=urlparse(v)
 if p.scheme!="https" or not p.hostname or p.username or p.password or p.fragment: raise ContractError(f"{w}: canonical HTTPS required")
 return v
def _slist(v,w):
 if type(v) is not list or not v: raise ContractError(f"{w}: list required")
 out=[_text(x,f"{w}[{i}]",96) for i,x in enumerate(v)]
 if len(out)!=len(set(out)) or out!=sorted(out): raise ContractError(f"{w}: unique sorted list required")
 return out

def evaluate_case(case:Any)->dict[str,Any]:
 r=_keys(case,CASE_KEYS,"case")
 if r["schema"]!=CASE_SCHEMA: raise ContractError("case.schema")
 cid=_ident(r["case_id"],"case.case_id"); bid=_ident(r["batch_id"],"case.batch_id")
 sr=_int(r["source_record_count"],"source_record_count",1); tr=_int(r["target_record_count"],"target_record_count")
 sgd=_int(r["source_gl_debit_cents"],"source_gl_debit_cents"); sgc=_int(r["source_gl_credit_cents"],"source_gl_credit_cents")
 tgd=_int(r["target_gl_debit_cents"],"target_gl_debit_cents"); tgc=_int(r["target_gl_credit_cents"],"target_gl_credit_cents")
 sap=_int(r["source_ap_cents"],"source_ap_cents"); tap=_int(r["target_ap_cents"],"target_ap_cents")
 sar=_int(r["source_ar_cents"],"source_ar_cents"); tar=_int(r["target_ar_cents"],"target_ar_cents")
 aae=_int(r["assessment_accounts_expected"],"assessment_accounts_expected"); aal=_int(r["assessment_accounts_loaded"],"assessment_accounts_loaded")
 ame=_int(r["assessment_amount_expected_cents"],"assessment_amount_expected_cents"); aml=_int(r["assessment_amount_loaded_cents"],"assessment_amount_loaded_cents")
 exp=_slist(r["retained_integrations_expected"],"retained_integrations_expected")
 got=_slist(r["retained_integrations_evidenced"],"retained_integrations_evidenced")
 if exp!=sorted(RETAINED_INTEGRATIONS): raise ContractError("retained_integrations_expected: contract drift")
 if set(got)-set(exp): raise ContractError("retained_integrations_evidenced: unknown integration")
 cut=_bool(r["cutover_rehearsal_complete"],"cutover_rehearsal_complete")
 close=_bool(r["first_close_exception_register_present"],"first_close_exception_register_present")
 if tr!=sr: d="HOLD_RECORD_COUNT"
 elif tgd!=sgd or tgc!=sgc or sgd!=sgc or tgd!=tgc: d="HOLD_GL_CONTROL_TOTAL"
 elif tap!=sap: d="HOLD_AP_CONTROL_TOTAL"
 elif tar!=sar: d="HOLD_AR_CONTROL_TOTAL"
 elif aal!=aae: d="HOLD_ASSESSMENT_ACCOUNT_COUNT"
 elif aml!=ame: d="HOLD_ASSESSMENT_AMOUNT"
 elif got!=exp: d="HOLD_RETAINED_INTEGRATION"
 elif not cut: d="HOLD_CUTOVER_REHEARSAL"
 elif not close: d="HOLD_FIRST_CLOSE_READINESS"
 else: d="ACCEPT_OWNER_REVIEW_READY"
 return _receipt({
  "schema":RESULT_SCHEMA,"case_id":cid,"batch_id":bid,"decision":d,
  "record_delta":tr-sr,"gl_debit_delta_cents":tgd-sgd,"gl_credit_delta_cents":tgc-sgc,
  "ap_delta_cents":tap-sap,"ar_delta_cents":tar-sar,
  "assessment_account_delta":aal-aae,"assessment_amount_delta_cents":aml-ame,
  "missing_retained_integrations":sorted(set(exp)-set(got)),**AUTHORITY_FALSE,
 })

def evaluate_matrix(doc:Any)->dict[str,Any]:
 m=_keys(doc,{"schema","cases"},"matrix")
 if m["schema"]!=MATRIX_SCHEMA or type(m["cases"]) is not list or len(m["cases"])<len(TERMINAL_DECISIONS): raise ContractError("matrix: terminal coverage required")
 counts={d:0 for d in TERMINAL_DECISIONS}; results=[]; cids=set(); bids=set()
 for i,raw in enumerate(m["cases"]):
  row=_keys(raw,{"expected_decision","case"},f"matrix.cases[{i}]"); exp=_text(row["expected_decision"],"expected_decision",64)
  if exp not in counts: raise ContractError("matrix: unsupported expected decision")
  res=evaluate_case(row["case"])
  if res["case_id"] in cids or res["batch_id"] in bids: raise ContractError("matrix: duplicate identity")
  cids.add(res["case_id"]); bids.add(res["batch_id"])
  if res["decision"]!=exp: raise ContractError(f"matrix: expected {exp}, got {res['decision']}")
  counts[exp]+=1; results.append(res)
 if any(v==0 for v in counts.values()): raise ContractError("matrix: missing terminal")
 return _receipt({"schema":MATRIX_SCHEMA,"case_count":len(results),"decision_counts":counts,"results":results,**AUTHORITY_FALSE})

def validate_manifest(manifest:Any,trusted_as_of:str)->dict[str,Any]:
 d=_keys(manifest,{"schema","solicitation","sources","research_references","commercial_offer","authority"},"manifest")
 if d["schema"]!=SCHEMA: raise ContractError("manifest.schema")
 sol=_keys(d["solicitation"],{"id","buyer","title","issued_date","questions_due_utc","proposal_due_utc","target_go_live_date"},"solicitation")
 expected={"id":SOLICITATION_ID,"buyer":BUYER,"title":TITLE,"issued_date":ISSUED_DATE,"questions_due_utc":QUESTIONS_DUE_UTC,"proposal_due_utc":PROPOSAL_DUE_UTC,"target_go_live_date":TARGET_GO_LIVE_DATE}
 if sol!=expected: raise ContractError("solicitation: controlling facts drift")
 q=_utc(sol["questions_due_utc"],"questions_due"); p=_utc(sol["proposal_due_utc"],"proposal_due")
 if q>=p: raise ContractError("questions deadline")
 src=_keys(d["sources"],{"portal","rfp_mirror","opportunity"},"sources")
 specs={
  "portal":(PORTAL_URL,"OFFICIAL_PROCUREMENT_PORTAL"),
  "rfp_mirror":(RFP_MIRROR_URL,"PUBLIC_RESEARCH_MIRROR_NOT_SUBMISSION_AUTHORITY"),
  "opportunity":(OPPORTUNITY_URL,"PUBLIC_RESEARCH_SUMMARY_NOT_SUBMISSION_AUTHORITY"),
 }
 asof=_utc(trusted_as_of,"trusted_as_of")
 for k,(url,role) in specs.items():
  s=_keys(src[k],{"url","captured_at_utc","role"},f"sources.{k}")
  if _https(s["url"],f"{k}.url")!=url or s["role"]!=role: raise ContractError(f"sources.{k}: drift")
  if _utc(s["captured_at_utc"],f"{k}.captured")>asof: raise ContractError(f"sources.{k}: future")
 refs=_keys(d["research_references"],{"legacy_erp","retained_integrations","annual_assessment_transactions_reference","annual_assessment_revenue_reference_cents","mandatory_mbe_participation_bps","implementation_only_prime_allowed"},"research_references")
 if refs["legacy_erp"]!="Infor Lawson V10" or _slist(refs["retained_integrations"],"retained_integrations")!=sorted(RETAINED_INTEGRATIONS): raise ContractError("research references: drift")
 if _int(refs["annual_assessment_transactions_reference"],"annual_assessment_transactions",1)!=27000: raise ContractError("assessment transactions: drift")
 if _int(refs["annual_assessment_revenue_reference_cents"],"assessment revenue",1)!=5000000000: raise ContractError("assessment revenue: drift")
 if _int(refs["mandatory_mbe_participation_bps"],"mbe",0,10000)!=2300 or _bool(refs["implementation_only_prime_allowed"],"implementation_only_prime_allowed") is not False: raise ContractError("prime/MBE reference: drift")
 offer=_keys(d["commercial_offer"],{"state","name","base_price_usd_cents","optional_extension_price_usd_cents","acceptance","external_send_authorized"},"commercial_offer")
 if offer["state"]!="PROPOSED_NOT_ACCEPTED" or offer["name"]!=OFFER_NAME: raise ContractError("offer: state/name drift")
 if _int(offer["base_price_usd_cents"],"base_price",1)!=BASE_PRICE_USD_CENTS or _int(offer["optional_extension_price_usd_cents"],"extension_price")!=EXTENSION_PRICE_USD_CENTS: raise ContractError("offer: price drift")
 _text(offer["acceptance"],"acceptance",1600)
 if _bool(offer["external_send_authorized"],"external_send_authorized") is not False: raise ContractError("offer: send must remain false")
 auth=_keys(d["authority"],set(AUTHORITY_FALSE),"authority")
 for k in AUTHORITY_FALSE:
  if _bool(auth[k],k) is not False: raise ContractError(f"authority.{k}: must remain false")
 facts={"id":SOLICITATION_ID,"buyer":BUYER,"title":TITLE,"issued_date":ISSUED_DATE,"questions_due_utc":QUESTIONS_DUE_UTC,"proposal_due_utc":PROPOSAL_DUE_UTC,"target_go_live_date":TARGET_GO_LIVE_DATE,"portal_url":PORTAL_URL,"rfp_mirror_url":RFP_MIRROR_URL,"opportunity_url":OPPORTUNITY_URL}
 return _receipt({
  "schema":SCHEMA,"solicitation_id":SOLICITATION_ID,"buyer":BUYER,
  "source_facts_sha256":hashlib.sha256(canonical_json(facts)).hexdigest(),
  "question_window_state":"OPEN" if asof<q else "CLOSED",
  "proposal_window_state":"OPEN" if asof<p else "CLOSED",
  "teaming_build_state":"READY" if asof<p else "HOLD_RESPONSE_WINDOW",
  "submission_state":"OWNER_AND_PRIME_ACTION_REQUIRED",
  "commercial_offer_state":offer["state"],"base_price_usd_cents":BASE_PRICE_USD_CENTS,
  "optional_extension_price_usd_cents":EXTENSION_PRICE_USD_CENTS,**AUTHORITY_FALSE,
 })

def compile_evidence(manifest:Any,matrix:Any,trusted_as_of:str)->dict[str,Any]:
 pursuit=validate_manifest(manifest,trusted_as_of); acc=evaluate_matrix(matrix)
 return _receipt({"schema":BUNDLE_SCHEMA,"solicitation_id":SOLICITATION_ID,"pursuit":pursuit,"acceptance_matrix":acc,
  "teaming_review_verdict":"READY_FOR_PAID_TEAMING_REVIEW" if pursuit["teaming_build_state"]=="READY" else "HOLD_RESPONSE_WINDOW",
  "submission_verdict":pursuit["submission_state"],**AUTHORITY_FALSE})
def verify_evidence(bundle:Any,manifest:Any,matrix:Any,trusted_as_of:str)->bool:
 return type(bundle) is dict and canonical_json(bundle)==canonical_json(compile_evidence(manifest,matrix,trusted_as_of))
