"""Temporary-file regressions for feature-tracker JSON text decoding."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host import feature_tracker as tracker


class FeatureTrackerInvalidTextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="commons-ft-text-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = self.root / tracker.REGISTRY_DIR
        self.evidence = self.root / tracker.EVIDENCE_DIR
        self.registry.mkdir(parents=True)
        self.evidence.mkdir(parents=True)
        self.feature = {
            "schema": tracker.SCHEMA_FEATURE,
            "id": "healthy-feature-20260906-01",
            "name": "Healthy feature",
            "capability": "A usable source record beside an unreadable record.",
            "owner_subsystem": "tracker",
            "carrier": "COBALT",
            "claimed_paths": ["source.py"],
            "test_paths": ["test_source.py"],
            "public_entrypoint": "",
            "dependencies": [],
            "resource_links": [],
            "next_gap": "Keep malformed records visible without losing healthy rows.",
        }
        self.feature_path = self.registry / (self.feature["id"] + ".json")
        self.write_json(self.feature_path, self.feature)
        (self.root / "source.py").write_text("# source fixture\n", encoding="utf-8")
        (self.root / "test_source.py").write_text("# test presence fixture\n", encoding="utf-8")

    @staticmethod
    def write_json(path, record):
        path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    def assert_healthy(self, projection, invalid_count):
        self.assertEqual(projection["n_features"], 1)
        self.assertEqual(projection["n_invalid"], invalid_count)
        self.assertEqual(len(projection["features"]), 1)
        row = projection["features"][0]
        self.assertEqual(row["id"], self.feature["id"])
        self.assertEqual(row["source_status"], "SOURCE_BUILT")
        self.assertEqual(row["test_status"], "TESTS_PRESENT")
        self.assertEqual(row["live_status"], "UNMEASURED")
        return row

    def add_bad_record(self, folder, name="bad-text-20260906-01.json"):
        path = folder / name
        path.write_bytes(b'{"name":"\xff"}')
        return path

    def run_cli(self, *extra):
        return subprocess.run(
            [sys.executable, str(Path(tracker.__file__).resolve()),
             "--root", str(self.root), *extra],
            check=False, capture_output=True, text=True, encoding="utf-8",
            timeout=20,
        )

    def test_loader_reports_invalid_utf8_without_replacing_bytes(self):
        path = self.registry / "invalid-text-20260906-01.json"
        for payload in (b"\xff", b'{"name":"\xe2\x82"}', b"\xff\xfe{\x00}\x00"):
            with self.subTest(payload=payload):
                path.write_bytes(payload)
                record, errors = tracker._load_json_file(path)
                self.assertIsNone(record)
                self.assertEqual(len(errors), 1)
                self.assertIn("UTF-8", errors[0])
                self.assertEqual(path.read_bytes(), payload)

    def test_invalid_registry_record_keeps_healthy_feature(self):
        bad = self.add_bad_record(self.registry)
        projection = tracker.project(str(self.root))
        self.assert_healthy(projection, 1)
        self.assertEqual(len(projection["problems"]), 1)
        self.assertIn(bad.name, projection["problems"][0])
        self.assertIn("UTF-8", projection["problems"][0])

    def test_invalid_evidence_keeps_valid_evidence(self):
        healthy = {
            "schema": tracker.SCHEMA_EVIDENCE,
            "id": "healthy-evidence-20260906-01",
            "feature_id": self.feature["id"],
            "kind": "RECEIPT",
            "receipt": "healthy-receipt-20260906-01",
        }
        self.write_json(self.evidence / (healthy["id"] + ".json"), healthy)
        bad = self.add_bad_record(self.evidence)
        projection = tracker.project(str(self.root))
        row = self.assert_healthy(projection, 1)
        self.assertEqual(row["evidence_ids"], [healthy["id"]])
        self.assertEqual(row["receipts"], [healthy["receipt"]])
        self.assertIn(bad.name, projection["problems"][0])

    def test_each_bad_record_is_counted_and_reported(self):
        names = []
        for folder, name in ((self.registry, "a-invalid-feature-20260906.json"),
                             (self.evidence, "z-invalid-evidence-20260906.json")):
            names.append(self.add_bad_record(folder, name).name)
        projection = tracker.project(str(self.root))
        self.assert_healthy(projection, 2)
        self.assertEqual(len(projection["problems"]), 2)
        for name in names:
            self.assertTrue(any(name in error for error in projection["problems"]))

    def test_cli_emits_json_diagnostics_and_nonzero_status_without_writes(self):
        self.add_bad_record(self.registry)
        before = {p.relative_to(self.root): p.read_bytes()
                  for p in self.root.rglob("*") if p.is_file()}
        result = self.run_cli()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assert_healthy(json.loads(result.stdout), 1)
        after = {p.relative_to(self.root): p.read_bytes()
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_write_cli_preserves_records_and_writes_usable_projections(self):
        bad = self.add_bad_record(self.evidence)
        originals = {p: p.read_bytes() for folder in (self.registry, self.evidence)
                     for p in folder.glob("*.json")}
        result = self.run_cli("--write")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr, "")
        projection = json.loads(result.stdout)
        self.assert_healthy(projection, 1)
        machine = json.loads((self.root / tracker.JSON_OUT).read_text(encoding="utf-8"))
        self.assertEqual(machine, projection)
        page = (self.root / tracker.HTML_OUT).read_text(encoding="utf-8")
        self.assertIn(self.feature["name"], page)
        self.assertIn(bad.name, page)
        self.assertIn("UTF-8", page)
        for path, original in originals.items():
            self.assertEqual(path.read_bytes(), original)

    def test_valid_unicode_is_not_changed_or_rejected(self):
        self.feature["name"] = "Café — 東京 🚀"
        self.write_json(self.feature_path, self.feature)
        original = self.feature_path.read_bytes()
        projection = tracker.project(str(self.root))
        row = self.assert_healthy(projection, 0)
        self.assertEqual(row["name"], self.feature["name"])
        self.assertEqual(projection["problems"], [])
        self.assertEqual(self.feature_path.read_bytes(), original)
        self.assertEqual(self.run_cli().returncode, 0)

    def test_malformed_json_keeps_existing_diagnostic(self):
        path = self.registry / "bad-json-20260906-01.json"
        path.write_text('{"unfinished":', encoding="utf-8")
        record, errors = tracker._load_json_file(path)
        self.assertIsNone(record)
        self.assertTrue(errors[0].startswith("not JSON:"))
        self.assert_healthy(tracker.project(str(self.root)), 1)

    def test_missing_empty_and_whitespace_keep_existing_diagnostic(self):
        path = self.registry / "empty-json-20260906-01.json"
        self.assertEqual(tracker._load_json_file(path), (None, ["unreadable or empty"]))
        for content in ("", " \n\t"):
            with self.subTest(content=content):
                path.write_text(content, encoding="utf-8")
                self.assertEqual(tracker._load_json_file(path), (None, ["unreadable or empty"]))

    def test_non_object_json_keeps_existing_diagnostic(self):
        path = self.registry / "non-object-20260906-01.json"
        for record in ([], None, 17, "text"):
            with self.subTest(record=record):
                self.write_json(path, record)
                self.assertEqual(tracker._load_json_file(path), (None, ["not an object"]))


if __name__ == "__main__":
    unittest.main()
