"""Local browser adapter for the existing laundry operator commands. No public hosting."""
from __future__ import annotations

import argparse
from contextlib import closing
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
from urllib.parse import parse_qs, urlsplit

import operate
from laundry_desk import LaundryDesk, LaundryDeskError, ValidationError

ACTIONS = ("customer", "site", "agreement", "plan", "manifest", "pickup",
           "process", "deliver", "resolve", "invoice-draft")
ASSETS = {"/": ("operator_console.html", "text/html; charset=utf-8"),
          "/operator_console.js": ("operator_console.js", "text/javascript; charset=utf-8")}
FORMATS = {"json": ("application/json", "json"), "csv": ("text/csv", "csv"),
           "markdown": ("text/markdown", "md")}


def overview(database: Path) -> dict:
    desk = LaundryDesk.open_read_only(database)
    with closing(desk._connect()) as conn:
        counts = {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                  for name in ("customers", "sites", "routes")}
        counts["open_exceptions"] = conn.execute(
            "SELECT COUNT(*) FROM exceptions WHERE status='OPEN'").fetchone()[0]
        routes = [dict(row) for row in conn.execute(
            "SELECT route_id,service_date,route_code,state FROM routes "
            "ORDER BY service_date DESC,route_id LIMIT 100")]
        customers = [dict(row) for row in conn.execute(
            "SELECT customer_id,name FROM customers ORDER BY customer_id LIMIT 100")]
        sites = [dict(row) for row in conn.execute(
            "SELECT site_id,customer_id,name FROM sites ORDER BY site_id LIMIT 100")]
    return {"counts": counts, "routes": routes, "customers": customers, "sites": sites,
            "list_limit": 100, "authority": operate.authority()}


class ConsoleServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, database: Path, port: int):
        self.database = database
        self.token = secrets.token_urlsafe(32)
        self.assets = {url: (Path(__file__).with_name(name).read_bytes(), mime)
                       for url, (name, mime) in ASSETS.items()}
        super().__init__(("127.0.0.1", port), ConsoleHandler)
        self.expected_host = f"127.0.0.1:{self.server_port}"
        self.origin = "http://" + self.expected_host


class ConsoleHandler(BaseHTTPRequestHandler):
    server: ConsoleServer
    server_version = "LaundryConsole/1"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_args):
        # No request paths, session credentials or customer data in access logs.
        pass

    def send_bytes(self, status: int, data: bytes, mime: str, filename: str | None = None):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; "
                         "style-src 'self' 'unsafe-inline'; connect-src 'self'; "
                         "img-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass  # A lost reply does not undo a committed operation. Retry its exact key.

    def send_json(self, status: int, value: dict):
        self.send_bytes(status, json.dumps(value, ensure_ascii=True).encode(),
                        "application/json; charset=utf-8")

    def permitted(self, *, api: bool, write: bool = False) -> bool:
        if self.headers.get_all("Host") != [self.server.expected_host]:
            self.send_json(403, {"message": "Use the exact loopback address printed at startup."})
            return False
        if api:
            supplied = self.headers.get_all("Authorization") or []
            expected = "Bearer " + self.server.token
            if len(supplied) != 1 or not hmac.compare_digest(
                    supplied[0].encode("utf-8"), expected.encode("ascii")):
                self.send_json(401, {"message": "Unlock with the current console session key."})
                return False
        if write and self.headers.get_all("Origin") != [self.server.origin]:
            self.send_json(403, {"message": "A same-origin browser request is required."})
            return False
        return True

    def do_GET(self):
        if not self.permitted(api=False):
            return
        target = urlsplit(self.path)
        if target.path in self.server.assets and not target.query:
            data, mime = self.server.assets[target.path]
            self.send_bytes(200, data, mime)
            return
        if not self.permitted(api=True):
            return
        try:
            query = parse_qs(target.query, strict_parsing=True, max_num_fields=4)
            if any(len(values) != 1 for values in query.values()):
                raise ValidationError("duplicate query parameter")
            if target.path == "/api/config" and not query:
                fields = {}
                for action in ACTIONS:
                    _, required, optional = operate.COMMANDS[action]
                    fields[action] = {"required": {"operation_key": "str", **{
                        key: kind.__name__ for key, kind in required.items()}},
                        "optional": {key: kind.__name__ for key, kind in optional.items()}}
                self.send_json(200, {"commands": fields})
            elif target.path == "/api/overview" and not query:
                self.send_json(200, overview(self.server.database))
            elif target.path == "/api/route" and set(query) == {"id"}:
                desk = LaundryDesk.open_read_only(self.server.database)
                self.send_json(200, desk.route_snapshot(query["id"][0]))
            elif target.path == "/api/export" and set(query) == {"kind", "id", "format"}:
                kind, identifier, fmt = (query[key][0] for key in ("kind", "id", "format"))
                if kind not in ("route", "customer") or fmt not in FORMATS:
                    raise ValidationError("unsupported export")
                desk = LaundryDesk.open_read_only(self.server.database)
                exports = (desk.render_route_exports(identifier) if kind == "route"
                           else desk.render_customer_exports(identifier))
                mime, extension = FORMATS[fmt]
                self.send_bytes(200, exports[fmt].encode("utf-8"), mime + "; charset=utf-8",
                                f"laundry-{kind}.{extension}")
            else:
                self.send_json(404, {"message": "Unknown console route."})
        except (LaundryDeskError, ValueError) as exc:
            self.send_json(400, {"message": str(exc)})
        except (OSError, sqlite3.Error):
            self.send_json(503, {"message": "The local database could not be read. Check the server terminal."})
            print("Console database read failed.", file=sys.stderr)

    def do_POST(self):
        if not self.permitted(api=True, write=True):
            return
        target = urlsplit(self.path)
        action = target.path.removeprefix("/api/operations/")
        if not target.path.startswith("/api/operations/") or target.query or action not in ACTIONS:
            self.send_json(404, {"message": "Unsupported operation."})
            return
        lengths = self.headers.get_all("Content-Length") or []
        if (len(lengths) != 1 or not 1 <= len(lengths[0]) <= 7 or not lengths[0].isascii() or not lengths[0].isdigit()
                or self.headers.get("Transfer-Encoding") is not None):
            self.send_json(411, {"message": "One fixed Content-Length is required."})
            return
        length = int(lengths[0])
        if not 0 < length <= operate.MAX_INPUT_BYTES:
            self.send_json(413, {"message": "One operation must be at most 1 MiB."})
            return
        if self.headers.get_content_type() != "application/json":
            self.send_json(415, {"message": "Send application/json."})
            return
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValidationError("incomplete request body")
            # Reuse the canonical CLI parser, type rules and engine dispatch unchanged.
            # A temporary input is private to this process and is never a customer file.
            with tempfile.TemporaryDirectory(prefix="laundry-console-") as temporary:
                payload = Path(temporary) / "operation.json"
                payload.write_bytes(raw)
                result = operate.execute(str(self.server.database), action, str(payload))
            self.send_json(200, result)
        except LaundryDeskError as exc:
            self.send_json(409 if type(exc).__name__ in ("StateConflict", "IdempotencyConflict", "InvoiceBlocked")
                           else 400, {"status": "REJECTED", "error_type": type(exc).__name__,
                                      "message": str(exc)})
        except (OSError, sqlite3.Error, OverflowError) as exc:
            # An I/O failure after commit can leave outcome uncertain; never suggest a new key.
            self.send_json(503, {"status": "UNKNOWN", "message":
                "Local I/O failed. Keep the exact operation key and payload; inspect state before retrying."})
            print(f"Console operation I/O failure: {type(exc).__name__}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local laundry operator console; invoices remain DRAFTS")
    parser.add_argument("database", type=Path, help="one operator-owned SQLite database")
    parser.add_argument("--init", action="store_true", help="explicitly create a NEW database; never overwrite")
    parser.add_argument("--port", type=int, default=0, help="loopback port; 0 chooses an available port")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("port must be 0..65535")
    try:
        if args.init:
            operate.execute(str(args.database), "init", None)
        operate._regular_database(args.database)
        LaundryDesk.open_read_only(args.database)
        with ConsoleServer(args.database.absolute(), args.port) as server:
            print(f"Open {server.origin}/#key={server.token}", flush=True)
            print("Local session key: keep this address private. Ctrl+C stops the console.", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    except (LaundryDeskError, OSError, sqlite3.Error) as exc:
        print(f"Console startup failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
