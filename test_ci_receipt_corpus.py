#!/usr/bin/env python3
"""Exact-evidence tests for the Commons CI receipt corpus candidate."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("ci_receipt_corpus", ROOT / "host/ci_receipt_corpus.py")
corpus = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(corpus)


class CiReceiptCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.schema = corpus.load(ROOT)

    def test_schema_and_semantic_contract(self):
        from test_outcome_commerce import MiniSchemaValidator

        self.assertIs(self.schema["additionalProperties"], False)
        MiniSchemaValidator(ROOT / "revenue/data").validate_file(self.data, "ci_receipt_corpus.schema.json")
        result = corpus.validate(ROOT, self.data, self.schema)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["source_pool_json"], 50)
        self.assertEqual(result["curated_entries"], 9)
        self.assertEqual(result["curated_bytes"], 3733)
        self.assertEqual(result["scan_hits"], 0)

    def test_exact_receipt_ids_and_no_payload_duplication(self):
        self.assertEqual([entry["receipt_id"] for entry in self.data["entries"]], list(corpus.ENTRY_IDS))
        self.assertIs(self.data["payloads_duplicated"], False)

    def test_source_blob_drift_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["entries"][0]["source_blob_sha"] = "0" * 40
        with self.assertRaisesRegex(corpus.CorpusError, "source blob drift"):
            corpus.validate(ROOT, broken, self.schema)

    def test_source_sha256_drift_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["entries"][0]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(corpus.CorpusError, "source SHA-256 drift"):
            corpus.validate(ROOT, broken, self.schema)

    def test_scanner_detects_representative_secret_and_pii_patterns(self):
        raw = b"email=test@example.com token=ghp_abcdefghijklmnopqrstuvwxyz password=hunter2"
        hits = corpus.scan_bytes(raw)
        self.assertEqual(hits["EMAIL"], 1)
        self.assertEqual(hits["GITHUB_TOKEN"], 1)
        self.assertEqual(hits["PASSWORD"], 1)

    def test_recorded_scan_mutation_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["scan"]["hit_counts"]["EMAIL"] = 1
        with self.assertRaisesRegex(corpus.CorpusError, "recorded scan contains hits"):
            corpus.validate(ROOT, broken, self.schema)

    def test_manual_review_must_remain_complete(self):
        broken = copy.deepcopy(self.data)
        broken["manual_review"]["files_reviewed"] = 8
        with self.assertRaisesRegex(corpus.CorpusError, "manual review incomplete"):
            corpus.validate(ROOT, broken, self.schema)

    def test_manual_review_criteria_repudiation_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["manual_review"]["criteria"] = "No deliberate byte review was performed; this is placeholder prose."
        with self.assertRaisesRegex(corpus.CorpusError, "manual review criteria drift"):
            corpus.validate(ROOT, broken, self.schema)

    def test_manual_review_result_repudiation_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["manual_review"]["result"] = "No content review result exists; this is placeholder prose only."
        with self.assertRaisesRegex(corpus.CorpusError, "manual review result drift"):
            corpus.validate(ROOT, broken, self.schema)

    def test_customer_or_outreach_material_fails_closed(self):
        for key in ("customer_material", "outreach_material"):
            with self.subTest(key=key):
                broken = copy.deepcopy(self.data)
                broken["entries"][3][key] = True
                with self.assertRaisesRegex(corpus.CorpusError, "excluded material present"):
                    corpus.validate(ROOT, broken, self.schema)

    def test_license_cannot_be_promoted_without_evidence(self):
        broken = copy.deepcopy(self.data)
        broken["license"]["status"] = "LICENSED"
        broken["license"]["reuse_rights_verified"] = True
        with self.assertRaisesRegex(corpus.CorpusError, "license must remain NOASSERTION"):
            corpus.validate(ROOT, broken, self.schema)

    def test_release_cannot_be_marked_ready(self):
        broken = copy.deepcopy(self.data)
        broken["release"]["state"] = "RELEASED"
        broken["release"]["transfer_ready"] = True
        with self.assertRaisesRegex(corpus.CorpusError, "must remain license-blocked"):
            corpus.validate(ROOT, broken, self.schema)

    def test_commercial_truth_cannot_be_invented(self):
        broken = copy.deepcopy(self.data)
        broken["truth"]["cash_received"] = True
        with self.assertRaisesRegex(corpus.CorpusError, "may not invent"):
            corpus.validate(ROOT, broken, self.schema)

    def test_cli_validate(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "host/ci_receipt_corpus.py"), "validate", "--root", str(ROOT)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["release_state"], "BLOCKED_LICENSE_REQUIRED")


if __name__ == "__main__":
    unittest.main()
