#!/usr/bin/env python3
"""Claim one pull-request work unit through Commons' atomic claim ledger.

PR review/merge drains use one canonical ``pr-N`` key.  This adapter owns the
single-key retry loop so a stale writer cannot overwrite a later winner after a
non-fast-forward race or because of modest clock skew between workers.
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


def _heartbeat(record):
    if not isinstance(record, dict):
        return None
    return cs._parse_ts(record.get("heartbeat_at") or record.get("taken_at"))


def _pr_holding_live(record, observed_now) -> bool:
    """Fail closed on a well-formed future heartbeat.

    ``coordination_state._holding_live`` intentionally requires a non-negative
    age.  For a distributed claim, however, a newer heartbeat is evidence of a
    winner or clock skew, never evidence that the claim expired.  Treat it as
    live so an older observer cannot steal the PR.
    """
    if cs._holding_live(record, observed_now):
        return True
    if not isinstance(record, dict) or record.get("state") != "HELD":
        return False
    beat = _heartbeat(record)
    ttl = record.get("ttl_s")
    return beat is not None and type(ttl) is int and 1 <= ttl <= 7200 and beat > observed_now


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
    """Take, renew, or release the canonical ``pr-N`` holding safely.

    Each retry re-reads ``state/claims`` and, unless a deterministic ``now`` was
    injected by a caller/test, observes a fresh clock *after* that read.  A
    non-fast-forward therefore cannot reuse a time that predates the winner it
    just discovered.  The commit format stays identical to the shared ledger.
    """
    if action not in {"take", "renew", "release"}:
        raise ValueError("action must be take, renew, or release")
    if not isinstance(holder, str) or not holder.strip():
        raise ValueError("holder must be non-empty text")
    if type(ttl_s) is not int or not 1 <= ttl_s <= 7200:
        raise ValueError("ttl must be between 1 and 7200 seconds")
    if type(attempts) is not int or attempts <= 0:
        raise ValueError("attempts must be a positive integer")

    holder = holder.strip()
    key = pr_key(pr)
    path = cs._holding_path(key)

    for _ in range(attempts):
        tip = cs._remote_tip(git, cs.HOLDINGS_BRANCH, remote)
        if tip:
            git.fetch([tip], remote)
        holdings = cs._read_holdings(git, tip)
        current = holdings.get(path)
        observed_now = now if now is not None else cs._now()
        live = _pr_holding_live(current, observed_now)

        if action == "take" and live and current.get("holder") != holder:
            return {
                "pr": pr,
                "action": action,
                "ok": False,
                "key": key,
                "held_by": current.get("holder"),
                "heartbeat_at": current.get("heartbeat_at"),
                "ttl_s": current.get("ttl_s"),
                "tip": tip,
            }
        if action in ("renew", "release") and (
            not current or current.get("holder") != holder
        ):
            return {
                "pr": pr,
                "action": action,
                "ok": False,
                "key": key,
                "held_by": (current or {}).get("holder"),
                "reason": "not the current holder",
                "tip": tip,
            }

        # Do not move this holder's heartbeat backwards if its prior timestamp
        # is ahead of this observer because of clock skew.
        beat = _heartbeat(current)
        write_now = (
            beat
            if live
            and current
            and current.get("holder") == holder
            and beat is not None
            and beat > observed_now
            else observed_now
        )
        stamp = cs._iso(write_now)
        record = dict(current or {})
        record.update(
            {
                "schema": cs.HOLDING_SCHEMA,
                "key": key,
                "holder": holder,
                "heartbeat_at": stamp,
                "ttl_s": ttl_s,
            }
        )
        if action == "take" and (
            not live or (current or {}).get("holder") != holder
        ):
            record["taken_at"] = stamp
            if current and current.get("holder") and current.get("holder") != holder:
                record["previous_holder"] = current.get("holder")
        record["state"] = "RELEASED" if action == "release" else "HELD"
        if note:
            record["note"] = note[:300]
        holdings[path] = record

        commit = cs._holdings_commit(
            git, tip, holdings, "%s %s by %s" % (action, key, holder), write_now
        )
        if not push:
            return {
                "pr": pr,
                "action": action,
                "ok": True,
                "key": key,
                "commit": commit,
                "pushed": False,
                "record": record,
                "push_line": "git -C %s push %s %s:refs/heads/%s"
                % (git.root, remote, commit, cs.HOLDINGS_BRANCH),
            }

        done = git.run(
            "push",
            remote,
            "%s:refs/heads/%s" % (commit, cs.HOLDINGS_BRANCH),
            check=False,
        )
        if done.returncode == 0:
            return {
                "pr": pr,
                "action": action,
                "ok": True,
                "key": key,
                "commit": commit,
                "pushed": True,
                "record": record,
            }
        if "non-fast-forward" not in done.stderr and "fetch first" not in done.stderr:
            return {
                "pr": pr,
                "action": action,
                "ok": False,
                "key": key,
                "reason": done.stderr.strip()[-300:],
            }
        # Another writer won. Loop from its tip and observe a fresh production
        # time before deciding whether that new record is live.

    return {
        "pr": pr,
        "action": action,
        "ok": False,
        "key": key,
        "reason": "branch kept moving; retry",
    }


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
