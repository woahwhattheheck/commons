from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Iterable

INPUT_SCHEMA = "stockton-lims-qualification/input-v1"
REPORT_SCHEMA = "stockton-lims-qualification/report-v1"
MAX_JSON_BYTES = 1_000_000
MAX_GATES = 128
MAX_SCOPE_IDS = 16

OPPORTUNITY_ID = "stockton-pur-27-007"
RFP_FILENAME = "PUR_27-007_Final_.pdf"
WORKBOOK_FILENAME = "Requirements.xlsx"
QUESTION_DEADLINE = "2026-09-24T21:00:00Z"
PROPOSAL_DEADLINE = "2026-10-08T21:00:00Z"

SOURCE_IDS = ("RFP_PDF", "REQUIREMENTS_XLSX")
SOURCE_STATUSES = {"BOUND", "METADATA_ONLY", "SOURCE_REQUIRED", "CONFLICT"}
EVIDENCE_STATUSES = {"VERIFIED", "MISSING", "CONFLICT", "NOT_APPLICABLE"}
OPPORTUNITY_STATUSES = {"OPEN", "CANCELLED", "CLOSED"}

MANDATORY_PRIME_GATES = (
    "CA_APPLICABLE_LICENSING",
    "THREE_RECENT_SIMILAR_REFERENCES",
    "PROPOSED_TEAM_SHARED_PROJECTS",
    "FINANCIAL_CAPACITY_CERTIFICATION",
    "CGL_2M",
    "AUTO_1M",
    "WORKERS_COMP",
    "EMPLOYERS_LIABILITY_1M",
    "CYBER_2M",
    "TECH_EO_2M",
    "LIMS_CORE_FUNCTIONALITY",
    "IMPLEMENTATION_PLAN",
    "CIWQS_ELECTRONIC_DELIVERABLE",
    "SCADA_AND_CONTRACT_LAB_INTEGRATION",
    "API_INTEGRATION",
    "TEN_YEAR_RETENTION",
    "AUDIT_AND_CHANGE_TRACKING",
    "DISASTER_RECOVERY",
    "AZURE_AD_RESPONSE",
    "SECURITY_PRIVACY_RESPONSE",
    "TRAINING_AND_SUPPORT",
    "COVER_AND_EXECUTIVE_SUMMARY",
    "FULL_SCOPE_RESPONSE",
    "ATTACHMENT_A",
    "ATTACHMENT_B",
    "ATTACHMENT_C_NOTARIZED",
    "ATTACHMENT_D",
    "ATTACHMENT_E",
    "ATTACHMENT_G",
    "ATTACHMENT_H",
    "ATTACHMENT_I",
    "SIGNED_ADDENDA",
    "SEPARATE_PRICE_FILE",
    "AUTHORIZED_SIGNATURE",
    "PROPOSAL_VALID_120_DAYS",
)

SPECIALIST_SCOPE_IDS = {
    "CIWQS_REPORTING_VALIDATION",
    "SCADA_CONTRACT_LAB_ADAPTERS",
    "MIGRATION_RECONCILIATION",
    "QC_ACCEPTANCE_TESTS",
    "TRAINING_VALIDATION",
}

_SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class QualificationError(ValueError):
    pass


def _pairs_no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise QualificationError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def loads_strict(raw: bytes | str) -> Any:
    if isinstance(raw, bytes):
        if len(raw) > MAX_JSON_BYTES:
            raise QualificationError("JSON input exceeds size limit")
        try:
            text = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise QualificationError("JSON must be strict UTF-8") from exc
    elif isinstance(raw, str):
        if len(raw.encode("utf-8")) > MAX_JSON_BYTES:
            raise QualificationError("JSON input exceeds size limit")
        text = raw
    else:
        raise QualificationError("JSON input must be bytes or str")
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_no_dupes,
            parse_constant=lambda token: (_ for _ in ()).throw(
                QualificationError(f"non-finite JSON number: {token}")
            ),
        )
    except QualificationError:
        raise
    except json.JSONDecodeError as exc:
        raise QualificationError("invalid JSON") from exc


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
        raise QualificationError("value is not canonical JSON") from exc


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _exact_keys(obj: Any, required: Iterable[str], optional: Iterable[str] = ()) -> dict[str, Any]:
    if type(obj) is not dict:
        raise QualificationError("expected object")
    required_set = set(required)
    allowed = required_set | set(optional)
    keys = set(obj)
    missing = sorted(required_set - keys)
    unknown = sorted(keys - allowed)
    if missing:
        raise QualificationError(f"missing keys: {','.join(missing)}")
    if unknown:
        raise QualificationError(f"unknown keys: {','.join(unknown)}")
    return obj


def _list(value: Any, *, minimum: int = 0, maximum: int, name: str) -> list[Any]:
    if type(value) is not list:
        raise QualificationError(f"{name} must be a list")
    if not minimum <= len(value) <= maximum:
        raise QualificationError(f"{name} length out of bounds")
    return value


def _safe_ref(value: Any, *, name: str) -> str:
    if type(value) is not str or not _SAFE_REF.fullmatch(value):
        raise QualificationError(f"{name} must be an opaque safe reference")
    if "@" in value or "/" in value or "\\" in value or "://" in value:
        raise QualificationError(f"{name} must not contain contact, URL, or path data")
    return value


def _digest(value: Any, *, name: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise QualificationError(f"{name} must be lowercase sha256")
    return value


def _canonical_time(value: Any, *, name: str) -> str:
    if type(value) is not str or len(value) != 20 or not value.endswith("Z"):
        raise QualificationError(f"{name} must be canonical UTC seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise QualificationError(f"{name} must be canonical UTC seconds") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise QualificationError(f"{name} must be canonical UTC seconds")
    return value


def dt(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def utc_now_string() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_source(row: Any) -> dict[str, Any]:
    row = _exact_keys(
        row,
        ["source_id", "status", "filename", "sha256", "size_bytes", "captured_at"],
    )
    source_id = row["source_id"]
    if source_id not in SOURCE_IDS:
        raise QualificationError("unknown source_id")
    expected_filename = RFP_FILENAME if source_id == "RFP_PDF" else WORKBOOK_FILENAME
    if row["filename"] != expected_filename:
        raise QualificationError(f"{source_id} filename must be {expected_filename}")
    status = row["status"]
    if status not in SOURCE_STATUSES:
        raise QualificationError("invalid source status")
    if status == "BOUND":
        digest = _digest(row["sha256"], name=f"{source_id}.sha256")
        if type(row["size_bytes"]) is not int or isinstance(row["size_bytes"], bool) or row["size_bytes"] <= 0:
            raise QualificationError(f"{source_id}.size_bytes must be positive integer")
        captured_at = _canonical_time(row["captured_at"], name=f"{source_id}.captured_at")
    else:
        if row["sha256"] is not None or row["size_bytes"] is not None:
            raise QualificationError(f"{source_id} unbound source must not carry digest or size")
        digest = None
        captured_at = None
        if row["captured_at"] is not None:
            captured_at = _canonical_time(row["captured_at"], name=f"{source_id}.captured_at")
    return {
        "source_id": source_id,
        "status": status,
        "filename": expected_filename,
        "sha256": digest,
        "size_bytes": row["size_bytes"],
        "captured_at": captured_at,
    }


def _validate_evidence(row: Any, *, name: str) -> dict[str, Any]:
    row = _exact_keys(
        row,
        ["status", "artifact_id", "sha256", "observed_at", "valid_until", "authority_ref"],
    )
    status = row["status"]
    if status not in EVIDENCE_STATUSES:
        raise QualificationError(f"{name}.status invalid")
    if status == "VERIFIED":
        artifact_id = _safe_ref(row["artifact_id"], name=f"{name}.artifact_id")
        digest = _digest(row["sha256"], name=f"{name}.sha256")
        observed_at = _canonical_time(row["observed_at"], name=f"{name}.observed_at")
        valid_until = _canonical_time(row["valid_until"], name=f"{name}.valid_until")
        authority_ref = _safe_ref(row["authority_ref"], name=f"{name}.authority_ref")
        if dt(valid_until) < dt(observed_at):
            raise QualificationError(f"{name} expires before observation")
    else:
        if any(row[key] is not None for key in ["artifact_id", "sha256", "observed_at", "valid_until", "authority_ref"]):
            raise QualificationError(f"{name} non-verified evidence must have null artifact fields")
        artifact_id = digest = observed_at = valid_until = authority_ref = None
    return {
        "status": status,
        "artifact_id": artifact_id,
        "sha256": digest,
        "observed_at": observed_at,
        "valid_until": valid_until,
        "authority_ref": authority_ref,
    }


def validate_packet(packet: Any) -> dict[str, Any]:
    packet = _exact_keys(
        packet,
        [
            "schema",
            "opportunity_id",
            "opportunity_status",
            "status_evidence",
            "sources",
            "addenda_census",
            "gates",
            "specialist_seam",
        ],
    )
    if packet["schema"] != INPUT_SCHEMA:
        raise QualificationError("unsupported input schema")
    if packet["opportunity_id"] != OPPORTUNITY_ID:
        raise QualificationError("unexpected opportunity_id")
    opportunity_status = packet["opportunity_status"]
    if opportunity_status not in OPPORTUNITY_STATUSES:
        raise QualificationError("invalid opportunity_status")
    status_evidence = _validate_evidence(packet["status_evidence"], name="status_evidence")

    source_rows = _list(packet["sources"], minimum=2, maximum=2, name="sources")
    sources: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for row in source_rows:
        parsed = _validate_source(row)
        if parsed["source_id"] in seen_sources:
            raise QualificationError("duplicate source_id")
        seen_sources.add(parsed["source_id"])
        sources.append(parsed)
    if seen_sources != set(SOURCE_IDS):
        raise QualificationError("both required sources must be present")

    addenda_census = _validate_evidence(packet["addenda_census"], name="addenda_census")

    gate_rows = _list(packet["gates"], maximum=MAX_GATES, name="gates")
    gates: list[dict[str, Any]] = []
    seen_gates: set[str] = set()
    allowed_gates = set(MANDATORY_PRIME_GATES)
    for row in gate_rows:
        row = _exact_keys(row, ["gate_id", "evidence"])
        gate_id = row["gate_id"]
        if gate_id not in allowed_gates:
            raise QualificationError(f"unknown gate_id: {gate_id}")
        if gate_id in seen_gates:
            raise QualificationError(f"duplicate gate_id: {gate_id}")
        seen_gates.add(gate_id)
        gates.append({"gate_id": gate_id, "evidence": _validate_evidence(row["evidence"], name=f"gate.{gate_id}")})

    seam = _exact_keys(packet["specialist_seam"], ["scope_ids", "evidence", "proposed_fee_usd"])
    scope_ids = _list(seam["scope_ids"], maximum=MAX_SCOPE_IDS, name="specialist_seam.scope_ids")
    if len(scope_ids) != len(set(scope_ids)):
        raise QualificationError("duplicate specialist scope id")
    for scope_id in scope_ids:
        if scope_id not in SPECIALIST_SCOPE_IDS:
            raise QualificationError(f"unknown specialist scope id: {scope_id}")
    fee = seam["proposed_fee_usd"]
    if fee is not None and (type(fee) is not int or isinstance(fee, bool) or fee <= 0 or fee > 10_000_000):
        raise QualificationError("proposed_fee_usd must be a bounded positive integer or null")
    specialist_seam = {
        "scope_ids": sorted(scope_ids),
        "evidence": _validate_evidence(seam["evidence"], name="specialist_seam.evidence"),
        "proposed_fee_usd": fee,
    }

    return {
        "schema": INPUT_SCHEMA,
        "opportunity_id": OPPORTUNITY_ID,
        "opportunity_status": opportunity_status,
        "status_evidence": status_evidence,
        "sources": sorted(sources, key=lambda row: row["source_id"]),
        "addenda_census": addenda_census,
        "gates": sorted(gates, key=lambda row: row["gate_id"]),
        "specialist_seam": specialist_seam,
    }
