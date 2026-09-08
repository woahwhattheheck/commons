#!/usr/bin/env python3
"""Real-file extractor-main tests and subprocess CLI smoke regressions.

Run with Python directly. BUNDLE_EXTRACTOR_UNDER_TEST optionally selects an
unchanged source snapshot when recording before/after evidence.
"""
from __future__ import annotations

import base64
import copy
import contextlib
import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import traceback
import unittest
from unittest import mock


PREFIX = Path("revenue/hive/multilingual-catalog-publisher")
SCRIPT = Path(os.environ.get("BUNDLE_EXTRACTOR_UNDER_TEST", str(
    Path(__file__).resolve().parent / PREFIX / "extract_source_bundle.py"))).resolve()
SCHEMA = "hive.multilingual-catalog-source-bundle.v1"
SPEC = importlib.util.spec_from_file_location("catalog_bundle_under_test", SCRIPT)
EXTRACTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXTRACTOR)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ManifestShapeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle"
        self.bundle.mkdir()
        self.destination = self.root / "destination"
        self.destination.mkdir()
        self.sentinel = self.destination / "untouched.txt"
        self.sentinel.write_bytes(b"existing unrelated data\n")
        self.files = {"sample.txt": (b"synthetic catalog fixture\n", 0o644),
                      "run.py": (b"print('fixture')\n", 0o755),
                      "empty.txt": (b"", 0o644)}
        self.manifest = self.build_bundle(self.files)

    def build_bundle(self, files):
        stream = io.BytesIO()
        members = []
        with tarfile.open(fileobj=stream, mode="w:xz") as package:
            for name, (data, mode) in files.items():
                member = tarfile.TarInfo((PREFIX / name).as_posix())
                member.size, member.mode, member.mtime = len(data), mode, 0
                package.addfile(member, io.BytesIO(data))
                members.append({"path": name, "bytes": len(data), "sha256": digest(data)})
        archive = stream.getvalue()
        encoded = base64.b64encode(archive)
        split = len(encoded) // 2
        parts = []
        for index, data in enumerate((encoded[:split], encoded[split:])):
            path = f"source.tar.xz.b64.part-{index:02d}"
            (self.bundle / path).write_bytes(data)
            parts.append({"path": path, "bytes": len(data), "sha256": digest(data)})
        return {"schema": SCHEMA, "archive_bytes": len(archive),
                "archive_sha256": digest(archive), "parts": parts, "members": members}

    def run_cli(self, manifest=None, *, raw=None):
        path = self.bundle / "BUNDLE.json"
        if raw is not None:
            path.write_bytes(raw)
        else:
            path.write_text(json.dumps(self.manifest if manifest is None else manifest), encoding="utf-8")
        argv = [str(SCRIPT), "--bundle-dir", str(self.bundle),
                "--destination", str(self.destination)]
        stdout, stderr = io.StringIO(), io.StringIO()
        # Exercise real argparse + file/tar operations without starting a Python
        # process for every malformed field. Separate smoke tests invoke the OS CLI.
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = EXTRACTOR.main()
            except SystemExit as exc:
                if isinstance(exc.code, int) or exc.code is None:
                    code = exc.code or 0
                else:
                    print(exc.code, file=sys.stderr)
                    code = 1
            except Exception:
                traceback.print_exc()
                code = 1
        return subprocess.CompletedProcess(argv, code, stdout.getvalue(), stderr.getvalue())

    def assert_no_install(self):
        self.assertFalse((self.destination / PREFIX).exists())
        self.assertEqual(self.sentinel.read_bytes(), b"existing unrelated data\n")

    def assert_invalid(self, manifest, label, *, raw=None):
        result = self.run_cli(manifest, raw=raw)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("invalid bundle manifest:", result.stderr)
        self.assertIn(label, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assert_no_install()

    def test_valid_bundle_extracts_exact_bytes_modes_and_json_receipt(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt, {"status": "extracted", "archive_sha256": self.manifest["archive_sha256"],
                                  "member_count": len(self.files), "destination": str(self.destination / PREFIX)})
        for name, (data, mode) in self.files.items():
            path = self.destination / PREFIX / name
            self.assertEqual(path.read_bytes(), data)
            if os.name != "nt":
                self.assertEqual(path.stat().st_mode & 0o777, mode)
        self.assertEqual(self.sentinel.read_bytes(), b"existing unrelated data\n")

    def test_valid_unicode_and_zero_byte_files(self):
        self.files = {"café.txt": ("Español — catálogo\n".encode(), 0o644), "zero.txt": (b"", 0o644)}
        self.manifest = self.build_bundle(self.files)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name, (data, _) in self.files.items():
            self.assertEqual((self.destination / PREFIX / name).read_bytes(), data)

    def test_unknown_metadata_is_preserved_and_ignored(self):
        self.manifest["future_metadata"] = {"note": "not an extraction field"}
        self.manifest["members"][0]["source_note"] = "retained fixture"
        self.assertEqual(self.run_cli().returncode, 0)

    def test_empty_member_bundle_keeps_existing_behavior(self):
        self.manifest = self.build_bundle({})
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["member_count"], 0)
        self.assert_no_install()

    def test_existing_file_refusal_is_unchanged(self):
        first = self.run_cli()
        self.assertEqual(first.returncode, 0, first.stderr)
        target = self.destination / PREFIX / "sample.txt"
        target.write_bytes(b"caller changed this\n")
        again = self.run_cli()
        self.assertNotEqual(again.returncode, 0)
        self.assertIn("refusing to replace existing path:", again.stderr)
        self.assertEqual(target.read_bytes(), b"caller changed this\n")

    def test_part_digest_mismatch_is_unchanged(self):
        path = self.bundle / self.manifest["parts"][0]["path"]
        path.write_bytes(path.read_bytes() + b"x")
        result = self.run_cli()
        self.assertIn("bundle part mismatch:", result.stderr)
        self.assertNotEqual(result.returncode, 0)
        self.assert_no_install()

    def test_archive_digest_mismatch_is_unchanged(self):
        self.manifest["archive_sha256"] = "0" * 64
        result = self.run_cli()
        self.assertIn("reconstructed archive does not match BUNDLE.json", result.stderr)
        self.assertNotEqual(result.returncode, 0)
        self.assert_no_install()

    def test_member_digest_mismatch_is_unchanged(self):
        self.manifest["members"][0]["sha256"] = "0" * 64
        result = self.run_cli()
        self.assertIn("archive member mismatch:", result.stderr)
        self.assertNotEqual(result.returncode, 0)
        self.assert_no_install()

    def test_unsupported_schema_diagnostic_is_unchanged(self):
        self.manifest["schema"] = "unsupported"
        result = self.run_cli()
        self.assertEqual(result.stderr.strip(), "unsupported bundle manifest schema")
        self.assertNotEqual(result.returncode, 0)
        self.assert_no_install()

    def test_non_object_manifest(self):
        for value in ([], None, True, 0, "text"):
            with self.subTest(value=value):
                self.assert_invalid({}, "expected an object", raw=json.dumps(value).encode())

    def test_missing_collection(self):
        for collection in ("parts", "members"):
            with self.subTest(collection=collection):
                manifest = copy.deepcopy(self.manifest)
                del manifest[collection]
                self.assert_invalid(manifest, collection)

    def test_non_array_collections(self):
        for collection in ("parts", "members"):
            for value in (None, {}, True, 0, "text"):
                with self.subTest(collection=collection, value=value):
                    manifest = copy.deepcopy(self.manifest)
                    manifest[collection] = value
                    self.assert_invalid(manifest, f"{collection} must be an array")

    def test_non_object_records(self):
        for collection in ("parts", "members"):
            for value in (None, [], True, 3, "text"):
                with self.subTest(collection=collection, value=value):
                    manifest = copy.deepcopy(self.manifest)
                    manifest[collection][0] = value
                    self.assert_invalid(manifest, f"{collection}[0] must be an object")

    def test_missing_record_fields(self):
        for collection in ("parts", "members"):
            for field in ("path", "bytes", "sha256"):
                with self.subTest(collection=collection, field=field):
                    manifest = copy.deepcopy(self.manifest)
                    del manifest[collection][0][field]
                    self.assert_invalid(manifest, f"{collection}[0].{field}")

    def test_path_field_shapes(self):
        for collection in ("parts", "members"):
            for value in (None, True, 12, [], {}, ""):
                with self.subTest(collection=collection, value=value):
                    manifest = copy.deepcopy(self.manifest)
                    manifest[collection][0]["path"] = value
                    self.assert_invalid(manifest, f"{collection}[0].path")

    def test_byte_count_shapes_and_boolean_exclusion(self):
        for collection in (None, "parts", "members"):
            for value in (None, True, False, -1, 1.5, "1", [], {}):
                with self.subTest(collection=collection, value=value):
                    manifest = copy.deepcopy(self.manifest)
                    label = "archive_bytes" if collection is None else f"{collection}[0].bytes"
                    if collection is None:
                        manifest["archive_bytes"] = value
                    else:
                        manifest[collection][0]["bytes"] = value
                    self.assert_invalid(manifest, label)

    def test_digest_field_shapes(self):
        for collection in (None, "parts", "members"):
            for value in (None, True, 3, [], {}, "", "f" * 63, "G" * 64, "F" * 64):
                with self.subTest(collection=collection, value=value):
                    manifest = copy.deepcopy(self.manifest)
                    label = "archive_sha256" if collection is None else f"{collection}[0].sha256"
                    if collection is None:
                        manifest["archive_sha256"] = value
                    else:
                        manifest[collection][0]["sha256"] = value
                    self.assert_invalid(manifest, label)

    def test_missing_archive_fields(self):
        for field in ("archive_bytes", "archive_sha256"):
            with self.subTest(field=field):
                manifest = copy.deepcopy(self.manifest)
                del manifest[field]
                self.assert_invalid(manifest, field)

    def test_invalid_json_is_a_manifest_error(self):
        self.assert_invalid({}, "invalid bundle manifest:", raw=b'{"schema":')

    def test_non_utf8_json_is_a_manifest_error(self):
        self.assert_invalid({}, "invalid bundle manifest:", raw=b'\xff\xfe')

    def test_subprocess_extracts_valid_bundle(self):
        (self.bundle / "BUNDLE.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", str(SCRIPT),
                                 "--bundle-dir", str(self.bundle),
                                 "--destination", str(self.destination)],
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["member_count"], len(self.files))
        for name, (data, _) in self.files.items():
            self.assertEqual((self.destination / PREFIX / name).read_bytes(), data)

    def test_subprocess_rejects_root_array_cleanly(self):
        (self.bundle / "BUNDLE.json").write_text("[]", encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", str(SCRIPT),
                                 "--bundle-dir", str(self.bundle),
                                 "--destination", str(self.destination)],
                                text=True, capture_output=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr.strip(), "invalid bundle manifest: expected an object")
        self.assert_no_install()

    def test_missing_manifest_is_a_manifest_error(self):
        result = subprocess.run([sys.executable, "-B", str(SCRIPT),
                                 "--bundle-dir", str(self.bundle),
                                 "--destination", str(self.destination)],
                                text=True, capture_output=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid bundle manifest:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assert_no_install()


if __name__ == "__main__":
    unittest.main(verbosity=2)
