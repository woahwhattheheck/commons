from copy import deepcopy
import json
import unittest
from pathlib import Path

from opportunities.invest_appalachia_framer_lms.carrier import CURRENT_PACKET_SHA256, PursuitError, digest, evaluate, load_json, normalize

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "opportunities" / "invest_appalachia_framer_lms" / "current_packet.json"

class PursuitCarrierTests(unittest.TestCase):
    def packet(self):
        return json.loads(PACKET.read_text(encoding="utf-8"))

    def test_current_packet_is_exact_retained_generation_and_prime_hold(self):
        p=self.packet();self.assertEqual(digest(p),CURRENT_PACKET_SHA256)
        out=evaluate(p)
        self.assertEqual(out["prime_status"],"PRIME_HOLD")
        self.assertEqual(out["teaming_status"],"TEAMING_ROUTE_OPEN_INTERNAL")
        self.assertEqual(out["attachments_status"],"PARTIAL")
        self.assertFalse(out["deadline_currentness_authoritative"])
        self.assertTrue(out["fresh_deadline_recensus_required_before_action"])
        self.assertFalse(out["submission_authorized"]);self.assertFalse(out["award_or_revenue_asserted"])

    def test_calendar_clear_does_not_verify_project_start_capacity(self):
        gate=self.packet()["qualification"]["start_capacity_2026_10_13"]
        self.assertEqual(gate["state"],"HOLD")
        self.assertTrue(gate["evidence_refs"])
        self.assertIn("not staffing/project-start capacity",gate["note"])

    def test_caller_cannot_promote_any_qualification_gate(self):
        for name in self.packet()["qualification"]:
            p=self.packet();p["qualification"][name]["state"]="VERIFIED";p["qualification"][name]["evidence_refs"]=[f"caller:{name}"]
            with self.subTest(name=name),self.assertRaises(PursuitError):normalize(p)

    def test_caller_cannot_complete_buyer_attachments(self):
        p=self.packet();p["opportunity"]["attachments_status"]="COMPLETE";p["proposal"]["attachments_complete"]=True
        with self.assertRaises(PursuitError):normalize(p)

    def test_caller_cannot_change_platform_or_budget(self):
        for field,value in (("platform_recommendation","CALLER_SELECTED"),("proposed_total_usd",59999),("year1_license_usd",1),("post_year1_recurring_usd",1)):
            p=self.packet();p["proposal"][field]=value
            with self.subTest(field=field),self.assertRaises(PursuitError):normalize(p)

    def test_any_external_authority_mutation_is_rejected(self):
        for field in self.packet()["authority"]:
            p=self.packet();p["authority"][field]=True
            with self.subTest(field=field),self.assertRaises(PursuitError):normalize(p)

    def test_duplicate_json_key_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"dup.json";path.write_text('{"a":1,"a":2}',encoding="utf-8")
            with self.assertRaises(PursuitError):load_json(path)

    def test_lone_surrogate_generation_fails_closed(self):
        p=self.packet();p["qualification"]["adult_learning_packaging"]["note"]="\ud800"
        with self.assertRaises(PursuitError):normalize(p)

    def test_receipt_is_deterministic(self):
        self.assertEqual(evaluate(self.packet()),evaluate(deepcopy(self.packet())))

if __name__=="__main__":unittest.main()
