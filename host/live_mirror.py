#!/usr/bin/env python3
"""GITHUB_TOKEN-safe live mirror of canonical main onto commons-backup.

Same-account GitHub copy at woahwhattheheck/commons-backup. The scheduled
workflow on the backup `ops` branch force-pushes canonical commons `main`
onto backup `main`. GitHub Apps (including Actions GITHUB_TOKEN) cannot
create or update `.github/workflows/*` without the `workflows` permission.

This is not a Commons lock and not a reason to add a PAT. Exact SHA push
is attempted first. On the measured GitHub App workflows rejection, dest
`.github/workflows` is grafted onto the source tree so the rest of the
corpus still moves. Source SHA is recorded at refs/backup/source-main.

Does not remint host/repo_backup.py or host/moving_main_mirror.py.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any


SCHEMA_VERSION = "commons-live-mirror/v1"
SOURCE_REF = "refs/backup/source-main"
WORKFLOWS_DIR = ".github/workflows"
WORKFLOWS_PERMISSION_RE = re.compile(
    r"create or update workflow|without [`']workflows[`'] permission",
    re.IGNORECASE,
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class MirrorError(RuntimeError):
    """A live-mirror plan, graft, or push failed its measured contract."""


def _run(
    args: list[str],
    *,
    git_dir: str | None = None,
    check: bool = True,
    input_bytes: bytes | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    cmd = ["git"]
    if git_dir:
        cmd.extend(["--git-dir", git_dir])
    cmd.extend(args)
    completed = subprocess.run(
        cmd,
        input=input_bytes,
        capture_output=True,
        check=False,
        env=env,
    )
    if check and completed.returncode:
        detail = (completed.stderr or completed.stdout).decode("utf-8", "replace").strip()
        raise MirrorError(f"git {' '.join(args)} failed: {detail}")
    return completed


def classify_push_error(stderr: str) -> str:
    """Return WORKFLOWS_PERMISSION or OTHER for a git-push rejection."""
    text = str(stderr or "")
    if WORKFLOWS_PERMISSION_RE.search(text):
        return "WORKFLOWS_PERMISSION"
    return "OTHER"


def plan(src_sha: str, dst_sha: str, mirrored_sha: str | None = None) -> dict[str, Any]:
    """Decide whether backup main already carries this source SHA."""
    if not SHA_RE.fullmatch(src_sha or ""):
        raise MirrorError("src_sha is not a full object id")
    if dst_sha and not SHA_RE.fullmatch(dst_sha):
        raise MirrorError("dst_sha is not a full object id")
    if mirrored_sha and not SHA_RE.fullmatch(mirrored_sha):
        raise MirrorError("mirrored_sha is not a full object id")
    if src_sha == dst_sha:
        return {"action": "already_in_sync", "reason": "exact_sha", "src_sha": src_sha, "dst_sha": dst_sha}
    if mirrored_sha and src_sha == mirrored_sha:
        return {
            "action": "already_in_sync",
            "reason": "recorded_source",
            "src_sha": src_sha,
            "dst_sha": dst_sha,
            "mirrored_sha": mirrored_sha,
        }
    return {"action": "push", "src_sha": src_sha, "dst_sha": dst_sha, "mirrored_sha": mirrored_sha}


def _ls_tree(git_dir: str, tree: str) -> list[tuple[str, str, str, str]]:
    completed = _run(["ls-tree", "-z", tree], git_dir=git_dir)
    rows: list[tuple[str, str, str, str]] = []
    for entry in completed.stdout.split(b"\0"):
        if not entry:
            continue
        meta, name = entry.split(b"\t", 1)
        mode, typ, sha = meta.decode("ascii").split(" ")
        rows.append((mode, typ, sha, name.decode("utf-8")))
    return rows


def _mktree(git_dir: str, rows: list[tuple[str, str, str, str]]) -> str:
    payload = b"".join(
        f"{mode} {typ} {sha}\t{name}\0".encode("utf-8")
        for mode, typ, sha, name in sorted(rows, key=lambda row: row[3].encode("utf-8"))
    )
    completed = _run(["mktree", "-z"], git_dir=git_dir, input_bytes=payload)
    tree = completed.stdout.decode("ascii").strip()
    if not SHA_RE.fullmatch(tree):
        raise MirrorError("mktree did not return a tree id")
    return tree


def _replace_entry(
    git_dir: str,
    tree: str,
    name: str,
    new_mode: str | None,
    new_type: str | None,
    new_sha: str | None,
) -> str:
    rows = []
    found = False
    for mode, typ, sha, fname in _ls_tree(git_dir, tree):
        if fname == name:
            found = True
            if new_sha is not None:
                rows.append((new_mode or mode, new_type or typ, new_sha, fname))
            continue
        rows.append((mode, typ, sha, fname))
    if not found and new_sha is not None:
        rows.append((new_mode or "040000", new_type or "tree", new_sha, name))
    return _mktree(git_dir, rows)


def _path_tree(git_dir: str, commit: str, path: str) -> str | None:
    completed = _run(["rev-parse", "--verify", f"{commit}:{path}"], git_dir=git_dir, check=False)
    if completed.returncode:
        return None
    sha = completed.stdout.decode("ascii").strip()
    return sha if SHA_RE.fullmatch(sha) else None


def graft_dest_workflows(git_dir: str, src_commit: str, dst_commit: str | None) -> dict[str, Any]:
    """Replace source `.github/workflows` with dest's so GITHUB_TOKEN can push.

    Dest workflow blobs are kept byte-identical. New source workflow files are
    omitted. Dest workflow files missing from source are kept. Non-workflow
    paths stay on the source tree.
    """
    src_tree = _run(["rev-parse", f"{src_commit}^{{tree}}"], git_dir=git_dir).stdout.decode("ascii").strip()
    dst_wf = _path_tree(git_dir, dst_commit, WORKFLOWS_DIR) if dst_commit else None
    src_wf = _path_tree(git_dir, src_commit, WORKFLOWS_DIR)
    src_github = _path_tree(git_dir, src_commit, ".github")

    if dst_wf is None:
        if src_wf is None:
            return {
                "schema_version": SCHEMA_VERSION,
                "state": "UNCHANGED",
                "src_tree": src_tree,
                "grafted_tree": src_tree,
                "workflows_frozen": False,
                "workflows_omitted": False,
            }
        if src_github is None:
            raise MirrorError("source has workflows but no .github tree")
        github_rows = [row for row in _ls_tree(git_dir, src_github) if row[3] != "workflows"]
        if github_rows:
            new_github = _mktree(git_dir, github_rows)
            grafted = _replace_entry(git_dir, src_tree, ".github", "040000", "tree", new_github)
        else:
            grafted = _replace_entry(git_dir, src_tree, ".github", None, None, None)
        return {
            "schema_version": SCHEMA_VERSION,
            "state": "OMITTED",
            "src_tree": src_tree,
            "grafted_tree": grafted,
            "workflows_frozen": False,
            "workflows_omitted": True,
        }

    if src_github is None:
        new_github = _mktree(git_dir, [("040000", "tree", dst_wf, "workflows")])
    else:
        new_github = _replace_entry(git_dir, src_github, "workflows", "040000", "tree", dst_wf)
    grafted = _replace_entry(git_dir, src_tree, ".github", "040000", "tree", new_github)
    frozen = src_wf != dst_wf
    return {
        "schema_version": SCHEMA_VERSION,
        "state": "FROZEN" if frozen else "UNCHANGED",
        "src_tree": src_tree,
        "grafted_tree": grafted,
        "src_workflows": src_wf,
        "dst_workflows": dst_wf,
        "workflows_frozen": frozen,
        "workflows_omitted": False,
    }


def commit_graft(
    git_dir: str,
    src_commit: str,
    grafted_tree: str,
    message: str | None = None,
) -> str:
    src_commit = _run(["rev-parse", src_commit], git_dir=git_dir).stdout.decode("ascii").strip()
    body = message or (
        f"live-mirror: commons {src_commit} with dest workflow files preserved\n"
        "\n"
        "GITHUB_TOKEN cannot create or update .github/workflows without workflows "
        "permission. Non-workflow paths stay on the source tree. Source SHA is "
        f"recorded at {SOURCE_REF}.\n"
    )
    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", "github-actions[bot]")
    env.setdefault("GIT_AUTHOR_EMAIL", "41898282+github-actions[bot]@users.noreply.github.com")
    env.setdefault("GIT_COMMITTER_NAME", "github-actions[bot]")
    env.setdefault("GIT_COMMITTER_EMAIL", "41898282+github-actions[bot]@users.noreply.github.com")
    sha = _run(
        ["commit-tree", grafted_tree, "-p", src_commit, "-m", body],
        git_dir=git_dir,
        env=env,
    ).stdout.decode("ascii").strip()
    if not SHA_RE.fullmatch(sha):
        raise MirrorError("commit-tree did not return a commit id")
    return sha


def _push(git_dir: str, dest_url: str, refspec: str) -> subprocess.CompletedProcess[bytes]:
    return _run(["push", dest_url, refspec], git_dir=git_dir, check=False)


def push_mirror(
    git_dir: str,
    src_ref: str,
    dest_url: str,
    dst_ref: str | None = None,
) -> dict[str, Any]:
    """Exact-push source main; on workflows rejection, graft dest workflows and push."""
    src_sha = _run(["rev-parse", src_ref], git_dir=git_dir).stdout.decode("ascii").strip()
    dst_sha = None
    if dst_ref:
        completed = _run(["rev-parse", "--verify", dst_ref], git_dir=git_dir, check=False)
        if completed.returncode == 0:
            dst_sha = completed.stdout.decode("ascii").strip()

    exact = _push(git_dir, dest_url, f"{src_sha}:refs/heads/main")
    if exact.returncode == 0:
        _push(git_dir, dest_url, f"{src_sha}:{SOURCE_REF}")
        return {
            "schema_version": SCHEMA_VERSION,
            "state": "EXACT",
            "src_sha": src_sha,
            "pushed_sha": src_sha,
            "workflows_frozen": False,
        }

    stderr = (exact.stderr or exact.stdout).decode("utf-8", "replace")
    kind = classify_push_error(stderr)
    if kind != "WORKFLOWS_PERMISSION":
        raise MirrorError(f"exact push failed: {stderr.strip()}")

    graft = graft_dest_workflows(git_dir, src_sha, dst_sha)
    if graft["grafted_tree"] == graft["src_tree"]:
        raise MirrorError(
            "workflows permission rejected an exact push but grafted tree equals source tree: "
            + stderr.strip()
        )
    grafted_commit = commit_graft(git_dir, src_sha, graft["grafted_tree"])
    grafted = _push(git_dir, dest_url, f"{grafted_commit}:refs/heads/main")
    if grafted.returncode:
        detail = (grafted.stderr or grafted.stdout).decode("utf-8", "replace").strip()
        raise MirrorError(f"grafted push failed: {detail}")
    _push(git_dir, dest_url, f"{src_sha}:{SOURCE_REF}")
    return {
        "schema_version": SCHEMA_VERSION,
        "state": "GRAFTED",
        "src_sha": src_sha,
        "pushed_sha": grafted_commit,
        "grafted_tree": graft["grafted_tree"],
        "workflows_frozen": True,
        "first_error": stderr.strip().splitlines()[-1] if stderr.strip() else "workflows permission",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    classify = commands.add_parser("classify-error")
    classify.add_argument("--stderr", default="")
    classify.add_argument("--stderr-file", default=None)

    planned = commands.add_parser("plan")
    planned.add_argument("--src", required=True)
    planned.add_argument("--dst", required=True)
    planned.add_argument("--mirrored", default=None)

    graft = commands.add_parser("graft")
    graft.add_argument("--git-dir", required=True)
    graft.add_argument("--src-ref", required=True)
    graft.add_argument("--dst-ref", default=None)

    push = commands.add_parser("push")
    push.add_argument("--git-dir", required=True)
    push.add_argument("--src-ref", required=True)
    push.add_argument("--dst-ref", default=None)
    push.add_argument("--dest-url", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "classify-error":
            text = args.stderr
            if args.stderr_file:
                text = open(args.stderr_file, encoding="utf-8", errors="replace").read()
            payload = {"kind": classify_push_error(text)}
        elif args.command == "plan":
            payload = plan(args.src, args.dst, args.mirrored)
        elif args.command == "graft":
            payload = graft_dest_workflows(args.git_dir, args.src_ref, args.dst_ref)
        else:
            payload = push_mirror(args.git_dir, args.src_ref, args.dest_url, args.dst_ref)
        print(json.dumps(payload, sort_keys=True))
        return 0
    except MirrorError as error:
        print(f"LIVE_MIRROR_ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
