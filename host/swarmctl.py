#!/usr/bin/env python3
"""Tiny operator for the existing Commons claims/feed/seat runtime.

Use --url for the shared command center (one cache and provider quota pool).
Without --url this uses the same canonical state/claims branch through git.
--no-push produces a native GitHub Git Data publication proposal, not custody.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load(path, default=None):
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else default


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--url", default=os.environ.get("COMMONS_SWARM_URL"))
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--worker", default=os.environ.get("COMMONS_SEAT"))
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--output", type=Path, help="write full response to this file")
    commands = parser.add_subparsers(dest="command", required=True)
    sync = commands.add_parser("sync")
    sync.add_argument("--work-snapshot")
    sync.add_argument("--facts")
    sync.add_argument("--events")
    sync.add_argument("--max-calls", type=int, default=4)
    sync.add_argument("--cached", action="store_true", help="ingest existing evidence without provider calls")
    status = commands.add_parser("status")
    status.add_argument("--fresh", action="store_true")
    status.add_argument("--limit", type=int, default=100)
    for name in ("open", "take", "heartbeat", "ship", "block", "abandon", "next"):
        command = commands.add_parser(name)
        command.add_argument("task", nargs="?")
        command.add_argument("--operation-id")
        command.add_argument("--data", help="JSON operation metadata file (seat, capabilities, artifact, blocker)")
        command.add_argument("--blocker")
        command.add_argument("--next-action")
        command.add_argument("--feed-cursor")
    args = parser.parse_args(argv)
    try:
        if args.command == "sync":
            if not 0 <= args.max_calls <= 20:
                raise ValueError("max-calls must be between 0 and 20")
            payload = {"work_snapshot": load(args.work_snapshot), "provider_facts": load(args.facts, {}),
                       "events": load(args.events, []), "max_calls": args.max_calls,
                       "refresh_providers": not args.cached}
        elif args.command == "status":
            payload = {"refresh": args.fresh, "limit": args.limit, "worker": args.worker}
        else:
            payload = load(args.data, {})
            if not isinstance(payload, dict):
                raise ValueError("data must be a JSON object")
            for field, value in (("worker", args.worker), ("task_key", args.task),
                                 ("blocker", args.blocker), ("next_action", args.next_action),
                                 ("feed_cursor", args.feed_cursor)):
                if value is not None:
                    payload[field] = value
            operation_id = args.operation_id or payload.get("operation_id")
            if not operation_id:
                # Stable command replays; heartbeats advance in minute buckets.
                from host.swarm_runtime.runtime import now_iso
                seed = {"action": args.command, "payload": payload}
                if args.command in {"heartbeat", "next"}:
                    seed["minute"] = now_iso()[:16]
                operation_id = "cli-" + hashlib.sha256(json.dumps(seed, sort_keys=True).encode()).hexdigest()[:32]
            payload["operation_id"] = operation_id
            print("operation_id=" + operation_id, file=sys.stderr, flush=True)
        if args.url:
            if args.no_push:
                raise ValueError("--no-push applies to local Git Data proposals, not shared HTTP operations")
            request = urllib.request.Request(args.url.rstrip("/") + "/api/swarm/tasks",
                data=json.dumps({"action": args.command, **payload}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.load(response)
        else:
            from host.swarm_runtime.runtime import Runtime
            runtime = Runtime(args.root, state_dir=args.state_dir)
            if args.command == "status":
                result = runtime.read(**payload)
            elif args.command == "sync":
                result = runtime.sync(**payload, push=not args.no_push)
            else:
                result = runtime.operate(args.command, payload, push=not args.no_push)
        output = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
            print(json.dumps({"ok": result.get("ok"), "published": result.get("published"),
                              "output": str(args.output), "changed": result.get("changed")}))
        else:
            print(output, end="")
        if not result.get("ok", True):
            return 2
        if (result.get("result") or {}).get("rejected"):
            return 2
        return 0
    except Exception as exc:
        from host.swarm_runtime.store import StoreError
        if isinstance(exc, StoreError):
            error = exc.as_dict()
        else:
            error = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        print(json.dumps(error, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
