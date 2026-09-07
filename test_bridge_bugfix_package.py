"""Focused offline tests for the actual site packager; no host deployment."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "host" / "package_bugfix_site.py"
SPEC = importlib.util.spec_from_file_location("bridge_package", SCRIPT)
PACKAGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGER)


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.source = self.root / PACKAGER.SOURCE_PATH
        self.source.parent.mkdir(parents=True)
        self.payload = '<!doctype html>\r\n<html lang="en">A → B 🌍</html>\n'.encode("utf-8")
        self.source.write_bytes(self.payload)
        self.output = Path(self.temp.name) / "output"

    def test_archive_contains_only_index_at_webroot(self):
        (self.source.parent / "private-notes.md").write_text("do not publish")
        (self.root / ".env").write_text("fixture-not-a-real-secret")
        (self.root / "customer.csv").write_text("fixture")
        result = PACKAGER.build_package(self.root, self.output)
        with zipfile.ZipFile(self.output / PACKAGER.ARCHIVE_NAME) as archive:
            self.assertEqual(archive.namelist(), ["index.html"])
            self.assertEqual(archive.read("index.html"), self.payload)
        self.assertEqual(result["archive_members"], ["index.html"])

    def test_receipt_is_outside_the_upload_archive(self):
        result = PACKAGER.build_package(self.root, self.output)
        receipt = json.loads((self.output / PACKAGER.RECEIPT_NAME).read_text())
        self.assertEqual(result, receipt)
        self.assertFalse(receipt["deployment_performed"])
        self.assertEqual(set(path.name for path in self.output.iterdir()),
                         {PACKAGER.ARCHIVE_NAME, PACKAGER.RECEIPT_NAME})

    def test_source_hashes_match_preserved_bytes(self):
        result = PACKAGER.build_package(self.root, self.output)
        blob = b"blob " + str(len(self.payload)).encode() + b"\0" + self.payload
        self.assertEqual(result["source_sha256"], hashlib.sha256(self.payload).hexdigest())
        self.assertEqual(result["source_git_blob_sha1"], hashlib.sha1(blob).hexdigest())
        self.assertEqual(result["source_bytes"], len(self.payload))

    def test_archive_hash_matches_written_archive(self):
        result = PACKAGER.build_package(self.root, self.output)
        archive = (self.output / PACKAGER.ARCHIVE_NAME).read_bytes()
        self.assertEqual(result["archive_sha256"], hashlib.sha256(archive).hexdigest())
        self.assertEqual(result["archive_bytes"], len(archive))

    def test_output_is_reproducible_despite_mtime(self):
        first = PACKAGER.build_package(self.root, self.output)
        os.utime(self.source, (1234567890, 1234567890))
        other = self.output.with_name("other")
        second = PACKAGER.build_package(self.root, other)
        self.assertEqual(first, second)
        for name in (PACKAGER.ARCHIVE_NAME, PACKAGER.RECEIPT_NAME):
            self.assertEqual((self.output / name).read_bytes(), (other / name).read_bytes())

    def test_existing_directory_is_not_modified(self):
        self.output.mkdir()
        marker = self.output / PACKAGER.ARCHIVE_NAME
        marker.write_bytes(b"existing artifact")
        with self.assertRaises(FileExistsError):
            PACKAGER.build_package(self.root, self.output)
        self.assertEqual(marker.read_bytes(), b"existing artifact")
        self.assertEqual(list(self.output.iterdir()), [marker])

    def test_missing_source_does_not_create_output(self):
        self.source.unlink()
        with self.assertRaises(FileNotFoundError):
            PACKAGER.build_package(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_invalid_utf8_does_not_create_output(self):
        self.source.write_bytes(b"<!doctype html>\xff")
        with self.assertRaises(UnicodeError):
            PACKAGER.build_package(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_non_html_does_not_create_output(self):
        self.source.write_text("wrong file")
        with self.assertRaises(ValueError):
            PACKAGER.build_package(self.root, self.output)
        self.assertFalse(self.output.exists())

    @unittest.skipIf(os.name == "nt", "Symlink creation may require Windows privileges")
    def test_symlink_is_not_followed(self):
        private = Path(self.temp.name) / "private.html"
        private.write_bytes(self.payload)
        self.source.unlink()
        self.source.symlink_to(private)
        with self.assertRaises(ValueError):
            PACKAGER.build_package(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_cli_packages_the_requested_repository(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", str(self.root), "--output", str(self.output)],
            check=True, capture_output=True, text=True, timeout=10,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["source_sha256"], hashlib.sha256(self.payload).hexdigest())
        self.assertFalse(result["deployment_performed"])

    def test_real_page_roundtrip_without_transformation(self):
        actual = (ROOT / PACKAGER.SOURCE_PATH).read_bytes()
        result = PACKAGER.build_package(ROOT, self.output)
        with zipfile.ZipFile(self.output / PACKAGER.ARCHIVE_NAME) as archive:
            self.assertEqual(archive.read("index.html"), actual)
        self.assertEqual(result["source_sha256"], hashlib.sha256(actual).hexdigest())


if __name__ == "__main__":
    unittest.main()
