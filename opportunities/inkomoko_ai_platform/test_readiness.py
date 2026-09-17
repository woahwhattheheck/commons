from __future__ import annotations
import copy,tempfile,unittest
from datetime import timedelta
from opportunities.inkomoko_ai_platform.core import CarrierError
from opportunities.inkomoko_ai_platform.engine import _compile_at,_verify_at
from opportunities.inkomoko_ai_platform.report import publish,render_markdown
from test_support import NOW,all_evidence,buyer,fixture

class ReadinessTests(unittest.TestCase):
    def setUp(self):self.ref=fixture("reference_rfp.json");self.c=fixture("synthetic_candidate.json")
    def test_public_reproduction_holds(self):
        p=_compile_at(self.ref,self.c,NOW);self.assertEqual(p["status"],"HOLD");self.assertTrue(all(v is False for v in p["authority"].values()))
    def test_prime_candidate(self):
        r=buyer(self.ref);self.assertEqual(_compile_at(r,all_evidence(r,self.c),NOW)["status"],"PRIME_CANDIDATE")
    def test_team_candidate(self):
        r=buyer(self.ref);ids={q["id"] for q in r["requirements"] if q["mandatory"] and q["partner_curable"]}
        self.assertEqual(_compile_at(r,all_evidence(r,self.c,ids),NOW)["status"],"TEAMING_CANDIDATE")
    def test_missing_partner_not_ready(self):
        r=buyer(self.ref);c=all_evidence(r,self.c);c["evidence"]=[e for e in c["evidence"] if e["requirement_id"]!="QUAL-REFERENCES-3"]
        self.assertEqual(_compile_at(r,c,NOW)["status"],"HOLD_TEAMING_EVIDENCE_REQUIRED")
    def test_deadline_passed(self):
        r=buyer(self.ref);c=all_evidence(r,self.c);self.assertEqual(_compile_at(r,c,NOW+timedelta(days=2))["status"],"HOLD_DEADLINE_PASSED")
    def test_deadline_time_unknown(self):
        r=buyer(self.ref);c=all_evidence(r,self.c);self.assertEqual(_compile_at(r,c,NOW+timedelta(days=1))["status"],"HOLD_DEADLINE_TIME_UNKNOWN")
    def test_packet_tamper(self):
        r=buyer(self.ref);c=all_evidence(r,self.c);p=_compile_at(r,c,NOW);bad=copy.deepcopy(p);bad["status"]="HOLD"
        with self.assertRaisesRegex(CarrierError,"does not recompute"):_verify_at(bad,r,c,NOW)
    def test_candidate_drift(self):
        r=buyer(self.ref);c=all_evidence(r,self.c);p=_compile_at(r,c,NOW);changed=copy.deepcopy(c);changed["vendor_name"]="Different Vendor"
        with self.assertRaisesRegex(CarrierError,"does not recompute"):_verify_at(p,r,changed,NOW)
    def test_rows_deterministic(self):
        r=buyer(self.ref);c=all_evidence(r,self.c);a=_compile_at(r,c,NOW);d=copy.deepcopy(c);d["evidence"].reverse();b=_compile_at(r,d,NOW)
        self.assertEqual(a["requirements"],b["requirements"]);self.assertNotEqual(a["candidate"]["candidate_digest"],b["candidate"]["candidate_digest"])
    def test_render_unpriced(self):
        text=render_markdown(_compile_at(self.ref,self.c,NOW));self.assertIn("PROPOSED_NOT_ACCEPTED",text);self.assertIn("UNPRICED",text)
    def test_publish_exclusive(self):
        p=_compile_at(self.ref,self.c,NOW)
        with tempfile.TemporaryDirectory() as td:
            publish(p,td)
            with self.assertRaisesRegex(CarrierError,"overwrite"):publish(p,td)
    def test_future_packet(self):
        r=buyer(self.ref);c=all_evidence(r,self.c);future=NOW+timedelta(hours=1);p=_compile_at(r,c,future)
        with self.assertRaisesRegex(CarrierError,"future packet"):_verify_at(p,r,c,NOW)
    def test_stale_packet(self):
        r=buyer(self.ref);r["opportunity"]["observed_at"]="2026-09-16T20:00:00Z";c=all_evidence(r,self.c)
        for e in c["evidence"]:e["observed_at"]="2026-09-16T20:30:00Z"
        old=NOW-timedelta(hours=7);p=_compile_at(r,c,old)
        with self.assertRaisesRegex(CarrierError,"stale packet"):_verify_at(p,r,c,NOW)

if __name__=="__main__":unittest.main()
