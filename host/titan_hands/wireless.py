"""LAN bind + debug-APK helper for TITAN Hands.

Still one MCP tool: `titan_hands` with `target=wireless`. Local computer-use
targets stay open. Remote bind measures a paid Stripe checkout session when
STRIPE_SECRET_KEY is present. A missing key is PAY_UNCONFIGURED with a probe.
This helper does not rewrite lda/README.md and does not remint PR 3812.

Cite: p/wire-commons-android-apk-20260826-01.md
      p/blink-titan-money-20260826-01.md
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from host.titan_hands.lanes import PIXELS_NEVER, PIXELS_NOT_CAPTURED, _SemanticLane, _node
from host.titan_hands.pay import PayServer, measure_pay_transport, require_paid_session
from host.titan_hands_windows.protocol import PROTOCOL_VERSION, failure


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
APK_REL = "lda/app/build/outputs/apk/debug/app-debug.apk"
APK_RECIPE = "host/titan_hands/build_lda_apk.sh"


def apk_status(root: Path | None = None) -> dict[str, Any]:
    base = Path(root or ROOT)
    path = base / APK_REL
    return {
        "apk_rel": APK_REL,
        "apk_path": str(path),
        "apk_present": path.is_file(),
        "apk_bytes": path.stat().st_size if path.is_file() else 0,
        "recipe": APK_RECIPE,
        "recipe_present": (base / APK_RECIPE).is_file(),
        "gradle": "lda/app/build.gradle",
        "note": "debug APK is the existing lda/ Kotlin app; this helper does not rewrite lda/README.md",
    }


class _WirelessHandler(BaseHTTPRequestHandler):
    server_version = "titan-hands-wireless/0.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return None

    def _write(self, status: int, payload: dict[str, Any], *, raw: bytes | None = None, ctype: str = "application/json") -> None:
        body = raw if raw is not None else (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/status"}:
            self._write(200, self.server.status())  # type: ignore[attr-defined]
            return
        if path == "/apk":
            info = apk_status(self.server.root)  # type: ignore[attr-defined]
            if not info["apk_present"]:
                self._write(200, {"ok": False, "failure_reason": "APK_MISS", **info})
                return
            data = Path(info["apk_path"]).read_bytes()
            self._write(200, {}, raw=data, ctype="application/vnd.android.package-archive")
            return
        self._write(200, {"ok": False, "failure_reason": "UNKNOWN_OPERATION", "path": path})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/titan_hands":
            self._write(200, {"ok": False, "failure_reason": "UNKNOWN_OPERATION", "path": path})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            request = json.loads(raw.decode("utf-8"))
        except ValueError:
            self._write(200, {"ok": False, "failure_reason": "INVALID_REQUEST", "message": "body must be JSON"})
            return
        if not isinstance(request, dict):
            self._write(200, {"ok": False, "failure_reason": "INVALID_REQUEST", "message": "body must be an object"})
            return
        target = str(request.get("target") or "").strip().lower()
        if target in {"wireless", "pay"}:
            self._write(
                200,
                {
                    "ok": False,
                    "failure_reason": "INVALID_REQUEST",
                    "message": "wireless bind forwards computer-use and Commons lanes, not a nested bind",
                },
            )
            return
        if self.server.secret_present:  # type: ignore[attr-defined]
            paid = require_paid_session(
                request,
                pay=self.server.pay,  # type: ignore[attr-defined]
            )
            if not paid.get("ok"):
                self._write(200, paid)
                return
        result = self.server.router.handle(request)  # type: ignore[attr-defined]
        self._write(200, result)


class WirelessBindServer(ThreadingHTTPServer):
    def __init__(
        self,
        host: str,
        port: int,
        *,
        root: Path,
        pay: PayServer,
        router: Any,
        secret_present: bool,
    ) -> None:
        super().__init__((host, port), _WirelessHandler)
        self.root = root
        self.pay = pay
        self.router = router
        self.secret_present = secret_present
        self.allow_reuse_address = True

    def status(self) -> dict[str, Any]:
        host, port = self.server_address[:2]
        return {
            "ok": True,
            "kind": "wireless_bind",
            "host": host,
            "port": port,
            "url": f"http://{host}:{port}/",
            "apk_url": f"http://{host}:{port}/apk",
            "hands_url": f"http://{host}:{port}/titan_hands",
            **apk_status(self.root),
        }


class WirelessHandsServer(_SemanticLane):
    platform = "wireless"
    observation = "wireless-semantic-delta"
    pixels = PIXELS_NEVER
    actions = ("bind", "unbind", "serve_apk")

    def __init__(
        self,
        root: str | Path | None = None,
        environ: Mapping[str, str] | None = None,
        pay: PayServer | None = None,
        router_factory: Callable[[], Any] | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        super().__init__()
        self.root = Path(root or ROOT)
        self.environ = dict(environ) if environ is not None else None
        self.pay = pay or PayServer(root=self.root, environ=self.environ)
        self.router_factory = router_factory
        env = self._env()
        self.host = host or str(env.get("TITAN_HANDS_WIRELESS_HOST") or "127.0.0.1")
        self.port = int(port if port is not None else env.get("TITAN_HANDS_WIRELESS_PORT") or 0)
        self._httpd: WirelessBindServer | None = None
        self._thread: threading.Thread | None = None

    def close(self) -> None:
        self._stop()
        super().close()

    def _env(self) -> Mapping[str, str]:
        return self.environ if self.environ is not None else os.environ

    def _stop(self) -> None:
        if self._httpd is not None:
            try:
                self._httpd.shutdown()
            except Exception:
                pass
            try:
                self._httpd.server_close()
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._httpd = None
        self._thread = None

    def _bind_status(self) -> dict[str, Any]:
        if self._httpd is None:
            return {"bound": False, "host": self.host, "port": self.port}
        return {"bound": True, **self._httpd.status()}

    def _capabilities(self) -> dict[str, Any]:
        result = super()._capabilities()
        probe = measure_pay_transport(self._env(), self.root)
        result.update(apk_status(self.root))
        result.update(
            {
                "stripe_secret_key": probe["stripe_secret_key"],
                "checkout_sessions": probe["checkout_sessions"],
                "bind": self._bind_status(),
            }
        )
        return result

    def _snapshot(self, request: Mapping[str, Any]) -> dict[str, Any]:
        del request
        apk = apk_status(self.root)
        probe = measure_pay_transport(self._env(), self.root)
        bind = self._bind_status()
        nodes = [
            _node("wireless:host", "Window", "TITAN Hands wireless bind", actions=["bind", "unbind"]),
            _node(
                "wireless:apk",
                "File",
                APK_REL,
                parent="wireless:host",
                actions=["serve_apk"],
                present=apk["apk_present"],
            ),
            _node(
                "wireless:pay",
                "Receipt",
                "paid checkout session",
                parent="wireless:host",
                actions=["bind"],
                stripe_secret_key=probe["stripe_secret_key"],
            ),
        ]
        return {
            "ok": True,
            "nodes": nodes,
            "kind": "semantic_snapshot",
            "platform": "wireless",
            "pixels": PIXELS_NOT_CAPTURED,
            "apk": apk,
            "probe": probe,
            "bind": bind,
        }

    def _act(self, action: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
        action_type = str(action.get("type") or "").strip().lower()
        if action_type == "serve_apk":
            return {
                "ok": True,
                "protocol": PROTOCOL_VERSION,
                "kind": "action_outcome",
                "platform": "wireless",
                "action": "serve_apk",
                **apk_status(self.root),
                "bind": self._bind_status(),
            }
        if action_type == "unbind":
            self._stop()
            return {
                "ok": True,
                "protocol": PROTOCOL_VERSION,
                "kind": "action_outcome",
                "platform": "wireless",
                "action": "unbind",
                "bound": False,
            }
        if action_type == "bind":
            return self._bind(request, action)
        return failure("UNKNOWN_OPERATION", f"wireless lane has no handler for {action_type or '<empty>'}")

    def _bind(self, request: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, Any]:
        paid = require_paid_session(
            {
                "paid_session": action.get("paid_session") or request.get("paid_session"),
                "checkout_session_id": action.get("checkout_session_id") or request.get("checkout_session_id"),
                "session": action.get("session") or request.get("session"),
            },
            pay=self.pay,
        )
        if not paid.get("ok"):
            return paid
        if self._httpd is None:
            from host.titan_hands.one_tool import TitanHandsOne

            router = self.router_factory() if self.router_factory is not None else TitanHandsOne()
            httpd = WirelessBindServer(
                self.host,
                self.port,
                root=self.root,
                pay=self.pay,
                router=router,
                secret_present=bool(self.pay._secret()),
            )
            thread = threading.Thread(target=httpd.serve_forever, name="titan-hands-wireless", daemon=True)
            thread.start()
            self._httpd = httpd
            self._thread = thread
        status = self._httpd.status()
        return {
            "ok": True,
            "protocol": PROTOCOL_VERSION,
            "kind": "action_outcome",
            "platform": "wireless",
            "action": "bind",
            "paid": True,
            "checkout_session_id": paid.get("checkout_session_id"),
            **status,
        }
