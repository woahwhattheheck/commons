#!/usr/bin/env python3
"""Focused contracts for canonical TITAN drift diagnostics."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("titan_build_integrated", LAB / "build_integrated.py")
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


class RuntimeDriftTests(unittest.TestCase):
    def test_exact_added_removed_changed_and_unchanged_members(self):
        actual = {"runtime": {
            "same.py": {"sha256": "same", "bytes": 4, "source_path": "same.py"},
            "changed.py": {"sha256": "old", "bytes": 3, "source_path": "changed.py"},
            "removed.py": {"sha256": "gone", "bytes": 4, "source_path": "removed.py"},
        }}
        expected = {"runtime": {
            "same.py": {"sha256": "same", "bytes": 4, "source_path": "same.py"},
            "changed.py": {"sha256": "new", "bytes": 3, "source_path": "changed.py"},
            "added.py": {"sha256": "add", "bytes": 3, "source_path": "added.py"},
        }}
        delta = BUILDER._runtime_drift(actual, expected)
        self.assertEqual(delta["added"], ["added.py"])
        self.assertEqual(delta["removed"], ["removed.py"])
        self.assertEqual([item["member"] for item in delta["changed"]], ["changed.py"])
        self.assertEqual(delta["unchanged"], 1)


class PublicationDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.old_root = BUILDER.ROOT
        self.temp = tempfile.TemporaryDirectory()
        BUILDER.ROOT = Path(self.temp.name)
        (BUILDER.ROOT / "exports").mkdir(parents=True)
        (BUILDER.ROOT / "runtime/integrated-selected").mkdir(parents=True)

    def tearDown(self):
        BUILDER.ROOT = self.old_root
        self.temp.cleanup()

    def fixture(self):
        manifest_value = {"runtime": {
            "same.py": {"sha256": "same", "bytes": 4, "source_path": "same.py"},
            "changed.py": {"sha256": "new", "bytes": 3, "source_path": "changed.py"},
            "added.py": {"sha256": "add", "bytes": 3, "source_path": "added.py"},
        }}
        manifest = encoded(manifest_value)
        archive = b"new archive bytes"
        receipt = {
            "path": BUILDER.ARCHIVE,
            "entrypoint": "main.py::agent",
            "config": "TITAN-CONFIG.json",
            "sha256": hashlib.sha256(archive).hexdigest(),
            "bytes": len(archive),
            "runtime_files": 3,
            "source_manifest": BUILDER.RECORD + "CURRENT-SOURCE.json",
            "source_manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        }
        return archive, manifest, receipt

    def write_publication(self, archive, manifest, receipt):
        (BUILDER.ROOT / BUILDER.ARCHIVE).write_bytes(archive)
        (BUILDER.ROOT / (BUILDER.RECORD + "CURRENT-SOURCE.json")).write_bytes(manifest)
        (BUILDER.ROOT / (BUILDER.RECORD + "CURRENT-ARCHIVE.json")).write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    def test_clean_publication_is_reported_without_mutation(self):
        archive, manifest, receipt = self.fixture()
        self.write_publication(archive, manifest, receipt)
        before = {
            path: path.read_bytes()
            for path in (
                BUILDER.ROOT / BUILDER.ARCHIVE,
                BUILDER.ROOT / (BUILDER.RECORD + "CURRENT-SOURCE.json"),
                BUILDER.ROOT / (BUILDER.RECORD + "CURRENT-ARCHIVE.json"),
            )
        }
        report = BUILDER._diagnose_rendered(archive, manifest, receipt)
        self.assertEqual(report["status"], "clean")
        self.assertTrue(report["pointer"]["matches"])
        self.assertTrue(report["archive"]["matches"])
        self.assertTrue(report["manifest"]["matches"])
        self.assertEqual(report["runtime"], {
            "added": [], "removed": [], "changed": [], "unchanged": 3,
        })
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_drift_names_exact_runtime_members(self):
        archive, manifest, receipt = self.fixture()
        actual_manifest = encoded({"runtime": {
            "same.py": {"sha256": "same", "bytes": 4, "source_path": "same.py"},
            "changed.py": {"sha256": "old", "bytes": 3, "source_path": "changed.py"},
            "removed.py": {"sha256": "gone", "bytes": 4, "source_path": "removed.py"},
        }})
        self.write_publication(b"old archive bytes", actual_manifest, {"sha256": "old"})
        report = BUILDER._diagnose_rendered(archive, manifest, receipt)
        self.assertEqual(report["status"], "drift")
        self.assertEqual(report["runtime"]["added"], ["added.py"])
        self.assertEqual(report["runtime"]["removed"], ["removed.py"])
        self.assertEqual([item["member"] for item in report["runtime"]["changed"]],
                         ["changed.py"])
        self.assertEqual(BUILDER._drift_summary(report),
                         "runtime_added=added.py; runtime_removed=removed.py; "
                         "runtime_changed=changed.py; stale=pointer,archive,manifest")

    def test_verify_error_retains_legacy_prefix_and_adds_member_names(self):
        archive, manifest, receipt = self.fixture()
        actual_manifest = encoded({"runtime": {
            "changed.py": {"sha256": "old", "bytes": 3, "source_path": "changed.py"},
        }})
        self.write_publication(b"old", actual_manifest, {"sha256": "old"})
        old_render = BUILDER.render
        BUILDER.render = lambda: (archive, manifest, receipt)
        try:
            with self.assertRaisesRegex(
                    ValueError,
                    r"^Current release pointer differs from current source: .*changed\.py"):
                BUILDER.verify_current()
        finally:
            BUILDER.render = old_render

    def test_missing_publication_is_a_report_not_an_unhandled_io_error(self):
        archive, manifest, receipt = self.fixture()
        report = BUILDER._diagnose_rendered(archive, manifest, receipt)
        self.assertEqual(report["status"], "drift")
        self.assertEqual(report["pointer"]["error"], "missing")
        self.assertEqual(report["archive"]["error"], "missing")
        self.assertEqual(report["manifest"]["error"], "missing")


if __name__ == "__main__":
    unittest.main()
