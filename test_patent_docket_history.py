#!/usr/bin/env python3
"""Real-Git source-receipt regressions; no project data or network required."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("patent_docket_history", ROOT / "host/patent_docket.py")
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
URL = "https://github.com/woahwhattheheck/commons/blob/"


class SourceReceiptHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "origin"
        self.root.mkdir()
        self.clock = 0
        self.env = dict(
            os.environ,
            GIT_AUTHOR_NAME="History fixture",
            GIT_AUTHOR_EMAIL="history@example.test",
            GIT_COMMITTER_NAME="History fixture",
            GIT_COMMITTER_EMAIL="history@example.test",
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_TERMINAL_PROMPT="0",
        )
        self.git("init", "-q", "-b", "main")

    def git(self, *args, root=None):
        result = subprocess.run(
            ["git", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", "-C", str(root or self.root), *args],
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def write(self, path, text="source\n"):
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")

    def commit(self, label):
        stamp = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=self.clock)
        self.clock += 1
        self.env["GIT_AUTHOR_DATE"] = stamp.isoformat()
        self.env["GIT_COMMITTER_DATE"] = stamp.isoformat()
        self.git("add", "-A")
        self.git("commit", "-qm", label)
        return self.git("rev-parse", "HEAD"), self.git("show", "-s", "--format=%cI", "HEAD")

    def receipt(self, path, commit, stamp):
        return {"path": path, "commit_sha": commit, "disclosed_at": stamp, "public_url": URL + commit + "/" + path}

    def rename_chain(self, original="original.txt", current="current.txt"):
        self.write(original, "exact source bytes\n")
        self.write("unrelated.txt", "different bytes\n")
        created, stamp = self.commit("creation")
        self.git("mv", "--", original, "intermediate.txt")
        self.commit("first rename")
        self.write("unrelated.txt", "unrelated update\n")
        self.commit("unrelated update")
        self.git("mv", "--", "intermediate.txt", current)
        renamed, _ = self.commit("second rename")
        return created, stamp, renamed

    def validate(self, receipt, source="current.txt", root=None):
        mod._validate_receipt(root or self.root, receipt, source, "receipt")

    def test_unrenamed_source_keeps_original_record(self):
        self.write("source.txt")
        created, stamp = self.commit("creation")
        self.write("source.txt", "source edited\n")
        self.commit("edit")
        self.assertEqual(mod._earliest_add(self.root, "source.txt"), (created, stamp))
        self.validate(self.receipt("source.txt", created, stamp), "source.txt")

    def test_two_renames_retain_original_add_commit(self):
        created, stamp, _ = self.rename_chain()
        self.assertEqual(mod._earliest_add(self.root, "current.txt"), (created, stamp))

    def test_real_consumer_accepts_linked_historical_receipt(self):
        created, stamp, _ = self.rename_chain()
        self.validate(self.receipt("original.txt", created, stamp))

    def test_historical_path_framing_preserves_special_names(self):
        for index, name in enumerate(("old name.txt", "tab\tname.txt", "line\nbreak.txt", "\nleading.txt", "caf\u00e9-\u96ea.txt")):
            with self.subTest(name=name):
                current = "current-%d.txt" % index
                self.write(name, "unique source %d\n" % index)
                created, stamp = self.commit("special creation %d" % index)
                self.git("mv", "--", name, current)
                self.commit("special rename %d" % index)
                self.assertEqual(mod._earliest_add(self.root, current), (created, stamp))
                self.validate(self.receipt(name, created, stamp), current)

    def test_unrelated_historical_path_is_rejected(self):
        created, stamp, _ = self.rename_chain()
        with self.assertRaises(mod.DocketError):
            self.validate(self.receipt("unrelated.txt", created, stamp))

    def test_identical_but_unlinked_path_is_rejected(self):
        self.write("original.txt", "same bytes\n")
        self.write("unrelated.txt", "same bytes\n")
        created, stamp = self.commit("creation")
        self.git("mv", "original.txt", "current.txt")
        self.commit("rename")
        with self.assertRaises(mod.DocketError):
            self.validate(self.receipt("unrelated.txt", created, stamp))

    def test_current_path_is_not_invented_at_original_commit(self):
        created, stamp, _ = self.rename_chain()
        with self.assertRaises(mod.DocketError):
            self.validate(self.receipt("current.txt", created, stamp))

    def test_rename_commit_cannot_replace_creation(self):
        _, _, renamed = self.rename_chain()
        renamed_at = self.git("show", "-s", "--format=%cI", renamed)
        with self.assertRaises(mod.DocketError):
            self.validate(self.receipt("original.txt", renamed, renamed_at))

    def test_forged_timestamp_remains_rejected(self):
        created, _, _ = self.rename_chain()
        with self.assertRaises(mod.DocketError):
            self.validate(self.receipt("original.txt", created, "2026-02-01T00:00:00Z"))

    def test_receipt_url_must_use_exact_historical_path(self):
        created, stamp, _ = self.rename_chain()
        receipt = self.receipt("original.txt", created, stamp)
        receipt["public_url"] = URL + created + "/current.txt"
        with self.assertRaises(mod.DocketError):
            self.validate(receipt)

    def test_delete_and_readd_still_selects_oldest_add(self):
        self.write("source.txt", "first\n")
        created, stamp = self.commit("creation")
        (self.root / "source.txt").unlink()
        self.commit("deletion")
        self.write("source.txt", "second\n")
        self.commit("readdition")
        self.assertEqual(mod._earliest_add(self.root, "source.txt"), (created, stamp))
        self.validate(self.receipt("source.txt", created, stamp), "source.txt")

    def test_committed_source_hash_consumer_is_unchanged(self):
        created, stamp, _ = self.rename_chain()
        raw = b"exact source bytes\n"
        source = {
            "path": "current.txt",
            "blob_sha": self.git("rev-parse", "HEAD:current.txt"),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_count": len(raw),
            "public_url": URL + "main/current.txt",
        }
        self.assertEqual(mod._validate_source(self.root, source, "source"), raw)
        self.validate(self.receipt("original.txt", created, stamp))

    def test_dirty_worktree_does_not_change_committed_history(self):
        created, stamp, _ = self.rename_chain()
        self.write("current.txt", "uncommitted replacement\n")
        self.assertEqual(mod._earliest_add(self.root, "current.txt"), (created, stamp))
        self.validate(self.receipt("original.txt", created, stamp))

    def test_missing_history_is_a_docket_error(self):
        self.write("other.txt")
        self.commit("unrelated")
        with self.assertRaisesRegex(mod.DocketError, "no add commit"):
            mod._earliest_add(self.root, "missing.txt")

    def shallow_fixture(self):
        self.write("source.txt", "first\n")
        created, stamp = self.commit("creation")
        self.write("source.txt", "changed\n")
        self.commit("edit")
        clone = Path(self.tmp.name) / "shallow"
        self.git("clone", "-q", "--depth=1", self.root.as_uri(), str(clone))
        self.git("fetch", "-q", "--depth=1", "origin", created, root=clone)
        self.assertTrue(mod._is_shallow(clone))
        self.assertNotEqual(mod._earliest_add(clone, "source.txt")[0], created)
        return clone, created, stamp

    def test_real_shallow_checkout_keeps_pinned_add_fallback(self):
        clone, created, stamp = self.shallow_fixture()
        self.validate(self.receipt("source.txt", created, stamp), "source.txt", clone)

    def test_real_shallow_checkout_rejects_timestamp_drift(self):
        clone, created, _ = self.shallow_fixture()
        with self.assertRaisesRegex(mod.DocketError, "disclosure timestamp drift"):
            self.validate(self.receipt("source.txt", created, "2026-02-01T00:00:00Z"), "source.txt", clone)

    def test_shallow_history_does_not_invent_unseen_rename_links(self):
        created, stamp, _ = self.rename_chain()
        clone = Path(self.tmp.name) / "shallow-renamed"
        self.git("clone", "-q", "--depth=1", self.root.as_uri(), str(clone))
        self.git("fetch", "-q", "--depth=1", "origin", created, root=clone)
        with self.assertRaises(mod.DocketError):
            self.validate(self.receipt("original.txt", created, stamp), root=clone)


if __name__ == "__main__":
    unittest.main(verbosity=2)
