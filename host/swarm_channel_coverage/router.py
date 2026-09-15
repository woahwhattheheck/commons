from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

INPUT_SCHEMA = "swarm-channel-coverage/v1"
REPORT_SCHEMA = "swarm-channel-coverage-report/v1"
KINDS = frozenset({"DEMAND", "TAKE", "SHIP", "MESSAGE"})
STATES = frozenset({"UNDERCOVERED_DEMAND", "SATURATED", "ACTIVE", "QUIET", "HOLD"})
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"


class ValidationError(ValueError):
    pass


def _reject_constant(value: str) -> Any:
    raise ValidationError(f"non-finite JSON number: {value}")


def _reject_float(value: str) -> Any:
    raise ValidationError(f"floating-point JSON number not allowed: {value}")


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValidationError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def loads_strict(raw: str | bytes) -> Any:
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise ValidationError("input is not valid UTF-8") from exc
    if type(raw) is not str:
        raise ValidationError("JSON input must be str or UTF-8 bytes")
    try:
        return json.loads(
            raw,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except ValidationError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValidationError(f"invalid JSON: {exc}") from exc


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_object(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValidationError(f"{name} must be an object")
    return value


def _require_list(value: Any, name: str, maximum: int) -> list[Any]:
    if type(value) is not list:
        raise ValidationError(f"{name} must be an array")
    if len(value) > maximum:
        raise ValidationError(f"{name} exceeds maximum size {maximum}")
    return value


def _exact_keys(obj: dict[str, Any], required: set[str], name: str) -> None:
    keys = set(obj)
    if keys != required:
        missing = sorted(required - keys)
        extra = sorted(keys - required)
        raise ValidationError(f"{name} keys mismatch; missing={missing} extra={extra}")


def _require_str(value: Any, name: str, maximum: int = 256, allow_empty: bool = False) -> str:
    if type(value) is not str:
        raise ValidationError(f"{name} must be a string")
    if not allow_empty and not value:
        raise ValidationError(f"{name} must not be empty")
    if len(value) > maximum:
        raise ValidationError(f"{name} exceeds {maximum} characters")
    return value


def _safe_id(value: Any, name: str) -> str:
    text = _require_str(value, name, 128)
    if not _ID_RE.fullmatch(text):
        raise ValidationError(f"{name} is not a safe identifier")
    return text


def _digest(value: Any, name: str) -> str:
    text = _require_str(value, name, 64)
    if not _SHA_RE.fullmatch(text):
        raise ValidationError(f"{name} must be lowercase SHA-256")
    return text


def _int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int:
        raise ValidationError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValidationError(f"{name} must be in [{minimum}, {maximum}]")
    return value


def _utc(value: Any, name: str) -> datetime:
    text = _require_str(value, name, 20)
    try:
        parsed = datetime.strptime(text, _UTC_FMT).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValidationError(f"{name} must be canonical UTC seconds (YYYY-MM-DDTHH:MM:SSZ)") from exc
    if parsed.strftime(_UTC_FMT) != text:
        raise ValidationError(f"{name} is not canonical UTC")
    return parsed


def _age_minutes(as_of: datetime, when: datetime) -> int:
    seconds = int((as_of - when).total_seconds())
    return seconds // 60


def validate_packet(packet: Any, as_of_text: str) -> tuple[dict[str, Any], datetime]:
    root = _require_object(packet, "packet")
    _exact_keys(root, {"schema", "inventory", "events", "policy"}, "packet")
    if root["schema"] != INPUT_SCHEMA:
        raise ValidationError(f"unsupported schema: {root['schema']!r}")
    as_of = _utc(as_of_text, "as_of")

    inventory = _require_object(root["inventory"], "inventory")
    _exact_keys(inventory, {"source_ref", "source_sha256", "captured_at", "channels"}, "inventory")
    _safe_id(inventory["source_ref"], "inventory.source_ref")
    _digest(inventory["source_sha256"], "inventory.source_sha256")
    captured = _utc(inventory["captured_at"], "inventory.captured_at")
    if captured > as_of:
        raise ValidationError("inventory capture is in the future")

    channels = _require_list(inventory["channels"], "inventory.channels", 500)
    if not channels:
        raise ValidationError("inventory.channels must not be empty")
    channel_ids: set[str] = set()
    for idx, row in enumerate(channels):
        item = _require_object(row, f"inventory.channels[{idx}]")
        _exact_keys(item, {"channel_id", "label"}, f"inventory.channels[{idx}]")
        channel_id = _safe_id(item["channel_id"], f"inventory.channels[{idx}].channel_id")
        _require_str(item["label"], f"inventory.channels[{idx}].label", 120)
        if channel_id in channel_ids:
            raise ValidationError(f"duplicate channel_id: {channel_id}")
        channel_ids.add(channel_id)

    events = _require_list(root["events"], "events", 10000)
    event_ids: set[str] = set()
    demands: dict[str, dict[str, Any]] = {}
    ships: dict[str, dict[str, Any]] = {}
    work_events: list[dict[str, Any]] = []
    normalized_events: list[dict[str, Any]] = []
    for idx, row in enumerate(events):
        item = _require_object(row, f"events[{idx}]")
        _exact_keys(
            item,
            {"event_id", "channel_id", "actor_ref", "kind", "observed_at", "source_ref", "source_sha256", "work_key"},
            f"events[{idx}]",
        )
        event_id = _safe_id(item["event_id"], f"events[{idx}].event_id")
        if event_id in event_ids:
            raise ValidationError(f"duplicate event_id: {event_id}")
        event_ids.add(event_id)
        channel_id = _safe_id(item["channel_id"], f"events[{idx}].channel_id")
        if channel_id not in channel_ids:
            raise ValidationError(f"orphan event channel: {channel_id}")
        actor_ref = _safe_id(item["actor_ref"], f"events[{idx}].actor_ref")
        kind = _require_str(item["kind"], f"events[{idx}].kind", 16)
        if kind not in KINDS:
            raise ValidationError(f"invalid event kind: {kind}")
        observed = _utc(item["observed_at"], f"events[{idx}].observed_at")
        if observed > as_of:
            raise ValidationError(f"future event: {event_id}")
        source_ref = _safe_id(item["source_ref"], f"events[{idx}].source_ref")
        source_sha256 = _digest(item["source_sha256"], f"events[{idx}].source_sha256")
        work_key_raw = item["work_key"]
        if kind == "MESSAGE":
            if work_key_raw is not None:
                raise ValidationError("MESSAGE work_key must be null")
            work_key = None
        else:
            work_key = _safe_id(work_key_raw, f"events[{idx}].work_key")
        normalized = {
            "event_id": event_id,
            "channel_id": channel_id,
            "actor_ref": actor_ref,
            "kind": kind,
            "observed_at": item["observed_at"],
            "source_ref": source_ref,
            "source_sha256": source_sha256,
            "work_key": work_key,
        }
        normalized_events.append(normalized)
        if work_key is not None:
            work_events.append(normalized)
            if kind == "DEMAND":
                if work_key in demands:
                    raise ValidationError(f"duplicate DEMAND work_key: {work_key}")
                demands[work_key] = normalized
            elif kind == "SHIP":
                if work_key in ships:
                    raise ValidationError(f"duplicate SHIP work_key: {work_key}")
                ships[work_key] = normalized

    for event in work_events:
        key = event["work_key"]
        if event["kind"] in {"TAKE", "SHIP"} and key not in demands:
            raise ValidationError(f"{event['kind']} without DEMAND: {key}")
        if event["kind"] in {"TAKE", "SHIP"}:
            demand_time = _utc(demands[key]["observed_at"], "demand observed_at")
            event_time = _utc(event["observed_at"], "event observed_at")
            if event_time < demand_time:
                raise ValidationError(f"{event['kind']} precedes DEMAND: {key}")
        if event["kind"] == "TAKE" and key in ships:
            take_time = _utc(event["observed_at"], "take observed_at")
            ship_time = _utc(ships[key]["observed_at"], "ship observed_at")
            if take_time > ship_time:
                raise ValidationError(f"TAKE follows SHIP: {key}")

    policy = _require_object(root["policy"], "policy")
    _exact_keys(
        policy,
        {
            "active_window_minutes",
            "stale_after_minutes",
            "max_inventory_age_minutes",
            "saturation_worker_share_bps",
            "undercovered_max_active_actors",
            "max_inspect",
        },
        "policy",
    )
    active_window = _int(policy["active_window_minutes"], "policy.active_window_minutes", 1, 10080)
    stale_after = _int(policy["stale_after_minutes"], "policy.stale_after_minutes", active_window, 43200)
    max_inventory_age = _int(policy["max_inventory_age_minutes"], "policy.max_inventory_age_minutes", 1, 10080)
    saturation = _int(policy["saturation_worker_share_bps"], "policy.saturation_worker_share_bps", 1, 10000)
    undercovered = _int(policy["undercovered_max_active_actors"], "policy.undercovered_max_active_actors", 0, 1000)
    max_inspect = _int(policy["max_inspect"], "policy.max_inspect", 1, 100)

    normalized = {
        "schema": INPUT_SCHEMA,
        "inventory": {
            "source_ref": inventory["source_ref"],
            "source_sha256": inventory["source_sha256"],
            "captured_at": inventory["captured_at"],
            "channels": sorted(
                ({"channel_id": row["channel_id"], "label": row["label"]} for row in channels),
                key=lambda row: row["channel_id"],
            ),
        },
        "events": sorted(normalized_events, key=lambda row: row["event_id"]),
        "policy": {
            "active_window_minutes": active_window,
            "stale_after_minutes": stale_after,
            "max_inventory_age_minutes": max_inventory_age,
            "saturation_worker_share_bps": saturation,
            "undercovered_max_active_actors": undercovered,
            "max_inspect": max_inspect,
        },
    }
    return normalized, as_of


def _channel_projection(packet: dict[str, Any], as_of: datetime) -> tuple[list[dict[str, Any]], bool, list[str]]:
    policy = packet["policy"]
    inventory_time = _utc(packet["inventory"]["captured_at"], "inventory.captured_at")
    inventory_age = _age_minutes(as_of, inventory_time)
    global_hold = inventory_age > policy["max_inventory_age_minutes"]
    hold_reasons = ["STALE_INVENTORY"] if global_hold else []

    channels = {row["channel_id"]: row for row in packet["inventory"]["channels"]}
    events_by_channel: dict[str, list[dict[str, Any]]] = {channel_id: [] for channel_id in channels}
    for event in packet["events"]:
        events_by_channel[event["channel_id"]].append(event)

    demands = {event["work_key"]: event for event in packet["events"] if event["kind"] == "DEMAND"}
    shipped = {event["work_key"] for event in packet["events"] if event["kind"] == "SHIP"}
    unresolved = {key: event for key, event in demands.items() if key not in shipped}

    active_cutoff = as_of.timestamp() - policy["active_window_minutes"] * 60
    active_actors_by_channel: dict[str, set[str]] = {channel_id: set() for channel_id in channels}
    active_take_counts: dict[str, int] = {channel_id: 0 for channel_id in channels}
    for event in packet["events"]:
        if event["kind"] != "TAKE" or event["work_key"] not in unresolved:
            continue
        event_time = _utc(event["observed_at"], "take observed_at")
        if event_time.timestamp() >= active_cutoff:
            active_actors_by_channel[event["channel_id"]].add(event["actor_ref"])
            active_take_counts[event["channel_id"]] += 1

    slots = sum(len(actors) for actors in active_actors_by_channel.values())
    rows: list[dict[str, Any]] = []
    for channel_id in sorted(channels):
        channel_events = events_by_channel[channel_id]
        last_activity = None
        if channel_events:
            last_activity = max(event["observed_at"] for event in channel_events)
        last_age = None if last_activity is None else _age_minutes(as_of, _utc(last_activity, "last_activity"))
        unresolved_count = sum(1 for event in unresolved.values() if event["channel_id"] == channel_id)
        actors = sorted(active_actors_by_channel[channel_id])
        actor_count = len(actors)
        share_bps = 0 if slots == 0 else (actor_count * 10000) // slots
        stale = last_age is None or last_age >= policy["stale_after_minutes"]
        if global_hold:
            state = "HOLD"
        elif unresolved_count > 0 and actor_count <= policy["undercovered_max_active_actors"]:
            state = "UNDERCOVERED_DEMAND"
        elif actor_count > 0 and share_bps >= policy["saturation_worker_share_bps"]:
            state = "SATURATED"
        elif actor_count > 0 or (last_age is not None and last_age <= policy["active_window_minutes"]):
            state = "ACTIVE"
        else:
            state = "QUIET"
        pressure_milli = unresolved_count * 1000 // max(1, actor_count)
        rows.append(
            {
                "channel_id": channel_id,
                "label": channels[channel_id]["label"],
                "state": state,
                "unresolved_demand": unresolved_count,
                "active_actor_count": actor_count,
                "active_actors": actors,
                "active_take_count": active_take_counts[channel_id],
                "worker_share_bps": share_bps,
                "pressure_milli": pressure_milli,
                "last_activity_at": last_activity,
                "last_activity_age_minutes": last_age,
                "stale": stale,
            }
        )
    return rows, global_hold, hold_reasons


def _queue(rows: list[dict[str, Any]], policy: dict[str, Any], global_hold: bool) -> list[dict[str, Any]]:
    if global_hold:
        return []
    demand_rows = [row for row in rows if row["unresolved_demand"] > 0 and row["state"] != "HOLD"]
    undercovered = [row for row in demand_rows if row["state"] == "UNDERCOVERED_DEMAND"]
    candidates = [row for row in demand_rows if row["state"] != "SATURATED"] if undercovered else demand_rows

    def sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
        if row["active_actor_count"] == 0:
            tier = 0
        elif row["state"] == "UNDERCOVERED_DEMAND":
            tier = 1
        elif row["stale"]:
            tier = 2
        elif row["state"] != "SATURATED":
            tier = 3
        else:
            tier = 4
        last = row["last_activity_at"] or "0000-00-00T00:00:00Z"
        return (tier, -row["pressure_milli"], -row["unresolved_demand"], last, row["channel_id"])

    selected = sorted(candidates, key=sort_key)[: policy["max_inspect"]]
    return [
        {
            "rank": idx + 1,
            "channel_id": row["channel_id"],
            "state": row["state"],
            "unresolved_demand": row["unresolved_demand"],
            "active_actor_count": row["active_actor_count"],
            "pressure_milli": row["pressure_milli"],
            "reason": (
                "ZERO_COVERAGE_DEMAND"
                if row["active_actor_count"] == 0
                else "UNDERCOVERED_DEMAND"
                if row["state"] == "UNDERCOVERED_DEMAND"
                else "STALE_DEMAND"
                if row["stale"]
                else "UNRESOLVED_DEMAND"
            ),
        }
        for idx, row in enumerate(selected)
    ]


def compile_report(packet: Any, as_of_text: str) -> dict[str, Any]:
    normalized, as_of = validate_packet(packet, as_of_text)
    rows, global_hold, hold_reasons = _channel_projection(normalized, as_of)
    queue = _queue(rows, normalized["policy"], global_hold)
    source = {
        "input_sha256": sha256_hex(canonical_bytes(normalized)),
        "inventory_source_ref": normalized["inventory"]["source_ref"],
        "inventory_source_sha256": normalized["inventory"]["source_sha256"],
    }
    projection = {
        "schema": REPORT_SCHEMA,
        "as_of": as_of_text,
        "status": "HOLD" if global_hold else "ROUTED",
        "hold_reasons": hold_reasons,
        "authority": {
            "inspection_guidance_only": True,
            "take_authorized": False,
            "slack_mutation_authorized": False,
            "external_send_authorized": False,
        },
        "source": source,
        "channels": rows,
        "inspect_next": queue,
    }
    return {
        "report": projection,
        "receipt_sha256": sha256_hex(canonical_bytes(projection)),
    }


def verify_report(packet: Any, report: Any, as_of_text: str) -> bool:
    if type(report) is not dict:
        return False
    try:
        expected = compile_report(packet, as_of_text)
    except ValidationError:
        return False
    return canonical_bytes(expected) == canonical_bytes(report)
