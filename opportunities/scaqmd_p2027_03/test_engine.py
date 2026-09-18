import copy, hashlib, unittest
from .engine import *
KEY=bytes.fromhex("22"*32); KEY_ID="test-owner"; AS_OF="2026-09-16T13:05:00+00:00"
def d(s): return hashlib.sha256(s.encode()).hexdigest()
def source(bound=True):
    return {"solicitation_id":SOLICITATION_ID,"title":TITLE,"official_url":OFFICIAL_URL,"page_count":70,"observed_date":"2026-09-16","raw_status":"RAW_BYTES_BOUND" if bound else "RAW_BYTES_UNBOUND","raw_sha256":d("buyer-pdf") if bound else None,"raw_size_bytes":123456 if bound else 0}
def auth(s): return build_source_authority(s,key_id=KEY_ID,key=KEY,issued_at=AS_OF)
def projects():
    return [
      {"id":"P1","client":"Public Utility","completed_date":"2026-01-01","public_or_regulated":True,"value_minor":12_000_000,"duration_months":8,"technologies":["MICROSOFT_AZURE"],"client_reference":"ref:p1","challenge_corrective_documented":True,"evidence_refs":["contract:p1"]},
      {"id":"P2","client":"Client B","completed_date":"2025-01-01","public_or_regulated":False,"value_minor":5_000_000,"duration_months":14,"technologies":["SQL_SERVER"],"client_reference":"ref:p2","challenge_corrective_documented":False,"evidence_refs":["contract:p2"]},
      {"id":"P3","client":"Client C","completed_date":"2024-01-01","public_or_regulated":False,"value_minor":1_000_000,"duration_months":6,"technologies":["DOTNET_CSHARP"],"client_reference":"ref:p3","challenge_corrective_documented":False,"evidence_refs":["contract:p3"]},
    ]
def gates(proven=True):
    return [{"id":g,"state":"PROVEN" if proven else "UNKNOWN","responsible_party":"PRIME","evidence_refs":[f"e:{g}"] if proven else []} for g in sorted(REQUIRED_TEAM_GATES)]
def caps():
    return [{"id":f"C{i}","kind":k,"state":"DEFINED","owner":"TJL" if k!="MIGRATION_CUTOVER_ACCEPTANCE" else "SHARED","evidence_refs":[f"plan:{k}"]} for i,k in enumerate(sorted(REQUIRED_CAPABILITIES),1)]
def packet(s=None):
    s=s or source(True)
    return {"schema":SCHEMA,"solicitation":{"id":SOLICITATION_ID,"title":TITLE,"proposal_deadline":PROPOSAL_DEADLINE,"conference_at":CONFERENCE_DATE,"evaluation_points":{"understanding":20,"technical_management":20,"qualifications":20,"similar_experience":10,"cost":30},"commercial_posture":"TEAMING_TASK_ORDER_SPECIALIST_FIRST"},"source":s,"conference":{"state":"ATTENDED","evidence_refs":["attendance:buyer-confirmed"]},"projects":projects(),"team_gates":gates(True),"capabilities":caps(),"commercial":{"state":"PROPOSED_NOT_ACCEPTED","proposed_workshare_minor":5000000,"currency":"USD","preference_points_claimed":0,"external_contact_authorized":False,"price_commitment_authorized":False}}
class Tests(unittest.TestCase):
    def compile(self,p,as_of=AS_OF): return compile_assessment(p,auth(p["source"]),key=KEY,expected_key_id=KEY_ID,as_of=as_of)
    def test_ready(self):
        p=packet(); a=self.compile(p); self.assertEqual(a["state"],"READY_FOR_OWNER_PROPOSAL_REVIEW"); self.assertTrue(verify_assessment(p,auth(p["source"]),a,key=KEY,expected_key_id=KEY_ID)); self.assertTrue(all(v is False for v in a["authority"].values()))
    def test_unbound_source_holds(self):
        p=packet(source(False)); a=self.compile(p); self.assertEqual(a["state"],"HOLD_SOURCE_BYTES_REQUIRED")
    def test_unbound_source_cannot_claim_digest(self):
        s=source(False); s["raw_sha256"]=d("fake")
        with self.assertRaises(ValidationError): auth(s)
    def test_bound_source_needs_digest(self):
        s=source(True); s["raw_sha256"]=None
        with self.assertRaises(ValidationError): auth(s)
    def test_source_url_drift(self):
        s=source(True); s["official_url"] += "&mirror=x"
        with self.assertRaises(ValidationError): auth(s)
    def test_wrong_key(self):
        p=packet()
        with self.assertRaises(ValidationError): compile_assessment(p,auth(p["source"]),key=b"x"*32,expected_key_id=KEY_ID,as_of=AS_OF)
    def test_wrong_key_id(self):
        p=packet()
        with self.assertRaises(ValidationError): compile_assessment(p,auth(p["source"]),key=KEY,expected_key_id="wrong",as_of=AS_OF)
    def test_authority_tamper(self):
        p=packet(); a=auth(p["source"]); a["source"]["page_count"]=69
        with self.assertRaises(ValidationError): compile_assessment(p,a,key=KEY,expected_key_id=KEY_ID,as_of=AS_OF)
    def test_packet_source_mutation(self):
        p=packet(); a=auth(p["source"]); p["source"]["observed_date"]="2026-09-15"
        with self.assertRaises(ValidationError): compile_assessment(p,a,key=KEY,expected_key_id=KEY_ID,as_of=AS_OF)
    def test_conference_not_attended(self):
        p=packet(); p["conference"]={"state":"REGISTERED","evidence_refs":["registration:r"]}; self.assertEqual(self.compile(p)["state"],"HOLD_CONFERENCE_ATTENDANCE")
    def test_conference_claim_needs_evidence(self):
        p=packet(); p["conference"]={"state":"ATTENDED","evidence_refs":[]}
        with self.assertRaises(ValidationError): self.compile(p)
    def test_only_two_projects(self):
        p=packet(); p["projects"]=p["projects"][:2]; a=self.compile(p); self.assertEqual(a["state"],"HOLD_PAST_PROJECT_QUALIFICATION"); self.assertIn("THREE_COMPARABLE_PROJECTS",a["project_gaps"])
    def test_no_public_project(self):
        p=packet()
        for x in p["projects"]: x["public_or_regulated"]=False
        self.assertIn("PUBLIC_OR_REGULATED_PROJECT",self.compile(p)["project_gaps"])
    def test_value_or_duration_threshold(self):
        p=packet()
        for x in p["projects"]: x["value_minor"]=9_999_999; x["duration_months"]=11
        self.assertIn("VALUE_100K_OR_DURATION_12MO",self.compile(p)["project_gaps"])
    def test_exact_100k_threshold_passes(self):
        p=packet(); p["projects"][0]["value_minor"]=10_000_000; p["projects"][0]["duration_months"]=0; self.assertNotIn("VALUE_100K_OR_DURATION_12MO",self.compile(p)["project_gaps"])
    def test_old_project_rejected(self):
        p=packet(); p["projects"][0]["completed_date"]="2021-12-03"
        with self.assertRaises(ValidationError): self.compile(p)
    def test_unknown_technology_rejected(self):
        p=packet(); p["projects"][0]["technologies"]=["MAGIC_STACK"]
        with self.assertRaises(ValidationError): self.compile(p)
    def test_duplicate_project_id_rejected(self):
        p=packet(); p["projects"][1]["id"]="P1"
        with self.assertRaises(ValidationError): self.compile(p)
    def test_project_evidence_required(self):
        p=packet(); p["projects"][0]["evidence_refs"]=[]
        with self.assertRaises(ValidationError): self.compile(p)
    def test_challenge_example_required(self):
        p=packet()
        for x in p["projects"]: x["challenge_corrective_documented"]=False
        self.assertIn("CHALLENGE_CORRECTIVE_EXAMPLE",self.compile(p)["project_gaps"])
    def test_team_unknown_holds(self):
        p=packet(); p["team_gates"]=gates(False); self.assertEqual(self.compile(p)["state"],"HOLD_TEAM_QUALIFICATION")
    def test_missing_gate_rejected(self):
        p=packet(); p["team_gates"].pop()
        with self.assertRaises(ValidationError): self.compile(p)
    def test_proven_gate_evidence_required(self):
        p=packet(); p["team_gates"][0]["evidence_refs"]=[]
        with self.assertRaises(ValidationError): self.compile(p)
    def test_missing_capability_holds(self):
        p=packet(); p["capabilities"]=p["capabilities"][:-1]; self.assertEqual(self.compile(p)["state"],"HOLD_CAPABILITY_PLAN")
    def test_duplicate_capability_kind_rejected(self):
        p=packet(); x=copy.deepcopy(p["capabilities"][0]); x["id"]="C9"; p["capabilities"].append(x)
        with self.assertRaises(ValidationError): self.compile(p)
    def test_preference_self_mint_rejected(self):
        p=packet(); p["commercial"]["preference_points_claimed"]=10
        with self.assertRaises(ValidationError): self.compile(p)
    def test_contact_authority_rejected(self):
        p=packet(); p["commercial"]["external_contact_authorized"]=True
        with self.assertRaises(ValidationError): self.compile(p)
    def test_price_authority_rejected(self):
        p=packet(); p["commercial"]["price_commitment_authorized"]=True
        with self.assertRaises(ValidationError): self.compile(p)
    def test_bool_money_rejected(self):
        p=packet(); p["commercial"]["proposed_workshare_minor"]=True
        with self.assertRaises(ValidationError): self.compile(p)
    def test_deadline_holds(self): self.assertEqual(self.compile(packet(),"2026-12-04T13:00:01-08:00")["state"],"HOLD_DEADLINE_PASSED")
    def test_eval_weight_drift(self):
        p=packet(); p["solicitation"]["evaluation_points"]["cost"]=29
        with self.assertRaises(ValidationError): self.compile(p)
    def test_extra_key_rejected(self):
        p=packet(); p["x"]=1
        with self.assertRaises(ValidationError): self.compile(p)
    def test_assessment_tamper_rejected(self):
        p=packet(); au=auth(p["source"]); a=compile_assessment(p,au,key=KEY,expected_key_id=KEY_ID,as_of=AS_OF); a["state"]="READY_BOGUS"
        with self.assertRaises(ValidationError): verify_assessment(p,au,a,key=KEY,expected_key_id=KEY_ID)
    def test_deterministic_reorder(self):
        p=packet(); a1=self.compile(p); p["team_gates"]=list(reversed(p["team_gates"])); p["capabilities"]=list(reversed(p["capabilities"])); p["projects"]=list(reversed(p["projects"])); self.assertEqual(a1,self.compile(p))
if __name__=="__main__": unittest.main()
