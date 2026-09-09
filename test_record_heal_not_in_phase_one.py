#!/usr/bin/env python3
"""Healed p/*.html for records already on origin are bake, not phase-one source.

Measured 2026-09-09 commons-board run 34397160828: heal_missing_pages
synthesized 614 permalinks for md already on main. _record_paths treated
those html files as append-only source, the record commit became a 600-file
bake, and push_origin_main exhausted PUSH_DEADLINE_S with non-fast-forward,
stamping PUSH_FAIL on 40 new posts that never reached main.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest


def run(args, cwd, **kw):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, **kw)
    assert r.returncode == 0, (args, r.stdout, r.stderr)
    return r


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


class RecordHealNotInPhaseOneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="commons-heal-record-")
        self.saved_root = board_ingest.ROOT
        self.origin = os.path.join(self.tmp, "origin.git")
        self.ours = os.path.join(self.tmp, "ours")
        run(["git", "init", "-q", "--bare", "-b", "main", self.origin], self.tmp)
        run(["git", "clone", "-q", self.origin, self.ours], self.tmp)
        run(["git", "config", "user.email", "t@t"], self.ours)
        run(["git", "config", "user.name", "t"], self.ours)
        write(os.path.join(self.ours, "p", "old.md"), "old record\n")
        write(os.path.join(self.ours, "board.html"), "BAKE:old.md\n")
        run(["git", "add", "-A"], self.ours)
        run(["git", "commit", "-qm", "base"], self.ours)
        run(["git", "push", "-q", "origin", "HEAD:main"], self.ours)
        board_ingest.ROOT = self.ours

    def tearDown(self):
        board_ingest.ROOT = self.saved_root
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_companion_md_helper(self):
        self.assertEqual(
            board_ingest._companion_md_for_permalink("p/new-post.html"),
            "p/new-post.md",
        )
        self.assertIsNone(board_ingest._companion_md_for_permalink("p/new-post.md"))
        self.assertIsNone(board_ingest._companion_md_for_permalink("wake_jobs/x.json"))

    def test_healed_html_for_existing_md_is_not_a_record_path(self):
        write(os.path.join(self.ours, "p", "old.html"), "<p>healed old</p>\n")
        write(os.path.join(self.ours, "p", "new.md"), "new record\n")
        write(os.path.join(self.ours, "p", "new.html"), "<p>new companion</p>\n")
        write(os.path.join(self.ours, "wake_jobs", "job.json"), "{}\n")
        env = board_ingest.git_env()
        rec = board_ingest._record_paths(env)
        self.assertIn("p/new.md", rec)
        self.assertIn("p/new.html", rec)
        self.assertTrue(
            any(p == "wake_jobs/job.json" or p.startswith("wake_jobs") for p in rec),
            rec,
        )
        self.assertNotIn("p/old.html", rec)

    def test_resolve_rebase_skips_healed_html_already_recorded_on_origin(self):
        write(os.path.join(self.ours, "p", "old.html"), "<p>healed old</p>\n")
        write(os.path.join(self.ours, "p", "new.md"), "new record\n")
        write(os.path.join(self.ours, "p", "new.html"), "<p>new companion</p>\n")
        run(["git", "add", "-A"], self.ours)
        run(["git", "commit", "-qm", "mixed record plus heal"], self.ours)
        env = board_ingest.git_env()
        rc = board_ingest._resolve_rebase(env)
        self.assertEqual(rc.returncode, 0, (rc.stdout, rc.stderr))
        names = run(
            ["git", "show", "--name-only", "--format=", "HEAD"], self.ours
        ).stdout.split()
        self.assertIn("p/new.md", names)
        self.assertIn("p/new.html", names)
        self.assertNotIn("p/old.html", names)
        subject = run(["git", "log", "--format=%s", "-1"], self.ours).stdout.strip()
        self.assertTrue(subject.startswith("record: replayed"), subject)

    def test_commit_and_push_lands_new_record_without_healed_html(self):
        write(os.path.join(self.ours, "p", "old.html"), "<p>healed old</p>\n")
        write(os.path.join(self.ours, "p", "new.md"), "new record\n")
        write(os.path.join(self.ours, "p", "new.html"), "<p>new companion</p>\n")
        write(os.path.join(self.ours, "board.html"), "BAKE:old.md,new.md\n")

        saved_rebuild = board_ingest.rebuild

        def bake():
            write(os.path.join(self.ours, "board.html"), "BAKE:old.md,new.md\n")

        board_ingest.rebuild = bake
        try:
            st = board_ingest.commit_and_push(
                "board ingest", extra_paths=["board.html", "p"]
            )
        finally:
            board_ingest.rebuild = saved_rebuild
        self.assertEqual(st, "pushed", st)

        check = os.path.join(self.tmp, "check")
        run(["git", "clone", "-q", self.origin, check], self.tmp)
        self.assertTrue(os.path.isfile(os.path.join(check, "p", "new.md")))
        subjects = run(["git", "log", "--format=%s", "-8"], check).stdout
        self.assertIn("record: board ingest", subjects)
        record_files = run(
            ["git", "log", "--diff-filter=A", "--name-only", "--format=",
             "--grep=record: board ingest", "-1"],
            check,
        ).stdout.split()
        self.assertIn("p/new.md", record_files)
        self.assertIn("p/new.html", record_files)
        self.assertNotIn("p/old.html", record_files)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
