from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from opportunities.air_ai_workforce_rfi_2026 import preflight as pf

HERE = Path(__file__).resolve().parent

def H(ch="a"):
    return ch * 64

def load_source():
    return json.loads((HERE / "source_snapshot.json").read_text())

def base_owner():
    return {
        "schema": pf.OWNER_SCHEMA,
        "organization": {
            "public_name": "TokenJunkieLabs",
            "organization_type": "technology provider",
            "background": "Builds auditable AI workflow and evaluation infrastructure.",
            "website": "https://example.com",
        },
        "contact": {
            "name": "Private Owner Contact",
            "title": "Principal",
            "email": "owner@example.com",
            "phone": "+1-555-0100",
        },
        "innovation": {
            "project_title": "Evidence-Bound AI Career Navigation & Readiness Lab",
            "summary": "Human-supervised AI support with evaluator-facing provenance and versioned telemetry.",
            "focus_areas": ["Career Navigation & Job Placement", "Skill Training & Development"],
            "workforce_challenge": "Career-navigation staff must synthesize fragmented information while checking AI guidance for errors.",
            "learning_questions": ["Does bounded AI support improve task quality without increasing error or inequity?"],
            "population_description": "Partner-served adult jobseekers in a defined 2027-2028 cohort.",
            "population_size_2027_2028": 250,
            "technical_approach": "Versioned model orchestration, evidence provenance, human review, and deterministic evaluation receipts.",
            "maturity": "Concept",
            "early_results": "NO_EARLY_RESULTS_CLAIMED",
            "safeguards": "Human decision authority, data minimization, provenance, subgroup error monitoring, and escalation.",
            "air_partnership": "AIR could independently refine measures, comparison design, implementation fidelity, and evidence interpretation.",
        },
        "workforce_track_record": [],
        "partner": {
            "status": "NONE",
            "organization_ref": "",
            "population_delivery_role": "",
            "evidence_ref": "",
            "evidence_sha256": "",
            "workforce_track_record": [],
        },
        "evidence_design": {
            "worker_voice": "Consented qualitative interviews and structured feedback on usefulness, accessibility, pressure, and privacy.",
            "primary_outcomes": ["bounded task quality", "staff rework", "factual support error rate"],
            "comparison_design": "Pre-specified stepped-wedge or randomized service variant if operationally feasible.",
            "instrumentation": "Opaque IDs, model/config identity, evidence digests, staff accept/revise/reject, and failure flags.",
            "privacy_plan": "Keep direct identity in partner systems and minimize the evaluator extract.",
            "fairness_plan": "Pre-specify subgroup error/helpfulness metrics and reporting thresholds.",
            "human_oversight": "Staff retain consequential decisions and can reject or escalate every AI suggestion.",
            "failure_modes": ["unsupported certainty", "harmful guidance", "privacy leakage", "model drift"],
            "air_independent_evaluation_role": "AIR can audit design, implementation fidelity, measures, missingness, and causal language.",
        },
        "claims": [],
    }

def track(record_id="track-1", supportable=True):
    return {
        "record_id": record_id,
        "workforce_domain": "career readiness and adult upskilling",
        "population": "adult jobseekers",
        "period_start": "2025-01-01",
        "period_end": "2026-08-31",
        "evidence_ref": f"evidence:{record_id}",
        "evidence_sha256": H("b"),
        "externally_supportable": supportable,
    }

NOW = datetime(2026, 9, 13, 11, 0, tzinfo=timezone.utc)

class RouteTests(unittest.TestCase):
    def test_partner_required_is_default_for_complete_concept_without_track_record(self):
        r = pf.evaluate(load_source(), base_owner(), trusted_now=NOW)
        self.assertEqual(r["state"], pf.PARTNER_REQUIRED)
        self.assertEqual(r["recommended_route"], "PARTNER_RFI")
        self.assertIn("DIRECT_ROUTE_LACKS_EVIDENCED_WORKFORCE_DELIVERY_TRACK_RECORD", r["route_gaps"])
        self.assertIn("NO_COMMITTED_WORKFORCE_DELIVERY_PARTNER", r["route_gaps"])
        self.assertTrue(all(v is False for v in r["authority"].values()))
        self.assertFalse(r["rfi_has_award"])

    def test_direct_ready_requires_evidenced_track_record(self):
        o = base_owner()
        o["workforce_track_record"] = [track()]
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertEqual(r["state"], pf.DIRECT_READY)
        self.assertEqual(r["direct_track_record_count"], 1)
        self.assertEqual(r["recommended_route"], "DIRECT_RFI")

    def test_unsubstantiated_track_record_does_not_green_direct(self):
        o = base_owner()
        o["workforce_track_record"] = [track(supportable=False)]
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertEqual(r["state"], pf.PARTNER_REQUIRED)
        self.assertEqual(r["direct_track_record_count"], 0)

    def test_partner_ready_requires_committed_partner_and_track_record(self):
        o = base_owner()
        o["partner"] = {
            "status": "COMMITTED",
            "organization_ref": "partner:opaque-001",
            "population_delivery_role": "Owns recruitment, service delivery, worker relationship, and staff supervision.",
            "evidence_ref": "evidence:partner-commitment-001",
            "evidence_sha256": H("c"),
            "workforce_track_record": [track("partner-track-1")],
        }
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertEqual(r["state"], pf.PARTNER_READY)
        self.assertEqual(r["recommended_route"], "PARTNER_RFI")
        self.assertEqual(r["partner_track_record_count"], 1)

    def test_prospective_partner_is_not_commitment(self):
        o = base_owner()
        o["partner"]["status"] = "PROSPECTIVE"
        o["partner"]["organization_ref"] = "partner:maybe"
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertEqual(r["state"], pf.PARTNER_REQUIRED)
        self.assertIn("PROSPECTIVE_PARTNER_NOT_COMMITTED", r["route_gaps"])
        self.assertIn("PROSPECTIVE_PARTNER_IS_NOT_A_COMMITMENT", r["warnings"])

    def test_committed_partner_without_evidence_holds(self):
        o = base_owner()
        o["partner"]["status"] = "COMMITTED"
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertEqual(r["state"], pf.HOLD)
        self.assertIn("COMMITTED_PARTNER_EVIDENCE_SHA256_REQUIRED", r["blockers"])

class ContentGateTests(unittest.TestCase):
    def test_population_size_required_and_bool_does_not_alias_int(self):
        o = base_owner(); o["innovation"]["population_size_2027_2028"] = True
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertEqual(r["state"], pf.HOLD)
        self.assertIn("POSITIVE_2027_2028_POPULATION_SIZE_REQUIRED", r["blockers"])

    def test_unknown_focus_area_holds(self):
        o = base_owner(); o["innovation"]["focus_areas"] = ["Magic Jobs"]
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertIn("UNKNOWN_FOCUS_AREA:Magic Jobs", r["blockers"])

    def test_duplicate_focus_area_holds(self):
        o = base_owner(); o["innovation"]["focus_areas"] = ["Career Navigation & Job Placement"] * 2
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertIn("DUPLICATE_FOCUS_AREA", r["blockers"])

    def test_worker_voice_is_required(self):
        o = base_owner(); o["evidence_design"]["worker_voice"] = "OWNER_INPUT_REQUIRED"
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertIn("EVIDENCE_DESIGN_WORKER_VOICE_REQUIRED", r["blockers"])

    def test_learning_questions_required(self):
        o = base_owner(); o["innovation"]["learning_questions"] = []
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertIn("LEARNING_QUESTIONS_REQUIRED", r["blockers"])

    def test_non_concept_maturity_requires_claim_evidence(self):
        o = base_owner(); o["innovation"]["maturity"] = "Pilot"
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertIn("NON_CONCEPT_MATURITY_REQUIRES_EVIDENCE", r["blockers"])

    def test_supported_maturity_claim_allows_maturity(self):
        o = base_owner(); o["innovation"]["maturity"] = "Pilot"; o["workforce_track_record"] = [track()]
        o["claims"] = [{
            "claim_id":"maturity-1","kind":"MATURITY","text":"A workforce pilot was executed.",
            "evidence_ref":"evidence:maturity-1","evidence_sha256":H("d"),"support_level":"SUPPORTED"
        }]
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertEqual(r["state"], pf.DIRECT_READY)

    def test_early_results_require_evidence(self):
        o = base_owner(); o["innovation"]["early_results"] = "Participants improved."
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertIn("EARLY_RESULTS_REQUIRE_EVIDENCE", r["blockers"])

    def test_unsupported_claim_is_explicit_hold(self):
        o = base_owner()
        o["claims"] = [{
            "claim_id":"outcome-1","kind":"OUTCOME","text":"Placement improved 20 percent.",
            "evidence_ref":"","evidence_sha256":"","support_level":"UNSUPPORTED"
        }]
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertIn("UNSUPPORTED_CLAIM:outcome-1", r["blockers"])

    def test_private_contact_not_copied_to_receipt(self):
        o = base_owner()
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        raw = json.dumps(r)
        self.assertNotIn(o["contact"]["email"], raw)
        self.assertNotIn(o["contact"]["phone"], raw)
        self.assertIn("owner_input_sha256", r)

class SourceTruthTests(unittest.TestCase):
    def test_source_preserves_no_award_and_no_guarantee(self):
        s = load_source(); s["rfi_has_award"] = True
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(s, base_owner(), trusted_now=NOW)

    def test_source_does_not_fabricate_pdf_digest(self):
        s = load_source(); s["rfp_pdf_sha256"] = H("e")
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(s, base_owner(), trusted_now=NOW)

    def test_prompt_limit_drift_rejected(self):
        s = load_source(); s["prompts"][3]["word_limit"] = 301
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(s, base_owner(), trusted_now=NOW)

    def test_missing_prompt_rejected(self):
        s = load_source(); s["prompts"].pop()
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(s, base_owner(), trusted_now=NOW)

    def test_unknown_source_key_rejected(self):
        s = load_source(); s["invented"] = True
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(s, base_owner(), trusted_now=NOW)

    def test_stale_source_holds(self):
        s = load_source(); s["checked_at"] = "2026-09-01T00:00:00Z"
        r = pf.evaluate(s, base_owner(), trusted_now=NOW)
        self.assertIn("SOURCE_SNAPSHOT_OLDER_THAN_7_DAYS", r["blockers"])

    def test_future_source_capture_rejected(self):
        s = load_source(); s["checked_at"] = "2026-09-14T00:00:00Z"
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(s, base_owner(), trusted_now=NOW)

    def test_deadline_is_fail_closed(self):
        later = datetime(2026, 10, 2, 16, 0, tzinfo=timezone.utc)
        s = load_source(); s["checked_at"] = "2026-10-02T15:59:00Z"
        r = pf.evaluate(s, base_owner(), trusted_now=later)
        self.assertIn("RFI_DEADLINE_PASSED", r["blockers"])
        self.assertEqual(r["state"], pf.HOLD)

class IntegrityTests(unittest.TestCase):
    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(pf.PreflightError):
            pf.load_json_bytes(b'{"schema":"x","schema":"y"}', "x")

    def test_nonfinite_rejected(self):
        with self.assertRaises(pf.PreflightError):
            pf.load_json_bytes(b'{"x":NaN}', "x")

    def test_float_rejected(self):
        with self.assertRaises(pf.PreflightError):
            pf.load_json_bytes(b'{"x":1.25}', "x")

    def test_unsafe_integer_rejected(self):
        with self.assertRaises(pf.PreflightError):
            pf.load_json_bytes(b'{"x":9007199254740992}', "x")

    def test_owner_unknown_key_rejected(self):
        o = base_owner(); o["mystery"] = "x"
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(load_source(), o, trusted_now=NOW)

    def test_track_record_duplicate_ids_hold(self):
        o = base_owner(); o["workforce_track_record"] = [track("same"), track("same")]
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertIn("WORKFORCE_TRACK_RECORD_RECORD_ID_INVALID_OR_DUPLICATE", r["blockers"])

    def test_track_record_period_inversion_holds(self):
        o = base_owner(); row = track(); row["period_start"]="2026-09-01"; row["period_end"]="2025-09-01"
        o["workforce_track_record"]=[row]
        r = pf.evaluate(load_source(), o, trusted_now=NOW)
        self.assertIn("WORKFORCE_TRACK_RECORD_0_PERIOD_INVERTED", r["blockers"])

    def test_receipt_verifies_and_tamper_fails(self):
        s=load_source(); o=base_owner()
        r=pf.evaluate(s,o,trusted_now=NOW)
        self.assertTrue(pf.verify(s,o,r,trusted_now=NOW))
        tampered=copy.deepcopy(r); tampered["state"]=pf.DIRECT_READY
        self.assertFalse(pf.verify(s,o,tampered,trusted_now=NOW))

    def test_canonical_dict_key_order_stable(self):
        a={"b":2,"a":1}; b={"a":1,"b":2}
        self.assertEqual(pf.canonical_bytes(a), pf.canonical_bytes(b))
        self.assertEqual(pf.sha256(a),pf.sha256(b))

    def test_receipt_deterministic_for_exact_inputs(self):
        s=load_source(); o=base_owner()
        self.assertEqual(pf.evaluate(s,o,trusted_now=NOW), pf.evaluate(copy.deepcopy(s),copy.deepcopy(o),trusted_now=NOW))

class FileBoundaryTests(unittest.TestCase):
    def test_publish_exclusive_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"receipt.json"
            pf.publish_exclusive(p,b"one")
            self.assertEqual(p.read_bytes(),b"one")
            with self.assertRaises(pf.PreflightError):
                pf.publish_exclusive(p,b"two")
            self.assertEqual(p.read_bytes(),b"one")

    def test_publish_exclusive_refuses_symlink(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unsupported")
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); target=td/"target"; target.write_bytes(b"safe")
            link=td/"out"; link.symlink_to(target)
            with self.assertRaises(pf.PreflightError):
                pf.publish_exclusive(link,b"evil")
            self.assertEqual(target.read_bytes(),b"safe")

    def test_read_plain_file_refuses_symlink(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unsupported")
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); target=td/"target"; target.write_text("{}")
            link=td/"input"; link.symlink_to(target)
            if hasattr(os, "O_NOFOLLOW"):
                with self.assertRaises(pf.PreflightError):
                    pf.read_plain_file(link,"input")

if __name__ == "__main__":
    unittest.main()
