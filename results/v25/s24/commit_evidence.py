#!/usr/bin/env python3
"""Commit unique S24 H evidence onto the live tip of a ref. Never force-push.

The holdout executes on a detached triggering SHA so later branch motion cannot
change the games. Evidence lives under a unique run-id directory, so it can be
committed on top of whatever the live target ref currently is: an earlier
serialized evidence commit, a merge, or origin/main if the branch is gone.
The manifest already binds evidence_branch_head and triggering_head_sha.

Measured failure: run 34383948697 committed on detached 698ec9bc then
`git push origin HEAD:$GITHUB_HEAD_REF` was rejected non-fast-forward because
run 34380863095 had already fast-forwarded the same branch with sibling
evidence. Unique paths do not need to stay parented at the triggering SHA.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FORCE_FLAGS = ("--force", "-f", "--force-with-lease", "--force-if-includes")


class GitError(RuntimeError):
    pass


def _looks_like_force(args: list[str]) -> str | None:
    tokens = list(args)
    for i, token in enumerate(tokens):
        if token in FORCE_FLAGS:
            return token
        if token.startswith("--force"):
            return token
        if token == "-f":
            return token
        # git push -u -f origin HEAD:ref
        if token.startswith("-") and not token.startswith("--") and "f" in token[1:] and token != "--":
            # allow --foo; reject -fu / -uf
            if token != "-C" and "f" in token[1:] and all(c in "ufnqe" for c in token[1:]):
                return token
    return None


def run_git(repo: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    forced = _looks_like_force(args)
    if forced:
        raise GitError(f"refusing git force flag {forced}")
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise GitError(f"git {' '.join(args)} failed ({proc.returncode}): {detail}")
    return proc


def fetch_base(repo: Path, remote: str, target_ref: str) -> str:
    """Return the live tip SHA to parent the evidence commit on."""
    target = run_git(repo, ["fetch", remote, f"refs/heads/{target_ref}"], check=False)
    if target.returncode == 0:
        return run_git(repo, ["rev-parse", "FETCH_HEAD"]).stdout.strip()
    main = run_git(repo, ["fetch", remote, "refs/heads/main"], check=False)
    if main.returncode != 0:
        raise GitError(
            f"target ref {target_ref!r} missing and fetching main failed: "
            f"{(main.stderr or target.stderr or '').strip()}"
        )
    return run_git(repo, ["rev-parse", "FETCH_HEAD"]).stdout.strip()


def _files(root: Path) -> list[Path]:
    return sorted(p.relative_to(root) for p in root.rglob("*") if p.is_file())


def same_tree(left: Path, right: Path) -> bool:
    if not left.is_dir() or not right.is_dir():
        return False
    a, b = _files(left), _files(right)
    if a != b:
        return False
    return all((left / rel).read_bytes() == (right / rel).read_bytes() for rel in a)


def _copy_evidence(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)


def commit_evidence(
    repo: Path,
    evidence_dir: Path,
    target_ref: str,
    run_id: str,
    remote: str = "origin",
    message: str | None = None,
    retries: int = 1,
) -> dict:
    repo = repo.resolve()
    evidence_dir = evidence_dir.resolve()
    if not evidence_dir.is_dir():
        raise GitError(f"missing evidence dir {evidence_dir}")
    if not target_ref or target_ref.startswith("-") or ".." in target_ref or "\n" in target_ref:
        raise GitError(f"invalid target ref {target_ref!r}")
    try:
        rel = evidence_dir.relative_to(repo)
    except ValueError:
        rel = Path("results/v25/s24/official-h") / evidence_dir.name

    msg = message or f"S24 frozen champion robustness H evidence [{run_id}]"
    last_err = "no attempt"
    for attempt in range(retries + 1):
        stash = Path(tempfile.mkdtemp(prefix="s24-ev-"))
        copied = stash / evidence_dir.name
        shutil.copytree(evidence_dir, copied)
        try:
            base = fetch_base(repo, remote, target_ref)
            dest = repo / rel
            # Holdout output is already copied aside. Drop the working-tree copy
            # so `git switch` can materialize a live-tip version of the same
            # unique path when it is already tracked.
            if dest.exists():
                shutil.rmtree(dest)
            run_git(repo, ["switch", "--detach", base])
            tracked = bool(
                run_git(repo, ["ls-files", "--", str(rel)]).stdout.strip()
            )
            if tracked and dest.exists() and same_tree(dest, copied):
                push = run_git(repo, ["push", remote, f"HEAD:refs/heads/{target_ref}"], check=False)
                if push.returncode == 0:
                    return {
                        "status": "already-present",
                        "base": base,
                        "target_ref": target_ref,
                        "path": str(rel),
                    }
                last_err = (push.stderr or push.stdout or "").strip()
                continue
            if tracked and dest.exists() and not same_tree(dest, copied):
                raise GitError(f"evidence path {rel} exists with different bytes; refusing overwrite")
            # Untracked holdout output may already occupy dest; tracked files at
            # this unique path are the only overwrite risk.
            _copy_evidence(copied, dest)
            run_git(repo, ["add", "--", str(rel)])
            cached = run_git(repo, ["diff", "--cached", "--quiet"], check=False)
            if cached.returncode == 0:
                return {
                    "status": "no-op",
                    "base": base,
                    "target_ref": target_ref,
                    "path": str(rel),
                }
            run_git(repo, ["commit", "-m", msg])
            push = run_git(repo, ["push", remote, f"HEAD:refs/heads/{target_ref}"], check=False)
            if push.returncode == 0:
                sha = run_git(repo, ["rev-parse", "HEAD"]).stdout.strip()
                return {
                    "status": "pushed",
                    "sha": sha,
                    "base": base,
                    "target_ref": target_ref,
                    "path": str(rel),
                    "attempt": attempt,
                }
            err = ((push.stderr or "") + "\n" + (push.stdout or "")).strip()
            last_err = err
            if "non-fast-forward" in err or "failed to push some refs" in err:
                continue
            raise GitError(f"push failed: {err}")
        finally:
            shutil.rmtree(stash, ignore_errors=True)
    raise GitError(f"push rejected after retries: {last_err}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--target-ref", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    result = commit_evidence(
        Path(args.repo),
        Path(args.evidence_dir),
        args.target_ref,
        args.run_id,
        args.remote,
    )
    print(result)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GitError as exc:
        print(f"commit_evidence: {exc}", file=sys.stderr)
        raise SystemExit(1)
