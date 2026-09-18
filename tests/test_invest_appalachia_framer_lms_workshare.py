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

    def test_runtime_semantics_ignore_post_import_global_rebinding(self):
        baseline = workshare.evaluate(self.packet, self.ws)
        original_error = workshare.WorkshareError
        originals = {
            "SCHEMA": workshare.SCHEMA,
            "OPPORTUNITY_ID": workshare.OPPORTUNITY_ID,
            "QUALIFICATION_GENERATION_SHA256": workshare.QUALIFICATION_GENERATION_SHA256,
            "WORKSHARE_SHA256": workshare.WORKSHARE_SHA256,
            "PRICE_USD": workshare.PRICE_USD,
            "BUYER_CAP_USD": workshare.BUYER_CAP_USD,
            "canonical_json": workshare.canonical_json,
            "digest": workshare.digest,
            "load_json": workshare.load_json,
            "validate_qualification_generation": workshare.validate_qualification_generation,
            "validate_workshare": workshare.validate_workshare,
            "WorkshareError": workshare.WorkshareError,
        }

        class ForgedWorkshareError(Exception):
            pass

        try:
            workshare.SCHEMA = "forged"
            workshare.OPPORTUNITY_ID = "forged"
            workshare.QUALIFICATION_GENERATION_SHA256 = "f" * 64
            workshare.WORKSHARE_SHA256 = "f" * 64
            workshare.PRICE_USD = 60000
            workshare.BUYER_CAP_USD = 999999
            workshare.canonical_json = lambda value: b"forged"
            workshare.digest = lambda value: "f" * 64
            workshare.load_json = lambda path: {"forged": True}
            workshare.validate_qualification_generation = lambda packet: None
            workshare.validate_workshare = lambda value: value
            workshare.WorkshareError = ForgedWorkshareError

            rebuilt = workshare.evaluate(self.packet, self.ws)
            self.assertEqual(rebuilt, baseline)
            self.assertEqual(rebuilt["specialist_price_usd"], 24000)
            self.assertEqual(rebuilt["buyer_budget_cap_usd"], 60000)
            self.assertEqual(rebuilt["commercial_status"], "PROPOSED_NOT_ACCEPTED")
            self.assertEqual(rebuilt["prime_posture"], "NO_CHANGE_PRIME_HOLD")
            self.assertFalse(rebuilt["partner_contact_authorized"])
            self.assertFalse(rebuilt["payment_authorized"])
            self.assertFalse(rebuilt["award_or_revenue_asserted"])

            forged = copy.deepcopy(self.ws)
            forged["commercial"]["commercial_status"] = "ACCEPTED"
            with self.assertRaises(original_error):
                workshare.evaluate(self.packet, forged)
        finally:
            for name, value in originals.items():
                setattr(workshare, name, value)


if __name__ == "__main__":
    unittest.main()
