from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tarc_validate_recovery", HERE / "validate_recovery.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)

def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))

class TarcCarrierTests(unittest.TestCase):
    def setUp(self):
        self.public = load("public_opportunity_20260917.json")
        self.partner = load("partner_route_ledger_20260917.json")

    def assert_public_bad(self, mutate):
        packet = copy.deepcopy(self.public)
        mutate(packet)
        with self.assertRaises(mod.PacketError):
            mod.validate_public(packet)

    def assert_partner_bad(self, mutate):
        packet = copy.deepcopy(self.partner)
        mutate(packet)
        with self.assertRaises(mod.PacketError):
            mod.validate_partner(packet)

    def test_baseline(self):
        self.assertIn("TARC_20262046_IDENTITY_BOUND", mod.validate_public(self.public))
        result = mod.validate_partner(self.partner)
        self.assertIn("MUSE_ARBITRATION_PENDING", result)
        self.assertIn("REPOSITORY_SEND_AUTHORITY_FALSE", result)

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.json"
            p.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(mod.PacketError):
                mod.load_json(p)

    def test_bool_int_alias_rejected_public(self):
        self.assert_public_bad(lambda p: p.__setitem__("schema_version", True))

    def test_bool_int_alias_rejected_amount(self):
        self.assert_partner_bad(lambda p: p["routes"][0]["commercial_hypothesis"].__setitem__("amount_minor", True))

    def test_identity_drift_rejected(self):
        self.assert_public_bad(lambda p: p.__setitem__("solicitation_id", "20262047"))

    def test_portal_url_drift_rejected(self):
        self.assert_public_bad(lambda p: p["official_portal"].__setitem__("url", "https://example.invalid"))

    def test_pack_custody_claim_rejected(self):
        self.assert_public_bad(lambda p: p["official_portal"].__setitem__("solicitation_pack_acquired", True))

    def test_fake_pack_digest_rejected(self):
        self.assert_public_bad(lambda p: p["official_portal"].__setitem__("solicitation_pack_sha256", "0"*64))

    def test_intent_deadline_drift_rejected(self):
        self.assert_public_bad(lambda p: p["public_time_gates"].__setitem__("intent_to_bid_due", "2026-10-07T12:00:00-04:00"))

    def test_proposal_deadline_drift_rejected(self):
        self.assert_public_bad(lambda p: p["public_time_gates"].__setitem__("proposal_due", "2026-10-16T12:00:00-04:00"))

    def test_buyer_authority_escalation_rejected(self):
        self.assert_public_bad(lambda p: p["authority"].__setitem__("buyer_contact_authorized", True))

    def test_submission_authority_escalation_rejected(self):
        self.assert_public_bad(lambda p: p["authority"].__setitem__("bid_submission_authorized", True))

    def test_revenue_escalation_rejected(self):
        self.assert_public_bad(lambda p: p["authority"].__setitem__("recognized_revenue", True))

    def test_second_partner_rejected(self):
        self.assert_partner_bad(lambda p: p["routes"].append(copy.deepcopy(p["routes"][0])))

    def test_route_drift_rejected(self):
        self.assert_partner_bad(lambda p: p["routes"][0].__setitem__("route", "info@cherryroad.com"))

    def test_commercial_key_drift_rejected(self):
        self.assert_partner_bad(lambda p: p["routes"][0].__setitem__("commercial_key", "OTHER"))

    def test_amount_drift_rejected(self):
        self.assert_partner_bad(lambda p: p["routes"][0]["commercial_hypothesis"].__setitem__("amount_minor", 1))

    def test_false_acceptance_rejected(self):
        self.assert_partner_bad(lambda p: p["routes"][0]["commercial_hypothesis"].__setitem__("offer_state", "ACCEPTED"))

    def test_scope_collapse_rejected(self):
        self.assert_partner_bad(lambda p: p["routes"][0].__setitem__("scope", ["one"]))

    def test_prime_authority_collapse_rejected(self):
        self.assert_partner_bad(lambda p: p["routes"][0].__setitem__("retained_by_prime", ["one"]))

    def test_send_authority_cannot_be_minted(self):
        self.assert_partner_bad(lambda p: p["routes"][0].__setitem__("send_authorized", True))

    def test_clear_state_requires_receipt(self):
        def mutate(p):
            r = p["routes"][0]
            r["state"] = "MUSE_CLEAR_PROVIDER_SEND_PENDING"
            r["muse_arbitration"]["explicit_clearance_observed"] = True
            r["muse_arbitration"]["clearance_ts"] = None
        self.assert_partner_bad(mutate)

    def test_valid_muse_clear_still_has_no_repo_send_authority(self):
        p = copy.deepcopy(self.partner)
        r = p["routes"][0]
        r["state"] = "MUSE_CLEAR_PROVIDER_SEND_PENDING"
        r["muse_arbitration"]["explicit_clearance_observed"] = True
        r["muse_arbitration"]["clearance_ts"] = "1789619999.000001"
        self.assertIn("MUSE_CLEAR_PROVIDER_SEND_PENDING", mod.validate_partner(p))
        self.assertIs(r["send_authorized"], False)

    def test_provider_receipt_without_send_rejected(self):
        self.assert_partner_bad(lambda p: p["routes"][0]["provider_send"].__setitem__("message_id", "x"))

    def test_provider_send_without_clearance_rejected(self):
        def mutate(p):
            r = p["routes"][0]
            r["state"] = "HARD_DNR_PROVIDER_SENT"
            r["provider_send"] = {
                "performed": True,
                "message_id": "m",
                "thread_id": "t",
                "sent_at": "2026-09-17T00:00:00-04:00",
            }
        self.assert_partner_bad(mutate)

    def test_valid_provider_sent_requires_hard_dnr_and_clearance(self):
        p = copy.deepcopy(self.partner)
        r = p["routes"][0]
        r["state"] = "HARD_DNR_PROVIDER_SENT"
        r["muse_arbitration"]["explicit_clearance_observed"] = True
        r["muse_arbitration"]["clearance_ts"] = "1789619999.000001"
        r["provider_send"] = {
            "performed": True,
            "message_id": "m",
            "thread_id": "t",
            "sent_at": "2026-09-17T00:00:00-04:00",
        }
        self.assertIn("HARD_DNR_PROVIDER_SENT", mod.validate_partner(p))
        self.assertFalse(r["accepted_workshare"])
        self.assertFalse(r["revenue"])

if __name__ == "__main__":
    unittest.main()
