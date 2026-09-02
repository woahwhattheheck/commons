from __future__ import annotations

import csv
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "revenue" / "mwdoc_d365_soq"
SPEC = importlib.util.spec_from_file_location(
    "mwdoc_builder", ROOT / "scripts" / "build_mwdoc_d365_soq.py"
)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(builder)


class MWDOCReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = builder.load_source()
        cls.data = builder.build_packet(cls.source)
        cls.schema = json.loads(
            (PACKET / "readiness.schema.json").read_text(encoding="utf-8")
        )

    def test_generated_readiness_matches_the_source_projection(self):
        generated = json.loads((PACKET / "readiness.json").read_text(encoding="utf-8"))
        self.assertEqual(generated, self.data)
        self.assertEqual(builder.load(), self.data)

    def test_schema_contract_matches_the_generated_packet(self):
        self.assertEqual(
            self.data["schema"], self.schema["properties"]["schema"]["const"]
        )
        self.assertEqual(self.data["id"], self.schema["properties"]["id"]["const"])
        self.assertEqual(
            self.data["decision"], self.schema["properties"]["decision"]["const"]
        )
        self.assertEqual(
            self.data["source_path"],
            self.schema["properties"]["source_path"]["const"],
        )
        self.assertTrue(set(self.schema["required"]).issubset(self.data))
        self.assertFalse(set(self.data) - set(self.schema["properties"]))
        self.assertEqual(builder.schema_errors(self.data, self.schema), [])
        invalid = dict(self.data)
        invalid["schema"] = "wrong-version"
        self.assertTrue(builder.schema_errors(invalid, self.schema))

        target_schema = self.schema["properties"]["targets"]["items"]
        target_required = set(target_schema["required"])
        for target in self.data["targets"]:
            self.assertTrue(target_required.issubset(target))
            self.assertFalse(set(target) - set(target_schema["properties"]))

    def test_scores_and_mandatory_evidence_are_deterministic(self):
        scores = {
            row["company"]: row["computed_score"] for row in self.data["targets"]
        }
        self.assertEqual(
            scores,
            {
                "HSO": 50,
                "RSM US LLP": 45,
                "Hitachi Solutions America": 40,
                "Consultadd Public Services": 27.5,
            },
        )
        self.assertTrue(
            all(
                len(row["mandatory_gates"]) == 5
                and row["missing_mandatory_gates"]
                and row["status"] == "PROVISIONAL_RESEARCH_ONLY"
                for row in self.data["targets"]
            )
        )

    def test_summary_is_deterministic_and_non_operational(self):
        first = builder.summary(self.data)
        self.assertEqual(first, builder.summary(self.data))
        parsed = json.loads(first)
        self.assertFalse(parsed["external_action"])
        self.assertEqual(parsed["reference_slots_ready"], 0)
        self.assertEqual(parsed["targets"], 4)
        self.assertEqual(parsed["targets_with_complete_mandatory_evidence"], 0)

    def test_deadlines_are_exact(self):
        schedule = self.data["schedule"]
        self.assertEqual(schedule["soq_due"], "2026-09-25T17:00:00-07:00")
        self.assertEqual(schedule["required_content_start"], "2026-10-26")
        self.assertEqual(schedule["evaluation_start"], "2026-09-21")
        self.assertEqual(schedule["start_discrepancy_state"], "ADDENDUM_REQUIRED")

    def test_subcontract_scope_is_nonproduction(self):
        scope = self.data["proposed_subcontract_scope"]
        self.assertIn("NON_PRODUCTION", scope["label"])
        self.assertTrue(
            any("No production access" in item for item in scope["exclusions"])
        )

    def test_reference_slots_and_truth_flags_remain_incomplete(self):
        slots = self.data["reference_slots"]
        self.assertEqual(len(slots), 2)
        self.assertTrue(
            all(
                row["status"] == "OWNER_PRIVATE_EVIDENCE_REQUIRED"
                and row["public_contact_data"] is False
                for row in slots
            )
        )
        self.assertTrue(
            all(value is False for value in self.data["truth_flags"].values())
        )

    def test_rate_sheet_is_tbd_only(self):
        with (PACKET / "rate-sheet-template.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertTrue(all(value == "TBD" for value in rows[0].values()))

    def test_no_login_html_is_current_and_keeps_the_truth_boundary(self):
        self.assertEqual(
            (PACKET / "readiness.html").read_text(encoding="utf-8"),
            builder.render_html(self.data),
        )
        public = (
            (PACKET / "README.md").read_text(encoding="utf-8")
            + (PACKET / "readiness.html").read_text(encoding="utf-8")
        ).lower()
        self.assertNotIn("we submitted", public)
        self.assertNotIn("we were awarded", public)
        self.assertIn("no-go as prime", public)
        self.assertIn("provisional partner research", public)


if __name__ == "__main__":
    unittest.main()
