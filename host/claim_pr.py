#!/usr/bin/env python3
"""Claim one pull-request work unit through Commons' atomic claim ledger.

This is a thin PR-specific adapter over ``host.coordination_state``.  It keeps
review/merge drains on the canonical ``pr-N`` key so concurrent seats cannot
accidentally avoid collision detection by inventing different marker names for
the same pull request.
"""

from __future__ import annotations

import argparse
import json
import sys

try:
    from host import coordination_state as cs
except ImportError:  # Direct execution as ``python host/claim_pr.py``.
    import coordination_state as cs  # type: ignore


def pr_key(pr: int) -> str:
    """Return the one claim-ledger key for a GitHub pull request number."""
    if type(pr) is not int or pr <= 0:
        raise ValueError("pull request number must be a positive integer")
    return cs.change_key(pr=pr)


def write_pr_holding(
    git: cs.Git,
    pr: int,
    holder: str,
    action: str,
    *,
    ttl_s: int = 1800,
    note: str = "",
    now=None,
    remote: str = "origin",
    push: bool = True,
    attempts: int = 3,
) -> dict:
    """Take, renew, or release the canonical ``pr-N`` holding.

    The underlying fast-forward-only write and collision reconciliation stay in
    ``coordination_state.holding_write``; this adapter adds no second claim
    protocol.  Runtime retries are deliberately one shared-writer attempt at a
    time so each non-fast-forward retry observes a fresh clock.  An explicitly
    supplied ``now`` remains fixed for deterministic tests.
    """
    if action not in {"take", "renew", "release"}:
        raise ValueError("action must be take, renew, or release")
    if not isinstance(holder, str) or not holder.strip():
        raise ValueError("holder must be non-empty text")
    if type(ttl_s) is not int or not 1 <= ttl_s <= 7200:
        raise ValueError("ttl must be between 1 and 7200 seconds")
    if type(attempts) is not int or not 1 <= attempts <= 10:
        raise ValueError("attempts must be between 1 and 10")

    fixed_now = now
    result = None
    for _ in range(attempts):
        attempt_now = fixed_now if fixed_now is not None else cs._now()
        result = cs.holding_write(
            git,
            pr_key(pr),
            holder.strip(),
            action,
            ttl_s=ttl_s,
            note=note,
            now=attempt_now,
            remote=remote,
            push=push,
            attempts=1,
        )
        if result.get("ok") or result.get("reason") != "branch kept moving; retry":
            break
    return {"pr": pr, "action": action, **(result or {"ok": False, "reason": "no attempt"})}


def _positive_pr(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("PR must be an integer") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError("PR must be positive")
    return value


def _ttl(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("TTL must be an integer") from exc
    if not 1 <= value <= 7200:
        raise argparse.ArgumentTypeError("TTL must be between 1 and 7200 seconds")
    return value


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Atomically take/renew/release the canonical claim for one pull request"
    )
    parser.add_argument("action", choices=("take", "renew", "release"))
    parser.add_argument("pr", type=_positive_pr)
    parser.add_argument("--holder", required=True)
    parser.add_argument("--ttl", type=_ttl, default=1800)
    parser.add_argument("--note", default="")
    parser.add_argument("--git-root", default=None, help="checkout used for git plumbing")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--no-push", action="store_true")
    args = parser.parse_args(argv)

    git = cs.Git(args.git_root or cs.ROOT)
    try:
        result = write_pr_holding(
            git,
            args.pr,
            args.holder,
            args.action,
            ttl_s=args.ttl,
            note=args.note,
            remote=args.remote,
            push=not args.no_push,
        )
    except (ValueError, cs.GitError) as exc:
        result = {"ok": False, "pr": args.pr, "action": args.action, "reason": str(exc)}
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
