#!/usr/bin/env python3
"""The current-work report stays machine-readable after a catalog decode error."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / "host"))
import current_work as cw


class CatalogEncodingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.catalog_path = self.root / "ground" / "CURRENT_WORK.json"
        self.catalog_path.parent.mkdir()

    def catalog(self):
        return {
            "schema": cw.SCHEMA,
            "add_work": {"preferred": cw.SHIP_LOOP},
            "items": [{
                "id": "encoding-work-20260907-01",
                "title": "Unicode work café 日本語 🌾",
                "kind": "BUILDABLE",
                "claimed_paths": ["récolte-稲.txt"],
            }],
        }

    def write_catalog(self, catalog):
        raw = json.dumps(catalog, ensure_ascii=False).encode("utf-8")
        self.catalog_path.write_bytes(raw)
        return raw

    def run_cli(self, sha="a" * 40):
        return subprocess.run(
            [sys.executable, str(Path(cw.__file__).resolve()),
             "--root", str(self.root), "--main-sha", sha],
            capture_output=True, text=True, check=False, timeout=10,
        )

    def assert_decode_report(self, result):
        self.assertEqual(result, {
            "error": "catalog is not UTF-8",
            "open_now": [],
            "items": [],
        })

    def test_invalid_utf8_returns_explicit_error_without_rewriting_input(self):
        for raw in (b"\xff", b"\x80", b"\xc3", b"\xed\xa0\x80", b"\xf0\x9f\x8c"):
            with self.subTest(raw=raw):
                self.catalog_path.write_bytes(raw)
                self.assert_decode_report(cw.measure_tree(str(self.root), "a" * 40))
                self.assertEqual(self.catalog_path.read_bytes(), raw)

    def test_valid_looking_catalog_with_bad_title_byte_is_not_lossily_projected(self):
        raw = self.write_catalog(self.catalog()).replace("café".encode("utf-8"), b"caf\xff")
        self.catalog_path.write_bytes(raw)
        (self.root / "récolte-稲.txt").write_text("delivered", encoding="utf-8")
        self.assert_decode_report(cw.measure_tree(str(self.root), "a" * 40))
        self.assertEqual(self.catalog_path.read_bytes(), raw)

    def test_cli_emits_error_json_and_exit_one_without_traceback(self):
        for raw in (b"\xff", b'{"schema":"\xc3"}', b"\xff\xfe{\x00}"):
            with self.subTest(raw=raw):
                self.catalog_path.write_bytes(raw)
                completed = self.run_cli()
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stderr, "")
                self.assert_decode_report(json.loads(completed.stdout))
                self.assertEqual(self.catalog_path.read_bytes(), raw)

    def test_valid_unicode_catalog_and_paths_remain_exact(self):
        catalog = self.catalog()
        raw = self.write_catalog(catalog)
        (self.root / "récolte-稲.txt").write_text("real evidence\n", encoding="utf-8")
        report = cw.measure_tree(str(self.root), "a" * 40)
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["items"][0]["title"], catalog["items"][0]["title"])
        self.assertEqual(report["items"][0]["status"], "CLOSED")
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(json.loads(completed.stdout), report)
        self.assertEqual(self.catalog_path.read_bytes(), raw)

    def test_valid_empty_catalog_is_distinct_from_decode_failure(self):
        catalog = self.catalog()
        catalog["items"] = []
        self.write_catalog(catalog)
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertNotIn("error", report)
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["open_now"], [])

    def test_json_syntax_and_top_level_type_errors_are_unchanged(self):
        for raw, error in ((b'{"items":', "catalog is not JSON"),
                           (b"[]", "catalog is not an object")):
            with self.subTest(raw=raw):
                self.catalog_path.write_bytes(raw)
                completed = self.run_cli()
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stderr, "")
                self.assertEqual(json.loads(completed.stdout), {
                    "error": error, "open_now": [], "items": [],
                })

    def test_missing_empty_and_directory_catalogs_retain_validation_diagnostics(self):
        for kind in ("missing", "empty", "directory"):
            with self.subTest(kind=kind):
                if kind == "empty":
                    self.catalog_path.write_bytes(b"")
                elif kind == "directory":
                    self.catalog_path.unlink()
                    self.catalog_path.mkdir()
                completed = self.run_cli()
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stderr, "")
                report = json.loads(completed.stdout)
                self.assertTrue(report.get("problems"))
                self.assertEqual(report["items"], [])
                self.assertEqual(report["open_now"], [])

    def test_repaired_catalog_is_read_on_next_call(self):
        self.catalog_path.write_bytes(b"\xff")
        self.assert_decode_report(cw.measure_tree(str(self.root)))
        self.write_catalog(self.catalog())
        report = cw.measure_tree(str(self.root))
        self.assertNotIn("error", report)
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["items"][0]["status"], "OPEN")
        self.assertEqual(len(report["open_now"]), 1)


if __name__ == "__main__":
    unittest.main()
