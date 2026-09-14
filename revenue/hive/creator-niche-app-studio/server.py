from __future__ import annotations

import argparse
import json
import mimetypes
import secrets
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from core import (
    MAX_JSON_BYTES,
    StudioError,
    StudioStore,
    ValidationError,
    canonical_bytes,
    loads_strict,
    verify_bundle,
)

STATIC_ROOT = Path(__file__).with_name("static")


class StudioServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], db_path: str):
        self.store = StudioStore(db_path)
        self.csrf_token = secrets.token_urlsafe(24)
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "CreatorNicheStudio/1"

    @property
    def app(self) -> StudioServer:
        return self.server  # type: ignore[return-value]

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _headers(self, status: int, content_type: str, length: int, *, cache: str = "no-store", extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        self.end_headers()

    def _json(self, status: int, value: object) -> None:
        body = canonical_bytes(value)
        self._headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def _error(self, exc: Exception) -> None:
        if isinstance(exc, StudioError):
            self._json(exc.status, exc.as_dict())
        else:
            self._json(500, {"error": "INTERNAL_ERROR", "message": "internal error"})

    def _same_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        try:
            parsed = urlparse(origin)
        except ValueError:
            return False
        host = self.headers.get("Host", "")
        return parsed.scheme in {"http", "https"} and parsed.netloc == host

    def _post_body(self) -> dict:
        if not self._same_origin():
            raise ValidationError("cross-origin request denied")
        if self.headers.get("X-CSRF-Token") != self.app.csrf_token:
            raise ValidationError("invalid CSRF token")
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValidationError("Content-Type must be application/json")
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or "")
        except ValueError as exc:
            raise ValidationError("invalid Content-Length") from exc
        if length < 0 or length > MAX_JSON_BYTES:
            raise ValidationError("request body size is invalid")
        body = self.rfile.read(length)
        if len(body) != length:
            raise ValidationError("request body was truncated")
        value = loads_strict(body)
        if not isinstance(value, dict):
            raise ValidationError("request body must be an object")
        return value

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/bootstrap":
                self._json(
                    200,
                    {
                        "schema": "creator-niche-api/v1",
                        "csrf_token": self.app.csrf_token,
                        "workspace": self.app.store.workspace(),
                        "plans": self.app.store.list_plans(),
                        "authority": {
                            "outbound_authorized": False,
                            "provider_mutation_authorized": False,
                            "payment_authorized": False,
                            "revenue_recognized": False,
                        },
                    },
                )
                return
            if path.startswith("/api/plans/") and path.endswith("/export"):
                plan_id = path[len("/api/plans/") : -len("/export")].strip("/")
                bundle = self.app.store.export_bundle(plan_id)
                self._headers(
                    200,
                    "application/zip",
                    len(bundle),
                    extra={"Content-Disposition": f'attachment; filename="{plan_id}-supply-plan.zip"'},
                )
                self.wfile.write(bundle)
                return
            if path.startswith("/api/plans/"):
                plan_id = path[len("/api/plans/") :].strip("/")
                self._json(200, self.app.store.get_plan(plan_id))
                return
            if path == "/":
                path = "/index.html"
            candidate = (STATIC_ROOT / path.lstrip("/")).resolve()
            if STATIC_ROOT.resolve() not in candidate.parents or not candidate.is_file():
                self._json(404, {"error": "NOT_FOUND", "message": "not found"})
                return
            body = candidate.read_bytes()
            content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
                content_type += "; charset=utf-8"
            self._headers(200, content_type, len(body), cache="no-cache")
            self.wfile.write(body)
        except Exception as exc:  # noqa: BLE001
            self._error(exc)

    def do_POST(self) -> None:
        try:
            path = urlparse(self.path).path
            body = self._post_body()
            if path == "/api/workspace":
                response = self.app.store.configure_workspace(
                    body.get("config"),
                    request_key=body.get("request_key"),
                    expected_revision=body.get("expected_revision"),
                )
                self._json(200, response)
                return
            if path == "/api/plans":
                response = self.app.store.save_plan(
                    body.get("plan"),
                    request_key=body.get("request_key"),
                    expected_revision=body.get("expected_revision"),
                )
                self._json(200, response)
                return
            if path.startswith("/api/plans/") and path.endswith("/archive"):
                plan_id = path[len("/api/plans/") : -len("/archive")].strip("/")
                response = self.app.store.archive_plan(
                    plan_id,
                    request_key=body.get("request_key"),
                    expected_revision=body.get("expected_revision"),
                )
                self._json(200, response)
                return
            if path == "/api/support":
                response = self.app.store.create_support_handoff(
                    body.get("support"), request_key=body.get("request_key")
                )
                self._json(200, response)
                return
            if path == "/api/verify":
                encoded = body.get("bundle_hex")
                if not isinstance(encoded, str) or len(encoded) > 10_000_000:
                    raise ValidationError("bundle_hex is invalid")
                try:
                    bundle = bytes.fromhex(encoded)
                except ValueError as exc:
                    raise ValidationError("bundle_hex is invalid") from exc
                self._json(200, verify_bundle(bundle))
                return
            self._json(404, {"error": "NOT_FOUND", "message": "not found"})
        except Exception as exc:  # noqa: BLE001
            self._error(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Creator-backed niche app studio loopback server")
    parser.add_argument("--db", default="creator-studio.sqlite3")
    parser.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1", "localhost"])
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    server = StudioServer((args.host, args.port), args.db)
    print(f"Creator Niche App Studio: http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
