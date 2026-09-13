from __future__ import annotations
import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from preflight import *

HERE = Path(__file__).resolve().parent
SOURCE = json.loads((HERE / "source_snapshot.json").read_text())
TEMPLATE = json.loads((HERE / "owner_inputs.template.json").read_text())
NOW = datetime(2026, 9, 13, 11, 0, tzinfo=timezone.utc)

def ready_source():
    s = copy.deepcopy(SOURCE)
    s["rfi_pdf_bytes_acquired"] = True
    s["rfi_pdf_sha256"] = "a" * 64
    s["source_extraction_receipt"]["raw_byte_hash_available"] = True
    return s

def direct_owner():
    return {
        "schema": OWNER_SCHEMA,
        "route": "DIRECT_RFI",
        "contact": {"name": "Owner Name", "title": "Lead", "organization": "Example Org", "email": "owner@example.invalid", "phone": "+1-555-0100"},
        "project_title": "Evidence-Bound Career Navigation",
        "focus_areas": ["Career Navigation and Job Placement", "Personalized Support"],
        "maturity": "Concept",
        "population": {"description": "Adult workers in an owner-verified partner program.", "estimated_size_2027_2028": 120, "evidence_ref": "private-population-plan-001"},
        "drafts": {
            "organizational_background": "Owner-verified organization background and workforce expertise.",
            "innovation_overview": "A human-supervised AI career-navigation concept with evidence receipts and bounded tools.",
            "workforce_challenge": "Workers face fragmented information and constrained coaching time.",
            "learning_questions": "Which tasks benefit from AI, for whom, and under which human oversight conditions?",
            "population_of_focus": "Adult workers served by the verified program, with an owner-supported 2027 to 2028 cohort estimate.",
            "technical_approach": "Bounded language-model workflows, approved sources, provenance, human override, and deterministic telemetry.",
            "early_results": "No workforce outcome claims are asserted; this submission is concept stage.",
            "responsible_ai": "Fairness checks, bias review, transparency, privacy minimization, human authority, and versioned governance are planned.",
            "air_partnership": "AIR could co-design the evaluation, pre-analysis plan, implementation study, and field-learning products."
        },
        "direct_workforce_track_record": [{
            "record_id": "direct-1", "population": "Adult learners", "workforce_service": "Career readiness and job-entry support", "period": "2025-2026", "evidence_ref": "private-track-001", "evidence_sha256": "b" * 64
        }],
        "partner": {"organization": "PARTNER_INPUT_REQUIRED", "role": "PARTNER_INPUT_REQUIRED", "commitment_evidence_ref": "PARTNER_INPUT_REQUIRED", "workforce_track_record": []},
        "responsible_ai_controls": {
            "fairness": "Pre-specified subgroup error and usefulness analysis.",
            "bias": "Error taxonomy and differential-impact review.",
            "transparency": "Participants are told when AI is involved and when humans review it.",
            "privacy": "Minimize fields, separate identity from telemetry, and bind retention limits.",
            "governance": "Version models, prompts, tools, policies, and incident decisions."
        },
        "evidence_design": {
            "outcomes": "Partner-defined verified service and labor-market milestones.",
            "comparison_design": "Randomized encouragement or stepped-wedge design where feasible.",
            "instrumentation": "Opaque IDs, assignment, model version, action class, override, error, and milestone events.",
            "worker_voice": "Workers and coaches co-design error classes, explanations, and burden measures.",
            "data_minimization": "Collect only fields required for pre-specified learning questions.",
            "human_oversight": "Humans retain authority for consequential service decisions.",
            "failure_modes": "Measure hallucination, stale data, unsafe guidance, access gaps, automation bias, and replay errors.",
            "interim_learning": "Use implementation reviews without converting interim observations into outcome claims.",
            "independent_evaluation_fit": "AIR can pre-specify analysis and independently evaluate implementation and outcomes."
        },
        "early_results_claimed": False,
        "early_results_evidence": [],
        "source_refresh_reviewed": True,
        "submission_boundary_reviewed": True
    }

def partner_owner():
    o = direct_owner()
    o["route"] = "PARTNER_RFI"
    o["direct_workforce_track_record"] = []
    o["partner"] = {
        "organization": "Verified Workforce Partner",
        "role": "Participant recruitment, workforce service delivery, coaching policy, and outcome evidence.",
        "commitment_evidence_ref": "private-partner-commitment-001",
        "workforce_track_record": [{
            "record_id": "partner-1", "population": "Adult learners", "workforce_service": "Career readiness and placement", "period": "2024-2026", "evidence_ref": "private-partner-track-001", "evidence_sha256": "c" * 64
        }]
    }
    return o

class PreflightTests(unittest.TestCase):
    def ev(self, owner=None, source=None, now=NOW):
        return evaluate(copy.deepcopy(ready_source() if source is None else source), copy.deepcopy(direct_owner() if owner is None else owner), trusted_now=now)

    def test_01_direct_ready(self):
        r = self.ev(); self.assertEqual(r["state"], READY); self.assertTrue(all(v is False for v in r["authority"].values()))
    def test_02_partner_ready(self): self.assertEqual(self.ev(partner_owner())["state"], READY)
    def test_03_committed_source_is_custody_hold(self): self.assertEqual(self.ev(source=SOURCE)["state"], SOURCE_CUSTODY_REQUIRED)
    def test_04_template_never_ready(self): self.assertNotEqual(self.ev(TEMPLATE, SOURCE)["state"], READY)
    def test_05_direct_track_record_required(self):
        o=direct_owner(); o["direct_workforce_track_record"]=[]; r=self.ev(o); self.assertEqual(r["state"],PARTNER_REQUIRED); self.assertIn("ESTABLISHED_DIRECT_WORKFORCE_TRACK_RECORD_NOT_EVIDENCED",r["blockers"])
    def test_06_partner_identity_required(self):
        o=partner_owner(); o["partner"]["organization"]="PARTNER_INPUT_REQUIRED"; self.assertEqual(self.ev(o)["state"],PARTNER_REQUIRED)
    def test_07_partner_track_record_required(self):
        o=partner_owner(); o["partner"]["workforce_track_record"]=[]; self.assertEqual(self.ev(o)["state"],PARTNER_REQUIRED)
    def test_08_track_digest_required(self):
        o=direct_owner(); o["direct_workforce_track_record"][0]["evidence_sha256"]="no"; self.assertTrue(any("BAD_DIGEST" in x for x in self.ev(o)["blockers"]))
    def test_09_duplicate_track_ids(self):
        o=direct_owner(); o["direct_workforce_track_record"].append(copy.deepcopy(o["direct_workforce_track_record"][0])); self.assertTrue(any("IDS_NOT_UNIQUE" in x for x in self.ev(o)["blockers"]))
    def test_10_project_title_required(self):
        o=direct_owner(); o["project_title"]="TODO"; self.assertIn("PROJECT_TITLE_REQUIRED",self.ev(o)["blockers"])
    def test_11_contact_required(self):
        o=direct_owner(); o["contact"]["phone"]="OWNER_INPUT_REQUIRED"; self.assertIn("CONTACT_PHONE_REQUIRED",self.ev(o)["blockers"])
    def test_12_focus_required(self):
        o=direct_owner(); o["focus_areas"]=[]; self.assertIn("SELECT_AT_LEAST_ONE_FOCUS_AREA",self.ev(o)["blockers"])
    def test_13_unknown_focus(self):
        o=direct_owner(); o["focus_areas"]=["Magic"]; self.assertTrue(any(x.startswith("UNKNOWN_FOCUS_AREA") for x in self.ev(o)["blockers"]))
    def test_14_duplicate_focus(self):
        o=direct_owner(); o["focus_areas"]=["Personalized Support","Personalized Support"]; self.assertIn("DUPLICATE_FOCUS_AREA",self.ev(o)["blockers"])
    def test_15_maturity(self):
        o=direct_owner(); o["maturity"]="Production-ish"; self.assertIn("MATURITY_INVALID",self.ev(o)["blockers"])
    def test_16_bool_population_size(self):
        o=direct_owner(); o["population"]["estimated_size_2027_2028"]=True; self.assertIn("POPULATION_2027_2028_SIZE_REQUIRED",self.ev(o)["blockers"])
    def test_17_unsafe_population_size(self):
        o=direct_owner(); o["population"]["estimated_size_2027_2028"]=MAX_SAFE_INT+1; self.assertIn("POPULATION_2027_2028_SIZE_REQUIRED",self.ev(o)["blockers"])
    def test_18_draft_set_exact(self):
        o=direct_owner(); del o["drafts"]["air_partnership"]; self.assertIn("DRAFT_PROMPT_SET_MUST_MATCH_RFI",self.ev(o)["blockers"])
    def test_19_word_limit(self):
        o=direct_owner(); o["drafts"]["population_of_focus"]="word "*101; self.assertTrue(any(x.startswith("WORD_LIMIT_EXCEEDED:population_of_focus") for x in self.ev(o)["blockers"]))
    def test_20_placeholder_draft(self):
        o=direct_owner(); o["drafts"]["technical_approach"]="OWNER_INPUT_REQUIRED"; self.assertIn("DRAFT_TECHNICAL_APPROACH_REQUIRED",self.ev(o)["blockers"])
    def test_21_responsible_ai(self):
        o=direct_owner(); o["responsible_ai_controls"]["privacy"]="TBD"; self.assertIn("RESPONSIBLE_AI_PRIVACY_REQUIRED",self.ev(o)["blockers"])
    def test_22_evidence_design(self):
        o=direct_owner(); o["evidence_design"]["worker_voice"]="TODO"; self.assertIn("EVIDENCE_DESIGN_WORKER_VOICE_REQUIRED",self.ev(o)["blockers"])
    def test_23_results_claim_needs_evidence(self):
        o=direct_owner(); o["early_results_claimed"]=True; self.assertIn("EARLY_RESULTS_EVIDENCE_REQUIRED",self.ev(o)["blockers"])
    def test_24_results_evidence_must_be_hashed(self):
        o=direct_owner(); o["early_results_claimed"]=True; o["early_results_evidence"]=[{"claim":"Validated result","evidence_ref":"private-result","evidence_sha256":"bad"}]; self.assertTrue(any(x.startswith("EARLY_RESULTS_EVIDENCE_0_INVALID") for x in self.ev(o)["blockers"]))
    def test_25_no_claim_with_evidence(self):
        o=direct_owner(); o["early_results_evidence"]=[{"claim":"x","evidence_ref":"y","evidence_sha256":"d"*64}]; self.assertIn("EARLY_RESULTS_EVIDENCE_PRESENT_WHILE_CLAIM_FALSE",self.ev(o)["blockers"])
    def test_26_source_review_required(self):
        o=direct_owner(); o["source_refresh_reviewed"]=False; self.assertIn("SOURCE_REFRESH_REVIEW_REQUIRED",self.ev(o)["blockers"])
    def test_27_submission_boundary_required(self):
        o=direct_owner(); o["submission_boundary_reviewed"]=False; self.assertIn("SUBMISSION_BOUNDARY_REVIEW_REQUIRED",self.ev(o)["blockers"])
    def test_28_source_stale(self): self.assertEqual(self.ev(now=NOW+timedelta(days=7,seconds=1))["state"],SOURCE_REFRESH_REQUIRED)
    def test_29_source_future(self):
        s=ready_source(); s["checked_at"]="2026-09-13T11:01:00Z"; self.assertRaises(PreflightError,self.ev,None,s,NOW)
    def test_30_deadline(self):
        s=ready_source(); s["checked_at"]="2026-10-02T15:59:00Z"; self.assertEqual(self.ev(source=s,now=datetime(2026,10,2,16,0,1,tzinfo=timezone.utc))["state"],DEADLINE_PASSED)
    def test_31_fake_pdf_claim(self):
        s=copy.deepcopy(SOURCE); s["rfi_pdf_bytes_acquired"]=True; self.assertRaises(PreflightError,self.ev,None,s,NOW)
    def test_32_digest_without_bytes(self):
        s=copy.deepcopy(SOURCE); s["rfi_pdf_sha256"]="a"*64; self.assertRaises(PreflightError,self.ev,None,s,NOW)
    def test_33_no_award_boundary(self):
        s=ready_source(); s["no_award_at_rfi_stage"]=False; self.assertRaises(PreflightError,self.ev,None,s,NOW)
    def test_34_future_funding_not_guaranteed(self):
        s=ready_source(); s["future_funding_guaranteed"]=True; self.assertRaises(PreflightError,self.ev,None,s,NOW)
    def test_35_source_authority(self):
        s=ready_source(); s["authority"]["submission_authorized"]=True; self.assertRaises(PreflightError,self.ev,None,s,NOW)
    def test_36_duplicate_json(self): self.assertRaises(PreflightError,load_json_bytes,b'{"x":1,"x":2}',"x")
    def test_37_nonfinite_json(self): self.assertRaises(PreflightError,load_json_bytes,b'{"x":NaN}',"x")
    def test_38_naive_trusted_time(self): self.assertRaises(PreflightError,evaluate,ready_source(),direct_owner(),trusted_now=datetime(2026,9,13))
    def test_39_deterministic_receipt(self): self.assertEqual(self.ev()["receipt_sha256"],self.ev()["receipt_sha256"])
    def test_40_receipt_tamper(self):
        s=ready_source(); o=direct_owner(); r=evaluate(s,o,trusted_now=NOW); self.assertTrue(verify_receipt(r,s,o,trusted_now=NOW)); r["state"]="HOLD"; self.assertFalse(verify_receipt(r,s,o,trusted_now=NOW))
    def test_41_owner_change_breaks_receipt(self):
        s=ready_source(); o=direct_owner(); r=evaluate(s,o,trusted_now=NOW); o["population"]["estimated_size_2027_2028"]=121; self.assertFalse(verify_receipt(r,s,o,trusted_now=NOW))
    def test_42_optimized_safe_invariant(self): self.assertFalse(any(self.ev()["authority"].values()))

    def test_43_official_url_substitution_rejected(self):
        s=ready_source(); s["official_urls"][0]="https://mirror.example.invalid/rfi.pdf"; self.assertRaises(PreflightError,self.ev,None,s,NOW)
    def test_44_focus_semantic_drift_rejected(self):
        s=ready_source(); s["focus_areas"][0]="Generic AI"; self.assertRaises(PreflightError,self.ev,None,s,NOW)
    def test_45_extraction_custody_conflict_rejected(self):
        s=ready_source(); s["source_extraction_receipt"]["raw_byte_hash_available"]=False; self.assertRaises(PreflightError,self.ev,None,s,NOW)
    def test_46_source_authority_key_omission_rejected(self):
        s=ready_source(); del s["authority"]["contact_authorized"]; self.assertRaises(PreflightError,self.ev,None,s,NOW)

if __name__ == "__main__":
    unittest.main()
