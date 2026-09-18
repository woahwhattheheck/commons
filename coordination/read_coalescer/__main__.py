"""Explicit one-shot CLI. A WAIT result never performs an internal retry."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

from .core import Broker, InvalidInput, Page, Policy, ReadRequest, strict_loads
from .slack_reader import SlackReader


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="private SQLite file on one host's local filesystem")
    parser.add_argument("--policy", help="JSON policy; every worker must use the same complete configuration")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stats")
    maintenance = sub.add_parser("maintain")
    maintenance.add_argument("--retain-ms", type=int, default=3_600_000)
    sub.add_parser("demo", help="offline deterministic fake-provider demonstration, never Slack")
    read = sub.add_parser("slack-read", help="one optional live Slack read; no retries and no sends")
    read.add_argument("--app", required=True)
    read.add_argument("--workspace", required=True)
    read.add_argument("--visibility-epoch", required=True, help="trusted adapter permission-generation id")
    read.add_argument("--method", required=True)
    read.add_argument("--params", required=True, help="path to bounded JSON query object, no credentials")
    read.add_argument("--token-env", default="SLACK_READ_TOKEN", help="environment variable NAME, not its value")
    read.add_argument("--ttl-ms", type=int, default=5000)
    read.add_argument("--max-age-ms", type=int)
    args = parser.parse_args(argv)
    try:
        policy = Policy()
        if args.policy:
            with open(args.policy, "rb") as handle:
                values = strict_loads(handle.read(65_537), 65_536)
            if type(values) is not dict:
                raise InvalidInput("policy must be an object")
            policy = Policy(**values)
        broker = Broker(args.db, policy)
        if args.command == "stats":
            output, code = broker.stats(), 0
        elif args.command == "maintain":
            output, code = broker.maintain(retain_ms=args.retain_ms), 0
        elif args.command == "demo":
            request = ReadRequest.make(provider="offline-demo", app="demo", workspace="demo",
                method="conversations.history", access_scope="synthetic", params={"channel": "CDEMO", "limit": 2})
            calls = 0
            def synthetic_reader(_: ReadRequest) -> Page:
                nonlocal calls
                calls += 1
                return Page({"ok": True, "messages": [{"text": "synthetic only"}],
                             "response_metadata": {"next_cursor": "page2"}}, False, "page2")
            first = broker.read_once(request, synthetic_reader)
            second = broker.read_once(request, synthetic_reader)
            output = {"scenario": "OFFLINE_SYNTHETIC", "provider_callback_calls_this_process": calls,
                "first": first.public_dict(), "second": second.public_dict(), "stats": broker.stats()}
            code = 0 if first.status in ("FETCHED", "CACHE") and second.status == "CACHE" else 2
        else:
            if policy.lease_ms <= 12_000:
                raise InvalidInput("Slack CLI lease_ms must exceed its 10-second transport timeout plus margin")
            token = os.environ.get(args.token_env)
            if not token:
                raise InvalidInput("the named credential environment variable is unset")
            with open(args.params, "rb") as handle:
                params = strict_loads(handle.read(65_537), 65_536)
            reader = SlackReader(token=token, app=args.app, workspace=args.workspace,
                visibility_epoch=args.visibility_epoch)
            result = broker.read_once(reader.request(args.method, params), reader,
                ttl_ms=args.ttl_ms, max_age_ms=args.max_age_ms)
            output = result.public_dict()
            code = 0 if result.status in ("FETCHED", "CACHE") else (2 if result.status == "WAIT" else 3)
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
        return code
    except (InvalidInput, TypeError, OSError, sqlite3.Error):
        # Do not print tokens, sensitive filesystem contents or credential-bearing
        # network error messages. Troubleshoot the local adapter separately.
        print(json.dumps({"status": "ERROR", "reason": "LOCAL_CONFIGURATION_OR_STORAGE_ERROR",
                          "send_authorized": False}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
