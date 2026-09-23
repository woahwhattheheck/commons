#!/usr/bin/env python3
"""Loopback-only, in-memory browser intake for the existing parity engine."""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from csv_intake import bundle_bytes, compile_csv, inspect_csv
from errors import ParityError
from parity_schema import MAX_INPUT_BYTES, canonical_bytes, loads_strict

MAX_REQUEST_BYTES = 12_000_000


class IntakeServer(HTTPServer):
    def __init__(self, port: int):
        self.token = secrets.token_urlsafe(32)
        template = Path(__file__).with_name("web_intake.html").read_text(encoding="utf-8")
        self.page = template.replace("__INTAKE_TOKEN__", self.token).encode("utf-8")
        super().__init__(("127.0.0.1", port), Handler)
        self.authority = f"127.0.0.1:{self.server_port}"
        self.origin = f"http://{self.authority}"

    def get_request(self):
        sock, address = super().get_request()
        sock.settimeout(20)
        return sock, address


class Handler(BaseHTTPRequestHandler):
    server: IntakeServer

    def log_message(self, *_args):
        pass  # Never log imported data, filenames, or request bodies.

    def send(self, status: int, payload: bytes, kind: str = "application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", f"default-src 'none'; script-src 'nonce-{self.server.token}'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def error(self, status: int, message: str):
        self.send(status, json.dumps({"error": message}).encode("utf-8"))

    def valid_host(self) -> bool:
        return self.headers.get_all("Host", []) == [self.server.authority]

    def do_GET(self):
        if not self.valid_host():
            return self.error(403, "Open the exact loopback URL printed by the server")
        if self.path != "/":
            return self.error(404, "Not found")
        self.send(200, self.server.page, "text/html; charset=utf-8")

    def do_POST(self):
        if not self.valid_host() or self.headers.get("Origin") != self.server.origin or not secrets.compare_digest(self.headers.get("X-Intake-Token", ""), self.server.token):
            return self.error(403, "Request must originate from this local intake page")
        if self.path not in {"/inspect", "/compile"}:
            return self.error(404, "Not found")
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            return self.error(415, "Send JSON from the local intake page")
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) != 1 or not lengths[0].isdigit():
            return self.error(411, "A single Content-Length is required")
        length = int(lengths[0])
        if not 0 < length <= MAX_REQUEST_BYTES:
            return self.error(413, "Request exceeds local intake size limit")
        try:
            body = self.rfile.read(length)
            if len(body) != length:
                return self.error(400, "Incomplete upload; retry explicitly")
            data = loads_strict(body)
            if type(data) is not dict:
                raise ParityError("Request must be an object")
            if self.path == "/inspect":
                delimiter = data.get("delimiter")
                if type(delimiter) is not str:
                    raise ParityError("Choose a delimiter")
                result = inspect_csv(self.decode_file(data.get("csv")), delimiter)
            else:
                result = compile_csv(self.decode_file(data.get("source")), self.decode_file(data.get("target")), data.get("plan"))
                result["bundle_base64"] = base64.b64encode(bundle_bytes(result)).decode("ascii")
                # Preserve canonical bytes for the existing exact-byte verifier.
                result["report_text"] = canonical_bytes(result["report"]).decode("utf-8")
                result["plan_text"] = canonical_bytes(result["plan"]).decode("utf-8")
                del result["manifest"]  # Private raw values are present only in the clearly labeled ZIP.
            self.send(200, canonical_bytes(result))
        except (ParityError, binascii.Error) as exc:
            self.error(400, str(exc))
        except (TimeoutError, ConnectionError, BrokenPipeError):
            self.close_connection = True
        except Exception:
            self.error(500, "Intake failed; no files were stored or provider actions performed")

    @staticmethod
    def decode_file(value) -> bytes:
        if type(value) is not str or len(value) > 4 * ((MAX_INPUT_BYTES + 2) // 3):
            raise ParityError("CSV missing or too large")
        try:
            raw = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ParityError("CSV upload is not valid base64") from exc
        if len(raw) > MAX_INPUT_BYTES:
            raise ParityError("CSV exceeds 4,000,000 bytes")
        return raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765, help="loopback port, or 0 to choose a free port")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be in 0..65535")
    try:
        with IntakeServer(args.port) as server:
            print(f"Open {server.origin}/ — local memory only; Ctrl-C to stop", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except OSError as exc:
        parser.exit(2, f"Cannot start local intake: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
