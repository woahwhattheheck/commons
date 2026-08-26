"""One model-facing TITAN Hands dispatcher.

Computer-use keeps the landed DeltaUI broker (Windows + Android). Additional
routes share the same typed-failure envelope. Linux AT-SPI is catalogued and
returns ADAPTER_NOT_WRITTEN.
"""

from __future__ import annotations

from typing import Any, Mapping

from host.titan_hands_windows.protocol import PROTOCOL_VERSION, ProtocolError, failure

from .broker import TitanHandsBroker
from .linux import ATSPI_SKETCH, handle_linux
from .routes import COMMONS_SLACK_CHANNEL, HandsRoutes


COMPUTER_OPS = {
    "observe",
    "act",
    "capture",
    "done",
    "targets",
    "capabilities",
    "reset",
}

ROUTE_STATUS = (
    {
        "route": "computer",
        "status": "LIVE",
        "ops": sorted(COMPUTER_OPS),
        "targets": ["windows", "android"],
        "pixels": "explicit capture only",
        "contract": "DeltaUI",
    },
    {
        "route": "file",
        "status": "LIVE",
        "ops": ["list", "read", "write"],
        "write": "additive-only; existing paths return PATH_EXISTS",
    },
    {
        "route": "git",
        "status": "LIVE",
        "ops": ["status", "diff", "log", "add", "commit"],
        "write": "additive-only; tracked HEAD paths return NOT_ADDITIVE",
    },
    {
        "route": "slack",
        "status": "LIVE",
        "ops": ["read", "post"],
        "channel": COMMONS_SLACK_CHANNEL,
        "token": "COMMONS_SLACK_BOT_TOKEN or SLACK_BOT_TOKEN; TOKEN_MISS if absent",
    },
    {
        "route": "board",
        "status": "LIVE",
        "ops": ["read", "post"],
        "path": "new p/{id}.md only; existing ids return REMINT_REFUSED",
    },
    {
        "route": "shell",
        "status": "LIVE",
        "ops": ["run"],
        "cwd": "repository root",
    },
    {
        "route": "web",
        "status": "LIVE",
        "ops": ["fetch"],
        "pixels": "image bodies omitted",
    },
    {
        "route": "linux",
        "status": "ADAPTER_NOT_WRITTEN",
        "ops": ["observe", "act", "capture", "capabilities"],
        "adapter": "AT-SPI",
        "sketch": ATSPI_SKETCH,
    },
)


class TitanHandsRuntime:
    """Primary `hands` surface. DeltaUI computer-use is unchanged underneath."""

    def __init__(
        self,
        broker: TitanHandsBroker | None = None,
        routes: HandsRoutes | None = None,
    ) -> None:
        self.broker = broker or TitanHandsBroker()
        self.routes = routes or HandsRoutes()

    def close(self) -> None:
        self.broker.close()

    def catalog(self) -> dict[str, Any]:
        return {
            "ok": True,
            "protocol": PROTOCOL_VERSION,
            "kind": "route_catalog",
            "primary_tool": "hands",
            "compat_tools": [
                "hands_targets",
                "hands_observe",
                "hands_act",
                "hands_capture",
                "hands_capabilities",
            ],
            "default_route": "computer",
            "pixels": "explicit capture only",
            "routes": list(ROUTE_STATUS),
        }

    def handle(self, request: Mapping[str, Any]) -> dict[str, Any]:
        try:
            if not isinstance(request, Mapping):
                raise ProtocolError("request must be an object")
            payload = dict(request)
            route = str(payload.pop("route", "") or "").strip().lower()
            op = str(payload.get("op") or "").strip().lower()
            if not route:
                if op in {"catalog", "routes"}:
                    route = "catalog"
                elif op in COMPUTER_OPS or not op:
                    route = "computer"
                else:
                    raise ProtocolError("route is required when op is not a computer operation")
            if route in {"catalog", "routes"} or op in {"catalog", "routes"}:
                return self.catalog()
            if route in {"computer", "windows", "android"}:
                if route in {"windows", "android"}:
                    payload.setdefault("target", route)
                if op == "done" and not isinstance(payload.get("action"), Mapping):
                    payload["op"] = "act"
                    payload["action"] = {"type": "done"}
                result = self.broker.handle(payload)
                result.setdefault("route", "computer")
                return result
            if route == "linux":
                result = handle_linux(payload)
                result.setdefault("route", "linux")
                return result
            result = self.routes.handle(route, payload)
            result.setdefault("route", route)
            return result
        except ProtocolError as exc:
            message = str(exc)
            if message == "MNO_REFUSED":
                return failure("MNO_REFUSED", "commons.mno is not smashed or rewritten here")
            if message.startswith("PATH_OUTSIDE_REPO:"):
                return failure("PATH_OUTSIDE_REPO", f"path is outside the repository: {message.split(':', 1)[1]}")
            return failure("INVALID_REQUEST", message)
        except Exception as exc:
            return failure("BACKEND_ERROR", str(exc))
