#!/usr/bin/env python3
"""Check feature-tracker path blob identity against real Git index objects."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from host import feature_tracker as ft


class TreeBlobSymlinks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="commons-ft-links-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "feature-tracker-test")
        self.git("config", "user.email", "feature-tracker@example.test")
        self.git("config", "core.symlinks", "true")

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.root), *args], stderr=subprocess.PIPE
        ).decode("ascii").strip()

    def stage_blob(self, name):
        self.git("add", "--", name)
        return self.git("rev-parse", ":" + name)

    def test_regular_file_keeps_its_git_blob(self):
        (self.root / "file.txt").write_bytes(b"regular contents\n")
        self.assertEqual(ft.tree_blob(str(self.root), "file.txt"), self.stage_blob("file.txt"))

    def test_file_symlink_uses_link_blob_not_referent(self):
        (self.root / "target.txt").write_bytes(b"not the symlink blob\n")
        (self.root / "link").symlink_to("target.txt")
        self.assertEqual(ft.tree_blob(str(self.root), "link"), self.stage_blob("link"))

    def test_untracked_dangling_symlink_has_a_blob(self):
        (self.root / "link").symlink_to("absent.txt")
        observed = ft.tree_blob(str(self.root), "link")
        self.assertEqual(observed, self.stage_blob("link"))

    def test_directory_symlink_has_its_own_blob(self):
        (self.root / "folder").mkdir()
        (self.root / "link").symlink_to("folder", target_is_directory=True)
        self.assertEqual(ft.tree_blob(str(self.root), "link"), self.stage_blob("link"))

    def test_changed_dangling_link_does_not_reuse_head_blob(self):
        link = self.root / "link"
        link.symlink_to("old-missing.txt")
        old = self.stage_blob("link")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "record link")
        link.unlink()
        link.symlink_to("new-missing.txt")
        observed = ft.tree_blob(str(self.root), "link")
        new = self.stage_blob("link")
        self.assertNotEqual(old, new)
        self.assertEqual(observed, new)

    def test_referent_edit_does_not_change_link_object(self):
        target = self.root / "target.txt"
        target.write_bytes(b"before\n")
        (self.root / "link").symlink_to("target.txt")
        expected = self.stage_blob("link")
        target.write_bytes(b"after\n")
        self.assertEqual(ft.tree_blob(str(self.root), "link"), expected)

    @unittest.skipUnless(os.name == "posix", "POSIX byte-valued symlink target")
    def test_non_utf8_target_bytes_match_git(self):
        os.symlink(b"target-\xff", os.fsencode(self.root / "link"))
        self.assertEqual(ft.tree_blob(str(self.root), "link"), self.stage_blob("link"))

    def test_missing_worktree_file_still_falls_back_to_head(self):
        path = self.root / "file.txt"
        path.write_bytes(b"sparse worktree fallback\n")
        expected = self.stage_blob("file.txt")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "record file")
        path.unlink()
        self.assertEqual(ft.tree_blob(str(self.root), "file.txt"), expected)

    def test_projection_consumes_link_blob_and_detects_retargeting(self):
        for name in ("first.txt", "second.txt"):
            (self.root / name).write_bytes(b"same target contents\n")
        link = self.root / "link"
        link.symlink_to("first.txt")
        blob = self.stage_blob("link")
        feature = {
            "schema": ft.SCHEMA_FEATURE, "id": "symlink-feature-20260908-01",
            "name": "Symlink fixture", "capability": "Test link blob projection",
            "owner_subsystem": "tests", "carrier": "test-fixture",
            "claimed_paths": ["link"], "test_paths": [],
            "public_entrypoint": "link", "dependencies": [], "resource_links": [],
            "next_gap": "Synthetic fixture only",
        }
        evidence = {
            "schema": ft.SCHEMA_EVIDENCE, "id": "symlink-evidence-20260908-01",
            "feature_id": feature["id"], "kind": "LIVE_MEASUREMENT",
            "sha": "a" * 40, "blob": blob, "path": "link",
            "url": "https://example.invalid/symlink-fixture",
        }
        for directory, record in ((ft.REGISTRY_DIR, feature), (ft.EVIDENCE_DIR, evidence)):
            folder = self.root / directory
            folder.mkdir(parents=True)
            (folder / (record["id"] + ".json")).write_text(json.dumps(record))
        self.assertEqual(ft.project(str(self.root))["features"][0]["live_status"], "LIVE")
        link.unlink()
        link.symlink_to("second.txt")
        self.assertEqual(ft.project(str(self.root))["features"][0]["live_status"], "DEGRADED")

    def test_sha256_repository_link_uses_its_object_format(self):
        root = self.root / "sha256-repo"
        result = subprocess.run(
            ["git", "init", "-q", "--object-format=sha256", str(root)],
            capture_output=True,
        )
        if result.returncode:
            self.skipTest("Git does not support SHA-256 repositories")
        (root / "link").symlink_to("missing.txt")
        subprocess.run(["git", "-C", str(root), "add", "--", "link"], check=True)
        expected = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", ":link"], text=True
        ).strip()
        self.assertEqual(len(expected), 64)
        self.assertEqual(ft.tree_blob(str(root), "link"), expected)

    def test_existing_invalid_path_behavior_is_unchanged(self):
        for rel in (None, "", "/absolute", "../outside", "dir/../file"):
            with self.subTest(rel=rel):
                self.assertEqual(ft.tree_blob(str(self.root), rel), "")


if __name__ == "__main__":
    unittest.main()
