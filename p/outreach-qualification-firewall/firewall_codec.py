from __future__ import annotations

import hashlib
import json
import re
import time as _time_module
import unicodedata
from datetime import datetime as _datetime, timezone as _timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

SCHEMA = "outreach-qualification-firewall.v1"
DECISION_SCHEMA = "outreach-qualification-firewall.decision.v1"
MAX_INPUT_BYTES = 1_000_000
MAX_LIST_ROWS = 500
MAX_MINOR_UNITS = 10**12
MAX_QUANTITY = 10**6
MAX_RUNWAY_SECONDS = 366 * 24 * 3600
MAX_LEASE_SECONDS = 3600
TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}$")
HEX = set("0123456789abcdef")

TOP_KEYS = {
    "schema",
    "source_packet",
    "source_packet_sha256",
    "qualifications",
    "economics",
    "contact",
    "requesting_seat",
    "session_nonce",
    "writer_lease",
}
SOURCE_KEYS = {
    "opportunity_id",
    "source_uri",
    "source_generation",
    "observed_at",
    "deadline_at",
    "min_runway_seconds",
    "submission_route_type",
    "submission_route",
    "registration_required",
    "registration_state",
}
QUAL_KEYS = {"gate_id", "disposition", "required_for_outreach", "evidence_ref", "evidence_sha256"}
ECON_KEYS = {"workshare_ref", "currency", "amount_minor", "compensation_basis", "quantity_max", "scope_ref"}
CONTACT_KEYS = {
    "org_ref",
    "contact_ref",
    "route_type",
    "route",
    "relationship_state",
    "relationship_evidence_ref",
    "relationship_evidence_sha256",
    "purpose_ref",
}
LEASE_KEYS = {"lease_id", "collision_key", "seat", "session_nonce", "issued_at", "expires_at", "status"}
DECISION_KEYS = {
    "schema",
    "evaluated_at",
    "evaluation_mode",
    "packet_digest",
    "source_packet_sha256",
    "dedupe_key",
    "qualification_state",
    "qualified_for_owner_review",
    "send_state",
    "authorized_to_send",
    "hold_reasons",
    "authority",
    "receipt_sha256",
}

QUAL_DISPOSITIONS = {"SATISFIED", "UNSATISFIED", "UNKNOWN"}
SUBMISSION_ROUTE_TYPES = {"EMAIL", "PORTAL", "FORM"}
REGISTRATION_STATES = {"NOT_REQUIRED", "READY", "UNKNOWN", "INCOMPLETE"}
COMPENSATION_BASES = {"FIXED", "HOURLY", "MILESTONE"}
RELATIONSHIP_STATES = {"OPEN", "DNR", "BOUNCE", "SENT_DNR", "HUMAN_EVENT_REOPEN"}
LEASE_STATUSES = {"GO", "SELECTED", "HOLD", "COLLISION", "CONSUMED", "EXPIRED"}

AUTHORITY_FALSE = {
    "package_performs_send": False,
    "buyer_qualified_or_interested": False,
    "submission_authorized": False,
    "signature_or_contract_authority": False,
    "award_or_payment_authority": False,
    "cash_or_revenue_authority": False,
}


class FirewallError(ValueError):
    pass


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise FirewallError("duplicate JSON key")
        out[key] = value
    return out


def _parse_int(token: str) -> int:
    unsigned = token[1:] if token.startswith("-") else token
    if len(unsigned) > 20:
        raise FirewallError("integer token exceeds bounded width")
    try:
        return int(token)
    except ValueError as exc:
        raise FirewallError("invalid integer token") from exc


def strict_json_loads(raw: str) -> Any:
    if not isinstance(raw, str):
        raise FirewallError("JSON input must be text")
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_no_duplicate_pairs,
            parse_int=_parse_int,
            parse_float=lambda _: (_ for _ in ()).throw(FirewallError("floating point numbers are forbidden")),
            parse_constant=lambda _: (_ for _ in ()).throw(FirewallError("non-finite numbers are forbidden")),
        )
    except FirewallError:
        raise
    except (json.JSONDecodeError, RecursionError, UnicodeError, ValueError, OverflowError) as exc:
        raise FirewallError("invalid bounded JSON") from exc
    _reject_unsafe_unicode(value)
    return value


def _reject_unsafe_unicode(value: Any) -> None:
    if isinstance(value, str):
        for ch in value:
            if unicodedata.category(ch) in {"Cc", "Cf", "Cs", "Zl", "Zp"}:
                raise FirewallError("forbidden control/format/surrogate character")
    elif isinstance(value, list):
        for item in value:
            _reject_unsafe_unicode(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_unsafe_unicode(key)
            _reject_unsafe_unicode(item)


def canonical_json(value: Any) -> bytes:
    _reject_unsafe_unicode(value)
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise FirewallError("value is not canonically serializable") from exc


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FirewallError(f"{label} must be an object")
    keys = set(value)
    if keys != expected:
        raise FirewallError(f"{label} schema mismatch")
    return dict(value)


def _token(value: Any, field: str) -> str:
    if not isinstance(value, str) or not TOKEN_RE.fullmatch(value):
        raise FirewallError(f"{field} must be a bounded opaque ASCII token")
    return value


def _digest(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in HEX for ch in value):
        raise FirewallError(f"{field} must be lowercase SHA-256 hex")
    return value


def _exact_int(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise FirewallError(f"{field} must be an exact integer")
    if not minimum <= value <= maximum:
        raise FirewallError(f"{field} is out of range")
    return value


def _exact_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise FirewallError(f"{field} must be boolean")
    return value


def _utc(value: Any, field: str, _fromisoformat=_datetime.fromisoformat, _tz=_timezone.utc) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise FirewallError(f"{field} must be canonical UTC Z time")
    try:
        dt = _fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise FirewallError(f"{field} must be canonical UTC Z time") from exc
    canonical = dt.astimezone(_tz).isoformat(timespec="seconds").replace("+00:00", "Z")
    if dt.utcoffset() is None or dt.utcoffset().total_seconds() != 0 or canonical != value:
        raise FirewallError(f"{field} must be canonical UTC Z time to whole seconds")
    return dt


def _utc_text(dt: datetime) -> str:
    return dt.astimezone(_timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _process_utc_now(_clock=_time_module.time, _fromtimestamp=_datetime.fromtimestamp, _tz=_timezone.utc) -> datetime:
    # Default arguments capture initialization-owned callables so ordinary module/global rebinding
    # cannot substitute caller-selected historical time into compile_current().
    return _fromtimestamp(_clock(), _tz).replace(microsecond=0)


def _canonical_https(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) > 512:
        raise FirewallError(f"{field} must be bounded HTTPS URL text")
    parts = urlsplit(value)
    if parts.scheme.lower() != "https" or not parts.hostname or parts.username or parts.password or parts.fragment:
        raise FirewallError(f"{field} must be canonical HTTPS without credentials/fragment")
    try:
        port = parts.port
    except ValueError as exc:
        raise FirewallError(f"{field} has invalid port syntax") from exc
    if port not in (None, 443):
        raise FirewallError(f"{field} may not use a non-default port")
    if not parts.hostname.isascii():
        raise FirewallError(f"{field} hostname must be ASCII")
    netloc = parts.hostname.lower()
    path = parts.path or "/"
    normalized = urlunsplit(("https", netloc, path, parts.query, ""))
    if normalized != value:
        raise FirewallError(f"{field} must already be canonical")
    return value


def _canonical_email(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) > 254 or not EMAIL_RE.fullmatch(value):
        raise FirewallError(f"{field} must be an email address")
    return value.lower()


def _canonical_route(route_type: str, value: Any, field: str) -> str:
    if route_type == "EMAIL":
        return _canonical_email(value, field)
    return _canonical_https(value, field)


