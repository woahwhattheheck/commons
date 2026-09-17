#!/usr/bin/env python3
"""Deterministic offline acceptance engine for the OneWriter demo contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _norm_text(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def _norm_domain(value: str) -> str:
    value = _norm_text(value)
    value = re.sub(r"^https?://", "", value)
    value = value.split("/", 1)[0].strip(".")
    if value.startswith("www."):
        value = value[4:]
    return value


def normalize_lane(lane: dict[str, str]) -> dict[str, str]:
    required = ("organization", "domain", "route", "purpose", "opportunity")
    missing = [k for k in required if not lane.get(k)]
    if missing:
        raise ValueError(f"lane missing fields: {', '.join(missing)}")
    return {
        "organization": _norm_text(lane["organization"]),
        "domain": _norm_domain(lane["domain"]),
        "route": _norm_text(lane["route"]),
        "purpose": _norm_text(lane["purpose"]),
        "opportunity": _norm_text(lane["opportunity"]),
    }


def collision_key(lane: dict[str, str]) -> str:
    return hashlib.sha256(_canon(normalize_lane(lane))).hexdigest()


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("event timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


@dataclass
class LaneState:
    normalized_lane: dict[str, str]
    state: str = "CLEAR"
    lease_holder: str | None = None
    lease_expires_at: datetime | None = None
    stale_expired: bool = False


@dataclass
class Replay:
    lanes: dict[str, LaneState] = field(default_factory=dict)
    receipts: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, int] = field(default_factory=lambda: {
        "collisions_prevented": 0,
        "duplicate_touches_prevented": 0,
        "stale_leases_recovered": 0,
        "route_failures": 0,
        "human_reopens": 0,
    })

    def _receipt(self, event: dict[str, Any], key: str, prior: str | None,
                 next_state: str | None, accepted: bool, reason: str) -> dict[str, Any]:
        prior_digest = self.receipts[-1]["digest"] if self.receipts else "GENESIS"
        payload = {
            "seq": len(self.receipts) + 1,
            "event_id": event["event_id"],
            "at": event["at"],
            "actor": event["actor"],
            "collision_key": key,
            "action": event["action"],
            "accepted": accepted,
            "prior_state": prior,
            "next_state": next_state,
            "reason": reason,
            "prior_digest": prior_digest,
        }
        payload["digest"] = hashlib.sha256(_canon(payload)).hexdigest()
        self.receipts.append(payload)
        return payload

    def apply(self, event: dict[str, Any]) -> dict[str, Any]:
        key = collision_key(event["lane"])
        action = event["action"]
        now = parse_time(event["at"])
        lane = self.lanes.get(key)
        prior = lane.state if lane else None

        if action == "PROPOSE":
            if lane is not None:
                return self._receipt(event, key, prior, prior, False, "lane_exists")
            lane = LaneState(normalize_lane(event["lane"]))
            self.lanes[key] = lane
            return self._receipt(event, key, prior, "CLEAR", True, "lane_created")

        if lane is None:
            return self._receipt(event, key, prior, prior, False, "unknown_lane")

        if action == "ACQUIRE_LEASE":
            if lane.state == "LEASED":
                self.metrics["collisions_prevented"] += 1
                return self._receipt(event, key, prior, prior, False, "active_lease")
            if lane.state == "SENT_DNR":
                self.metrics["duplicate_touches_prevented"] += 1
                return self._receipt(event, key, prior, prior, False, "sent_dnr")
            if lane.state == "DEAD_ROUTE":
                return self._receipt(event, key, prior, prior, False, "dead_route")
            if lane.state == "HOLD":
                return self._receipt(event, key, prior, prior, False, "hold")
            if lane.state not in {"CLEAR", "HUMAN_EVENT_REOPEN"}:
                return self._receipt(event, key, prior, prior, False, "invalid_state")
            seconds = int(event.get("lease_seconds", 0))
            if seconds < 1 or seconds > 3600:
                return self._receipt(event, key, prior, prior, False, "invalid_lease_seconds")
            lane.state = "LEASED"
            lane.lease_holder = event["actor"]
            lane.lease_expires_at = now + timedelta(seconds=seconds)
            if lane.stale_expired:
                self.metrics["stale_leases_recovered"] += 1
                lane.stale_expired = False
            return self._receipt(event, key, prior, lane.state, True, "lease_acquired")

        if action == "EXPIRE_LEASE":
            if lane.state != "LEASED" or lane.lease_expires_at is None:
                return self._receipt(event, key, prior, prior, False, "no_active_lease")
            if now < lane.lease_expires_at:
                return self._receipt(event, key, prior, prior, False, "lease_not_expired")
            lane.state = "CLEAR"
            lane.lease_holder = None
            lane.lease_expires_at = None
            lane.stale_expired = True
            return self._receipt(event, key, prior, lane.state, True, "lease_expired")

        if action == "RELEASE_LEASE":
            if lane.state != "LEASED":
                return self._receipt(event, key, prior, prior, False, "no_active_lease")
            if lane.lease_holder != event["actor"]:
                return self._receipt(event, key, prior, prior, False, "not_lease_holder")
            lane.state = "CLEAR"
            lane.lease_holder = None
            lane.lease_expires_at = None
            return self._receipt(event, key, prior, lane.state, True, "lease_released")

        if action in {"PROVIDER_SENT", "PROVIDER_BOUNCE"}:
            if lane.state != "LEASED":
                return self._receipt(event, key, prior, prior, False, "no_active_lease")
            if lane.lease_holder != event["actor"]:
                return self._receipt(event, key, prior, prior, False, "not_lease_holder")
            if not event.get("provider_receipt"):
                return self._receipt(event, key, prior, prior, False, "missing_provider_receipt")
            lane.lease_holder = None
            lane.lease_expires_at = None
            if action == "PROVIDER_SENT":
                lane.state = "SENT_DNR"
                reason = "provider_sent"
            else:
                lane.state = "DEAD_ROUTE"
                self.metrics["route_failures"] += 1
                reason = "provider_bounce"
            return self._receipt(event, key, prior, lane.state, True, reason)

        if action == "HUMAN_EVENT":
            if lane.state != "SENT_DNR":
                return self._receipt(event, key, prior, prior, False, "human_event_not_reopenable")
            if not event.get("human_event_ref"):
                return self._receipt(event, key, prior, prior, False, "missing_human_event_ref")
            lane.state = "HUMAN_EVENT_REOPEN"
            self.metrics["human_reopens"] += 1
            return self._receipt(event, key, prior, lane.state, True, "human_event_reopen")

        if action == "PLACE_HOLD":
            lane.state = "HOLD"
            lane.lease_holder = None
            lane.lease_expires_at = None
            return self._receipt(event, key, prior, lane.state, True, "hold_placed")

        return self._receipt(event, key, prior, prior, False, "unknown_action")


def verify_receipts(receipts: list[dict[str, Any]]) -> None:
    prior = "GENESIS"
    for index, receipt in enumerate(receipts, start=1):
        if receipt.get("seq") != index:
            raise ValueError(f"receipt sequence mismatch at {index}")
        if receipt.get("prior_digest") != prior:
            raise ValueError(f"receipt chain mismatch at {index}")
        candidate = deepcopy(receipt)
        digest = candidate.pop("digest", None)
        expected = hashlib.sha256(_canon(candidate)).hexdigest()
        if digest != expected:
            raise ValueError(f"receipt digest mismatch at {index}")
        prior = digest


def replay_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    replay = Replay()
    seen_ids: set[str] = set()
    for event in fixture["events"]:
        if event["event_id"] in seen_ids:
            raise ValueError(f"duplicate event_id {event['event_id']}")
        seen_ids.add(event["event_id"])
        receipt = replay.apply(event)
        expected = event.get("expect", {})
        for field, value in expected.items():
            actual = receipt["next_state"] if field == "state" else receipt.get(field)
            if actual != value:
                raise ValueError(f"{event['event_id']} expectation failed for {field}: expected {value!r}, got {actual!r}")
    verify_receipts(replay.receipts)
    if replay.metrics != fixture.get("expected_metrics", replay.metrics):
        raise ValueError(f"metric mismatch: expected {fixture.get('expected_metrics')}, got {replay.metrics}")
    by_org = {lane.normalized_lane["organization"]: lane.state for lane in replay.lanes.values()}
    expected_states = {_norm_text(k): v for k, v in fixture.get("expected_final_states", {}).items()}
    if expected_states and by_org != expected_states:
        raise ValueError(f"final-state mismatch: expected {expected_states}, got {by_org}")
    return {"ok": True, "events_replayed": len(fixture["events"]), "receipt_tip": replay.receipts[-1]["digest"] if replay.receipts else "GENESIS", "metrics": replay.metrics, "final_states": by_org, "receipts": replay.receipts}


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay and verify OneWriter demo events")
    parser.add_argument("fixture", nargs="?", type=Path, default=HERE / "demo_events.json")
    parser.add_argument("--receipts-out", type=Path)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    result = replay_fixture(fixture)
    if args.receipts_out:
        args.receipts_out.write_text(json.dumps(result["receipts"], indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "receipts"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
