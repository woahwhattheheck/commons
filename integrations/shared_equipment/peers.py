"""Expose Gemini + GrokBot lifecycle operations through shared equipment."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .services import _schema

DEFAULT_GROKBOT_CONTROL = "http://127.0.0.1:8881"


class GeminiEquipment:
    def __init__(self, gateway):
        self.gateway = gateway

    def tools(self):
        return [
            _schema(
                "gemini_submit",
                "Submit useful work to an existing Gemini peer; returns a request id. Request completion may require model/tool turns. Reuse the equipment envelope IDs on retry.",
                {"peer": "string", "message": "string"},
            ),
            _schema(
                "gemini_get_request",
                "Inspect a Gemini request without starting work. Wait up to 45 seconds if desired.",
                {"request_id": "string"},
                {"wait_ms": "integer"},
            ),
            _schema(
                "gemini_follow_up",
                "Continue the same named Gemini conversation with a new request. Preserves the existing upstream history.",
                {"request_id": "string", "message": "string"},
            ),
            _schema(
                "gemini_cancel",
                "Request cooperative cancellation. In-flight provider response may finish; no further tool effects then run. Does not kill the provider or other work.",
                {"request_id": "string"},
            ),
            _schema(
                "gemini_recover",
                "Inspect interrupted requests after a gateway restart. Never automatically replays work; inspect prior tool effects and explicitly follow up.",
                {},
            ),
            _schema(
                "gemini_events",
                "Read Gemini lifecycle and results after a cursor.",
                {},
                {"after": "integer", "limit": "integer", "peer": "string"},
            ),
        ]

    def call(self, name, args):
        g = self.gateway
        if name == "gemini_submit":
            item = g.submit(g.normalize_peer(args["peer"]), args["message"])
            return {"request_id": item.request_id, "status": "queued"}
        if name == "gemini_get_request":
            return {
                "event": g.events.request(
                    args["request_id"], min(45000, max(0, int(args.get("wait_ms", 0))))
                )
            }
        if name == "gemini_cancel":
            return g.cancel(args["request_id"])
        if name == "gemini_follow_up":
            prior = g.events.request(args["request_id"], 0)
            if prior is None:
                return {"error": "request_not_found"}
            item = g.submit(prior["peer"], args["message"])
            return {
                "request_id": item.request_id,
                "peer": prior["peer"],
                "previous_request_id": args["request_id"],
                "status": "queued",
            }
        if name == "gemini_recover":
            return {
                "interrupted": [
                    event
                    for event in g.events._latest.values()
                    if event.get("status") == "interrupted"
                ],
                "replayed": False,
            }
        if name == "gemini_events":
            events = g.events.after(
                int(args.get("after", 0)),
                args.get("peer"),
                min(200, max(1, int(args.get("limit", 20)))),
                0,
            )
            return {
                "events": events,
                "next_cursor": max(
                    [int(args.get("after", 0))] + [e["event_id"] for e in events]
                ),
            }
        return {"error": "unknown_equipment_tool"}


class GrokBotEquipment:
    """Drive existing GrokBot pools via integrations/grokbot_control (:8881).

    Distinct from Gemini lifecycle tools and from grok.com. Does not start the
    control gateway; callers point base_url at a running (or test) instance.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_GROKBOT_CONTROL,
        *,
        opener=None,
    ) -> None:
        self.base_url = str(base_url or DEFAULT_GROKBOT_CONTROL).rstrip("/")
        self.opener = opener or urllib.request.urlopen

    def tools(self):
        return [
            _schema(
                "grokbot_submit",
                "Submit work to an existing GrokBot pool via grokbot_control. Returns run_id + session_id. Not grok.com. Not Cursor cloud.",
                {"prompt": "string"},
                {"pool_id": "string", "seat": "string", "async": "boolean"},
            ),
            _schema(
                "grokbot_inspect",
                "Inspect a GrokBot run by run_id. Optional wait_ms blocks until terminal.",
                {"run_id": "string"},
                {"wait_ms": "integer"},
            ),
            _schema(
                "grokbot_follow_up",
                "Follow up on the same GrokBot session_id (new run_id). Pass any prior run_id from that session.",
                {"run_id": "string", "prompt": "string"},
                {"async": "boolean"},
            ),
            _schema(
                "grokbot_cancel",
                "Cancel one GrokBot run_id only. Session remains recoverable for follow-up.",
                {"run_id": "string"},
            ),
            _schema(
                "grokbot_session",
                "Recover a GrokBot session and its runs after controller replacement.",
                {"session_id": "string"},
            ),
            _schema(
                "grokbot_events",
                "Read GrokBot control events after a cursor (Gemini/C1 convention).",
                {},
                {"after": "integer", "limit": "integer", "pool_id": "string", "wait_ms": "integer"},
            ),
            _schema(
                "grokbot_pools",
                "List known GrokBot pool_ids (corpus ids only; second account kebab not invented).",
                {},
            ),
        ]

    def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "grokbot_submit":
            body = {
                "prompt": args["prompt"],
                "pool_id": args.get("pool_id") or "grokbot",
                "async": bool(args.get("async", True)),
            }
            if args.get("seat"):
                body["seat"] = args["seat"]
            return self._request("POST", "/v1/runs", payload=body)
        if name == "grokbot_inspect":
            wait_ms = min(45000, max(0, int(args.get("wait_ms", 0))))
            query = {"wait_ms": wait_ms} if wait_ms else None
            return self._request(
                "GET",
                "/v1/runs/%s" % args["run_id"],
                query=query,
                timeout=max(60.0, wait_ms / 1000.0 + 5),
            )
        if name == "grokbot_follow_up":
            body = {
                "prompt": args["prompt"],
                "async": bool(args.get("async", True)),
            }
            return self._request(
                "POST",
                "/v1/runs/%s/follow-up" % args["run_id"],
                payload=body,
            )
        if name == "grokbot_cancel":
            return self._request(
                "POST", "/v1/runs/%s/cancel" % args["run_id"], payload={}
            )
        if name == "grokbot_session":
            return self._request("GET", "/v1/sessions/%s" % args["session_id"])
        if name == "grokbot_events":
            return self._request(
                "GET",
                "/v1/events",
                query={
                    "after": int(args.get("after", 0)),
                    "limit": min(200, max(1, int(args.get("limit", 50)))),
                    "wait_ms": min(45000, max(0, int(args.get("wait_ms", 0)))),
                    "pool_id": args.get("pool_id"),
                },
            )
        if name == "grokbot_pools":
            return self._request("GET", "/v1/pools")
        return {"error": "unknown_equipment_tool"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(
                {k: v for k, v in query.items() if v is not None}
            )
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self.opener(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return {
                    "ok": False,
                    "error": "grokbot_control_http_error",
                    "status": exc.code,
                    "body": body[:500],
                }
        except Exception as exc:
            return {
                "ok": False,
                "error": "grokbot_control_unreachable",
                "message": "%s: %s" % (type(exc).__name__, exc),
                "base_url": self.base_url,
                "note": "Control gateway not running; do not relaunch residents on owner PC until cleared.",
            }