#!/usr/bin/env python3
"""Tiny stdlib client for the headless Claude gateway.

Usable from any Commons harness on this machine, as a CLI or as a module:

    python integrations/claude_headless/client.py health
    python integrations/claude_headless/client.py submit "prompt" --wait 300
    python integrations/claude_headless/client.py status RUN_ID
    python integrations/claude_headless/client.py events RUN_ID --follow
    python integrations/claude_headless/client.py followup RUN_ID "next prompt" --wait 300
    python integrations/claude_headless/client.py cancel RUN_ID
    python integrations/claude_headless/client.py session SESSION_ID
    python integrations/claude_headless/client.py resume SESSION_ID "continue" --wait 300

Every command prints one JSON document. A prompt of ``-`` reads stdin.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_BASE = "http://127.0.0.1:8879"
TERMINAL = {"completed", "failed", "cancelled", "interrupted"}


class HeadlessClient:
    def __init__(self, base: str = DEFAULT_BASE, timeout: float = 60.0) -> None:
        self.base = base.rstrip("/")
        self.timeout = timeout

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None, **query: Any) -> dict[str, Any]:
        clean = {k: v for k, v in query.items() if v is not None}
        url = self.base + path + ("?" + urllib.parse.urlencode(clean) if clean else "")
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                return json.loads(exc.read().decode("utf-8"))
            except ValueError:
                return {"ok": False, "error": f"HTTP {exc.code}"}

    def health(self) -> dict[str, Any]:
        return self._call("GET", "/health")

    def submit(self, prompt: str, **options: Any) -> dict[str, Any]:
        return self._call("POST", "/v1/runs", {"prompt": prompt, **options})

    def followup(self, run_id: str, prompt: str, **options: Any) -> dict[str, Any]:
        return self._call("POST", f"/v1/runs/{run_id}/followup", {"prompt": prompt, **options})

    def resume(self, session_id: str, prompt: str, **options: Any) -> dict[str, Any]:
        return self._call("POST", f"/v1/sessions/{session_id}/runs", {"prompt": prompt, **options})

    def status(self, run_id: str, wait_ms: int = 0) -> dict[str, Any]:
        return self._call("GET", f"/v1/runs/{run_id}", wait_ms=wait_ms or None)

    def events(self, run_id: str, after: int = 0, wait_ms: int = 0, limit: int = 100) -> dict[str, Any]:
        return self._call("GET", f"/v1/runs/{run_id}/events", after=after, wait_ms=wait_ms or None, limit=limit)

    def all_events(self, after: int = 0, wait_ms: int = 0, limit: int = 100) -> dict[str, Any]:
        return self._call("GET", "/v1/events", after=after, wait_ms=wait_ms or None, limit=limit)

    def cancel(self, run_id: str) -> dict[str, Any]:
        return self._call("POST", f"/v1/runs/{run_id}/cancel", {})

    def runs(self, status: str | None = None, session_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        return self._call("GET", "/v1/runs", status=status, session_id=session_id, limit=limit)

    def session(self, session_id: str) -> dict[str, Any]:
        return self._call("GET", f"/v1/sessions/{session_id}")

    def wait(self, run_id: str, seconds: float) -> dict[str, Any]:
        deadline = time.monotonic() + seconds
        while True:
            remaining = max(0.0, deadline - time.monotonic())
            chunk = int(min(55_000, remaining * 1000))
            view = self.status(run_id, wait_ms=chunk)
            run = view.get("run") or {}
            if run.get("status") in TERMINAL or remaining <= 0:
                return view
            if chunk == 0:
                return view

    def follow(self, run_id: str, after: int = 0, out=None) -> dict[str, Any]:
        out = out or sys.stdout
        cursor = after
        while True:
            page = self.events(run_id, after=cursor, wait_ms=30_000)
            for event in page.get("events", []):
                out.write(json.dumps(event, ensure_ascii=False) + "\n")
                out.flush()
                cursor = max(cursor, int(event["event_id"]))
            if page.get("status") in TERMINAL and not page.get("events"):
                return page


def _prompt_arg(value: str) -> str:
    if value == "-":
        return sys.stdin.read()
    return value


def _options(args: argparse.Namespace) -> dict[str, Any]:
    fields = (
        "cwd",
        "model",
        "max_turns",
        "permission_mode",
        "effort",
        "append_system_prompt",
        "label",
    )
    out: dict[str, Any] = {k: getattr(args, k) for k in fields if getattr(args, k, None) not in (None, "")}
    if getattr(args, "sender", None):
        out["from"] = args.sender
    if getattr(args, "allowed_tools", None):
        out["allowed_tools"] = args.allowed_tools
    if getattr(args, "add_dir", None):
        out["add_dirs"] = args.add_dir
    if getattr(args, "strict_mcp_config", False):
        out["strict_mcp_config"] = True
    if getattr(args, "no_retain_prompt", False):
        out["retain_prompt"] = False
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default=DEFAULT_BASE)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_run_options(p: argparse.ArgumentParser) -> None:
        p.add_argument("--cwd")
        p.add_argument("--model")
        p.add_argument("--max-turns", type=int, dest="max_turns")
        p.add_argument("--permission-mode", dest="permission_mode")
        p.add_argument("--effort")
        p.add_argument("--append-system-prompt", dest="append_system_prompt")
        p.add_argument("--label")
        p.add_argument("--from", dest="sender", help="optional attribution")
        p.add_argument("--allowed-tools", nargs="*", dest="allowed_tools")
        p.add_argument("--add-dir", nargs="*", dest="add_dir")
        p.add_argument("--strict-mcp-config", action="store_true", dest="strict_mcp_config")
        p.add_argument("--no-retain-prompt", action="store_true", dest="no_retain_prompt")
        p.add_argument("--wait", type=float, default=0, help="seconds to wait for a terminal state")

    sub.add_parser("health")
    p = sub.add_parser("submit")
    p.add_argument("prompt")
    add_run_options(p)
    p = sub.add_parser("followup")
    p.add_argument("run_id")
    p.add_argument("prompt")
    add_run_options(p)
    p = sub.add_parser("resume")
    p.add_argument("session_id")
    p.add_argument("prompt")
    add_run_options(p)
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
    p = sub.add_parser("cancel")
    p.add_argument("run_id")
    p = sub.add_parser("runs")
    p.add_argument("--status")
    p.add_argument("--session", dest="session_id")
    p.add_argument("--limit", type=int, default=50)
    p = sub.add_parser("session")
    p.add_argument("session_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    client = HeadlessClient(args.base)
    if args.command == "health":
        result = client.health()
    elif args.command in ("submit", "followup", "resume"):
        prompt = _prompt_arg(args.prompt)
        options = _options(args)
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
        if args.follow:
            result = client.follow(args.run_id, after=args.after)
        else:
            result = client.events(args.run_id, after=args.after)
    elif args.command == "tail":
        result = client.all_events(after=args.after, wait_ms=args.wait_ms)
    elif args.command == "cancel":
        result = client.cancel(args.run_id)
    elif args.command == "runs":
        result = client.runs(status=args.status, session_id=args.session_id, limit=args.limit)
    else:
        result = client.session(args.session_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
