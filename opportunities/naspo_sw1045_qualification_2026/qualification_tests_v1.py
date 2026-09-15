from __future__ import annotations
import copy, json, os, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from opportunities.naspo_sw1045_qualification_2026 import qualification as q

HERE=Path(__file__).resolve().parent
NOW=datetime(2026,9,13,11,15,tzinfo=timezone.utc)
def H(ch="a"): return ch*64

def source():
    return json.loads((HERE/"source_snapshot.json").read_text())
def attachments():
    return json.loads((HERE/"attachment_manifest.json").read_text())
def requirements():
    return json.loads((HERE/"requirements.json").read_text())

def owner(*,team=True,cats=None):
    if cats is None: cats=[]
    return {
      "schema":q.OWNER_SCHEMA,
      "organization":{
        "public_name":"TokenJunkieLabs",
        "website":"https://example.com",
        "legal_entity_evidence_ref":"",
        "legal_entity_evidence_sha256":""
      },
      "bid_intent":{"categories":list(cats),"teaming_subcontract":team},
      "public_sector_references":[],
      "personnel_evidence":[],
      "technical_evidence":[{
        "evidence_id":"SW1045-AGENT-WORKFLOW-ACCEPTANCE",
        "path":"revenue/naspo_sw1045_agent_workflow_acceptance/README.md",
        "blob_sha":"66deb64378a06e3261f54d357c30b6a895ca7e38",
        "capability":"Deterministic approval, idempotency, reconciliation, receipts, and hostile workflow tests.",
        "public_sector_past_performance":False
      }],
      "mandatory_requirement_evidence":[],
      "prime_partner":{
        "status":"NONE","organization_ref":"","commitment_evidence_ref":"","commitment_evidence_sha256":"",
        "public_sector_prime_track_record":[],"cooperative_contract_admin_evidence_ref":"","cooperative_contract_admin_evidence_sha256":""
      },
      "teaming_scope":{
        "summary":"Provide bounded AI and agent engineering under an established public-sector prime.",
        "deliverables":["agent architecture","responsible-AI controls","acceptance tests","MLOps/evaluation receipts"],
        "staffing_roles":["AI workflow engineer","evaluation engineer"],
        "acceptance_evidence":"Versioned test evidence, deterministic receipts, replay/reconciliation, and hostile tests.",
        "responsible_ai":"Human authority, bounded actions, evidence provenance, privacy minimization, and failure analysis.",
        "data_boundary":"No offshore assumption; exact buyer data-residency terms remain packet-bound until official capture."
      },
      "pricing":{"status":"NOT_COMMITTED","currency":"USD","unit_model":"Draft role/rate worksheet only after official pricing units are captured.","evidence_ref":"","evidence_sha256":""},
      "claims":[]
    }

def ready_packet():
    s=source(); a=attachments(); r=requirements()
    s["packet_access"]={
      "official_packet_acquired":True,"official_packet_sha256":H("1"),
      "official_packet_attachment_count":len(a["documents"]),
      "official_addenda_inventory_confirmed":True,
      "observation":"Exact official packet and addenda inventory acquired under a separately recorded evidence capture."
    }
    a["complete_inventory_confirmed"]=True; a["official_addenda_inventory_confirmed"]=True
    for i,d in enumerate(a["documents"]):
        d["discovery_authority"]="OFFICIAL_PACKET"; d["status"]="OFFICIAL_EXACT"
        d["official_url"]=f"https://financials.ok.gov/sw1045/document/{i+1}"
        d["sha256"]=hashlib_sha(i)
    r["source_authority"]="CONTROLLING_PACKET"; r["evaluation_model_status"]="EXACT_CAPTURED"
    r["categories"][0]["mandatory_requirements"]= [
      {"requirement_id":"C1-EXP","text":"Category 1 evidence requirement captured from controlling packet.","source_document_id":"ATTACHMENT_H_REQUIREMENTS","source_sha256":H("2")}
    ]
    r["categories"][1]["mandatory_requirements"]= [
      {"requirement_id":"C2-EXP","text":"Category 2 evidence requirement captured from controlling packet.","source_document_id":"ATTACHMENT_H_REQUIREMENTS","source_sha256":H("2")}
    ]
    return s,a,r
def hashlib_sha(i): return ("%064x" % (i+10))[-64:]
def ref():
    return {"reference_id":"ref-1","client_class":"state or local government","project_summary":"Supportable public-sector technology project.",
            "period_start":"2025-01-01","period_end":"2026-01-01","evidence_ref":"evidence:ref-1","evidence_sha256":H("3"),"externally_supportable":True}
def staff():
    return {"person_id":"role-1","role":"senior emerging technology lead","years_relevant":8,"evidence_ref":"evidence:person-1",
            "evidence_sha256":H("4"),"commitment_status":"OWNER_AUTHORIZED_COMMITMENT"}
def mreq(cat,rid):
    return {"requirement_id":rid,"category_id":cat,"status":"PROVEN","evidence_ref":f"evidence:{cat}:{rid}","evidence_sha256":H("5")}

class RouteTests(unittest.TestCase):
    def test_current_evidence_yields_teaming_draft_and_prime_packet_holds(self):
        o=owner(team=True,cats=["CATEGORY_1_CONSULTING","CATEGORY_2_SERVICES"])
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertEqual(rec["state"],q.TEAM_DRAFT)
        self.assertEqual(rec["recommended_route"],"TEAMING_SUBCONTRACT")
        self.assertEqual(rec["route_states"]["PRIME_CATEGORY_1_CONSULTING"],q.HOLD_PACKET)
        self.assertEqual(rec["route_states"]["PRIME_CATEGORY_2_SERVICES"],q.HOLD_PACKET)
        self.assertFalse(rec["official_packet_ready"])
        self.assertTrue(all(v is False for v in rec["authority"].values()))

    def test_no_team_selected_and_prime_packet_missing_is_hold_packet(self):
        rec=q.evaluate(source(),attachments(),requirements(),owner(team=False,cats=["CATEGORY_1_CONSULTING"]),trusted_now=NOW)
        self.assertEqual(rec["state"],q.HOLD_PACKET)
        self.assertEqual(rec["route_states"]["TEAMING_SUBCONTRACT"],"NOT_SELECTED")

    def test_prime_cat1_ready_only_after_packet_and_exact_requirement_evidence(self):
        s,a,r=ready_packet(); o=owner(team=False,cats=["CATEGORY_1_CONSULTING"])
        o["public_sector_references"]=[ref()]; o["personnel_evidence"]=[staff()]
        o["mandatory_requirement_evidence"]=[mreq("CATEGORY_1_CONSULTING","C1-EXP")]
        rec=q.evaluate(s,a,r,o,trusted_now=NOW)
        self.assertEqual(rec["route_states"]["PRIME_CATEGORY_1_CONSULTING"],q.PRIME_READY)
        self.assertEqual(rec["recommended_route"],"PRIME_CATEGORY_1_CONSULTING")
        self.assertEqual(rec["state"],q.PRIME_READY)

    def test_category1_evidence_does_not_bleed_to_category2(self):
        s,a,r=ready_packet(); o=owner(team=False,cats=["CATEGORY_1_CONSULTING","CATEGORY_2_SERVICES"])
        o["public_sector_references"]=[ref()]; o["personnel_evidence"]=[staff()]
        o["mandatory_requirement_evidence"]=[mreq("CATEGORY_1_CONSULTING","C1-EXP")]
        rec=q.evaluate(s,a,r,o,trusted_now=NOW)
        self.assertEqual(rec["route_states"]["PRIME_CATEGORY_1_CONSULTING"],q.PRIME_READY)
        self.assertEqual(rec["route_states"]["PRIME_CATEGORY_2_SERVICES"],q.HOLD)
        self.assertIn("REQUIREMENT_UNMAPPED:C2-EXP",rec["category_blockers"]["CATEGORY_2_SERVICES"])

    def test_partner_committed_plus_packet_can_be_teaming_ready(self):
        s,a,r=ready_packet(); o=owner(team=True,cats=[])
        o["prime_partner"]={
          "status":"COMMITTED","organization_ref":"partner:opaque","commitment_evidence_ref":"evidence:commit",
          "commitment_evidence_sha256":H("6"),"public_sector_prime_track_record":["evidence-bound public-sector prime record"],
          "cooperative_contract_admin_evidence_ref":"evidence:coop-admin","cooperative_contract_admin_evidence_sha256":H("7")
        }
        rec=q.evaluate(s,a,r,o,trusted_now=NOW)
        self.assertEqual(rec["state"],q.TEAM_READY)

    def test_committed_partner_without_packet_stays_draft(self):
        o=owner()
        o["prime_partner"]={
          "status":"COMMITTED","organization_ref":"partner:opaque","commitment_evidence_ref":"evidence:commit",
          "commitment_evidence_sha256":H("6"),"public_sector_prime_track_record":["supportable record"],
          "cooperative_contract_admin_evidence_ref":"evidence:coop","cooperative_contract_admin_evidence_sha256":H("7")
        }
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertEqual(rec["state"],q.TEAM_DRAFT)

    def test_prospective_prime_never_counts_as_commitment(self):
        o=owner(); o["prime_partner"]["status"]="PROSPECTIVE"; o["prime_partner"]["organization_ref"]="prime:maybe"
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertEqual(rec["state"],q.TEAM_DRAFT)
        self.assertIn("PROSPECTIVE_PRIME_IS_NOT_A_COMMITMENT",rec["warnings"])

class SourceAuthorityTests(unittest.TestCase):
    def test_spoofed_official_origin_rejected(self):
        s=source(); s["official_sources"][0]["url"]="https://example.com/sw1045"
        with self.assertRaises(q.QualificationError): q.evaluate(s,attachments(),requirements(),owner(),trusted_now=NOW)

    def test_mirror_cannot_be_relabelled_official(self):
        s=source(); s["mirror_sources"][0]["authority"]="OFFICIAL_SUMMARY"
        with self.assertRaises(q.QualificationError): q.evaluate(s,attachments(),requirements(),owner(),trusted_now=NOW)

    def test_unacquired_packet_cannot_have_digest(self):
        s=source(); s["packet_access"]["official_packet_sha256"]=H("a")
        with self.assertRaises(q.QualificationError): q.evaluate(s,attachments(),requirements(),owner(),trusted_now=NOW)

    def test_packet_acquired_requires_digest_and_count(self):
        s=source(); s["packet_access"]["official_packet_acquired"]=True
        with self.assertRaises(q.QualificationError): q.evaluate(s,attachments(),requirements(),owner(),trusted_now=NOW)

    def test_mirror_document_cannot_carry_official_digest(self):
        a=attachments(); a["documents"][0]["sha256"]=H("a")
        with self.assertRaises(q.QualificationError): q.evaluate(source(),a,requirements(),owner(),trusted_now=NOW)

    def test_official_document_requires_official_packet_authority(self):
        a=attachments(); d=a["documents"][0]; d["status"]="OFFICIAL_EXACT"; d["sha256"]=H("a"); d["official_url"]="https://example.com/d"
        with self.assertRaises(q.QualificationError): q.evaluate(source(),a,requirements(),owner(),trusted_now=NOW)

    def test_mirror_requirements_cannot_define_mandatory_minimum(self):
        r=requirements()
        r["categories"][0]["mandatory_requirements"]=[{"requirement_id":"fake","text":"fake","source_document_id":"x","source_sha256":H("a")}]
        with self.assertRaises(q.QualificationError): q.evaluate(source(),attachments(),r,owner(),trusted_now=NOW)

    def test_controlling_requirements_require_exact_evaluation_model(self):
        r=requirements(); r["source_authority"]="CONTROLLING_PACKET"
        with self.assertRaises(q.QualificationError): q.evaluate(source(),attachments(),r,owner(),trusted_now=NOW)

    def test_status_drift_rejected(self):
        s=source(); s["status"]="AWARDED"
        with self.assertRaises(q.QualificationError): q.evaluate(s,attachments(),requirements(),owner(),trusted_now=NOW)

    def test_award_fiction_rejected(self):
        s=source(); s["award_status"]="AWARDED_TO_US"
        with self.assertRaises(q.QualificationError): q.evaluate(s,attachments(),requirements(),owner(),trusted_now=NOW)

class FreshnessTests(unittest.TestCase):
    def test_stale_source_holds(self):
        s=source(); s["checked_at"]="2026-09-01T00:00:00Z"
        rec=q.evaluate(s,attachments(),requirements(),owner(),trusted_now=NOW)
        self.assertIn("SOURCE_SNAPSHOT_OLDER_THAN_7_DAYS",rec["global_blockers"])
        self.assertEqual(rec["state"],q.HOLD)

    def test_future_capture_rejected(self):
        s=source(); s["checked_at"]="2026-09-14T00:00:00Z"
        with self.assertRaises(q.QualificationError): q.evaluate(s,attachments(),requirements(),owner(),trusted_now=NOW)

    def test_deadline_reached_holds(self):
        s=source(); s["checked_at"]="2026-10-15T19:59:00Z"
        later=datetime(2026,10,15,20,0,tzinfo=timezone.utc)
        rec=q.evaluate(s,attachments(),requirements(),owner(),trusted_now=later)
        self.assertIn("SOLICITATION_CLOSED_OR_DEADLINE_REACHED",rec["global_blockers"])
        self.assertEqual(rec["state"],q.HOLD)

class EvidenceTests(unittest.TestCase):
    def test_technical_evidence_cannot_self_upgrade_to_public_sector_past_performance(self):
        o=owner(); o["technical_evidence"][0]["public_sector_past_performance"]=True
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertIn("TECH_EVIDENCE_0_CANNOT_ASSERT_PUBLIC_SECTOR_PAST_PERFORMANCE",rec["global_blockers"])
        self.assertEqual(rec["state"],q.HOLD)

    def test_reference_bool_alias_rejected(self):
        o=owner(); x=ref(); x["externally_supportable"]=1; o["public_sector_references"]=[x]
        with self.assertRaises(q.QualificationError): q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)

    def test_inverted_reference_period_holds(self):
        o=owner(); x=ref(); x["period_start"]="2026-01-02"; x["period_end"]="2026-01-01"; o["public_sector_references"]=[x]
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertIn("PUBLIC_SECTOR_REFERENCE_0_PERIOD_INVERTED",rec["global_blockers"])

    def test_personnel_years_bool_does_not_alias_int(self):
        o=owner(); x=staff(); x["years_relevant"]=True; o["personnel_evidence"]=[x]
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertIn("PERSON_0_YEARS_INVALID",rec["global_blockers"])

    def test_supported_claim_needs_digest(self):
        o=owner(); o["claims"]=[{"claim_id":"c1","kind":"TECHNICAL_CAPABILITY","text":"works","evidence_ref":"e","evidence_sha256":"","support_level":"SUPPORTED"}]
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertIn("CLAIM_0_SUPPORTED_WITHOUT_EVIDENCE",rec["global_blockers"])

    def test_unsupported_claim_holds(self):
        o=owner(); o["claims"]=[{"claim_id":"c1","kind":"PUBLIC_SECTOR_PAST_PERFORMANCE","text":"state success","evidence_ref":"","evidence_sha256":"","support_level":"UNSUPPORTED"}]
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertIn("UNSUPPORTED_CLAIM:c1",rec["global_blockers"])

    def test_proven_mandatory_requirement_needs_evidence(self):
        o=owner(); o["mandatory_requirement_evidence"]=[{"requirement_id":"x","category_id":"CATEGORY_1_CONSULTING","status":"PROVEN","evidence_ref":"","evidence_sha256":""}]
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertIn("PROVEN_MANDATORY_REQUIREMENT_REQUIRES_EVIDENCE",rec["global_blockers"])

    def test_duplicate_category_requirement_evidence_holds(self):
        o=owner(); e=mreq("CATEGORY_1_CONSULTING","x"); o["mandatory_requirement_evidence"]=[e,copy.deepcopy(e)]
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertIn("MANDATORY_REQUIREMENT_EVIDENCE_DUPLICATE",rec["global_blockers"])

class DraftCompletenessTests(unittest.TestCase):
    def test_team_summary_required(self):
        o=owner(); o["teaming_scope"]["summary"]="OWNER_INPUT_REQUIRED"
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertIn("TEAMING_SUMMARY_REQUIRED",rec["global_blockers"])

    def test_team_deliverables_required(self):
        o=owner(); o["teaming_scope"]["deliverables"]=[]
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertIn("TEAMING_DELIVERABLES_REQUIRED",rec["global_blockers"])

    def test_price_status_must_not_imply_commitment_without_owner_evidence(self):
        o=owner(); o["pricing"]["status"]="OWNER_AUTHORIZED_DRAFT"
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertIn("OWNER_AUTHORIZED_PRICING_REQUIRES_EVIDENCE",rec["global_blockers"])

    def test_unknown_pricing_status_holds(self):
        o=owner(); o["pricing"]["status"]="COMMITTED"
        rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertIn("PRICING_STATUS_INVALID",rec["global_blockers"])

    def test_invalid_category_holds(self):
        o=owner(cats=["CATEGORY_3"]); rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertIn("BID_CATEGORIES_INVALID",rec["global_blockers"])

    def test_duplicate_category_holds(self):
        o=owner(cats=["CATEGORY_1_CONSULTING","CATEGORY_1_CONSULTING"]); rec=q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
        self.assertIn("BID_CATEGORIES_INVALID",rec["global_blockers"])

class JsonBoundaryTests(unittest.TestCase):
    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(q.QualificationError): q.load_json_bytes(b'{"x":1,"x":2}',"x")
    def test_nan_rejected(self):
        with self.assertRaises(q.QualificationError): q.load_json_bytes(b'{"x":NaN}',"x")
    def test_float_rejected(self):
        with self.assertRaises(q.QualificationError): q.load_json_bytes(b'{"x":1.5}',"x")
    def test_unsafe_int_rejected(self):
        with self.assertRaises(q.QualificationError): q.load_json_bytes(b'{"x":9007199254740992}',"x")
    def test_unknown_owner_key_rejected(self):
        o=owner(); o["mystery"]=1
        with self.assertRaises(q.QualificationError): q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)
    def test_receipt_deterministic(self):
        args=(source(),attachments(),requirements(),owner())
        self.assertEqual(q.evaluate(*args,trusted_now=NOW),q.evaluate(*copy.deepcopy(args),trusted_now=NOW))
    def test_tamper_fails_verify(self):
        s,a,r,o=source(),attachments(),requirements(),owner(); rec=q.evaluate(s,a,r,o,trusted_now=NOW)
        self.assertTrue(q.verify(s,a,r,o,rec,trusted_now=NOW))
        bad=copy.deepcopy(rec); bad["state"]=q.PRIME_READY
        self.assertFalse(q.verify(s,a,r,o,bad,trusted_now=NOW))
    def test_contact_pii_not_present_because_schema_does_not_accept_it(self):
        o=owner(); o["organization"]["contact_email"]="secret@example.com"
        with self.assertRaises(q.QualificationError): q.evaluate(source(),attachments(),requirements(),o,trusted_now=NOW)

class FileBoundaryTests(unittest.TestCase):
    def test_publish_exclusive_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"r.json"; q.publish_exclusive(f,b"one")
            with self.assertRaises(q.QualificationError): q.publish_exclusive(f,b"two")
            self.assertEqual(f.read_bytes(),b"one")
    def test_publish_exclusive_refuses_symlink(self):
        if not hasattr(os,"symlink"): self.skipTest("symlink unsupported")
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); target=td/"target"; target.write_bytes(b"safe"); link=td/"out"; link.symlink_to(target)
            with self.assertRaises(q.QualificationError): q.publish_exclusive(link,b"evil")
            self.assertEqual(target.read_bytes(),b"safe")
    def test_read_plain_refuses_symlink_when_no_follow_available(self):
        if not hasattr(os,"O_NOFOLLOW"): self.skipTest("no O_NOFOLLOW")
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); target=td/"target"; target.write_text("{}"); link=td/"in"; link.symlink_to(target)
            with self.assertRaises(q.QualificationError): q.read_plain_file(link,"in")

if __name__=="__main__": unittest.main()
