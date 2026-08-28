#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from host import repo_backup


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


class RepoBackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        git(self.source, "init", "-b", "main")
        git(self.source, "config", "user.email", "backup-test@example.invalid")
        git(self.source, "config", "user.name", "backup-test")
        (self.source / "proof.txt").write_text("open door\n", encoding="utf-8")
        git(self.source, "add", "proof.txt")
        git(self.source, "commit", "-m", "proof")
        git(self.source, "tag", "proof-v1")
        self.output = self.root / "backup"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_snapshot_verify_restore_round_trip(self) -> None:
        manifest_path = repo_backup.snapshot(self.source, self.output)
        verified = repo_backup.verify(manifest_path)
        self.assertEqual(verified["state"], "VERIFIED")
        self.assertGreaterEqual(verified["refs"], 2)

        target = self.root / "restored"
        restored = repo_backup.restore(manifest_path, target)
        self.assertEqual(restored["state"], "RESTORED")
        self.assertEqual(restored["restored_head_sha"], git(self.source, "rev-parse", "HEAD"))
        self.assertEqual(
            (target / "proof.txt").read_text(encoding="utf-8"),
            "open door\n",
        )

    def test_manifest_and_bundle_are_exact_and_tamper_evident(self) -> None:
        manifest_path = repo_backup.snapshot(self.source, self.output)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], repo_backup.SCHEMA_VERSION)
        bundle = manifest_path.parent / manifest["bundle"]
        with bundle.open("ab") as handle:
            handle.write(b"tamper")
        with self.assertRaises(repo_backup.BackupError):
            repo_backup.verify(manifest_path)

    def test_restore_refuses_existing_target(self) -> None:
        manifest_path = repo_backup.snapshot(self.source, self.output)
        target = self.root / "exists"
        target.mkdir()
        with self.assertRaises(repo_backup.BackupError):
            repo_backup.restore(manifest_path, target)


if __name__ == "__main__":
    unittest.main()
