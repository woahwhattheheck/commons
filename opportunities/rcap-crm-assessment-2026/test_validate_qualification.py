#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from datetime import date

import validate_qualification as gate


class QualificationTests(unittest.TestCase):
    def base(self):
        return {
            "schema": gate.SCHEMA,
            "opportunity": {
                "official_url": gate.OFFICIAL_URL,
                "release_date": "2026-09-04",
                "questions_due": "2026-09-13",
                "proposals_due": "2026-10-04",
                "revalidated_date": "2026-09-13",
            },
            "evaluation": dict(gate.EVALUATION_WEIGHTS),
            "organization": {
                "primary_place_of_business_country": "US",
                "professional_indemnity_coi": "WILL_OBTAIN_BEFORE_AWARD",
            },
            "qualification": {
                "desired_experience": {name: "UNKNOWN" for name in gate.DESIRED_QUALIFICATIONS},
                "comparable_examples_or_references": [],
            },
            "proposal": {
                "firm_overview_ready": True,
                "approach_ready": True,
                "deliverable_description_ready": True,
                "schedule_ready": True,
                "delivery_model_ready": True,
                "discovery_meetings_included": 8,
                "fixed_fee_usd": 25000,
                "optional_services_separated": True,
                "deadline_time_revalidated": True,
                "owner_submission_authorized": True,
            },
        }

    def test_desired_experience_is_warning_not_false_hard_gate(self):
        result = gate.evaluate(self.base(), today=date(2026, 9, 13))
        self.assertEqual(result["status"], "READY_TO_SUBMIT")
        self.assertTrue(any(x.startswith("desired_experience_is_not_pass_fail:") for x in result["warnings"]))

    def test_unknown_us_place_of_business_holds(self):
        facts = self.base()
        facts["organization"]["primary_place_of_business_country"] = None
        result = gate.evaluate(facts, today=date(2026, 9, 13))
        self.assertIn("us_primary_place_of_business_unverified", result["blockers"])
        self.assertEqual(result["status"], "HOLD")

    def test_non_us_place_of_business_holds(self):
        facts = self.base()
        facts["organization"]["primary_place_of_business_country"] = "CA"
        result = gate.evaluate(facts, today=date(2026, 9, 13))
        self.assertIn("us_primary_place_of_business_required", result["blockers"])

    def test_coi_can_be_planned_for_award_but_not_unknown(self):
        facts = self.base()
        self.assertEqual(gate.evaluate(facts, today=date(2026, 9, 13))["status"], "READY_TO_SUBMIT")
        facts["organization"]["professional_indemnity_coi"] = "UNKNOWN"
        self.assertIn("professional_indemnity_coi_plan_unverified", gate.evaluate(facts, today=date(2026, 9, 13))["blockers"])

    def test_fixed_fee_must_be_explicit_positive_integer(self):
        for hostile in (None, True, 0, -1, 12.5, "25000"):
            facts = self.base()
            facts["proposal"]["fixed_fee_usd"] = hostile
            if hostile is None:
                self.assertIn("fixed_fee_unset", gate.evaluate(facts, today=date(2026, 9, 13))["blockers"])
            else:
                with self.assertRaises(gate.FactsError):
                    gate.evaluate(facts, today=date(2026, 9, 13))

    def test_owner_authorization_is_required_for_ready(self):
        facts = self.base()
        facts["proposal"]["owner_submission_authorized"] = False
        result = gate.evaluate(facts, today=date(2026, 9, 13))
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("owner_submission_authorization_missing", result["blockers"])

    def test_exact_deadline_time_must_be_revalidated_before_ready(self):
        facts = self.base()
        facts["proposal"]["deadline_time_revalidated"] = False
        result = gate.evaluate(facts, today=date(2026, 9, 13))
        self.assertIn("exact_submission_deadline_time_unverified", result["blockers"])

    def test_source_staleness_holds_even_before_deadline(self):
        facts = self.base()
        facts["opportunity"]["revalidated_date"] = "2026-09-09"
        result = gate.evaluate(facts, today=date(2026, 9, 13))
        self.assertIn("official_source_stale", result["blockers"])

    def test_after_deadline_holds(self):
        facts = self.base()
        facts["opportunity"]["revalidated_date"] = "2026-10-05"
        result = gate.evaluate(facts, today=date(2026, 10, 5))
        self.assertIn("proposal_deadline_passed", result["blockers"])

    def test_evaluation_weights_are_source_bound(self):
        facts = self.base()
        facts["evaluation"]["cost_value"] = 20
        with self.assertRaises(gate.FactsError):
            gate.evaluate(facts, today=date(2026, 9, 13))

    def test_bool_cannot_spoof_positive_integer(self):
        facts = self.base()
        facts["proposal"]["discovery_meetings_included"] = True
        with self.assertRaises(gate.FactsError):
            gate.evaluate(facts, today=date(2026, 9, 13))

    def test_reference_shape_is_validated(self):
        facts = self.base()
        facts["qualification"]["comparable_examples_or_references"] = [{"description": "Enterprise-system assessment"}]
        result = gate.evaluate(facts, today=date(2026, 9, 13))
        self.assertEqual(result["status"], "READY_TO_SUBMIT")
        facts["qualification"]["comparable_examples_or_references"] = [{}]
        with self.assertRaises(gate.FactsError):
            gate.evaluate(facts, today=date(2026, 9, 13))

    def test_duplicate_json_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facts.json"
            path.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            with self.assertRaises(gate.FactsError):
                gate.load_json(path)

    def test_checked_in_scaffold_remains_hold(self):
        facts = gate.load_json(Path(__file__).with_name("qualification.json"))
        result = gate.evaluate(facts, today=date(2026, 9, 13))
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("us_primary_place_of_business_unverified", result["blockers"])
        self.assertIn("fixed_fee_unset", result["blockers"])
        self.assertIn("owner_submission_authorization_missing", result["blockers"])


if __name__ == "__main__":
    unittest.main()
