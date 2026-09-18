from __future__ import annotations
import copy, importlib.util, json, tempfile, unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("nc_clm_validate",HERE/"validate_recovery.py")
mod=importlib.util.module_from_spec(SPEC); assert SPEC.loader is not None; SPEC.loader.exec_module(mod)
def load(name): return json.loads((HERE/name).read_text(encoding="utf-8"))

class CarrierTests(unittest.TestCase):
    def setUp(self): self.public=load("public_opportunity_20260917.json"); self.partner=load("partner_route_ledger_20260917.json")
    def public_bad(self,f):
        p=copy.deepcopy(self.public); f(p)
        with self.assertRaises(mod.PacketError): mod.validate_public(p)
    def partner_bad(self,f):
        p=copy.deepcopy(self.partner); f(p)
        with self.assertRaises(mod.PacketError): mod.validate_partner(p)
    def test_baseline(self): self.assertIn("NC_DHB_CLM_IDENTITY_BOUND",mod.validate_public(self.public)); self.assertIn("MUSE_ARBITRATION_NOT_REQUESTED",mod.validate_partner(self.partner))
    def test_duplicate_key(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.json"; p.write_text('{"schema_version":1,"schema_version":1}',encoding="utf-8")
            with self.assertRaises(mod.PacketError): mod.load_json(p)
    def test_bool_int_schema_alias(self): self.public_bad(lambda p:p.__setitem__("schema_version",True))
    def test_bool_int_amount_alias(self): self.partner_bad(lambda p:p["routes"][0]["commercial_hypothesis"].__setitem__("amount_minor",True))
    def test_identity_drift(self): self.public_bad(lambda p:p.__setitem__("solicitation_id","OTHER"))
    def test_portal_drift(self): self.public_bad(lambda p:p["owner_portal"].__setitem__("url","https://example.invalid"))
    def test_open_status_drift(self): self.public_bad(lambda p:p["owner_portal"].__setitem__("status","CLOSED"))
    def test_registration_claim(self): self.public_bad(lambda p:p["owner_portal"].__setitem__("vendor_registration_performed",True))
    def test_deadline_drift(self): self.public_bad(lambda p:p["public_time_gates"].__setitem__("proposal_due","2026-10-24T14:00:00-04:00"))
    def test_contract_scale_drift(self): self.public_bad(lambda p:p["public_scale"].__setitem__("active_medicaid_contracts_min",1))
    def test_user_scale_drift(self): self.public_bad(lambda p:p["public_scale"].__setitem__("authorized_users_approx",1))
    def test_buyer_authority_escalation(self): self.public_bad(lambda p:p["authority"].__setitem__("buyer_contact_authorized",True))
    def test_submission_authority_escalation(self): self.public_bad(lambda p:p["authority"].__setitem__("proposal_submission_authorized",True))
    def test_revenue_escalation(self): self.public_bad(lambda p:p["authority"].__setitem__("recognized_revenue",True))
    def test_second_partner(self): self.partner_bad(lambda p:p["routes"].append(copy.deepcopy(p["routes"][0])))
    def test_route_drift(self): self.partner_bad(lambda p:p["routes"][0].__setitem__("route","sales@mitratech.com"))
    def test_key_drift(self): self.partner_bad(lambda p:p["routes"][0].__setitem__("commercial_key","OTHER"))
    def test_gate_weakened(self): self.partner_bad(lambda p:p["routes"][0].__setitem__("qualification_gate","Ask if interested"))
    def test_amount_drift(self): self.partner_bad(lambda p:p["routes"][0]["commercial_hypothesis"].__setitem__("amount_minor",1))
    def test_false_acceptance(self): self.partner_bad(lambda p:p["routes"][0]["commercial_hypothesis"].__setitem__("offer_state","ACCEPTED"))
    def test_scope_collapse(self): self.partner_bad(lambda p:p["routes"][0].__setitem__("scope",["one"]))
    def test_send_authority(self): self.partner_bad(lambda p:p["routes"][0].__setitem__("send_authorized",True))
    def test_participation_claim(self): self.partner_bad(lambda p:p["routes"][0].__setitem__("candidate_confirmed_evaluating",True))
    def test_pending_requires_request(self): self.partner_bad(lambda p:p["routes"][0].__setitem__("state","MUSE_ARBITRATION_PENDING"))
    def test_clear_requires_receipt(self):
        def f(p):
            r=p["routes"][0]; r["state"]="MUSE_CLEAR_PROVIDER_SEND_PENDING"; r["muse_arbitration"]["request_ts"]=["req"]; r["muse_arbitration"]["explicit_clearance_observed"]=True
        self.partner_bad(f)
    def test_valid_clear_still_no_repo_send_authority(self):
        p=copy.deepcopy(self.partner); r=p["routes"][0]; r["state"]="MUSE_CLEAR_PROVIDER_SEND_PENDING"; r["muse_arbitration"]["request_ts"]=["req"]; r["muse_arbitration"]["explicit_clearance_observed"]=True; r["muse_arbitration"]["clearance_ts"]="clear"
        self.assertIn("MUSE_CLEAR_PROVIDER_SEND_PENDING",mod.validate_partner(p)); self.assertFalse(r["send_authorized"])
    def test_receipt_without_send(self): self.partner_bad(lambda p:p["routes"][0]["provider_send"].__setitem__("message_id","x"))
    def test_send_without_clearance(self):
        def f(p):
            r=p["routes"][0]; r["state"]="HARD_DNR_PROVIDER_SENT"; r["provider_send"]={"performed":True,"message_id":"m","thread_id":"t","sent_at":"2026-09-17T00:00:00-04:00"}
        self.partner_bad(f)
    def test_valid_send_requires_clearance_and_dnr(self):
        p=copy.deepcopy(self.partner); r=p["routes"][0]; r["state"]="HARD_DNR_PROVIDER_SENT"; r["muse_arbitration"]["request_ts"]=["req"]; r["muse_arbitration"]["explicit_clearance_observed"]=True; r["muse_arbitration"]["clearance_ts"]="clear"; r["provider_send"]={"performed":True,"message_id":"m","thread_id":"t","sent_at":"2026-09-17T00:00:00-04:00"}
        self.assertIn("HARD_DNR_PROVIDER_SENT",mod.validate_partner(p)); self.assertFalse(r["revenue"])

if __name__=="__main__": unittest.main()
