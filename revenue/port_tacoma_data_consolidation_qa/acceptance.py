"""Deterministic synthetic acceptance generator/checker."""
from __future__ import annotations

import argparse
from copy import deepcopy
import random
from pathlib import Path
from typing import Any

try:
    from .core import batch_content_sha256, canonical_json, evaluate, verify_receipt
except ImportError:
    from core import batch_content_sha256, canonical_json, evaluate, verify_receipt


def _source_specs(entity_keys: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "source_id": "EDI-TERMINAL",
            "kind": "edi",
            "schema_version": "edi-v3",
            "required_fields": ["asset", "facility", "state", "weight_lb"],
            "field_map": {"asset": "asset_id", "facility": "facility", "state": "status", "weight_lb": "weight_lb"},
            "expected_entity_keys": entity_keys,
        },
        {
            "source_id": "API-OPS",
            "kind": "api",
            "schema_version": "api-v7",
            "required_fields": ["assetId", "site", "statusCode", "grossWeightLb"],
            "field_map": {"assetId": "asset_id", "site": "facility", "statusCode": "status", "grossWeightLb": "weight_lb"},
            "expected_entity_keys": entity_keys,
        },
        {
            "source_id": "FILE-ARCHIVE",
            "kind": "file",
            "schema_version": "csv-v2",
            "required_fields": ["equipment_id", "terminal", "state", "weight"],
            "field_map": {"equipment_id": "asset_id", "terminal": "facility", "state": "status", "weight": "weight_lb"},
            "expected_entity_keys": entity_keys,
        },
    ]


def make_clean_bundle(entity_count: int = 200, *, seed: int = 720261047) -> dict[str, Any]:
    keys = [f"ENTITY-{i:04d}" for i in range(1, entity_count + 1)]
    sources = _source_specs(keys)
    records: list[dict[str, Any]] = []
    batches: list[dict[str, Any]] = []
    field_by_source = {
        "EDI-TERMINAL": ("asset", "facility", "state", "weight_lb"),
        "API-OPS": ("assetId", "site", "statusCode", "grossWeightLb"),
        "FILE-ARCHIVE": ("equipment_id", "terminal", "state", "weight"),
    }
    schema_by_source = {s["source_id"]: s["schema_version"] for s in sources}
    for source_idx, source in enumerate(sources):
        source_id = source["source_id"]
        fields = field_by_source[source_id]
        split = (entity_count + 1) // 2
        for batch_no, start in enumerate((0, split), start=1):
            end = split if batch_no == 1 else entity_count
            batch_id = f"{source_id}-B{batch_no}"
            batch_rows: list[dict[str, Any]] = []
            for i in range(start, end):
                key = keys[i]
                values = (f"ASSET-{i+1:05d}", f"FAC-{(i % 7)+1}", "ACTIVE" if i % 9 else "HOLD", 20_000 + i)
                payload = {field: value for field, value in zip(fields, values)}
                row = {
                    "event_id": f"EV-{source_idx+1}-{i+1:05d}",
                    "source_id": source_id,
                    "batch_id": batch_id,
                    "external_id": f"EXT-{source_idx+1}-{i+1:05d}",
                    "entity_key": key,
                    "version": 1,
                    "payload": payload,
                }
                records.append(row)
                batch_rows.append(row)
            batches.append(
                {
                    "batch_id": batch_id,
                    "source_id": source_id,
                    "sequence": batch_no,
                    "schema_version": schema_by_source[source_id],
                    "content_sha256": batch_content_sha256(batch_rows),
                    "declared_records": len(batch_rows),
                }
            )
    # Exact event replays prove retry collapse without changing batch digests/counts.
    for idx in (3, 57, 111, 159):
        if idx < len(records):
            records.append(deepcopy(records[idx]))
    rng = random.Random(seed)
    rng.shuffle(records)
    rng.shuffle(batches)
    rng.shuffle(sources)
    return {
        "schema": "port-tacoma-data-consolidation-qa/v1",
        "assessment_id": f"SYNTH-PORT-TACOMA-{entity_count}",
        "canonical_schema": {
            "version": "canonical-v1",
            "required_fields": ["asset_id", "facility", "status", "weight_lb"],
            "optional_fields": [],
        },
        "sources": sources,
        "batches": batches,
        "records": records,
    }


def _codes(receipt: dict[str, Any]) -> set[str]:
    return {row["code"] for row in receipt["failures"]}


def run_acceptance() -> dict[str, Any]:
    bundle = make_clean_bundle()
    first = evaluate(bundle)
    reverse = deepcopy(bundle)
    reverse["records"].reverse()
    reverse["batches"].reverse()
    reverse["sources"].reverse()
    second = evaluate(reverse)
    if first.receipt["status"] != "PASS" or not verify_receipt(first.receipt):
        raise RuntimeError("clean synthetic assessment did not PASS")
    if first.receipt_sha256 != second.receipt_sha256:
        raise RuntimeError("order-invariance failed")

    hostile_codes: dict[str, str] = {}

    replay = make_clean_bundle(12)
    changed = deepcopy(replay["records"][0])
    changed["payload"][next(iter(changed["payload"]))] = "DRIFT"
    replay["records"].append(changed)
    hostile_codes["changed_event_replay"] = "EVENT_REPLAY_CONFLICT" if "EVENT_REPLAY_CONFLICT" in _codes(evaluate(replay).receipt) else "MISSING"

    content = make_clean_bundle(12)
    content["batches"][0]["content_sha256"] = "0" * 64
    hostile_codes["batch_content_drift"] = "BATCH_CONTENT_MISMATCH" if "BATCH_CONTENT_MISMATCH" in _codes(evaluate(content).receipt) else "MISSING"

    count = make_clean_bundle(12)
    count["batches"][0]["declared_records"] += 1
    hostile_codes["batch_count_drift"] = "BATCH_RECORD_COUNT_MISMATCH" if "BATCH_RECORD_COUNT_MISMATCH" in _codes(evaluate(count).receipt) else "MISSING"

    missing = make_clean_bundle(12)
    victim = missing["sources"][0]["source_id"]
    victim_key = missing["sources"][0]["expected_entity_keys"][0]
    missing["records"] = [r for r in missing["records"] if not (r["source_id"] == victim and r["entity_key"] == victim_key)]
    hostile_codes["source_missing_entity"] = "SOURCE_ENTITY_MISSING" if "SOURCE_ENTITY_MISSING" in _codes(evaluate(missing).receipt) else "MISSING"

    conflict = make_clean_bundle(12)
    # Drift one source's canonical status while keeping batch evidence truthful.
    row = next(r for r in conflict["records"] if r["source_id"] == "API-OPS" and r["entity_key"] == "ENTITY-0001")
    row["payload"]["statusCode"] = "CONFLICTING"
    for b in conflict["batches"]:
        if b["batch_id"] == row["batch_id"]:
            effective = []
            seen = set()
            for r in conflict["records"]:
                if r["batch_id"] == b["batch_id"] and r["event_id"] not in seen:
                    effective.append(r); seen.add(r["event_id"])
            b["content_sha256"] = batch_content_sha256(effective)
    hostile_codes["canonical_conflict"] = "CANONICAL_FIELD_CONFLICT" if "CANONICAL_FIELD_CONFLICT" in _codes(evaluate(conflict).receipt) else "MISSING"

    summary = {
        "schema": "port-tacoma-data-consolidation-acceptance/v1",
        "synthetic_sources": first.receipt["source_count"],
        "synthetic_batches": first.receipt["batch_count"],
        "trusted_batches": first.receipt["trusted_batch_count"],
        "synthetic_entities": first.receipt["entity_count"],
        "input_records": first.receipt["input_record_count"],
        "effective_records": first.receipt["effective_record_count"],
        "trusted_records": first.receipt["trusted_record_count"],
        "source_entity_completeness_ppm": first.receipt["reconciliation"]["source_entity_completeness_ppm"],
        "exact_replays_collapsed": first.receipt["exact_replay_count"],
        "migration_candidates": first.receipt["migration_candidate_count"],
        "quarantined_entities": first.receipt["quarantined_entity_count"],
        "order_invariant_receipt": first.receipt_sha256 == second.receipt_sha256,
        "receipt_verified": verify_receipt(first.receipt),
        "hostile_classes": dict(sorted(hostile_codes.items())),
        "migration_authorized": False,
        "external_effects_performed": False,
    }
    if any(value == "MISSING" for value in hostile_codes.values()):
        raise RuntimeError(f"hostile acceptance missing: {hostile_codes}")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path)
    args = parser.parse_args(argv)
    summary = run_acceptance()
    payload = canonical_json(summary) + b"\n"
    if args.write:
        args.write.write_bytes(payload)
    print(payload.decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
