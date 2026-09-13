from __future__ import annotations
import copy,json,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from preflight import *
HERE=Path(__file__).resolve().parent; SOURCE=json.loads((HERE/"source_snapshot.json").read_text()); NOW=datetime(2026,9,13,10,30,tzinfo=timezone.utc)
def owner():
 return {"schema":OWNER_SCHEMA,"organization":{"legal_name":"Example Consulting LLC","mission":"Evidence-backed operations.","website":"https://example.invalid","boston_community_knowledge":"No Boston-specific experience asserted; preference gap acknowledged."},"selected_tracks":["Communications"],"track_count_ambiguity_reviewed":True,"deadline_time_label_reviewed":True,"qualifying_experience":[{"engagement_name":"Owner-verified nonprofit project","category":"nonprofit","client_type":"nonprofit","scope":"Owner-verified scope.","outcomes":"Owner-verified outcome.","evidence_ref":"private-evidence-001"}],"references":[{"reference_id":"a","organization":"Org A","relationship":"Similar engagement","contact_delivery_plan":"Owner supplies privately."},{"reference_id":"b","organization":"Org B","relationship":"Similar engagement","contact_delivery_plan":"Owner supplies privately."}],"team":[{"role":"Lead","staffing_summary":"Confirmed owner-selected lead.","evidence_ref":"private-staff-001"}],"pricing":{"basis":"Hourly","schedule":"Owner-approved private schedule.","owner_approved":True},"dei_approach":"Owner-supplied actual approach.","service_request_tracking":"Owner-supported electronic tracking.","living_wage_obligation_reviewed":True,"sam_exclusion_requirement_reviewed":True,"track_answers":{"Communications":["A","B","C","D"]},"page_plan":{"organizational_overview_and_mission":1,"experience_and_qualifications":2,"dei_approach":1,"selected_track_answers":{"Communications":4},"team_and_staffing":2,"pricing":1}}
class T(unittest.TestCase):
 def ev(self,o=None,s=None,now=NOW): return evaluate(copy.deepcopy(SOURCE if s is None else s),owner() if o is None else o,trusted_now=now)
 def test_01_ready(self): self.assertEqual(self.ev()["state"],READY); self.assertTrue(all(v is False for v in self.ev()["authority"].values()))
 def test_02_template_hold(self): self.assertEqual(self.ev(json.loads((HERE/"owner_inputs.template.json").read_text()))["state"],OWNER_HOLD)
 def test_03_experience(self): o=owner();o["qualifying_experience"][0]["category"]="commercial";self.assertIn("QUALIFYING_PUBLIC_HEALTH_NONPROFIT_OR_GOVERNMENT_EXPERIENCE_REQUIRED",self.ev(o)["blockers"])
 def test_04_two_refs(self): o=owner();o["references"].pop();self.assertIn("TWO_PROFESSIONAL_REFERENCES_REQUIRED",self.ev(o)["blockers"])
 def test_05_ref_unique(self): o=owner();o["references"][1]["reference_id"]="a";self.assertIn("REFERENCE_IDS_MUST_BE_UNIQUE",self.ev(o)["blockers"])
 def test_06_team(self): o=owner();o["team"]=[];self.assertIn("TEAM_AND_STAFFING_REQUIRED",self.ev(o)["blockers"])
 def test_07_pricing(self): o=owner();o["pricing"]["schedule"]="TBD";self.assertIn("PRICING_REQUIRED",self.ev(o)["blockers"])
 def test_08_price_approval(self): o=owner();o["pricing"]["owner_approved"]=False;self.assertIn("PRICING_OWNER_APPROVAL_REQUIRED",self.ev(o)["blockers"])
 def test_09_dei(self): o=owner();o["dei_approach"]="OWNER_INPUT_REQUIRED";self.assertIn("DEI_APPROACH_REQUIRED",self.ev(o)["blockers"])
 def test_10_tracks(self): o=owner();o["selected_tracks"]=[];self.assertIn("SELECT_AT_LEAST_ONE_TRACK",self.ev(o)["blockers"])
 def test_11_unknown_track(self): o=owner();o["selected_tracks"]=["Magic"];self.assertTrue(any(x.startswith("UNKNOWN_SELECTED_TRACK") for x in self.ev(o)["blockers"]))
 def test_12_dup_track(self): o=owner();o["selected_tracks"]=["Communications"]*2;self.assertIn("DUPLICATE_SELECTED_TRACK",self.ev(o)["blockers"])
 def test_13_answers(self): o=owner();o["track_answers"]["Communications"].pop();self.assertIn("TRACK_ANSWERS_INCOMPLETE:Communications",self.ev(o)["blockers"])
 def test_14_stray_answers(self): o=owner();o["track_answers"]["Magic"]=["x"];self.assertTrue(any(x.startswith("UNKNOWN_TRACK_ANSWER_SET") for x in self.ev(o)["blockers"]))
 def test_15_track_ambiguity(self): o=owner();o["track_count_ambiguity_reviewed"]=False;self.assertIn("REVIEW_FOUR_TRACKS_VS_ALL_THREE_SOURCE_AMBIGUITY",self.ev(o)["blockers"])
 def test_16_est_review(self): o=owner();o["deadline_time_label_reviewed"]=False;self.assertIn("REVIEW_SOURCE_EST_TIMEZONE_LABEL",self.ev(o)["blockers"])
 def test_17_wage(self): o=owner();o["living_wage_obligation_reviewed"]=False;self.assertIn("LIVING_WAGE_OBLIGATION_REVIEW_REQUIRED",self.ev(o)["blockers"])
 def test_18_sam(self): o=owner();o["sam_exclusion_requirement_reviewed"]=False;self.assertIn("SAM_EXCLUSION_REQUIREMENT_REVIEW_REQUIRED",self.ev(o)["blockers"])
 def test_19_page(self): o=owner();o["page_plan"]["pricing"]=2;self.assertIn("PAGE_LIMIT_EXCEEDED:pricing",self.ev(o)["blockers"])
 def test_20_track_page(self): o=owner();o["page_plan"]["selected_track_answers"]["Communications"]=6;self.assertIn("TRACK_PAGE_LIMIT_EXCEEDED:Communications",self.ev(o)["blockers"])
 def test_21_bool_page(self): o=owner();o["page_plan"]["pricing"]=True;self.assertIn("PAGE_PLAN_PRICING_REQUIRED",self.ev(o)["blockers"])
 def test_22_stale(self): self.assertEqual(self.ev(now=NOW+timedelta(days=7,seconds=1))["state"],SOURCE_HOLD)
 def test_23_future_source(self): s=copy.deepcopy(SOURCE);s["checked_at"]="2026-09-13T10:31:00Z";self.assertRaises(PreflightError,self.ev,None,s,NOW)
 def test_24_deadline(self): s=copy.deepcopy(SOURCE);s["checked_at"]="2026-09-30T21:59:00Z";self.assertEqual(self.ev(s=s,now=datetime(2026,9,30,22,0,1,tzinfo=timezone.utc))["state"],DEADLINE_HOLD)
 def test_25_naive_time(self): self.assertRaises(PreflightError,evaluate,copy.deepcopy(SOURCE),owner(),trusted_now=datetime(2026,9,13))
 def test_26_duplicate_json(self): self.assertRaises(PreflightError,load_json_bytes,b'{"x":1,"x":2}',"x")
 def test_27_nan(self): self.assertRaises(PreflightError,load_json_bytes,b'{"x":NaN}',"x")
 def test_28_digest(self): self.assertEqual(digest(copy.deepcopy(SOURCE)),digest(copy.deepcopy(SOURCE)))
 def test_29_tamper_digest(self): s=copy.deepcopy(SOURCE);d=digest(s);s["pool_term_max_years"]=4;self.assertNotEqual(d,digest(s))
 def test_30_fake_pdf_digest(self): s=copy.deepcopy(SOURCE);s["rfp_pdf_bytes_locally_acquired"]=True;self.assertRaises(PreflightError,self.ev,None,s,NOW)
 def test_31_no_guarantee(self): s=copy.deepcopy(SOURCE);s["inclusion_guarantees_work"]=True;self.assertRaises(PreflightError,self.ev,None,s,NOW)
 def test_32_authority(self): s=copy.deepcopy(SOURCE);s["authority"]["submission_authorized"]=True;self.assertRaises(PreflightError,self.ev,None,s,NOW)
 def test_33_nested_placeholder(self): o=owner();o["track_answers"]["Communications"][1]="TODO";self.assertEqual(self.ev(o)["state"],OWNER_HOLD)
 def test_34_four_tracks(self):
  o=owner();o["selected_tracks"]=list(SOURCE["tracks"]);o["track_answers"]={t:[f"{t}-{i}" for i in range(4)] for t in SOURCE["tracks"]};o["page_plan"]["selected_track_answers"]={t:5 for t in SOURCE["tracks"]};self.assertEqual(self.ev(o)["state"],READY)
 def test_35_receipt_hash(self): o=owner();a=self.ev(o)["receipt_sha256"];o["organization"]["legal_name"]="Different LLC";self.assertNotEqual(a,self.ev(o)["receipt_sha256"])
if __name__=="__main__": unittest.main()
