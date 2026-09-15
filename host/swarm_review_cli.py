#!/usr/bin/env python3
"""Non-executable CLI dispatcher for the hardened Commons swarm-review surface."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

_PATCHED = (
    "actions_authorities",
    "exact_execution_pass",
    "change",
    "review_template",
    "live_pull",
    "verify_live",
)


def _require_hardened(surface):
    """Fail closed unless the wrapper has installed every authority gate."""
    core = getattr(surface, "_core", None)
    if core is None or not hasattr(surface, "_pr_identity"):
        raise RuntimeError("CLI requires hardened swarm_review front door")
    for name in _PATCHED:
        if getattr(core, name, None) is not getattr(surface, name, None):
            raise RuntimeError("unpatched swarm-review authority gate: " + name)
    return surface


def run(surface, argv=None):
    """Run packet/check/merge only through an already-hardened wrapper module."""
    surface = _require_hardened(surface)
    cs = surface.cs
    parser = argparse.ArgumentParser(description=surface.__doc__)
    parser.add_argument("--repo", default=cs.DEFAULT_REPO)
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    packet = sub.add_parser("packet")
    packet.add_argument("--prs", required=True)
    packet.add_argument("--out", required=True)
    check = sub.add_parser("check")
    check.add_argument("--pr", type=int, required=True)
    merge = sub.add_parser("merge")
    merge.add_argument("--pr", type=int, required=True)
    args = parser.parse_args(argv)
    git = cs.Git(str(Path(args.root).resolve()))
    github = cs.GitHub(args.repo, cs.discover_token())
    try:
        if args.command == "packet":
            numbers = list(dict.fromkeys(int(n) for n in args.prs.split(",")))
            if not 1 <= len(numbers) <= 10:
                raise ValueError("one packet holds 1–10 PRs")
            entries = []
            for number in numbers:
                subject, verdict = surface.verify_live(git, github, number)
                diff = git.out("diff", "--no-ext-diff", "--no-textconv",
                               subject["merge_base"], subject["head"], "--", *subject["paths"])
                entries.append({**subject, "review": verdict,
                                "diff": diff[:60000], "diff_truncated": len(diff) > 60000,
                                "review_template": surface.review_template(subject)})
            output = {"schema": "commons-review-packet/v1", "observed_at": cs._iso(cs._now()),
                      "prs": entries, "note": "GPT must read omitted diff content before approving; no automatic approval."}
            Path(args.out).write_text(json.dumps(output, indent=2) + "\n")
            print(json.dumps({"written": args.out, "prs": numbers}))
            return 0
        subject, verdict = surface.verify_live(git, github, args.pr)
        if verdict["state"] != "READY":
            print(json.dumps(verdict))
            return 1
        if args.command == "merge":
            # Re-read immediately before mutation. GitHub also checks head SHA.
            subject, verdict = surface.verify_live(git, github, args.pr)
            if verdict["state"] != "READY":
                print(json.dumps(verdict))
                return 1
            # Publish a merge commit with the reviewed main as its first parent.
            # A normal fast-forward push rejects a concurrent main advance;
            # REST /pulls/N/merge checks head but cannot compare-and-swap base.
            changes = git.diff_tree(subject["merge_base"], subject["head"])
            tree = git.compose(subject["main"], changes)
            commit = git.out("commit-tree", tree, "-p", subject["main"], "-p", subject["head"],
                             "-m", "Merge reviewed Commons PR #" + str(args.pr),
                             env=cs._commit_env()).strip()
            pushed = git.run("push", "origin", commit + ":refs/heads/main", check=False)
            print(json.dumps({"merged": pushed.returncode == 0, "sha": commit,
                              "reviewed_head": subject["head"], "reviewed_base": subject["main"],
                              "reason": "landed" if pushed.returncode == 0 else
                              "push rejected; re-read main and recompute, never force"}))
            return 0 if pushed.returncode == 0 else 1
        print(json.dumps(verdict))
        return 0
    except (ValueError, cs.GitError, cs.GitHubError) as exc:
        print(json.dumps({"state": "UNKNOWN", "reason": str(exc)[:300]}))
        return 1
