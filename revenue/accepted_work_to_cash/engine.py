from __future__ import annotations

from typing import Any

from .core import (
    ACCEPTANCE_KINDS,
    AUTHORITY,
    BUNDLE_SCHEMA,
    LANES,
    MAX_EVENTS_PER_ITEM,
    MAX_ITEMS,
    SCHEMA,
    ReconcileError,
    canonical_bytes,
    digest,
    exact_dict,
    money,
    parse_time,
    positive_int,
    text,
    validate_event,
)
from .policy import same_second_amount_conflict, target_amount, terminal_action


def compile_portfolio(raw: Any) -> dict[str, Any]:
    doc = exact_dict(raw, {"schema", "evaluation_at", "freshness_seconds", "items"}, "document")
    if doc["schema"] != SCHEMA:
        raise ReconcileError("document.schema: unsupported")
    evaluation_at = parse_time(doc["evaluation_at"], "evaluation_at")
    freshness_seconds = positive_int(doc["freshness_seconds"], "freshness_seconds", 30 * 24 * 3600)
    if type(doc["items"]) is not list or len(doc["items"]) > MAX_ITEMS:
        raise ReconcileError("items: bounded array required")

    outputs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_bindings: set[tuple[str, str, str]] = set()

    for raw_item in doc["items"]:
        keys = {"id", "title", "payer", "program", "lane", "currency", "advertised_amount_cents", "events"}
        item = exact_dict(raw_item, keys, "item")
        item_id = text(item["id"], "item.id", 120)
        if item_id in seen_ids:
            raise ReconcileError(f"duplicate item id: {item_id}")
        seen_ids.add(item_id)
        title = text(item["title"], f"{item_id}.title", 240)
        payer = text(item["payer"], f"{item_id}.payer", 240)
        program = text(item["program"], f"{item_id}.program", 240)
        lane = text(item["lane"], f"{item_id}.lane", 40)
        if lane not in LANES:
            raise ReconcileError(f"{item_id}.lane: unsupported")
        currency = text(item["currency"], f"{item_id}.currency", 8)
        if not (3 <= len(currency) <= 8 and currency.upper() == currency and currency.isalpha()):
            raise ReconcileError(f"{item_id}.currency: uppercase alphabetic currency/unit required")
        advertised = money(item["advertised_amount_cents"], f"{item_id}.advertised_amount_cents", optional=True)
        if type(item["events"]) is not list or len(item["events"]) > MAX_EVENTS_PER_ITEM:
            raise ReconcileError(f"{item_id}.events: bounded array required")

        events = [validate_event(event, item_id, evaluation_at) for event in item["events"]]
        event_ids = [event["id"] for event in events]
        if len(event_ids) != len(set(event_ids)):
            raise ReconcileError(f"{item_id}: duplicate event id")
        local_bindings: set[tuple[str, str, str]] = set()
        for event in events:
            binding = (event["source_class"], event["ref"], event["sha256"])
            if binding in local_bindings:
                raise ReconcileError(f"{item_id}: duplicate retained evidence binding")
            local_bindings.add(binding)
            if binding in seen_bindings:
                raise ReconcileError(f"{item_id}: retained evidence binding reused across work items")
            seen_bindings.add(binding)
        events.sort(key=lambda event: (event["observed_at"], event["id"]))

        conflict = same_second_amount_conflict(events)
        delivered = any(event["kind"] == "DELIVERED" for event in events)
        accepted = any(event["kind"] in ACCEPTANCE_KINDS for event in events)
        paid_total = sum(int(event["amount_cents"]) for event in events if event["kind"] == "PAYMENT_RECEIVED")
        target, target_source = target_amount(events, advertised)
        if conflict:
            action, score, reasons, contact = "HOLD_CONTRADICTION", 0, [conflict], None
        else:
            action, score, reasons, contact = terminal_action(
                events=events,
                evaluation_at=evaluation_at,
                freshness_seconds=freshness_seconds,
                accepted=accepted,
                delivered=delivered,
                paid_total=paid_total,
                target=target,
            )

        economically_unfinished = action not in {"DONE_PAID", "CLOSED_NO_CASH", "HOLD_NO_ACCEPTED_WORK"}
        outstanding = None if target is None else max(target - paid_total, 0)
        outputs.append({
            "id": item_id,
            "title": title,
            "payer": payer,
            "program": program,
            "lane": lane,
            "currency": currency,
            "advertised_amount_cents": advertised,
            "settlement_target_cents": target,
            "settlement_target_source": target_source,
            "payment_received_cents": paid_total,
            "outstanding_cents": outstanding,
            "accepted_evidence_present": accepted,
            "delivered_evidence_present": delivered,
            "economically_unfinished": economically_unfinished,
            "terminal_action": action,
            "realizability_score": score,
            "reasons": reasons,
            "contact_packet": contact,
            "event_count": len(events),
            "evidence_digest": digest(events),
        })

    ranked = sorted(
        outputs,
        key=lambda row: (
            -row["realizability_score"],
            -(row["outstanding_cents"] if row["outstanding_cents"] is not None else -1),
            row["id"],
        ),
    )
    totals: dict[str, dict[str, int]] = {}
    for row in outputs:
        cur = row["currency"]
        acc = totals.setdefault(cur, {"provider_backed_cash_cents": 0, "known_outstanding_cents": 0, "known_outstanding_items": 0})
        acc["provider_backed_cash_cents"] += row["payment_received_cents"]
        if row["outstanding_cents"] is not None and row["economically_unfinished"]:
            acc["known_outstanding_cents"] += row["outstanding_cents"]
            acc["known_outstanding_items"] += 1

    return {
        "schema": SCHEMA,
        "evaluation_at": evaluation_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "truth_boundary": "RETAINED_EVIDENCE_PROJECTION_NOT_CURRENT_PROVIDER_AUTHORITY",
        "authority": dict(AUTHORITY),
        "item_count": len(outputs),
        "items": sorted(outputs, key=lambda row: row["id"]),
        "ranked_terminal_actions": [
            {
                "rank": index + 1,
                "id": row["id"],
                "terminal_action": row["terminal_action"],
                "realizability_score": row["realizability_score"],
                "currency": row["currency"],
                "outstanding_cents": row["outstanding_cents"],
                "contact_packet": row["contact_packet"],
            }
            for index, row in enumerate(ranked)
        ],
        "cash_and_outstanding_by_currency": {key: totals[key] for key in sorted(totals)},
    }


def compile_bundle(raw: Any) -> dict[str, Any]:
    source_digest = digest(raw)
    portfolio = compile_portfolio(raw)
    core = {
        "bundle_schema": BUNDLE_SCHEMA,
        "source": raw,
        "source_sha256": source_digest,
        "portfolio": portfolio,
    }
    return {**core, "receipt_sha256": digest(core)}


def verify_bundle(bundle: Any) -> bool:
    expected_keys = {"bundle_schema", "source", "source_sha256", "portfolio", "receipt_sha256"}
    obj = exact_dict(bundle, expected_keys, "bundle")
    if obj["bundle_schema"] != BUNDLE_SCHEMA:
        raise ReconcileError("bundle_schema: unsupported")
    if obj["source_sha256"] != digest(obj["source"]):
        raise ReconcileError("source digest mismatch")
    rebuilt = compile_bundle(obj["source"])
    if canonical_bytes(rebuilt) != canonical_bytes(obj):
        raise ReconcileError("semantic bundle mismatch")
    return True
