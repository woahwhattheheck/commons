from .test_support import *  # noqa: F401,F403

class RenderingTests(unittest.TestCase):
    def test_acceptance_matrix_verifies(self):
        matrix = acceptance.compile_matrix()
        self.assertTrue(acceptance.verify_matrix(matrix))
        self.assertEqual([row["phase"] for row in matrix["phases"]], list(acceptance.PHASES))

    def test_acceptance_matrix_tamper_fails(self):
        matrix = acceptance.compile_matrix()
        matrix["phases"][0]["required_evidence"].append("forged")
        self.assertFalse(acceptance.verify_matrix(matrix))

    def test_concept_has_exact_six_sections_and_no_invented_price(self):
        report = compile_at(mode="HISTORICAL_INTEGRITY_ONLY")
        rendered = concept.render_concept(candidate(), report)
        for heading in concept.SECTION_ORDER:
            self.assertEqual(rendered.count(f"## {heading}"), 1)
        self.assertIn("OWNER_APPROVED", rendered)
        self.assertNotIn("$", rendered)
        self.assertIn("NOT AUTHORIZED", rendered)

    def test_concept_subject_mismatch_rejected(self):
        report = compile_at(mode="HISTORICAL_INTEGRITY_ONLY")
        other = candidate()
        other["subject_id"] = "other"
        with self.assertRaises(strict.ValidationError):
            concept.render_concept(other, report)

