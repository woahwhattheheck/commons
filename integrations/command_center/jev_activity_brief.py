"""Deterministic operator brief over the landed Jev activity ledger/action receipts.

The compiler is deliberately transport-free.  It verifies the exact ledger generation,
optionally verifies provider-readback action receipts, and emits one discoverable record plus
a concise Markdown projection.  A connector/controller may publish that projection, but must
reuse the stable operation marker and provider readback rather than spraying duplicate posts.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from integrations.command_center.jev_action_loop import ActionLoopError, verify_receipt
from integrations.command_center.jev_event_ledger import REPORT_SCHEMA as LEDGER_SCHEMA
from integrations.command_center.jev_event_ledger import verify_report

SCHEMA = "commons.jev_activity_brief/v1"
OPERATION_ID = "jev16537-activity-brief-v1"
MAX_RECEIPTS = 256
MAX_ATTENTION = 12
ATTENTION_KINDS = {"ASK", "OWNER_DIRECTION", "HANDOFF", "COLLISION"}
AUTHORITY = {
    "provider_send_authority": False,
    "provider_edit_authority": False,
    "claim_authority": False,
    "merge_authority": False,
    "payment_authority": False,
    "raw_private_text_included": False,
}


class ActivityBriefError(ValueError):
    """Malformed, unverifiable, or contradictory activity-brief input."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ActivityBriefError("not canonical JSON data") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _time(value: Any, where: str) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ActivityBriefError(f"{where}: expected RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ActivityBriefError(f"{where}: invalid timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise ActivityBriefError(f"{where}: timestamp is not UTC")
    return parsed


def _safe_link(value: str) -> str:
    """Render an already-validated source URL without creating Markdown syntax."""
    return value.replace("<", "%3C").replace(">", "%3E")


def _window_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    windows = report.get("windows")
    if type(windows) is not list:
        raise ActivityBriefError("ledger windows missing")
    result = {}
    for row in windows:
        if type(row) is not dict or type(row.get("label")) is not str:
            raise ActivityBriefError("ledger window malformed")
        if row["label"] in result:
            raise ActivityBriefError("duplicate ledger window label")
        result[row["label"]] = row
    required = {"15m", "1h", "24h", "historical"}
    if set(result) != required:
        raise ActivityBriefError("ledger window set mismatch")
    return result


def _receipt_projection(receipts: list[dict[str, Any]], evaluated_at: datetime) -> list[dict[str, Any]]:
    if type(receipts) is not list or len(receipts) > MAX_RECEIPTS:
        raise ActivityBriefError("action receipts: invalid count")
    output = []
    seen = set()
    for raw in receipts:
        try:
            verified = verify_receipt(raw)
        except (ActionLoopError, TypeError, ValueError) as exc:
            raise ActivityBriefError("action receipt failed verification") from exc
        observed = _time(raw.get("observed_at"), "receipt.observed_at")
        if observed > evaluated_at:
            raise ActivityBriefError("action receipt is newer than ledger snapshot")
        digest = verified["receipt_sha256"]
        if digest in seen:
            continue
        seen.add(digest)
        output.append({
            "operation_id": verified["operation_id"],
            "provider": raw["provider"],
            "destination_id": raw["destination_id"],
            "provider_resource_id": raw["provider_resource_id"],
            "outcome": verified["outcome"],
            "confirmed": verified["confirmed"],
            "observed_at": raw["observed_at"],
            "source_url": raw["source_url"],
            "receipt_sha256": digest,
        })
    return sorted(output, key=lambda row: (row["observed_at"], row["operation_id"], row["receipt_sha256"]))


def _attention(report: dict[str, Any], evaluated_at: datetime) -> list[dict[str, Any]]:
    events = report.get("events")
    if type(events) is not list:
        raise ActivityBriefError("ledger events missing")
    rows = []
    for event in events:
        if type(event) is not dict:
            raise ActivityBriefError("ledger event malformed")
        if event.get("kind") not in ATTENTION_KINDS:
            continue
        event_time = _time(event.get("provider_event_time"), "event.provider_event_time")
        age_seconds = max(0, int((evaluated_at - event_time).total_seconds()))
        urls = event.get("source_urls")
        if type(urls) is not list or not urls:
            raise ActivityBriefError("attention event lacks source links")
        rows.append({
            "event_id": event.get("event_id"),
            "kind": event.get("kind"),
            "provider": event.get("provider"),
            "work_id": event.get("work_id"),
            "actor_id": event.get("actor_id"),
            "provider_event_time": event.get("provider_event_time"),
            "age_seconds": age_seconds,
            "source_urls": sorted(set(urls)),
        })
    rows.sort(key=lambda row: (row["provider_event_time"], str(row["event_id"])), reverse=True)
    return rows[:MAX_ATTENTION]


def _render_markdown(record: dict[str, Any]) -> str:
    source = record["source"]
    freshness = record["freshness"]
    windows = {row["label"]: row for row in record["windows"]}
    action = record["actions"]
    lines = [
        "# Jev swarm activity brief",
        "",
        f"Snapshot `{source['snapshot_id']}` · observed `{source['evaluated_at']}` · ledger `{source['ledger_receipt_sha256'][:12]}…`.",
        "",
        "## Coverage and volume",
        "",
        (
            f"Sources: **{freshness['source_count']}** · fresh **{freshness['fresh']}** · "
            f"degraded/stale **{freshness['degraded']}** · partial/paginated **{freshness['partial']}**."
        ),
    ]
    for label in ("15m", "1h", "24h", "historical"):
        row = windows[label]
        stage = row["by_stage"]
        qualifier = "exact" if row["coverage_state"] == "COMPLETE" else "lower-bound"
        lines.append(
            f"- **{label}**: {row['event_count']} events ({qualifier}); "
            f"claims {stage.get('CLAIM', 0)}, sessions {stage.get('CONFIRMED_SESSION', 0)}, "
            f"accepted {stage.get('PROVIDER_ACCEPTED', 0)}, landed {stage.get('LANDED', 0)}, "
            f"business outcomes {stage.get('BUSINESS_OUTCOME', 0)}."
        )
    if freshness["degraded_source_ids"]:
        lines.extend([
            "",
            "Degraded source IDs: " + ", ".join(f"`{item}`" for item in freshness["degraded_source_ids"]),
        ])

    lines.extend(["", "## Attention candidates", ""])
    if not record["attention_candidates"]:
        lines.append("No ASK / OWNER_DIRECTION / HANDOFF / COLLISION events are present in this bounded ledger snapshot.")
    else:
        for row in record["attention_candidates"]:
            work = f" · work `{row['work_id']}`" if row["work_id"] else ""
            link = _safe_link(row["source_urls"][0])
            lines.append(
                f"- **{row['kind']}** · `{row['provider']}` · age {row['age_seconds']}s{work} · <{link}>"
            )
    lines.extend(["", "These are event-kind candidates, not assertions that an obligation remains unanswered or that an actor is currently active."])

    lines.extend(["", "## Action receipts", ""])
    lines.append(
        f"Supplied verified receipts: **{action['receipt_count']}** · confirmed **{action['confirmed']}** · "
        f"delivery-uncertain **{action['delivery_uncertain']}** · rejected **{action['rejected']}**."
    )
    for row in record["action_receipts"][-8:]:
        link = _safe_link(row["source_url"])
        lines.append(f"- `{row['operation_id']}` · **{row['outcome']}** · <{link}>")

    lines.extend([
        "",
        "## Continuation contract",
        "",
        f"Stable update operation: `{record['operation_id']}`. A publishing controller should edit/read back the existing provider resource for this operation, or create it once when no prior resource exists. This compiler has no send/edit/claim/merge/payment authority.",
        "",
        f"<!-- jev-activity-operation:{record['operation_id']} generation:{record['generation_sha256']} -->",
    ])
    return "\n".join(lines) + "\n"


def compile_brief(ledger_report: dict[str, Any], action_receipts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Verify a ledger generation and compile one deterministic operator/shared record."""
    if type(ledger_report) is not dict or ledger_report.get("schema") != LEDGER_SCHEMA:
        raise ActivityBriefError("unsupported ledger report schema")
    if not verify_report(ledger_report):
        raise ActivityBriefError("ledger report failed integrity verification")
    evaluated_at = _time(ledger_report.get("evaluated_at"), "ledger.evaluated_at")
    windows = _window_map(ledger_report)
    receipts = _receipt_projection(action_receipts or [], evaluated_at)

    source_summary = ledger_report.get("source_summary")
    if type(source_summary) is not dict:
        raise ActivityBriefError("ledger source summary missing")
    freshness_counts = source_summary.get("freshness_counts")
    if type(freshness_counts) is not dict:
        raise ActivityBriefError("ledger freshness counts missing")
    degraded_ids = source_summary.get("stale_or_degraded_sources")
    partial_ids = source_summary.get("partial_or_paginated_sources")
    if type(degraded_ids) is not list or type(partial_ids) is not list:
        raise ActivityBriefError("ledger source degradation lists missing")

    projected_windows = []
    for label in ("15m", "1h", "24h", "historical"):
        row = windows[label]
        coverage = row.get("coverage")
        if type(coverage) is not dict or coverage.get("state") not in {"COMPLETE", "LOWER_BOUND"}:
            raise ActivityBriefError("ledger window coverage malformed")
        projected_windows.append({
            "label": label,
            "start": row.get("start"),
            "end": row.get("end"),
            "event_count": row.get("event_count"),
            "distinct_observed_contributors": row.get("distinct_observed_contributors"),
            "distinct_work_items": row.get("distinct_work_items"),
            "by_stage": row.get("by_stage"),
            "by_provider": row.get("by_provider"),
            "by_kind": row.get("by_kind"),
            "coverage_state": coverage.get("state"),
            "incomplete_or_stale_sources": coverage.get("incomplete_or_stale_sources"),
            "source_window_receipt_sha256": row.get("window_receipt_sha256"),
        })

    outcome_counts = Counter(row["outcome"] for row in receipts)
    record = {
        "schema": SCHEMA,
        "operation_id": OPERATION_ID,
        "source": {
            "ledger_schema": ledger_report["schema"],
            "snapshot_id": ledger_report.get("snapshot_id"),
            "evaluated_at": ledger_report["evaluated_at"],
            "clock_source": ledger_report.get("clock_source"),
            "ledger_receipt_sha256": ledger_report.get("ledger_receipt_sha256"),
        },
        "freshness": {
            "source_count": source_summary.get("source_count"),
            "fresh": freshness_counts.get("FRESH", 0),
            "degraded": sum(value for key, value in freshness_counts.items() if key != "FRESH"),
            "partial": len(partial_ids),
            "degraded_source_ids": sorted(set(degraded_ids)),
            "partial_or_paginated_source_ids": sorted(set(partial_ids)),
        },
        "windows": projected_windows,
        "attention_candidates": _attention(ledger_report, evaluated_at),
        "actions": {
            "receipt_count": len(receipts),
            "confirmed": sum(1 for row in receipts if row["confirmed"]),
            "delivery_uncertain": outcome_counts.get("DELIVERY_UNCERTAIN", 0),
            "rejected": outcome_counts.get("REJECTED", 0),
        },
        "action_receipts": receipts,
        "publication": {
            "mode": "EDIT_EXISTING_OR_CREATE_ONCE",
            "operation_marker": OPERATION_ID,
            "requires_provider_readback": True,
        },
        "authority": dict(AUTHORITY),
    }
    generation_material = dict(record)
    record["generation_sha256"] = _digest(generation_material)
    record["markdown"] = _render_markdown(record)
    record["record_sha256"] = _digest({key: value for key, value in record.items() if key != "record_sha256"})
    return record


def verify_brief(record: dict[str, Any]) -> bool:
    """Verify a compiled brief has not drifted after compilation."""
    try:
        if type(record) is not dict or record.get("schema") != SCHEMA:
            return False
        if record.get("operation_id") != OPERATION_ID or record.get("authority") != AUTHORITY:
            return False
        expected_record = record.get("record_sha256")
        if type(expected_record) is not str or len(expected_record) != 64:
            return False
        body = {key: value for key, value in record.items() if key != "record_sha256"}
        if _digest(body) != expected_record:
            return False
        generation_body = {
            key: value for key, value in record.items()
            if key not in {"generation_sha256", "markdown", "record_sha256"}
        }
        expected_generation = record.get("generation_sha256")
        if type(expected_generation) is not str or _digest(generation_body) != expected_generation:
            return False
        if record.get("markdown") != _render_markdown(record):
            return False
        publication = record.get("publication")
        return publication == {
            "mode": "EDIT_EXISTING_OR_CREATE_ONCE",
            "operation_marker": OPERATION_ID,
            "requires_provider_readback": True,
        }
    except (ActivityBriefError, TypeError, ValueError, KeyError):
        return False


__all__ = ["ActivityBriefError", "OPERATION_ID", "SCHEMA", "compile_brief", "verify_brief"]
