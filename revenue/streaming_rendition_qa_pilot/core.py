from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Iterable

SCOPE_SCHEMA = "streaming-rendition-qa-pilot.scope/v1"
PROSPECT_SCHEMA = "streaming-rendition-qa-pilot.prospect/v1"
REPORT_SCHEMA = "streaming-rendition-qa-pilot.report/v1"
PROOF_SCHEMA = "streaming-rendition-qa-pilot.proof/v1"
PRODUCT = "Streaming Rendition QA Pilot"
VERSION = "1.0.0"
DIAGNOSTIC_PRICE_CENTS = 250_000
INTEGRATION_PRICE_CENTS = 750_000
MAX_ASSETS = 250
MAX_PROSPECTS = 10
UPSTREAM_OPERATION = "paramount-streaming-rendition-release-gate-01"
UPSTREAM_PR = 13885
UPSTREAM_FIXTURE_SHA256 = "27d34cc0574f3210e3e42c575f3615be9bd6d056f6f51576271bc7b6ecc79441"
UPSTREAM_PROJECTION_SHA256 = "e510ed89458a54d32a6cda0da425d92612ed40783fb311c2db86d3ad33f889c2"

FAULT_CLASSES = (
    "MISSING_RENDITION",
    "CODEC_PROFILE_MISMATCH",
    "SEGMENT_DISCONTINUITY",
    "CAPTION_AUDIO_ALIGNMENT_GAP",
    "DRM_REFERENCE_MISMATCH",
    "CHECKSUM_ORPHAN_ARTIFACT",
    "PUBLICATION_WINDOW_CONFLICT",
)
SUPPORTED_FORMATS = ("HLS", "DASH", "CMAF_METADATA")
PUBLIC_EVIDENCE_TAGS = (
    "HLS_PUBLIC_EVIDENCE",
    "DASH_PUBLIC_EVIDENCE",
    "MULTI_RENDITION_PUBLIC_EVIDENCE",
    "LIVE_VOD_PUBLIC_EVIDENCE",
)
HOLD_REASONS = (
    "ASSET_LIMIT_EXCEEDED",
    "MEDIA_BYTES_REQUIRED",
    "DRM_SECRET_REQUIRED",
    "LIVE_PROVIDER_ACCESS_REQUIRED",
    "UNSUPPORTED_FAULT_CLASS",
    "UNSUPPORTED_FORMAT",
    "INCOMPLETE_EXPORT_DESCRIPTOR",
    "SCOPE_ID_CONFLICT",
)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_URL_RE = re.compile(r"^https://[^\s]{1,500}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SECRET_MARKERS = ("password", "secret", "api_key", "apikey", "bearer ", "token=", "private_key", "drm_key")


class PilotError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def sha256_hex(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def parse_json_strict(text: str) -> Any:
    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise PilotError(f"duplicate JSON key {key!r}")
            out[key] = value
        return out
    def reject_constant(value: str) -> Any:
        raise PilotError(f"non-finite JSON number {value!r} is forbidden")
    try:
        return json.loads(text, object_pairs_hook=pairs_hook, parse_constant=reject_constant)
    except json.JSONDecodeError as exc:
        raise PilotError(f"invalid JSON: {exc.msg}") from exc


def _exact(raw: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PilotError(f"{label} must be object")
    if set(raw) != keys:
        raise PilotError(f"{label} keys mismatch missing={sorted(keys-set(raw))} extra={sorted(set(raw)-keys)}")
    return raw


def _text(v: Any, field: str, *, max_len: int = 128, opaque: bool = False) -> str:
    if not isinstance(v, str) or not v or len(v) > max_len:
        raise PilotError(f"{field} must be non-empty string <= {max_len}")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in v):
        raise PilotError(f"{field} contains control character")
    lower = v.lower()
    if any(m in lower for m in _SECRET_MARKERS):
        raise PilotError(f"{field} looks secret-shaped")
    if opaque and (not _ID_RE.fullmatch(v) or "@" in v or "://" in v):
        raise PilotError(f"{field} must be opaque identifier")
    return v


def _sha(v: Any, field: str) -> str:
    v = _text(v, field, max_len=64).lower()
    if not _SHA_RE.fullmatch(v):
        raise PilotError(f"{field} must be lowercase SHA-256")
    return v


def _bool(v: Any, field: str) -> bool:
    if type(v) is not bool:
        raise PilotError(f"{field} must be bool")
    return v


def _int(v: Any, field: str, lo: int, hi: int) -> int:
    if type(v) is not int or not lo <= v <= hi:
        raise PilotError(f"{field} must be integer {lo}..{hi}")
    return v


def _utc(v: Any, field: str) -> str:
    v = _text(v, field, max_len=20)
    if not _UTC_RE.fullmatch(v):
        raise PilotError(f"{field} must be canonical whole-second UTC")
    try:
        dt = datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise PilotError(f"{field} invalid") from exc
    if dt.strftime("%Y-%m-%dT%H:%M:%SZ") != v:
        raise PilotError(f"{field} non-canonical")
    return v


def _unique_tokens(values: Any, field: str, *, nonempty: bool = True) -> list[str]:
    if not isinstance(values, list) or (nonempty and not values):
        raise PilotError(f"{field} must be {'non-empty ' if nonempty else ''}array")
    out = []
    for i, value in enumerate(values):
        value = _text(value, f"{field}[{i}]", max_len=80)
        if not re.fullmatch(r"^[A-Z][A-Z0-9_]{1,79}$", value):
            raise PilotError(f"{field}[{i}] malformed controlled token")
        out.append(value)
    if len(out) != len(set(out)):
        raise PilotError(f"{field} duplicates")
    return sorted(out)


def _unique_enum(values: Any, allowed: Iterable[str], field: str, *, nonempty: bool = True) -> list[str]:
    out = _unique_tokens(values, field, nonempty=nonempty)
    unknown = sorted(set(out) - set(allowed))
    if unknown:
        raise PilotError(f"{field} unsupported values {unknown!r}")
    return out


def validate_scope(raw: dict[str, Any]) -> dict[str, Any]:
    raw = _exact(raw, {
        "schema", "pilot_id", "export_ref", "export_sha256", "export_descriptor_complete",
        "asset_count", "metadata_only", "requires_media_bytes", "requires_drm_secrets",
        "requires_live_provider_access", "formats", "fault_classes", "captured_at_utc",
        "source_ref", "source_sha256",
    }, "scope")
    if raw["schema"] != SCOPE_SCHEMA:
        raise PilotError("unsupported scope schema")
    return {
        "schema": SCOPE_SCHEMA,
        "pilot_id": _text(raw["pilot_id"], "pilot_id", opaque=True),
        "export_ref": _text(raw["export_ref"], "export_ref", opaque=True),
        "export_sha256": _sha(raw["export_sha256"], "export_sha256"),
        "export_descriptor_complete": _bool(raw["export_descriptor_complete"], "export_descriptor_complete"),
        "asset_count": _int(raw["asset_count"], "asset_count", 0, 1_000_000),
        "metadata_only": _bool(raw["metadata_only"], "metadata_only"),
        "requires_media_bytes": _bool(raw["requires_media_bytes"], "requires_media_bytes"),
        "requires_drm_secrets": _bool(raw["requires_drm_secrets"], "requires_drm_secrets"),
        "requires_live_provider_access": _bool(raw["requires_live_provider_access"], "requires_live_provider_access"),
        "formats": _unique_tokens(raw["formats"], "formats"),
        "fault_classes": _unique_tokens(raw["fault_classes"], "fault_classes"),
        "captured_at_utc": _utc(raw["captured_at_utc"], "captured_at_utc"),
        "source_ref": _text(raw["source_ref"], "source_ref", opaque=True),
        "source_sha256": _sha(raw["source_sha256"], "source_sha256"),
    }


def qualify_scope(raw: dict[str, Any]) -> dict[str, Any]:
    scope = validate_scope(raw)
    holds: list[str] = []
    if scope["asset_count"] > MAX_ASSETS:
        holds.append("ASSET_LIMIT_EXCEEDED")
    if not scope["metadata_only"] or scope["requires_media_bytes"]:
        holds.append("MEDIA_BYTES_REQUIRED")
    if scope["requires_drm_secrets"]:
        holds.append("DRM_SECRET_REQUIRED")
    if scope["requires_live_provider_access"]:
        holds.append("LIVE_PROVIDER_ACCESS_REQUIRED")
    if not scope["export_descriptor_complete"]:
        holds.append("INCOMPLETE_EXPORT_DESCRIPTOR")
    if set(scope["fault_classes"]) - set(FAULT_CLASSES):
        holds.append("UNSUPPORTED_FAULT_CLASS")
    if set(scope["formats"]) - set(SUPPORTED_FORMATS):
        holds.append("UNSUPPORTED_FORMAT")
    state = "QUALIFIED_FOR_OWNER_OFFER_REVIEW" if not holds else "HOLD"
    return {"scope": scope, "state": state, "hold_reasons": sorted(set(holds))}


def validate_prospect(raw: dict[str, Any]) -> dict[str, Any]:
    raw = _exact(raw, {
        "schema", "dedupe_key", "organization", "public_evidence_tags",
        "source_url", "source_sha256", "observed_at_utc",
    }, "prospect")
    if raw["schema"] != PROSPECT_SCHEMA:
        raise PilotError("unsupported prospect schema")
    url = _text(raw["source_url"], "source_url", max_len=512)
    if not _URL_RE.fullmatch(url):
        raise PilotError("source_url must be public https URL")
    org = _text(raw["organization"], "organization", max_len=120)
    if "@" in org or "://" in org:
        raise PilotError("organization must not be contact/URL data")
    return {
        "schema": PROSPECT_SCHEMA,
        "dedupe_key": _text(raw["dedupe_key"], "dedupe_key", opaque=True),
        "organization": org,
        "public_evidence_tags": _unique_enum(raw["public_evidence_tags"], PUBLIC_EVIDENCE_TAGS, "public_evidence_tags"),
        "source_url": url,
        "source_sha256": _sha(raw["source_sha256"], "source_sha256"),
        "observed_at_utc": _utc(raw["observed_at_utc"], "observed_at_utc"),
    }


def qualify_prospects(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(rows)
    if len(rows) > MAX_PROSPECTS:
        raise PilotError(f"prospect count exceeds {MAX_PROSPECTS}")
    seen: set[str] = set()
    out = []
    for raw in rows:
        p = validate_prospect(raw)
        if p["dedupe_key"] in seen:
            raise PilotError(f"duplicate prospect dedupe_key {p['dedupe_key']!r}")
        seen.add(p["dedupe_key"])
        out.append({**p, "state": "RESEARCH_READY", "contact_authority": False, "buyer_intent_inferred": False})
    return sorted(out, key=lambda r: (r["organization"].lower(), r["dedupe_key"]))


def synthetic_proof() -> dict[str, Any]:
    assets = []
    matrix = []
    for idx, fault in enumerate(FAULT_CLASSES):
        clean_id = f"proof-clean-{idx+1:02d}"
        fault_id = f"proof-fault-{idx+1:02d}"
        extra_id = f"proof-replay-{idx+1:02d}"
        assets.extend([
            {"asset_id": clean_id, "expected_state": "RELEASE_READY", "fault_class": None},
            {"asset_id": fault_id, "expected_state": "HOLD", "fault_class": fault},
            {"asset_id": extra_id, "expected_state": "RELEASE_READY", "fault_class": None},
        ])
        matrix.append({"fault_class": fault, "clean_asset_id": clean_id, "defect_asset_id": fault_id})
    payload = {
        "schema": PROOF_SCHEMA,
        "upstream": {
            "operation": UPSTREAM_OPERATION,
            "merged_pr": UPSTREAM_PR,
            "canonical_fixture_sha256": UPSTREAM_FIXTURE_SHA256,
            "canonical_projection_sha256": UPSTREAM_PROJECTION_SHA256,
            "canonical_acceptance": {"total": 168, "release_ready": 140, "hold": 28, "holds_per_fault_class": 4},
        },
        "assets": assets,
        "fault_matrix": matrix,
        "authority": "SYNTHETIC_BUYER_SAFE_PROOF_ONLY",
    }
    payload["proof_sha256"] = sha256_hex(canonical_json(payload))
    return payload


def commercial_sheet(scope_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "streaming-rendition-qa-pilot.commercial-sheet/v1",
        "pilot_state": "CANDIDATE_SCOPE",
        "qualification_state": scope_result["state"],
        "diagnostic_reference": {
            "currency": "USD", "price_cents": DIAGNOSTIC_PRICE_CENTS,
            "max_assets": MAX_ASSETS, "stage": "OWNER_OFFER_REVIEW_ONLY",
        },
        "integration_reference": {
            "currency": "USD", "price_cents": INTEGRATION_PRICE_CENTS,
            "stage": "OPTIONAL_AFTER_PAID_DIAGNOSTIC",
        },
        "included": [
            "sanitized metadata export qualification",
            "seven-class rendition diagnostic projection",
            "deterministic JSON diagnostic packet",
            "Markdown summary and defect inventory",
            "evidence/proof receipt",
            "integration mapping/HOLD list",
        ],
        "excluded": [
            "media bytes", "DRM secrets", "rights determination", "transcoding",
            "CDN mutation", "publishing", "provider credentials", "production actions",
        ],
        "artifact_acceptance": [
            "input scope validates and binds exact sanitized export digest",
            "diagnostic artifacts are deterministic and receipt-verifiable",
            "all detected HOLDs are enumerated without claiming media release authority",
        ],
        "commercial_authority": {
            "buyer_accepted": False, "contract_signed": False, "payment_received": False,
            "revenue_recognized": False, "deployment_authorized": False,
        },
    }


def build_report(scope_raw: dict[str, Any], prospects_raw: Iterable[dict[str, Any]], *, evaluated_at_utc: str) -> dict[str, Any]:
    evaluated_at_utc = _utc(evaluated_at_utc, "evaluated_at_utc")
    qualified = qualify_scope(scope_raw)
    prospects = qualify_prospects(prospects_raw)
    proof = synthetic_proof()
    report = {
        "schema": REPORT_SCHEMA,
        "product": PRODUCT,
        "version": VERSION,
        "evaluated_at_utc": evaluated_at_utc,
        "scope_sha256": sha256_hex(canonical_json(qualified["scope"])),
        "scope_result": qualified,
        "commercial_sheet": commercial_sheet(qualified),
        "synthetic_proof": proof,
        "prospects": prospects,
        "authority_map": {
            "prospect_contact": False, "provider_access": False, "media_byte_access": False,
            "drm_secret_access": False, "rights_determination": False, "transcoding": False,
            "cdn_mutation": False, "publishing": False, "deployment": False,
            "buyer_acceptance": False, "contract_signature": False, "payment_action": False,
            "cash_or_revenue_recognition": False,
        },
    }
    report["receipt_sha256"] = sha256_hex(canonical_json(report))
    return report


def verify_report(report: dict[str, Any], scope_raw: dict[str, Any], prospects_raw: Iterable[dict[str, Any]]) -> bool:
    if not isinstance(report, dict) or report.get("schema") != REPORT_SCHEMA:
        return False
    receipt = report.get("receipt_sha256")
    if not isinstance(receipt, str) or not _SHA_RE.fullmatch(receipt):
        return False
    body = dict(report); body.pop("receipt_sha256", None)
    if sha256_hex(canonical_json(body)) != receipt:
        return False
    try:
        rebuilt = build_report(scope_raw, prospects_raw, evaluated_at_utc=report["evaluated_at_utc"])
    except (PilotError, KeyError, TypeError, ValueError):
        return False
    return canonical_json(rebuilt) == canonical_json(report)
