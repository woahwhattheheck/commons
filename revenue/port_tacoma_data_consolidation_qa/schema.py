"""Deterministic provider-free data-consolidation assessment core.

The module evaluates caller-supplied synthetic inventory/batch/record evidence only.  It
never connects to Port of Tacoma/NWSA systems, EDI endpoints, APIs, fileshares, or a
migration target and never authorizes a migration.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence

ASSESSMENT_SCHEMA = "port-tacoma-data-consolidation-qa/v1"
RECEIPT_SCHEMA = "port-tacoma-data-consolidation-receipt/v1"
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_ITEMS = 100_000
MAX_TEXT = 512
MAX_FIELDS = 512
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_KINDS = {"edi", "api", "file"}
_MISSING = object()


class ConsolidationEvidenceError(ValueError):
    """Fail-closed structural/schema error."""


@dataclass(frozen=True)
class AssessmentResult:
    receipt: dict[str, Any]
    receipt_sha256: str


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _fail(code: str, detail: str = "") -> None:
    raise ConsolidationEvidenceError(f"{code}:{detail}" if detail else code)


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("EXPECTED_OBJECT", name)
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    got = set(value)
    if got != expected:
        _fail(
            "SCHEMA_KEYS",
            f"{name}:missing={sorted(expected-got)}:extra={sorted(got-expected)}",
        )


def _text(value: Any, name: str, *, identifier: bool = False, field: bool = False) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_TEXT:
        _fail("INVALID_TEXT", name)
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        _fail("CONTROL_CHARACTER", name)
    if identifier and not _ID_RE.fullmatch(value):
        _fail("INVALID_IDENTIFIER", name)
    if field and not _FIELD_RE.fullmatch(value):
        _fail("INVALID_FIELD_NAME", name)
    return value


def _plain_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail("INVALID_INTEGER", name)
    return value


def _scalar(value: Any, name: str) -> Any:
    # Deliberately no float acceptance: decimal transport differences are a migration-QA
    # ambiguity. Callers can use exact integer minor units or decimal strings.
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, str):
        return _text(value, name)
    _fail("NON_SCALAR_VALUE", name)


def _unique_text_list(value: Any, name: str, *, field: bool = False, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_ITEMS or (not allow_empty and not value):
        _fail("INVALID_LIST", name)
    rows = [_text(v, f"{name}[{i}]", identifier=not field, field=field) for i, v in enumerate(value)]
    if len(rows) != len(set(rows)):
        _fail("DUPLICATE_LIST_VALUE", name)
    return sorted(rows)


def _canonical_schema(value: Any) -> dict[str, Any]:
    row = _object(value, "canonical_schema")
    _exact_keys(row, {"version", "required_fields", "optional_fields"}, "canonical_schema")
    version = _text(row["version"], "canonical_schema.version", identifier=True)
    required = _unique_text_list(row["required_fields"], "canonical_schema.required_fields", field=True)
    optional = _unique_text_list(row["optional_fields"], "canonical_schema.optional_fields", field=True)
    if len(required) + len(optional) > MAX_FIELDS:
        _fail("TOO_MANY_CANONICAL_FIELDS")
    overlap = set(required) & set(optional)
    if overlap:
        _fail("CANONICAL_FIELD_OVERLAP", ",".join(sorted(overlap)))
    return {"version": version, "required_fields": required, "optional_fields": optional}


def _source(value: Any, index: int, canonical_fields: set[str]) -> dict[str, Any]:
    name = f"sources[{index}]"
    row = _object(value, name)
    _exact_keys(
        row,
        {"source_id", "kind", "schema_version", "required_fields", "field_map", "expected_entity_keys"},
        name,
    )
    source_id = _text(row["source_id"], f"{name}.source_id", identifier=True)
    kind = _text(row["kind"], f"{name}.kind")
    if kind not in _ALLOWED_KINDS:
        _fail("INVALID_SOURCE_KIND", kind)
    schema_version = _text(row["schema_version"], f"{name}.schema_version", identifier=True)
    required_fields = _unique_text_list(row["required_fields"], f"{name}.required_fields", field=True)
    fmap = _object(row["field_map"], f"{name}.field_map")
    if len(fmap) > MAX_FIELDS:
        _fail("TOO_MANY_FIELD_MAPPINGS", source_id)
    normalized_map: dict[str, str] = {}
    for raw_source, raw_target in fmap.items():
        source_field = _text(raw_source, f"{name}.field_map.source", field=True)
        target_field = _text(raw_target, f"{name}.field_map.{source_field}", field=True)
        if target_field not in canonical_fields:
            _fail("UNKNOWN_CANONICAL_FIELD", f"{source_id}:{target_field}")
        normalized_map[source_field] = target_field
    if not set(required_fields).issubset(normalized_map):
        _fail("UNMAPPED_REQUIRED_SOURCE_FIELD", source_id)
    targets = list(normalized_map.values())
    if len(targets) != len(set(targets)):
        _fail("AMBIGUOUS_FIELD_MAP", source_id)
    expected = _unique_text_list(row["expected_entity_keys"], f"{name}.expected_entity_keys")
    return {
        "source_id": source_id,
        "kind": kind,
        "schema_version": schema_version,
        "required_fields": required_fields,
        "field_map": dict(sorted(normalized_map.items())),
        "expected_entity_keys": expected,
    }


def _batch(value: Any, index: int) -> dict[str, Any]:
    name = f"batches[{index}]"
    row = _object(value, name)
    _exact_keys(
        row,
        {"batch_id", "source_id", "sequence", "schema_version", "content_sha256", "declared_records"},
        name,
    )
    digest = _text(row["content_sha256"], f"{name}.content_sha256")
    if not _HEX64_RE.fullmatch(digest):
        _fail("INVALID_SHA256", f"{name}.content_sha256")
    return {
        "batch_id": _text(row["batch_id"], f"{name}.batch_id", identifier=True),
        "source_id": _text(row["source_id"], f"{name}.source_id", identifier=True),
        "sequence": _plain_int(row["sequence"], f"{name}.sequence", minimum=1),
        "schema_version": _text(row["schema_version"], f"{name}.schema_version", identifier=True),
        "content_sha256": digest,
        "declared_records": _plain_int(row["declared_records"], f"{name}.declared_records"),
    }


def _record(value: Any, index: int) -> dict[str, Any]:
    name = f"records[{index}]"
    row = _object(value, name)
    _exact_keys(
        row,
        {"event_id", "source_id", "batch_id", "external_id", "entity_key", "version", "payload"},
        name,
    )
    payload = _object(row["payload"], f"{name}.payload")
    if len(payload) > MAX_FIELDS:
        _fail("TOO_MANY_PAYLOAD_FIELDS", name)
    normalized_payload: dict[str, Any] = {}
    for raw_key, raw_value in payload.items():
        key = _text(raw_key, f"{name}.payload.field", field=True)
        normalized_payload[key] = _scalar(raw_value, f"{name}.payload.{key}")
    return {
        "event_id": _text(row["event_id"], f"{name}.event_id", identifier=True),
        "source_id": _text(row["source_id"], f"{name}.source_id", identifier=True),
        "batch_id": _text(row["batch_id"], f"{name}.batch_id", identifier=True),
        "external_id": _text(row["external_id"], f"{name}.external_id", identifier=True),
        "entity_key": _text(row["entity_key"], f"{name}.entity_key", identifier=True),
        "version": _plain_int(row["version"], f"{name}.version", minimum=1),
        "payload": dict(sorted(normalized_payload.items())),
    }


def _normalize_bundle(bundle: Any) -> dict[str, Any]:
    try:
        encoded = canonical_json(bundle)
    except (TypeError, ValueError) as exc:
        _fail("INVALID_JSON_VALUE", str(exc))
    if len(encoded) > MAX_INPUT_BYTES:
        _fail("INPUT_TOO_LARGE")
    root = _object(bundle, "bundle")
    _exact_keys(
        root,
        {"schema", "assessment_id", "canonical_schema", "sources", "batches", "records"},
        "bundle",
    )
    if root["schema"] != ASSESSMENT_SCHEMA:
        _fail("UNSUPPORTED_SCHEMA")
    assessment_id = _text(root["assessment_id"], "assessment_id", identifier=True)
    canonical_schema = _canonical_schema(root["canonical_schema"])
    canonical_fields = set(canonical_schema["required_fields"]) | set(canonical_schema["optional_fields"])

    if not isinstance(root["sources"], list) or not root["sources"] or len(root["sources"]) > MAX_ITEMS:
        _fail("INVALID_SOURCES")
    sources = [_source(v, i, canonical_fields) for i, v in enumerate(root["sources"])]
    source_ids = [s["source_id"] for s in sources]
    if len(source_ids) != len(set(source_ids)):
        _fail("DUPLICATE_SOURCE_ID")

    if not isinstance(root["batches"], list) or not root["batches"] or len(root["batches"]) > MAX_ITEMS:
        _fail("INVALID_BATCHES")
    batches = [_batch(v, i) for i, v in enumerate(root["batches"])]
    batch_ids = [b["batch_id"] for b in batches]
    if len(batch_ids) != len(set(batch_ids)):
        _fail("DUPLICATE_BATCH_ID")

    if not isinstance(root["records"], list) or len(root["records"]) > MAX_ITEMS:
        _fail("INVALID_RECORDS")
    records = [_record(v, i) for i, v in enumerate(root["records"])]

    return {
        "schema": ASSESSMENT_SCHEMA,
        "assessment_id": assessment_id,
        "canonical_schema": canonical_schema,
        "sources": sorted(sources, key=lambda row: row["source_id"]),
        "batches": sorted(batches, key=lambda row: (row["source_id"], row["sequence"], row["batch_id"])),
        # Order is deliberately normalized: arrival order is evidence, not authority.
        "records": sorted(records, key=lambda row: (row["event_id"], _digest(row))),
    }


def batch_content_sha256(records: Iterable[Mapping[str, Any]]) -> str:
    """Return the canonical digest for unique normalized records in one batch."""
    normalized = []
    seen: set[str] = set()
    for index, row in enumerate(records):
        item = _record(dict(row), index)
        event_id = item["event_id"]
        if event_id in seen:
            _fail("DUPLICATE_EVENT_FOR_BATCH_DIGEST", event_id)
        seen.add(event_id)
        normalized.append(item)
    normalized.sort(key=lambda row: row["event_id"])
    return _digest(normalized)


def _failure(code: str, detail: str) -> dict[str, str]:
    return {"code": code, "detail": detail}


def load_strict_json(text: str) -> Any:
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        _fail("JSON_TOO_LARGE")

    def no_dupes(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                _fail("DUPLICATE_JSON_KEY", key)
            out[key] = value
        return out

    try:
        return json.loads(
            text,
            object_pairs_hook=no_dupes,
            parse_constant=lambda token: _fail("NONFINITE_JSON_NUMBER", token),
        )
    except ConsolidationEvidenceError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        _fail("INVALID_JSON", str(exc))


__all__ = [
    "ASSESSMENT_SCHEMA",
    "AssessmentResult",
    "ConsolidationEvidenceError",
    "RECEIPT_SCHEMA",
    "batch_content_sha256",
    "canonical_json",
    "load_strict_json",
]
