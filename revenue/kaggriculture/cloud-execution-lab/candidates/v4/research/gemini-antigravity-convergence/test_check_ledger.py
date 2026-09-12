#!/usr/bin/env python3
import copy
import json
from pathlib import Path
import tempfile
import unittest

import check_ledger as C

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "GEMINI-ANTIGRAVITY.json"
LEGACY = HERE / "LEGACY-GEMINI.json"


def load_doc(path=LEDGER):
    return json.loads(path.read_text(encoding="utf-8"))


def materialize_evidence(root: Path, *docs):
    paths = set()
    for doc in docs:
        for entry in doc.get("entries", []):
            paths.update(entry["canonical_evidence"])
        for override in doc.get("canonical_overrides", []):
            paths.update(override["canonical_evidence"])
    for rel in paths:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("evidence\n", encoding="utf-8")


class GeminiConvergenceTests(unittest.TestCase):
    def setUp(self):
        self.doc = load_doc()
        self.legacy = load_doc(LEGACY)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        materialize_evidence(self.root, self.doc, self.legacy)

    def tearDown(self):
        self.tmp.cleanup()

    def assertRejected(self, doc, pattern=None):
        with self.assertRaises(C.ConvergenceError) as ctx:
            C.validate_document(doc, self.root)
        if pattern is not None:
            self.assertIn(pattern, str(ctx.exception))

    def assertLegacyRejected(self, doc, pattern=None):
        with self.assertRaises(C.ConvergenceError) as ctx:
            C.validate_legacy_document(doc, self.root)
        if pattern is not None:
            self.assertIn(pattern, str(ctx.exception))

    def assertBundleRejected(self, primary, legacy, pattern=None):
        with self.assertRaises(C.ConvergenceError) as ctx:
            C.validate_bundle_documents(primary, legacy, self.root)
        if pattern is not None:
            self.assertIn(pattern, str(ctx.exception))

    def test_complete_bundle_accepts_all_36_propositions(self):
        result = C.validate_bundle_documents(
            copy.deepcopy(self.doc), copy.deepcopy(self.legacy), self.root
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["antigravity_entry_count"], 21)
        self.assertEqual(result["legacy_entry_count"], 15)
        self.assertEqual(result["entry_count"], 36)
        self.assertEqual(result["override_count"], 1)
        self.assertEqual(sum(result["dispositions"].values()), 36)

    def test_primary_ledger_still_accepts_exact_21(self):
        result = C.validate_document(copy.deepcopy(self.doc), self.root)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["entry_count"], 21)

    def test_missing_primary_required_id_rejected(self):
        doc = copy.deepcopy(self.doc)
        doc["entries"] = doc["entries"][1:]
        doc["entry_count"] -= 1
        self.assertRejected(doc, "coverage mismatch")

    def test_missing_legacy_required_id_rejected(self):
        doc = copy.deepcopy(self.legacy)
        doc["entries"] = doc["entries"][1:]
        doc["entry_count"] -= 1
        self.assertLegacyRejected(doc, "coverage mismatch")

    def test_duplicate_id_rejected(self):
        doc = copy.deepcopy(self.doc)
        doc["entries"][1]["id"] = doc["entries"][0]["id"]
        self.assertRejected(doc, "duplicate entry id")

    def test_entries_must_stay_sorted(self):
        doc = copy.deepcopy(self.legacy)
        doc["entries"][0], doc["entries"][1] = doc["entries"][1], doc["entries"][0]
        self.assertLegacyRejected(doc, "sorted by id")

    def test_primary_legacy_overlap_rejected(self):
        legacy = copy.deepcopy(self.legacy)
        legacy["entries"][0]["id"] = self.doc["entries"][0]["id"]
        # Repair the exact-set guard so this test reaches the cross-ledger guard.
        old = sorted(C.LEGACY_REQUIRED_IDS)[0]
        required = set(C.LEGACY_REQUIRED_IDS)
        required.remove(old)
        required.add(self.doc["entries"][0]["id"])
        saved = C.LEGACY_REQUIRED_IDS
        try:
            C.LEGACY_REQUIRED_IDS = frozenset(required)
            self.assertBundleRejected(self.doc, legacy, "duplicate propositions")
        finally:
            C.LEGACY_REQUIRED_IDS = saved

    def test_evidence_outside_v4_rejected(self):
        doc = copy.deepcopy(self.legacy)
        doc["entries"][0]["canonical_evidence"][0] = "README.md"
        self.assertLegacyRejected(doc, "outside canonical V4")

    def test_legacy_directory_evidence_rejected(self):
        doc = copy.deepcopy(self.legacy)
        rel = C.V4_PREFIX + "legacy/stale.md"
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stale\n", encoding="utf-8")
        doc["entries"][0]["canonical_evidence"][0] = rel
        self.assertLegacyRejected(doc, "noncanonical ancestry")

    def test_missing_evidence_rejected(self):
        doc = copy.deepcopy(self.legacy)
        rel = doc["entries"][0]["canonical_evidence"][0]
        (self.root / rel).unlink()
        self.assertLegacyRejected(doc, "missing canonical evidence")

    def test_directory_is_not_evidence(self):
        doc = copy.deepcopy(self.doc)
        rel = doc["entries"][0]["canonical_evidence"][0]
        path = self.root / rel
        path.unlink()
        path.mkdir()
        self.assertRejected(doc, "not a regular file")

    def test_falsified_claim_must_be_fenced(self):
        doc = copy.deepcopy(self.legacy)
        entry = next(e for e in doc["entries"] if e["disposition"] == "FALSIFIED")
        entry.pop("do_not_repeat_without_new_evidence")
        self.assertLegacyRejected(doc, "durably fenced")

    def test_field_blocked_claim_must_remain_blocked(self):
        doc = copy.deepcopy(self.legacy)
        entry = next(e for e in doc["entries"] if e["disposition"] == "FIELD_BLOCKED")
        entry["activation"] = "DEFAULT_OFF"
        self.assertLegacyRejected(doc, "must use BLOCKED activation")

    def test_pr_provenance_must_be_sorted_unique_plain_ints(self):
        doc = copy.deepcopy(self.legacy)
        doc["entries"][0]["provenance_pull_numbers"] = [13024, 10004, 10004]
        self.assertLegacyRejected(doc, "sorted and unique")
        doc = copy.deepcopy(self.legacy)
        doc["entries"][0]["provenance_pull_numbers"] = [True]
        self.assertLegacyRejected(doc, "invalid PR provenance")

    def test_nonfinite_json_rejected(self):
        path = self.root / "bad.json"
        path.write_text('{"x": NaN}', encoding="utf-8")
        with self.assertRaises(C.ConvergenceError):
            C.load_strict_json(path)

    def test_source_buckets_are_exact_per_ledger(self):
        doc = copy.deepcopy(self.doc)
        doc["source_stream"]["included_buckets"] = ["master_manifest"]
        self.assertRejected(doc, "included_buckets")
        legacy = copy.deepcopy(self.legacy)
        legacy["source_stream"]["included_buckets"] = ["legacy_gemini_v3"]
        self.assertLegacyRejected(legacy, "legacy included_buckets")

    def test_demand_velocity_override_is_mandatory_and_current_v4_only(self):
        doc = copy.deepcopy(self.legacy)
        doc["canonical_overrides"] = []
        self.assertLegacyRejected(doc, "canonical override mismatch")

        doc = copy.deepcopy(self.legacy)
        doc["canonical_overrides"][0]["canonical_evidence"][0] = "old/DEMAND.md"
        self.assertLegacyRejected(doc, "outside canonical V4")

    def test_override_must_target_primary_proposition(self):
        legacy = copy.deepcopy(self.legacy)
        legacy["canonical_overrides"][0]["id"] = "gemini.not-in-primary"
        saved = C.REQUIRED_OVERRIDE_IDS
        try:
            C.REQUIRED_OVERRIDE_IDS = frozenset({"gemini.not-in-primary"})
            self.assertBundleRejected(self.doc, legacy, "unknown primary id")
        finally:
            C.REQUIRED_OVERRIDE_IDS = saved


if __name__ == "__main__":
    unittest.main()