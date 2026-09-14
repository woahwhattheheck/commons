#!/usr/bin/env python3
"""Atomic, privacy-minimized outreach claims backed by GitHub Contents API.

The module is intentionally dependency-free.  It does not send outreach.  It only
coordinates who is allowed to contact a target and records a digest-only receipt
when contact occurs.
"""

from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import email.utils
import hashlib
import hmac
import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Mapping, MutableMapping, Optional

SCHEMA = "outreach-claim-fence/v1"
DEFAULT_BRANCH = "coordination/outreach-claims-v1"
DEFAULT_ROOT = ".coordination/outreach-claims/v1"
API_VERSION = "2022-11-28"
MIN_LEASE_SECONDS = 60
MAX_LEASE_SECONDS = 7 * 24 * 60 * 60
MIN_COOLDOWN_SECONDS = 5 * 60
MAX_COOLDOWN_SECONDS = 30 * 24 * 60 * 60
MAX_RETRIES = 4
_STATES = {"ACTIVE", "CONTACTED", "RELEASED"}
_TARGET_KINDS = {"email", "domain", "github", "slack", "custom"}
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_WEAK_COMPENSATION_PATHS = {
    "none",
    "n/a",
    "na",
    "free",
    "unknown",
    "tbd",
    "no payment",
    "unpaid",
}


class ClaimFenceError(Exception):
    """Base class for safe, user-facing failures."""

    exit_code = 6

    def __init__(self, message: str, *, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = dict(details or {})

    def safe_payload(self) -> Dict[str, Any]:
        return {
            "ok": False,
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(ClaimFenceError):
    exit_code = 2


class ClaimConflict(ClaimFenceError):
    exit_code = 3


class ClaimNotFound(ClaimFenceError):
    exit_code = 4


class OwnershipError(ClaimFenceError):
    exit_code = 5


class RemoteError(ClaimFenceError):
    exit_code = 6


class ProtocolError(ClaimFenceError):
    exit_code = 7


class _CasConflict(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class UrllibTransport:
    """Minimal HTTP transport that never leaks authorization headers in errors."""

    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[bytes] = None,
    ) -> HttpResponse:
        request = urllib.request.Request(url, data=body, method=method, headers=dict(headers))
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return HttpResponse(
                    status=int(response.status),
                    headers={str(k): str(v) for k, v in response.headers.items()},
                    body=response.read(),
                )
        except urllib.error.HTTPError as exc:
            return HttpResponse(
                status=int(exc.code),
                headers={str(k): str(v) for k, v in exc.headers.items()},
                body=exc.read(),
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RemoteError("GitHub request failed before a response was received") from exc


@dataclasses.dataclass(frozen=True)
class TargetIdentity:
    kind: str
    normalized: str
    claim_key: str
    hint: str


@dataclasses.dataclass(frozen=True)
class StoredClaim:
    record: Mapping[str, Any]
    blob_sha: str
    server_now: dt.datetime


@dataclasses.dataclass(frozen=True)
class ClaimReceipt:
    action: str
    claim_key: str
    state: str
    revision: int
    agent_id: str
    operation_id: str
    lease_expires_at: str
    record_digest: str
    path: str
    blob_sha: Optional[str] = None
    commit_sha: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {"ok": True, **dataclasses.asdict(self)}


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean_text(value: str, *, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    cleaned = " ".join(unicodedata.normalize("NFKC", value).split())
    if not cleaned:
        raise ValidationError(f"{field} must not be empty")
    if len(cleaned) > max_length:
        raise ValidationError(f"{field} exceeds {max_length} characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
        raise ValidationError(f"{field} contains a control character")
    return cleaned


def _normalize_domain(value: str) -> str:
    domain = value.strip().rstrip(".").casefold()
    if not domain or "." not in domain:
        raise ValidationError("domain must contain at least one dot")
    try:
        ascii_domain = domain.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValidationError("domain is not valid IDNA") from exc
    labels = ascii_domain.split(".")
    if any(not label or len(label) > 63 for label in labels) or len(ascii_domain) > 253:
        raise ValidationError("domain has an invalid label length")
    label_re = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
    if any(not label_re.fullmatch(label) for label in labels):
        raise ValidationError("domain contains invalid characters")
    return ascii_domain


def _masked_domain_hint(domain: str) -> str:
    return ".".join(f"{label[:1]}***" for label in domain.split("."))


def normalize_target(kind: str, value: str) -> TargetIdentity:
    kind = _clean_text(kind, field="target kind", max_length=24).casefold()
    if kind not in _TARGET_KINDS:
        raise ValidationError(
            "unsupported target kind", details={"allowed": sorted(_TARGET_KINDS)}
        )
    raw = _clean_text(value, field="contact target", max_length=512)

    if kind == "email":
        if raw.count("@") != 1:
            raise ValidationError("email target must contain exactly one @")
        local, domain = raw.rsplit("@", 1)
        local = unicodedata.normalize("NFKC", local).casefold()
        if not local or len(local) > 64 or any(ch.isspace() for ch in local):
            raise ValidationError("email local part is invalid")
        domain = _normalize_domain(domain)
        normalized = f"{local}@{domain}"
        hint = f"{local[:1]}***@{_masked_domain_hint(domain)}"
    elif kind == "domain":
        normalized = _normalize_domain(raw)
        hint = _masked_domain_hint(normalized)
    elif kind == "github":
        handle = raw.lstrip("@").casefold()
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,37}[a-z0-9])?", handle):
            raise ValidationError("GitHub handle is invalid")
        normalized = handle
        hint = f"@{handle[:2]}***" if len(handle) > 2 else f"@{handle[:1]}*"
    elif kind == "slack":
        handle = raw.lstrip("@").casefold()
        if not re.fullmatch(r"[a-z0-9._-]{1,80}", handle):
            raise ValidationError("Slack handle is invalid")
        normalized = handle
        hint = f"@{handle[:2]}***" if len(handle) > 2 else f"@{handle[:1]}*"
    else:
        normalized = raw.casefold()
        hint = f"{normalized[:2]}***" if len(normalized) > 2 else "***"

    claim_key = _sha256_hex(
        _canonical_json_bytes({"schema": SCHEMA, "target_kind": kind, "target": normalized})
    )
    return TargetIdentity(kind=kind, normalized=normalized, claim_key=claim_key, hint=hint)


def _format_timestamp(value: dt.datetime) -> str:
    if value.tzinfo is None:
        raise ValidationError("timestamp must be timezone-aware")
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any, *, field: str) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ProtocolError(f"stored {field} is not a canonical UTC timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ProtocolError(f"stored {field} is invalid") from exc
    if parsed.tzinfo is None:
        raise ProtocolError(f"stored {field} has no timezone")
    return parsed.astimezone(dt.timezone.utc)


def _server_time(headers: Mapping[str, str]) -> dt.datetime:
    date_value: Optional[str] = None
    for key, value in headers.items():
        if key.casefold() == "date":
            date_value = value
            break
    if not date_value:
        raise ProtocolError("GitHub response omitted the Date header; refusing local-clock fallback")
    try:
        parsed = email.utils.parsedate_to_datetime(date_value)
    except (TypeError, ValueError) as exc:
        raise ProtocolError("GitHub Date header is invalid") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc).replace(microsecond=0)


def _record_digest(record: Mapping[str, Any]) -> str:
    payload = dict(record)
    payload.pop("record_digest", None)
    return _sha256_hex(_canonical_json_bytes(payload))


def _seal_record(record: MutableMapping[str, Any]) -> Dict[str, Any]:
    sealed = dict(record)
    sealed.pop("record_digest", None)
    sealed["record_digest"] = _record_digest(sealed)
    return sealed


def _validate_record(record: Any, *, expected_claim_key: str) -> Dict[str, Any]:
    if not isinstance(record, dict):
        raise ProtocolError("stored claim is not a JSON object")
    required = {
        "schema": str,
        "claim_key": str,
        "target_kind": str,
        "target_hint": str,
        "state": str,
        "revision": int,
        "agent_id": str,
        "operation_id": str,
        "opportunity_label": str,
        "opportunity_digest": str,
        "claimed_at": str,
        "last_action_at": str,
        "lease_expires_at": str,
        "prior_record_digest": (str, type(None)),
        "record_digest": str,
        "contact_count": int,
        "last_contacted_at": (str, type(None)),
        "last_message_digest": (str, type(None)),
        "last_channel": (str, type(None)),
        "compensation_path": (str, type(None)),
        "release_reason": (str, type(None)),
    }
    for key, expected_type in required.items():
        if key not in record or not isinstance(record[key], expected_type):
            raise ProtocolError(f"stored claim field {key!r} has an invalid type")
    unexpected = sorted(set(record) - set(required))
    if unexpected:
        raise ProtocolError(
            "stored claim contains fields outside the v1 schema",
            details={"unexpected_fields": unexpected},
        )
    if record["schema"] != SCHEMA:
        raise ProtocolError("stored claim schema is unsupported")
    if record["claim_key"] != expected_claim_key:
        raise ProtocolError("stored claim key does not match its path")
    if record["state"] not in _STATES:
        raise ProtocolError("stored claim state is invalid")
    if record["target_kind"] not in _TARGET_KINDS:
        raise ProtocolError("stored target kind is invalid")
    owner_shape = re.compile(r"[A-Za-z0-9._:/-]+")
    if not owner_shape.fullmatch(record["agent_id"]) or not owner_shape.fullmatch(
        record["operation_id"]
    ):
        raise ProtocolError("stored claim ownership identifier is invalid")
    if not record["target_hint"] or len(record["target_hint"]) > 512:
        raise ProtocolError("stored target hint is invalid")
    if not record["opportunity_label"] or len(record["opportunity_label"]) > 200:
        raise ProtocolError("stored opportunity label is invalid")
    if isinstance(record["revision"], bool) or record["revision"] < 1:
        raise ProtocolError("stored claim revision is invalid")
    if isinstance(record["contact_count"], bool) or record["contact_count"] < 0:
        raise ProtocolError("stored contact count is invalid")
    if not _HEX_64.fullmatch(record["record_digest"]):
        raise ProtocolError("stored record digest has an invalid shape")
    if record["prior_record_digest"] is not None and not _HEX_64.fullmatch(
        record["prior_record_digest"]
    ):
        raise ProtocolError("stored prior record digest has an invalid shape")
    if not _HEX_64.fullmatch(record["opportunity_digest"]):
        raise ProtocolError("stored opportunity digest has an invalid shape")
    expected_opportunity_digest = _sha256_hex(
        record["opportunity_label"].casefold().encode("utf-8")
    )
    if not hmac.compare_digest(expected_opportunity_digest, record["opportunity_digest"]):
        raise ProtocolError("stored opportunity digest does not match its label")
    claimed_at = _parse_timestamp(record["claimed_at"], field="claimed_at")
    last_action_at = _parse_timestamp(record["last_action_at"], field="last_action_at")
    _parse_timestamp(record["lease_expires_at"], field="lease_expires_at")
    if last_action_at < claimed_at:
        raise ProtocolError("stored action chronology predates current ownership")
    if record["last_contacted_at"] is not None:
        _parse_timestamp(record["last_contacted_at"], field="last_contacted_at")
    if record["last_message_digest"] is not None and not _HEX_64.fullmatch(
        record["last_message_digest"]
    ):
        raise ProtocolError("stored last message digest has an invalid shape")
    if record["last_channel"] is not None and not record["last_channel"]:
        raise ProtocolError("stored last channel is empty")
    if record["compensation_path"] is not None and not _has_concrete_compensation_signal(
        record["compensation_path"]
    ):
        raise ProtocolError("stored compensation path is not concrete")
    contact_evidence_fields = (
        "last_contacted_at",
        "last_message_digest",
        "last_channel",
        "compensation_path",
    )
    has_any_contact_evidence = any(
        record[field] is not None for field in contact_evidence_fields
    )
    has_all_contact_evidence = all(
        record[field] is not None for field in contact_evidence_fields
    )
    if record["contact_count"] == 0 and has_any_contact_evidence:
        raise ProtocolError("zero-count claim carries contact evidence")
    if record["contact_count"] > 0 and not has_all_contact_evidence:
        raise ProtocolError("stored contact history is incomplete")
    if record["state"] == "CONTACTED" and record["contact_count"] < 1:
        raise ProtocolError("contacted claim has no contact count")
    if record["state"] == "RELEASED":
        if not record["release_reason"]:
            raise ProtocolError("released claim is missing a release reason")
    elif record["release_reason"] is not None:
        raise ProtocolError("non-released claim carries a release reason")
    expected_digest = _record_digest(record)
    if not hmac.compare_digest(expected_digest, record["record_digest"]):
        raise ProtocolError("stored claim digest does not verify")
    return dict(record)


def _validate_duration(value: int, *, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field} must be an integer number of seconds")
    if not minimum <= value <= maximum:
        raise ValidationError(f"{field} must be between {minimum} and {maximum} seconds")
    return value


def _safe_owner(value: str, *, field: str) -> str:
    cleaned = _clean_text(value, field=field, max_length=128)
    if not re.fullmatch(r"[A-Za-z0-9._:/-]+", cleaned):
        raise ValidationError(f"{field} contains unsupported characters")
    return cleaned


def _safe_label(value: str, *, field: str, max_length: int = 200) -> str:
    return _clean_text(value, field=field, max_length=max_length)


def _safe_message_digest(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("message digest must be a string")
    value = value.strip().casefold()
    if not _HEX_64.fullmatch(value):
        raise ValidationError("message digest must be 64 lowercase hexadecimal characters")
    return value


def _has_concrete_compensation_signal(value: str) -> bool:
    folded = value.casefold()
    if folded in _WEAK_COMPENSATION_PATHS:
        return False
    if re.search(r"(?:[$€£¥]|\b(?:usd|eur|gbp|cad|aud)\b)\s*\d", folded):
        return True
    terms = (
        "bounty",
        "paid",
        "payment",
        "proposal",
        "contract",
        "invoice",
        "retainer",
        "commission",
        "fee",
        "purchase order",
        "revenue share",
        "fixed-scope",
        "fixed scope",
        "discovery",
        "quote",
        "bid",
        "award",
    )
    return any(term in folded for term in terms)


def digest_message_bytes(message: bytes) -> str:
    if not isinstance(message, (bytes, bytearray)):
        raise ValidationError("message must be bytes")
    return _sha256_hex(bytes(message))


def digest_message_file(path: str) -> str:
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(64 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise ValidationError("message file could not be read") from exc
    return digest.hexdigest()
