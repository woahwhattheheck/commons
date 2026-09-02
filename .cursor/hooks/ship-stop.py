#!/usr/bin/env python3
"""Cursor stop hook: refuse to idle-stop with unshipped git work."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any


FOLLOWUP = """SHIP NOW. Default behavior: leave no work unshipped.

1. Confirm git remotes are woahwhattheheck, never tokenjunkielabs. If a remote is tokenjunkielabs, move this work onto the matching woahwhattheheck repo before committing.
2. git fetch origin; rebase onto the latest default branch.
3. Account for peer branches/PRs. Unique paths: continue. Same paths with a semantic conflict: keep your files, do not overwrite peers, do not freeze.
4. Commit, push, open or update a non-draft PR against current main. Merge when paths are unique or compatible. Respect explicit HOLD / no-merge titles.
5. Do not edit CLAUDE.md, AGENTS.md, or .claude/** unless this task is explicitly Claude Code.
6. Automations follow the same law.

Evidence:
{evidence}
"""


def git(repo: str, *args: str) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def repo_root() -> str | None:
    code, out, _ = git(".", "rev-parse", "--show-toplevel")
    if code != 0 or not out:
        cwd = os.getcwd()
        code, out, _ = git(cwd, "rev-parse", "--show-toplevel")
        if code != 0 or not out:
            return None
    return out


def collect(repo: str) -> list[str]:
    evidence: list[str] = []
    _, porcelain, _ = git(repo, "status", "--porcelain")
    if porcelain:
        dirty = [line for line in porcelain.splitlines() if line.strip()]
        evidence.append(f"dirty files ({len(dirty)}): " + "; ".join(dirty[:12]))

    _, branch, _ = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if branch:
        evidence.append(f"branch: {branch}")

    _, remotes, _ = git(repo, "remote", "-v")
    if "tokenjunkielabs" in remotes.lower():
        evidence.append("WRONG GITHUB: a remote points at tokenjunkielabs; move this work to woahwhattheheck")

    _, upstream, _ = git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if branch and branch not in {"main", "master", "HEAD"}:
        if not upstream:
            evidence.append(f"{branch} has no upstream — push and open a non-draft PR")
        else:
            git(repo, "fetch", "--quiet")
            _, counts, _ = git(repo, "rev-list", "--left-right", "--count", f"{upstream}...HEAD")
            if counts:
                behind, _, ahead = counts.partition("\t")
                if not ahead:
                    behind, _, ahead = counts.partition(" ")
                try:
                    ahead_n = int(ahead or "0")
                except ValueError:
                    ahead_n = 0
                if ahead_n:
                    evidence.append(f"{ahead_n} unpushed commit(s) vs {upstream}")

    _, unpushed, _ = git(repo, "log", "--oneline", "@{u}..HEAD")
    if unpushed:
        commits = unpushed.splitlines()
        evidence.append(f"unpushed ({len(commits)}): " + "; ".join(commits[:8]))

    return evidence


def decide(payload: dict[str, Any], evidence: list[str]) -> dict[str, Any]:
    if payload.get("status") == "aborted":
        return {}
    try:
        loop_count = int(payload.get("loop_count") or 0)
    except (TypeError, ValueError):
        loop_count = 0
    if loop_count >= 3:
        return {}
    needs_ship = any(
        item.startswith("dirty ")
        or "unpushed" in item
        or "WRONG GITHUB" in item
        or "no upstream" in item
        for item in evidence
    )
    if not needs_ship:
        return {}
    return {"followup_message": FOLLOWUP.format(evidence="\n".join(f"- {item}" for item in evidence))}


def main() -> None:
    raw = sys.stdin.read() if not sys.stdin.isatty() else "{}"
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    root = repo_root()
    evidence = collect(root) if root else ["not a git checkout"]
    sys.stdout.write(json.dumps(decide(payload, evidence)))


if __name__ == "__main__":
    main()
