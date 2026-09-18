#!/usr/bin/env python3
"""Preserve arbitrary Git metadata and filename bytes in landed-work reports."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "host" / "landed_work_feed.py"
SPEC = importlib.util.spec_from_file_location("landed_work_feed_git_bytes_subject", SOURCE)
assert SPEC and SPEC.loader
feed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(feed)


class GitBytePreservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "config", "user.email", "fixture@example.invalid"],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=self.repo, check=True)

    def git_text(self, *args: str) -> str:
        return subprocess.check_output(
            ["git", *args], cwd=self.repo, text=True, stderr=subprocess.PIPE
        ).strip()

    def normal_commit(self, title: str, filename: str = "base.txt") -> str:
        path = self.repo / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(title, encoding="utf-8")
        self.git_text("add", "--", filename)
        self.git_text("commit", "-qm", title)
        return self.git_text("rev-parse", "HEAD")

    def raw_commit(
        self,
        *,
        author: bytes,
        subject: bytes,
        filename: bytes,
        parent: str | None = None,
    ) -> str:
        repo_bytes = os.fsencode(self.repo)
        path = repo_bytes + b"/" + filename
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            os.write(fd, b"payload")
        finally:
            os.close(fd)
        subprocess.run(
            [b"git", b"add", b"--all"], cwd=repo_bytes, check=True, stderr=subprocess.PIPE
        )
        tree = subprocess.check_output([b"git", b"write-tree"], cwd=repo_bytes).strip()
        stamp = str(int(time.time())).encode("ascii")
        lines = [b"tree " + tree]
        if parent is not None:
            lines.append(b"parent " + parent.encode("ascii"))
        lines.extend(
            [
                b"author " + author + b" <author@example.invalid> " + stamp + b" +0000",
                b"committer Fixture <fixture@example.invalid> " + stamp + b" +0000",
                b"",
                subject,
            ]
        )
        raw = b"\n".join(lines) + b"\n"
        sha = subprocess.check_output(
            [b"git", b"hash-object", b"-t", b"commit", b"-w", b"--stdin"],
            cwd=repo_bytes,
            input=raw,
        ).strip().decode("ascii")
        subprocess.run(
            ["git", "update-ref", "refs/heads/main", sha], cwd=self.repo, check=True
        )
        return sha

    @staticmethod
    def original_bytes(text: str) -> bytes:
        return text.encode("utf-8", "surrogateescape")

    def test_non_utf8_author_subject_and_filename_round_trip(self) -> None:
        parent = self.normal_commit("Initial delivery")
        author = b"Astra-\xff-Stream"
        subject = b"Deliver \xfe evidence (#421)"
        filename = b"artifact-\xfd.bin"
        sha = self.raw_commit(
            author=author, subject=subject, filename=filename, parent=parent
        )

        row = feed.recent_merges(1, self.repo)[0]
        self.assertEqual(row["sha"], sha)
        self.assertEqual(self.original_bytes(row["author"]), author)
        self.assertEqual(self.original_bytes(row["title"]), subject)
        self.assertEqual([self.original_bytes(path) for path in row["paths"]], [filename])
        self.assertEqual(row["pr"], 421)

    def test_formatted_line_is_ascii_safe_and_byte_explicit(self) -> None:
        parent = self.normal_commit("Initial delivery")
        row_sha = self.raw_commit(
            author=b"Author-\xff",
            subject=b"Subject-\xfe (#422)",
            filename=b"name-\xfd.txt",
            parent=parent,
        )
        row = feed.recent_merges(1, self.repo)[0]
        line = feed.format_line(row)
        self.assertEqual(row["sha"], row_sha)
        line.encode("ascii")
        self.assertIn("\\udcff", line)
        self.assertIn("\\udcfe", line)
        self.assertIn("\\udcfd", line)
        self.assertNotIn("\udcff", line)
        self.assertEqual(len(line.splitlines()), 1)

    def test_cli_emits_valid_ascii_json_without_losing_original_bytes(self) -> None:
        parent = self.normal_commit("Initial delivery")
        sha = self.raw_commit(
            author=b"CLI-\xff",
            subject=b"CLI subject \xfe (#423)",
            filename=b"cli-\xfd.dat",
            parent=parent,
        )
        (self.repo / "host").mkdir()
        shutil.copyfile(SOURCE, self.repo / "host" / SOURCE.name)
        (self.repo / "ground").mkdir()
        catalog = {
            "id": "git-bytes-fixture",
            "ride": "commons-ship-enforcer",
            "headless_enforcer": "CLAUDE_TAKING",
            "repos_named_here": 6,
        }
        (self.repo / "ground" / "LANDED_WORK_FEED.json").write_text(
            json.dumps(catalog), encoding="utf-8"
        )
        proc = subprocess.run(
            [sys.executable, str(self.repo / "host" / SOURCE.name), "--json", "--limit", "1"],
            cwd=self.repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        proc.stdout.decode("ascii")
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["merges"][0]["sha"], sha)
        self.assertEqual(
            packet["merges"][0]["author"].encode("utf-8", "surrogateescape"),
            b"CLI-\xff",
        )
        self.assertEqual(
            packet["merges"][0]["title"].encode("utf-8", "surrogateescape"),
            b"CLI subject \xfe (#423)",
        )
        self.assertEqual(
            packet["merges"][0]["paths"][0].encode("utf-8", "surrogateescape"),
            b"cli-\xfd.dat",
        )

    def test_valid_unicode_and_normal_line_remain_unchanged(self) -> None:
        sha = self.normal_commit("Implement café support (#424)", "récolte.txt")
        row = feed.recent_merges(1, self.repo)[0]
        self.assertEqual(row["sha"], sha)
        self.assertEqual(row["author"], "Fixture")
        self.assertEqual(row["title"], "Implement café support (#424)")
        self.assertEqual(row["paths"], ["récolte.txt"])
        self.assertEqual(
            feed.format_line(row),
            "woahwhattheheck/commons #424 "
            + sha[:9]
            + " Implement café support (#424) harness=fixture paths=récolte.txt",
        )

    def test_git_helper_keeps_existing_error_semantics(self) -> None:
        with self.assertRaises(subprocess.CalledProcessError):
            feed.git(["rev-parse", "refs/heads/does-not-exist"], self.repo)

    def test_line_label_quotes_all_surrogates_but_not_unicode(self) -> None:
        self.assertEqual(feed._line_label("café"), "café")
        for codepoint in (0xD800, 0xDC80, 0xDCFF, 0xDFFF):
            text = "x" + chr(codepoint) + "y"
            label = feed._line_label(text)
            label.encode("ascii")
            self.assertEqual(json.loads(label), text)


if __name__ == "__main__":
    unittest.main()
