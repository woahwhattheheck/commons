#!/usr/bin/env python3
import copy
from pathlib import Path
import tempfile
import unittest

import check_ledger as C

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "GEMINI-ANTIGRAVITY.json"


def load_doc():
    return C.load_strict_json(LEDGER)


def materialize_evidence(root: Path, doc):
    for entry in doc["entries"]:
        for rel in entry["canonical_evidence"]:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("evidence\n", encoding="utf-8")


class GeminiConvergenceTests(unittest.TestCase):
    def setUp(self):
        self.doc = load_doc()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        materialize_evidence(self.root, self.doc)

    def tearDown(self):
        self.tmp.cleanup()

    def assertRejected(self, doc, pattern=None):
        with self.assertRaises(C.ConvergenceError) as ctx:
            C.validate_document(doc, self.root)
        if pattern is not None:
            self.assertIn(pattern, str(ctx.exception))

    def test_complete_ledger_accepts(self):
        result = C.validate_document(copy.deepcopy(self.doc), self.root)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["entry_count"], 34)
        self.assertEqual(sum(result["dispositions"].values()), 34)

    def test_missing_required_id_rejected(self):
        doc = copy.deepcopy(self.doc)
        doc["entries"] = doc["entries"][1:]
        doc["entry_count"] -= 1
        self.assertRejected(doc, "coverage mismatch")

    def test_authenticated_extension_ids_are_hard_required(self):
        extension = {
            "gemini.analyzer-margin-clipping",
            "gemini.fert-price-floor-arbitrage",
            "gemini.fert-revenue-liquidate",
            "gemini.flash-market",
            "gemini.g01-e11-rival-dump-deferral",
            "gemini.g01-e20-hire-guard",
            "gemini.g01-o01-public-rival-archetype",
            "gemini.g01-shop-absorption",
            "gemini.idle-hands",
            "gemini.pro-capital",
            "gemini.stratum-row-shed",
            "gemini.terminal-mass-hire",
            "gemini.wheat-market-denial",
        }
        self.assertTrue(extension.issubset(C.REQUIRED_IDS))
        for entry_id in sorted(extension):
            doc = copy.deepcopy(self.doc)
            doc["entries"] = [e for e in doc["entries"] if e["id"] != entry_id]
            doc["entry_count"] -= 1
            self.assertRejected(doc, "coverage mismatch")

    def test_provenance_quarantine_ids_are_not_minted(self):
        ids = {entry["id"] for entry in self.doc["entries"]}
        self.assertFalse(any("meridian" in entry_id for entry_id in ids))
        self.assertFalse(any("openmore" in entry_id for entry_id in ids))
        self.assertFalse(any("adaptive" in entry_id for entry_id in ids))

    def test_duplicate_id_rejected(self):
        doc = copy.deepcopy(self.doc)
        doc["entries"][1]["id"] = doc["entries"][0]["id"]
        self.assertRejected(doc, "duplicate entry id")

    def test_entries_must_stay_sorted(self):
        doc = copy.deepcopy(self.doc)
        doc["entries"][0], doc["entries"][1] = doc["entries"][1], doc["entries"][0]
        self.assertRejected(doc, "sorted by id")

    def test_evidence_outside_v4_rejected(self):
        doc = copy.deepcopy(self.doc)
        doc["entries"][0]["canonical_evidence"][0] = "README.md"
        self.assertRejected(doc, "outside canonical V4")

    def test_literal_legacy_evidence_rejected(self):
        doc = copy.deepcopy(self.doc)
        rel = C.V4_PREFIX + "legacy/stale.md"
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stale\n", encoding="utf-8")
        doc["entries"][0]["canonical_evidence"][0] = rel
        self.assertRejected(doc, "noncanonical ancestry")

    def test_symlink_ancestor_alias_rejected(self):
        doc = copy.deepcopy(self.doc)
        legacy = self.root / C.V4_PREFIX / "research" / "legacy"
        legacy.mkdir(parents=True, exist_ok=True)
        (legacy / "stale.md").write_text("stale\n", encoding="utf-8")
        alias = self.root / C.V4_PREFIX / "research" / "current-alias"
        try:
            alias.symlink_to("legacy", target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        rel = C.V4_PREFIX + "research/current-alias/stale.md"
        doc["entries"][0]["canonical_evidence"][0] = rel
        self.assertRejected(doc, "symlink path component")

    def test_leaf_symlink_rejected(self):
        doc = copy.deepcopy(self.doc)
        rel = doc["entries"][0]["canonical_evidence"][0]
        path = self.root / rel
        backing = path.with_name(path.name + ".real")
        path.replace(backing)
        try:
            path.symlink_to(backing.name)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        self.assertRejected(doc, "symlink path component")

    def test_missing_evidence_rejected(self):
        doc = copy.deepcopy(self.doc)
        rel = doc["entries"][0]["canonical_evidence"][0]
        (self.root / rel).unlink()
        self.assertRejected(doc, "missing canonical evidence")

    def test_directory_is_not_evidence(self):
        doc = copy.deepcopy(self.doc)
        rel = doc["entries"][0]["canonical_evidence"][0]
        path = self.root / rel
        path.unlink()
        path.mkdir()
        self.assertRejected(doc, "not a regular file")

    def test_falsified_claim_must_be_fenced(self):
        doc = copy.deepcopy(self.doc)
        entry = next(e for e in doc["entries"] if e["disposition"] == "FALSIFIED")
        entry.pop("do_not_repeat_without_new_evidence")
        self.assertRejected(doc, "durably fenced")

    def test_field_blocked_claim_must_remain_blocked(self):
        doc = copy.deepcopy(self.doc)
        entry = next(e for e in doc["entries"] if e["disposition"] == "FIELD_BLOCKED")
        entry["activation"] = "DEFAULT_OFF"
        self.assertRejected(doc, "must use BLOCKED activation")

    def test_melon_debt_cannot_be_promoted_without_checker_update(self):
        doc = copy.deepcopy(self.doc)
        entry = next(e for e in doc["entries"] if e["id"] == "gemini.melon-lifetime-cap")
        entry["disposition"] = "CORRECTED_DESCENDANT"
        entry["activation"] = "DEFAULT_OFF"
        entry.pop("do_not_repeat_without_new_evidence", None)
        self.assertRejected(doc, "must remain FIELD_BLOCKED")

    def test_pr_provenance_must_be_sorted_unique_plain_ints(self):
        doc = copy.deepcopy(self.doc)
        doc["entries"][0]["provenance_pull_numbers"] = [12837, 12819, 12819]
        self.assertRejected(doc, "sorted and unique")
        doc = copy.deepcopy(self.doc)
        doc["entries"][0]["provenance_pull_numbers"] = [True]
        self.assertRejected(doc, "invalid PR provenance")

    def test_nonfinite_json_rejected(self):
        path = self.root / "bad.json"
        path.write_text('{"x": NaN}', encoding="utf-8")
        with self.assertRaises(C.ConvergenceError):
            C.load_strict_json(path)

    def test_duplicate_root_json_key_rejected(self):
        path = self.root / "dup.json"
        path.write_text('{"schema":"a","schema":"b"}', encoding="utf-8")
        with self.assertRaisesRegex(C.ConvergenceError, "duplicate JSON key: schema"):
            C.load_strict_json(path)

    def test_duplicate_nested_json_key_rejected(self):
        path = self.root / "dup-nested.json"
        path.write_text('{"x":{"id":"first","id":"second"}}', encoding="utf-8")
        with self.assertRaisesRegex(C.ConvergenceError, "duplicate JSON key: id"):
            C.load_strict_json(path)

    def test_source_buckets_are_exact_and_unique(self):
        doc = copy.deepcopy(self.doc)
        doc["source_stream"]["included_buckets"] = ["master_manifest"]
        self.assertRejected(doc, "included_buckets")
        doc = copy.deepcopy(self.doc)
        doc["source_stream"]["included_buckets"].append("master_manifest")
        self.assertRejected(doc, "included_buckets")


if __name__ == "__main__":
    unittest.main()
