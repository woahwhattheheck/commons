"""Fail-closed current and historical qualification surface for DCSA Innovation Call #01."""

from __future__ import annotations

import datetime as dt
import hmac
import os
import stat
from pathlib import Path
from typing import Any, Dict

from .contracts import (
    AUTHORITY_SCHEMA,
    CANDIDATE_SCHEMA,
    FLOOR_SCHEMA,
    GENERAL_SOLICITATION_ID,
    CONCEPT_DEADLINE,
    MAX_CURRENT_REPORT_AGE,
    QUESTION_DEADLINE,
    NOTICE_ID,
    REPORT_SCHEMA,
    REQUIRED_CAPABILITIES,
    REQUIRED_DOCUMENTS,
    SOURCE_SCHEMA,
    _sha256,
    authority_sha256,
    normalize_authority,
    normalize_candidate,
    normalize_floor,
    normalize_source_ledger,
)
from .decision import _compile_at
from .strict import (
    CustodyError,
    ValidationError,
    canonical_json_bytes,
    format_utc,
    parse_utc,
    read_bounded_regular_file,
    require_bool,
    require_exact_keys,
    require_hex64,
    strict_json_loads,
)

HOST_ROOT = Path("/etc/commons/dcsa-innovation-call-01")
HOST_AUTHORITY_PATH = HOST_ROOT / "authority.json"
HOST_FLOOR_PATH = HOST_ROOT / "authority-floor.json"

def _read_fixed_host_trust(path: Path) -> bytes:
    if os.name != "posix":
        raise CustodyError("current host authority is supported only on the pinned POSIX boundary")
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise CustodyError("fixed host trust file is unavailable") from exc
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise CustodyError("fixed host trust file must be one regular-file generation")
    if before.st_uid != 0:
        raise CustodyError("fixed host trust file must be root-owned")
    if stat.S_IMODE(before.st_mode) & 0o022:
        raise CustodyError("fixed host trust file must not be group/other writable")
    data = read_bounded_regular_file(path)
    try:
        after = os.lstat(path)
    except OSError as exc:
        raise CustodyError("fixed host trust file disappeared after capture") from exc
    if (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_nlink,
        before.st_uid,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_nlink,
        after.st_uid,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise CustodyError("fixed host trust file generation changed during capture")
    return data


def _load_fixed_host_authority() -> tuple[Any | None, Any | None]:
    authority_value: Any | None = None
    floor_value: Any | None = None
    try:
        authority_value = strict_json_loads(_read_fixed_host_trust(HOST_AUTHORITY_PATH))
        floor_value = strict_json_loads(_read_fixed_host_trust(HOST_FLOOR_PATH))
    except (CustodyError, ValidationError):
        authority_value = None
        floor_value = None
    return authority_value, floor_value


def compile_current(candidate_bytes: bytes, source_bytes: bytes) -> Dict[str, Any]:
    """Compile a current owner-review disposition using fixed host authority paths."""

    candidate = strict_json_loads(candidate_bytes)
    source = strict_json_loads(source_bytes)
    authority_value, floor_value = _load_fixed_host_authority()
    return _compile_at(
        candidate,
        source,
        authority_value,
        floor_value,
        now=dt.datetime.now(dt.timezone.utc),
        mode="CURRENT",
    )


def compile_historical(
    candidate_bytes: bytes,
    source_bytes: bytes,
    authority_bytes: bytes,
    floor_bytes: bytes,
    *,
    as_of: str,
) -> Dict[str, Any]:
    """Reconstruct historical integrity without minting current readiness."""

    return _compile_at(
        strict_json_loads(candidate_bytes),
        strict_json_loads(source_bytes),
        strict_json_loads(authority_bytes),
        strict_json_loads(floor_bytes),
        now=parse_utc(as_of, field="historical as_of"),
        mode="HISTORICAL_INTEGRITY_ONLY",
    )


def verify_report_shape(report_value: Any) -> Dict[str, Any]:
    report = require_exact_keys(
        report_value,
        {
            "schema",
            "mode",
            "evaluated_at",
            "notice_id",
            "general_solicitation_id",
            "subject_id",
            "operation_id",
            "concept_title",
            "state",
            "historical_route_projection",
            "blockers",
            "question_window",
            "question_deadline",
            "live_qa_at",
            "concept_deadline",
            "estimated_start_date",
            "source_generation_sha256",
            "evidence_summary",
            "external_contact_authorized",
            "external_submission_authorized",
            "signature_authorized",
            "pricing_commitment_authorized",
            "clearance_claim_authorized",
            "award_or_revenue_claimed",
            "current_work_authorized",
            "receipt_sha256",
        },
        field="qualification report",
    )
    if report["schema"] != REPORT_SCHEMA:
        raise ValidationError("qualification report schema is unsupported")
    digest = require_hex64(report["receipt_sha256"], field="report receipt_sha256")
    expected = _sha256(canonical_json_bytes({**dict(report), "receipt_sha256": ""}))
    if not hmac.compare_digest(digest, expected):
        raise ValidationError("qualification report receipt does not verify")
    for key in (
        "external_contact_authorized",
        "external_submission_authorized",
        "signature_authorized",
        "pricing_commitment_authorized",
        "clearance_claim_authorized",
        "award_or_revenue_claimed",
    ):
        if require_bool(report[key], field=key):
            raise ValidationError(f"qualification report illegally grants {key}")
    return dict(report)


def verify_current(candidate_bytes: bytes, source_bytes: bytes, report_bytes: bytes) -> bool:
    retained = verify_report_shape(strict_json_loads(report_bytes))
    if retained["mode"] != "CURRENT":
        return False
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    retained_at = parse_utc(retained["evaluated_at"], field="report evaluated_at")
    if retained_at > now or now - retained_at > MAX_CURRENT_REPORT_AGE:
        return False
    candidate = strict_json_loads(candidate_bytes)
    source = strict_json_loads(source_bytes)
    authority_value, floor_value = _load_fixed_host_authority()
    historical_rebuild = _compile_at(
        candidate,
        source,
        authority_value,
        floor_value,
        now=retained_at,
        mode="CURRENT",
    )
    if not hmac.compare_digest(
        canonical_json_bytes(retained), canonical_json_bytes(historical_rebuild)
    ):
        return False
    fresh = _compile_at(
        candidate,
        source,
        authority_value,
        floor_value,
        now=now,
        mode="CURRENT",
    )
    retained_semantics = dict(retained)
    fresh_semantics = dict(fresh)
    for value in (retained_semantics, fresh_semantics):
        value.pop("evaluated_at", None)
        value.pop("receipt_sha256", None)
    return hmac.compare_digest(
        canonical_json_bytes(retained_semantics), canonical_json_bytes(fresh_semantics)
    )


def verify_historical(
    candidate_bytes: bytes,
    source_bytes: bytes,
    authority_bytes: bytes,
    floor_bytes: bytes,
    report_bytes: bytes,
    *,
    as_of: str,
) -> bool:
    retained = verify_report_shape(strict_json_loads(report_bytes))
    if retained["mode"] != "HISTORICAL_INTEGRITY_ONLY":
        return False
    fresh = compile_historical(
        candidate_bytes,
        source_bytes,
        authority_bytes,
        floor_bytes,
        as_of=as_of,
    )
    return hmac.compare_digest(canonical_json_bytes(retained), canonical_json_bytes(fresh))
