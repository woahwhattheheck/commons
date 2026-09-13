"""Read-only Google Calendar -> sales-meeting-readiness integration.

This module intentionally has no Google Calendar mutation client. A trusted host:
1) supplies a separately retained verified-human meeting trigger,
2) asks :func:`build_google_availability_plan` for exact free/busy arguments,
3) performs the read-only Google Calendar get_availability call,
4) immediately wraps that result with :func:`capture_google_availability`, and
5) compiles it through the already-landed sales_meeting_readiness core.

External digests are trust roots retained by the host; candidate packet bytes cannot
self-mint them.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from revenue.sales_meeting_readiness.meeting_readiness import (
    SCHEMA as CORE_SCHEMA,
    READY as CORE_READY,
    busy_digest as core_busy_digest,
    canonical_json_bytes as core_canonical_json_bytes,
    compile_meeting_readiness,
    render_markdown as render_core_markdown,
    request_digest as core_request_digest,
)

TRIGGER_SCHEMA = "sales-meeting-calendar-trigger/v1"
HUMAN_AUTHORITY_SCHEMA = "verified-human-meeting-request/v1"
PLAN_SCHEMA = "google-calendar-freebusy-plan/v1"
CAPTURE_SCHEMA = "google-calendar-freebusy-capture/v1"
RECEIPT_SCHEMA = "sales-meeting-calendar-consumer-receipt/v1"
PROVIDER_REF = "google-calendar:get_availability/v1"
CALENDAR_ID = "primary"

_SHA = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?(?:\(?\d{3}\)?[ .-]?)\d{3}[ .-]?\d{4}(?!\d)")
_SECRET = re.compile(r"(?i)\b(?:sk_live_|ghp_|github_pat_|AIza|xox[baprs]-)[A-Za-z0-9_\-]{8,}")

PREP_SCALARS = ("objective", "recommended_opening", "recommended_closing")
PREP_LISTS = ("key_questions", "likely_asks", "risks_commitments_to_avoid", "owner_actions")


class CalendarConsumerError(ValueError):
    """Raised when trigger/capture bytes cannot support an owner-review receipt."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_json_loads(data: str | bytes) -> Any:
    def pairs(items: Iterable[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise CalendarConsumerError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    try:
        return json.loads(data, object_pairs_hook=pairs)
    except CalendarConsumerError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CalendarConsumerError(f"invalid JSON: {exc}") from exc


def _exact(obj: Any, required: set[str], optional: set[str] | None = None, *, where: str) -> dict[str, Any]:
    if type(obj) is not dict:
        raise CalendarConsumerError(f"{where} must be an object")
    optional = optional or set()
    missing = required - set(obj)
    unknown = set(obj) - required - optional
    if missing:
        raise CalendarConsumerError(f"{where} missing keys: {sorted(missing)}")
    if unknown:
        raise CalendarConsumerError(f"{where} unknown keys: {sorted(unknown)}")
    return obj


def _text(value: Any, *, where: str, maximum: int = 256, allow_empty: bool = False) -> str:
    if type(value) is not str:
        raise CalendarConsumerError(f"{where} must be a string")
    if len(value) > maximum or (not allow_empty and not value) or "\x00" in value:
        raise CalendarConsumerError(f"{where} invalid string")
    return value


def _safe_id(value: Any, *, where: str) -> str:
    text = _text(value, where=where, maximum=128)
    if not _ID.fullmatch(text) or _EMAIL.search(text) or _PHONE.search(text) or _SECRET.search(text):
        raise CalendarConsumerError(f"{where} must be a safe opaque identifier")
    return text


def _sha(value: Any, *, where: str) -> str:
    text = _text(value, where=where, maximum=64)
    if not _SHA.fullmatch(text):
        raise CalendarConsumerError(f"{where} must be lowercase SHA-256")
    return text


def _aware(value: Any, *, where: str) -> datetime:
    text = _text(value, where=where, maximum=40)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CalendarConsumerError(f"{where} must be RFC3339") from exc
    if dt.tzinfo is None:
        raise CalendarConsumerError(f"{where} must include timezone")
    return dt.astimezone(timezone.utc)


def _utc_text(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise CalendarConsumerError("datetime must be timezone-aware")
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _iana(value: Any, *, where: str) -> str:
    name = _text(value, where=where, maximum=64)
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise CalendarConsumerError(f"{where} is not an IANA timezone") from exc
    return name


def _interval(value: Any, *, where: str) -> tuple[dict[str, str], datetime, datetime]:
    obj = _exact(value, {"start", "end"}, where=where)
    start = _aware(obj["start"], where=f"{where}.start")
    end = _aware(obj["end"], where=f"{where}.end")
    if end <= start:
        raise CalendarConsumerError(f"{where} end must be after start")
    return {"start": _utc_text(start), "end": _utc_text(end)}, start, end


def _intervals(value: Any, *, where: str, maximum: int, allow_empty: bool = False) -> list[dict[str, str]]:
    if type(value) is not list or len(value) > maximum or (not allow_empty and not value):
        raise CalendarConsumerError(f"{where} must be a bounded list")
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(value):
        normalized, _, _ = _interval(item, where=f"{where}[{index}]")
        key = (normalized["start"], normalized["end"])
        if key in seen:
            raise CalendarConsumerError(f"{where} contains duplicate interval")
        seen.add(key)
        out.append(normalized)
    return sorted(out, key=lambda x: (x["start"], x["end"]))


def _validate_prep(prep: Any) -> dict[str, Any]:
    required = {"context", *PREP_SCALARS, *PREP_LISTS}
    obj = _exact(prep, required, where="trigger.prep")
    context = obj["context"]
    if type(context) is not list or not context or len(context) > 16:
        raise CalendarConsumerError("trigger.prep.context must be nonempty bounded list")
    context_out: list[dict[str, str]] = []
    for index, raw in enumerate(context):
        item = _exact(raw, {"text", "source_ref"}, where=f"trigger.prep.context[{index}]")
        text = _text(item["text"], where=f"trigger.prep.context[{index}].text", maximum=2400)
        source_ref = _safe_id(item["source_ref"], where=f"trigger.prep.context[{index}].source_ref")
        if _EMAIL.search(text) or _PHONE.search(text) or _SECRET.search(text):
            raise CalendarConsumerError("prep context contains disallowed direct contact/secret material")
        context_out.append({"text": text, "source_ref": source_ref})
    out: dict[str, Any] = {"context": sorted(context_out, key=lambda x: (x["source_ref"], x["text"]))}
    for key in PREP_SCALARS:
        value = _text(obj[key], where=f"trigger.prep.{key}", maximum=2400)
        if _EMAIL.search(value) or _PHONE.search(value) or _SECRET.search(value):
            raise CalendarConsumerError(f"trigger.prep.{key} contains disallowed material")
        out[key] = value
    for key in PREP_LISTS:
        value = obj[key]
        if type(value) is not list or not value or len(value) > 16:
            raise CalendarConsumerError(f"trigger.prep.{key} must be nonempty bounded list")
        items: list[str] = []
        for index, raw in enumerate(value):
            text = _text(raw, where=f"trigger.prep.{key}[{index}]", maximum=2400)
            if _EMAIL.search(text) or _PHONE.search(text) or _SECRET.search(text):
                raise CalendarConsumerError(f"trigger.prep.{key}[{index}] contains disallowed material")
            items.append(text)
        if len(set(items)) != len(items):
            raise CalendarConsumerError(f"trigger.prep.{key} contains duplicates")
        out[key] = items
    return out


def _normalize_trigger(trigger: Any) -> dict[str, Any]:
    obj = _exact(
        trigger,
        {"schema", "opportunity_id", "owner_ref", "counterparty_ref", "thread_ref",
         "inbound", "request", "prep", "human_authority"},
        where="trigger",
    )
    if obj["schema"] != TRIGGER_SCHEMA:
        raise CalendarConsumerError("unsupported trigger schema")
    opportunity_id = _safe_id(obj["opportunity_id"], where="trigger.opportunity_id")
    owner_ref = _safe_id(obj["owner_ref"], where="trigger.owner_ref")
    counterparty_ref = _safe_id(obj["counterparty_ref"], where="trigger.counterparty_ref")
    thread_ref = _safe_id(obj["thread_ref"], where="trigger.thread_ref")

    inbound = _exact(obj["inbound"], {"observation_id", "content_sha256", "received_at"}, where="trigger.inbound")
    inbound_norm = {
        "observation_id": _safe_id(inbound["observation_id"], where="trigger.inbound.observation_id"),
        "content_sha256": _sha(inbound["content_sha256"], where="trigger.inbound.content_sha256"),
        "received_at": _utc_text(_aware(inbound["received_at"], where="trigger.inbound.received_at")),
    }

    request = _exact(obj["request"], {"duration_minutes", "timezone", "windows"}, where="trigger.request")
    if type(request["duration_minutes"]) is not int or not 5 <= request["duration_minutes"] <= 240:
        raise CalendarConsumerError("trigger.request.duration_minutes outside bounds")
    timezone_name = _iana(request["timezone"], where="trigger.request.timezone")
    windows = _intervals(request["windows"], where="trigger.request.windows", maximum=16)
    duration = timedelta(minutes=request["duration_minutes"])
    for index, item in enumerate(windows):
        if _aware(item["end"], where="window.end") - _aware(item["start"], where="window.start") < duration:
            raise CalendarConsumerError(f"trigger.request.windows[{index}] is shorter than requested duration")
    request_norm = {"duration_minutes": request["duration_minutes"], "timezone": timezone_name, "windows": windows}

    authority = _exact(
        obj["human_authority"],
        {"schema", "authority_id", "provider_ref", "event_id", "event_sha256", "observed_at",
         "opportunity_id", "thread_ref", "classification", "verified_human", "meeting_requested"},
        where="trigger.human_authority",
    )
    if authority["schema"] != HUMAN_AUTHORITY_SCHEMA:
        raise CalendarConsumerError("unsupported human authority schema")
    if authority["classification"] != "MEETING_REQUEST" or authority["verified_human"] is not True or authority["meeting_requested"] is not True:
        raise CalendarConsumerError("trigger is not verified human meeting intent")
    auth_norm = {
        "schema": HUMAN_AUTHORITY_SCHEMA,
        "authority_id": _safe_id(authority["authority_id"], where="trigger.human_authority.authority_id"),
        "provider_ref": _safe_id(authority["provider_ref"], where="trigger.human_authority.provider_ref"),
        "event_id": _safe_id(authority["event_id"], where="trigger.human_authority.event_id"),
        "event_sha256": _sha(authority["event_sha256"], where="trigger.human_authority.event_sha256"),
        "observed_at": _utc_text(_aware(authority["observed_at"], where="trigger.human_authority.observed_at")),
        "opportunity_id": _safe_id(authority["opportunity_id"], where="trigger.human_authority.opportunity_id"),
        "thread_ref": _safe_id(authority["thread_ref"], where="trigger.human_authority.thread_ref"),
        "classification": "MEETING_REQUEST",
        "verified_human": True,
        "meeting_requested": True,
    }
    bindings = (
        (auth_norm["event_id"], inbound_norm["observation_id"], "event id"),
        (auth_norm["event_sha256"], inbound_norm["content_sha256"], "event digest"),
        (auth_norm["observed_at"], inbound_norm["received_at"], "event time"),
        (auth_norm["opportunity_id"], opportunity_id, "opportunity"),
        (auth_norm["thread_ref"], thread_ref, "thread"),
    )
    for left, right, label in bindings:
        if left != right:
            raise CalendarConsumerError(f"human authority {label} binding mismatch")

    return {
        "schema": TRIGGER_SCHEMA,
        "opportunity_id": opportunity_id,
        "owner_ref": owner_ref,
        "counterparty_ref": counterparty_ref,
        "thread_ref": thread_ref,
        "inbound": inbound_norm,
        "request": request_norm,
        "prep": _validate_prep(obj["prep"]),
        "human_authority": auth_norm,
    }


def _human_authority_sha(trigger: dict[str, Any]) -> str:
    return sha256_hex(canonical_json_bytes(trigger["human_authority"]))




def _opaque_digest_id(prefix: str, digest: str) -> str:
    """Encode a SHA into a safe opaque ID without phone-like digit runs."""
    _sha(digest, where="digest")
    # Letter separators every two nibbles prevent the phone-shape guard from
    # ever interpreting an unlucky hash substring as contact information.
    encoded = "x".join(digest[i:i + 2] for i in range(0, len(digest), 2))
    value = f"{prefix}/{encoded}"
    return _safe_id(value, where="generated opaque id")


def _require_external_sha(actual: str, expected: Any, *, where: str) -> str:
    expected_sha = _sha(expected, where=where)
    if actual != expected_sha:
        raise CalendarConsumerError(f"{where} does not match retained authority")
    return expected_sha


def build_google_availability_plan(trigger: Any, *, expected_human_authority_sha256: str) -> dict[str, Any]:
    """Return exact read-only Google Calendar free/busy arguments for the trigger."""
    normalized = _normalize_trigger(trigger)
    authority_sha = _require_external_sha(
        _human_authority_sha(normalized), expected_human_authority_sha256,
        where="expected_human_authority_sha256",
    )
    windows = normalized["request"]["windows"]
    req_sha = core_request_digest(normalized["opportunity_id"], normalized["thread_ref"], normalized["request"])
    plan_core = {
        "schema": PLAN_SCHEMA,
        "provider_ref": PROVIDER_REF,
        "calendar_id": CALENDAR_ID,
        "time_min": min(w["start"] for w in windows),
        "time_max": max(w["end"] for w in windows),
        "response_timezone_str": normalized["request"]["timezone"],
        "request_digest": req_sha,
        "human_authority_sha256": authority_sha,
    }
    return {**plan_core, "plan_sha256": sha256_hex(canonical_json_bytes(plan_core))}


def google_tool_args(plan: Any) -> dict[str, Any]:
    """Return only the exact read-only get_availability arguments."""
    normalized = _normalize_plan(plan)
    return {
        "calendar_ids": [normalized["calendar_id"]],
        "time_min": normalized["time_min"],
        "time_max": normalized["time_max"],
        "response_timezone_str": normalized["response_timezone_str"],
    }


def _normalize_plan(plan: Any) -> dict[str, Any]:
    obj = _exact(
        plan,
        {"schema", "provider_ref", "calendar_id", "time_min", "time_max", "response_timezone_str",
         "request_digest", "human_authority_sha256", "plan_sha256"},
        where="plan",
    )
    if obj["schema"] != PLAN_SCHEMA or obj["provider_ref"] != PROVIDER_REF or obj["calendar_id"] != CALENDAR_ID:
        raise CalendarConsumerError("plan provider/schema/calendar mismatch")
    core = {
        "schema": PLAN_SCHEMA,
        "provider_ref": PROVIDER_REF,
        "calendar_id": CALENDAR_ID,
        "time_min": _utc_text(_aware(obj["time_min"], where="plan.time_min")),
        "time_max": _utc_text(_aware(obj["time_max"], where="plan.time_max")),
        "response_timezone_str": _iana(obj["response_timezone_str"], where="plan.response_timezone_str"),
        "request_digest": _sha(obj["request_digest"], where="plan.request_digest"),
        "human_authority_sha256": _sha(obj["human_authority_sha256"], where="plan.human_authority_sha256"),
    }
    if _aware(core["time_max"], where="plan.time_max") <= _aware(core["time_min"], where="plan.time_min"):
        raise CalendarConsumerError("plan time range invalid")
    expected_plan_sha = sha256_hex(canonical_json_bytes(core))
    if _sha(obj["plan_sha256"], where="plan.plan_sha256") != expected_plan_sha:
        raise CalendarConsumerError("plan digest mismatch")
    return {**core, "plan_sha256": expected_plan_sha}


def capture_google_availability(plan: Any, provider_result: Any, *, captured_at: datetime) -> dict[str, Any]:
    """Wrap one get_availability result without retaining event titles/details."""
    normalized_plan = _normalize_plan(plan)
    if captured_at.tzinfo is None:
        raise CalendarConsumerError("captured_at must be timezone-aware")
    captured_text = _utc_text(captured_at)
    result = _exact(provider_result, {"calendars"}, where="provider_result")
    calendars = result["calendars"]
    if type(calendars) is not list or len(calendars) != 1:
        raise CalendarConsumerError("provider_result must contain exactly one calendar")
    cal = _exact(calendars[0], {"calendar_id", "busy", "errors"}, where="provider_result.calendars[0]")
    if cal["calendar_id"] != CALENDAR_ID:
        raise CalendarConsumerError("provider calendar binding mismatch")
    errors = cal["errors"]
    if errors is not None and type(errors) is not list:
        raise CalendarConsumerError("provider errors must be null or list")
    errors_present = bool(errors)
    busy = _intervals(cal["busy"], where="provider_result.calendars[0].busy", maximum=128, allow_empty=True)
    qmin = _aware(normalized_plan["time_min"], where="plan.time_min")
    qmax = _aware(normalized_plan["time_max"], where="plan.time_max")
    for item in busy:
        start = _aware(item["start"], where="busy.start")
        end = _aware(item["end"], where="busy.end")
        if start < qmin or end > qmax:
            raise CalendarConsumerError("provider busy window exceeds exact query bounds")

    capture_core = {
        "schema": CAPTURE_SCHEMA,
        "capture_id": _opaque_digest_id("gcal", sha256_hex(canonical_json_bytes({
            "plan_sha256": normalized_plan["plan_sha256"],
            "captured_at": captured_text,
            "busy": busy,
            "errors_present": errors_present,
            "provider_result_sha256": sha256_hex(canonical_json_bytes(provider_result)),
        }))),
        "provider_ref": PROVIDER_REF,
        "calendar_id": CALENDAR_ID,
        "captured_at": captured_text,
        "plan": normalized_plan,
        "provider_result_sha256": sha256_hex(canonical_json_bytes(provider_result)),
        "response": {"calendars": [{"calendar_id": CALENDAR_ID, "busy": busy, "errors_present": errors_present}]},
    }
    return {**capture_core, "capture_sha256": sha256_hex(canonical_json_bytes(capture_core))}


def _normalize_capture(capture: Any) -> dict[str, Any]:
    obj = _exact(
        capture,
        {"schema", "capture_id", "provider_ref", "calendar_id", "captured_at", "plan", "provider_result_sha256", "response", "capture_sha256"},
        where="capture",
    )
    if obj["schema"] != CAPTURE_SCHEMA or obj["provider_ref"] != PROVIDER_REF or obj["calendar_id"] != CALENDAR_ID:
        raise CalendarConsumerError("capture provider/schema/calendar mismatch")
    plan = _normalize_plan(obj["plan"])
    response = _exact(obj["response"], {"calendars"}, where="capture.response")
    calendars = response["calendars"]
    if type(calendars) is not list or len(calendars) != 1:
        raise CalendarConsumerError("capture.response must contain exactly one calendar")
    cal = _exact(calendars[0], {"calendar_id", "busy", "errors_present"}, where="capture.response.calendars[0]")
    if cal["calendar_id"] != CALENDAR_ID:
        raise CalendarConsumerError("capture calendar binding mismatch")
    if type(cal["errors_present"]) is not bool:
        raise CalendarConsumerError("capture errors_present must be boolean")
    busy = _intervals(cal["busy"], where="capture.response.calendars[0].busy", maximum=128, allow_empty=True)
    core = {
        "schema": CAPTURE_SCHEMA,
        "capture_id": _safe_id(obj["capture_id"], where="capture.capture_id"),
        "provider_ref": PROVIDER_REF,
        "calendar_id": CALENDAR_ID,
        "captured_at": _utc_text(_aware(obj["captured_at"], where="capture.captured_at")),
        "plan": plan,
        "provider_result_sha256": _sha(obj["provider_result_sha256"], where="capture.provider_result_sha256"),
        "response": {"calendars": [{"calendar_id": CALENDAR_ID, "busy": busy, "errors_present": cal["errors_present"]}]},
    }
    expected = sha256_hex(canonical_json_bytes(core))
    if _sha(obj["capture_sha256"], where="capture.capture_sha256") != expected:
        raise CalendarConsumerError("capture digest mismatch")
    return {**core, "capture_sha256": expected}


def _first_requested_slot(request: dict[str, Any]) -> dict[str, str]:
    duration = timedelta(minutes=request["duration_minutes"])
    first = request["windows"][0]
    start = _aware(first["start"], where="request.windows[0].start")
    end = start + duration
    if end > _aware(first["end"], where="request.windows[0].end"):
        raise CalendarConsumerError("first request window cannot contain duration")
    return {"start": _utc_text(start), "end": _utc_text(end)}


def _earliest_free_slot(request: dict[str, Any], busy: list[dict[str, str]]) -> dict[str, str] | None:
    duration = timedelta(minutes=request["duration_minutes"])
    busy_ranges = [(_aware(x["start"], where="busy.start"), _aware(x["end"], where="busy.end")) for x in busy]
    for window in request["windows"]:
        start = _aware(window["start"], where="window.start")
        end = _aware(window["end"], where="window.end")
        cursor = start
        for bstart, bend in busy_ranges:
            if bend <= cursor or bstart >= end:
                continue
            if bstart > cursor and bstart - cursor >= duration:
                return {"start": _utc_text(cursor), "end": _utc_text(cursor + duration)}
            if bend > cursor:
                cursor = bend
            if cursor + duration > end:
                break
        if cursor + duration <= end:
            return {"start": _utc_text(cursor), "end": _utc_text(cursor + duration)}
    return None


def _overlaps(slot: dict[str, str], busy: list[dict[str, str]]) -> bool:
    s = _aware(slot["start"], where="slot.start")
    e = _aware(slot["end"], where="slot.end")
    for item in busy:
        bs = _aware(item["start"], where="busy.start")
        be = _aware(item["end"], where="busy.end")
        if s < be and bs < e:
            return True
    return False


def compile_calendar_consumer(
    trigger: Any,
    capture: Any,
    *,
    expected_human_authority_sha256: str,
    expected_calendar_capture_sha256: str,
    as_of: datetime,
) -> dict[str, Any]:
    """Compile the live-read observation through the landed readiness core."""
    normalized = _normalize_trigger(trigger)
    human_sha = _require_external_sha(
        _human_authority_sha(normalized), expected_human_authority_sha256,
        where="expected_human_authority_sha256",
    )
    cap = _normalize_capture(capture)
    capture_sha = _require_external_sha(
        cap["capture_sha256"], expected_calendar_capture_sha256,
        where="expected_calendar_capture_sha256",
    )
    if cap["plan"]["human_authority_sha256"] != human_sha:
        raise CalendarConsumerError("capture plan human authority mismatch")

    expected_plan = build_google_availability_plan(
        normalized, expected_human_authority_sha256=human_sha
    )
    if cap["plan"] != expected_plan:
        raise CalendarConsumerError("capture plan does not match exact trigger plan")

    cal = cap["response"]["calendars"][0]
    busy = cal["busy"]
    has_errors = cal["errors_present"]
    if has_errors:
        result = "UNKNOWN"
        slot = _first_requested_slot(normalized["request"])
    else:
        free_slot = _earliest_free_slot(normalized["request"], busy)
        if free_slot is not None:
            result = "FREE"
            slot = free_slot
        else:
            result = "BUSY"
            slot = _first_requested_slot(normalized["request"])
            if not _overlaps(slot, busy):
                # No free duration exists, but this particular fallback is not busy.
                # Move across request windows until finding a deterministic busy overlap.
                candidates: list[dict[str, str]] = []
                duration = timedelta(minutes=normalized["request"]["duration_minutes"])
                for window in normalized["request"]["windows"]:
                    wstart = _aware(window["start"], where="window.start")
                    wend = _aware(window["end"], where="window.end")
                    for item in busy:
                        bstart = max(wstart, _aware(item["start"], where="busy.start"))
                        bend = min(wend, _aware(item["end"], where="busy.end"))
                        start = max(wstart, bstart - duration + timedelta(seconds=1))
                        if start + duration <= wend and start < bend:
                            candidates.append({"start": _utc_text(start), "end": _utc_text(start + duration)})
                if not candidates:
                    raise CalendarConsumerError("calendar has no full free duration but no reproducible busy-overlap slot")
                slot = sorted(candidates, key=lambda x: (x["start"], x["end"]))[0]

    packet = {
        "schema": CORE_SCHEMA,
        "opportunity_id": normalized["opportunity_id"],
        "owner_ref": normalized["owner_ref"],
        "counterparty_ref": normalized["counterparty_ref"],
        "thread_ref": normalized["thread_ref"],
        "inbound": normalized["inbound"],
        "request": normalized["request"],
        "prep": normalized["prep"],
        "availability": {
            "observation_id": cap["capture_id"],
            "provider_ref": "google-calendar:primary",
            "captured_at": cap["captured_at"],
            "opportunity_id": normalized["opportunity_id"],
            "thread_ref": normalized["thread_ref"],
            "timezone": normalized["request"]["timezone"],
            "duration_minutes": normalized["request"]["duration_minutes"],
            "request_digest": cap["plan"]["request_digest"],
            "busy_windows": busy,
            "busy_digest": core_busy_digest(busy),
            "result": result,
            "proposed_slot": slot,
        },
    }
    core_receipt = compile_meeting_readiness(packet, as_of=as_of)
    wrapper_core = {
        "schema": RECEIPT_SCHEMA,
        "state": core_receipt["state"],
        "as_of": core_receipt["as_of"],
        "human_authority_sha256": human_sha,
        "calendar_capture_sha256": capture_sha,
        "calendar_plan_sha256": cap["plan"]["plan_sha256"],
        "core_receipt_sha256": core_receipt["receipt_sha256"],
        "core_receipt": core_receipt,
        "authority": {
            "owner_review_only": True,
            "calendar_freebusy_read_consumed": True,
            "calendar_create": False,
            "calendar_update": False,
            "calendar_delete": False,
            "invite_or_rsvp": False,
            "provider_send_or_reply": False,
            "scheduling_confirmation": False,
            "commercial_commitment": False,
        },
    }
    return {**wrapper_core, "receipt_sha256": sha256_hex(canonical_json_bytes(wrapper_core))}


def render_markdown(receipt: Any) -> str:
    obj = _exact(
        receipt,
        {"schema", "state", "as_of", "human_authority_sha256", "calendar_capture_sha256",
         "calendar_plan_sha256", "core_receipt_sha256", "core_receipt", "authority", "receipt_sha256"},
        where="receipt",
    )
    if obj["schema"] != RECEIPT_SCHEMA:
        raise CalendarConsumerError("unsupported receipt schema")
    core = obj["core_receipt"]
    if core.get("receipt_sha256") != obj["core_receipt_sha256"]:
        raise CalendarConsumerError("core receipt binding mismatch")
    wrapper_core = {k: deepcopy(v) for k, v in obj.items() if k != "receipt_sha256"}
    if sha256_hex(canonical_json_bytes(wrapper_core)) != _sha(obj["receipt_sha256"], where="receipt.receipt_sha256"):
        raise CalendarConsumerError("wrapper receipt digest mismatch")
    prefix = [
        "# Sales meeting calendar consumer",
        "",
        f"**State:** `{obj['state']}`",
        f"**Verified at:** `{obj['as_of']}`",
        f"**Human authority:** `{obj['human_authority_sha256']}`",
        f"**Calendar capture:** `{obj['calendar_capture_sha256']}`",
        "",
        "## Mutation boundary",
        "",
        "- Google Calendar free/busy: read-only evidence consumed.",
        "- Calendar create/update/delete: **not authorized**.",
        "- Invite/RSVP/send/reply/scheduling confirmation: **not authorized**.",
        "- A READY state means owner scheduling review only.",
        "",
    ]
    return "\n".join(prefix) + "\n" + render_core_markdown(core)


def is_ready_for_owner_review(receipt: dict[str, Any]) -> bool:
    return receipt.get("schema") == RECEIPT_SCHEMA and receipt.get("state") == CORE_READY
