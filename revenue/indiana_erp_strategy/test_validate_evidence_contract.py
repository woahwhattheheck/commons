#!/usr/bin/env python3
"""Hermetic regressions for the Indiana ERP evidence contract."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

try:
    from . import validate_evidence_contract as validator
except ImportError:
    import validate_evidence_contract as validator


class EvidenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads(
            (Path(__file__).resolve().parent / "evidence_contract.json").read_text(encoding="utf-8")
        )

    def test_canonical_contract_is_valid(self):
        validator.validate_contract(copy.deepcopy(self.base))

    def test_direct_state_submission_cannot_be_enabled(self):
        candidate = copy.deepcopy(self.base)
        candidate["direct_state_submission_authorized"] = True
        with self.assertRaisesRegex(validator.ContractError, "direct State submission"):
            validator.validate_contract(candidate)

    def test_prime_decision_authority_cannot_be_removed(self):
        candidate = copy.deepcopy(self.base)
        candidate["customer_prime_decision_authority_retained"] = False
        with self.assertRaisesRegex(validator.ContractError, "decision authority"):
            validator.validate_contract(candidate)

    def test_product_selection_cannot_enter_bounded_scope(self):
        candidate = copy.deepcopy(self.base)
        candidate["erp_product_selection_in_scope"] = True
        with self.assertRaisesRegex(validator.ContractError, "product selection"):
            validator.validate_contract(candidate)

    def test_unverified_past_performance_cannot_be_promoted(self):
        candidate = copy.deepcopy(self.base)
        candidate["qualification_evidence"]["public_sector_erp_past_performance_verified"] = True
        with self.assertRaisesRegex(validator.ContractError, "past_performance"):
            validator.validate_contract(candidate)

    def test_unknowns_cannot_become_observations(self):
        candidate = copy.deepcopy(self.base)
        candidate["evidence_rules"]["unknowns_may_be_promoted_to_observations"] = True
        with self.assertRaisesRegex(validator.ContractError, "unknowns_may_be_promoted"):
            validator.validate_contract(candidate)

    def test_cost_basis_rule_cannot_be_removed(self):
        candidate = copy.deepcopy(self.base)
        candidate["evidence_rules"]["cost_ranges_require_basis_currency_exclusions"] = False
        with self.assertRaisesRegex(validator.ContractError, "cost_ranges_require"):
            validator.validate_contract(candidate)

    def test_recommendation_traceability_rule_cannot_be_removed(self):
        candidate = copy.deepcopy(self.base)
        candidate["evidence_rules"]["recommendations_require_evidence_and_assumption_refs"] = False
        with self.assertRaisesRegex(validator.ContractError, "recommendations_require"):
            validator.validate_contract(candidate)

    def test_required_record_field_cannot_be_removed(self):
        candidate = copy.deepcopy(self.base)
        recommendation = next(r for r in candidate["required_record_types"] if r["type"] == "recommendation")
        recommendation["required_fields"].remove("decision_owner")
        with self.assertRaisesRegex(validator.ContractError, "recommendation is missing mandatory fields"):
            validator.validate_contract(candidate)

    def test_mandatory_forbidden_claim_cannot_be_removed(self):
        candidate = copy.deepcopy(self.base)
        candidate["forbidden_claims"].remove("indiana_endorsement_or_engagement")
        with self.assertRaisesRegex(validator.ContractError, "mandatory forbidden claim"):
            validator.validate_contract(candidate)


if __name__ == "__main__":
    unittest.main()
