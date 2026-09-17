from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
import validate

ROOT = Path(__file__).resolve().parent
RAW = (ROOT / "packet.json").read_text(encoding="utf-8")

class FultonPacketTests(unittest.TestCase):
    def packet(self):
        return validate.loads_exact(RAW)

    def test_current_packet_valid(self):
        self.assertTrue(validate.validate(self.packet()))

    def test_duplicate_key_rejected(self):
        with self.assertRaises(validate.ValidationError):
            validate.loads_exact('{"a":1,"a":2}')

    def test_direct_prime_escalation_rejected(self):
        p = self.packet()
        p["qualification"]["posture"] = "PRIME_READY"
        with self.assertRaises(validate.ValidationError):
            validate.validate(p)

    def test_target_contact_state_cannot_be_minted_by_repo(self):
        p = self.packet()
        p["target"]["state"] = "CONTACTED"
        with self.assertRaises(validate.ValidationError):
            validate.validate(p)

    def test_acceptance_revenue_authority_rejected(self):
        for key in ("accepted_workshare","award_claimed","payment_claimed","revenue_claimed"):
            p = self.packet()
            p["authority"][key] = True
            with self.subTest(key=key), self.assertRaises(validate.ValidationError):
                validate.validate(p)

    def test_bool_is_not_price_int(self):
        p = self.packet()
        p["workshare"]["fixed_price_usd"] = True
        with self.assertRaises(validate.ValidationError):
            validate.validate(p)

    def test_solicitation_identity_and_deadline_drift_rejected(self):
        for key, value in (
            ("registry_id","PE-DRIFT"),
            ("response_deadline","2026-09-30T14:30:00-04:00"),
            ("budget","250000"),
        ):
            p = self.packet()
            p["opportunity"][key] = value
            with self.subTest(key=key), self.assertRaises(validate.ValidationError):
                validate.validate(p)

    def test_target_route_drift_rejected(self):
        p = self.packet()
        p["target"]["route"] = "sales@mgt.us"
        with self.assertRaises(validate.ValidationError):
            validate.validate(p)

if __name__ == "__main__":
    unittest.main()
