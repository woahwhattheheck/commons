#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
PACKAGE = ROOT / "opportunities" / "snoco-ai-gov-26-0791bc"
SPEC = importlib.util.spec_from_file_location("snoco_validate", PACKAGE / "validate_matrix.py")
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)
GOLDEN = json.loads((PACKAGE / "capability_matrix.json").read_text(encoding="utf-8"))


def row(value, rid):
    return next(x for x in value["rows"] if x["id"] == rid)


class EvidenceMapTests(unittest.TestCase):
    def test_golden_matrix_passes(self):
        self.assertEqual(validator.validate(copy.deepcopy(GOLDEN)), [])

    def test_prime_boundary_cannot_be_enabled(self):
        value = copy.deepcopy(GOLDEN)
        value["boundary"]["tjlabs_is_prime"] = True
        self.assertIn("boundary_must_be_false:tjlabs_is_prime", validator.validate(value))

    def test_microsoft_boundary_cannot_be_upgraded(self):
        value = copy.deepcopy(GOLDEN)
        row(value, "m365-gcc-purview-implementation")["classification"] = "SUPPORTED_WEDGE"
        errors = validator.validate(value)
        self.assertIn("classification_boundary_violated:m365-gcc-purview-implementation", errors)

    def test_supported_wedge_requires_pinned_repository_evidence(self):
        value = copy.deepcopy(GOLDEN)
        row(value, "runtime-tool-evidence-receipts")["repository_evidence"] = []
        self.assertIn(
            "supported_wedge_without_repository_evidence:runtime-tool-evidence-receipts",
            validator.validate(value),
        )

    def test_repository_blob_cannot_be_rewritten_in_matrix(self):
        value = copy.deepcopy(GOLDEN)
        value["repository_evidence_catalog"][0]["blob"] = "0" * 40
        self.assertIn(
            "repository_evidence_pin_mismatch:mcp-conformance-receipts",
            validator.validate(value),
        )

    def test_unpinned_repository_evidence_is_rejected(self):
        value = copy.deepcopy(GOLDEN)
        value["repository_evidence_catalog"].append({
            "id": "marketing-claim",
            "path": "README.md",
            "blob": "a" * 40,
            "capabilities": ["anything"],
            "limitations": ["none"],
        })
        self.assertIn("repository_evidence_id_unpinned:marketing-claim", validator.validate(value))

    def test_unretrieved_packet_cannot_be_used_as_requirement_authority(self):
        value = copy.deepcopy(GOLDEN)
        row(value, "runtime-tool-evidence-receipts")["requirement_authority"] = "county_procurement_portal"
        self.assertIn(
            "unretrieved_packet_used_as_authority:runtime-tool-evidence-receipts",
            validator.validate(value),
        )

    def test_packet_required_row_must_stay_packet_bound(self):
        value = copy.deepcopy(GOLDEN)
        row(value, "contract-term-scoring-certifications")["requirement_authority"] = "secondary_scope_signal"
        self.assertIn(
            "packet_required_row_must_use_packet_authority:contract-term-scoring-certifications",
            validator.validate(value),
        )

    def test_duplicate_row_id_is_rejected(self):
        value = copy.deepcopy(GOLDEN)
        value["rows"].append(copy.deepcopy(value["rows"][0]))
        self.assertIn("duplicate_row_id:runtime-tool-evidence-receipts", validator.validate(value))

    def test_unknown_classification_is_rejected(self):
        value = copy.deepcopy(GOLDEN)
        row(value, "runtime-tool-evidence-receipts")["classification"] = "PROVEN_PRIME"
        self.assertIn("classification_invalid:runtime-tool-evidence-receipts", validator.validate(value))

    def test_supported_wedge_requires_explicit_nonclaim_boundary(self):
        value = copy.deepcopy(GOLDEN)
        row(value, "design-vs-live-change-receipts")["does_not_establish"] = []
        self.assertIn(
            "supported_wedge_without_nonclaim_boundary:design-vs-live-change-receipts",
            validator.validate(value),
        )

    def test_non_supported_row_cannot_borrow_positive_evidence(self):
        value = copy.deepcopy(GOLDEN)
        row(value, "shadow-ai-enterprise-discovery")["repository_evidence"] = ["mcp-conformance-receipts"]
        self.assertIn(
            "non_supported_row_must_not_use_positive_repo_evidence:shadow-ai-enterprise-discovery",
            validator.validate(value),
        )

    def test_portal_source_cannot_claim_packet_was_retrieved(self):
        value = copy.deepcopy(GOLDEN)
        portal = next(x for x in value["sources"] if x["id"] == "county-procurement-portal")
        portal["packet_retrieved"] = True
        self.assertIn("portal_packet_must_remain_unretrieved", validator.validate(value))

    def test_recommendation_cannot_silently_upgrade_to_prime(self):
        value = copy.deepcopy(GOLDEN)
        value["solicitation"]["recommendation"] = "PRIME_AND_SUBMIT"
        self.assertIn(
            "recommendation_must_remain_teaming_wedge_pending_packet",
            validator.validate(value),
        )

    def test_verification_receipt_is_deterministic(self):
        raw = (PACKAGE / "capability_matrix.json").read_bytes()
        first = validator.verification_receipt(raw)
        second = validator.verification_receipt(raw)
        self.assertEqual(first, second)
        self.assertTrue(first["ok"])
        self.assertEqual(first["recommendation"], validator.RECOMMENDATION)
        self.assertFalse(first["packet_retrieved"])
        self.assertEqual(first["classification_counts"]["SUPPORTED_WEDGE"], 3)

    def test_invalid_json_fails_closed(self):
        receipt = validator.verification_receipt(b"{not-json")
        self.assertFalse(receipt["ok"])
        self.assertIsNone(receipt["semantic_sha256"])
        self.assertTrue(receipt["errors"][0].startswith("invalid_json:"))


if __name__ == "__main__":
    unittest.main()
