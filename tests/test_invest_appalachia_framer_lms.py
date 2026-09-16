from copy import deepcopy
from datetime import datetime, timezone
import json
import unittest
from pathlib import Path

from opportunities.invest_appalachia_framer_lms.carrier import PursuitError, evaluate, load_json, normalize

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "opportunities" / "invest_appalachia_framer_lms" / "current_packet.json"

class PursuitCarrierTests(unittest.TestCase):
    def packet(self):
        return json.loads(PACKET.read_text(encoding="utf-8"))

    def test_current_packet_is_prime_hold_and_teaming_ready(self):
        out=evaluate(self.packet(),now=datetime(2026,9,16,14,0,tzinfo=timezone.utc))
        self.assertEqual(out["prime_status"],"PRIME_HOLD")
        self.assertEqual(out["teaming_status"],"TEAMING_PACKAGE_READY_INTERNAL")
        self.assertIn("two_lms_platform_implementations",out["unverified_or_missing_gates"])
        self.assertFalse(out["submission_authorized"])
        self.assertFalse(out["award_or_revenue_asserted"])

    def test_verified_without_evidence_is_rejected(self):
        p=self.packet();p["qualification"]["two_lms_platform_implementations"]["state"]="VERIFIED"
        with self.assertRaises(PursuitError):normalize(p)

    def test_all_gates_still_need_complete_buyer_attachments(self):
        p=self.packet()
        for gate in p["qualification"].values():gate["state"]="VERIFIED";gate["evidence_refs"]=["retained:evidence"]
        p["proposal"]["attachments_complete"]=True
        self.assertEqual(evaluate(p,now=datetime(2026,9,16,14,0,tzinfo=timezone.utc))["prime_status"],"PRIME_HOLD")

    def test_only_complete_sources_and_gates_can_reach_internal_prime_review(self):
        p=self.packet();p["opportunity"]["attachments_status"]="COMPLETE";p["proposal"]["attachments_complete"]=True
        for name,gate in p["qualification"].items():gate["state"]="VERIFIED";gate["evidence_refs"]=[f"retained:{name}"]
        out=evaluate(p,now=datetime(2026,9,16,14,0,tzinfo=timezone.utc))
        self.assertEqual(out["prime_status"],"PRIME_QUALIFICATION_EVIDENCED_INTERNAL_REVIEW")
        self.assertFalse(out["submission_authorized"])

    def test_budget_over_cap_is_rejected(self):
        p=self.packet();p["proposal"]["proposed_total_usd"]=60001
        with self.assertRaises(PursuitError):normalize(p)

    def test_any_external_authority_is_rejected(self):
        for field in self.packet()["authority"]:
            p=self.packet();p["authority"][field]=True
            with self.subTest(field=field),self.assertRaises(PursuitError):normalize(p)

    def test_deadline_is_hard(self):
        out=evaluate(self.packet(),now=datetime(2026,9,22,21,0,tzinfo=timezone.utc))
        self.assertEqual(out["prime_status"],"DEADLINE_PASSED");self.assertEqual(out["teaming_status"],"DEADLINE_PASSED")

    def test_duplicate_json_key_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"dup.json";path.write_text('{"a":1,"a":2}',encoding="utf-8")
            with self.assertRaises(PursuitError):load_json(path)

    def test_receipt_is_deterministic(self):
        when=datetime(2026,9,16,14,0,tzinfo=timezone.utc)
        self.assertEqual(evaluate(self.packet(),now=when),evaluate(deepcopy(self.packet()),now=when))

if __name__=="__main__":unittest.main()
