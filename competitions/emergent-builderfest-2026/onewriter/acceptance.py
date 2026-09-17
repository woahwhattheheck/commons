#!/usr/bin/env python3
"""Deterministic offline acceptance engine for the OneWriter demo contract.

The bundled fixture is trusted synthetic input. A deployed implementation MUST derive event
timestamps and actor roles from its authenticated backend; caller-supplied role/time fields are
not production authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent

LANE_FIELDS = ("organization", "domain", "route", "purpose", "opportunity")
VALID_ROLES = frozenset({"WORKER", "SYSTEM", "HUMAN_SOURCE", "OPERATOR"})
ACTION_ROLES = {
    "PROPOSE": "WORKER",
    "ACQUIRE_LEASE": "WORKER",
    "RELEASE_LEASE": "WORKER",
    "PROVIDER_SENT": "WORKER",
    "PROVIDER_BOUNCE": "WORKER",
    "EXPIRE_LEASE": "SYSTEM",
    "HUMAN_EVENT": "HUMAN_SOURCE",
    "PLACE_HOLD": "OPERATOR",
}
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_DOMAIN = re.compile(
    r"^(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z"
)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _clean_text(value: Any, field_name: str, *, max_length: int = 512) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    value = unicodedata.normalize("NFKC", value)
    for char in value:
        category = unicodedata.category(char)
        if category.startswith("C") or category in {"Zl", "Zp"}:
            raise ValueError(
                f"{field_name} contains a control, format, or line-separator character"
            )
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError(f"{field_name} must be non-empty")
    if len(cleaned) > max_length:
        raise ValueError(f"{field_name} exceeds {max_length} characters")
    return cleaned


def _norm_text(value: Any, field_name: str = "text") -> str:
    return _clean_text(value, field_name).casefold()


def _norm_domain(value: Any) -> str:
    domain = _norm_text(value, "lane.domain")
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/", 1)[0].strip(".")
    if domain.startswith("www."):
        domain = domain[4:]
    if not domain or not _DOMAIN.fullmatch(domain):
        raise ValueError("lane.domain is not a valid normalized hostname")
    return domain


def normalize_lane(lane: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(lane, Mapping):
        raise ValueError("lane must be an object")
    keys = set(lane)
    required = set(LANE_FIELDS)
    missing = sorted(required - keys)
    extra = sorted(keys - required)
    if missing:
        raise ValueError(f"lane missing fields: {', '.join(missing)}")
    if extra:
        raise ValueError(f"lane has unsupported fields: {', '.join(extra)}")
    return {
        "organization": _norm_text(lane["organization"], "lane.organization"),
        "domain": _norm_domain(lane["domain"]),
        "route": _norm_text(lane["route"], "lane.route"),
        "purpose": _norm_text(lane["purpose"], "lane.purpose"),
        "opportunity": _norm_text(lane["opportunity"], "lane.opportunity"),
    }


def collision_key(lane: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canon(normalize_lane(lane))).hexdigest()


def parse_time(value: Any) -> datetime:
    cleaned = _clean_text(value, "event.at", max_length=64)
    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("event timestamp must be a valid ISO-8601 instant") from exc
    if parsed.tzinfo is None:
        raise ValueError("event timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _optional_ref(event: Mapping[str, Any], name: str) -> str | None:
    value = event.get(name)
    if value is None:
        return None
    return _clean_text(value, f"event.{name}", max_length=512)


@dataclass
class LaneState:
    normalized_lane: dict[str, str]
    state: str = "CLEAR"
    lease_holder: str | None = None
    lease_expires_at: datetime | None = None
    lease_return_state: str | None = None
    stale_expired: bool = False


@dataclass
class Replay:
    lanes: dict[str, LaneState] = field(default_factory=dict)
    receipts: list[dict[str, Any]] = field(default_factory=list)
    seen_event_ids: set[str] = field(default_factory=set)
    last_event_at: datetime | None = None
    metrics: dict[str, int] = field(default_factory=lambda: {
        "collisions_prevented": 0,
        "duplicate_touches_prevented": 0,
        "stale_leases_recovered": 0,
        "route_failures": 0,
        "human_reopens": 0,
    })

    def _prepare_event(
        self, event: Mapping[str, Any]
    ) -> tuple[dict[str, Any], datetime, str]:
        if not isinstance(event, Mapping):
            raise ValueError("event must be an object")
        allowed_fields = {
            "event_id",
            "at",
            "actor",
            "role",
            "action",
            "lane",
            "lease_seconds",
            "provider_receipt",
            "human_event_ref",
            "expect",
        }
        extra_fields = sorted(set(event) - allowed_fields)
        if extra_fields:
            raise ValueError(f"event has unsupported fields: {', '.join(extra_fields)}")
        event_id = _clean_text(
            event.get("event_id"), "event.event_id", max_length=128
        )
        if event_id in self.seen_event_ids:
            raise ValueError(f"duplicate event_id {event_id}")
        at = parse_time(event.get("at"))
        if self.last_event_at is not None and at < self.last_event_at:
            raise ValueError("event timestamp moved backward")
        actor = _clean_text(event.get("actor"), "event.actor", max_length=128)
        role = _clean_text(event.get("role"), "event.role", max_length=32).upper()
        if role not in VALID_ROLES:
            raise ValueError(f"unsupported event role {role}")
        if role == "SYSTEM" and actor != "system":
            raise ValueError("SYSTEM role requires canonical system actor")
        if role != "SYSTEM" and actor == "system":
            raise ValueError("canonical system actor requires SYSTEM role")
        action = _clean_text(
            event.get("action"), "event.action", max_length=64
        ).upper()
        normalized_lane = normalize_lane(event.get("lane"))
        key = hashlib.sha256(_canon(normalized_lane)).hexdigest()

        lease_seconds = event.get("lease_seconds")
        if lease_seconds is not None and (
            isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int)
        ):
            raise ValueError("event.lease_seconds must be an integer")
        provider_receipt = _optional_ref(event, "provider_receipt")
        human_event_ref = _optional_ref(event, "human_event_ref")

        decision_input = {
            "event_id": event_id,
            "at": _format_time(at),
            "actor": actor,
            "role": role,
            "action": action,
            "collision_key": key,
            "normalized_lane": normalized_lane,
            "lease_seconds": lease_seconds,
            "provider_receipt": provider_receipt,
            "human_event_ref": human_event_ref,
        }
        self.seen_event_ids.add(event_id)
        self.last_event_at = at
        return decision_input, at, key

    def _receipt(
        self,
        decision_input: dict[str, Any],
        prior: str | None,
        next_state: str | None,
        accepted: bool,
        reason: str,
    ) -> dict[str, Any]:
        prior_digest = self.receipts[-1]["digest"] if self.receipts else "GENESIS"
        payload = {
            "seq": len(self.receipts) + 1,
            "event_id": decision_input["event_id"],
            "at": decision_input["at"],
            "actor": decision_input["actor"],
            "role": decision_input["role"],
            "collision_key": decision_input["collision_key"],
            "action": decision_input["action"],
            "accepted": accepted,
            "prior_state": prior,
            "next_state": next_state,
            "reason": reason,
            "decision_input": deepcopy(decision_input),
            "event_digest": hashlib.sha256(_canon(decision_input)).hexdigest(),
            "prior_digest": prior_digest,
        }
        payload["digest"] = hashlib.sha256(_canon(payload)).hexdigest()
        self.receipts.append(payload)
        return payload

    def _finish_lease(self, lane: LaneState) -> str:
        target = lane.lease_return_state or "CLEAR"
        lane.state = target
        lane.lease_holder = None
        lane.lease_expires_at = None
        lane.lease_return_state = None
        return target

    def apply(self, event: Mapping[str, Any]) -> dict[str, Any]:
        decision, now, key = self._prepare_event(event)
        action = decision["action"]
        role = decision["role"]
        actor = decision["actor"]
        lane = self.lanes.get(key)
        prior = lane.state if lane else None

        required_role = ACTION_ROLES.get(action)
        if required_role is not None and role != required_role:
            return self._receipt(
                decision,
                prior,
                prior,
                False,
                f"role_requires_{required_role.lower()}",
            )

        if action == "PROPOSE":
            if lane is not None:
                return self._receipt(decision, prior, prior, False, "lane_exists")
            lane = LaneState(deepcopy(decision["normalized_lane"]))
            self.lanes[key] = lane
            return self._receipt(decision, prior, "CLEAR", True, "lane_created")

        if lane is None:
            return self._receipt(decision, prior, prior, False, "unknown_lane")

        if action == "ACQUIRE_LEASE":
            if lane.state == "LEASED":
                if (
                    lane.lease_expires_at is not None
                    and now >= lane.lease_expires_at
                ):
                    return self._receipt(
                        decision,
                        prior,
                        prior,
                        False,
                        "expired_lease_requires_system_recovery",
                    )
                self.metrics["collisions_prevented"] += 1
                return self._receipt(
                    decision, prior, prior, False, "active_lease"
                )
            if lane.state == "SENT_DNR":
                self.metrics["duplicate_touches_prevented"] += 1
                return self._receipt(decision, prior, prior, False, "sent_dnr")
            if lane.state == "DEAD_ROUTE":
                return self._receipt(decision, prior, prior, False, "dead_route")
            if lane.state == "HOLD":
                return self._receipt(decision, prior, prior, False, "hold")
            if lane.state not in {"CLEAR", "HUMAN_EVENT_REOPEN"}:
                return self._receipt(
                    decision, prior, prior, False, "invalid_state"
                )
            seconds = decision["lease_seconds"]
            if seconds is None or seconds < 1 or seconds > 3600:
                return self._receipt(
                    decision, prior, prior, False, "invalid_lease_seconds"
                )
            lane.lease_return_state = lane.state
            lane.state = "LEASED"
            lane.lease_holder = actor
            lane.lease_expires_at = now + timedelta(seconds=seconds)
            if lane.stale_expired:
                self.metrics["stale_leases_recovered"] += 1
                lane.stale_expired = False
            return self._receipt(
                decision, prior, lane.state, True, "lease_acquired"
            )

        if action == "EXPIRE_LEASE":
            if lane.state != "LEASED" or lane.lease_expires_at is None:
                return self._receipt(
                    decision, prior, prior, False, "no_active_lease"
                )
            if now < lane.lease_expires_at:
                return self._receipt(
                    decision, prior, prior, False, "lease_not_expired"
                )
            target = self._finish_lease(lane)
            lane.stale_expired = True
            return self._receipt(
                decision, prior, target, True, "lease_expired"
            )

        if action == "RELEASE_LEASE":
            if lane.state != "LEASED":
                return self._receipt(
                    decision, prior, prior, False, "no_active_lease"
                )
            if lane.lease_holder != actor:
                return self._receipt(
                    decision, prior, prior, False, "not_lease_holder"
                )
            if (
                lane.lease_expires_at is None
                or now >= lane.lease_expires_at
            ):
                return self._receipt(
                    decision, prior, prior, False, "lease_expired"
                )
            target = self._finish_lease(lane)
            return self._receipt(
                decision, prior, target, True, "lease_released"
            )

        if action in {"PROVIDER_SENT", "PROVIDER_BOUNCE"}:
            if lane.state != "LEASED":
                return self._receipt(
                    decision, prior, prior, False, "no_active_lease"
                )
            if lane.lease_holder != actor:
                return self._receipt(
                    decision, prior, prior, False, "not_lease_holder"
                )
            if (
                lane.lease_expires_at is None
                or now >= lane.lease_expires_at
            ):
                return self._receipt(
                    decision, prior, prior, False, "lease_expired"
                )
            if not decision["provider_receipt"]:
                return self._receipt(
                    decision,
                    prior,
                    prior,
                    False,
                    "missing_provider_receipt",
                )
            lane.lease_holder = None
            lane.lease_expires_at = None
            lane.lease_return_state = None
            if action == "PROVIDER_SENT":
                lane.state = "SENT_DNR"
                reason = "provider_sent"
            else:
                lane.state = "DEAD_ROUTE"
                self.metrics["route_failures"] += 1
                reason = "provider_bounce"
            return self._receipt(
                decision, prior, lane.state, True, reason
            )

        if action == "HUMAN_EVENT":
            if lane.state != "SENT_DNR":
                return self._receipt(
                    decision,
                    prior,
                    prior,
                    False,
                    "human_event_not_reopenable",
                )
            if not decision["human_event_ref"]:
                return self._receipt(
                    decision,
                    prior,
                    prior,
                    False,
                    "missing_human_event_ref",
                )
            lane.state = "HUMAN_EVENT_REOPEN"
            self.metrics["human_reopens"] += 1
            return self._receipt(
                decision, prior, lane.state, True, "human_event_reopen"
            )

        if action == "PLACE_HOLD":
            lane.state = "HOLD"
            lane.lease_holder = None
            lane.lease_expires_at = None
            lane.lease_return_state = None
            lane.stale_expired = False
            return self._receipt(
                decision, prior, lane.state, True, "hold_placed"
            )

        return self._receipt(
            decision, prior, prior, False, "unknown_action"
        )


_RECEIPT_KEYS = {
    "seq",
    "event_id",
    "at",
    "actor",
    "role",
    "collision_key",
    "action",
    "accepted",
    "prior_state",
    "next_state",
    "reason",
    "decision_input",
    "event_digest",
    "prior_digest",
    "digest",
}


def verify_receipts(receipts: list[dict[str, Any]]) -> None:
    if not isinstance(receipts, list):
        raise ValueError("receipts must be a list")
    prior = "GENESIS"
    seen_event_ids: set[str] = set()
    for index, receipt in enumerate(receipts, start=1):
        if not isinstance(receipt, dict) or set(receipt) != _RECEIPT_KEYS:
            raise ValueError(f"receipt schema mismatch at {index}")
        if receipt.get("seq") != index:
            raise ValueError(f"receipt sequence mismatch at {index}")
        event_id = receipt.get("event_id")
        if event_id in seen_event_ids:
            raise ValueError(f"duplicate receipt event_id at {index}")
        seen_event_ids.add(event_id)
        if receipt.get("prior_digest") != prior:
            raise ValueError(f"receipt chain mismatch at {index}")
        decision_input = receipt.get("decision_input")
        if not isinstance(decision_input, dict):
            raise ValueError(f"receipt decision input mismatch at {index}")
        if receipt.get("event_id") != decision_input.get("event_id"):
            raise ValueError(f"receipt event binding mismatch at {index}")
        event_digest = hashlib.sha256(_canon(decision_input)).hexdigest()
        if receipt.get("event_digest") != event_digest:
            raise ValueError(f"receipt event digest mismatch at {index}")
        digest = receipt.get("digest")
        if not isinstance(digest, str) or not _HEX_64.fullmatch(digest):
            raise ValueError(f"receipt digest format mismatch at {index}")
        candidate = deepcopy(receipt)
        candidate.pop("digest")
        expected = hashlib.sha256(_canon(candidate)).hexdigest()
        if digest != expected:
            raise ValueError(f"receipt digest mismatch at {index}")
        prior = digest


def replay_fixture(fixture: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(fixture, Mapping) or not isinstance(
        fixture.get("events"), list
    ):
        raise ValueError("fixture must contain an events list")
    replay = Replay()
    for event in fixture["events"]:
        receipt = replay.apply(event)
        expected = event.get("expect", {})
        if not isinstance(expected, Mapping):
            raise ValueError("event.expect must be an object")
        for field, value in expected.items():
            actual = (
                receipt["next_state"]
                if field == "state"
                else receipt.get(field)
            )
            if actual != value:
                raise ValueError(
                    f"{event.get('event_id')} expectation failed for {field}: "
                    f"expected {value!r}, got {actual!r}"
                )
    verify_receipts(replay.receipts)
    expected_metrics = fixture.get("expected_metrics", replay.metrics)
    if replay.metrics != expected_metrics:
        raise ValueError(
            f"metric mismatch: expected {expected_metrics}, got {replay.metrics}"
        )
    by_org = {
        lane.normalized_lane["organization"]: lane.state
        for lane in replay.lanes.values()
    }
    expected_states = {
        _norm_text(key, "expected_final_states key"): value
        for key, value in fixture.get("expected_final_states", {}).items()
    }
    if expected_states and by_org != expected_states:
        raise ValueError(
            f"final-state mismatch: expected {expected_states}, got {by_org}"
        )
    return {
        "ok": True,
        "events_replayed": len(fixture["events"]),
        "receipt_tip": (
            replay.receipts[-1]["digest"] if replay.receipts else "GENESIS"
        ),
        "metrics": replay.metrics,
        "final_states": by_org,
        "receipts": replay.receipts,
    }


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON token {value}")


def _load_fixture(path: Path) -> dict[str, Any]:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_nonfinite,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid fixture: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay and verify OneWriter demo events"
    )
    parser.add_argument(
        "fixture", nargs="?", type=Path, default=HERE / "demo_events.json"
    )
    parser.add_argument("--receipts-out", type=Path)
    args = parser.parse_args()
    try:
        fixture = _load_fixture(args.fixture)
        result = replay_fixture(fixture)
        if args.receipts_out:
            args.receipts_out.write_text(
                json.dumps(
                    result["receipts"],
                    indent=2,
                    ensure_ascii=False,
                    allow_nan=False,
                )
                + "\n",
                encoding="utf-8",
            )
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key != "receipts"
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
