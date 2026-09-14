from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from revenue.wri_open_timber_portal.engine import ContractError, compile_proposal, load_json_strict, render_markdown, verify_report

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "public_known.json"
NOW = datetime(2026, 9, 14, 1, 30, 0, tzinfo=timezone.utc)


def fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class EngineTests(unittest.TestCase):
    def test_public_fixture_is_technically_ready_but_not_submission_ready(self):
        report = compile_proposal(fixture(), as_of=NOW)
        self.assertEqual(report["technical_readiness"], "TECHNICALLY_READY")
        self.assertEqual(report["submission_readiness"], "HOLD_CONTROLLING_SOURCE")
        self.assertEqual(set(report["blocking_unknowns"]), {"submission_route", "deadline_time_and_timezone", "mandatory_qualifications", "required_forms_and_representations", "evaluation_method", "pricing_instructions", "role_title"})
        self.assertEqual(set(report["company_evidence_gaps"]), {"ruby_rails_delivery", "legal_vendor_eligibility", "relevant_past_performance", "named_staffing"})

    def test_authority_ceiling_is_all_false(self):
        authority = compile_proposal(fixture(), as_of=NOW)["authority"]
        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))

    def test_markdown_preserves_hold_and_no_submission_authority(self):
        report = compile_proposal(fixture(), as_of=NOW)
        md = render_markdown(report)
        self.assertIn("HOLD_CONTROLLING_SOURCE", md)
        self.assertIn("Commercial posture", md)
        self.assertIn("does not authorize contact or submission", md)
        self.assertIn("Ruby on Rails", md)

    def test_unretrieved_official_source_cannot_launder_claims(self):
        p = fixture()
        p["sources"][0]["claims"] = ["submission_email_known"]
        with self.assertRaises(ContractError):
            compile_proposal(p, as_of=NOW)

    def test_required_unknown_category_cannot_be_hidden(self):
        p = fixture()
        p["controlling_unknowns"] = [row for row in p["controlling_unknowns"] if row["category"] != "pricing_instructions"]
        with self.assertRaises(ContractError):
            compile_proposal(p, as_of=NOW)

    def test_required_unknown_cannot_be_marked_nonblocking(self):
        p = fixture()
        p["controlling_unknowns"][0]["blocking"] = False
        with self.assertRaises(ContractError):
            compile_proposal(p, as_of=NOW)

    def test_self_asserted_resolution_is_rejected(self):
        p = fixture()
        p["controlling_unknowns"][0]["resolution_evidence"] = "I think the email is procurement@example.com."
        with self.assertRaises(ContractError):
            compile_proposal(p, as_of=NOW)

    def test_buyer_repo_must_back_technical_baseline(self):
        p = fixture()
        p["technical_baseline"]["repo_source_id"] = "secondary_rfp_activity_mirror"
        with self.assertRaises(ContractError):
            compile_proposal(p, as_of=NOW)

    def test_repo_url_transplant_is_rejected(self):
        p = fixture()
        p["technical_baseline"]["repo_url"] = "https://github.com/example/other"
        with self.assertRaises(ContractError):
            compile_proposal(p, as_of=NOW)

    def test_non_rails_target_is_rejected(self):
        p = fixture()
        p["technical_baseline"]["application"] = "Angular frontend"
        with self.assertRaises(ContractError):
            compile_proposal(p, as_of=NOW)

    def test_all_published_work_buckets_are_required(self):
        p = fixture()
        p["workstreams"] = p["workstreams"][:-1]
        with self.assertRaises(ContractError):
            compile_proposal(p, as_of=NOW)

    def test_duplicate_source_url_is_rejected(self):
        p = fixture()
        p["sources"][3]["url"] = p["sources"][2]["url"]
        with self.assertRaises(ContractError):
            compile_proposal(p, as_of=NOW)

    def test_stale_buyer_repo_fails_closed(self):
        later = datetime(2026, 9, 19, 0, 0, 0, tzinfo=timezone.utc)
        with self.assertRaises(ContractError):
            compile_proposal(fixture(), as_of=later)

    def test_naive_evaluation_time_is_rejected(self):
        with self.assertRaises(ContractError):
            compile_proposal(fixture(), as_of=datetime(2026, 9, 14, 1, 30, 0))

    def test_bool_int_alias_is_rejected(self):
        p = fixture()
        p["controlling_unknowns"][0]["blocking"] = 1
        with self.assertRaises(ContractError):
            compile_proposal(p, as_of=NOW)

    def test_owner_decision_pricing_cannot_smuggle_amount(self):
        p = fixture()
        p["commercial"]["amount_minor"] = 500000
        with self.assertRaises(ContractError):
            compile_proposal(p, as_of=NOW)

    def test_proposed_pricing_requires_amount_but_does_not_clear_procurement_hold(self):
        p = fixture()
        p["commercial"]["pricing_status"] = "PROPOSED_NOT_SUBMITTED"
        p["commercial"]["amount_minor"] = 500000
        report = compile_proposal(p, as_of=NOW)
        self.assertEqual(report["commercial"]["amount_minor"], 500000)
        self.assertEqual(report["submission_readiness"], "HOLD_CONTROLLING_SOURCE")
        self.assertFalse(report["authority"]["submission_authorized"])

    def test_even_verified_company_evidence_does_not_clear_controlling_unknowns(self):
        p = fixture()
        for key in p["company_evidence"]:
            p["company_evidence"][key] = "VERIFIED"
        report = compile_proposal(p, as_of=NOW)
        self.assertEqual(report["company_evidence_gaps"], [])
        self.assertEqual(report["submission_readiness"], "HOLD_CONTROLLING_SOURCE")

    def test_reordering_sources_and_workstreams_is_deterministic(self):
        p = fixture()
        a = compile_proposal(p, as_of=NOW)
        p["sources"] = list(reversed(p["sources"]))
        p["workstreams"] = list(reversed(p["workstreams"]))
        b = compile_proposal(p, as_of=NOW)
        self.assertEqual(a, b)

    def test_tampered_report_fails_verification(self):
        p = fixture()
        report = compile_proposal(p, as_of=NOW)
        altered = deepcopy(report)
        altered["commercial"]["pricing_basis"] = "tampered"
        verification = verify_report(p, altered, current_as_of=NOW)
        self.assertEqual(verification["verdict"], "STALE_OR_DRIFTED")
        self.assertFalse(verification["historical_receipt_valid"])

    def test_exact_report_verifies(self):
        p = fixture()
        report = compile_proposal(p, as_of=NOW)
        verification = verify_report(p, report, current_as_of=NOW)
        self.assertEqual(verification["verdict"], "CURRENT_TECHNICAL_CARRIER_VERIFIED")
        self.assertTrue(verification["historical_exact"])
        self.assertEqual(verification["current_submission_readiness"], "HOLD_CONTROLLING_SOURCE")

    def test_input_change_invalidates_historical_exact(self):
        p = fixture()
        report = compile_proposal(p, as_of=NOW)
        changed = fixture()
        changed["commercial"]["pricing_basis"] += " Owner note changed."
        verification = verify_report(changed, report, current_as_of=NOW)
        self.assertEqual(verification["verdict"], "STALE_OR_DRIFTED")
        self.assertFalse(verification["historical_exact"])

    def test_duplicate_json_keys_and_nonfinite_numbers_rejected(self):
        with self.assertRaises(ContractError):
            load_json_strict(b'{"a":1,"a":2}')
        with self.assertRaises(ContractError):
            load_json_strict(b'{"a":NaN}')


if __name__ == "__main__":
    unittest.main()
