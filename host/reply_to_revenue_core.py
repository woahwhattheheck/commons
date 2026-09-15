#!/usr/bin/env python3
"""Single-generation reply-to-revenue core with retained authority.

The retained implementation is stored as non-importable source beside this
module. This surface loads it, then installs an observation loader and contact
policy whose complete semantic dependency graphs are closure-captured. Direct
imports, the wrapper, and both CLI paths therefore share one production graph;
post-import rebinding of helper globals cannot silently rewrite evidence
identity, classification, chronology, DNC, or positive-surface semantics.
"""

from __future__ import annotations

import types
from pathlib import Path
from typing import Any


_IMPL_PATH = Path(__file__).with_name("reply_to_revenue_core_impl.source")
_impl = types.ModuleType("_commons_reply_to_revenue_core_impl")
_impl.__file__ = str(_IMPL_PATH)
_impl.__package__ = None
exec(
    compile(_IMPL_PATH.read_text(encoding="utf-8"), str(_IMPL_PATH), "exec"),
    _impl.__dict__,
)

for _name, _value in vars(_impl).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

PUBLIC_LIMITS = [
    (
        "ingest each inbound event_ref once; collision on same ref with a "
        "different full observation envelope"
        if item.startswith("ingest each inbound event_ref once;")
        else item
    )
    for item in _impl.PUBLIC_LIMITS
]
_impl.PUBLIC_LIMITS = PUBLIC_LIMITS


def _make_time_parser(*, fromisoformat: Any, utc: Any, reply_error: type[Exception]) -> Any:
    _fromisoformat = fromisoformat
    _utc = utc
    _reply_error = reply_error
    _parse_errors = (TypeError, ValueError)

    def frozen_parse_time(value: str) -> Any:
        text_value = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = _fromisoformat(text_value)
        except _parse_errors as error:
            raise _reply_error(f"invalid date-time: {value}") from error
        if parsed.tzinfo is None:
            raise _reply_error("date-time must include a timezone")
        return parsed.astimezone(_utc)

    return frozen_parse_time


_frozen_parse_time = _make_time_parser(
    fromisoformat=_impl.dt.datetime.fromisoformat,
    utc=_impl.dt.timezone.utc,
    reply_error=ReplyRevenueError,
)


def _make_observation_loader(
    *,
    parse_received_at: Any,
    json_loads: Any,
    json_dumps: Any,
    json_decode_error: type[Exception],
    sha256_callable: Any,
    opaque_fullmatch: Any,
    prospect_fullmatch: Any,
    sha_fullmatch: Any,
    classifications: frozenset[str],
    failure_markers: tuple[str, ...],
    auto_markers: tuple[str, ...],
    positive_markers: tuple[str, ...],
    class_to_next: dict[str, str],
    reply_error: type[Exception],
    collision_error: type[Exception],
) -> Any:
    """Build an observation loader with no policy lookup through module globals."""
    _parse = parse_received_at
    _json_loads = json_loads
    _json_dumps = json_dumps
    _sha256 = sha256_callable
    _opaque_fullmatch = opaque_fullmatch
    _prospect_fullmatch = prospect_fullmatch
    _sha_fullmatch = sha_fullmatch
    _classes = frozenset(classifications)
    _failure_markers = tuple(failure_markers)
    _auto_markers = tuple(auto_markers)
    _positive_markers = tuple(positive_markers)
    _next = dict(class_to_next)
    _reply_error = reply_error
    _collision_error = collision_error
    _read_errors = (OSError, json_decode_error)
    _isinstance = isinstance
    _type = type
    _int = int
    _str = str
    _list = list
    _dict = dict
    _set = set
    _sorted = sorted
    _all = all
    _len = len

    def exact_keys(value: dict[str, Any], expected: set[str], where: str) -> None:
        actual = _set(value)
        if actual != expected:
            raise _reply_error(
                f"{where} fields differ: missing={_sorted(expected - actual)} "
                f"extra={_sorted(actual - expected)}"
            )

    def read_one(path: Any) -> dict[str, Any]:
        try:
            value = _json_loads(path.read_text(encoding="utf-8"))
        except _read_errors as error:
            raise _reply_error(f"cannot read JSON object {path}: {error}") from error
        if not _isinstance(value, _dict):
            raise _reply_error(f"{path} must contain one JSON object")
        return value

    def envelope_identity(event: dict[str, Any]) -> str:
        canonical = _json_dumps(
            event,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        ) + "\n"
        return _sha256(canonical.encode("utf-8")).hexdigest()

    def classify(markers: list[str], requested: str | None = None) -> dict[str, Any]:
        if not _isinstance(markers, _list) or not _all(
            _isinstance(item, _str) and item.strip() for item in markers
        ):
            raise _reply_error("markers must be nonempty strings")
        blob = " ".join(item.casefold() for item in markers)
        matched_failure = [marker for marker in _failure_markers if marker in blob]
        if matched_failure:
            reason = (
                "delivery-failure markers override a human-response claim"
                if requested in {"POSITIVE_SCOPE", "QUESTION", "NEEDS_HUMAN"}
                else "delivery failed; owner must review an alternate route before any new contact"
            )
            return {
                "classification": "DELIVERY_FAILURE",
                "next_action": _next["DELIVERY_FAILURE"],
                "buyer_interest": False,
                "auto_ack": False,
                "delivery_failure": True,
                "matched_markers": matched_failure,
                "reason": reason,
            }
        matched_auto = [marker for marker in _auto_markers if marker in blob]
        if matched_auto:
            reason = (
                "auto-ack markers override a positivity or question claim"
                if requested in {"POSITIVE_SCOPE", "QUESTION"}
                else "automated acknowledgement is not buyer interest"
            )
            return {
                "classification": "AUTO_RESPONSE",
                "next_action": _next["AUTO_RESPONSE"],
                "buyer_interest": False,
                "auto_ack": True,
                "delivery_failure": False,
                "matched_markers": matched_auto,
                "reason": reason,
            }
        if requested is not None:
            if requested not in _classes:
                raise _reply_error(f"unknown classification: {requested}")
            return {
                "classification": requested,
                "next_action": _next[requested],
                "buyer_interest": requested == "POSITIVE_SCOPE",
                "auto_ack": False,
                "delivery_failure": False,
                "matched_markers": [],
                "reason": "operator classification with no delivery-failure or auto-ack markers",
            }
        matched_positive = [marker for marker in _positive_markers if marker in blob]
        if matched_positive:
            return {
                "classification": "POSITIVE_SCOPE",
                "next_action": _next["POSITIVE_SCOPE"],
                "buyer_interest": True,
                "auto_ack": False,
                "delivery_failure": False,
                "matched_markers": matched_positive,
                "reason": "explicit buyer-scope language with no delivery-failure or auto-ack markers",
            }
        return {
            "classification": "NEEDS_HUMAN",
            "next_action": _next["NEEDS_HUMAN"],
            "buyer_interest": False,
            "auto_ack": False,
            "delivery_failure": False,
            "matched_markers": [],
            "reason": "no delivery-failure, auto-ack, or explicit buyer-scope language",
        }

    def assert_window(measured_at_value: Any, events: list[Any]) -> None:
        if not _isinstance(measured_at_value, _str):
            raise _reply_error("observations.measured_at must be a date-time string")
        measured_at = _parse(measured_at_value)
        for index, event in enumerate(events):
            where = f"events[{index}]"
            if not _isinstance(event, _dict):
                raise _reply_error(f"{where} must be an object")
            received_at_value = event.get("received_at")
            if not _isinstance(received_at_value, _str):
                raise _reply_error(f"{where}.received_at must be a date-time string")
            if _parse(received_at_value) > measured_at:
                raise _reply_error(f"{where}.received_at exceeds observations.measured_at")

    def frozen_load_observations(path: Any = OBSERVATIONS_PATH) -> dict[str, Any]:
        value = read_one(path)
        exact_keys(
            value,
            {"schema_version", "kind", "measured_at", "monitor", "events"},
            "observations",
        )
        if value["schema_version"] != "commons-reply-to-revenue-observations/v1":
            raise _reply_error("unsupported observations version")
        if value["kind"] != "REPLY_TO_REVENUE_OBSERVATIONS":
            raise _reply_error("unsupported observations kind")
        _parse(value["measured_at"])
        monitor = value["monitor"]
        if not _isinstance(monitor, _dict):
            raise _reply_error("monitor must be an object")
        exact_keys(
            monitor,
            {"connector", "status", "mailbox_claim", "sends", "queries", "attributed_inbound"},
            "monitor",
        )
        if _type(monitor["sends"]) is not _int or monitor["sends"] != 0:
            raise _reply_error("monitor.sends must be 0")
        if _type(monitor["queries"]) is not _int or monitor["queries"] < 0:
            raise _reply_error("monitor.queries must be a non-negative integer")
        if _type(monitor["attributed_inbound"]) is not _int or monitor["attributed_inbound"] < 0:
            raise _reply_error("monitor.attributed_inbound must be a non-negative integer")
        events = value["events"]
        if not _isinstance(events, _list):
            raise _reply_error("events must be an array")

        seen_refs: dict[str, str] = {}
        seen_hashes: dict[str, str] = {}
        cleaned: list[dict[str, Any]] = []
        fields = {
            "event_ref",
            "received_at",
            "prospect_key",
            "payload_sha256",
            "markers",
            "provider",
            "matched_receipt_id",
            "requested_classification",
        }
        for index, event in enumerate(events):
            where = f"events[{index}]"
            if not _isinstance(event, _dict):
                raise _reply_error(f"{where} must be an object")
            exact_keys(event, fields, where)
            if _opaque_fullmatch(event["event_ref"]) is None:
                raise _reply_error(f"{where}.event_ref is invalid")
            _parse(event["received_at"])
            if _prospect_fullmatch(event["prospect_key"]) is None:
                raise _reply_error(f"{where}.prospect_key is invalid")
            if _sha_fullmatch(event["payload_sha256"]) is None:
                raise _reply_error(f"{where}.payload_sha256 is invalid")
            if not _isinstance(event["markers"], _list):
                raise _reply_error(f"{where}.markers must be an array")
            requested = event["requested_classification"]
            if requested is not None and requested not in _classes:
                raise _reply_error(f"{where}.requested_classification is invalid")

            identity = envelope_identity(event)
            previous = seen_refs.get(event["event_ref"])
            if previous is not None and previous != identity:
                raise _collision_error(
                    f"duplicate event_ref with different observation envelope: {event['event_ref']}"
                )
            hashed = seen_hashes.get(event["payload_sha256"])
            if hashed and hashed != event["event_ref"]:
                raise _collision_error("duplicate payload_sha256 under a second event_ref")
            if previous is not None:
                continue
            seen_refs[event["event_ref"]] = identity
            seen_hashes[event["payload_sha256"]] = event["event_ref"]
            verdict = classify(event["markers"], requested)
            cleaned.append(
                {
                    "event_ref": event["event_ref"],
                    "received_at": event["received_at"],
                    "prospect_key": event["prospect_key"],
                    "payload_sha256": event["payload_sha256"],
                    "provider": event["provider"],
                    "matched_receipt_id": event["matched_receipt_id"],
                    **verdict,
                }
            )

        if monitor["attributed_inbound"] != _len(cleaned):
            raise _reply_error("monitor.attributed_inbound does not match ingested unique events")
        value = _dict(value)
        value["events"] = cleaned
        assert_window(value["measured_at"], cleaned)
        return value

    return frozen_load_observations


load_observations = _make_observation_loader(
    parse_received_at=_frozen_parse_time,
    json_loads=_impl.json.loads,
    json_dumps=_impl.json.dumps,
    json_decode_error=_impl.json.JSONDecodeError,
    sha256_callable=_impl.hashlib.sha256,
    opaque_fullmatch=_impl.OPAQUE_RE.fullmatch,
    prospect_fullmatch=_impl.PROSPECT_RE.fullmatch,
    sha_fullmatch=_impl.SHA256_RE.fullmatch,
    classifications=frozenset(_impl.CLASSIFICATIONS),
    failure_markers=tuple(_impl.DELIVERY_FAILURE_MARKERS),
    auto_markers=tuple(_impl.AUTO_ACK_MARKERS),
    positive_markers=tuple(_impl.POSITIVE_MARKERS),
    class_to_next=dict(_impl.CLASS_TO_NEXT),
    reply_error=ReplyRevenueError,
    collision_error=CollisionError,
)


_MACHINE_CLASSIFICATIONS = frozenset({"DELIVERY_FAILURE", "AUTO_RESPONSE"})


def _make_policy_bundle(
    *,
    parse_received_at: Any,
    human_state_classifications: frozenset[str],
    machine_classifications: frozenset[str],
    reply_error: type[Exception],
    acceptance_tool: str,
    reply_intake_tool: str,
    route_recovery_tool: str,
) -> tuple[Any, Any, Any, Any]:
    """Build the complete contact policy without inherited mutable dependencies."""
    _parse = parse_received_at
    _human_classes = frozenset(human_state_classifications)
    _machine_classes = frozenset(machine_classifications)
    _known_classes = _human_classes | _machine_classes
    _reply_error = reply_error
    _acceptance_tool = acceptance_tool
    _reply_intake_tool = reply_intake_tool
    _route_recovery_tool = route_recovery_tool
    _max = max
    _min = min
    _sorted = sorted
    _str = str

    def latest_event(events: list[dict[str, Any]]) -> dict[str, Any]:
        if not events:
            raise _reply_error("cannot select the latest event from an empty set")
        return _max(
            events,
            key=lambda item: (
                _parse(_str(item["received_at"])),
                _str(item.get("event_ref") or ""),
            ),
        )

    def latest_human_bucket(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        semantic = [event for event in events if event.get("classification") in _human_classes]
        if not semantic:
            return []
        stamped = [(_parse(_str(event["received_at"])), event) for event in semantic]
        latest_time = _max(stamp for stamp, _ in stamped)
        return [event for stamp, event in stamped if stamp == latest_time]

    def reduce_contact_state(events: list[dict[str, Any]]) -> dict[str, Any]:
        if not events:
            return {
                "classification": None,
                "lane": "NO_RESPONSE",
                "next_action": "MONITOR_NO_RESEND",
                "handoff": None,
                "effective_event": None,
            }

        unknown = _sorted(
            {
                _str(event.get("classification"))
                for event in events
                if event.get("classification") not in _known_classes
            }
        )
        if unknown:
            raise _reply_error(f"contact state contains unknown classifications: {unknown}")

        semantic = [event for event in events if event["classification"] in _human_classes]
        effective_event: dict[str, Any] | None
        if semantic:
            latest_semantic = latest_human_bucket(events)
            opt_outs = [
                event for event in latest_semantic if event.get("classification") == "OPT_OUT"
            ]
            if opt_outs:
                classification = "OPT_OUT"
                effective_event = _min(
                    opt_outs,
                    key=lambda item: _str(item.get("event_ref") or ""),
                )
            else:
                latest_classes = {event["classification"] for event in latest_semantic}
                if len(latest_classes) != 1:
                    classification = "NEEDS_HUMAN"
                    effective_event = None
                else:
                    classification = next(iter(latest_classes))
                    effective_event = _min(
                        latest_semantic,
                        key=lambda item: _str(item.get("event_ref") or ""),
                    )
        else:
            failures = [
                event for event in events if event["classification"] == "DELIVERY_FAILURE"
            ]
            if failures:
                classification = "DELIVERY_FAILURE"
                effective_event = latest_event(failures)
            else:
                auto = [event for event in events if event["classification"] == "AUTO_RESPONSE"]
                classification = "AUTO_RESPONSE"
                effective_event = latest_event(auto)

        if classification == "POSITIVE_SCOPE":
            lane, next_action, handoff = "HUMAN_POSITIVE", "NEEDS_ACCEPTANCE", _acceptance_tool
        elif classification == "QUESTION":
            lane, next_action, handoff = "HUMAN_QUESTION", "DRAFT_REPLY", _reply_intake_tool
        elif classification == "OPT_OUT":
            lane, next_action, handoff = "CLOSED", "DNC/CLOSE", None
        elif classification == "NEGATIVE":
            lane, next_action, handoff = "CLOSED", "CLOSE", None
        elif classification == "DELIVERY_FAILURE":
            lane, next_action, handoff = (
                "DELIVERY_FAILURE",
                "RECOVER_ROUTE_OWNER_REVIEW",
                _route_recovery_tool,
            )
        elif classification == "AUTO_RESPONSE":
            lane, next_action, handoff = "AUTO_ACK_WAIT", "WAIT_FOR_HUMAN_REPLY", None
        else:
            lane, next_action, handoff = (
                "NEEDS_HUMAN",
                "ESCALATE_ONLY_IF_BUYER_REQUESTS_BRYCE",
                None,
            )
        return {
            "classification": classification,
            "lane": lane,
            "next_action": next_action,
            "handoff": handoff,
            "effective_event": effective_event,
        }

    def positive_context(events: list[dict[str, Any]]) -> str:
        machine_classes = _sorted(
            {
                _str(event.get("classification"))
                for event in events
                if event.get("classification") in _machine_classes
            }
        )
        if not machine_classes:
            return (
                "effective human inbound classified POSITIVE_SCOPE; "
                "no machine delivery-failure or auto-response observations were recorded"
            )
        recorded = ", ".join(machine_classes)
        return (
            "effective human inbound classified POSITIVE_SCOPE; "
            f"recorded machine observations ({recorded}) do not override human semantics"
        )

    def positive_surface(
        contacts: list[dict[str, Any]],
        inbound: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        positives: list[dict[str, Any]] = []
        inbound_by_key: dict[str, list[dict[str, Any]]] = {}
        for event in inbound:
            inbound_by_key.setdefault(event["prospect_key"], []).append(event)
        for contact in contacts:
            if contact["lane"] != "HUMAN_POSITIVE":
                continue
            events = inbound_by_key.get(contact["prospect_key"], [])
            state = reduce_contact_state(events)
            effective_event = state["effective_event"]
            if state["lane"] != "HUMAN_POSITIVE" or effective_event is None:
                raise _reply_error(
                    f"positive contact {contact['prospect_key']} lacks an effective POSITIVE_SCOPE event"
                )
            if effective_event.get("classification") != "POSITIVE_SCOPE":
                raise _reply_error(
                    f"positive contact {contact['prospect_key']} resolved to non-positive evidence"
                )
            positives.append(
                {
                    "prospect_key": contact["prospect_key"],
                    "organization": contact["organization"],
                    "event_ref": effective_event["event_ref"],
                    "received_at": effective_event["received_at"],
                    "next_action": "NEEDS_ACCEPTANCE",
                    "handoff": _acceptance_tool,
                    "context": positive_context(events),
                    "buyer_interest": True,
                }
            )
        positives.sort(key=lambda item: item["prospect_key"])
        return positives

    return latest_human_bucket, reduce_contact_state, positive_context, positive_surface


(
    _latest_human_bucket,
    _reduce_contact_state,
    _positive_context,
    surface_positives,
) = _make_policy_bundle(
    parse_received_at=_frozen_parse_time,
    human_state_classifications=frozenset(_impl.HUMAN_STATE_CLASSIFICATIONS),
    machine_classifications=_MACHINE_CLASSIFICATIONS,
    reply_error=ReplyRevenueError,
    acceptance_tool=str(_impl.ACCEPTANCE_TOOL),
    reply_intake_tool=str(_impl.REPLY_INTAKE_TOOL),
    route_recovery_tool=str(_impl.ROUTE_RECOVERY_TOOL),
)

# Retained implementation functions such as _contact_rows/build_funnel/main resolve
# these names in `_impl.__dict__`; install the frozen authorities before callers
# execute. The functions themselves no longer delegate semantic work back into
# mutable retained/public helper graphs.
_impl.load_observations = load_observations
_impl._reduce_contact_state = _reduce_contact_state
_impl.surface_positives = surface_positives

if _impl.load_observations is not load_observations:
    raise ImportError("reply-to-revenue observation authority was not installed")
if _impl._reduce_contact_state is not _reduce_contact_state:
    raise ImportError("reply-to-revenue reducer authority was not installed")
if _impl.surface_positives is not surface_positives:
    raise ImportError("reply-to-revenue positive-surface authority was not installed")


if __name__ == "__main__":
    raise SystemExit(_impl.main())
