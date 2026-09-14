"""Zero-dependency local demo server for QuietOps."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any

from .core import QuietOpsError, process_offline, strict_json_loads

ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = ROOT / "web"
DEMO_ROOT = ROOT / "demo"
MAX_BODY = 256 * 1024


class QuietOpsHandler(BaseHTTPRequestHandler):
    server_version = "QuietOpsDemo/1.0"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: Any) -> None:
        self._send(status, json.dumps(payload, sort_keys=True).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            self._send(200, (WEB_ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
            return
        if self.path == "/demo/autonomous":
            self._send(200, (DEMO_ROOT / "inbox.json").read_bytes(), "application/json; charset=utf-8")
            return
        if self.path == "/demo/human":
            self._send(200, (DEMO_ROOT / "human_required.json").read_bytes(), "application/json; charset=utf-8")
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/process":
            self._json(404, {"error": "not_found"})
            return
        raw_len = self.headers.get("Content-Length")
        try:
            length = int(raw_len or "0")
        except ValueError:
            self._json(400, {"error": "bad_content_length"})
            return
        if length <= 0 or length > MAX_BODY:
            self._json(413 if length > MAX_BODY else 400, {"error": "body_size"})
            return
        try:
            text = self.rfile.read(length).decode("utf-8", errors="strict")
            item = strict_json_loads(text)
            result = process_offline(item)
        except (UnicodeError, QuietOpsError, json.JSONDecodeError, TypeError, ValueError, RecursionError) as exc:
            self._json(400, {"error": "invalid_work_item", "detail": str(exc)})
            return
        self._json(200, result)

    def log_message(self, format: str, *args: Any) -> None:
        # Demo server is quiet by default so screen recordings stay clean.
        return


def make_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), QuietOpsHandler)


def main() -> int:
    server = make_server()
    host, port = server.server_address[:2]
    print(f"QuietOps demo: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
