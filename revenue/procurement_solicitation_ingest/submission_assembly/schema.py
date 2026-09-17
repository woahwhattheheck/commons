"""Strict schemas and normalization for procurement submission assembly."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

INPUT_SCHEMA = "procurement-submission-assembly/input/v1"
MANIFEST_SCHEMA = "procurement-submission-assembly/manifest/v1"
RECEIPT_SCHEMA = "procurement-submission-assembly/receipt/v1"
TRUTH_BOUNDARY = "OWNER_REVIEW_ONLY_NO_SUBMISSION_AUTHORITY"

READY = "ASSEMBLY_READY_FOR_OWNER_REVIEW"
MISSING = "HOLD_MISSING_REQUIRED_ARTIFACT"
CONFLICT = "HOLD_SOURCE_CONFLICT"
DEADLINE = "HOLD_DEADLINE_PASSED"
STATUSES = {READY, MISSING, CONFLICT, DEADLINE}

SOURCE_AUTHORITY = "BUYER_OFFICIAL_RETAINED_SOURCE"
SIGNATURE_REQUIREMENTS = {
    "NONE",
    "SIGNATURE_PRESENT_REQUIRED",
    "AUTHORIZED_SIGNATORY_REVIEW_REQUIRED",
    "NOTARIZATION_PRESENT_REQUIRED",
}
CERTIFICATION_REQUIREMENTS = {"NONE", "CERTIFICATION_PRESENT_REQUIRED"}
ATTESTATION_TYPES = {"SIGNATURE_PRESENT", "NOTARIZATION_PRESENT", "CERTIFICATION_PRESENT"}

AUTHORITY = {
    "buyer_contact_authorized": False,
    "portal_login_authorized": False,
    "portal_upload_authorized": False,
    "form_submit_authorized": False,
    "signature_action_authorized": False,
    "certification_action_authorized": False,
    "pricing_commitment_authorized": False,
    "proposal_submission_authorized": False,
    "contract_or_award_established": False,
    "payment_action_authorized": False,
    "receivable_established": False,
    "revenue_established": False,
}

MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
MAX_GENERATIONS = 128
MAX_SLOTS = 512
MAX_ARTIFACTS = 1024
MAX_TEXT = 512
MAX_PATH = 240

INPUT_KEYS = {
    "schema",
    "truth_boundary",
    "evaluated_at",
    "opportunity_id",
    "source_generations",
    "artifacts",
}
GENERATION_KEYS = {
    "source_id",
    "source_sha256",
    "source_authority",
    "observed_at",
    "sequence",
    "deadline_at",
    "slots",
}
SLOT_KEYS = {
    "slot_id",
    "required",
    "order",
    "file_name",
    "formats",
    "max_pages",
    "max_bytes",
    "signature_requirement",
    "certification_requirement",
    "attachment_class",
    "portal_field",
    "section_id",
}
ARTIFACT_KEYS = {
    "artifact_id",
    "slot_id",
    "path",
    "sha256",
    "format",
    "pages",
    "attestations",
}
ATTESTATION_KEYS = {"type", "artifact_sha256", "evidence_sha256"}


class AssemblyError(ValueError):
    pass


class ArtifactCustodyError(AssemblyError):
    pass


def _reject_constant(value: str):
    raise AssemblyError(f"non-finite JSON number forbidden: {value}")


def _reject_float(value: str):
    raise AssemblyError(f"floating JSON number forbidden: {value}")


def _no_dupes(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise AssemblyError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_strict_json(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, (bytes, bytearray)):
        raise AssemblyError("input bytes required")
    raw = bytes(raw)
    if len(raw) > MAX_JSON_BYTES:
        raise AssemblyError("input JSON too large")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_dupes,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssemblyError("invalid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise AssemblyError("top-level JSON object required")
    return value


def canon(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exact_keys(value: Any, keys: set[str], where: str):
    if not isinstance(value, dict) or set(value) != keys:
        raise AssemblyError(f"{where}: exact keys required")


def _text(value: Any, where: str, *, allow_empty: bool = False, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str) or len(value) > limit or (not value and not allow_empty):
        raise AssemblyError(f"{where}: invalid text")
    normalized = unicodedata.normalize("NFKC", value)
    if normalized != value:
        raise AssemblyError(f"{where}: text must already be NFKC-normalized")
    for ch in value:
        cat = unicodedata.category(ch)
        if cat in {"Cc", "Cf", "Cs"}:
            raise AssemblyError(f"{where}: control/format characters forbidden")
    return value


def _token(value: Any, where: str) -> str:
    value = _text(value, where, limit=160)
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:/-")
    if value[0] not in allowed or any(ch not in allowed for ch in value):
        raise AssemblyError(f"{where}: unsafe token")
    return value


def _sha(value: Any, where: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise AssemblyError(f"{where}: lowercase SHA-256 required")
    return value


def _int(value: Any, where: str, *, lo: int = 0, hi: int = 2**31 - 1, nullable: bool = False):
    if value is None and nullable:
        return None
    if type(value) is not int or not (lo <= value <= hi):
        raise AssemblyError(f"{where}: exact integer in range required")
    return value


def _bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise AssemblyError(f"{where}: exact boolean required")
    return value


def _timestamp(value: Any, where: str) -> tuple[str, datetime]:
    if not isinstance(value, str) or len(value) > 64:
        raise AssemblyError(f"{where}: timezone-aware timestamp required")
    text = value
    try:
        parse_text = text[:-1] + "+00:00" if text.endswith("Z") else text
        dt = datetime.fromisoformat(parse_text)
    except ValueError as exc:
        raise AssemblyError(f"{where}: invalid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise AssemblyError(f"{where}: timezone offset required")
    return text, dt.astimezone(timezone.utc)


def _relative_path(value: Any, where: str) -> str:
    value = _text(value, where, limit=MAX_PATH)
    if "\\" in value:
        raise AssemblyError(f"{where}: POSIX relative path required")
    p = PurePosixPath(value)
    if p.is_absolute() or not p.parts or any(part in {"", ".", ".."} for part in p.parts):
        raise AssemblyError(f"{where}: safe relative path required")
    return value


def _nullable_text(value: Any, where: str, *, limit: int = MAX_TEXT):
    if value is None:
        return None
    return _text(value, where, limit=limit)


def _normalize_slot(slot: Any, where: str) -> dict[str, Any]:
    _exact_keys(slot, SLOT_KEYS, where)
    slot_id = _token(slot["slot_id"], where + ".slot_id")
    required = _bool(slot["required"], where + ".required")
    order = _int(slot["order"], where + ".order", lo=1, hi=10000, nullable=True)
    file_name = _nullable_text(slot["file_name"], where + ".file_name", limit=180)
    if file_name is not None and ("/" in file_name or "\\" in file_name or file_name in {".", ".."}):
        raise AssemblyError(f"{where}.file_name: base filename only")
    formats = slot["formats"]
    if not isinstance(formats, list) or len(formats) > 32:
        raise AssemblyError(f"{where}.formats: list required")
    norm_formats = []
    for i, item in enumerate(formats):
        token = _token(item, f"{where}.formats[{i}]").lower()
        if token in norm_formats:
            raise AssemblyError(f"{where}.formats: duplicate")
        norm_formats.append(token)
    max_pages = _int(slot["max_pages"], where + ".max_pages", lo=1, hi=100000, nullable=True)
    max_bytes = _int(slot["max_bytes"], where + ".max_bytes", lo=1, hi=MAX_ARTIFACT_BYTES, nullable=True)
    signature_requirement = _text(slot["signature_requirement"], where + ".signature_requirement", limit=64)
    if signature_requirement not in SIGNATURE_REQUIREMENTS:
        raise AssemblyError(f"{where}.signature_requirement: invalid enum")
    certification_requirement = _text(slot["certification_requirement"], where + ".certification_requirement", limit=64)
    if certification_requirement not in CERTIFICATION_REQUIREMENTS:
        raise AssemblyError(f"{where}.certification_requirement: invalid enum")
    return {
        "slot_id": slot_id,
        "required": required,
        "order": order,
        "file_name": file_name,
        "formats": norm_formats,
        "max_pages": max_pages,
        "max_bytes": max_bytes,
        "signature_requirement": signature_requirement,
        "certification_requirement": certification_requirement,
        "attachment_class": _nullable_text(slot["attachment_class"], where + ".attachment_class", limit=96),
        "portal_field": _nullable_text(slot["portal_field"], where + ".portal_field", limit=128),
        "section_id": _text(slot["section_id"], where + ".section_id", limit=160),
    }


def _normalize_generation(generation: Any, where: str, opportunity_id: str, evaluated_utc: datetime) -> dict[str, Any]:
    _exact_keys(generation, GENERATION_KEYS, where)
    source_id = _token(generation["source_id"], where + ".source_id")
    source_sha = _sha(generation["source_sha256"], where + ".source_sha256")
    authority = _text(generation["source_authority"], where + ".source_authority", limit=64)
    if authority != SOURCE_AUTHORITY:
        raise AssemblyError(f"{where}.source_authority: buyer-official retained source required")
    observed_text, observed_utc = _timestamp(generation["observed_at"], where + ".observed_at")
    sequence = _int(generation["sequence"], where + ".sequence", lo=0, hi=10**9)
    deadline_text, deadline_utc = _timestamp(generation["deadline_at"], where + ".deadline_at")
    slots = generation["slots"]
    if not isinstance(slots, list) or len(slots) > MAX_SLOTS:
        raise AssemblyError(f"{where}.slots: bounded list required")
    normalized_slots = [_normalize_slot(slot, f"{where}.slots[{i}]") for i, slot in enumerate(slots)]
    return {
        "source_id": source_id,
        "source_sha256": source_sha,
        "source_authority": authority,
        "observed_at": observed_text,
        "_observed_utc": observed_utc,
        "sequence": sequence,
        "deadline_at": deadline_text,
        "_deadline_utc": deadline_utc,
        "slots": normalized_slots,
        "_future_source": observed_utc > evaluated_utc,
        "_opportunity_id": opportunity_id,
    }


def _normalize_attestation(value: Any, where: str, artifact_sha: str):
    _exact_keys(value, ATTESTATION_KEYS, where)
    kind = _text(value["type"], where + ".type", limit=64)
    if kind not in ATTESTATION_TYPES:
        raise AssemblyError(f"{where}.type: invalid enum")
    bound_sha = _sha(value["artifact_sha256"], where + ".artifact_sha256")
    evidence_sha = _sha(value["evidence_sha256"], where + ".evidence_sha256")
    if bound_sha != artifact_sha:
        raise AssemblyError(f"{where}: attestation bound to different artifact bytes")
    return {"type": kind, "artifact_sha256": bound_sha, "evidence_sha256": evidence_sha}


def _normalize_artifact(value: Any, where: str) -> dict[str, Any]:
    _exact_keys(value, ARTIFACT_KEYS, where)
    artifact_id = _token(value["artifact_id"], where + ".artifact_id")
    slot_id = _token(value["slot_id"], where + ".slot_id")
    path = _relative_path(value["path"], where + ".path")
    digest_value = _sha(value["sha256"], where + ".sha256")
    fmt = _token(value["format"], where + ".format").lower()
    pages = _int(value["pages"], where + ".pages", lo=1, hi=100000, nullable=True)
    attestations = value["attestations"]
    if not isinstance(attestations, list) or len(attestations) > 16:
        raise AssemblyError(f"{where}.attestations: bounded list required")
    norm_attestations = [_normalize_attestation(a, f"{where}.attestations[{i}]", digest_value) for i, a in enumerate(attestations)]
    kinds = [a["type"] for a in norm_attestations]
    if len(kinds) != len(set(kinds)):
        raise AssemblyError(f"{where}.attestations: duplicate type")
    return {
        "artifact_id": artifact_id,
        "slot_id": slot_id,
        "path": path,
        "sha256": digest_value,
        "format": fmt,
        "pages": pages,
        "attestations": norm_attestations,
    }


def normalize_input(raw: bytes) -> dict[str, Any]:
    value = load_strict_json(raw)
    _exact_keys(value, INPUT_KEYS, "input")
    if value["schema"] != INPUT_SCHEMA:
        raise AssemblyError("input.schema: unsupported")
    if value["truth_boundary"] != TRUTH_BOUNDARY:
        raise AssemblyError("input.truth_boundary: unsupported")
    evaluated_text, evaluated_utc = _timestamp(value["evaluated_at"], "input.evaluated_at")
    opportunity_id = _token(value["opportunity_id"], "input.opportunity_id")
    generations = value["source_generations"]
    if not isinstance(generations, list) or not generations or len(generations) > MAX_GENERATIONS:
        raise AssemblyError("input.source_generations: non-empty bounded list required")
    normalized_generations = [
        _normalize_generation(g, f"input.source_generations[{i}]", opportunity_id, evaluated_utc)
        for i, g in enumerate(generations)
    ]
    artifacts = value["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) > MAX_ARTIFACTS:
        raise AssemblyError("input.artifacts: bounded list required")
    normalized_artifacts = [_normalize_artifact(a, f"input.artifacts[{i}]") for i, a in enumerate(artifacts)]
    return {
        "schema": INPUT_SCHEMA,
        "truth_boundary": TRUTH_BOUNDARY,
        "evaluated_at": evaluated_text,
        "_evaluated_utc": evaluated_utc,
        "opportunity_id": opportunity_id,
        "source_generations": normalized_generations,
        "artifacts": normalized_artifacts,
    }
