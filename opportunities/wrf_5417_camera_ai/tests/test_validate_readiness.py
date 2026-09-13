import copy
import datetime as dt
import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("wrfcheck", HERE.parent / "validate_readiness.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
BASE = json.loads((HERE.parent / "submission_manifest.json").read_text())
NOW = dt.datetime(2026, 9, 13, 13, 30, tzinfo=dt.timezone.utc)


def prove(e):
    e["status"] = "PROVEN"
    e["evidence"] = ["synthetic:test"]


def ready_fixture():
    m = copy.deepcopy(BASE)
    m["intended_submission_state"] = v.READY
    prove(m["deadline"]["deadline_offset_recheck"])
    m["budget"]["wrf_request_usd"] = 300000
    m["budget"]["documented_eligible_contribution_usd"] = 99000
    prove(m["budget"]["budget_workbook"])
    prove(m["budget"]["budget_narrative"])
    for e in m["hard_gates"].values():
        prove(e)
    m["utility_participants"] = [
        {"name":"Synthetic A","sector":"drinking_water","consent_status":"PROVEN","consent_evidence":["synthetic:a"]},
        {"name":"Synthetic B","sector":"wastewater","consent_status":"PROVEN","consent_evidence":["synthetic:b"]},
    ]
    return m


class Tests(unittest.TestCase):
    def test_default_holds(self):
        state, reasons = v.check(copy.deepcopy(BASE), NOW)
        self.assertEqual(state, "HOLD")
        self.assertTrue(any("organization_my_portal_account" in x for x in reasons))

    def test_ready_spoof_holds(self):
        m = copy.deepcopy(BASE)
        m["intended_submission_state"] = v.READY
        state, reasons = v.check(m, NOW)
        self.assertEqual(state, "HOLD")
        self.assertIn("READY spoofed while blockers remain", reasons)

    def test_one_cent_short_cost_share_holds(self):
        m = ready_fixture()
        m["budget"]["documented_eligible_contribution_usd"] = 98999.99
        state, reasons = v.check(m, NOW)
        self.assertEqual(state, "HOLD")
        self.assertTrue(any("99000.00" in x for x in reasons))

    def test_public_name_without_consent_holds(self):
        m = ready_fixture()
        m["utility_participants"][0]["consent_status"] = "HOLD"
        m["utility_participants"][0]["consent_evidence"] = []
        state, reasons = v.check(m, NOW)
        self.assertEqual(state, "HOLD")
        self.assertTrue(any("consent not proven" in x for x in reasons))

    def test_expired_deadline_holds(self):
        m = ready_fixture()
        state, reasons = v.check(m, dt.datetime(2026, 9, 15, tzinfo=dt.timezone.utc))
        self.assertEqual(state, "HOLD")
        self.assertIn("deadline expired", reasons)

    def test_full_synthetic_fixture_reaches_review_ready_not_submission(self):
        m = ready_fixture()
        state, reasons = v.check(m, NOW)
        self.assertEqual(state, v.READY)
        self.assertEqual(reasons, [])
        self.assertFalse(m["submission_authority"]["carrier_may_submit"])


if __name__ == "__main__":
    unittest.main()
