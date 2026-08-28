#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from host import live_mirror

ROOT = Path(__file__).resolve().parent
FAILED_PUSH = (
    "To https://github.com/woahwhattheheck/commons-backup.git\n"
    " ! [remote rejected]     src-main -> main (refusing to allow a GitHub App "
    "to create or update workflow `.github/workflows/board-label.yml` without "
    "`workflows` permission)\n"
    "error: failed to push some refs to 'https://github.com/woahwhattheheck/commons-backup.git'\n"
)


def git(repo: Path, *args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        text=True,
        capture_output=True,
    )
    if check and completed.returncode:
        raise RuntimeError(completed.stderr)
    return completed.stdout.strip()


def init_repo(path: Path, branch: str = "main") -> None:
    path.mkdir(parents=True)
    git(path, "init", "-b", branch)
    git(path, "config", "user.email", "live-mirror-test@example.invalid")
    git(path, "config", "user.name", "live-mirror-test")


def commit_tree(path: Path, files: dict[str, str], message: str) -> str:
    for rel, body in files.items():
        dest = path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
        git(path, "add", rel)
    # drop files that disappeared
    git(path, "add", "-A")
    git(path, "commit", "-m", message, "--allow-empty")
    return git(path, "rev-parse", "HEAD")


class LiveMirrorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_classify_failed_run_33201665650(self) -> None:
        self.assertEqual(live_mirror.classify_push_error(FAILED_PUSH), "WORKFLOWS_PERMISSION")
        self.assertEqual(live_mirror.classify_push_error("rejected: stale info"), "OTHER")

    def test_plan_exact_and_recorded_source(self) -> None:
        sha = "a" * 40
        other = "b" * 40
        self.assertEqual(live_mirror.plan(sha, sha)["action"], "already_in_sync")
        self.assertEqual(live_mirror.plan(sha, other, sha)["reason"], "recorded_source")
        self.assertEqual(live_mirror.plan(sha, other)["action"], "push")

    def test_graft_keeps_dest_workflow_bytes(self) -> None:
        src = self.root / "src"
        dst = self.root / "dst"
        init_repo(src)
        init_repo(dst)
        commit_tree(
            dst,
            {
                "readme.md": "old\n",
                ".github/workflows/board-label.yml": "name: old-label\n",
                ".github/workflows/tests.yml": "name: tests-old\n",
            },
            "dest snapshot",
        )
        # source moved: new file, updated workflow, extra workflow
        for rel in (".github/workflows/board-label.yml", ".github/workflows/tests.yml", "readme.md"):
            (src / rel).parent.mkdir(parents=True, exist_ok=True)
        # copy dest history then diverge
        git(src, "remote", "add", "dst", str(dst))
        git(src, "fetch", "dst")
        git(src, "reset", "--hard", "dst/main")
        commit_tree(
            src,
            {
                "readme.md": "new\n",
                "posts.md": "hello\n",
                ".github/workflows/board-label.yml": "name: new-label\n",
                ".github/workflows/tests.yml": "name: tests-new\n",
                ".github/workflows/open-repo-backup.yml": "name: backup\n",
            },
            "source moved",
        )
        git_dir = str(src / ".git")
        src_sha = git(src, "rev-parse", "HEAD")
        dst_sha = git(dst, "rev-parse", "HEAD")
        graft = live_mirror.graft_dest_workflows(git_dir, src_sha, dst_sha)
        self.assertTrue(graft["workflows_frozen"])
        self.assertNotEqual(graft["grafted_tree"], graft["src_tree"])
        grafted = live_mirror.commit_graft(git_dir, src_sha, graft["grafted_tree"])
        git(src, "checkout", grafted)
        self.assertEqual((src / "readme.md").read_text(encoding="utf-8"), "new\n")
        self.assertEqual((src / "posts.md").read_text(encoding="utf-8"), "hello\n")
        self.assertEqual(
            (src / ".github/workflows/board-label.yml").read_text(encoding="utf-8"),
            "name: old-label\n",
        )
        self.assertFalse((src / ".github/workflows/open-repo-backup.yml").exists())
        self.assertEqual(git(src, "rev-parse", "HEAD^"), src_sha)

    def test_graft_omits_workflows_when_dest_has_none(self) -> None:
        src = self.root / "src"
        dst = self.root / "dst"
        init_repo(src)
        init_repo(dst)
        commit_tree(dst, {"readme.md": "old\n"}, "dest no workflows")
        git(src, "remote", "add", "dst", str(dst))
        git(src, "fetch", "dst")
        git(src, "reset", "--hard", "dst/main")
        commit_tree(
            src,
            {
                "readme.md": "new\n",
                ".github/workflows/board-label.yml": "name: new-label\n",
            },
            "source added workflow",
        )
        graft = live_mirror.graft_dest_workflows(
            str(src / ".git"),
            git(src, "rev-parse", "HEAD"),
            git(dst, "rev-parse", "HEAD"),
        )
        self.assertTrue(graft["workflows_omitted"])
        grafted = live_mirror.commit_graft(str(src / ".git"), git(src, "rev-parse", "HEAD"), graft["grafted_tree"])
        git(src, "checkout", grafted)
        self.assertEqual((src / "readme.md").read_text(encoding="utf-8"), "new\n")
        self.assertFalse((src / ".github/workflows").exists())

    def test_local_push_exact_then_graft_fallback(self) -> None:
        src = self.root / "src"
        dest = self.root / "dest.git"
        init_repo(src)
        commit_tree(
            src,
            {
                "readme.md": "one\n",
                ".github/workflows/board-label.yml": "name: v1\n",
            },
            "first",
        )
        git(src, "clone", "--bare", str(src), str(dest))
        first = git(src, "rev-parse", "HEAD")
        receipt = live_mirror.push_mirror(
            str(src / ".git"),
            first,
            str(dest),
            dst_ref=None,
        )
        self.assertEqual(receipt["state"], "EXACT")
        self.assertEqual(receipt["pushed_sha"], first)

        commit_tree(
            src,
            {
                "readme.md": "two\n",
                ".github/workflows/board-label.yml": "name: v2\n",
            },
            "second",
        )
        second = git(src, "rev-parse", "HEAD")
        dest_url = str(dest)

        original_push = live_mirror._push

        def fake_push(git_dir: str, url: str, refspec: str):
            if refspec.endswith(":refs/heads/main") and refspec.startswith(second):
                class Fake:
                    returncode = 1
                    stdout = b""
                    stderr = FAILED_PUSH.encode("utf-8")

                return Fake()
            return original_push(git_dir, url, refspec)

        live_mirror._push = fake_push  # type: ignore[method-assign]
        try:
            grafted = live_mirror.push_mirror(
                str(src / ".git"),
                second,
                dest_url,
                dst_ref=first,
            )
        finally:
            live_mirror._push = original_push  # type: ignore[method-assign]
        self.assertEqual(grafted["state"], "GRAFTED")
        self.assertTrue(grafted["workflows_frozen"])
        self.assertEqual(grafted["src_sha"], second)
        shown = git(src, "show", f"{grafted['pushed_sha']}:.github/workflows/board-label.yml")
        self.assertEqual(shown, "name: v1")
        shown_readme = git(src, "show", f"{grafted['pushed_sha']}:readme.md")
        self.assertEqual(shown_readme, "two")

    def test_cli_classify_and_plan(self) -> None:
        tool = ROOT / "host" / "live_mirror.py"
        classify = subprocess.run(
            [sys.executable, str(tool), "classify-error", "--stderr", FAILED_PUSH],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertEqual(json.loads(classify.stdout)["kind"], "WORKFLOWS_PERMISSION")
        sha = "c" * 40
        planned = subprocess.run(
            [sys.executable, str(tool), "plan", "--src", sha, "--dst", sha],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertEqual(json.loads(planned.stdout)["action"], "already_in_sync")


if __name__ == "__main__":
    unittest.main()
