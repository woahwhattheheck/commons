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
FAILED_SOURCE_REF_PUSH = (
    "To https://github.com/woahwhattheheck/commons-backup.git\n"
    " ! [remote rejected]       ae68c9b82a87a9972a59052d031b6e4a9b6ff0e8 -> "
    "refs/backup/source-main (refusing to allow a GitHub App to create or "
    "update workflow `.github/workflows/affordable-housing-compliance-demo.yml` "
    "without `workflows` permission)\n"
    "error: failed to push some refs to 'https://github.com/woahwhattheheck/commons-backup.git'\n"
)
FAILED_TAG_PUSH = (
    "To https://github.com/woahwhattheheck/commons-backup.git\n"
    " ! [remote rejected]       commons-apk-debug-20260827 -> "
    "commons-apk-debug-20260827 (refusing to allow a GitHub App to create or "
    "update workflow `.github/workflows/capability-entrypoints.yml` without "
    "`workflows` permission)\n"
    " ! [remote rejected]       titan-kaggriculture-gauntlet-20260912 -> "
    "titan-kaggriculture-gauntlet-20260912 (refusing to allow a GitHub App to "
    "create or update workflow `.github/workflows/astra-kag-study.yml` without "
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


class _FakeReject:
    def __init__(self, stderr: str) -> None:
        self.returncode = 1
        self.stdout = b""
        self.stderr = stderr.encode("utf-8")


class LiveMirrorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_classify_failed_run_33201665650(self) -> None:
        self.assertEqual(live_mirror.classify_push_error(FAILED_PUSH), "WORKFLOWS_PERMISSION")
        self.assertEqual(live_mirror.classify_push_error("rejected: stale info"), "OTHER")

    def test_classify_failed_run_34784776092_source_ref(self) -> None:
        self.assertEqual(
            live_mirror.classify_push_error(FAILED_SOURCE_REF_PUSH),
            "WORKFLOWS_PERMISSION",
        )

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
            spec = refspec[1:] if refspec.startswith("+") else refspec
            if spec.endswith(":refs/heads/main") and spec.startswith(second):
                return _FakeReject(FAILED_PUSH)
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

    def test_grafted_push_force_updates_diverged_dest(self) -> None:
        """A second graft is not a fast-forward of the first grafted dest commit."""
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
        commit_tree(
            src,
            {
                "readme.md": "two\n",
                ".github/workflows/board-label.yml": "name: v2\n",
            },
            "second",
        )
        second = git(src, "rev-parse", "HEAD")
        original_push = live_mirror._push

        def block_exact(block_sha: str):
            def fake_push(git_dir: str, url: str, refspec: str):
                spec = refspec[1:] if refspec.startswith("+") else refspec
                if spec.endswith(":refs/heads/main") and spec.startswith(block_sha):
                    return _FakeReject(FAILED_PUSH)
                return original_push(git_dir, url, refspec)

            return fake_push

        live_mirror._push = block_exact(second)  # type: ignore[method-assign]
        try:
            first_graft = live_mirror.push_mirror(
                str(src / ".git"),
                second,
                str(dest),
                dst_ref=first,
            )
        finally:
            live_mirror._push = original_push  # type: ignore[method-assign]
        self.assertEqual(first_graft["state"], "GRAFTED")
        dest_after = git(dest, "rev-parse", "refs/heads/main")
        self.assertEqual(dest_after, first_graft["pushed_sha"])

        commit_tree(
            src,
            {
                "readme.md": "three\n",
                ".github/workflows/board-label.yml": "name: v3\n",
            },
            "third",
        )
        third = git(src, "rev-parse", "HEAD")
        live_mirror._push = block_exact(third)  # type: ignore[method-assign]
        try:
            second_graft = live_mirror.push_mirror(
                str(src / ".git"),
                third,
                str(dest),
                dst_ref=dest_after,
            )
        finally:
            live_mirror._push = original_push  # type: ignore[method-assign]
        self.assertEqual(second_graft["state"], "GRAFTED")
        self.assertEqual(git(dest, "rev-parse", "refs/heads/main"), second_graft["pushed_sha"])
        self.assertEqual(
            git(dest, "show", f"{second_graft['pushed_sha']}:readme.md"),
            "three",
        )
        self.assertEqual(
            git(dest, "show", f"{second_graft['pushed_sha']}:.github/workflows/board-label.yml"),
            "name: v1",
        )
        self.assertEqual(
            git(dest, "rev-parse", live_mirror.SOURCE_REF),
            third,
        )

    def test_source_ref_receipt_when_workflows_rejected(self) -> None:
        """Run 34784776092: grafted main landed; source-main exact SHA was rejected."""
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
        commit_tree(
            src,
            {
                "readme.md": "two\n",
                ".github/workflows/board-label.yml": "name: v2\n",
                ".github/workflows/affordable-housing-compliance-demo.yml": "name: housing\n",
            },
            "second with new workflow",
        )
        second = git(src, "rev-parse", "HEAD")
        original_push = live_mirror._push

        def fake_push(git_dir: str, url: str, refspec: str):
            spec = refspec[1:] if refspec.startswith("+") else refspec
            if spec.endswith(":refs/heads/main") and spec.startswith(second):
                return _FakeReject(FAILED_PUSH)
            if spec.endswith(":" + live_mirror.SOURCE_REF) and spec.startswith(second):
                return _FakeReject(FAILED_SOURCE_REF_PUSH)
            return original_push(git_dir, url, refspec)

        live_mirror._push = fake_push  # type: ignore[method-assign]
        try:
            grafted = live_mirror.push_mirror(
                str(src / ".git"),
                second,
                str(dest),
                dst_ref=first,
            )
        finally:
            live_mirror._push = original_push  # type: ignore[method-assign]

        self.assertEqual(grafted["state"], "GRAFTED")
        self.assertEqual(grafted["source_ref_state"], "RECEIPT_REF")
        self.assertEqual(grafted["src_sha"], second)
        self.assertNotEqual(grafted["source_ref_sha"], second)
        dest_git = str(dest)
        recorded = live_mirror.read_source_receipt(dest_git, live_mirror.SOURCE_REF)
        self.assertEqual(recorded, second)
        receipt_sha = git(dest, "rev-parse", live_mirror.SOURCE_REF)
        self.assertEqual(receipt_sha, grafted["source_ref_sha"])
        self.assertEqual(
            git(dest, "show", f"{receipt_sha}:{live_mirror.SOURCE_RECEIPT_NAME}"),
            second,
        )
        ls = git(dest, "ls-tree", "--name-only", receipt_sha)
        self.assertEqual(ls, live_mirror.SOURCE_RECEIPT_NAME)
        missing = subprocess.run(
            ["git", "rev-parse", "--verify", f"{receipt_sha}:{live_mirror.WORKFLOWS_DIR}"],
            cwd=dest,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(missing.returncode, 0)
        self.assertEqual(git(dest, "rev-parse", live_mirror.DEST_REF), grafted["pushed_sha"])
        planned = live_mirror.plan(second, grafted["pushed_sha"], recorded)
        self.assertEqual(planned["action"], "already_in_sync")
        self.assertEqual(planned["reason"], "recorded_source")
        live_mirror._push = fake_push  # type: ignore[method-assign]
        try:
            again = live_mirror.record_receipts(
                str(src / ".git"),
                str(dest),
                second,
                grafted["pushed_sha"],
            )
        finally:
            live_mirror._push = original_push  # type: ignore[method-assign]
        self.assertEqual(again["source_ref_state"], "ALREADY_RECORDED")
        self.assertEqual(again["src_sha"], second)

    def test_record_receipts_skips_when_already_recorded(self) -> None:
        src = self.root / "src"
        dest = self.root / "dest.git"
        init_repo(src)
        first = commit_tree(
            src,
            {
                "readme.md": "one\n",
                ".github/workflows/board-label.yml": "name: v1\n",
            },
            "first",
        )
        git(src, "clone", "--bare", str(src), str(dest))
        first_record = live_mirror.record_receipts(str(src / ".git"), str(dest), first, first)
        self.assertEqual(first_record["source_ref_state"], "EXACT_REF")
        git(src, "fetch", str(dest), f"+{live_mirror.SOURCE_REF}:{live_mirror.SOURCE_REF}")
        second_record = live_mirror.record_receipts(str(src / ".git"), str(dest), first, first)
        self.assertEqual(second_record["source_ref_state"], "ALREADY_RECORDED")
        self.assertEqual(live_mirror.read_source_receipt(str(dest), live_mirror.SOURCE_REF), first)

    def test_read_source_receipt_legacy_commit(self) -> None:
        src = self.root / "src"
        dest = self.root / "dest.git"
        init_repo(src)
        first = commit_tree(src, {"readme.md": "one\n"}, "first")
        git(src, "clone", "--bare", str(src), str(dest))
        git(src, "push", str(dest), f"{first}:{live_mirror.SOURCE_REF}")
        self.assertEqual(live_mirror.read_source_receipt(str(dest)), first)

    def test_cli_classify_and_plan(self) -> None:
        tool = ROOT / "host" / "live_mirror.py"
        classify = subprocess.run(
            [sys.executable, str(tool), "classify-error", "--stderr", FAILED_PUSH],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertEqual(json.loads(classify.stdout)["kind"], "WORKFLOWS_PERMISSION")
        classify_src = subprocess.run(
            [sys.executable, str(tool), "classify-error", "--stderr", FAILED_SOURCE_REF_PUSH],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertEqual(json.loads(classify_src.stdout)["kind"], "WORKFLOWS_PERMISSION")
        sha = "c" * 40
        planned = subprocess.run(
            [sys.executable, str(tool), "plan", "--src", sha, "--dst", sha],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertEqual(json.loads(planned.stdout)["action"], "already_in_sync")

    def test_cli_read_source_receipt(self) -> None:
        src = self.root / "src"
        dest = self.root / "dest.git"
        init_repo(src)
        first = commit_tree(
            src,
            {".github/workflows/board-label.yml": "name: v1\n", "readme.md": "one\n"},
            "first",
        )
        git(src, "clone", "--bare", str(src), str(dest))
        original_push = live_mirror._push

        def reject_source(git_dir: str, url: str, refspec: str):
            spec = refspec[1:] if refspec.startswith("+") else refspec
            if spec.endswith(":" + live_mirror.SOURCE_REF) and spec.startswith(first):
                return _FakeReject(FAILED_SOURCE_REF_PUSH)
            return original_push(git_dir, url, refspec)

        live_mirror._push = reject_source  # type: ignore[method-assign]
        try:
            recorded = live_mirror.record_receipts(str(src / ".git"), str(dest), first, first)
        finally:
            live_mirror._push = original_push  # type: ignore[method-assign]
        self.assertEqual(recorded["source_ref_state"], "RECEIPT_REF")
        tool = ROOT / "host" / "live_mirror.py"
        read = subprocess.run(
            [
                sys.executable,
                str(tool),
                "read-source",
                "--git-dir",
                str(dest),
                "--ref",
                live_mirror.SOURCE_REF,
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertEqual(json.loads(read.stdout)["src_sha"], first)

    def test_classify_failed_run_34785478675_tags(self) -> None:
        self.assertEqual(live_mirror.classify_push_error(FAILED_TAG_PUSH), "WORKFLOWS_PERMISSION")

    def test_push_tags_skips_workflows_rejected_tags(self) -> None:
        src = self.root / "src"
        dest = self.root / "dest.git"
        init_repo(src)
        first = commit_tree(src, {"readme.md": "one\n"}, "first")
        git(src, "tag", "safe-tag")
        git(
            src,
            "tag",
            "commons-apk-debug-20260827",
        )
        git(src, "clone", "--bare", str(src), str(dest))
        git(dest, "symbolic-ref", "HEAD", "refs/heads/main")
        original_namespace = live_mirror._push_tag_namespace
        original_push = live_mirror._push

        def reject_namespace(git_dir: str, dest_url: str):
            return _FakeReject(FAILED_TAG_PUSH)

        def fake_push(git_dir: str, url: str, refspec: str):
            spec = refspec[1:] if refspec.startswith("+") else refspec
            if spec.endswith(":refs/tags/commons-apk-debug-20260827"):
                return _FakeReject(FAILED_TAG_PUSH)
            return original_push(git_dir, url, refspec)

        live_mirror._push_tag_namespace = reject_namespace  # type: ignore[method-assign]
        live_mirror._push = fake_push  # type: ignore[method-assign]
        try:
            result = live_mirror.push_tags(str(src / ".git"), str(dest))
        finally:
            live_mirror._push_tag_namespace = original_namespace  # type: ignore[method-assign]
            live_mirror._push = original_push  # type: ignore[method-assign]
        self.assertEqual(result["state"], "TAGS_WORKFLOWS_SKIPPED")
        self.assertIn("refs/tags/safe-tag", result["pushed"])
        skipped_refs = [row["ref"] for row in result["skipped"]]
        self.assertEqual(skipped_refs, ["refs/tags/commons-apk-debug-20260827"])
        self.assertEqual(git(dest, "rev-parse", "refs/tags/safe-tag"), first)

    def test_push_tags_other_error_fail_closed(self) -> None:
        src = self.root / "src"
        dest = self.root / "dest.git"
        init_repo(src)
        commit_tree(src, {"readme.md": "one\n"}, "first")
        git(src, "tag", "safe-tag")
        git(src, "clone", "--bare", str(src), str(dest))

        def reject_namespace(git_dir: str, dest_url: str):
            return _FakeReject("error: failed to push some refs (remote hung up)\n")

        original = live_mirror._push_tag_namespace
        live_mirror._push_tag_namespace = reject_namespace  # type: ignore[method-assign]
        try:
            with self.assertRaises(live_mirror.MirrorError):
                live_mirror.push_tags(str(src / ".git"), str(dest))
        finally:
            live_mirror._push_tag_namespace = original  # type: ignore[method-assign]


if __name__ == "__main__":
    unittest.main()
