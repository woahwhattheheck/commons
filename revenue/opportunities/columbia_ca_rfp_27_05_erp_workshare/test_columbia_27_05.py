from __future__ import annotations
import copy, unittest
from pathlib import Path
from columbia_27_05 import (
 AUTHORITY_FALSE,CASE_SCHEMA,ContractError,RETAINED_INTEGRATIONS,
 compile_evidence,evaluate_case,evaluate_matrix,strict_load,strict_loads,
 validate_manifest,verify_evidence,
)
ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/"fixtures"/"manifest.json"; CASES=ROOT/"fixtures"/"migration_cases.json"
AS_OF="2026-09-18T02:55:00Z"
def manifest(): return strict_load(MANIFEST)
def matrix(): return strict_load(CASES)
def base_case(**updates):
 r={
  "schema":CASE_SCHEMA,"case_id":"case-ready","batch_id":"batch-ready",
  "source_record_count":1200,"target_record_count":1200,
  "source_gl_debit_cents":350000000,"source_gl_credit_cents":350000000,
  "target_gl_debit_cents":350000000,"target_gl_credit_cents":350000000,
  "source_ap_cents":88000000,"target_ap_cents":88000000,
  "source_ar_cents":42000000,"target_ar_cents":42000000,
  "assessment_accounts_expected":27000,"assessment_accounts_loaded":27000,
  "assessment_amount_expected_cents":5000000000,"assessment_amount_loaded_cents":5000000000,
  "retained_integrations_expected":sorted(RETAINED_INTEGRATIONS),
  "retained_integrations_evidenced":sorted(RETAINED_INTEGRATIONS),
  "cutover_rehearsal_complete":True,"first_close_exception_register_present":True,
 }
 r.update(updates); return r

class CaseTests(unittest.TestCase):
 def test_ready_and_authority(self):
  x=evaluate_case(base_case()); self.assertEqual(x["decision"],"ACCEPT_OWNER_REVIEW_READY")
  for k in AUTHORITY_FALSE: self.assertFalse(x[k])
 def test_record_count(self): self.assertEqual(evaluate_case(base_case(target_record_count=1199))["decision"],"HOLD_RECORD_COUNT")
 def test_gl_total(self): self.assertEqual(evaluate_case(base_case(target_gl_credit_cents=349999999))["decision"],"HOLD_GL_CONTROL_TOTAL")
 def test_source_gl_unbalanced(self): self.assertEqual(evaluate_case(base_case(source_gl_credit_cents=349999999,target_gl_credit_cents=349999999))["decision"],"HOLD_GL_CONTROL_TOTAL")
 def test_ap(self): self.assertEqual(evaluate_case(base_case(target_ap_cents=87999999))["decision"],"HOLD_AP_CONTROL_TOTAL")
 def test_ar(self): self.assertEqual(evaluate_case(base_case(target_ar_cents=41999999))["decision"],"HOLD_AR_CONTROL_TOTAL")
 def test_assessment_count(self): self.assertEqual(evaluate_case(base_case(assessment_accounts_loaded=26999))["decision"],"HOLD_ASSESSMENT_ACCOUNT_COUNT")
 def test_assessment_amount(self): self.assertEqual(evaluate_case(base_case(assessment_amount_loaded_cents=4999999999))["decision"],"HOLD_ASSESSMENT_AMOUNT")
 def test_integration_missing(self):
  got=sorted(RETAINED_INTEGRATIONS)[:-1]; x=evaluate_case(base_case(retained_integrations_evidenced=got))
  self.assertEqual(x["decision"],"HOLD_RETAINED_INTEGRATION"); self.assertEqual(len(x["missing_retained_integrations"]),1)
 def test_unknown_integration_rejected(self):
  with self.assertRaises(ContractError): evaluate_case(base_case(retained_integrations_evidenced=sorted(RETAINED_INTEGRATIONS)+["invented"]))
 def test_cutover(self): self.assertEqual(evaluate_case(base_case(cutover_rehearsal_complete=False))["decision"],"HOLD_CUTOVER_REHEARSAL")
 def test_first_close(self): self.assertEqual(evaluate_case(base_case(first_close_exception_register_present=False))["decision"],"HOLD_FIRST_CLOSE_READINESS")
 def test_bool_int_alias_rejected(self):
  with self.assertRaises(ContractError): evaluate_case(base_case(cutover_rehearsal_complete=1))
 def test_unknown_key_rejected(self):
  r=base_case(); r["portal_submit"]=True
  with self.assertRaises(ContractError): evaluate_case(r)
 def test_key_order_deterministic(self):
  r=base_case(); self.assertEqual(evaluate_case(r),evaluate_case(dict(reversed(list(r.items())))))

class MatrixTests(unittest.TestCase):
 def test_terminal_coverage(self):
  x=evaluate_matrix(matrix()); self.assertEqual(x["case_count"],10); self.assertTrue(all(v==1 for v in x["decision_counts"].values()))
 def test_expected_mismatch(self):
  d=matrix(); d["cases"][0]["expected_decision"]="HOLD_AP_CONTROL_TOTAL"
  with self.assertRaises(ContractError): evaluate_matrix(d)
 def test_duplicate_case(self):
  d=matrix(); d["cases"][1]["case"]["case_id"]=d["cases"][0]["case"]["case_id"]
  with self.assertRaises(ContractError): evaluate_matrix(d)
 def test_duplicate_batch(self):
  d=matrix(); d["cases"][1]["case"]["batch_id"]=d["cases"][0]["case"]["batch_id"]
  with self.assertRaises(ContractError): evaluate_matrix(d)
 def test_missing_terminal(self):
  d=matrix(); d["cases"]=[x for x in d["cases"] if x["expected_decision"]!="HOLD_FIRST_CLOSE_READINESS"]
  with self.assertRaises(ContractError): evaluate_matrix(d)

class ManifestTests(unittest.TestCase):
 def test_live_window_review_only(self):
  x=validate_manifest(manifest(),AS_OF)
  self.assertEqual((x["question_window_state"],x["proposal_window_state"],x["teaming_build_state"]),("OPEN","OPEN","READY"))
  self.assertEqual(x["submission_state"],"OWNER_AND_PRIME_ACTION_REQUIRED"); self.assertEqual(x["commercial_offer_state"],"PROPOSED_NOT_ACCEPTED")
  for k in AUTHORITY_FALSE: self.assertFalse(x[k])
 def test_questions_close_first(self):
  x=validate_manifest(manifest(),"2026-10-16T20:00:00Z")
  self.assertEqual((x["question_window_state"],x["proposal_window_state"],x["teaming_build_state"]),("CLOSED","OPEN","READY"))
 def test_proposal_deadline_holds(self):
  x=validate_manifest(manifest(),"2026-10-27T18:00:00Z"); self.assertEqual(x["teaming_build_state"],"HOLD_RESPONSE_WINDOW")
 def test_deadline_drift(self):
  d=manifest(); d["solicitation"]["proposal_due_utc"]="2026-10-27T19:00:00Z"
  with self.assertRaises(ContractError): validate_manifest(d,AS_OF)
 def test_source_drift(self):
  d=manifest(); d["sources"]["portal"]["url"]="https://example.com/"
  with self.assertRaises(ContractError): validate_manifest(d,AS_OF)
 def test_future_source(self):
  d=manifest(); d["sources"]["rfp_mirror"]["captured_at_utc"]="2026-09-18T02:56:00Z"
  with self.assertRaises(ContractError): validate_manifest(d,AS_OF)
 def test_offer_self_accept(self):
  d=manifest(); d["commercial_offer"]["state"]="ACCEPTED"
  with self.assertRaises(ContractError): validate_manifest(d,AS_OF)
 def test_offer_send(self):
  d=manifest(); d["commercial_offer"]["external_send_authorized"]=True
  with self.assertRaises(ContractError): validate_manifest(d,AS_OF)
 def test_price_drift(self):
  d=manifest(); d["commercial_offer"]["base_price_usd_cents"]+=1
  with self.assertRaises(ContractError): validate_manifest(d,AS_OF)
 def test_authority_self_promotion(self):
  for k in AUTHORITY_FALSE:
   d=manifest(); d["authority"][k]=True
   with self.subTest(k=k):
    with self.assertRaises(ContractError): validate_manifest(d,AS_OF)
 def test_mbe_is_reference_not_certification(self):
  d=manifest(); self.assertEqual(d["research_references"]["mandatory_mbe_participation_bps"],2300); self.assertFalse(d["authority"]["certification_assertion_authorized"])
 def test_duplicate_json(self):
  with self.assertRaises(ContractError): strict_loads('{"a":1,"a":2}')
 def test_nonfinite_json(self):
  with self.assertRaises(ContractError): strict_loads('{"a":NaN}')

class BundleTests(unittest.TestCase):
 def test_bundle_recomputes(self):
  b=compile_evidence(manifest(),matrix(),AS_OF); self.assertEqual(b["teaming_review_verdict"],"READY_FOR_PAID_TEAMING_REVIEW")
  self.assertEqual(b["submission_verdict"],"OWNER_AND_PRIME_ACTION_REQUIRED"); self.assertTrue(verify_evidence(b,manifest(),matrix(),AS_OF))
 def test_tamper_detected(self):
  b=compile_evidence(manifest(),matrix(),AS_OF); f=copy.deepcopy(b); f["submission_verdict"]="READY"
  self.assertFalse(verify_evidence(f,manifest(),matrix(),AS_OF))
 def test_manifest_transplant_rejected(self):
  b=compile_evidence(manifest(),matrix(),AS_OF); d=manifest(); d["research_references"]["annual_assessment_transactions_reference"]=27001
  with self.assertRaises(ContractError): verify_evidence(b,d,matrix(),AS_OF)

if __name__=="__main__": unittest.main()
