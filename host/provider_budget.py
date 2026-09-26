#!/usr/bin/env python3
"""Cooperating GitHub publication admission using the existing request budget.

Every caller must use the same state directory. Renew before each connector
write, keep its operation ID on uncertainty, and release the lease in finally.
This command performs no provider calls and never sleeps or schedules retries.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.command_center.request_budget import RequestBudget, RequestDeferred

SCOPE = "github:publication"
# Preserve the existing provider-wide and primary-core cooldown identities.
SHARED_SCOPES = ("github:GET", "github:GET:core")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    configure = commands.add_parser("configure", help="coordinator sets the shared concurrency cap")
    configure.add_argument("--capacity", type=int, required=True)
    commands.add_parser("status")
    acquire = commands.add_parser("acquire", help="admit one publication per unique holder")
    renew = commands.add_parser("renew", help="check ownership/cooldown and extend before each write")
    release = commands.add_parser("release")
    release.add_argument("--successful", action="store_true", help="reset expired fallback after confirmed provider success")
    for command in (acquire, renew, release):
        command.add_argument("--holder", required=True)
    for command in (acquire, renew):
        command.add_argument("--ttl-seconds", type=int, default=300)
    for command in (renew, release):
        command.add_argument("--lease-id", required=True)
    limited = commands.add_parser("limited", help="record observed provider rate-limit evidence")
    limited.add_argument("--retry-after", help="provider seconds or HTTP date; omit if unavailable")
    limited.add_argument("--reset-at", type=float, help="provider reset epoch when primary quota is exhausted")
    limited.add_argument("--primary-core", action="store_true", help="only for confirmed primary core quota exhaustion")
    args = parser.parse_args(argv)
    try:
        args.state_dir.mkdir(parents=True, exist_ok=True)
        budget = RequestBudget(args.state_dir)
        if args.command == "configure":
            result = budget.set_capacity(SCOPE, args.capacity)
        elif args.command == "status":
            result = budget.lease_status(SCOPE, shared_scopes=SHARED_SCOPES)
        elif args.command == "acquire":
            result = budget.acquire_lease(SCOPE, args.holder, ttl_seconds=args.ttl_seconds,
                                          shared_scopes=SHARED_SCOPES)
        elif args.command == "renew":
            result = budget.renew_lease(SCOPE, args.holder, args.lease_id, ttl_seconds=args.ttl_seconds,
                                        shared_scopes=SHARED_SCOPES)
        elif args.command == "release":
            result = budget.release_lease(SCOPE, args.holder, args.lease_id)
            if result["released"] and args.successful:
                budget.succeeded(SCOPE, shared_scopes=SHARED_SCOPES)
        else:
            scope = "github:GET:core" if args.primary_core else "github:GET"
            result = budget.rate_limited(scope, args.retry_after,
                                         reset_at=args.reset_at if args.primary_core else None)
        print(json.dumps({"ok": True, **result}), flush=True)
        return 0
    except RequestDeferred as exc:
        print(json.dumps({"ok": False, "error": "provider_admission_deferred", "scope": exc.scope,
                          "reason": exc.reason, "retry_not_before": exc.retry_not_before}), flush=True)
        return 75
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"ok": False, "error": "provider_admission_failed", "message": str(exc)}), flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
