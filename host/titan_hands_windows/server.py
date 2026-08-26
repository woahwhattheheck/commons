#!/usr/bin/env python3
"""JSONL server for the native Windows TITAN Hands backend."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Mapping, Protocol

from .protocol import PROTOCOL_VERSION, DeltaTracker, ProtocolError, failure


class Backend(Protocol):
    def request(self, message: Mapping[str, Any]) -> dict[str, Any]: ...

    def close(self) -> None: ...


class PowerShellBridge:
    """Keeps AutomationElement references alive inside one PowerShell process."""

    def __init__(self, script: Path | None = None) -> None:
        self.script = script or Path(__file__).with_name("backend.ps1")
        executable = os.environ.get("TITAN_HANDS_POWERSHELL", "powershell.exe")
        self.process = subprocess.Popen(
            [
                executable,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.script),
                "-Stdio",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        self._lock = threading.Lock()

    def request(self, message: Mapping[str, Any]) -> dict[str, Any]:
        if self.process.poll() is not None:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"Windows backend exited: {stderr.strip()}")
        line = json.dumps(dict(message), ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            assert self.process.stdin is not None
            assert self.process.stdout is not None
            self.process.stdin.write(line + "\n")
            self.process.stdin.flush()
            response = self.process.stdout.readline()
        if not response:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"Windows backend returned no response: {stderr.strip()}")
        parsed = json.loads(response)
        if not isinstance(parsed, dict):
            raise RuntimeError("Windows backend response was not an object")
        return parsed

    def close(self) -> None:
        if self.process.poll() is not None:
            return
        try:
            self.request({"op": "shutdown"})
        except Exception:
            self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()


class TitanHandsServer:
    def __init__(self, backend: Backend | None = None) -> None:
        self.backend = backend or PowerShellBridge()
        self.tracker = DeltaTracker()

    def close(self) -> None:
        self.backend.close()

    def _observe(self, request: Mapping[str, Any]) -> dict[str, Any]:
        raw = self.backend.request(
            {
                "op": "snapshot",
                "max_nodes": int(request.get("max_nodes") or 600),
                "max_depth": int(request.get("max_depth") or 8),
                "include_offscreen": bool(request.get("include_offscreen", False)),
            }
        )
        if not raw.get("ok"):
            return raw
        return self.tracker.observe(raw)

    def handle(self, request: Mapping[str, Any]) -> dict[str, Any]:
        try:
            if not isinstance(request, Mapping):
                raise ProtocolError("request must be an object")
            op = str(request.get("op") or "").strip().lower()
            if op == "capabilities":
                backend = self.backend.request({"op": "capabilities"})
                if not backend.get("ok"):
                    return backend
                return {
                    "ok": True,
                    "protocol": PROTOCOL_VERSION,
                    "kind": "capabilities",
                    "platform": "windows",
                    "transport": "jsonl",
                    "backend": backend,
                }
            if op == "observe":
                return self._observe(request)
            if op == "reset":
                self.tracker.reset()
                return {"ok": True, "protocol": PROTOCOL_VERSION, "kind": "reset"}
            if op == "capture":
                result = self.backend.request(dict(request))
                result.setdefault("protocol", PROTOCOL_VERSION)
                return result
            if op == "act":
                action = request.get("action")
                if not isinstance(action, Mapping):
                    raise ProtocolError("act requires an action object")
                result = self.backend.request({"op": "action", "action": dict(action)})
                result.setdefault("protocol", PROTOCOL_VERSION)
                if result.get("ok") and request.get("observe_after", True):
                    result["observation"] = self._observe(request)
                return result
            return failure("UNKNOWN_OPERATION", f"unknown operation: {op or '<empty>'}")
        except (ProtocolError, TypeError, ValueError) as exc:
            return failure("INVALID_REQUEST", str(exc))
        except Exception as exc:
            return failure("BACKEND_ERROR", str(exc))


def serve_jsonl(server: TitanHandsServer) -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = server.handle(request)
        except json.JSONDecodeError as exc:
            response = failure("INVALID_JSON", str(exc))
        sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
        sys.stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="strict")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", help="process one JSON request and exit")
    args = parser.parse_args(argv)
    server = TitanHandsServer()
    try:
        if args.request is not None:
            response = server.handle(json.loads(args.request))
            print(json.dumps(response, ensure_ascii=False, indent=2))
            return 0 if response.get("ok") else 1
        return serve_jsonl(server)
    finally:
        server.close()


if __name__ == "__main__":
    raise SystemExit(main())
