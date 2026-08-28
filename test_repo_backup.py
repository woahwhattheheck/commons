#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import open_door_guard as guard
from host import repo_backup

ROOT = Path(__file__).resolve().parent


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def show_ref_head(repo: Path) -> list[dict[str, str]]:
    rows = []
    for line in git(repo, "show-ref", "--head").splitlines():
        sha, separator, ref = line.partition(" ")
        if separator:
            rows.append({"ref": ref.strip(), "sha": sha})
    return sorted(rows, key=lambda row: row["ref"])


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
        self.assertGreaterEqual(verified["refs"], 3)

        target = self.root / "restored"
        restored = repo_backup.restore(manifest_path, target)
        self.assertEqual(restored["state"], "RESTORED")
        self.assertEqual(restored["restored_head_sha"], git(self.source, "rev-parse", "HEAD"))
        self.assertEqual(
            (target / "proof.txt").read_text(encoding="utf-8"),
            "open door\n",
        )

    def test_inventory_includes_head_and_matches_source_show_ref(self) -> None:
        manifest_path = repo_backup.snapshot(self.source, self.output)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = show_ref_head(self.source)
        self.assertEqual(manifest["refs"], expected)
        self.assertTrue(any(row["ref"] == "HEAD" for row in manifest["refs"]))
        self.assertEqual(manifest["head_sha"], git(self.source, "rev-parse", "HEAD"))

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

    def test_cli_snapshot_verify_restore(self) -> None:
        tool = ROOT / "host" / "repo_backup.py"
        snap = subprocess.run(
            [
                sys.executable,
                str(tool),
                "snapshot",
                "--source",
                str(self.source),
                "--output-dir",
                str(self.output),
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        payload = json.loads(snap.stdout)
        self.assertEqual(payload["state"], "SNAPSHOT")
        manifest = Path(payload["manifest"])
        verify = subprocess.run(
            [sys.executable, str(tool), "verify", str(manifest)],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertEqual(json.loads(verify.stdout)["state"], "VERIFIED")
        target = self.root / "cli-restored"
        restore = subprocess.run(
            [sys.executable, str(tool), "restore", str(manifest), str(target)],
            check=True,
            text=True,
            capture_output=True,
        )
        restored = json.loads(restore.stdout)
        self.assertEqual(restored["state"], "RESTORED")
        self.assertEqual(restored["restored_head_sha"], git(self.source, "rev-parse", "HEAD"))

    def test_backup_law_is_prohibition_not_a_lock(self) -> None:
        paths = (
            ROOT / "AGENTS.md",
            ROOT / "ground" / "BACKUP_OPEN_REPO.md",
            ROOT / "backups" / "README.md",
            ROOT / "host" / "repo_backup.py",
            ROOT / "test_repo_backup.py",
        )
        lines = [
            guard.AddedLine(path.as_posix(), line_number, text)
            for path in paths
            for line_number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        ]
        self.assertEqual(guard.scan_added(lines), [])


if __name__ == "__main__":
    unittest.main()
