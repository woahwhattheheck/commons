#!/usr/bin/env python3
"""Local export intake and comparison workbench; Python 3.10+, standard library only.

Run `python workbench.py --port 8767`, then open the printed loopback address.
Uploads live only within their request; there is no retained job or upload store.
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from errors import ParityError
from export_intake import build_manifest, parse_export
from parity import compile_bytes
from parity_schema import _exact_keys, canonical_bytes, loads_strict

MAX_REQUEST_BYTES = 12_000_000
ASSET_ROOT = Path(__file__).resolve().parent


def compare_exports(request: Any) -> dict[str, str]:
    manifest = build_manifest(request)
    report, markdown = compile_bytes(manifest)
    # Return exact strings. The browser must not parse/re-serialize the manifest:
    # signed 64-bit identifiers can exceed JavaScript's exact integer range.
    return {
        "manifest_json": manifest.decode("utf-8"),
        "report_json": canonical_bytes(report).decode("utf-8"),
        "report_markdown": markdown,
    }


def make_handler(assets: dict[str, tuple[str, bytes]]) -> type[BaseHTTPRequestHandler]:
    class WorkbenchHandler(BaseHTTPRequestHandler):
        server_version = "ParityWorkbench/1.0"
        sys_version = ""

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(20)

        def log_message(self, format: str, *args: Any) -> None:
            # No uploaded data, raw paths or request bodies in access logs.
            pass

        def respond(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            if self.command != "HEAD":
                self.wfile.write(body)

        def json_response(self, status: int, value: Any) -> None:
            self.respond(status, json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"))

        def do_GET(self) -> None:
            asset = assets.get(self.path)
            if asset is None:
                self.json_response(404, {"error": "Unknown route"})
                return
            mime, body = asset
            self.respond(200, body, mime)

        do_HEAD = do_GET

        def do_POST(self) -> None:
            if self.path not in ("/api/inspect", "/api/compare"):
                self.json_response(404, {"error": "Unknown route"})
                return
            if self.headers.get("Transfer-Encoding"):
                self.json_response(400, {"error": "Send a fixed-length JSON request"})
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                self.json_response(415, {"error": "Content-Type must be application/json"})
                return
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdecimal() or len(lengths[0]) > 9:
                self.json_response(411, {"error": "One valid Content-Length is required"})
                return
            length = int(lengths[0])
            if not 0 < length <= MAX_REQUEST_BYTES:
                self.json_response(413, {"error": f"Request must contain 1..{MAX_REQUEST_BYTES} bytes"})
                return
            try:
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ParityError("Request ended before its declared length")
                request = loads_strict(raw)
                if self.path == "/api/inspect":
                    _exact_keys(request, {"format", "text"}, "export preview")
                    columns, records = parse_export(request["text"], request["format"])
                    self.json_response(200, {"columns": columns, "record_count": len(records)})
                else:
                    self.json_response(200, compare_exports(request))
            except (ParityError, UnicodeError, ValueError) as exc:
                self.json_response(400, {"error": str(exc)})
            except (BrokenPipeError, ConnectionResetError):
                self.close_connection = True
            except TimeoutError:
                self.json_response(408, {"error": "Request timed out"})
            except Exception as exc:
                print(f"ERROR: request failed ({type(exc).__name__})", file=sys.stderr)
                self.json_response(500, {"error": "Comparison could not complete; check the server terminal"})

    return WorkbenchHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8767, help="loopback TCP port (default: 8767; 0 selects an available port)")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    try:
        assets = {
            "/": ("text/html; charset=utf-8", (ASSET_ROOT / "workbench.html").read_bytes()),
            "/workbench.js": ("text/javascript; charset=utf-8", (ASSET_ROOT / "workbench.js").read_bytes()),
        }
        with HTTPServer(("127.0.0.1", args.port), make_handler(assets)) as server:
            print(f"Parity workbench: http://127.0.0.1:{server.server_port}/", flush=True)
            print("Local operator tool. No upload storage or external services. Ctrl+C stops it.", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
        return 0
    except OSError as exc:
        print(f"ERROR: workbench could not start: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
