import copy
import hashlib
import json
import unittest

from .engine import (
    OFFICIAL_SOURCES,
    REQUIRED_TEAM_GATES,
    build_source_authority,
    compile_assessment,
    verify_assessment,
    ValidationError,
)

KEY = bytes.fromhex("11" * 32)
KEY_ID = "test-owner"
AS_OF = "2026-09-16T12:00:00+00:00"


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def sources(retrieved=True):
    rows = []
    for sid, spec in sorted(OFFICIAL_SOURCES.items()):
        rows.append({
            "id": sid,
            "kind": spec["kind"],
            "url": spec["url"],
            "retrieved": retrieved,
            "current": retrieved,
            "sha256": digest(sid) if retrieved else None,
            "size_bytes": 100 + len(sid) if retrieved else 0,
            "issued_date": "2026-09-14",
            "supersedes": [],
        })
    return rows


def team(proven=True):
    party = {
        "ERP_OR_GMS_PRODUCT_AUTHORITY":"ERP_OEM",
        "THREE_SIMILAR_PUBLIC_SECTOR_PROJECTS":"PRIME",
        "PUBLIC_SECTOR_REFERENCES":"PRIME",
        "IMPLEMENTATION_LEAD":"PRIME",
        "SUPPORT_MAINTENANCE_MODEL":"ERP_OEM",
        "SHORTLIST_DEMO_READINESS":"PRIME",
        "PHYSICAL_SUBMISSION_OWNER":"PRIME",
        "INSURANCE_BINDABILITY_PLAN":"PRIME",
        "SUBCONTRACT_DISCLOSURE_AND_CONSENT_PLAN":"PRIME",
    }
    return [{"id":g,"evidence_state":"PROVEN" if proven else "UNKNOWN","evidence_refs":[f"evidence:{g}"] if proven else [],"responsible_party":party[g]} for g in sorted(REQUIRED_TEAM_GATES)]


def implementation():
    vals = [
        ("ACC","HUMAN_ACCEPTANCE_BOUNDARY","BUYER"),
        ("EXC","EXCEPTION_DISPOSITION","SHARED"),
        ("IFC","INTERFACE_REPLAY","TJL"),
        ("MIG","MIGRATION_RECONCILIATION","TJL"),
        ("UAT","REQUIREMENT_UAT_TRACE","SHARED"),
    ]
    return [{"id":i,"kind":k,"state":"DEFINED","evidence_refs":[f"plan:{i}"],"owner":o} for i,k,o in vals]


def packet(src=None, proven_team=True):
    src = src or sources(True)
    a_sha = next(x["sha256"] for x in src if x["id"] == "appendix_a")
    req = {"id":"A.1","source_id":"appendix_a","source_sha256":a_sha,"domain":"AP","mandatory":True,"text_fingerprint":digest("functional requirement one"),"response_state":"READY","owner":"ERP_PRIME","evidence_refs":["evidence:demo"]}
    return {
        "schema":"vctc-erp-gms-pursuit/v1",
        "solicitation":{
            "id":"VCTC-ERP-GMS-2026-09-14",
            "title":"Enterprise Resource Planning (ERP) System, Grants Management System, and Implementation Services",
            "proposal_deadline":"2026-11-09T15:00:00-08:00",
            "evaluation_points":{"firm_qualifications":15,"proposed_solution":10,"functional_requirements":20,"implementation_approach":20,"support_maintenance":15,"cost":20},
            "submission_mode":"PHYSICAL_PAPER_PLUS_THUMB_DRIVE",
            "prime_posture":"TEAMING_SPECIALIST_SUBCONTRACT_FIRST",
        },
        "sources": src,
        "requirements": [req],
        "team_gates": team(proven_team),
        "implementation_evidence": implementation(),
        "commercial":{"state":"PROPOSED_NOT_ACCEPTED","workshare_minor":3500000,"currency":"USD","pricing_authorized":False,"external_contact_authorized":False},
    }


class VCTCTests(unittest.TestCase):
    def auth(self, src):
        return build_source_authority(src, key_id=KEY_ID, key=KEY, issued_at=AS_OF)

    def compile(self, p):
        return compile_assessment(p, self.auth(p["sources"]), key=KEY, expected_key_id=KEY_ID, as_of=AS_OF)

    def test_ready(self):
        p = packet()
        a = self.compile(p)
        self.assertEqual(a["state"], "READY_FOR_OWNER_PROPOSAL_REVIEW")
        self.assertTrue(verify_assessment(p, self.auth(p["sources"]), a, key=KEY, expected_key_id=KEY_ID))
        self.assertTrue(all(v is False for v in a["authority"].values()))

    def test_discovery_missing_rfp_holds(self):
        src = sources(False)
        p = packet(sources(True))
        # No requirement may bind to an unretrieved source, so use an empty matrix for discovery.
        p["sources"] = src
        p["requirements"] = []
        a = compile_assessment(p, self.auth(src), key=KEY, expected_key_id=KEY_ID, as_of=AS_OF)
        self.assertEqual(a["state"], "HOLD_CONTROLLING_RFP_REQUIRED")

    def test_only_appendices_missing_holds(self):
        src = sources(True)
        for row in src:
            if row["id"] in {"appendix_a","appendix_b"}:
                row.update(retrieved=False,current=False,sha256=None,size_bytes=0)
        p = packet(sources(True)); p["sources"] = src; p["requirements"] = []
        a = compile_assessment(p, self.auth(src), key=KEY, expected_key_id=KEY_ID, as_of=AS_OF)
        self.assertEqual(a["state"], "HOLD_APPENDIX_BYTES_REQUIRED")

    def test_wrong_key_rejected(self):
        p = packet(); auth = self.auth(p["sources"])
        with self.assertRaises(ValidationError):
            compile_assessment(p, auth, key=b"x"*32, expected_key_id=KEY_ID, as_of=AS_OF)

    def test_source_mutation_rejected(self):
        p = packet(); auth = self.auth(p["sources"])
        p["sources"][0]["sha256"] = digest("mutated")
        with self.assertRaises(ValidationError):
            compile_assessment(p, auth, key=KEY, expected_key_id=KEY_ID, as_of=AS_OF)

    def test_authority_mutation_rejected(self):
        p = packet(); auth = self.auth(p["sources"])
        auth["sources"][0]["current"] = False
        with self.assertRaises(ValidationError):
            compile_assessment(p, auth, key=KEY, expected_key_id=KEY_ID, as_of=AS_OF)

    def test_wrong_key_id_rejected(self):
        p = packet()
        with self.assertRaises(ValidationError):
            compile_assessment(p, self.auth(p["sources"]), key=KEY, expected_key_id="other", as_of=AS_OF)

    def test_requirement_source_digest_rejected(self):
        p = packet(); p["requirements"][0]["source_sha256"] = digest("bad")
        with self.assertRaises(ValidationError): self.compile(p)

    def test_requirement_semantic_remint_rejected(self):
        p = packet(); b = copy.deepcopy(p["requirements"][0]); b["id"] = "A.2"; p["requirements"].append(b)
        with self.assertRaises(ValidationError): self.compile(p)

    def test_mandatory_gap_holds(self):
        p = packet(); p["requirements"][0]["response_state"] = "HOLD"; p["requirements"][0]["evidence_refs"] = []
        a = self.compile(p)
        self.assertEqual(a["state"], "HOLD_MANDATORY_REQUIREMENT_GAPS")

    def test_ready_without_evidence_rejected(self):
        p = packet(); p["requirements"][0]["evidence_refs"] = []
        with self.assertRaises(ValidationError): self.compile(p)

    def test_team_unknown_holds(self):
        p = packet(proven_team=False)
        a = self.compile(p)
        self.assertEqual(a["state"], "HOLD_TEAM_QUALIFICATION")
        self.assertEqual(len(a["team_gate_gaps"]), len(REQUIRED_TEAM_GATES))

    def test_missing_team_gate_rejected(self):
        p = packet(); p["team_gates"].pop()
        with self.assertRaises(ValidationError): self.compile(p)

    def test_proven_team_gate_requires_evidence(self):
        p = packet(); p["team_gates"][0]["evidence_refs"] = []
        with self.assertRaises(ValidationError): self.compile(p)

    def test_missing_implementation_kind_holds(self):
        p = packet(); p["implementation_evidence"] = p["implementation_evidence"][:-1]
        a = self.compile(p)
        self.assertEqual(a["state"], "HOLD_IMPLEMENTATION_EVIDENCE_PLAN")

    def test_duplicate_implementation_kind_rejected(self):
        p = packet(); x = copy.deepcopy(p["implementation_evidence"][0]); x["id"] = "ACC2"; p["implementation_evidence"].append(x)
        with self.assertRaises(ValidationError): self.compile(p)

    def test_commercial_authority_cannot_be_true(self):
        p = packet(); p["commercial"]["external_contact_authorized"] = True
        with self.assertRaises(ValidationError): self.compile(p)

    def test_pricing_authority_cannot_be_true(self):
        p = packet(); p["commercial"]["pricing_authorized"] = True
        with self.assertRaises(ValidationError): self.compile(p)

    def test_bool_money_rejected(self):
        p = packet(); p["commercial"]["workshare_minor"] = True
        with self.assertRaises(ValidationError): self.compile(p)

    def test_deadline_passed_holds(self):
        p = packet()
        a = compile_assessment(p, self.auth(p["sources"]), key=KEY, expected_key_id=KEY_ID, as_of="2026-11-10T00:00:00-08:00")
        self.assertEqual(a["state"], "HOLD_DEADLINE_PASSED")

    def test_wrong_evaluation_weights_rejected(self):
        p = packet(); p["solicitation"]["evaluation_points"]["cost"] = 19
        with self.assertRaises(ValidationError): self.compile(p)

    def test_wrong_submission_mode_rejected(self):
        p = packet(); p["solicitation"]["submission_mode"] = "ELECTRONIC"
        with self.assertRaises(ValidationError): self.compile(p)

    def test_extra_packet_key_rejected(self):
        p = packet(); p["extra"] = 1
        with self.assertRaises(ValidationError): self.compile(p)

    def test_unretrieved_source_cannot_claim_current(self):
        src = sources(False); src[0]["current"] = True
        with self.assertRaises(ValidationError): self.auth(src)

    def test_source_url_drift_rejected(self):
        src = sources(True); src[0]["url"] += "?mirror=1"
        with self.assertRaises(ValidationError): self.auth(src)

    def test_assessment_tamper_rejected(self):
        p = packet(); auth = self.auth(p["sources"]); a = compile_assessment(p, auth, key=KEY, expected_key_id=KEY_ID, as_of=AS_OF)
        a["state"] = "READY_FOR_OWNER_PROPOSAL_REVIEW_TAMPERED"
        with self.assertRaises(ValidationError): verify_assessment(p, auth, a, key=KEY, expected_key_id=KEY_ID)

    def test_deterministic_reorder(self):
        p = packet(); a1 = self.compile(p)
        p["team_gates"] = list(reversed(p["team_gates"])); p["implementation_evidence"] = list(reversed(p["implementation_evidence"]))
        a2 = self.compile(p)
        self.assertEqual(a1, a2)

    def test_workshare_is_reference_only(self):
        p = packet(); a = self.compile(p)
        self.assertEqual(a["proposed_workshare_minor"], 3500000)
        self.assertEqual(a["commercial_state"], "PROPOSED_NOT_ACCEPTED")
        self.assertFalse(a["authority"]["price_commitment"])


if __name__ == "__main__":
    unittest.main()
