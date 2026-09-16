from __future__ import annotations
import copy, json, unittest
from revenue.numih_ai_sad_admission_readiness.compiler import ValidationError, compile_packet, loads_strict, render_markdown, verify_result

def packet():
    from pathlib import Path
    return json.loads((Path(__file__).parents[1]/"examples"/"fictional_partner_packet.json").read_text())

class T(unittest.TestCase):
    def test_complete_partner_packet(self):
        p=packet(); r=compile_packet(p)
        self.assertEqual(r["packet_state"],"PACKET_REVIEW_READY")
        self.assertEqual(r["rubric"]["evidence_coverage_points"],100)
        self.assertEqual(r["dce"]["currentness"],"CURRENTNESS_UNVERIFIED")
        self.assertEqual(r["external_submission_state"],"HOLD_CURRENTNESS_AND_OWNER_ACTIONS")
        self.assertTrue(all(v is False for v in r["authority"].values()))
        self.assertTrue(verify_result(p,r))
    def test_missing_commitment_blocks_partner_capacity(self):
        p=packet(); p["partners"][0]["commitment_evidence_id"]=None
        r=compile_packet(p); self.assertEqual(r["packet_state"],"INCOMPLETE_EVIDENCE")
        dim=next(x for x in r["rubric"]["dimensions"] if x["dimension"]=="recent_ai_references")
        self.assertEqual(dim["rows"][0]["coverage"],"PARTNER_COMMITMENT_MISSING")
    def test_cross_party_commitment_rejected(self):
        p=packet(); p["partners"].append({"id":"other","display_name":"Other","commitment_evidence_id":"e6"})
        with self.assertRaisesRegex(ValidationError,"cross-party"): compile_packet(p)
    def test_applicant_only_transplant_rejected(self):
        p=packet(); p["evidence"][0]["party_id"]="partner"
        with self.assertRaisesRegex(ValidationError,"must belong to applicant"): compile_packet(p)
    def test_category_gap_holds(self):
        p=packet(); p["evidence"]=[e for e in p["evidence"] if e["kind"]!="category_fit_4"]
        r=compile_packet(p)
        self.assertEqual(next(x for x in r["categories"] if x["category"]==4)["state"],"HOLD")
    def test_original_fr_language_mismatch_rejected(self):
        p=packet(); p["evidence"][6]["language"]="en"
        with self.assertRaisesRegex(ValidationError,"ORIGINAL_FR requires language=fr"): compile_packet(p)
    def test_translation_queue(self):
        p=packet(); p["evidence"][6]["language"]="en"; p["evidence"][6]["translation_status"]="WORKING_TRANSLATION"
        r=compile_packet(p); self.assertEqual(r["translation_queue"][0]["evidence_id"],"e7")
        self.assertEqual(r["packet_state"],"INCOMPLETE_EVIDENCE")
    def test_claimed_unverified_does_not_count(self):
        p=packet(); e=p["evidence"][11]; e["status"]="CLAIMED_UNVERIFIED"; e.pop("source")
        r=compile_packet(p); self.assertLess(r["rubric"]["evidence_coverage_points"],100)
    def test_currentness_self_assertion_rejected(self):
        p=packet(); p["dce"]["current"]=True
        with self.assertRaisesRegex(ValidationError,"unknown fields"): compile_packet(p)
    def test_bool_int_alias_rejected(self):
        p=packet(); p["categories"]=[True]
        with self.assertRaisesRegex(ValidationError,"integer"): compile_packet(p)
    def test_duplicate_json_key(self):
        with self.assertRaisesRegex(ValidationError,"duplicate JSON key"): loads_strict('{"x":1,"x":2}')
    def test_nonfinite_json(self):
        with self.assertRaisesRegex(ValidationError,"non-finite"): loads_strict('{"x":NaN}')
    def test_duplicate_evidence(self):
        p=packet(); p["evidence"][1]["id"]=p["evidence"][0]["id"]
        with self.assertRaisesRegex(ValidationError,"duplicate evidence id"): compile_packet(p)
    def test_unknown_category(self):
        p=packet(); p["categories"]=[5]
        with self.assertRaisesRegex(ValidationError,"1..4"): compile_packet(p)
    def test_semantic_order_invariance(self):
        p1=packet(); p2=copy.deepcopy(p1); p2["evidence"].reverse(); p2["categories"].reverse()
        a=compile_packet(p1); b=compile_packet(p2); a.pop("receipt"); b.pop("receipt"); self.assertEqual(a,b)
    def test_tamper_detected(self):
        p=packet(); r=compile_packet(p); r["authority"]["payment"]=True
        self.assertFalse(verify_result(p,r))
    def test_markdown_truth_labels(self):
        md=render_markdown(compile_packet(packet()))
        self.assertIn("not a sponsor score",md); self.assertIn("authority fields are `false`",md)

if __name__=="__main__": unittest.main()
