#!/usr/bin/env python3
"""Atomic alias holdings for Commons coordination claims.

The legacy coordination_state holder API remains valid for a single key.
This wrapper lets one logical claim reserve its canonical target key and
operation/content aliases in one state/claims commit, so differently named
workers cannot both own the same PR target.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

try:
    from host import coordination_state as cs
except ImportError:  # direct `python host/coordination_claims.py`
    import coordination_state as cs

_KEY_RE = re.compile(r"^[A-Za-z0-9._-]{1,96}$")


def alias_keys(operation="", pr=None, content=""):
    """Return the deterministic alias set for one logical claim."""
    keys = []
    if operation:
        keys.append(cs.change_key(value=operation))
    if pr is not None:
        keys.append(cs.change_key(pr=pr))
    if content:
        keys.append(cs.change_key(content=content))
    keys = sorted(set(keys))
    if not keys:
        raise ValueError("claim needs --operation, --pr, or --content")
    for key in keys:
        if not _KEY_RE.fullmatch(key):
            raise ValueError("unsafe claim key: %r" % key)
    return keys


def holding_write_aliases(
    git,
    keys,
    holder,
    action,
    ttl_s=1800,
    note="",
    now=None,
    remote="origin",
    branch=cs.HOLDINGS_BRANCH,
    push=True,
    attempts=3,
):
    """Take, renew, or release all aliases atomically.

    Every alias is checked against the same branch tip before any record is
    changed. A live conflicting alias aborts the whole operation. A rejected
    non-fast-forward push re-reads every alias before retrying.
    """
    keys = sorted(set(keys))
    if not keys:
        raise ValueError("at least one alias is required")
    if not isinstance(holder, str) or not holder.strip():
        raise ValueError("holder must be non-empty")
    if action not in ("take", "renew", "release"):
        raise ValueError("action must be take, renew, or release")
    if type(ttl_s) is not int or not 1 <= ttl_s <= 7200:
        raise ValueError("ttl must be between 1 and 7200 seconds")
    for key in keys:
        if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
            raise ValueError("unsafe claim key: %r" % key)

    holder = holder.strip()
    now = now or cs._now()
    for _ in range(attempts):
        tip = cs._remote_tip(git, branch, remote)
        if tip:
            git.fetch([tip], remote)
        holdings = cs._read_holdings(git, tip)

        conflicts = []
        for key in keys:
            current = holdings.get(cs._holding_path(key))
            live = cs._holding_live(current, now)
            if action == "take":
                if live and current.get("holder") != holder:
                    conflicts.append({
                        "key": key,
                        "held_by": current.get("holder"),
                        "heartbeat_at": current.get("heartbeat_at"),
                        "ttl_s": current.get("ttl_s"),
                    })
            elif not current or current.get("holder") != holder:
                conflicts.append({
                    "key": key,
                    "held_by": (current or {}).get("holder"),
                    "reason": "not the current holder",
                })
        if conflicts:
            return {
                "ok": False,
                "keys": keys,
                "conflicts": conflicts,
                "held_by": conflicts[0].get("held_by"),
                "tip": tip,
            }

        stamp = cs._iso(now)
        records = {}
        for key in keys:
            path = cs._holding_path(key)
            current = holdings.get(path)
            live = cs._holding_live(current, now)
            record = dict(current or {})
            record.update({
                "schema": cs.HOLDING_SCHEMA,
                "key": key,
                "holder": holder,
                "heartbeat_at": stamp,
                "ttl_s": ttl_s,
                "aliases": keys,
                "state": "RELEASED" if action == "release" else "HELD",
            })
            if action == "take" and (not live or (current or {}).get("holder") != holder):
                record["taken_at"] = stamp
                if current and current.get("holder") and current.get("holder") != holder:
                    record["previous_holder"] = current.get("holder")
            if note:
                record["note"] = note[:300]
            holdings[path] = record
            records[key] = record

        message = "%s aliases %s by %s" % (action, ",".join(keys), holder)
        commit = cs._holdings_commit(git, tip, holdings, message, now)
        if not push:
            return {
                "ok": True,
                "keys": keys,
                "commit": commit,
                "pushed": False,
                "records": records,
                "push_line": "git -C %s push %s %s:refs/heads/%s"
                % (git.root, remote, commit, branch),
            }
        done = git.run(
            "push",
            remote,
            "%s:refs/heads/%s" % (commit, branch),
            check=False,
        )
        if done.returncode == 0:
            return {
                "ok": True,
                "keys": keys,
                "commit": commit,
                "pushed": True,
                "records": records,
            }
        if "non-fast-forward" not in done.stderr and "fetch first" not in done.stderr:
            return {
                "ok": False,
                "keys": keys,
                "reason": done.stderr.strip()[-300:],
            }
        # Another peer wrote first. Retry from the new tip and re-check every alias.
    return {"ok": False, "keys": keys, "reason": "branch kept moving; retry"}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Atomically hold canonical Commons claim aliases"
    )
    ap.add_argument("--git-root", default=None)
    ap.add_argument("--remote", default="origin")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("take", "renew", "release"):
        command = sub.add_parser(name)
        command.add_argument("--holder", required=True)
        command.add_argument("--operation", default="")
        command.add_argument("--pr", type=int)
        command.add_argument("--content", default="")
        command.add_argument("--ttl", type=int, default=1800)
        command.add_argument("--note", default="")
        command.add_argument("--no-push", action="store_true")
    sub.add_parser("holders")

    args = ap.parse_args(argv)
    git = cs.Git(args.git_root or cs.ROOT)
    if args.cmd == "holders":
        print(json.dumps(cs.holdings_list(git, args.remote), indent=1))
        return 0

    try:
        keys = alias_keys(args.operation, args.pr, args.content)
        result = holding_write_aliases(
            git,
            keys,
            args.holder,
            args.cmd,
            ttl_s=args.ttl,
            note=args.note,
            remote=args.remote,
            push=not args.no_push,
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}, indent=1))
        return 2
    print(json.dumps(result, indent=1))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
