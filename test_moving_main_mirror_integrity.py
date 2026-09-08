#!/usr/bin/env python3
"""Real-file and Git regressions for mirror path and cursor-state integrity."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from host import moving_main_mirror as mirror


class MirrorIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="mirror-integrity-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.output = self.root / "output"
        self.git("init", "-b", "main")
        self.git("config", "user.name", "mirror-test")
        self.git("config", "user.email", "mirror-test@example.invalid")
        self.first = self.commit("first\n")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.source), *args],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    def commit(self, text: str) -> str:
        (self.source / "fresh.md").write_text(text, encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "fixture")
        return self.git("rev-parse", "HEAD")

    def run_sync(self, *, live: bool = False) -> dict:
        # Source, object reads, ancestry, state files and hashing remain real.
        with contextlib.redirect_stdout(io.StringIO()):
            return mirror.sync(self.source, live=live, output=self.output)

    @property
    def checkpoint(self) -> Path:
        return self.output / "cursor-state.json"

    @property
    def diagnostic(self) -> Path:
        return self.output / "last.json"

    def accepted_pair(self) -> tuple[str, bytes]:
        self.assertEqual(self.run_sync()["cursor"]["seq"], 1)
        newest = self.commit("second\n")
        self.assertEqual(self.run_sync()["cursor"]["seq"], 2)
        return newest, self.checkpoint.read_bytes()

    def assert_row(self, spelling: str, expected_path: str, data: bytes, sha: str | None = None) -> None:
        self.assertEqual(mirror.read_paths(self.source, [spelling], sha=sha), [{
            "path": expected_path, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }])

    def test_dotfile_is_not_replaced_by_undotted_sibling(self) -> None:
        (self.source / ".settings").write_bytes(b"hidden\x00\xff\n")
        (self.source / "settings").write_bytes(b"different\n")
        self.assert_row(".settings", ".settings", b"hidden\x00\xff\n")

    def test_hidden_directory_and_repeated_dot_slash(self) -> None:
        (self.source / ".metadata").mkdir()
        (self.source / ".metadata" / "record.json").write_bytes(b"{}\n")
        self.assert_row("././.metadata/record.json", ".metadata/record.json", b"{}\n")

    def test_windows_separator_spelling_preserves_hidden_name(self) -> None:
        (self.source / ".metadata").mkdir()
        (self.source / ".metadata" / "record.json").write_bytes(b"[]\n")
        self.assert_row(".\\.\\.metadata\\record.json", ".metadata/record.json", b"[]\n")

    def test_multiple_leading_dots_are_filename_bytes(self) -> None:
        (self.source / "...notes").write_bytes(b"three dots\n")
        self.assert_row("./...notes", "...notes", b"three dots\n")

    def test_pinned_hidden_git_blob_ignores_dirty_worktree(self) -> None:
        payload = b"committed\x00\xfe\n"
        (self.source / ".settings").write_bytes(payload)
        (self.source / "settings").write_bytes(b"undotted\n")
        pinned = self.commit("pinned\n")
        (self.source / ".settings").write_bytes(b"uncommitted\n")
        self.assert_row("./.settings", ".settings", payload, sha=pinned)

    def test_ordinary_paths_and_missing_file_behavior_are_unchanged(self) -> None:
        self.assert_row("././fresh.md", "fresh.md", b"first\n")
        self.assertEqual(
            mirror.read_paths(self.source, ["missing.md", "fresh.md"]),
            mirror.read_paths(self.source, ["fresh.md"]),
        )
        with self.assertRaises(mirror.MirrorError):
            mirror.read_paths(self.source, ["missing.md"])

    def test_stale_retry_keeps_exact_accepted_checkpoint(self) -> None:
        newest, accepted = self.accepted_pair()
        self.git("checkout", "--detach", self.first)
        for attempt in range(2):
            with self.subTest(attempt=attempt):
                result = self.run_sync()
                self.assertEqual(result["state"], "STALE")
                self.assertEqual(result["cursor"]["seq"], 2)
                self.assertEqual(result["cursor"]["head_sha"], newest)
                self.assertEqual(self.checkpoint.read_bytes(), accepted)

    def test_stale_diagnostic_uses_last_json(self) -> None:
        newest, _ = self.accepted_pair()
        self.git("checkout", "--detach", self.first)
        result = self.run_sync()
        self.assertEqual(json.loads(self.diagnostic.read_text()), result)
        self.assertEqual(result["state"], "STALE")
        self.assertEqual(result["snapshot"]["head_sha"], self.first)
        self.assertEqual(result["cursor"]["head_sha"], newest)
        self.assertEqual(result["receipts"], [])

    def test_return_to_accepted_head_after_stale_is_idempotent(self) -> None:
        newest, _ = self.accepted_pair()
        self.git("checkout", "--detach", self.first)
        self.assertEqual(self.run_sync()["state"], "STALE")
        self.git("checkout", "--detach", newest)
        result = self.run_sync()
        self.assertEqual(result["state"], "IDEMPOTENT")
        self.assertEqual(result["cursor"]["seq"], 2)

    def test_new_descendant_after_stale_continues_sequence(self) -> None:
        self.accepted_pair()
        self.git("checkout", "--detach", self.first)
        self.run_sync()
        self.git("checkout", "main")
        newest = self.commit("third\n")
        result = self.run_sync()
        self.assertEqual(result["state"], "ADVANCE")
        self.assertEqual(result["cursor"]["seq"], 3)
        self.assertEqual(result["cursor"]["head_sha"], newest)

    def test_conflict_retry_keeps_checkpoint_and_records_diagnostic(self) -> None:
        newest, accepted = self.accepted_pair()
        self.git("checkout", "-b", "divergent", self.first)
        divergent = self.commit("different branch\n")
        for attempt in range(2):
            with self.subTest(attempt=attempt):
                result = self.run_sync()
                self.assertEqual(result["state"], "CONFLICT")
                self.assertEqual(result["cursor"]["head_sha"], newest)
                self.assertEqual(result["snapshot"]["head_sha"], divergent)
                self.assertEqual(result["cursor"]["conflicts"][0]["path"], "fresh.md")
                self.assertEqual(self.checkpoint.read_bytes(), accepted)
                self.assertEqual(json.loads(self.diagnostic.read_text()), result)

    def test_corrupt_digest_retry_preserves_state_for_diagnosis(self) -> None:
        self.run_sync()
        previous = json.loads(self.checkpoint.read_text())
        previous["digest"] = "f" * 64
        stored = (json.dumps(previous, indent=2, sort_keys=True) + "\n").encode()
        self.checkpoint.write_bytes(stored)
        for attempt in range(2):
            with self.subTest(attempt=attempt):
                result = self.run_sync()
                self.assertEqual(result["state"], "CORRUPT")
                self.assertEqual(self.checkpoint.read_bytes(), stored)
                self.assertEqual(json.loads(self.diagnostic.read_text()), result)

    def test_stale_live_request_calls_no_provider(self) -> None:
        _, accepted = self.accepted_pair()
        self.git("checkout", "--detach", self.first)
        with patch.object(mirror, "http_call", side_effect=AssertionError("unexpected network call")) as http:
            result = self.run_sync(live=True)
        self.assertEqual(result["state"], "STALE")
        http.assert_not_called()
        self.assertEqual(self.checkpoint.read_bytes(), accepted)

    def test_dry_cli_stale_retry_preserves_sequence(self) -> None:
        self.accepted_pair()
        self.git("checkout", "--detach", self.first)
        command = [sys.executable, str(Path(mirror.__file__).resolve()), "sync",
                   "--source", str(self.source), "--output", str(self.output)]
        for attempt in range(2):
            with self.subTest(attempt=attempt):
                completed = subprocess.run(command, capture_output=True, text=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(json.loads(self.diagnostic.read_text())["state"], "STALE")
                saved = json.loads(self.checkpoint.read_text())
                self.assertEqual(saved["seq"], 2)
                self.assertEqual(saved["head_sha"], self.git("rev-parse", "main"))


if __name__ == "__main__":
    unittest.main()
