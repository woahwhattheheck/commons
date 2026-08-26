"""One model-facing TITAN Hands router.

The existing Windows/Android adapters keep their four ops (observe, act, capture,
capabilities). This router is one call in front of that contract, plus thin
lanes for files, git, Slack #commons, board posts, shell, and browser. Linux
AT-SPI is named next and returns a typed ADAPTER_PENDING failure.

Cite: p/emissary-titan-hands-features-20260826-01.md
      p/emissary-titan-hands-unified-runtime-20260826-01.md
Do not remint those receipts or the Windows/Android adapters.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from host.titan_hands_windows.protocol import PROTOCOL_VERSION, ProtocolError, failure

from .broker import HandsServer, TitanHandsBroker
from .lanes import (
    BoardServer,
    BrowserServer,
    FilesServer,
    GitServer,
    LinuxPendingServer,
    ShellServer,
    SlackServer,
)


PIXEL_PAYLOAD_KEYS = frozenset(
    {
        "pixel_ref",
        "screenshot",
        "image_png",
        "png_base64",
        "image_base64",
        "frame_png",
        "image_data",
    }
)
PIXEL_LABELS = frozenset({"", "not-captured", "on-demand-only", "never", "none"})


def contains_pixel_payload(value: Any) -> bool:
    """True when a result carries actual pixel bytes or a capture receipt."""

    if isinstance(value, list):
        return any(contains_pixel_payload(item) for item in value)
    if not isinstance(value, Mapping):
        return False
    if str(value.get("kind") or "") == "pixel_capture":
        return True
    for key, item in value.items():
        if key in PIXEL_PAYLOAD_KEYS and item not in (None, *PIXEL_LABELS):
            return True
        if contains_pixel_payload(item):
            return True
    return False


class BrokerTarget:
    """Forwards one computer-use target through the existing broker. Not a remint."""

    def __init__(self, broker: TitanHandsBroker, target: str) -> None:
        self.broker = broker
        self.target = target

    def handle(self, request: Mapping[str, Any]) -> dict[str, Any]:
        forwarded = dict(request)
        forwarded["target"] = self.target
        return self.broker.handle(forwarded)

    def close(self) -> None:
        return None


def default_factories(broker: TitanHandsBroker) -> dict[str, Callable[[], HandsServer]]:
    return {
        "windows": lambda: BrokerTarget(broker, "windows"),
        "android": lambda: BrokerTarget(broker, "android"),
        "linux": LinuxPendingServer,
        "files": FilesServer,
        "git": GitServer,
        "slack": SlackServer,
        "board": BoardServer,
        "shell": ShellServer,
        "browser": BrowserServer,
    }


class TitanHandsOne:
    """One handle({op, target, ...}) surface for computer-use and Commons lanes."""

    def __init__(
        self,
        factories: Mapping[str, Callable[[], HandsServer]] | None = None,
        default_target: str | None = None,
        computer_broker: TitanHandsBroker | None = None,
    ) -> None:
        self._broker = computer_broker
        if factories is None:
            self._broker = computer_broker or TitanHandsBroker()
            factories = default_factories(self._broker)
        self.factories = dict(factories)
        self.default_target = (default_target or "windows").strip().lower()
        self._servers: dict[str, HandsServer] = {}

    def close(self) -> None:
        for server in self._servers.values():
            server.close()
        self._servers.clear()
        if self._broker is not None:
            self._broker.close()

    def _server(self, target: str) -> HandsServer:
        target = target.strip().lower()
        if target not in self.factories:
            raise ProtocolError(f"unknown TITAN Hands target: {target}")
        if target not in self._servers:
            self._servers[target] = self.factories[target]()
        return self._servers[target]

    def _capability(self, target: str) -> dict[str, Any]:
        try:
            result = self._server(target).handle({"op": "capabilities"})
            return {"target": target, **result}
        except Exception as exc:
            return {
                "target": target,
                "ok": False,
                "protocol": PROTOCOL_VERSION,
                "kind": "failure",
                "failure_reason": "TARGET_UNAVAILABLE",
                "message": str(exc),
            }

    def handle(self, request: Mapping[str, Any]) -> dict[str, Any]:
        try:
            if not isinstance(request, Mapping):
                raise ProtocolError("request must be an object")
            op = str(request.get("op") or "").strip().lower()
            target_value = request.get("target")
            if op == "targets" or (op == "capabilities" and not target_value):
                result = {
                    "ok": True,
                    "protocol": PROTOCOL_VERSION,
                    "kind": "target_catalog",
                    "default_target": self.default_target,
                    "next_adapter": "linux-at-spi",
                    "model_facing_tools": 1,
                    "targets": [self._capability(target) for target in sorted(self.factories)],
                }
            else:
                target = str(target_value or self.default_target).strip().lower()
                forwarded = dict(request)
                forwarded.pop("target", None)
                forwarded["op"] = op
                result = self._server(target).handle(forwarded)
                result.setdefault("target", target)
            if op != "capture" and contains_pixel_payload(result):
                return failure(
                    "PIXEL_POLICY",
                    "pixels travel only when op=capture",
                    leaked_kind=str(result.get("kind") or ""),
                    target=result.get("target"),
                )
            return result
        except ProtocolError as exc:
            return failure("INVALID_REQUEST", str(exc))
        except Exception as exc:
            return failure("BACKEND_ERROR", str(exc))
