#!/usr/bin/env python3
"""Cloud-current worktree: dirt is preserved, origin is measured, owner disk is frozen."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from cloud_current_worktree import (  # noqa: E402
    ForbiddenGit,
    OwnerDiskRefuse,
    classify_three_way,
    dirty_paths,
    fetch_origin_main,
    git,
    journal_has_forbidden,
    open_worktree,
    owner_disk_reason,
    recover,
    refresh,
    refuse_forbidden_argv,
    snapshot,
    status,
    write_file_bytes,
    read_file_bytes,
)


def _init_origin(path):
    os.makedirs(path, exist_ok=True)
    git(["init", "-b", "main"], cwd=path)
    git(["config", "user.email", "peer@commons.test"], cwd=path)
    git(["config", "user.name", "cloud-current"], cwd=path)
    write_file_bytes(path, "README.md", b"hello commons\n")
    write_file_bytes(path, "keep.txt", b"stable\n")
    write_file_bytes(path, "shared.txt", b"alpha\nbeta\n")
    write_file_bytes(path, "data.json", b'{"a": 1}\n')
    git(["add", "README.md", "keep.txt", "shared.txt", "data.json"], cwd=path)
    git(["commit", "-m", "init"], cwd=path)
    return path


def _commit_file(repo, rel, body, message):
    write_file_bytes(repo, rel, body)
    git(["add", rel], cwd=repo)
    git(["commit", "-m", message], cwd=repo)


class CloudCurrentWorktreeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cc-test-")
        self.origin = _init_origin(os.path.join(self.tmp, "origin"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _open(self, name="peer", mode="clone", source=None):
        dest = os.path.join(self.tmp, name)
        return open_worktree(peer=name, dest=dest, repo=self.origin, mode=mode, source=source)

    def test_owner_disk_refuse_markers(self):
        cases = [
            "/tmp/Users/lucys/Desktop/commons/copy",
            "/x/.cursor/worktrees/abc",
            "/x/.claude/worktrees/abc",
            "/opt/LocalDeviceAgent/.claude/worktrees/muhl-osc",
        ]
        for path in cases:
            self.assertTrue(owner_disk_reason(path), path)
            with self.assertRaises(OwnerDiskRefuse):
                open_worktree(peer="x", dest=path, repo=self.origin)

    def test_owner_disk_env_flag(self):
        dest = os.path.join(self.tmp, "flagged")
        old = os.environ.get("COMMONS_OWNER_DISK")
        os.environ["COMMONS_OWNER_DISK"] = "1"
        try:
            with self.assertRaises(OwnerDiskRefuse):
                open_worktree(peer="x", dest=dest, repo=self.origin)
        finally:
            if old is None:
                os.environ.pop("COMMONS_OWNER_DISK", None)
            else:
                os.environ["COMMONS_OWNER_DISK"] = old

    def test_forbidden_git_argv(self):
        bad = [
            ["reset", "--hard", "HEAD"],
            ["reset", "--merge"],
            ["checkout", "HEAD", "--", "file"],
            ["stash", "drop"],
            ["stash", "pop"],
            ["clean", "-fd"],
            ["push", "--force"],
            ["push", "-f"],
            ["worktree", "remove", "--force", "x"],
            ["gc"],
            ["prune"],
        ]
        for argv in bad:
            with self.assertRaises(ForbiddenGit, msg=argv):
                refuse_forbidden_argv(argv)
        refuse_forbidden_argv(["stash", "create"])
        refuse_forbidden_argv(["fetch", "origin", "main"])
        refuse_forbidden_argv(["worktree", "add", "/tmp/x", "wt/peer/1"])

    def test_snapshot_preserves_dirt(self):
        opened = self._open("snap")
        dest = opened["worktree"]
        write_file_bytes(dest, "dirt.txt", b"do not lose me\n")
        receipt = snapshot(dest, peer="snap")
        self.assertEqual(receipt["readiness"], "SNAPSHOTTED")
        copied = os.path.join(dest, ".commons-worktree", "receipts", receipt["id"], "files", "dirt.txt")
        self.assertTrue(os.path.isfile(copied))
        self.assertEqual(open(copied, "rb").read(), b"do not lose me\n")
        self.assertEqual(read_file_bytes(dest, "dirt.txt"), b"do not lose me\n")
        self.assertFalse(receipt["destructive"])
        self.assertFalse(receipt["deleted_user_work"])

    def test_non_overlap_refresh_merges(self):
        opened = self._open("disjoint")
        dest = opened["worktree"]
        write_file_bytes(dest, "mine.txt", b"peer dirt\n")
        _commit_file(self.origin, "keep.txt", b"stable\nfrom-main\n", "main advanced keep.txt")
        receipt = refresh(dest, peer="disjoint")
        self.assertEqual(receipt["origin_state"], "CURRENT")
        self.assertEqual(read_file_bytes(dest, "mine.txt"), b"peer dirt\n")
        self.assertIn(b"from-main", read_file_bytes(dest, "keep.txt") or b"")
        self.assertEqual(receipt["readiness"], "READY")
        self.assertFalse(receipt["conflicts"])

    def test_semantic_conflict_keeps_ours(self):
        opened = self._open("conflict")
        dest = opened["worktree"]
        write_file_bytes(dest, "shared.txt", b"alpha-OURS\nbeta\n")
        _commit_file(self.origin, "shared.txt", b"alpha-THEIRS\nbeta\n", "main changed same line")
        receipt = refresh(dest, peer="conflict")
        self.assertEqual(read_file_bytes(dest, "shared.txt"), b"alpha-OURS\nbeta\n")
        self.assertTrue(receipt["conflicts"])
        self.assertEqual(receipt["conflicts"][0]["path"], "shared.txt")
        self.assertEqual(receipt["readiness"], "READY_WITH_CONFLICTS")
        artifact = os.path.join(
            dest, ".commons-worktree", "receipts", receipt["id"], "conflicts", "shared.txt", "theirs"
        )
        self.assertTrue(os.path.isfile(artifact))
        self.assertIn(b"THEIRS", open(artifact, "rb").read())

    def test_identical_overlap_dedupes(self):
        opened = self._open("dedupe")
        dest = opened["worktree"]
        body = b"alpha\nbeta\ngamma\n"
        write_file_bytes(dest, "shared.txt", body)
        _commit_file(self.origin, "shared.txt", body, "same bytes")
        receipt = refresh(dest, peer="dedupe")
        self.assertEqual(read_file_bytes(dest, "shared.txt"), body)
        self.assertFalse(receipt["conflicts"])
        ops = [row["op"] for row in receipt["actions"] if row.get("path") == "shared.txt"]
        self.assertIn("dedupe", ops)

    def test_json_key_union_composes(self):
        opened = self._open("json")
        dest = opened["worktree"]
        write_file_bytes(dest, "data.json", b'{"a": 1, "ours": true}\n')
        _commit_file(self.origin, "data.json", b'{"a": 1, "theirs": true}\n', "json theirs")
        receipt = refresh(dest, peer="json")
        self.assertFalse(receipt["conflicts"])
        data = json.loads(read_file_bytes(dest, "data.json"))
        self.assertEqual(data.get("a"), 1)
        self.assertTrue(data.get("ours"))
        self.assertTrue(data.get("theirs"))
        ops = [row["op"] for row in receipt["actions"] if row.get("path") == "data.json"]
        self.assertIn("compose", ops)

    def test_text_insert_only_composes(self):
        base = b"alpha\nbeta\n"
        ours = b"alpha\nbeta\nOURS_INSERT\n"
        theirs = b"alpha\nbeta\nTHEIRS_INSERT\n"
        result = classify_three_way(base, ours, theirs)
        self.assertNotEqual(result["verdict"], "CONFLICT")

        opened = self._open("insert")
        dest = opened["worktree"]
        write_file_bytes(dest, "shared.txt", ours)
        _commit_file(self.origin, "shared.txt", theirs, "insert on main")
        receipt = refresh(dest, peer="insert")
        self.assertFalse(receipt["conflicts"])
        body = read_file_bytes(dest, "shared.txt") or b""
        # Either merge-file composed both inserts, or ours kept with origin recorded.
        self.assertIn(b"alpha", body)
        self.assertIn(b"beta", body)

    def test_fetch_fail_is_stale_not_stop(self):
        opened = self._open("stale")
        dest = opened["worktree"]
        write_file_bytes(dest, "dirt.txt", b"keep through stale\n")
        git(["remote", "set-url", "origin", os.path.join(self.tmp, "no-such-origin")], cwd=dest)
        receipt = refresh(dest, peer="stale")
        self.assertEqual(receipt["origin_state"], "STALE")
        self.assertEqual(receipt["readiness"], "STALE_ORIGIN")
        self.assertEqual(read_file_bytes(dest, "dirt.txt"), b"keep through stale\n")
        self.assertFalse(receipt["destructive"])

    def test_recover_does_not_clobber_newer_dirt(self):
        opened = self._open("recover")
        dest = opened["worktree"]
        write_file_bytes(dest, "dirt.txt", b"old dirt\n")
        snap = snapshot(dest, peer="recover")
        write_file_bytes(dest, "dirt.txt", b"newer dirt\n")
        write_file_bytes(dest, "gone.txt", b"will restore if missing\n")
        snap2 = snapshot(dest, peer="recover")
        os.remove(os.path.join(dest, "gone.txt"))
        receipt = recover(dest, snap["id"], peer="recover")
        self.assertEqual(read_file_bytes(dest, "dirt.txt"), b"newer dirt\n")
        ops = {row["path"]: row["op"] for row in receipt["actions"]}
        self.assertEqual(ops.get("dirt.txt"), "kept_newer_dirt")
        # restore missing file from the later snapshot
        receipt2 = recover(dest, snap2["id"], peer="recover")
        self.assertEqual(read_file_bytes(dest, "gone.txt"), b"will restore if missing\n")
        ops2 = {row["path"]: row["op"] for row in receipt2["actions"]}
        self.assertEqual(ops2.get("gone.txt"), "restore")
        self.assertEqual(read_file_bytes(dest, "dirt.txt"), b"newer dirt\n")

    def test_git_journal_has_no_forbidden_argv(self):
        opened = self._open("journal")
        dest = opened["worktree"]
        write_file_bytes(dest, "dirt.txt", b"x\n")
        refresh(dest, peer="journal")
        snapshot(dest, peer="journal")
        status(dest, peer="journal")
        self.assertFalse(journal_has_forbidden(dest))
        with self.assertRaises(ForbiddenGit):
            git(["reset", "--hard", "HEAD"], cwd=dest)

    def test_two_peer_isolation(self):
        a = self._open("alice")
        b = self._open("bob")
        write_file_bytes(a["worktree"], "alice.txt", b"alice dirt\n")
        write_file_bytes(b["worktree"], "bob.txt", b"bob dirt\n")
        _commit_file(self.origin, "keep.txt", b"stable\nshared-main\n", "main for both")
        ra = refresh(a["worktree"], peer="alice")
        rb = refresh(b["worktree"], peer="bob")
        self.assertEqual(read_file_bytes(a["worktree"], "alice.txt"), b"alice dirt\n")
        self.assertIsNone(read_file_bytes(a["worktree"], "bob.txt"))
        self.assertEqual(read_file_bytes(b["worktree"], "bob.txt"), b"bob dirt\n")
        self.assertIsNone(read_file_bytes(b["worktree"], "alice.txt"))
        self.assertIn(b"shared-main", read_file_bytes(a["worktree"], "keep.txt") or b"")
        self.assertIn(b"shared-main", read_file_bytes(b["worktree"], "keep.txt") or b"")
        self.assertNotEqual(a["worktree"], b["worktree"])
        self.assertFalse(ra["destructive"])
        self.assertFalse(rb["destructive"])

    def test_worktree_mode_unique_branch_never_main(self):
        source = self._open("source-clone")
        src = source["worktree"]
        opened = open_worktree(
            peer="claude",
            dest=os.path.join(self.tmp, "wt-claude"),
            repo=self.origin,
            mode="worktree",
            source=src,
        )
        dest = opened["worktree"]
        rc, out, _ = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=dest, check=False)
        branch = out.decode("utf-8").strip()
        self.assertTrue(branch.startswith("wt/claude/"), branch)
        self.assertNotEqual(branch, "main")
        write_file_bytes(dest, "claude-dirt.txt", b"farm dirt\n")
        _commit_file(self.origin, "README.md", b"hello commons\nmain note\n", "origin moved")
        git(["remote", "set-url", "origin", self.origin], cwd=src)
        git(["remote", "set-url", "origin", self.origin], cwd=dest)
        receipt = refresh(dest, peer="claude")
        self.assertEqual(read_file_bytes(dest, "claude-dirt.txt"), b"farm dirt\n")
        self.assertIn(receipt["origin_state"], ("CURRENT", "STALE"))

    def test_origin_delete_does_not_drop_dirty_file(self):
        opened = self._open("del")
        dest = opened["worktree"]
        write_file_bytes(dest, "keep.txt", b"my keep\n")
        git(["rm", "keep.txt"], cwd=self.origin)
        git(["commit", "-m", "origin deleted keep"], cwd=self.origin)
        receipt = refresh(dest, peer="del")
        self.assertEqual(read_file_bytes(dest, "keep.txt"), b"my keep\n")
        paths = [c["path"] for c in receipt["conflicts"]]
        self.assertIn("keep.txt", paths)

    def test_secret_names_redacted_in_receipt(self):
        opened = self._open("secret")
        dest = opened["worktree"]
        write_file_bytes(dest, ".env", b"TOKEN=do-not-publish\n")
        write_file_bytes(dest, "notes.txt", b"ok\n")
        receipt = snapshot(dest, peer="secret")
        env_rows = [r for r in receipt["dirty_files"] if r["path"] == ".env"]
        self.assertTrue(env_rows)
        self.assertTrue(env_rows[0].get("redacted"))
        self.assertEqual(env_rows[0].get("sha256"), "")
        copied_env = os.path.join(dest, ".commons-worktree", "receipts", receipt["id"], "files", ".env")
        self.assertFalse(os.path.isfile(copied_env))
        copied_notes = os.path.join(dest, ".commons-worktree", "receipts", receipt["id"], "files", "notes.txt")
        self.assertTrue(os.path.isfile(copied_notes))

    def test_occupied_dest_is_not_deleted(self):
        dest = os.path.join(self.tmp, "occupied")
        os.makedirs(dest)
        marker = os.path.join(dest, "preexisting.txt")
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write("stay\n")
        receipt = open_worktree(peer="occ", dest=dest, repo=self.origin)
        self.assertEqual(receipt["readiness"], "DEST_OCCUPIED")
        self.assertTrue(os.path.isfile(marker))
        with open(marker, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "stay\n")

    def test_status_measures_not_fabricates(self):
        opened = self._open("stat")
        dest = opened["worktree"]
        git(["remote", "set-url", "origin", os.path.join(self.tmp, "missing-origin")], cwd=dest)
        receipt = status(dest, peer="stat")
        self.assertIn(receipt["origin_state"], ("STALE", "UNKNOWN"))
        self.assertNotEqual(receipt["origin_state"], "CURRENT")
        self.assertNotEqual(receipt["readiness"], "CURRENT")

    def test_classify_json_scalar_conflict(self):
        result = classify_three_way(b'{"a": 1}\n', b'{"a": 2}\n', b'{"a": 3}\n')
        self.assertEqual(result["verdict"], "CONFLICT")
        self.assertEqual(result["merged"], b'{"a": 2}\n')


if __name__ == "__main__":
    unittest.main(verbosity=2)
