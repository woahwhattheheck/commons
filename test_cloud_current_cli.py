#!/usr/bin/env python3
"""Exercise both supported common-option positions through the actual CLI."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parent / "host" / "cloud_current_worktree.py"


class CloudCurrentCLITests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="cc-cli-test-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.origin = self.root / "origin"
        self.origin.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.email", "peer@commons.test")
        self.git("config", "user.name", "cloud-current-cli-test")
        (self.origin / "tracked.txt").write_text("initial\n", encoding="utf-8")
        self.git("add", "tracked.txt")
        self.git("commit", "-m", "fixture")

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.origin, capture_output=True,
            text=True, check=True, timeout=20,
        )

    def cli(self, *args):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args], cwd=self.root,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def open_root_options(self, peer="root-peer"):
        dest = self.root / "work"
        result = self.cli("--json", "--peer", peer, "open", "--dest", str(dest),
                          "--repo", str(self.origin))
        self.assertEqual(result["peer"], peer)
        self.assertEqual(result["readiness"], "READY")
        return dest

    def test_documented_open_peer_after_subcommand(self):
        dest = self.root / "work"
        result = self.cli("open", "--peer", "after-peer", "--json", "--dest", str(dest),
                          "--repo", str(self.origin))
        self.assertEqual(result["peer"], "after-peer")
        session = json.loads((dest / ".commons-worktree" / "session.json").read_text())
        self.assertEqual(session["peer"], "after-peer")
        self.assertEqual(result["readiness"], "READY")

    def test_root_options_keep_their_existing_values(self):
        dest = self.open_root_options("before-peer")
        result = self.cli("--json", "--peer", "before-status", "--worktree", str(dest), "status")
        self.assertEqual(result["peer"], "before-status")
        self.assertEqual(result["worktree"], str(dest))

    def test_common_options_work_after_each_worktree_subcommand(self):
        dest = self.open_root_options()
        dirt = dest / "dirt.txt"
        dirt.write_bytes(b"keep across commands\n")
        for command in ("status", "snapshot", "refresh", "current"):
            with self.subTest(command=command):
                result = self.cli(command, "--worktree", str(dest), "--peer", "after", "--json")
                self.assertEqual(result["peer"], "after")
                self.assertEqual(result["worktree"], str(dest))
                self.assertEqual(dirt.read_bytes(), b"keep across commands\n")

    def test_recover_accepts_common_options_with_receipt(self):
        dest = self.open_root_options()
        dirt = dest / "recover-me.txt"
        dirt.write_bytes(b"saved bytes\n")
        snapshot = self.cli("--json", "--worktree", str(dest), "snapshot")
        dirt.unlink()
        result = self.cli("recover", snapshot["id"], "--worktree", str(dest), "--peer", "restorer", "--json")
        self.assertEqual(result["peer"], "restorer")
        self.assertEqual(result["readiness"], "RECOVERED")
        self.assertEqual(dirt.read_bytes(), b"saved bytes\n")

    def test_later_explicit_option_overrides_earlier_option(self):
        dest = self.open_root_options()
        result = self.cli("--json", "--peer", "earlier", "--worktree", str(self.root / "unused"),
                          "status", "--peer", "later", "--worktree", str(dest))
        self.assertEqual(result["peer"], "later")
        self.assertEqual(result["worktree"], str(dest))

    def test_root_and_subcommand_options_can_be_mixed(self):
        dest = self.open_root_options()
        result = self.cli("--peer", "mixed-peer", "status", "--json", "--worktree", str(dest))
        self.assertEqual(result["peer"], "mixed-peer")
        self.assertEqual(result["readiness"], "READY")


if __name__ == "__main__":
    unittest.main()
