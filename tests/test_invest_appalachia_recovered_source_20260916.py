import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "opportunities" / "invest_appalachia_framer_lms" / "recovered_20260916" / "SOURCE_MANIFEST.json"

class RecoveredSourceManifestTests(unittest.TestCase):
    def setUp(self):
        self.m = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_schema_and_no_mutation_of_15049(self):
        self.assertEqual(self.m["schema"], "invest_appalachia_framer_lms.recovered_source_manifest.v1")
        self.assertEqual(self.m["does_not_mutate"]["commons_pr"], 15049)
        self.assertEqual(self.m["does_not_mutate"]["exact_head"], "fc9d626dda146c5e25e0c6915c0484634cfa06f2")
        self.assertFalse(self.m["authority"]["submission_authorized"])
        self.assertIsNone(self.m["authority"]["platform_recommendation"])
        self.assertIsNone(self.m["authority"]["pricing_recommendation"])

    def test_faq_not_visible_yet_is_not_no_change(self):
        page = self.m["buyer_page"]
        self.assertEqual(page["faq_classification"], "FAQ_NOT_VISIBLE_YET")
        self.assertFalse(page["faq_body_or_link_visible"])
        self.assertTrue(page["faq_absence_is_not_no_change"])
        self.assertIn("RFP FAQ Posted to This Page", page["faq_schedule_line_exact"])
        self.assertEqual(page["visible_nte_usd"], 60000)

    def test_zip_and_attachments_recovered_with_full_sha256(self):
        z = self.m["first_party_files"]["zipped_rfp_docs"]
        self.assertEqual(z["classification"], "RECOVERED")
        self.assertEqual(z["bytes"], 2129973)
        self.assertEqual(len(z["sha256"]), 64)
        self.assertEqual(z["sha256"], "ddbaf6d67a19a718f88487647cd38861a013ff791bd17c2557150fa4da4f1bb9")
        pdf = self.m["first_party_files"]["rfp_pdf"]
        self.assertEqual(pdf["sha256"], "997a93be4b25c7476b03d0b72a360bf5f60de53800c7fd649b96415372576a19")
        self.assertTrue(self.m["zip_inner_rfp_pdf_matches_standalone"])
        for key in ("A_functional_requirements", "B_selection_rubric", "C_budget_template", "D_optional_response_template"):
            att = self.m["attachments"][key]
            self.assertEqual(att["classification"], "RECOVERED")
            self.assertEqual(len(att["sha256"]), 64)

    def test_attachment_c_blank_dollars_are_not_priced_evidence(self):
        c = self.m["attachments"]["C_budget_template"]
        self.assertEqual(c["budget_cap_usd"], 60000)
        self.assertTrue(c["zero_placeholders_are_not_priced_evidence"])
        self.assertIn("Vendor Implementation Services", c["line_items"])
        self.assertIn("none", c["formulas_visible_in_docx"])

    def test_attachment_a_priority_census(self):
        a = self.m["attachments"]["A_functional_requirements"]
        self.assertEqual(a["functional_rows"], 67)
        self.assertEqual(a["priority_counts"]["Required"], 54)
        self.assertEqual(a["priority_counts"]["Preferred"], 12)
        self.assertEqual(a["priority_counts"]["Required / Preferred"], 1)

    def test_attachment_b_100_point_rubric(self):
        b = self.m["attachments"]["B_selection_rubric"]
        self.assertEqual(b["maximum_total_score"], 100)
        self.assertEqual(sum(x["points"] for x in b["criteria"]), 100)

if __name__ == "__main__":
    unittest.main()
