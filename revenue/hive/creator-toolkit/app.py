#!/usr/bin/env python3
"""Run Creator Desk with public member flows and capability-gated operator controls."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from operator_auth import OperatorAuth, OperatorSetupRequired
from toolkit import CONSENT_TEXT, DeskError, Store
from workspace_copy import CopyError, snapshot_bytes

MAX_BODY = 12 * 1024 * 1024
OPERATOR_ACTIONS = frozenset({"resource.create", "resource.update", "outbox.record", "inquiry.close"})


def _page_with_operator_boundary() -> bytes:
    page = Path(__file__).with_name("index.html").read_bytes()
    marker = b"<script>\n'use strict';"
    if marker not in page:
        raise RuntimeError("Creator Desk page script marker is missing")
    return page.replace(marker, b'<script src="/operator-auth.js"></script>\n' + marker, 1)


def make_server(store: Store, host="127.0.0.1", port=8768, operator_auth: OperatorAuth | None = None):
    auth = operator_auth or OperatorAuth(store.path)

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def log_message(self, *_args):
            # Do not put member references, addresses, capabilities or request bodies in logs.
            pass

        def respond(self, code, data, content_type="application/json; charset=utf-8", headers=None):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def require_operator(self):
            if not auth.verify_header(self.headers.get("Authorization")):
                raise DeskError("Valid operator capability required", 403)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            try:
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query)
                key = query.get("id", [None])[0]
                if parsed.path == "/":
                    return self.respond(200, _page_with_operator_boundary(), "text/html; charset=utf-8")
                if parsed.path == "/operator-auth.js":
                    return self.respond(200, Path(__file__).with_name("operator_auth.js").read_bytes(), "text/javascript; charset=utf-8")
                if parsed.path == "/api/operator":
                    self.require_operator()
                    return self.respond(200, {"operator": True})
                if parsed.path == "/workspace.sqlite3":
                    self.require_operator()
                    try:
                        data, receipt = snapshot_bytes(store.path)
                    except CopyError as exc:
                        raise DeskError(str(exc), 409) from None
                    except OSError:
                        raise DeskError("Workspace snapshot is unavailable", 503) from None
                    return self.respond(200, data, "application/octet-stream", {
                        "Content-Disposition": 'attachment; filename="creator-workspace.sqlite3"',
                        "X-Content-SHA256": receipt["sha256"],
                    })
                if parsed.path == "/api/catalog":
                    return self.respond(200, {"resources": store.catalog(), "consent_text": CONSENT_TEXT})
                if parsed.path == "/api/member":
                    return self.respond(200, store.member(key))
                if parsed.path == "/api/dashboard":
                    self.require_operator()
                    return self.respond(200, store.dashboard())
                if parsed.path == "/api/delivery":
                    result = store.delivery(key)
                    result.pop("data")
                    result["sequence"] = json.loads(result["sequence"])
                    return self.respond(200, result)
                if parsed.path == "/download":
                    result = store.delivery(key)
                    if result["kind"] != "file":
                        raise DeskError("This delivery is a link, not a file")
                    return self.respond(200, result["data"], "application/octet-stream", {
                        "Content-Disposition": "attachment; filename*=UTF-8''" + quote(result["filename"], safe=""),
                        "X-Content-SHA256": result["sha256"],
                    })
                if parsed.path == "/draft.eml":
                    self.require_operator()
                    return self.respond(200, store.email_draft(key), "message/rfc822", {
                        "Content-Disposition": 'attachment; filename="follow-up-draft.eml"',
                    })
                raise DeskError("Not found", 404)
            except DeskError as exc:
                self.respond(exc.status, {"error": str(exc)})
            except (BrokenPipeError, ConnectionResetError):
                return

        def do_POST(self):
            try:
                if urlsplit(self.path).path != "/api/change":
                    raise DeskError("Not found", 404)
                if self.headers.get_content_type() != "application/json":
                    raise DeskError("Use application/json", 415)
                length = self.headers.get("Content-Length", "")
                if not length.isdecimal():
                    raise DeskError("Content-Length is required", 411)
                length = int(length)
                if not 0 < length <= MAX_BODY:
                    raise DeskError("Request must be between 1 byte and 12 MiB", 413)
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise DeskError("Incomplete request")
                try:
                    payload = json.loads(raw)
                except (ValueError, UnicodeError, RecursionError):
                    raise DeskError("Invalid JSON") from None
                if not isinstance(payload, dict) or not isinstance(payload.get("action"), str):
                    raise DeskError("Expected an object with action, operation_id and payload")
                if payload["action"] in OPERATOR_ACTIONS:
                    self.require_operator()
                result = store.mutate(payload["action"], payload.get("operation_id"), payload.get("payload"))
                self.respond(200, result)
            except DeskError as exc:
                self.respond(exc.status, {"error": str(exc)})
            except (BrokenPipeError, ConnectionResetError):
                return
            except TimeoutError:
                self.respond(408, {"error": "Request timed out"})

    server = ThreadingHTTPServer((host, port), Handler)
    server.operator_auth = auth
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Persistent SQLite file outside the source tree")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8768)
    args = parser.parse_args()
    store = Store(args.db)
    try:
        auth = OperatorAuth(args.db)
    except OperatorSetupRequired as exc:
        parser.error(str(exc))
    server = make_server(store, args.host, args.port, auth)
    print(f"Creator Desk: http://{args.host}:{server.server_port}/", flush=True)
    print("Member flows are public to this listener; creator controls require the initialized operator capability. No email is sent.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
