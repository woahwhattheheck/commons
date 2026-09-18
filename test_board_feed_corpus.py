#!/usr/bin/env python3
"""Exact-evidence tests for the Commons board feed corpus sample."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("board_feed_corpus", ROOT / "host/board_feed_corpus.py")
corpus = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(corpus)


class BoardFeedCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.schema = corpus.load(ROOT)

    def test_schema_and_semantic_contract(self):
        from test_outcome_commerce import MiniSchemaValidator

        self.assertIs(self.schema["additionalProperties"], False)
        MiniSchemaValidator(ROOT / "revenue/data").validate_file(self.data, "board_feed_corpus.schema.json")
        result = corpus.validate(ROOT, self.data, self.schema)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["rows"], 500)
        self.assertEqual(result["distinct_froms"], 24)
        self.assertEqual(result["scan_hits"], 0)
        self.assertEqual(result["release_state"], "BLOCKED_LICENSE_REQUIRED")

    def test_exact_entry_ids_and_frozen_copy_flag(self):
        self.assertEqual([entry["entry_id"] for entry in self.data["entries"]], list(corpus.ENTRY_IDS))
        self.assertIs(self.data["snapshot_frozen_copy"], True)

    def test_sample_blob_drift_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["entries"][0]["sample_blob_sha"] = "0" * 40
        with self.assertRaisesRegex(corpus.CorpusError, "sample blob drift"):
            corpus.validate(ROOT, broken, self.schema)

    def test_sample_sha256_drift_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["entries"][0]["sample_sha256"] = "0" * 64
        with self.assertRaisesRegex(corpus.CorpusError, "sample SHA-256 drift"):
            corpus.validate(ROOT, broken, self.schema)

    def test_window_stats_drift_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["window"]["distinct_froms"] = 23
        with self.assertRaisesRegex(corpus.CorpusError, "window stats drift"):
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

    def test_sensitivity_review_must_remain_complete(self):
        broken = copy.deepcopy(self.data)
        broken["sensitivity_review"]["files_reviewed"] = 0
        with self.assertRaisesRegex(corpus.CorpusError, "sensitivity review incomplete"):
            corpus.validate(ROOT, broken, self.schema)

    def test_customer_or_outreach_material_fails_closed(self):
        for key in ("customer_material", "outreach_material"):
            with self.subTest(key=key):
                broken = copy.deepcopy(self.data)
                broken["entries"][0][key] = True
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
            [sys.executable, str(ROOT / "host/board_feed_corpus.py"), "validate", "--root", str(ROOT)],
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
