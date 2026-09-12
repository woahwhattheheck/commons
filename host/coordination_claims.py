#!/usr/bin/env python3
"""Atomic alias holdings for Commons coordination claims.

One logical claim may reserve its canonical target key plus operation/content
aliases in a single state/claims commit. Persisted alias sets are authoritative
across later take/renew/release calls, so a caller cannot accidentally revive or
extend only one member of a logical claim.

The legacy coordination_state single-key holder remains available for legacy
uses, but canonical PR claims must not mix the two APIs: the old writer does not
carry multi-alias continuity.
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


def _validate_keys(keys):
    out = sorted(set(keys))
    if not out:
        raise ValueError("at least one alias is required")
    for key in out:
        if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
            raise ValueError("unsafe claim key: %r" % key)
    return out


def alias_keys(operation="", pr=None, content=""):
    """Return the deterministic alias set for one logical claim."""
    keys = []
    if operation:
        keys.append(cs.change_key(value=operation))
    if pr is not None:
        if type(pr) is not int or pr <= 0:
            raise ValueError("pr must be a positive integer")
        keys.append(cs.change_key(pr=pr))
    if content:
        keys.append(cs.change_key(content=content))
    if not keys:
        raise ValueError("claim needs --operation, --pr, or --content")
    return _validate_keys(keys)


def _expand_persisted_aliases(holdings, requested):
    """Close requested keys over every persisted aliases[] relation.

    Alias continuity is part of the stored claim, not caller discipline. A
    later subset renew/take/release therefore re-binds to the full persisted
    logical claim before any conflict check or write.
    """
    resolved = set(_validate_keys(requested))
    queue = list(resolved)
    while queue:
        key = queue.pop()
        record = holdings.get(cs._holding_path(key))
        if not isinstance(record, dict) or "aliases" not in record:
            continue
        aliases = record.get("aliases")
        if not isinstance(aliases, list) or not aliases:
            raise ValueError("invalid persisted alias set for %s" % key)
        for alias in _validate_keys(aliases):
            if alias not in resolved:
                resolved.add(alias)
                queue.append(alias)
    return sorted(resolved)


def _live_fail_closed(record, observed_now):
    """Legacy liveness plus future-heartbeat safety for clock/race skew."""
    if cs._holding_live(record, observed_now):
        return True
    if not isinstance(record, dict) or record.get("state") != "HELD":
        return False
    beat = cs._parse_ts(record.get("heartbeat_at") or record.get("taken_at"))
    ttl = record.get("ttl_s")
    # A heartbeat newer than this observer is not proof of expiry. Treat it as
    # live so clock skew or an NFF winner cannot be overwritten by an older
    # observer.
    return beat is not None and type(ttl) is int and 1 <= ttl <= 7200 and beat > observed_now


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
    """Take, renew, or release a persisted logical alias set atomically.

    Every retry re-reads the branch tip, re-expands the persisted alias closure,
    and (for production calls where ``now`` is omitted) observes a fresh clock
    after that read. A conflict aborts before any alias record is mutated.
    """
    requested = _validate_keys(keys)
    if not isinstance(holder, str) or not holder.strip():
        raise ValueError("holder must be non-empty")
    if action not in ("take", "renew", "release"):
        raise ValueError("action must be take, renew, or release")
    if type(ttl_s) is not int or not 1 <= ttl_s <= 7200:
        raise ValueError("ttl must be between 1 and 7200 seconds")

    holder = holder.strip()
    last_keys = requested
    for _ in range(attempts):
        tip = cs._remote_tip(git, branch, remote)
        if tip:
            git.fetch([tip], remote)
        holdings = cs._read_holdings(git, tip)
        keys_now = _expand_persisted_aliases(holdings, requested)
        last_keys = keys_now
        observed_now = now if now is not None else cs._now()

        conflicts = []
        for key in keys_now:
            current = holdings.get(cs._holding_path(key))
            live = _live_fail_closed(current, observed_now)
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
                "keys": keys_now,
                "conflicts": conflicts,
                "held_by": conflicts[0].get("held_by"),
                "tip": tip,
            }

        stamp = cs._iso(observed_now)
        records = {}
        for key in keys_now:
            path = cs._holding_path(key)
            current = holdings.get(path)
            live = _live_fail_closed(current, observed_now)
            record = dict(current or {})
            record.update({
                "schema": cs.HOLDING_SCHEMA,
                "key": key,
                "holder": holder,
                "heartbeat_at": stamp,
                "ttl_s": ttl_s,
                "aliases": keys_now,
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

        message = "%s aliases %s by %s" % (action, ",".join(keys_now), holder)
        commit = cs._holdings_commit(git, tip, holdings, message, observed_now)
        if not push:
            return {
                "ok": True,
                "keys": keys_now,
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
                "keys": keys_now,
                "commit": commit,
                "pushed": True,
                "records": records,
            }
        if "non-fast-forward" not in done.stderr and "fetch first" not in done.stderr:
            return {
                "ok": False,
                "keys": keys_now,
                "reason": done.stderr.strip()[-300:],
            }
        # Another peer wrote first. Loop from the new tip, alias closure, and
        # a fresh production clock before deciding whether that winner is live.
    return {"ok": False, "keys": last_keys, "reason": "branch kept moving; retry"}


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
