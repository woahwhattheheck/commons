from .test_support import *  # noqa: F401,F403

class RepositoryArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = pathlib.Path(__file__).resolve().parent

    def test_checked_in_historical_report_verifies(self):
        valid = gate.verify_historical(
            (self.root / "candidate.example.json").read_bytes(),
            (self.root / "source_ledger.json").read_bytes(),
            (self.root / "authority.example.json").read_bytes(),
            (self.root / "authority-floor.example.json").read_bytes(),
            (self.root / "historical_report.example.json").read_bytes(),
            as_of="2026-09-14T04:45:00Z",
        )
        self.assertTrue(valid)

    def test_checked_in_concept_is_generated_exactly(self):
        candidate_value = strict.strict_json_loads((self.root / "candidate.example.json").read_bytes())
        report_value = strict.strict_json_loads((self.root / "historical_report.example.json").read_bytes())
        self.assertEqual(
            (self.root / "concept_paper.internal.md").read_text(),
            concept.render_concept(candidate_value, report_value),
        )

    def test_checked_in_acceptance_outputs_are_generated_exactly(self):
        matrix = acceptance.compile_matrix()
        self.assertEqual(
            strict.strict_json_loads((self.root / "acceptance_matrix.json").read_bytes()),
            matrix,
        )
        self.assertEqual(
            (self.root / "ACCEPTANCE.md").read_text(),
            acceptance.render_matrix_markdown(matrix),
        )

    def test_requirements_catalog_is_unique_and_non_authorizing(self):
        catalog = strict.strict_json_loads((self.root / "requirements.json").read_bytes())
        self.assertEqual(catalog["schema"], "dcsa-innovation-call-01/requirements/v1")
        self.assertIs(catalog["external_action_authorized"], False)
        ids = [row["id"] for row in catalog["requirements"]]
        self.assertEqual(len(ids), 35)
        self.assertEqual(len(set(ids)), 35)
        self.assertEqual(ids, sorted(ids))

    def test_teaming_catalog_starts_empty_and_non_authorizing(self):
        matrix = strict.strict_json_loads((self.root / "teaming_targets.json").read_bytes())
        self.assertEqual(matrix["status"], "RESEARCH_REQUIRED")
        self.assertEqual(matrix["targets"], [])
        self.assertIs(matrix["external_send_authorized"], False)

    def test_checked_in_source_is_metadata_only(self):
        ledger = gate.normalize_source_ledger(
            strict.strict_json_loads((self.root / "source_ledger.json").read_bytes())
        )
        self.assertFalse(ledger["complete"])
        self.assertTrue(all(row["sha256"] is None for row in ledger["documents"]))

