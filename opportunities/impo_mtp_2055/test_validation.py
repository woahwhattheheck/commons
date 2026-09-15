"""Schema validation tests."""

import copy
import unittest

from .schema import OpportunityInputError, validate_input
from .test_support import load_owner_fixture, ready_fixture

class ValidationTests(unittest.TestCase):
    def test_owner_fixture_validates(self) -> None:
        normalized = validate_input(load_owner_fixture())
        self.assertEqual(normalized["schema_version"], 1)

    def test_detaches_nested_input(self) -> None:
        value = ready_fixture()
        normalized = validate_input(value)
        value["team"]["staff"][0]["name"] = "MUTATED"
        self.assertEqual(normalized["team"]["staff"][0]["name"], "Morgan Model")

    def test_rejects_extra_root_key(self) -> None:
        value = load_owner_fixture()
        value["surprise"] = True
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_rejects_naive_timestamp(self) -> None:
        value = load_owner_fixture()
        value["as_of"] = "2026-09-14T00:00:00"
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_rejects_future_source_check(self) -> None:
        value = load_owner_fixture()
        value["source_checks"]["last_checked_at"] = "2026-09-14T00:00:01-04:00"
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_rejects_invalid_source_digest(self) -> None:
        value = load_owner_fixture()
        value["opportunity"]["source_sha256"] = "ABC"
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_verified_bytes_require_digest(self) -> None:
        value = load_owner_fixture()
        value["source_checks"]["base_rfp_bytes_verified"] = True
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_rejects_invalid_currency(self) -> None:
        value = load_owner_fixture()
        value["opportunity"]["currency"] = "usd"
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_rejects_invalid_uei(self) -> None:
        value = load_owner_fixture()
        value["organization"]["sam_uei"] = "short"
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_verified_evidence_requires_reference(self) -> None:
        value = load_owner_fixture()
        value["organization"]["title_vi_compliance"] = {
            "state": "VERIFIED",
            "reference": None,
            "note": None,
        }
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_not_applicable_evidence_cannot_claim_reference(self) -> None:
        value = load_owner_fixture()
        value["organization"]["title_vi_compliance"] = {
            "state": "NOT_APPLICABLE",
            "reference": "fake",
            "note": None,
        }
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_rejects_duplicate_staff_names(self) -> None:
        value = ready_fixture()
        value["team"]["staff"][1]["name"] = value["team"]["staff"][0]["name"]
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_rejects_duplicate_partner_names(self) -> None:
        value = ready_fixture()
        value["team"]["partners"].append(copy.deepcopy(value["team"]["partners"][0]))
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_rejects_duplicate_project_names(self) -> None:
        value = ready_fixture()
        value["projects"][1]["name"] = value["projects"][0]["name"]
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_rejects_duplicate_pricing_task_ids(self) -> None:
        value = ready_fixture()
        value["pricing"]["tasks"][1]["id"] = value["pricing"]["tasks"][0]["id"]
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_rejects_negative_pricing(self) -> None:
        value = ready_fixture()
        value["pricing"]["tasks"][0]["hours"] = -1
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_rejects_stated_total_mismatch(self) -> None:
        value = ready_fixture()
        value["pricing"]["stated_total_minor"] += 1
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_true_authority_requires_provenance(self) -> None:
        value = load_owner_fixture()
        value["authority"]["submit_proposal"] = True
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_false_authority_rejects_stray_approval_metadata(self) -> None:
        value = load_owner_fixture()
        value["authority"]["approved_by"] = "Someone"
        value["authority"]["approval_reference"] = "ref"
        with self.assertRaises(OpportunityInputError):
            validate_input(value)

    def test_bool_not_accepted_as_integer(self) -> None:
        value = ready_fixture()
        value["team"]["staff"][0]["years_relevant"] = True
        with self.assertRaises(OpportunityInputError):
            validate_input(value)


