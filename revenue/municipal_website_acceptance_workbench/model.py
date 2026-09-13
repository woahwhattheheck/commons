from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

PASS = "PASS"
HOLD = "HOLD"
PACKET_READY_FOR_HUMAN_UAT = "PACKET_READY_FOR_HUMAN_UAT"

MIGRATION = "MIGRATION"
REDIRECT = "REDIRECT"
LINK_DOCUMENT = "LINK_DOCUMENT"
ACCESSIBILITY = "ACCESSIBILITY"
INTEGRATION = "INTEGRATION"
ROLE_PERMISSION = "ROLE_PERMISSION"
RESTORE = "RESTORE"
KINDS = (MIGRATION, REDIRECT, LINK_DOCUMENT, ACCESSIBILITY, INTEGRATION, ROLE_PERMISSION, RESTORE)

MIGRATION_DIGEST_MISMATCH = "MIGRATION_DIGEST_MISMATCH"
REDIRECT_CHAIN_INVALID = "REDIRECT_CHAIN_INVALID"
LINK_OR_DOCUMENT_FAILURE = "LINK_OR_DOCUMENT_FAILURE"
ACCESSIBILITY_EVIDENCE_FAILURE = "ACCESSIBILITY_EVIDENCE_FAILURE"
INTEGRATION_FIXTURE_MISMATCH = "INTEGRATION_FIXTURE_MISMATCH"
ROLE_PERMISSION_DRIFT = "ROLE_PERMISSION_DRIFT"
RESTORE_EVIDENCE_INVALID = "RESTORE_EVIDENCE_INVALID"
DEFECT_CODES = (
    MIGRATION_DIGEST_MISMATCH,
    REDIRECT_CHAIN_INVALID,
    LINK_OR_DOCUMENT_FAILURE,
    ACCESSIBILITY_EVIDENCE_FAILURE,
    INTEGRATION_FIXTURE_MISMATCH,
    ROLE_PERMISSION_DRIFT,
    RESTORE_EVIDENCE_INVALID,
)

SCHEMA = "municipal-website-acceptance-workbench/v1"
RECORD_SCHEMA = "municipal-website-acceptance-record/v1"

ROW_KEYS = frozenset(
    {
        "sequence",
        "evidence_id",
        "kind",
        "resource_id",
        "source_ref",
        "observed_at",
        "source_snapshot_sha256",
        "details",
    }
)

_SECRET = re.compile(
    r"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|authorization)\s*[:=]"
)
_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PATH = re.compile(r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/-]*$")


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(value: str) -> str:
    return digest(value.encode("utf-8"))


def require_keys(value: Mapping[str, Any], expected: frozenset[str], where: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{where}: expected mapping")
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing or unknown:
        parts: list[str] = []
        if missing:
            parts.append(f"missing fields: {missing}")
        if unknown:
            parts.append(f"unknown fields: {unknown}")
        raise ValueError(f"{where}: " + "; ".join(parts))


def safe_text(value: Any, where: str, *, allow_spaces: bool = True) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{where}: invalid string")
    if any(ord(ch) < 0x20 for ch in value):
        raise ValueError(f"{where}: control character")
    if not allow_spaces and any(ch.isspace() for ch in value):
        raise ValueError(f"{where}: whitespace not allowed")
    if _SECRET.search(value):
        raise ValueError(f"{where}: secret-shaped value refused")
    if _EMAIL.search(value):
        raise ValueError(f"{where}: email/PII-shaped value refused")
    return value


def safe_sha256(value: Any, where: str) -> str:
    value = safe_text(value, where, allow_spaces=False)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{where}: expected lowercase sha256 hex")
    return value


def safe_path(value: Any, where: str) -> str:
    value = safe_text(value, where, allow_spaces=False)
    if not _PATH.fullmatch(value) or ".." in value.split("/"):
        raise ValueError(f"{where}: invalid path")
    return value


def parse_time(value: Any, where: str) -> datetime:
    value = safe_text(value, where, allow_spaces=False)
    if not value.endswith("Z"):
        raise ValueError(f"{where}: expected UTC Z timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{where}: invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{where}: timezone required")
    return parsed.astimezone(timezone.utc)


def nonnegative_int(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{where}: expected nonnegative integer")
    return value


def decimal_text(value: Any, where: str) -> str:
    if isinstance(value, bool):
        raise ValueError(f"{where}: boolean is not numeric")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{where}: invalid decimal") from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f"{where}: expected nonnegative finite decimal")
    rendered = format(number.normalize(), "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def string_list(value: Any, where: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{where}: expected sequence")
    normalized = [safe_text(item, f"{where}[]", allow_spaces=False) for item in value]
    if normalized != sorted(set(normalized)):
        raise ValueError(f"{where}: expected unique sorted values")
    return normalized


def normalize_details(kind: str, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("details: expected mapping")
    if kind == MIGRATION:
        expected = frozenset({"legacy_path", "new_path", "expected_content_sha256", "observed_content_sha256"})
        require_keys(raw, expected, "migration details")
        return {
            "legacy_path": safe_path(raw["legacy_path"], "legacy_path"),
            "new_path": safe_path(raw["new_path"], "new_path"),
            "expected_content_sha256": safe_sha256(raw["expected_content_sha256"], "expected_content_sha256"),
            "observed_content_sha256": safe_sha256(raw["observed_content_sha256"], "observed_content_sha256"),
        }
    if kind == REDIRECT:
        expected = frozenset({"legacy_path", "expected_target_path", "observed_target_path", "http_status", "hop_count"})
        require_keys(raw, expected, "redirect details")
        return {
            "legacy_path": safe_path(raw["legacy_path"], "legacy_path"),
            "expected_target_path": safe_path(raw["expected_target_path"], "expected_target_path"),
            "observed_target_path": safe_path(raw["observed_target_path"], "observed_target_path"),
            "http_status": nonnegative_int(raw["http_status"], "http_status"),
            "hop_count": nonnegative_int(raw["hop_count"], "hop_count"),
        }
    if kind == LINK_DOCUMENT:
        expected = frozenset({"page_path", "target_path", "http_status", "document_expected_sha256", "document_observed_sha256"})
        require_keys(raw, expected, "link details")
        return {
            "page_path": safe_path(raw["page_path"], "page_path"),
            "target_path": safe_path(raw["target_path"], "target_path"),
            "http_status": nonnegative_int(raw["http_status"], "http_status"),
            "document_expected_sha256": safe_sha256(raw["document_expected_sha256"], "document_expected_sha256"),
            "document_observed_sha256": safe_sha256(raw["document_observed_sha256"], "document_observed_sha256"),
        }
    if kind == ACCESSIBILITY:
        expected = frozenset({"page_path", "standard", "tool", "critical_count", "serious_count", "max_age_days"})
        require_keys(raw, expected, "accessibility details")
        standard = safe_text(raw["standard"], "standard", allow_spaces=False)
        if standard not in {"WCAG2.1AA", "WCAG2.2AA"}:
            raise ValueError("standard: unsupported")
        return {
            "page_path": safe_path(raw["page_path"], "page_path"),
            "standard": standard,
            "tool": safe_text(raw["tool"], "tool"),
            "critical_count": nonnegative_int(raw["critical_count"], "critical_count"),
            "serious_count": nonnegative_int(raw["serious_count"], "serious_count"),
            "max_age_days": nonnegative_int(raw["max_age_days"], "max_age_days"),
        }
    if kind == INTEGRATION:
        expected = frozenset({"integration_name", "fixture_id", "expected_result_sha256", "observed_result_sha256"})
        require_keys(raw, expected, "integration details")
        return {
            "integration_name": safe_text(raw["integration_name"], "integration_name"),
            "fixture_id": safe_text(raw["fixture_id"], "fixture_id", allow_spaces=False),
            "expected_result_sha256": safe_sha256(raw["expected_result_sha256"], "expected_result_sha256"),
            "observed_result_sha256": safe_sha256(raw["observed_result_sha256"], "observed_result_sha256"),
        }
    if kind == ROLE_PERMISSION:
        expected = frozenset({"role", "expected_permissions", "observed_permissions"})
        require_keys(raw, expected, "role details")
        return {
            "role": safe_text(raw["role"], "role", allow_spaces=False),
            "expected_permissions": string_list(raw["expected_permissions"], "expected_permissions"),
            "observed_permissions": string_list(raw["observed_permissions"], "observed_permissions"),
        }
    if kind == RESTORE:
        expected = frozenset({"backup_sha256", "restored_sha256", "restore_exit_code", "expected_item_count", "restored_item_count"})
        require_keys(raw, expected, "restore details")
        return {
            "backup_sha256": safe_sha256(raw["backup_sha256"], "backup_sha256"),
            "restored_sha256": safe_sha256(raw["restored_sha256"], "restored_sha256"),
            "restore_exit_code": nonnegative_int(raw["restore_exit_code"], "restore_exit_code"),
            "expected_item_count": nonnegative_int(raw["expected_item_count"], "expected_item_count"),
            "restored_item_count": nonnegative_int(raw["restored_item_count"], "restored_item_count"),
        }
    raise ValueError(f"unsupported kind: {kind}")


def normalize_row(raw: Mapping[str, Any], *, as_of: datetime) -> dict[str, Any]:
    require_keys(raw, ROW_KEYS, "evidence row")
    sequence = raw["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ValueError("sequence: expected positive integer")
    evidence_id = safe_text(raw["evidence_id"], "evidence_id", allow_spaces=False)
    kind = safe_text(raw["kind"], "kind", allow_spaces=False)
    if kind not in KINDS:
        raise ValueError(f"kind: unsupported {kind}")
    observed_at = parse_time(raw["observed_at"], "observed_at")
    if observed_at > as_of:
        raise ValueError("observed_at: future evidence refused")
    return {
        "sequence": sequence,
        "evidence_id": evidence_id,
        "kind": kind,
        "resource_id": safe_text(raw["resource_id"], "resource_id", allow_spaces=False),
        "source_ref": safe_text(raw["source_ref"], "source_ref"),
        "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
        "source_snapshot_sha256": safe_sha256(raw["source_snapshot_sha256"], "source_snapshot_sha256"),
        "details": normalize_details(kind, raw["details"]),
    }
