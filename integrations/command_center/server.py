"""Owner control surface: no model inference or build dependencies."""
from __future__ import annotations
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from .core import CommandCenter, CoreError
from .telemetry import with_host

WEB = Path(__file__).with_name("web")
# integrations/command_center/server.py -> repository root. The observability
# snapshot reads static bakes from the checkout; COMMONS_REPO_ROOT overrides it
# when the app runs from somewhere other than the repository.
REPO_ROOT = os.environ.get(
    "COMMONS_REPO_ROOT", str(Path(__file__).resolve().parents[2]))
DEFAULT_STATE = Path(os.environ.get("COMMONS_COMMAND_CENTER_STATE", str(Path.home() / ".commons" / "command-center")))
ROUTES = {"/api/focus": "focus", "/api/sessions": "sessions", "/api/budgets": "budgets", "/api/runtimes": "runtimes", "/api/janny": "janny", "/api/feed": "feed", "/api/feed/moderate": "feed/moderate"}
MANIFEST = {
    "name": "Commons command center", "version": "2",
    "state": "GET /api/state", "refresh": "GET /api/state?refresh=1",
    "tools": "GET /api/tools", "call": "POST /api/tools/call", "event": "GET /api/event?event_id=...",
    "call_shape": {"operation_id": "caller-stable-id", "runtime_id": "shared-equipment", "name": "exact catalog tool name", "arguments": {}},
    "mutations": ROUTES,
    "observability": "GET /api/observability; the four board bakes read from main at the current commit (checkout fallback, labelled), liveness recomputed at read time; optional limit=N caps the board events returned, refresh=1 re-reads main now",
    "work": "GET /api/work; any read older than freshness.ttl_seconds since the last completed collection starts one bounded direct-provider read in the background and returns at once, with a freshness block; GET /api/work?refresh=1 starts one now",
    "ingest_work": "POST /api/work/ingest: operation_id, source with explicit scope/coverage/observed_at, selected items",
    "direct_work_refresh": "POST /api/work/refresh; status is included in GET /api/work",
    "owner_work": "POST /api/work/item: operation_id, source_id, item_id, priority, next_action, optional prepared job",
    "source_modes": "Direct collectors use existing shared GitHub and Slack service roads. Gmail, Airtable and native task observations are supplied by their actual connector-equipped peers through ingest. A source read does not establish complete fleet coverage or business activity.",
    "sharing": "The human and all current and future Commons peers use the same state and capabilities. Roles coordinate responsibility, never access.",
    "operations": "Reuse the same operation_id and exact payload after a transport interruption. Pending or uncertain is not completion. Reconcile at the provider; never remint an ID to force replay.",
    "credentials": "Direct retrieval remains available through the existing shared secure vault client and credential_retrieve_sealed tool. This panel does not decrypt, record, or display credential values.",
    "janny": "Assign an existing peer. Reversible derived-feed hide/restore with a reason; originals remain available. No source deletion or tool-access changes.",
    "model_driver": "A capable model can read state, inspect tool schemas, register existing sessions and runtimes, update focus, and invoke existing service tools through these APIs within the owner's instructions. This interface does not start an autonomous loop by itself.",
}
class Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, center):
        self.center = center
        super().__init__(address, Handler)

class Handler(BaseHTTPRequestHandler):
    server_version = "CommonsCommandCenter/1"
    def log_message(self, *_):
        pass
    def send_bytes(self, status, content, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass
    def send_json(self, status, value):
        self.send_bytes(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
    def valid_transport(self):
        # Browser transport integrity, not peer authorization.
        host = self.headers.get("Host", "")
        parsed = urlsplit("http://" + host)
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1", self.server.server_address[0]}:
            return False
        origin = self.headers.get("Origin")
        return not origin or origin == "http://" + host
    def do_GET(self):
        if not self.valid_transport():
            self.send_json(400, {"error": "invalid_origin"})
            return
        parsed = urlsplit(self.path)
        try:
            if parsed.path == "/api/state":
                self.send_json(200, with_host(self.server.center, self.server.center.state(refresh=parse_qs(parsed.query).get("refresh") == ["1"])))
            elif parsed.path == "/api/work":
                self.send_json(200, self.server.center.work_state(refresh=parse_qs(parsed.query).get("refresh") == ["1"]))
            elif parsed.path == "/api/event":
                event_id = (parse_qs(parsed.query).get("event_id") or [""])[0]
                self.send_json(200, self.server.center.event(event_id))
            elif parsed.path == "/api/tools":
                self.send_json(200, self.server.center.tools())
            elif parsed.path == "/api/manifest":
                self.send_json(200, MANIFEST)
            elif parsed.path == "/api/observability":
                # Read-only composition of pulse.json, feed/head.json,
                # seats.json and feed/github.json: what moved on the board,
                # which seats are awake enough to be given it, and what the
                # repository is doing. Read from main at the current commit so
                # a checkout that has not been pulled cannot freeze the panel;
                # the checkout is the labelled fallback. Adds no source of
                # truth and mutates nothing; a source it cannot read is
                # reported as degraded rather than rendered as an empty panel.
                query = parse_qs(parsed.query)
                limit = (query.get("limit") or ["20"])[0]
                try:
                    limit = max(1, min(200, int(limit)))
                except ValueError:
                    limit = 20
                self.send_json(200, self.server.center.observability(
                    limit, REPO_ROOT, refresh=query.get("refresh") == ["1"]))
            elif parsed.path == "/health":
                self.send_json(200, {"ok": True, "service": "commons-command-center"})
            else:
                names = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8"), "/work.js": ("work.js", "text/javascript; charset=utf-8"), "/work.css": ("work.css", "text/css; charset=utf-8")}
                entry = names.get(parsed.path)
                if entry is None:
                    self.send_json(404, {"error": "not_found"})
                else:
                    self.send_bytes(200, (WEB / entry[0]).read_bytes(), entry[1])
        except CoreError as exc:
            self.send_json(exc.status, {"error": str(exc)})
        except Exception as exc:
            self.send_json(502, {"error": type(exc).__name__, "message": "The source could not be read. Existing state is preserved."})
    def do_POST(self):
        if not self.valid_transport():
            self.send_json(400, {"error": "invalid_origin"})
            return
        path = urlsplit(self.path).path
        if path not in ROUTES and path not in {"/api/tools/call", "/api/work/ingest", "/api/work/item", "/api/work/refresh"}:
            self.send_json(404, {"error": "not_found"})
            return
        try:
            if self.headers.get_content_type() != "application/json":
                self.send_json(415, {"error": "application/json required"})
                return
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 1048576:
                self.send_json(413, {"error": "body_size"})
                return
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            if path == "/api/work/ingest":
                result = self.server.center.ingest_work(payload)
            elif path == "/api/work/item":
                result = {**self.server.center.update_work(payload), "status": "completed"}
            elif path == "/api/work/refresh":
                if payload:
                    raise CoreError(400, "Read refresh accepts an empty object.")
                result = self.server.center.refresh_work()
            else:
                result = self.server.center.call_tool(payload) if path == "/api/tools/call" else self.server.center.mutate(ROUTES[path], payload)
            self.send_json(200, result)
        except CoreError as exc:
            self.send_json(exc.status, {"error": str(exc)})
        except (ValueError, UnicodeError) as exc:
            self.send_json(400, {"error": type(exc).__name__, "message": str(exc)})
        except Exception as exc:
            self.send_json(502, {"error": type(exc).__name__, "status": "uncertain", "message": "Read operation state before retrying with the same ID."})
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8890)
    parser.add_argument("--gateway", default="http://127.0.0.1:8878")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args(argv)
    center = CommandCenter(args.state_dir, gateway_url=args.gateway)
    server = Server(("127.0.0.1", args.port), center)
    print(json.dumps({"ready": True, "url": "http://127.0.0.1:" + str(server.server_port)}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
