"""Expose existing Gemini lifecycle operations through shared equipment."""
from .services import _schema


class GeminiEquipment:
    def __init__(self, gateway):
        self.gateway = gateway

    def tools(self):
        return [
            _schema("gemini_submit", "Submit useful work to an existing Gemini peer; returns a request id. Request completion may require model/tool turns. Reuse the equipment envelope IDs on retry.", {"peer": "string", "message": "string"}),
            _schema("gemini_get_request", "Inspect a Gemini request without starting work. Wait up to 45 seconds if desired.", {"request_id": "string"}, {"wait_ms": "integer"}),
            _schema("gemini_follow_up", "Continue the same named Gemini conversation with a new request. Preserves the existing upstream history.", {"request_id": "string", "message": "string"}),
            _schema("gemini_cancel", "Request cooperative cancellation. In-flight provider response may finish; no further tool effects then run. Does not kill the provider or other work.", {"request_id": "string"}),
            _schema("gemini_recover", "Inspect interrupted requests after a gateway restart. Never automatically replays work; inspect prior tool effects and explicitly follow up.", {}),
            _schema("gemini_events", "Read Gemini lifecycle and results after a cursor.", {}, {"after": "integer", "limit": "integer", "peer": "string"}),
        ]

    def call(self, name, args):
        g = self.gateway
        if name == "gemini_submit":
            item = g.submit(g.normalize_peer(args["peer"]), args["message"])
            return {"request_id": item.request_id, "status": "queued"}
        if name == "gemini_get_request":
            return {"event": g.events.request(args["request_id"], min(45000, max(0, int(args.get("wait_ms", 0)))))}
        if name == "gemini_cancel":
            return g.cancel(args["request_id"])
        if name == "gemini_follow_up":
            prior = g.events.request(args["request_id"], 0)
            if prior is None:
                return {"error": "request_not_found"}
            item = g.submit(prior["peer"], args["message"])
            return {"request_id": item.request_id, "peer": prior["peer"], "previous_request_id": args["request_id"], "status": "queued"}
        if name == "gemini_recover":
            return {"interrupted": [event for event in g.events._latest.values() if event.get("status") == "interrupted"], "replayed": False}
        if name == "gemini_events":
            events = g.events.after(int(args.get("after", 0)), args.get("peer"), min(200, max(1, int(args.get("limit", 20)))), 0)
            return {"events": events, "next_cursor": max([int(args.get("after", 0))] + [e["event_id"] for e in events])}
        return {"error": "unknown_equipment_tool"}
