#!/usr/bin/env python3
"""Peer client for the headless Claude gateway (build demand C1, CLEAT's half).

The thing a peer in another harness imports or runs to drive Claude through
TENON's loopback gateway (`integrations/claude_headless/gateway.py`, port
8879). Stdlib only. Every command prints one JSON document. A prompt of ``-``
reads stdin.

    python integrations/claude_headless/client.py health
    python integrations/claude_headless/client.py submit "prompt" --peer MYSEAT --label task --wait 300
    python integrations/claude_headless/client.py status RUN_ID [--wait 300]
    python integrations/claude_headless/client.py events RUN_ID [--after N] [--follow]
    python integrations/claude_headless/client.py followup RUN_ID "next prompt" --wait 300
    python integrations/claude_headless/client.py resume SESSION_ID "continue" --wait 300
    python integrations/claude_headless/client.py session SESSION_ID
    python integrations/claude_headless/client.py cancel RUN_ID
    python integrations/claude_headless/client.py recover
    python integrations/claude_headless/client.py tail [--after N] [--wait-ms 30000]

Contract implemented (TENON, as built, 2026-09-04 20:43 EDT):
  GET  /health
  POST /v1/runs {prompt, cwd?, model?, tools?, permission_mode?, label?, peer?, partial?, session_id?, wait_ms?}
  GET  /v1/runs/{run_id}?wait_ms=            -> {ok, run}
  GET  /v1/runs/{run_id}/events?after=&limit=&wait_ms=  -> {events:[{seq, event}], next_cursor}
  POST /v1/runs/{run_id}/followup {prompt}
  POST /v1/sessions/{session_id}/followup {prompt}
  GET  /v1/sessions/{session_id}
  POST /v1/runs/{run_id}/cancel              (409 when already terminal)
  POST /v1/recover
  GET  /v1/events?after=&wait_ms=&run_id=
Statuses: queued | running | completed | error | cancelled | interrupted.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

DEFAULT_BASE = os.environ.get("CLAUDE_HEADLESS_BASE", "http://127.0.0.1:8879")
TERMINAL = frozenset({"completed", "error", "cancelled", "interrupted", "failed"})
MAX_WAIT_MS = 55_000


def unwrap_run(body: dict[str, Any]) -> dict[str, Any]:
    """The gateway answers ``{ok, run:{...}}``; accept a flat run too."""
    run = body.get("run")
    if isinstance(run, dict):
        return run
    return body


class HeadlessClient:
    def __init__(self, base: str = DEFAULT_BASE, timeout: float = 70.0, opener: Callable[..., Any] | None = None) -> None:
        self.base = base.rstrip("/")
        self.timeout = timeout
        self._opener = opener or urllib.request.urlopen

    # ---- transport -----------------------------------------------------
    def call(self, method: str, path: str, body: dict[str, Any] | None = None, **query: Any) -> dict[str, Any]:
        clean = {k: v for k, v in query.items() if v is not None}
        url = self.base + path + ("?" + urllib.parse.urlencode(clean) if clean else "")
        data = None
        headers = {"Accept": "application/json"}
        if body is not None or method == "POST":
            data = json.dumps(body or {}, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                status = getattr(response, "status", 200)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            status = exc.code
        except (OSError, urllib.error.URLError) as exc:
            return {"ok": False, "error": "unreachable", "message": str(exc), "url": url}
        try:
            value = json.loads(raw) if raw.strip() else {}
        except ValueError:
            value = {"ok": False, "error": "non_json_response", "body": raw[:2000]}
        if not isinstance(value, dict):
            value = {"ok": False, "error": "non_object_response", "body": value}
        value.setdefault("http_status", status)
        if status >= 400:
            value.setdefault("ok", False)
        return value

    # ---- operations ----------------------------------------------------
    def health(self) -> dict[str, Any]:
        return self.call("GET", "/health")

    def submit(self, prompt: str, **options: Any) -> dict[str, Any]:
        payload = {"prompt": prompt, **{k: v for k, v in options.items() if v is not None}}
        return self.call("POST", "/v1/runs", payload)

    def followup(self, run_id: str, prompt: str, **options: Any) -> dict[str, Any]:
        payload = {"prompt": prompt, **{k: v for k, v in options.items() if v is not None}}
        return self.call("POST", f"/v1/runs/{run_id}/followup", payload)

    def resume(self, session_id: str, prompt: str, **options: Any) -> dict[str, Any]:
        payload = {"prompt": prompt, **{k: v for k, v in options.items() if v is not None}}
        return self.call("POST", f"/v1/sessions/{session_id}/followup", payload)

    def status(self, run_id: str, wait_ms: int = 0) -> dict[str, Any]:
        return self.call("GET", f"/v1/runs/{run_id}", wait_ms=(min(MAX_WAIT_MS, wait_ms) or None))

    def run(self, run_id: str, wait_ms: int = 0) -> dict[str, Any]:
        return unwrap_run(self.status(run_id, wait_ms))

    def events(self, run_id: str, after: int = 0, limit: int | None = None, wait_ms: int = 0) -> dict[str, Any]:
        return self.call(
            "GET",
            f"/v1/runs/{run_id}/events",
            after=after,
            limit=limit,
            wait_ms=(min(MAX_WAIT_MS, wait_ms) or None),
        )

    def journal(self, after: int = 0, wait_ms: int = 0, run_id: str | None = None) -> dict[str, Any]:
        return self.call("GET", "/v1/events", after=after, wait_ms=(min(MAX_WAIT_MS, wait_ms) or None), run_id=run_id)

    def session(self, session_id: str) -> dict[str, Any]:
        return self.call("GET", f"/v1/sessions/{session_id}")

    def cancel(self, run_id: str) -> dict[str, Any]:
        return self.call("POST", f"/v1/runs/{run_id}/cancel", {})

    def recover(self) -> dict[str, Any]:
        return self.call("POST", "/v1/recover", {})

    # ---- conveniences --------------------------------------------------
    def wait(self, run_id: str, seconds: float, poll_ms: int = MAX_WAIT_MS) -> dict[str, Any]:
        """Long-poll until the run is terminal or ``seconds`` elapse. Returns the last body."""
        deadline = time.monotonic() + seconds
        body = self.status(run_id, 0)
        while True:
            run = unwrap_run(body)
            if run.get("status") in TERMINAL or not body.get("ok", True):
                return body
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return body
            body = self.status(run_id, int(min(poll_ms, remaining * 1000)) or 1)

    def follow(self, run_id: str, after: int = 0, out: Any = None, wait_ms: int = 30_000) -> dict[str, Any]:
        """Print each event line as it arrives; return the final run body."""
        out = out or sys.stdout
        cursor = after
        while True:
            page = self.events(run_id, after=cursor, wait_ms=wait_ms)
            for item in page.get("events", []):
                out.write(json.dumps(item, ensure_ascii=False) + "\n")
                out.flush()
                seq = item.get("seq", item.get("event_id"))
                if isinstance(seq, int):
                    cursor = max(cursor, seq)
            nxt = page.get("next_cursor")
            if isinstance(nxt, int):
                cursor = max(cursor, nxt)
            if not page.get("ok", True):
                return page
            run = unwrap_run(self.status(run_id, 0))
            if run.get("status") in TERMINAL and not page.get("events"):
                return {"ok": True, "run": run, "next_cursor": cursor}


# ---- CLI -------------------------------------------------------------------


def _prompt_arg(value: str) -> str:
    return sys.stdin.read() if value == "-" else value


RUN_OPTION_FIELDS = ("cwd", "model", "permission_mode", "label", "peer")


def _run_options(args: argparse.Namespace) -> dict[str, Any]:
    out: dict[str, Any] = {}
    fields = RUN_OPTION_FIELDS + (("session_id",) if args.command == "submit" else ())
    for field in fields:
        value = getattr(args, field, None)
        if value not in (None, ""):
            out[field] = value
    if getattr(args, "tools", None):
        out["tools"] = args.tools
    if getattr(args, "partial", False):
        out["partial"] = True
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default=DEFAULT_BASE, help="gateway base URL (env CLAUDE_HEADLESS_BASE)")
    sub = parser.add_subparsers(dest="command", required=True)

    def run_options(p: argparse.ArgumentParser) -> None:
        p.add_argument("--cwd")
        p.add_argument("--model")
        p.add_argument("--tools", nargs="*")
        p.add_argument("--permission-mode", dest="permission_mode")
        p.add_argument("--label")
        p.add_argument("--peer", help="optional attribution recorded on the run")
        p.add_argument("--partial", action="store_true", help="ask for partial message chunks in events")
        p.add_argument("--wait", type=float, default=0, help="seconds to wait for a terminal status")

    sub.add_parser("health")
    p = sub.add_parser("submit")
    p.add_argument("prompt")
    p.add_argument("--session-id", dest="session_id", help="resume this conversation instead of starting one")
    run_options(p)
    p = sub.add_parser("followup")
    p.add_argument("run_id")
    p.add_argument("prompt")
    run_options(p)
    p = sub.add_parser("resume")
    p.add_argument("session_id")
    p.add_argument("prompt")
    run_options(p)
    p = sub.add_parser("status")
    p.add_argument("run_id")
    p.add_argument("--wait", type=float, default=0)
    p = sub.add_parser("events")
    p.add_argument("run_id")
    p.add_argument("--after", type=int, default=0)
    p.add_argument("--follow", action="store_true")
    p = sub.add_parser("tail")
    p.add_argument("--after", type=int, default=0)
    p.add_argument("--wait-ms", type=int, default=0, dest="wait_ms")
    p.add_argument("--run-id", dest="run_id")
    p = sub.add_parser("session")
    p.add_argument("session_id")
    p = sub.add_parser("cancel")
    p.add_argument("run_id")
    sub.add_parser("recover")
    return parser


def main(argv: list[str] | None = None, out: Any = None) -> int:
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    client = HeadlessClient(args.base)
    if args.command == "health":
        result = client.health()
    elif args.command in ("submit", "followup", "resume"):
        prompt = _prompt_arg(args.prompt)
        options = _run_options(args)
        if args.command == "submit":
            result = client.submit(prompt, **options)
        elif args.command == "followup":
            result = client.followup(args.run_id, prompt, **options)
        else:
            result = client.resume(args.session_id, prompt, **options)
        if args.wait and result.get("run_id"):
            result = client.wait(result["run_id"], args.wait)
    elif args.command == "status":
        result = client.wait(args.run_id, args.wait) if args.wait else client.status(args.run_id)
    elif args.command == "events":
        result = client.follow(args.run_id, after=args.after, out=out) if args.follow else client.events(args.run_id, after=args.after)
    elif args.command == "tail":
        result = client.journal(after=args.after, wait_ms=args.wait_ms, run_id=args.run_id)
    elif args.command == "session":
        result = client.session(args.session_id)
    elif args.command == "cancel":
        result = client.cancel(args.run_id)
    else:
        result = client.recover()
    out.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
