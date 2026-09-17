from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sd_edss_validate", HERE / "validate_recovery.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)

def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))

class SdEdssCarrierTests(unittest.TestCase):
    def setUp(self):
        self.public = load("public_opportunity_20260917.json")
        self.partner = load("partner_route_ledger_20260917.json")

    def public_bad(self, mutate):
        p = copy.deepcopy(self.public); mutate(p)
        with self.assertRaises(mod.PacketError): mod.validate_public(p)

    def partner_bad(self, mutate):
        p = copy.deepcopy(self.partner); mutate(p)
        with self.assertRaises(mod.PacketError): mod.validate_partner(p)

    def test_baseline(self):
        self.assertIn("INVITATION_ONLY_BOUND", mod.validate_public(self.public))
        self.assertIn("MUSE_ARBITRATION_NOT_REQUESTED", mod.validate_partner(self.partner))

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.json"; p.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(mod.PacketError): mod.load_json(p)

    def test_bool_int_schema_alias_rejected(self):
        self.public_bad(lambda p: p.__setitem__("schema_version", True))

    def test_bool_int_amount_alias_rejected(self):
        self.partner_bad(lambda p: p["routes"][0]["commercial_hypothesis"].__setitem__("amount_minor", True))

    def test_solicitation_drift_rejected(self):
        self.public_bad(lambda p: p.__setitem__("solicitation_id", "OTHER"))

    def test_invitation_mode_drift_rejected(self):
        self.public_bad(lambda p: p.__setitem__("procurement_mode", "OPEN"))

    def test_loi_deadline_drift_rejected(self):
        self.public_bad(lambda p: p["public_time_gates"].__setitem__("letter_of_intent_due", "2026-09-09"))

    def test_proposal_deadline_drift_rejected(self):
        self.public_bad(lambda p: p["public_time_gates"].__setitem__("proposal_due", "2026-10-20T23:59:00-05:00"))

    def test_invited_offeror_escalation_rejected(self):
        self.public_bad(lambda p: p["authority"].__setitem__("invited_offeror", True))

    def test_loi_claim_rejected(self):
        self.public_bad(lambda p: p["authority"].__setitem__("letter_of_intent_submitted", True))

    def test_buyer_contact_authority_rejected(self):
        self.public_bad(lambda p: p["authority"].__setitem__("buyer_contact_authorized", True))

    def test_submission_authority_rejected(self):
        self.public_bad(lambda p: p["authority"].__setitem__("bid_submission_authorized", True))

    def test_revenue_claim_rejected(self):
        self.public_bad(lambda p: p["authority"].__setitem__("recognized_revenue", True))

    def test_second_partner_rejected(self):
        self.partner_bad(lambda p: p["routes"].append(copy.deepcopy(p["routes"][0])))

    def test_route_drift_rejected(self):
        self.partner_bad(lambda p: p["routes"][0].__setitem__("route", "info@inductivehealth.com"))

    def test_key_drift_rejected(self):
        self.partner_bad(lambda p: p["routes"][0].__setitem__("commercial_key", "OTHER"))

    def test_qualification_gate_removal_rejected(self):
        self.partner_bad(lambda p: p["routes"][0].__setitem__("qualification_gate", "Ask about scope"))

    def test_amount_drift_rejected(self):
        self.partner_bad(lambda p: p["routes"][0]["commercial_hypothesis"].__setitem__("amount_minor", 1))

    def test_false_acceptance_rejected(self):
        self.partner_bad(lambda p: p["routes"][0]["commercial_hypothesis"].__setitem__("offer_state", "ACCEPTED"))

    def test_send_authority_cannot_be_minted(self):
        self.partner_bad(lambda p: p["routes"][0].__setitem__("send_authorized", True))

    def test_participation_claim_rejected(self):
        self.partner_bad(lambda p: p["routes"][0].__setitem__("candidate_confirmed_invited_participating", True))

    def test_pending_requires_request(self):
        self.partner_bad(lambda p: p["routes"][0].__setitem__("state", "MUSE_ARBITRATION_PENDING"))

    def test_clear_requires_receipt(self):
        def mutate(p):
            r=p["routes"][0]; r["state"]="MUSE_CLEAR_PROVIDER_SEND_PENDING"; r["muse_arbitration"]["request_ts"]=["x"]; r["muse_arbitration"]["explicit_clearance_observed"]=True
        self.partner_bad(mutate)

    def test_valid_muse_clear_still_no_repo_send_authority(self):
        p=copy.deepcopy(self.partner); r=p["routes"][0]
        r["state"]="MUSE_CLEAR_PROVIDER_SEND_PENDING"; r["muse_arbitration"]["request_ts"]=["req"]; r["muse_arbitration"]["explicit_clearance_observed"]=True; r["muse_arbitration"]["clearance_ts"]="clear"
        self.assertIn("MUSE_CLEAR_PROVIDER_SEND_PENDING", mod.validate_partner(p)); self.assertFalse(r["send_authorized"])

    def test_provider_receipt_without_send_rejected(self):
        self.partner_bad(lambda p: p["routes"][0]["provider_send"].__setitem__("message_id", "x"))

    def test_provider_send_without_clearance_rejected(self):
        def mutate(p):
            r=p["routes"][0]; r["state"]="HARD_DNR_PROVIDER_SENT"; r["provider_send"]={"performed":True,"message_id":"m","thread_id":"t","sent_at":"2026-09-17T00:00:00-04:00"}
        self.partner_bad(mutate)

    def test_valid_provider_send_requires_clearance_and_dnr(self):
        p=copy.deepcopy(self.partner); r=p["routes"][0]
        r["state"]="HARD_DNR_PROVIDER_SENT"; r["muse_arbitration"]["request_ts"]=["req"]; r["muse_arbitration"]["explicit_clearance_observed"]=True; r["muse_arbitration"]["clearance_ts"]="clear"; r["provider_send"]={"performed":True,"message_id":"m","thread_id":"t","sent_at":"2026-09-17T00:00:00-04:00"}
        self.assertIn("HARD_DNR_PROVIDER_SENT", mod.validate_partner(p)); self.assertFalse(r["revenue"])

if __name__ == "__main__": unittest.main()
