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
        cls.data = json.loads((PACKET / "readiness.json").read_text(encoding="utf-8"))

    def test_all_three_mandatory_gates_fail_closed(self):
        gates = self.data["mandatory_responsiveness"]
        self.assertEqual(len(gates), 3)
        self.assertTrue(all(row["state"] == "NOT_EVIDENCED" for row in gates))
        self.assertTrue(all(row["effect"] == "NONRESPONSIVE_IF_PRIME" for row in gates))

    def test_no_prime_eligibility_claim(self):
        self.assertEqual(
            self.data["decision"],
            "NO_GO_AS_PRIME; CONDITIONAL_SUBCONTRACTOR_ONLY",
        )
        self.assertEqual(self.data["partner_screen"][0]["verified_gates"], 0)

    def test_two_required_references_are_empty(self):
        slots = self.data["reference_slots"]
        self.assertEqual(len(slots), 2)
        self.assertTrue(all(row["state"] == "EMPTY_FAIL_CLOSED" for row in slots))

    def test_summary_is_deterministic_and_non_operational(self):
        first = builder.summary(self.data)
        self.assertEqual(first, builder.summary(self.data))
        parsed = json.loads(first)
        self.assertFalse(parsed["external_action"])
        self.assertFalse(parsed["references_ready"])

    def test_deadlines_are_exact(self):
        schedule = self.data["schedule"]
        self.assertEqual(schedule["qa_addendum_expected_by"], "2026-09-04")
        self.assertEqual(schedule["soq_due"], "2026-09-25T17:00:00-07:00")

    def test_subcontract_scope_is_nonproduction(self):
        role = self.data["structure"]["tokenjunkielabs_sub"].lower()
        self.assertIn("non-production", role)
        self.assertIn("prime control", role)

    def test_truth_boundary_rejects_procurement_claims(self):
        boundary = self.data["truth_boundary"].lower()
        for term in ("not an soq", "bid", "submission", "award", "qualification"):
            self.assertIn(term, boundary)

    def test_no_external_partner_is_invented(self):
        candidate = self.data["partner_screen"][1]
        self.assertIn("not identified", candidate["candidate"])
        self.assertEqual(candidate["status"], "UNVERIFIED")

    def test_rate_sheet_is_tbd_only(self):
        with (PACKET / "rate-sheet-template.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertTrue(all(value == "TBD" for value in rows[0].values()))

    def test_public_artifacts_make_no_submission_or_award_claim(self):
        public = (
            (PACKET / "README.md").read_text(encoding="utf-8")
            + (PACKET / "readiness.html").read_text(encoding="utf-8")
        ).lower()
        self.assertNotIn("we submitted", public)
        self.assertNotIn("we were awarded", public)
        self.assertIn("no-go as prime", public)


if __name__ == "__main__":
    unittest.main()
