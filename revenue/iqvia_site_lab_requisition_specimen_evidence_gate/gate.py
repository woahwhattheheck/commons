"""Deterministic, read-only requisition-to-specimen evidence gate.

This module evaluates deidentified/synthetic operational evidence only.
It never decides patient eligibility, specimen disposition, clinical meaning,
database locks, or laboratory release.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

SCHEMA = "iqvia-site-lab-requisition-specimen-evidence-gate/v1"
AUTHORITY = "EVIDENCE_ONLY_HUMAN_SITE_LAB_RESOLUTION"
STATUS_READY = "SPECIMEN_READY"
STATUS_HOLD = "HOLD"

CODES = (
    "PROTOCOL_VISIT_MISMATCH",
    "KIT_EXPIRED",
    "COLLECTION_WINDOW_BREACH",
    "MISSING_COURIER_TEMPERATURE",
    "ACCESSION_METHOD_INCOMPATIBLE",
    "UNRESOLVED_QUERY",
)

SOURCE_KEYS = (
    "protocol",
    "requisition",
    "kit",
    "collection",
    "courier",
    "accession",
    "method",
    "queries",
)

PACKET_KEYS = {
    "schema",
    "packet_id",
    "protocol_id",
    "expected_protocol_id",
    "expected_visit_id",
    "requisition_protocol_id",
    "requisition_visit_id",
    "requisition_version",
    "kit_lot",
    "kit_expires_at",
    "collection_at",
    "collection_window_start",
    "collection_window_end",
    "courier_scan_id",
    "courier_temperature_c",
    "courier_min_c",
    "courier_max_c",
    "accession_id",
    "sample_type",
    "required_sample_type",
    "method_id",
    "method_allowed_sample_types",
    "queries",
    "source_refs",
}

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class EvidenceError(ValueError):
    """Raised when input cannot be treated as canonical evidence."""


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EvidenceError("value must be canonical JSON") from exc


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _exact_mapping(value: Any, keys: set[str], field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise EvidenceError(f"{field} must be a mapping")
    obj = dict(value)
    if set(obj) != keys:
        raise EvidenceError(f"{field} must contain exactly {sorted(keys)}")
    return obj


def _bounded_text(value: Any, field: str, limit: int = 256) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > limit:
        raise EvidenceError(f"{field} must be a bounded non-empty string")
    return value


def _identifier(value: Any, field: str) -> str:
    text = _bounded_text(value, field, 128)
    if not ID_RE.fullmatch(text):
        raise EvidenceError(f"{field} is not a canonical identifier")
    return text


def _hash(value: Any, field: str) -> str:
    text = _bounded_text(value, field, 64)
    if not HASH_RE.fullmatch(text):
        raise EvidenceError(f"{field} must be lowercase sha256 hex")
    return text


def _time(value: Any, field: str) -> datetime:
    text = _bounded_text(value, field, 40)
    if not text.endswith("Z"):
        raise EvidenceError(f"{field} must be UTC RFC3339 ending in Z")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise EvidenceError(f"{field} must be RFC3339") from exc
    return parsed.astimezone(timezone.utc)


def _number(value: Any, field: str, lo: float, hi: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceError(f"{field} must be numeric")
    out = float(value)
    if not math.isfinite(out) or out < lo or out > hi:
        raise EvidenceError(f"{field} must be finite in [{lo}, {hi}]")
    return out


def _optional_number(value: Any, field: str, lo: float, hi: float) -> float | None:
    if value is None:
        return None
    return _number(value, field, lo, hi)


def _optional_id(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _identifier(value, field)


def _source_refs(value: Any) -> dict[str, str]:
    obj = _exact_mapping(value, set(SOURCE_KEYS), "source_refs")
    return {key: _hash(obj[key], f"source_refs.{key}") for key in SOURCE_KEYS}


def _sample_types(value: Any) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= 32:
        raise EvidenceError("method_allowed_sample_types must be a bounded non-empty list")
    items = [_identifier(item, "method_allowed_sample_types[]") for item in value]
    if len(items) != len(set(items)):
        raise EvidenceError("method_allowed_sample_types contains duplicates")
    return sorted(items)


def _queries(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 64:
        raise EvidenceError("queries must be a bounded list")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, raw in enumerate(value):
        obj = _exact_mapping(
            raw,
            {"query_id", "status", "resolution_evidence_hash"},
            f"queries[{idx}]",
        )
        query_id = _identifier(obj["query_id"], f"queries[{idx}].query_id")
        if query_id in seen:
            raise EvidenceError("queries contain duplicate query_id")
        seen.add(query_id)
        status = _bounded_text(obj["status"], f"queries[{idx}].status", 32)
        if status not in {"OPEN", "RESOLVED"}:
            raise EvidenceError("query status must be OPEN or RESOLVED")
        evidence = obj["resolution_evidence_hash"]
        if status == "RESOLVED":
            evidence = _hash(evidence, f"queries[{idx}].resolution_evidence_hash")
        elif evidence is not None:
            raise EvidenceError("OPEN query cannot carry resolution evidence")
        out.append(
            {
                "query_id": query_id,
                "status": status,
                "resolution_evidence_hash": evidence,
            }
        )
    return sorted(out, key=lambda row: row["query_id"])


def normalize_packet(raw: Mapping[str, Any]) -> dict[str, Any]:
    obj = _exact_mapping(raw, PACKET_KEYS, "packet")
    if obj["schema"] != SCHEMA:
        raise EvidenceError("unsupported packet schema")

    protocol_id = _identifier(obj["protocol_id"], "protocol_id")
    expected_protocol_id = _identifier(obj["expected_protocol_id"], "expected_protocol_id")
    expected_visit_id = _identifier(obj["expected_visit_id"], "expected_visit_id")
    requisition_protocol_id = _identifier(obj["requisition_protocol_id"], "requisition_protocol_id")
    requisition_visit_id = _identifier(obj["requisition_visit_id"], "requisition_visit_id")

    collection_at = _time(obj["collection_at"], "collection_at")
    window_start = _time(obj["collection_window_start"], "collection_window_start")
    window_end = _time(obj["collection_window_end"], "collection_window_end")
    kit_expires = _time(obj["kit_expires_at"], "kit_expires_at")
    if window_end < window_start:
        raise EvidenceError("collection window is inverted")

    courier_min = _number(obj["courier_min_c"], "courier_min_c", -100.0, 100.0)
    courier_max = _number(obj["courier_max_c"], "courier_max_c", -100.0, 100.0)
    if courier_max < courier_min:
        raise EvidenceError("courier temperature range is inverted")
    courier_temp = _optional_number(
        obj["courier_temperature_c"], "courier_temperature_c", -100.0, 100.0
    )

    return {
        "schema": SCHEMA,
        "packet_id": _identifier(obj["packet_id"], "packet_id"),
        "protocol_id": protocol_id,
        "expected_protocol_id": expected_protocol_id,
        "expected_visit_id": expected_visit_id,
        "requisition_protocol_id": requisition_protocol_id,
        "requisition_visit_id": requisition_visit_id,
        "requisition_version": _identifier(obj["requisition_version"], "requisition_version"),
        "kit_lot": _identifier(obj["kit_lot"], "kit_lot"),
        "kit_expires_at": kit_expires.isoformat().replace("+00:00", "Z"),
        "collection_at": collection_at.isoformat().replace("+00:00", "Z"),
        "collection_window_start": window_start.isoformat().replace("+00:00", "Z"),
        "collection_window_end": window_end.isoformat().replace("+00:00", "Z"),
        "courier_scan_id": _optional_id(obj["courier_scan_id"], "courier_scan_id"),
        "courier_temperature_c": courier_temp,
        "courier_min_c": courier_min,
        "courier_max_c": courier_max,
        "accession_id": _identifier(obj["accession_id"], "accession_id"),
        "sample_type": _identifier(obj["sample_type"], "sample_type"),
        "required_sample_type": _identifier(obj["required_sample_type"], "required_sample_type"),
        "method_id": _identifier(obj["method_id"], "method_id"),
        "method_allowed_sample_types": _sample_types(obj["method_allowed_sample_types"]),
        "queries": _queries(obj["queries"]),
        "source_refs": _source_refs(obj["source_refs"]),
    }


def evaluate_packet(raw: Mapping[str, Any]) -> dict[str, Any]:
    p = normalize_packet(raw)
    collection = _time(p["collection_at"], "collection_at")
    reasons: list[dict[str, Any]] = []

    def hold(code: str, sources: Iterable[str]) -> None:
        refs = {key: p["source_refs"][key] for key in sorted(set(sources))}
        reasons.append({"code": code, "source_refs": refs})

    if (
        p["protocol_id"] != p["expected_protocol_id"]
        or p["requisition_protocol_id"] != p["expected_protocol_id"]
        or p["requisition_visit_id"] != p["expected_visit_id"]
    ):
        hold("PROTOCOL_VISIT_MISMATCH", ("protocol", "requisition"))

    if collection > _time(p["kit_expires_at"], "kit_expires_at"):
        hold("KIT_EXPIRED", ("kit", "collection"))

    if not (
        _time(p["collection_window_start"], "collection_window_start")
        <= collection
        <= _time(p["collection_window_end"], "collection_window_end")
    ):
        hold("COLLECTION_WINDOW_BREACH", ("collection", "requisition"))

    if (
        p["courier_scan_id"] is None
        or p["courier_temperature_c"] is None
        or not (p["courier_min_c"] <= p["courier_temperature_c"] <= p["courier_max_c"])
    ):
        hold("MISSING_COURIER_TEMPERATURE", ("courier",))

    if (
        p["sample_type"] != p["required_sample_type"]
        or p["sample_type"] not in p["method_allowed_sample_types"]
    ):
        hold("ACCESSION_METHOD_INCOMPATIBLE", ("accession", "method", "requisition"))

    unresolved = [
        q for q in p["queries"]
        if q["status"] != "RESOLVED" or not q["resolution_evidence_hash"]
    ]
    if unresolved:
        hold("UNRESOLVED_QUERY", ("queries",))

    reasons = sorted(reasons, key=lambda item: item["code"])
    status = STATUS_READY if not reasons else STATUS_HOLD
    evidence_digest = sha256_value(p)
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "packet_id": p["packet_id"],
        "status": status,
        "reason_codes": [item["code"] for item in reasons],
        "reasons": reasons,
        "source_refs": p["source_refs"],
        "source_digest": sha256_value(p["source_refs"]),
        "evidence_digest": evidence_digest,
    }


def evaluate_batch(packets: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(packets)
    if not 1 <= len(rows) <= 10000:
        raise EvidenceError("batch must contain 1..10000 packets")
    normalized_ids: set[str] = set()
    results: list[dict[str, Any]] = []
    for raw in rows:
        result = evaluate_packet(raw)
        packet_id = result["packet_id"]
        if packet_id in normalized_ids:
            raise EvidenceError(f"duplicate packet_id: {packet_id}")
        normalized_ids.add(packet_id)
        results.append(result)
    results.sort(key=lambda row: row["packet_id"])
    counts = {STATUS_READY: 0, STATUS_HOLD: 0}
    reason_counts = {code: 0 for code in CODES}
    for row in results:
        counts[row["status"]] += 1
        for code in row["reason_codes"]:
            reason_counts[code] += 1
    core = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "packet_count": len(results),
        "status_counts": counts,
        "reason_counts": reason_counts,
        "results": results,
    }
    return {**core, "batch_digest": sha256_value(core)}


def render_json(report: Mapping[str, Any]) -> bytes:
    return canonical_bytes(report) + b"\n"


def render_csv(report: Mapping[str, Any]) -> bytes:
    obj = _exact_mapping(
        report,
        {
            "schema",
            "authority",
            "packet_count",
            "status_counts",
            "reason_counts",
            "results",
            "batch_digest",
        },
        "report",
    )
    sink = io.StringIO(newline="")
    writer = csv.writer(sink, lineterminator="\n")
    writer.writerow(
        [
            "packet_id",
            "status",
            "reason_codes",
            "source_digest",
            "evidence_digest",
            "source_refs_json",
        ]
    )
    for row in obj["results"]:
        writer.writerow(
            [
                row["packet_id"],
                row["status"],
                "|".join(row["reason_codes"]),
                row["source_digest"],
                row["evidence_digest"],
                canonical_bytes(row["source_refs"]).decode("utf-8"),
            ]
        )
    return sink.getvalue().encode("utf-8")


def output_manifest(report: Mapping[str, Any]) -> dict[str, Any]:
    json_bytes = render_json(report)
    csv_bytes = render_csv(report)
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "packet_count": report["packet_count"],
        "batch_digest": report["batch_digest"],
        "json_sha256": hashlib.sha256(json_bytes).hexdigest(),
        "csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
    }
