#!/usr/bin/env python3
"""Keep backup CI independent of unrelated Windows-incompatible tree paths."""
from __future__ import annotations

from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
WORKFLOW = ROOT / ".github" / "workflows" / "lattice-delta-backup-refs.yml"


class BackupWorkflowSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def archive_paths(self) -> list[str]:
        logical_lines = self.workflow.replace("\\\n", " ")
        command = re.search(r"^\s+git archive (.+)$", logical_lines, re.MULTILINE)
        self.assertIsNotNone(command, "source job must archive the checked-out commit")
        args = shlex.split(command.group(1))
        self.assertIn("--format=tar", args)
        self.assertEqual(args[args.index("--") - 1], "HEAD")
        return args[args.index("--") + 1:]

    def test_matrix_uses_same_source_without_windows_checkout(self) -> None:
        self.assertIn("  source-snapshot:\n", self.workflow)
        snapshot, matrix = self.workflow.split("  restore-regressions:\n", 1)
        self.assertIn("runs-on: ubuntu-24.04", snapshot)
        self.assertIn("actions/checkout@v4", snapshot)
        self.assertIn("persist-credentials: false", snapshot)
        self.assertIn("actions/upload-artifact@v4", snapshot)
        self.assertIn("if-no-files-found: error", snapshot)
        self.assertIn("needs: source-snapshot", matrix)
        self.assertIn("os: [ubuntu-24.04, windows-latest]", matrix)
        self.assertIn("fail-fast: false", matrix)
        self.assertIn("actions/download-artifact@v4", matrix)
        self.assertNotIn("actions/checkout", matrix)
        self.assertIn('EXPECTED_SOURCE_COMMIT: ${{ github.sha }}', matrix)
        self.assertIn('filter="data"', matrix)
        self.assertNotIn("core.protectNTFS", self.workflow)
        self.assertNotIn("continue-on-error", self.workflow)

    def test_every_test_module_and_dependency_is_transferred(self) -> None:
        paths = self.archive_paths()
        command = re.search(r"run: python -m unittest -v (.+)", self.workflow)
        self.assertIsNotNone(command)
        modules = shlex.split(command.group(1))
        self.assertIn("test_repo_backup", modules)
        self.assertIn("test_repo_backup_refs", modules)
        self.assertIn("test_repo_backup_short_writes", modules)
        self.assertIn("test_repo_backup_manifest_encoding", modules)
        self.assertIn("test_backup_workflow_source_transfer", modules)
        for module in modules:
            self.assertIn(module + ".py", paths)
        for path in (
            "host/repo_backup.py", "open_door_guard.py", "AGENTS.md",
            "ground/BACKUP_OPEN_REPO.md", "backups/README.md",
            ".github/workflows/open-repo-backup.yml",
            ".github/workflows/lattice-delta-backup-refs.yml",
        ):
            self.assertIn(path, paths)
        self.assertEqual(len(paths), len(set(paths)))
        for path in paths:
            self.assertIn(f'      - "{path}"', self.workflow)
            self.assertIn(f"            /{path}\n", self.workflow)

    @staticmethod
    def git(repo: Path, *args: str, data: bytes | None = None) -> bytes:
        return subprocess.run(
            ["git", *args], cwd=repo, input=data, check=True, capture_output=True,
        ).stdout

    def test_archive_preserves_commit_bytes_and_excludes_incompatible_paths(self) -> None:
        paths = self.archive_paths()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            self.git(source, "init", "-b", "main")
            self.git(source, "config", "user.name", "backup-ci-test")
            self.git(source, "config", "user.email", "backup-ci-test@example.invalid")
            self.git(source, "config", "core.autocrlf", "false")
            expected = {}
            for index, name in enumerate(paths):
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                expected[name] = f"committed {index}: caf\u00e9\n".encode("utf-8")
                path.write_bytes(expected[name])
            self.git(source, "add", "--", *paths)
            self.git(source, "commit", "-m", "source fixture")
            # Build the unrelated invalid-on-Windows path as Git objects only;
            # never create that filename on either runner's filesystem.
            blob = self.git(source, "hash-object", "-w", "--stdin", data=b"unrelated\n").strip()
            tree = self.git(
                source, "mktree", "-z",
                data=b'100644 blob ' + blob + b'\t"2026-09-0.html\0',
            ).strip()
            entries = self.git(source, "ls-tree", "-z", "HEAD")
            root_tree = self.git(source, "mktree", "-z", data=entries + b"040000 tree " + tree + b"\td\0").strip()
            commit = self.git(source, "commit-tree", root_tree.decode(), "-p", "HEAD", "-m", "unrelated tree path").strip()
            self.git(source, "update-ref", "HEAD", commit.decode())
            tree_paths = self.git(source, "ls-tree", "-r", "--name-only", "-z", "HEAD")
            self.assertIn(b'd/"2026-09-0.html\0', tree_paths)
            # A dirty working copy must not substitute for the committed source.
            (source / paths[0]).write_bytes(b"uncommitted replacement\r\n")
            archive_path = root / "source.tar"
            self.git(source, "archive", "--format=tar", f"--output={archive_path}", "HEAD", "--", *paths)
            with tarfile.open(archive_path, "r:") as archive:
                actual = {member.name: archive.extractfile(member).read()
                          for member in archive.getmembers() if member.isfile()}
            self.assertEqual(actual, expected)
            self.assertNotIn('d/"2026-09-0.html', actual)
            self.assertNotIn(".git/config", actual)


if __name__ == "__main__":
    unittest.main()
