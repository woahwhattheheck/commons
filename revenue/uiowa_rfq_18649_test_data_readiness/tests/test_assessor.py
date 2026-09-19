import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "test_data_assessor.py"
FIXTURE_PATH = ROOT / "fixtures" / "catalog.synthetic.json"

spec = importlib.util.spec_from_file_location("test_data_assessor", MODULE_PATH)
assessor = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(assessor)


class TestDataReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.report = assessor.evaluate_catalog(cls.payload)
        cls.by_id = {d["dataset_id"]: d for d in cls.report["datasets"]}

    def test_catalog_has_three_service_examples(self):
        self.assertEqual(self.report["dataset_count"], 3)
        self.assertEqual({d["service"] for d in self.report["datasets"]}, {"ESS", "RIS", "IAM"})

    def test_clean_ess_fixture_is_fully_evidenced(self):
        ess = self.by_id["ESS-REGISTRATION-BOUNDARIES"]
        self.assertEqual(ess["summary"][assessor.OBSERVED_GAP], 0)
        self.assertEqual(ess["summary"][assessor.UNKNOWN], 0)
        self.assertEqual(ess["summary"][assessor.EVIDENCED], 7)

    def test_ris_exposes_staleness_interface_drift_and_missing_cases(self):
        ris = self.by_id["RIS-AWARD-SYNC"]
        states = {c["check_id"]: c["state"] for c in ris["checks"]}
        self.assertEqual(states["refresh_freshness"], assessor.OBSERVED_GAP)
        self.assertEqual(states["interface_alignment"], assessor.OBSERVED_GAP)
        self.assertEqual(states["representativeness"], assessor.OBSERVED_GAP)
        self.assertEqual(ris["summary"][assessor.OBSERVED_GAP], 3)

    def test_iam_missing_evidence_stays_unknown(self):
        iam = self.by_id["IAM-ROLE-TRANSITION"]
        states = {c["check_id"]: c["state"] for c in iam["checks"]}
        self.assertEqual(states["ownership"], assessor.UNKNOWN)
        self.assertEqual(states["refresh_freshness"], assessor.UNKNOWN)
        self.assertEqual(states["cleanup"], assessor.UNKNOWN)
        self.assertEqual(states["retention"], assessor.UNKNOWN)
        self.assertEqual(states["representativeness"], assessor.OBSERVED_GAP)
        self.assertNotEqual(states["ownership"], assessor.OBSERVED_GAP)

    def test_interface_alignment_can_be_evidenced_despite_other_unknowns(self):
        iam = self.by_id["IAM-ROLE-TRANSITION"]
        states = {c["check_id"]: c["state"] for c in iam["checks"]}
        self.assertEqual(states["interface_alignment"], assessor.EVIDENCED)
        self.assertEqual(states["data_origin"], assessor.EVIDENCED)

    def test_invalid_as_of_fails_closed(self):
        with self.assertRaises(ValueError):
            assessor.evaluate_catalog({"as_of": "not-a-date", "datasets": []})

    def test_markdown_explains_unknown_boundary(self):
        text = assessor.render_markdown(self.report)
        self.assertIn("UNKNOWN means evidence is missing or insufficient", text)
        self.assertIn("IAM-ROLE-TRANSITION", text)
        self.assertIn("RIS-AWARD-SYNC", text)


if __name__ == "__main__":
    unittest.main()
