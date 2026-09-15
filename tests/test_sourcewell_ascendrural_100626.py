import hashlib
import unittest
from datetime import datetime, timezone
from revenue.sourcewell_ascendrural_100626.qualification import QualificationError, qualify, verify_receipt as verify_q
from revenue.sourcewell_ascendrural_100626.relay import RelayError, audit_request, verify_receipt as verify_r

def digest(label): return hashlib.sha256(label.encode()).hexdigest()
def opportunity():
    return {"rfp_id":"100626","issuer":"Sourcewell","title":"AscendRural Innovation Challenge: Bridging Distance to Rural Care & Services","status":"OPEN","question_deadline":"2026-09-28T15:30:00-05:00","close_deadline":"2026-10-06T15:30:00-05:00","submission_type":"ONLINE_ONLY","official_portal_url":"https://proportal.sourcewell-mn.gov/Module/Tenders/en/Tender/Detail/8f76f478-9d49-487b-8802-2f07435c3d66/","problem_areas":["transportation_access_and_coordination","last_mile_delivery_of_essentials","business_of_rural_access"],"public_budget":None,"source_observed_at":"2026-09-13T14:20:00+00:00"}
def product():
    return {"name":"Rural Access Relay","version":1,"problem_areas":["transportation_access_and_coordination","last_mile_delivery_of_essentials","business_of_rural_access"],"low_bandwidth_mode":True,"idempotent_replay":True,"evidence_bound_status":True,"operator_review_required":True,"emergency_dispatch_authority":False,"clinical_decision_authority":False,"diagnosis_authority":False,"treatment_authority":False,"eligibility_adjudication_authority":False,"payment_authority":False,"buyer_contact_authority":False,"submission_authority":False,"contract_signature_authority":False,"revenue_recognition_authority":False}
def docs():
    base="https://proportal.sourcewell-mn.gov/Module/Tenders/en/Document/Download/"
    return [{"kind":k,"name":k.lower()+".pdf","sha256":digest(k),"source_url":base+digest(k),"retrieved_at":"2026-09-13T14:25:00+00:00","superseded":False} for k in ("RFP","MASTER_AGREEMENT","FAQ_OR_QA","ADDENDA_INDEX")]
def request():
    return {"request_id":"r-1","service_kind":"NON_EMERGENCY_RIDE","emergency":False,"clinical_decision_required":False,"operator_review_required":True,"origin_zone":"county-a","destination_zone":"clinic-zone"}
def ev(i,typ,provider=None,eid=None):
    return {"event_id":eid or f"e-{i}","request_id":"r-1","type":typ,"provider_id":provider,"sequence":i,"evidence_sha256":digest(f"{typ}:{i}:{provider}")}

class QualificationTests(unittest.TestCase):
    NOW=datetime(2026,9,13,15,0,tzinfo=timezone.utc)
    def test_notice_only_holds(self):
        r=qualify(opportunity(),[],product(),verified_at=self.NOW); self.assertEqual(r.disposition,"HOLD"); self.assertEqual(len(r.blockers),4); self.assertTrue(verify_q(r.as_dict()))
    def test_full_docs_still_need_review(self):
        r=qualify(opportunity(),docs(),product(),verified_at=self.NOW); self.assertEqual(r.disposition,"CONTROLLING_SOURCE_BOUND_REVIEW_REQUIRED"); self.assertEqual(r.blockers,("REQUIREMENTS_AND_PROPOSAL_REVIEW_REQUIRED",)); self.assertTrue(verify_q(r.as_dict()))
    def test_budget_invention_rejected(self):
        o=opportunity(); o["public_budget"]=500000
        with self.assertRaises(QualificationError): qualify(o,[],product(),verified_at=self.NOW)
    def test_deadline_drift_rejected(self):
        o=opportunity(); o["close_deadline"]="2026-10-07T15:30:00-05:00"
        with self.assertRaises(QualificationError): qualify(o,[],product(),verified_at=self.NOW)
    def test_nonofficial_doc_rejected(self):
        d=docs(); d[0]["source_url"]="https://example.com/rfp.pdf"
        with self.assertRaises(QualificationError): qualify(opportunity(),d,product(),verified_at=self.NOW)
    def test_duplicate_doc_kind_rejected(self):
        d=docs(); d.append(dict(d[0],sha256=digest("other")))
        with self.assertRaises(QualificationError): qualify(opportunity(),d,product(),verified_at=self.NOW)
    def test_authority_escalation_rejected(self):
        p=product(); p["clinical_decision_authority"]=True
        with self.assertRaises(QualificationError): qualify(opportunity(),[],p,verified_at=self.NOW)
    def test_problem_area_overclaim_rejected(self):
        p=product(); p["problem_areas"]=["chronic_condition_management"]
        with self.assertRaises(QualificationError): qualify(opportunity(),[],p,verified_at=self.NOW)
    def test_future_observation_rejected(self):
        o=opportunity(); o["source_observed_at"]="2026-09-14T00:00:00+00:00"
        with self.assertRaises(QualificationError): qualify(o,[],product(),verified_at=self.NOW)
    def test_closed_deadline_holds(self):
        r=qualify(opportunity(),docs(),product(),verified_at=datetime(2026,10,6,21,0,tzinfo=timezone.utc)); self.assertIn("DEADLINE_CLOSED",r.blockers); self.assertEqual(r.disposition,"HOLD")
    def test_receipt_tamper(self):
        r=qualify(opportunity(),[],product(),verified_at=self.NOW).as_dict(); r["disposition"]="READY"; self.assertFalse(verify_q(r))

class RelayTests(unittest.TestCase):
    def clean(self): return [ev(0,"REQUEST_RECORDED"),ev(1,"ASSIGNMENT_OFFERED","p-1"),ev(2,"PROVIDER_ACCEPTED","p-1"),ev(3,"SERVICE_STARTED","p-1"),ev(4,"SERVICE_COMPLETED","p-1")]
    def test_clean(self):
        r=audit_request(request(),self.clean()); self.assertEqual(r.disposition,"CONSISTENT_FOR_OPERATOR_REVIEW"); self.assertEqual(r.state,"COMPLETED"); self.assertTrue(verify_r(r.as_dict()))
    def test_exact_replay_idempotent(self):
        e=self.clean(); e.insert(2,dict(e[1])); r=audit_request(request(),e); self.assertEqual(r.disposition,"CONSISTENT_FOR_OPERATOR_REVIEW"); self.assertEqual(r.logical_event_count,5)
    def test_changed_duplicate_holds(self):
        e=self.clean(); c=dict(e[1]); c["provider_id"]="p-2"; e.insert(2,c); r=audit_request(request(),e); self.assertIn("EVENT_ID_CONFLICT:e-1",r.blockers)
    def test_provider_mismatch_holds(self):
        e=self.clean(); e[2]=ev(2,"PROVIDER_ACCEPTED","p-2"); self.assertIn("PROVIDER_ACCEPTANCE_MISMATCH",audit_request(request(),e).blockers)
    def test_event_after_terminal_holds(self): self.assertIn("EVENT_AFTER_TERMINAL:EXCEPTION_RECORDED",audit_request(request(),self.clean()+[ev(5,"EXCEPTION_RECORDED","p-1")]).blockers)
    def test_exception_reassignment(self):
        e=[ev(0,"REQUEST_RECORDED"),ev(1,"ASSIGNMENT_OFFERED","p-1"),ev(2,"PROVIDER_ACCEPTED","p-1"),ev(3,"EXCEPTION_RECORDED","p-1"),ev(4,"ASSIGNMENT_OFFERED","p-2"),ev(5,"PROVIDER_ACCEPTED","p-2")]; r=audit_request(request(),e); self.assertEqual(r.disposition,"CONSISTENT_FOR_OPERATOR_REVIEW"); self.assertEqual(r.provider_id,"p-2")
    def test_sequence_gap(self): self.assertIn("SEQUENCE_GAP",audit_request(request(),[ev(0,"REQUEST_RECORDED"),ev(2,"ASSIGNMENT_OFFERED","p-1")]).blockers)
    def test_duplicate_sequence(self):
        e=[ev(0,"REQUEST_RECORDED"),ev(1,"ASSIGNMENT_OFFERED","p-1")]; x=ev(2,"PROVIDER_ACCEPTED","p-1"); x["sequence"]=1; e.append(x); self.assertIn("DUPLICATE_SEQUENCE",audit_request(request(),e).blockers)
    def test_cross_request_rejected(self):
        e=self.clean(); e[1]=dict(e[1],request_id="other")
        with self.assertRaises(RelayError): audit_request(request(),e)
    def test_emergency_rejected(self):
        q=request(); q["emergency"]=True
        with self.assertRaises(RelayError): audit_request(q,[])
    def test_clinical_rejected(self):
        q=request(); q["clinical_decision_required"]=True
        with self.assertRaises(RelayError): audit_request(q,[])
    def test_start_without_acceptance(self): self.assertIn("SERVICE_START_WITHOUT_ACCEPTANCE",audit_request(request(),[ev(0,"REQUEST_RECORDED"),ev(1,"SERVICE_STARTED","p-1")]).blockers)
    def test_receipt_tamper(self):
        r=audit_request(request(),self.clean()).as_dict(); r["state"]="CANCELLED"; self.assertFalse(verify_r(r))

if __name__=="__main__": unittest.main()
