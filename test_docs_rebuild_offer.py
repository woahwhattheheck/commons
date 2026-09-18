"""Real archive, CLI, content, and failure-path checks for the offer packet."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from host.package_docs_rebuild_offer import DOCUMENTS, SOURCE, build_package

ROOT = Path(__file__).resolve().parent


class DocsRebuildOfferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        shutil.copytree(SOURCE, self.source)
        self.output = self.root / "offer.zip"

    def test_archive_contains_exact_documents_and_matching_manifest(self):
        result = build_package(self.source, self.output)
        with zipfile.ZipFile(self.output) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(archive.namelist(), sorted((*DOCUMENTS, "manifest.json")))
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["offer_id"], "docs-rebuild-repair-v1")
            self.assertEqual(manifest["audience"], "internal_sales_enablement")
            self.assertEqual(set(manifest["files"]), set(DOCUMENTS))
            for name in DOCUMENTS:
                data = (self.source / name).read_bytes()
                self.assertEqual(archive.read(name), data)
                self.assertEqual(manifest["files"][name], {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
                self.assertEqual(archive.getinfo(name).date_time, (1980, 1, 1, 0, 0, 0))
        self.assertEqual(result["bytes"], self.output.stat().st_size)
        self.assertEqual(result["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())

    def test_repeat_package_ignores_source_mtime_and_extra_files(self):
        build_package(self.source, self.output)
        for name in DOCUMENTS:
            os.utime(self.source / name, (1, 1))
        (self.source / "not-for-distribution.txt").write_text("private test fixture", encoding="utf-8")
        other = self.root / "second.zip"
        build_package(self.source, other)
        self.assertEqual(self.output.read_bytes(), other.read_bytes())

    def test_changed_document_changes_payload_and_manifest(self):
        build_package(self.source, self.output)
        with zipfile.ZipFile(self.output) as archive:
            old = json.loads(archive.read("manifest.json"))
        path = self.source / "offer.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nRevision fixture.\n", encoding="utf-8")
        other = self.root / "changed.zip"
        build_package(self.source, other)
        with zipfile.ZipFile(other) as archive:
            new = json.loads(archive.read("manifest.json"))
        self.assertNotEqual(old["files"]["offer.md"], new["files"]["offer.md"])
        self.assertEqual(old["files"]["delivery-checklist.md"], new["files"]["delivery-checklist.md"])
        self.assertNotEqual(self.output.read_bytes(), other.read_bytes())

    def test_missing_document_creates_no_archive(self):
        (self.source / DOCUMENTS[1]).unlink()
        with self.assertRaises(FileNotFoundError):
            build_package(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_non_utf8_document_creates_no_archive(self):
        (self.source / DOCUMENTS[0]).write_bytes(b"\xff")
        with self.assertRaises(UnicodeDecodeError):
            build_package(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_empty_document_creates_no_archive(self):
        (self.source / DOCUMENTS[0]).write_text(" \n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "empty"):
            build_package(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_symlink_is_not_packaged(self):
        path = self.source / DOCUMENTS[0]
        path.unlink()
        try:
            path.symlink_to(self.source / DOCUMENTS[1])
        except (OSError, NotImplementedError):
            self.skipTest("This platform cannot create symlinks")
        with self.assertRaisesRegex(ValueError, "regular file"):
            build_package(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_output_is_preserved(self):
        self.output.write_bytes(b"existing user file")
        with self.assertRaises(FileExistsError):
            build_package(self.source, self.output)
        self.assertEqual(self.output.read_bytes(), b"existing user file")

    def test_cli_works_outside_repository_and_reports_duplicate_output(self):
        cmd = [sys.executable, str(ROOT / "host/package_docs_rebuild_offer.py"), "--output", str(self.output)]
        result = subprocess.run(cmd, cwd=self.root, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())
        previous = self.output.read_bytes()
        duplicate = subprocess.run(cmd, cwd=self.root, text=True, capture_output=True, check=False)
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn("Package not created", duplicate.stderr)
        self.assertEqual(self.output.read_bytes(), previous)

    def test_offer_has_complete_scope_and_truthful_evidence_boundaries(self):
        offer = (SOURCE / "offer.md").read_text(encoding="utf-8")
        for section in ("Target customer and problem", "Deliverable and inclusions", "Exclusions and scope changes", "Required client inputs", "Objective acceptance criteria", "Timeline assumptions", "Price and next step", "Source-linked case study: links that survive regeneration", "Concise outreach message"):
            self.assertIn("## " + section, offer)
        self.assertEqual(len(re.findall(r"^\d+\. ", offer, flags=re.M)), 7)
        self.assertIn("Proposed fixed price: USD 450", offer)
        self.assertIn("internal owner-repository work, not an external client engagement", offer)
        self.assertIn("broader repository suite was not claimed green", offer)
        self.assertIn("c145b61171c90a72f54df9c2645c6a0088ee3d31/test_manual_tools_rebake.py", offer)
        self.assertNotRegex(offer, r"\b(?:TODO|TBD|PLACEHOLDER)\b")

    def test_outreach_has_no_storefront_links_or_subject_price(self):
        offer = (SOURCE / "offer.md").read_text(encoding="utf-8")
        outreach = offer.split("## Concise outreach message\n", 1)[1]
        subject = next(line for line in outreach.splitlines() if line.startswith("Subject:"))
        self.assertNotRegex(subject.lower(), r"price|payment|delivery|usd|\$")
        self.assertNotIn("http", outreach)
        self.assertIn("reply YES", outreach)

    def test_packaged_relative_links_resolve_inside_archive(self):
        for name in DOCUMENTS:
            text = (SOURCE / name).read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if "://" not in target and not target.startswith("#"):
                    self.assertIn(target.split("#", 1)[0], DOCUMENTS)


if __name__ == "__main__":
    unittest.main()
