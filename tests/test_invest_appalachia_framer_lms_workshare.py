from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / "opportunities" / "invest_appalachia_framer_lms"
SPEC = importlib.util.spec_from_file_location("ia_workshare", LANE / "workshare.py")
assert SPEC and SPEC.loader
workshare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workshare)

class InvestAppalachiaWorkshareTests(unittest.TestCase):
    def setUp(self):
        self.packet = workshare.load_json(LANE / "current_packet.json")
        self.ws = workshare.load_json(LANE / "partner_workshare.json")

    def test_current_generation_yields_internal_workshare_only(self):
        receipt = workshare.evaluate(self.packet, self.ws)
        self.assertEqual(receipt["prime_posture"], "NO_CHANGE_PRIME_HOLD")
        self.assertEqual(receipt["workshare_posture"], "READY_FOR_INTERNAL_QUALIFIED_PRIME_SELECTION")
        self.assertEqual(receipt["specialist_price_usd"], 24000)
        self.assertEqual(receipt["commercial_status"], "PROPOSED_NOT_ACCEPTED")
        self.assertEqual(receipt["buyer_budget_fit"], "UNRESOLVED_QUALIFIED_PRIME_MUST_INTEGRATE_WITH_60000_CAP")
        self.assertEqual(receipt["money_state"], "NO_ACCEPTANCE_NO_RECEIVABLE_NO_REVENUE")
        self.assertTrue(receipt["muse_dm_clearance_required"])
        self.assertEqual(receipt["maximum_external_messages_if_cleared"], 1)

    def test_workshare_cannot_assert_contact_or_revenue_authority(self):
        forged = copy.deepcopy(self.ws)
        forged["authority"]["partner_contact_authorized"] = True
        with self.assertRaises(workshare.WorkshareError):
            workshare.validate_workshare(forged)
        forged = copy.deepcopy(self.ws)
        forged["authority"]["award_or_revenue_asserted"] = True
        with self.assertRaises(workshare.WorkshareError):
            workshare.validate_workshare(forged)

    def test_price_and_acceptance_state_are_frozen(self):
        forged = copy.deepcopy(self.ws)
        forged["commercial"]["price_usd"] = 60000
        with self.assertRaises(workshare.WorkshareError):
            workshare.validate_workshare(forged)
        forged = copy.deepcopy(self.ws)
        forged["commercial"]["commercial_status"] = "ACCEPTED"
        with self.assertRaises(workshare.WorkshareError):
            workshare.validate_workshare(forged)

    def test_budget_fit_cannot_be_self_promoted(self):
        forged = copy.deepcopy(self.ws)
        forged["commercial"]["buyer_budget_integration_state"] = "WITHIN_CAP"
        with self.assertRaises(workshare.WorkshareError):
            workshare.validate_workshare(forged)

    def test_qualification_generation_movement_invalidates_workshare(self):
        forged = copy.deepcopy(self.packet)
        forged["qualification"]["two_lms_platform_implementations"]["state"] = "VERIFIED"
        with self.assertRaises(workshare.WorkshareError):
            workshare.evaluate(forged, self.ws)

    def test_scope_or_prime_ownership_cannot_be_widened_without_review(self):
        forged = copy.deepcopy(self.ws)
        forged["scope"].append("prime proposal submission")
        with self.assertRaises(workshare.WorkshareError):
            workshare.validate_workshare(forged)
        forged = copy.deepcopy(self.ws)
        forged["qualified_prime_must_own"] = []
        with self.assertRaises(workshare.WorkshareError):
            workshare.validate_workshare(forged)

    def test_duplicate_and_nonfinite_json_rejected(self):
        p = LANE / "_hostile_workshare_tmp.json"
        try:
            p.write_bytes(b'{"a":1,"a":2}')
            with self.assertRaises(workshare.WorkshareError):
                workshare.load_json(p)
            p.write_bytes(b'{"a":NaN}')
            with self.assertRaises(workshare.WorkshareError):
                workshare.load_json(p)
        finally:
            p.unlink(missing_ok=True)

if __name__ == "__main__":
    unittest.main()
