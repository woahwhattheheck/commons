#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "revenue" / "inprs_clm_migration_gate"
MODULE_PATH = PACKAGE / "verify_bundle.py"
FIXTURE = PACKAGE / "fixtures" / "golden_bundle.json"

_spec = importlib.util.spec_from_file_location("inprs_verify_bundle", MODULE_PATH)
assert _spec and _spec.loader
verify = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify)


class InprsClmMigrationGateTest(unittest.TestCase):
    def load(self) -> dict:
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def error_codes(self, bundle: dict) -> set[str]:
        return {row.split(":", 1)[0] for row in verify.validate_bundle(bundle)["errors"]}

    def test_golden_bundle_passes_and_report_is_byte_stable(self) -> None:
        bundle = self.load()
        first = verify.validate_bundle(bundle)
        second = verify.validate_bundle(copy.deepcopy(bundle))
        self.assertTrue(first["ok"], first)
        self.assertEqual(verify.canonical_report_bytes(first), verify.canonical_report_bytes(second))

    def test_duplicate_contract_id_fails_closed(self) -> None:
        bundle = self.load()
        bundle["contracts"].append(copy.deepcopy(bundle["contracts"][0]))
        bundle["expectations"]["source_contract_count"] += 1
        self.assertIn("DUPLICATE_CONTRACT_ID", self.error_codes(bundle))

    def test_orphan_amendment_fails_closed(self) -> None:
        bundle = self.load()
        bundle["contracts"][1]["parent_legacy_id"] = "MISSING"
        self.assertIn("AMENDMENT_PARENT_ORPHAN", self.error_codes(bundle))

    def test_lineage_cycle_fails_closed(self) -> None:
        bundle = self.load()
        bundle["contracts"][1]["parent_legacy_id"] = "C-102"
        bundle["contracts"][2]["parent_legacy_id"] = "C-101"
        self.assertIn("LINEAGE_CYCLE", self.error_codes(bundle))

    def test_migration_hash_drift_fails_closed(self) -> None:
        bundle = self.load()
        bundle["contracts"][0]["target_sha256"] = "f" * 64
        self.assertIn("MIGRATION_HASH_DRIFT", self.error_codes(bundle))

    def test_version_history_must_be_consecutive_and_end_at_target(self) -> None:
        bundle = self.load()
        bundle["contracts"][0]["version_history"][1]["revision"] = 3
        bundle["contracts"][0]["version_history"][1]["sha256"] = "e" * 64
        codes = self.error_codes(bundle)
        self.assertIn("VERSION_SEQUENCE_INVALID", codes)
        self.assertIn("VERSION_FINAL_HASH_MISMATCH", codes)

    def test_public_projection_rejects_internal_field_leak(self) -> None:
        bundle = self.load()
        bundle["public_records"][0]["internal_notes"] = "do not publish"
        self.assertIn("PUBLIC_FIELD_LEAK", self.error_codes(bundle))

    def test_redacted_public_document_must_use_declared_redacted_hash(self) -> None:
        bundle = self.load()
        record = next(row for row in bundle["public_records"] if row["legacy_id"] == "C-101")
        record["document_sha256"] = next(
            row["target_sha256"] for row in bundle["contracts"] if row["legacy_id"] == "C-101"
        )
        self.assertIn("PUBLIC_DOCUMENT_HASH_MISMATCH", self.error_codes(bundle))

    def test_missing_public_record_fails_closed(self) -> None:
        bundle = self.load()
        bundle["public_records"] = [
            row for row in bundle["public_records"] if row["legacy_id"] != "C-100"
        ]
        bundle["expectations"]["public_record_count"] -= 1
        self.assertIn("PUBLIC_RECORD_MISSING", self.error_codes(bundle))

    def test_withheld_record_cannot_be_published(self) -> None:
        bundle = self.load()
        source = next(row for row in bundle["contracts"] if row["legacy_id"] == "C-202")
        leaked = {
            key: source[key]
            for key in (
                "legacy_id",
                "company_name",
                "service_type",
                "contract_cost_cents",
                "effective_date",
                "expiration_date",
                "procurement_method",
                "rfp_number",
            )
        }
        leaked.update(
            document_sha256=source["target_sha256"],
            redacted=False,
            redaction_attestation_sha256=None,
        )
        leaked["search_terms"] = verify.canonical_search_terms(leaked)
        bundle["public_records"].append(leaked)
        bundle["expectations"]["public_record_count"] += 1
        self.assertIn("WITHHELD_RECORD_PUBLISHED", self.error_codes(bundle))

    def test_search_terms_are_exact_and_deterministic(self) -> None:
        bundle = self.load()
        bundle["public_records"][0]["search_terms"].append("secret alias")
        self.assertIn("PUBLIC_SEARCH_TERMS_MISMATCH", self.error_codes(bundle))

    def test_vendor_documents_are_internal_and_hash_preserved(self) -> None:
        bundle = self.load()
        bundle["vendor_documents"][0]["access"] = "public"
        bundle["vendor_documents"][1]["target_sha256"] = "a" * 64
        codes = self.error_codes(bundle)
        self.assertIn("VENDOR_DOCUMENT_PUBLIC_ACCESS", codes)
        self.assertIn("VENDOR_DOCUMENT_HASH_DRIFT", codes)

    def test_expected_counts_prevent_silent_drop(self) -> None:
        bundle = self.load()
        bundle["contracts"].pop()
        self.assertIn("COUNT_MISMATCH", self.error_codes(bundle))


if __name__ == "__main__":
    unittest.main()
