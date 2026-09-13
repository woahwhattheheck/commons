"""Deterministic reconciliation and receipt evaluation."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .schema import (
    AssessmentResult,
    RECEIPT_SCHEMA,
    _HEX64_RE,
    _digest,
    _failure,
    _normalize_bundle,
)

def evaluate(bundle: Any) -> AssessmentResult:
    """Evaluate synthetic consolidation evidence and emit a deterministic receipt."""
    normalized = _normalize_bundle(bundle)
    sources = {row["source_id"]: row for row in normalized["sources"]}
    batches = {row["batch_id"]: row for row in normalized["batches"]}
    failures: list[dict[str, str]] = []

    # Cross-reference batch metadata first. Any batch whose identity/schema/sequence
    # evidence is invalid is excluded from downstream canonicalization even if its
    # individual record payloads otherwise look well formed.
    invalid_batches: set[str] = set()
    sequence_groups: dict[tuple[str, int], list[str]] = defaultdict(list)
    for batch in normalized["batches"]:
        source = sources.get(batch["source_id"])
        if source is None:
            failures.append(_failure("UNKNOWN_BATCH_SOURCE", batch["batch_id"]))
            invalid_batches.add(batch["batch_id"])
            continue
        if batch["schema_version"] != source["schema_version"]:
            failures.append(_failure("BATCH_SCHEMA_MISMATCH", batch["batch_id"]))
            invalid_batches.add(batch["batch_id"])
        sequence_groups[(batch["source_id"], batch["sequence"])].append(batch["batch_id"])

    for (source_id, sequence), batch_ids in sorted(sequence_groups.items()):
        if len(batch_ids) > 1:
            failures.append(_failure("DUPLICATE_BATCH_SEQUENCE", f"{source_id}:{sequence}"))
            invalid_batches.update(batch_ids)

    # Event-id idempotence: exact replay collapses; changed replay is quarantined.
    event_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in normalized["records"]:
        event_groups[record["event_id"]].append(record)
    effective_records: list[dict[str, Any]] = []
    exact_replays = 0
    conflicting_event_ids: set[str] = set()
    for event_id, rows in sorted(event_groups.items()):
        identities = {_digest(row) for row in rows}
        if len(identities) > 1:
            failures.append(_failure("EVENT_REPLAY_CONFLICT", event_id))
            conflicting_event_ids.add(event_id)
            continue
        effective_records.append(rows[0])
        exact_replays += len(rows) - 1

    # Reference and payload contract validation. Invalid records remain visible but never
    # participate in canonical migration candidates.
    eligible_records: list[dict[str, Any]] = []
    records_by_batch: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in effective_records:
        source = sources.get(record["source_id"])
        batch = batches.get(record["batch_id"])
        valid = True
        if source is None:
            failures.append(_failure("UNKNOWN_RECORD_SOURCE", record["event_id"]))
            valid = False
        if batch is None:
            failures.append(_failure("UNKNOWN_RECORD_BATCH", record["event_id"]))
            valid = False
        elif batch["source_id"] != record["source_id"]:
            failures.append(_failure("RECORD_BATCH_SOURCE_MISMATCH", record["event_id"]))
            valid = False
        if source is not None:
            missing = sorted(set(source["required_fields"]) - set(record["payload"]))
            for field in missing:
                failures.append(_failure("MISSING_REQUIRED_SOURCE_FIELD", f"{record['event_id']}:{field}"))
                valid = False
            unmapped = sorted(set(record["payload"]) - set(source["field_map"]))
            for field in unmapped:
                failures.append(_failure("UNMAPPED_SOURCE_FIELD", f"{record['event_id']}:{field}"))
                valid = False
        if valid:
            eligible_records.append(record)
            records_by_batch[record["batch_id"]].append(record)

    # Exact batch count/content evidence is authoritative and order-invariant. A failed
    # batch is not merely a top-level HOLD: every record carried by it is untrusted for
    # canonical entity construction.
    for batch in normalized["batches"]:
        rows = sorted(records_by_batch.get(batch["batch_id"], []), key=lambda row: row["event_id"])
        batch_failed = False
        if len(rows) != batch["declared_records"]:
            failures.append(
                _failure(
                    "BATCH_RECORD_COUNT_MISMATCH",
                    f"{batch['batch_id']}:declared={batch['declared_records']}:observed={len(rows)}",
                )
            )
            batch_failed = True
        observed_digest = _digest(rows)
        if observed_digest != batch["content_sha256"]:
            failures.append(_failure("BATCH_CONTENT_MISMATCH", batch["batch_id"]))
            batch_failed = True
        if batch_failed:
            invalid_batches.add(batch["batch_id"])

    trusted_records = [
        record for record in eligible_records if record["batch_id"] not in invalid_batches
    ]

    # Explicit source inventory completeness is part of each entity's disposition, not
    # only a global assessment failure. This keeps a missing source or untrusted batch
    # from leaving a superficially clean migration candidate behind.
    entity_holds: dict[str, list[dict[str, str]]] = defaultdict(list)
    observed_keys_by_source: dict[str, set[str]] = defaultdict(set)
    for record in trusted_records:
        observed_keys_by_source[record["source_id"]].add(record["entity_key"])
    for source_id, source in sorted(sources.items()):
        expected = set(source["expected_entity_keys"])
        observed = observed_keys_by_source.get(source_id, set())
        for key in sorted(expected - observed):
            reason = _failure("SOURCE_ENTITY_MISSING", f"{source_id}:{key}")
            failures.append(reason)
            entity_holds[key].append(reason)
        for key in sorted(observed - expected):
            reason = _failure("SOURCE_ENTITY_UNEXPECTED", f"{source_id}:{key}")
            failures.append(reason)
            entity_holds[key].append(reason)

    # Reduce each trusted (source, entity) stream to its latest unambiguous version.
    per_source_entity: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in trusted_records:
        per_source_entity[(record["source_id"], record["entity_key"])].append(record)

    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for (source_id, entity_key), rows in sorted(per_source_entity.items()):
        max_version = max(row["version"] for row in rows)
        candidates = [row for row in rows if row["version"] == max_version]
        semantic_keys = {
            _digest(
                {
                    "external_id": row["external_id"],
                    "payload": row["payload"],
                }
            )
            for row in candidates
        }
        if len(semantic_keys) > 1:
            detail = f"{source_id}:{entity_key}:v{max_version}"
            reason = _failure("ENTITY_VERSION_CONFLICT", detail)
            failures.append(reason)
            entity_holds[entity_key].append(reason)
            continue
        latest[(source_id, entity_key)] = sorted(candidates, key=lambda row: row["event_id"])[0]

    expected_entity_keys = {
        key
        for source in normalized["sources"]
        for key in source["expected_entity_keys"]
    }
    all_entity_keys = sorted(expected_entity_keys | {r["entity_key"] for r in trusted_records})
    required_canonical = set(normalized["canonical_schema"]["required_fields"])
    entity_rows: list[dict[str, Any]] = []
    for entity_key in all_entity_keys:
        values: dict[str, list[tuple[str, str, Any]]] = defaultdict(list)
        lineage: list[dict[str, Any]] = []
        reasons = list(entity_holds.get(entity_key, []))
        for source_id, source in sorted(sources.items()):
            record = latest.get((source_id, entity_key))
            if record is None:
                continue
            lineage.append(
                {
                    "source_id": source_id,
                    "kind": source["kind"],
                    "batch_id": record["batch_id"],
                    "event_id": record["event_id"],
                    "external_id": record["external_id"],
                    "version": record["version"],
                    "record_sha256": _digest(record),
                }
            )
            for source_field, raw_value in record["payload"].items():
                target = source["field_map"].get(source_field)
                if target is not None and raw_value is not None:
                    values[target].append((source_id, record["event_id"], raw_value))

        canonical: dict[str, Any] = {}
        field_lineage: dict[str, list[dict[str, str]]] = {}
        for field, rows in sorted(values.items()):
            distinct = {_digest(value) for _, _, value in rows}
            if len(distinct) > 1:
                sources_text = ",".join(sorted({source_id for source_id, _, _ in rows}))
                reason = _failure("CANONICAL_FIELD_CONFLICT", f"{entity_key}:{field}:{sources_text}")
                failures.append(reason)
                reasons.append(reason)
                continue
            canonical[field] = rows[0][2]
            field_lineage[field] = [
                {"source_id": source_id, "event_id": event_id}
                for source_id, event_id, _ in sorted(rows)
            ]
        for field in sorted(required_canonical - set(canonical)):
            reason = _failure("CANONICAL_REQUIRED_FIELD_MISSING", f"{entity_key}:{field}")
            failures.append(reason)
            reasons.append(reason)

        unique_reasons = sorted(
            {(r["code"], r["detail"]) for r in reasons},
            key=lambda item: item,
        )
        status = "CANDIDATE" if not unique_reasons else "HOLD"
        entity_rows.append(
            {
                "entity_key": entity_key,
                "status": status,
                "reason_codes": [code for code, _ in unique_reasons],
                "reasons": [{"code": code, "detail": detail} for code, detail in unique_reasons],
                "canonical_record": canonical if status == "CANDIDATE" else None,
                "canonical_record_sha256": _digest(canonical) if status == "CANDIDATE" else None,
                "field_lineage": field_lineage,
                "source_lineage": lineage,
            }
        )

    failures = [
        {"code": code, "detail": detail}
        for code, detail in sorted({(f["code"], f["detail"]) for f in failures})
    ]
    candidate_count = sum(row["status"] == "CANDIDATE" for row in entity_rows)
    hold_count = len(entity_rows) - candidate_count
    status = "PASS" if not failures and hold_count == 0 else "HOLD"
    inventory = []
    total_expected_links = 0
    total_matched_links = 0
    total_missing_links = 0
    total_unexpected_links = 0
    for s in normalized["sources"]:
        expected = set(s["expected_entity_keys"])
        observed = observed_keys_by_source.get(s["source_id"], set())
        matched = len(expected & observed)
        missing = len(expected - observed)
        unexpected = len(observed - expected)
        total_expected_links += len(expected)
        total_matched_links += matched
        total_missing_links += missing
        total_unexpected_links += unexpected
        inventory.append(
            {
                "source_id": s["source_id"],
                "kind": s["kind"],
                "schema_version": s["schema_version"],
                "batch_count": sum(b["source_id"] == s["source_id"] for b in normalized["batches"]),
                "trusted_batch_count": sum(
                    b["source_id"] == s["source_id"] and b["batch_id"] not in invalid_batches
                    for b in normalized["batches"]
                ),
                "expected_entities": len(expected),
                "observed_entities": len(observed),
                "matched_entities": matched,
                "missing_entities": missing,
                "unexpected_entities": unexpected,
                "completeness_ppm": 1_000_000 if not expected else matched * 1_000_000 // len(expected),
            }
        )
    exception_counts: dict[str, int] = defaultdict(int)
    for failure in failures:
        exception_counts[failure["code"]] += 1
    reconciliation = {
        "expected_source_entity_links": total_expected_links,
        "matched_source_entity_links": total_matched_links,
        "missing_source_entity_links": total_missing_links,
        "unexpected_source_entity_links": total_unexpected_links,
        "source_entity_completeness_ppm": (
            1_000_000
            if total_expected_links == 0
            else total_matched_links * 1_000_000 // total_expected_links
        ),
        "candidate_entities": candidate_count,
        "held_entities": hold_count,
        "exception_counts": dict(sorted(exception_counts.items())),
    }
    payload = {
        "schema": RECEIPT_SCHEMA,
        "status": status,
        "assessment_id": normalized["assessment_id"],
        "input_sha256": _digest(normalized),
        "canonical_schema": normalized["canonical_schema"],
        "source_inventory": inventory,
        "reconciliation": reconciliation,
        "source_count": len(normalized["sources"]),
        "batch_count": len(normalized["batches"]),
        "trusted_batch_count": len(normalized["batches"]) - len(invalid_batches),
        "invalid_batch_count": len(invalid_batches),
        "input_record_count": len(normalized["records"]),
        "effective_record_count": len(effective_records),
        "trusted_record_count": len(trusted_records),
        "exact_replay_count": exact_replays,
        "conflicting_event_count": len(conflicting_event_ids),
        "entity_count": len(entity_rows),
        "migration_candidate_count": candidate_count,
        "quarantined_entity_count": hold_count,
        "entities": entity_rows,
        "failures": failures,
        "migration_authorized": False,
        "external_effects_performed": False,
        "buyer_acceptance_claimed": False,
        "contract_award_claimed": False,
        "revenue_claimed": False,
    }
    receipt_sha = _digest(payload)
    receipt = {**payload, "receipt_sha256": receipt_sha}
    return AssessmentResult(receipt=receipt, receipt_sha256=receipt_sha)


def verify_receipt(receipt: Any) -> bool:
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        return False
    digest = receipt.get("receipt_sha256")
    if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
        return False
    payload = dict(receipt)
    payload.pop("receipt_sha256", None)
    try:
        return _digest(payload) == digest
    except (TypeError, ValueError):
        return False


__all__ = ["evaluate", "verify_receipt"]
