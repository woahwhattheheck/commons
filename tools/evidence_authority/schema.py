"""Closed schemas and validation for the evidence-authority kernel."""
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from .codec import DomainError, canonical_bytes

MANIFEST_SCHEMA = "commons.evidence-authority.manifest.v1"
SOURCE_SCHEMA = "commons.evidence-authority.source.v1"
CANDIDATE_SCHEMA = "commons.evidence-authority.candidate.v1"
RECEIPT_SCHEMA = "commons.evidence-authority.receipt.v1"

AUTHORITY_CLASSES = frozenset(
    {"PROVIDER_AUTHENTICATED", "BUYER_AUTHENTICATED", "ISSUER_AUTHENTICATED"}
)
MAX_SOURCES = 32
MAX_RECORDS_PER_SOURCE = 256
MAX_CLAIM_PAYLOAD_BYTES = 16_384


def _build_schema_kernel():
    _re = re
    _datetime = datetime
    _utc = UTC
    _DomainError = DomainError
    _canonical = canonical_bytes
    _manifest_schema = MANIFEST_SCHEMA
    _source_schema = SOURCE_SCHEMA
    _candidate_schema = CANDIDATE_SCHEMA
    _authority_classes = frozenset(AUTHORITY_CLASSES)
    _max_sources = MAX_SOURCES
    _max_records = MAX_RECORDS_PER_SOURCE
    _max_payload = MAX_CLAIM_PAYLOAD_BYTES

    _id_re = _re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+ -]{0,127}$")
    _sha_re = _re.compile(r"^[0-9a-f]{64}$")
    _ts_re = _re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    manifest_keys = frozenset({"schema", "generation", "source_count", "sources"})
    manifest_source_keys = frozenset(
        {"source_id", "path", "sha256", "byte_count"}
    )
    source_keys = frozenset(
        {"schema", "source_id", "generation", "record_count", "records"}
    )
    record_keys = frozenset(
        {
            "record_id",
            "claim_id",
            "authority_class",
            "issuer_id",
            "subject_id",
            "claim_kind",
            "claim_scope",
            "generation",
            "issued_at",
            "observed_at",
            "valid_from",
            "valid_until",
            "claim_payload",
        }
    )
    candidate_keys = frozenset(
        {
            "schema",
            "claim_id",
            "authority_class",
            "issuer_id",
            "subject_id",
            "claim_kind",
            "claim_scope",
            "generation",
            "claim_payload",
        }
    )

    def _exact_keys(obj: Any, keys: frozenset[str], where: str) -> dict[str, Any]:
        if not isinstance(obj, dict):
            raise _DomainError(f"{where} must be an object")
        actual = frozenset(obj)
        if actual != keys:
            missing = sorted(keys - actual)
            extra = sorted(actual - keys)
            raise _DomainError(
                f"{where} keys mismatch; missing={missing}, extra={extra}"
            )
        return obj

    def _identifier(value: Any, where: str) -> str:
        if not isinstance(value, str) or not _id_re.fullmatch(value):
            raise _DomainError(f"{where} is not a bounded identifier")
        if any(ord(ch) < 0x20 or 0x7F <= ord(ch) <= 0x9F for ch in value):
            raise _DomainError(f"{where} contains control characters")
        return value

    def _sha(value: Any, where: str) -> str:
        if not isinstance(value, str) or not _sha_re.fullmatch(value):
            raise _DomainError(f"{where} must be lowercase SHA-256 hex")
        return value

    def _path(value: Any, where: str) -> str:
        if (
            not isinstance(value, str)
            or not value
            or len(value.encode("utf-8")) > 240
        ):
            raise _DomainError(f"{where} must be a bounded relative path")
        if value.startswith("/") or "\\" in value or "//" in value:
            raise _DomainError(f"{where} is not a canonical relative POSIX path")
        parts = value.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise _DomainError(f"{where} contains an aliased path segment")
        for part in parts:
            _identifier(part, where)
        return value

    def parse_timestamp(value: Any, where: str) -> datetime:
        if not isinstance(value, str) or not _ts_re.fullmatch(value):
            raise _DomainError(f"{where} must be canonical UTC seconds")
        try:
            parsed = _datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=_utc
            )
        except ValueError as exc:
            raise _DomainError(f"{where} is not a real UTC timestamp") from exc
        return parsed

    def format_timestamp(value: datetime) -> str:
        if value.tzinfo is None:
            raise _DomainError("timestamp must be timezone-aware")
        return (
            value.astimezone(_utc)
            .replace(microsecond=0)
            .strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    def validate_manifest(value: Any) -> dict[str, Any]:
        obj = _exact_keys(value, manifest_keys, "manifest")
        if obj["schema"] != _manifest_schema:
            raise _DomainError("unsupported manifest schema")
        generation = _identifier(obj["generation"], "manifest.generation")
        sources = obj["sources"]
        if not isinstance(sources, list) or not (1 <= len(sources) <= _max_sources):
            raise _DomainError("manifest.sources must be a non-empty bounded array")
        source_count = obj["source_count"]
        if isinstance(source_count, bool) or not isinstance(source_count, int):
            raise _DomainError("manifest.source_count must be an integer")
        if source_count != len(sources):
            raise _DomainError("manifest.source_count does not match sources")

        paths: list[str] = []
        source_ids: list[str] = []
        for index, entry in enumerate(sources):
            item = _exact_keys(
                entry, manifest_source_keys, f"manifest.sources[{index}]"
            )
            source_ids.append(
                _identifier(
                    item["source_id"], f"manifest.sources[{index}].source_id"
                )
            )
            paths.append(_path(item["path"], f"manifest.sources[{index}].path"))
            _sha(item["sha256"], f"manifest.sources[{index}].sha256")
            byte_count = item["byte_count"]
            if isinstance(byte_count, bool) or not isinstance(byte_count, int):
                raise _DomainError(
                    "manifest source byte_count must be an integer"
                )
            if byte_count < 2 or byte_count > 131_072:
                raise _DomainError("manifest source byte_count outside bound")
        if len(set(paths)) != len(paths) or len(set(source_ids)) != len(source_ids):
            raise _DomainError("manifest source paths and ids must be unique")
        if paths != sorted(paths):
            raise _DomainError("manifest source inventory must be path-sorted")
        return {
            "schema": _manifest_schema,
            "generation": generation,
            "source_count": source_count,
            "sources": sources,
        }

    def validate_source(value: Any) -> dict[str, Any]:
        obj = _exact_keys(value, source_keys, "authority source")
        if obj["schema"] != _source_schema:
            raise _DomainError("unsupported authority-source schema")
        source_id = _identifier(obj["source_id"], "authority source.source_id")
        generation = _identifier(
            obj["generation"], "authority source.generation"
        )
        records = obj["records"]
        if not isinstance(records, list) or len(records) > _max_records:
            raise _DomainError("authority source.records exceeds bound")
        record_count = obj["record_count"]
        if isinstance(record_count, bool) or not isinstance(record_count, int):
            raise _DomainError("authority source.record_count must be an integer")
        if record_count != len(records):
            raise _DomainError(
                "authority source.record_count does not match records"
            )

        record_ids: set[str] = set()
        claim_ids: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for index, record in enumerate(records):
            item = _exact_keys(record, record_keys, f"records[{index}]")
            record_id = _identifier(
                item["record_id"], f"records[{index}].record_id"
            )
            claim_id = _identifier(
                item["claim_id"], f"records[{index}].claim_id"
            )
            if record_id in record_ids:
                raise _DomainError("duplicate authority record_id")
            if claim_id in claim_ids:
                raise _DomainError(
                    "duplicate authority claim_id within source"
                )
            record_ids.add(record_id)
            claim_ids.add(claim_id)
            authority_class = item["authority_class"]
            if authority_class not in _authority_classes:
                raise _DomainError("unsupported authority class")
            _identifier(item["issuer_id"], f"records[{index}].issuer_id")
            _identifier(item["subject_id"], f"records[{index}].subject_id")
            _identifier(item["claim_kind"], f"records[{index}].claim_kind")
            _identifier(item["claim_scope"], f"records[{index}].claim_scope")
            record_generation = _identifier(
                item["generation"], f"records[{index}].generation"
            )
            if record_generation != generation:
                raise _DomainError(
                    "record generation differs from source generation"
                )
            issued = parse_timestamp(
                item["issued_at"], f"records[{index}].issued_at"
            )
            observed = parse_timestamp(
                item["observed_at"], f"records[{index}].observed_at"
            )
            valid_from = parse_timestamp(
                item["valid_from"], f"records[{index}].valid_from"
            )
            valid_until = parse_timestamp(
                item["valid_until"], f"records[{index}].valid_until"
            )
            if issued > observed:
                raise _DomainError(
                    "authority record issued_at is after observed_at"
                )
            if valid_from > valid_until:
                raise _DomainError(
                    "authority record validity window is inverted"
                )
            payload_bytes = _canonical(item["claim_payload"])
            if len(payload_bytes) > _max_payload:
                raise _DomainError("claim payload exceeds bound")
            normalized.append(item)
        return {
            "schema": _source_schema,
            "source_id": source_id,
            "generation": generation,
            "record_count": record_count,
            "records": normalized,
        }

    def validate_candidate(value: Any) -> dict[str, Any]:
        obj = _exact_keys(value, candidate_keys, "candidate")
        if obj["schema"] != _candidate_schema:
            raise _DomainError("unsupported candidate schema")
        _identifier(obj["claim_id"], "candidate.claim_id")
        authority_class = obj["authority_class"]
        if authority_class not in _authority_classes:
            raise _DomainError("unsupported requested authority class")
        _identifier(obj["issuer_id"], "candidate.issuer_id")
        _identifier(obj["subject_id"], "candidate.subject_id")
        _identifier(obj["claim_kind"], "candidate.claim_kind")
        _identifier(obj["claim_scope"], "candidate.claim_scope")
        _identifier(obj["generation"], "candidate.generation")
        if len(_canonical(obj["claim_payload"])) > _max_payload:
            raise _DomainError("candidate claim payload exceeds bound")
        return obj

    def validate_pinned_root(value: Any) -> str:
        return _sha(value, "pinned manifest root")

    return (
        parse_timestamp,
        format_timestamp,
        validate_manifest,
        validate_source,
        validate_candidate,
        validate_pinned_root,
    )


(
    parse_timestamp,
    format_timestamp,
    validate_manifest,
    validate_source,
    validate_candidate,
    validate_pinned_root,
) = _build_schema_kernel()
del _build_schema_kernel
