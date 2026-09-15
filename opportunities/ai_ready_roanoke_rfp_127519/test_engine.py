from __future__ import annotations
import copy, unittest
from .acceptance import fixture, AS_OF
from .budget import BudgetError, validate_budget
from .engine import PursuitError, evaluate, strict_json_loads, verify, REQUIRED_GATES

class Tests(unittest.TestCase):
    def setUp(self): self.p=fixture()
    def test_current_real_posture(self):
        o=evaluate(self.p,AS_OF); self.assertEqual(o["disposition"],"PARTNER_OUTREACH_READY"); self.assertEqual(o["outreach"]["state"],"SENT_NOT_ACCEPTED")
    def test_no_external_authority(self): self.assertFalse(any(evaluate(self.p,AS_OF)["authority"].values()))
    def test_addendum_deadline_required(self):
        self.p["deadlines"]["deadline_source_id"]="rfp-public-mirror-20260831"
        with self.assertRaises(PursuitError): evaluate(self.p,AS_OF)
    def test_missing_addendum_refreshes(self):
        self.p["sources"]=self.p["sources"][:1]
        self.p["deadlines"]["deadline_source_id"]="rfp-public-mirror-20260831"
        with self.assertRaises(PursuitError): evaluate(self.p,AS_OF)
    def test_incomplete_source_set(self):
        self.p["source_set_complete"]=False; self.assertEqual(evaluate(self.p,AS_OF)["disposition"],"SOURCE_REFRESH_REQUIRED")
    def test_expired(self): self.assertEqual(evaluate(self.p,"2026-10-03T04:00:00Z")["disposition"],"EXPIRED")
    def test_future_source_fails(self):
        self.p["sources"][0]["captured_at"]="2026-09-14T00:00:00Z"
        with self.assertRaises(PursuitError): evaluate(self.p,AS_OF)
    def test_bool_not_budget_int(self):
        self.p["budget"]["total_cents"]=True
        with self.assertRaises(PursuitError): evaluate(self.p,AS_OF)
    def test_over_ceiling_fails(self):
        self.p["budget"]["total_cents"]=25_000_001
        with self.assertRaises(PursuitError): evaluate(self.p,AS_OF)
    def test_sent_needs_provider_receipt(self):
        self.p["outreach"]["provider_receipt_id"]=None
        with self.assertRaises(PursuitError): evaluate(self.p,AS_OF)
    def test_sent_is_not_partner_confirmation(self):
        o=evaluate(self.p,AS_OF); self.assertFalse(o["partner_posture"]["confirmed"]); self.assertNotEqual(o["disposition"],"TEAMING_RESPONSE_BUILD_READY")
    def test_workshare_cannot_precede_partner(self):
        self.p["partner"]["commercial_workshare_agreed"]=True
        with self.assertRaises(PursuitError): evaluate(self.p,AS_OF)
    def test_pass_needs_evidence(self):
        self.p["gates"][11]["state"]="PASS"
        with self.assertRaises(PursuitError): evaluate(self.p,AS_OF)
    def test_confirmed_team_can_build_response_but_mirror_blocks_submission(self):
        self.p["partner"]={"candidate_id":"prime-1","confirmed":True,"commercial_workshare_agreed":True,"evidence_refs":["reply-1"]}
        for g in self.p["gates"]:
            if g["route"]=="TEAM": g["state"]="PASS"; g["evidence_refs"]=["evidence-"+g["gate_id"]]
        self.assertEqual(evaluate(self.p,AS_OF)["disposition"],"TEAMING_RESPONSE_BUILD_READY")
    def test_official_team_ready_requires_owner_budget_release(self):
        for s in self.p["sources"]: s["authority"]="OFFICIAL_BYTES"; s["content_sha256"]="a"*64
        self.p["partner"]={"candidate_id":"prime-1","confirmed":True,"commercial_workshare_agreed":True,"evidence_refs":["reply-1"]}
        for g in self.p["gates"]:
            if g["route"]=="TEAM": g["state"]="PASS"; g["evidence_refs"]=["evidence-"+g["gate_id"]]
        self.p["budget"]={"math_valid":True,"owner_approved":True,"total_cents":20_000_000}; self.p["owner_release"]=True
        self.assertEqual(evaluate(self.p,AS_OF)["disposition"],"TEAM_READY_FOR_OWNER_SUBMISSION_REVIEW")
    def test_prime_ready_independent_of_team_partner(self):
        for s in self.p["sources"]: s["authority"]="OFFICIAL_BYTES"; s["content_sha256"]="b"*64
        for g in self.p["gates"]:
            if g["route"]=="PRIME": g["state"]="PASS"; g["evidence_refs"]=["prime-"+g["gate_id"]]
        self.p["budget"]={"math_valid":True,"owner_approved":True,"total_cents":24_000_000}; self.p["owner_release"]=True
        self.assertEqual(evaluate(self.p,AS_OF)["disposition"],"PRIME_READY_FOR_OWNER_SUBMISSION_REVIEW")
    def test_missing_one_team_gate_blocks_submission(self):
        for s in self.p["sources"]: s["authority"]="OFFICIAL_BYTES"; s["content_sha256"]="c"*64
        self.p["partner"]={"candidate_id":"prime-1","confirmed":True,"commercial_workshare_agreed":True,"evidence_refs":["reply-1"]}
        for g in self.p["gates"]:
            if g["route"]=="TEAM": g["state"]="PASS"; g["evidence_refs"]=["evidence-"+g["gate_id"]]
        next(g for g in self.p["gates"] if g["route"]=="TEAM" and g["gate_id"]=="required_insurance")["state"]="MISSING"
        next(g for g in self.p["gates"] if g["route"]=="TEAM" and g["gate_id"]=="required_insurance")["evidence_refs"]=[]
        self.p["budget"]={"math_valid":True,"owner_approved":True,"total_cents":20_000_000}; self.p["owner_release"]=True
        self.assertEqual(evaluate(self.p,AS_OF)["disposition"],"PARTNER_OUTREACH_READY")
    def test_changed_duplicate_source_fails(self):
        d=copy.deepcopy(self.p["sources"][0]); d["source_ref"]="mirror:changed"; self.p["sources"].append(d)
        with self.assertRaises(PursuitError): evaluate(self.p,AS_OF)
    def test_duplicate_json_fails(self):
        with self.assertRaises(PursuitError): strict_json_loads('{"x":1,"x":2}')
    def test_nonfinite_json_fails(self):
        with self.assertRaises(PursuitError): strict_json_loads('{"x":NaN}')
    def test_order_invariant_sources_gates(self):
        a=evaluate(self.p,AS_OF); self.p["sources"].reverse(); self.p["gates"].reverse(); b=evaluate(self.p,AS_OF)
        self.assertEqual(a["disposition"],b["disposition"]); self.assertEqual(a["source_posture"],b["source_posture"])
    def test_verifier_tamper(self):
        o=evaluate(self.p,AS_OF); self.assertTrue(verify(self.p,AS_OF,o)); o["disposition"]="TEAM_READY_FOR_OWNER_SUBMISSION_REVIEW"; self.assertFalse(verify(self.p,AS_OF,o))
    def test_budget_valid(self):
        p={"workstreams":{"demand_analysis":"30000.00","program_design":"20000.00","workforce_analysis":"30000.00","site_feasibility":"30000.00","cost_financial_modeling":"25000.00","governance_design":"15000.00"},"milestones":[{"milestone_id":"phase1","amount":"80000.00"},{"milestone_id":"phase2","amount":"70000.00"}],"owner_approved":False}
        o=validate_budget(p); self.assertEqual(o["total_cents"],15_000_000); self.assertTrue(o["math_valid"])
    def test_budget_ceiling(self):
        p={"workstreams":{"demand_analysis":"250000.01","program_design":"0","workforce_analysis":"0","site_feasibility":"0","cost_financial_modeling":"0","governance_design":"0"},"milestones":[{"milestone_id":"m1","amount":"250000.01"}],"owner_approved":False}
        with self.assertRaises(BudgetError): validate_budget(p)
    def test_budget_milestone_sum(self):
        p={"workstreams":{"demand_analysis":"1","program_design":"1","workforce_analysis":"1","site_feasibility":"1","cost_financial_modeling":"1","governance_design":"1"},"milestones":[{"milestone_id":"m1","amount":"5"}],"owner_approved":False}
        with self.assertRaises(BudgetError): validate_budget(p)
    def test_gate_universe_stable(self): self.assertEqual(len(REQUIRED_GATES),11)

if __name__=="__main__": unittest.main()
