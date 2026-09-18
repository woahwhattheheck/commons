from __future__ import annotations

import hashlib
import json
import re
import time as _time_module
import unicodedata
from datetime import datetime as _datetime, timezone as _timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

SCHEMA = "outreach-qualification-firewall.v2"
DECISION_SCHEMA = "outreach-qualification-firewall.decision.v2"
MAX_INPUT_BYTES = 1_000_000
MAX_LIST_ROWS = 500
MAX_MINOR_UNITS = 10**12
MAX_QUANTITY = 10**6
MAX_RUNWAY_SECONDS = 366 * 24 * 3600
MAX_LEASE_SECONDS = 3600
MAX_IDENTITY_VALIDITY_SECONDS = 180 * 24 * 3600
MAX_RELATIONSHIP_VALIDITY_SECONDS = 600
MAX_RELATIONSHIP_AGE_SECONDS = 60
TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_\`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}$")
HEX = set("0123456789abcdef")

TOP_KEYS = {
    "schema",
    "source_packet",
    "source_packet_sha256",
    "qualifications",
    "economics",
    "contact",
    "identity_binding",
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
IDENTITY_KEYS = {
    "binding_id",
    "source_packet_sha256",
    "opportunity_id",
    "org_ref",
    "purpose_ref",
    "canonical_org_id",
    "canonical_purpose_id",
    "observed_at",
    "valid_until",
    "auth_tag_hex",
}
CONTACT_KEYS = {
    "org_ref",
    "contact_ref",
    "route_type",
    "route",
    "relationship_state",
    "relationship_evidence_ref",
    "relationship_evidence_sha256",
    "relationship_generation",
    "relationship_head_sha256",
    "relationship_observed_at",
    "relationship_valid_until",
    "relationship_authority_tag_hex",
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


def _make_no_duplicate_pairs(_err: type[Exception]):
    def no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise _err("duplicate JSON key")
            out[key] = value
        return out
    return no_duplicate_pairs


_no_duplicate_pairs = _make_no_duplicate_pairs(FirewallError)


def _make_parse_int(_int: type[int], _err: type[Exception]):
    def parse_int(token: str) -> int:
        unsigned = token[1:] if token.startswith("-") else token
        if len(unsigned) > 20:
            raise _err("integer token exceeds bounded width")
        try:
            return _int(token)
        except ValueError as exc:
            raise _err("invalid integer token") from exc
    return parse_int


_parse_int = _make_parse_int(int, FirewallError)


def _make_unicode_rejector(_category, _err):
    def reject(value: Any) -> None:
        if isinstance(value, str):
            for ch in value:
                if _category(ch) in {"Cc", "Cf", "Cs", "Zl", "Zp"}:
                    raise _err("forbidden control/format/surrogate character")
        elif isinstance(value, list):
            for item in value:
                reject(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                reject(key)
                reject(item)
    return reject


_reject_unsafe_unicode = _make_unicode_rejector(unicodedata.category, FirewallError)


def _make_strict_json_loads(_loads, _len, _max, _pairs, _parse_int_fn, _reject, _err, _parse_errors):
    def strict_json_loads(raw: str) -> Any:
        if type(raw) is not str:
            raise _err("JSON input must be exact text")
        try:
            encoded = raw.encode("utf-8", "strict")
        except UnicodeError as exc:
            raise _err("invalid bounded JSON") from exc
        if _len(encoded) > _max:
            raise _err("JSON input exceeds byte ceiling")
        try:
            value = _loads(
                raw,
                object_pairs_hook=_pairs,
                parse_int=_parse_int_fn,
                parse_float=lambda _: (_ for _ in ()).throw(_err("floating point numbers are forbidden")),
                parse_constant=lambda _: (_ for _ in ()).throw(_err("non-finite numbers are forbidden")),
            )
        except _err:
            raise
        except _parse_errors as exc:
            raise _err("invalid bounded JSON") from exc
        _reject(value)
        return value
    return strict_json_loads


strict_json_loads = _make_strict_json_loads(
    json.loads,
    len,
    MAX_INPUT_BYTES,
    _no_duplicate_pairs,
    _parse_int,
    _reject_unsafe_unicode,
    FirewallError,
    (json.JSONDecodeError, RecursionError, UnicodeError, ValueError, OverflowError),
)


def _make_canonical_json(_reject, _dumps, _err, _errors):
    def canonical_json(value: Any) -> bytes:
        _reject(value)
        try:
            return _dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        except _errors as exc:
            raise _err("value is not canonically serializable") from exc
    return canonical_json


canonical_json = _make_canonical_json(
    _reject_unsafe_unicode,
    json.dumps,
    FirewallError,
    (TypeError, ValueError, UnicodeError, RecursionError),
)


def _make_sha256_hex(_sha256):
    def sha256_hex(data: bytes) -> str:
        return _sha256(data).hexdigest()
    return sha256_hex


sha256_hex = _make_sha256_hex(hashlib.sha256)


def _make_exact_keys(_dict_type, _set, _dict, _err):
    def exact_keys(value: Any, expected: set[str] | frozenset[str], label: str) -> dict[str, Any]:
        if type(value) is not _dict_type:
            raise _err(f"{label} must be an exact object")
        keys = _set(value)
        if keys != expected:
            raise _err(f"{label} schema mismatch")
        return _dict(value)
    return exact_keys


_exact_keys = _make_exact_keys(dict, set, dict, FirewallError)


def _make_token(_regex, _str_type, _err):
    def token(value: Any, field: str) -> str:
        if type(value) is not _str_type or not _regex.fullmatch(value):
            raise _err(f"{field} must be a bounded opaque ASCII token")
        return value
    return token


_token = _make_token(TOKEN_RE, str, FirewallError)


def _make_digest(_str_type, _len, _hex_chars, _err):
    def digest(value: Any, field: str) -> str:
        if type(value) is not _str_type or _len(value) != 64 or any(ch not in _hex_chars for ch in value):
            raise _err(f"{field} must be lowercase SHA-256 hex")
        return value
    return digest


_digest = _make_digest(str, len, frozenset(HEX), FirewallError)


def _make_exact_int(_int_type, _err):
    def exact_int(value: Any, field: str, minimum: int, maximum: int) -> int:
        if type(value) is not _int_type:
            raise _err(f"{field} must be an exact integer")
        if not minimum <= value <= maximum:
            raise _err(f"{field} is out of range")
        return value
    return exact_int


_exact_int = _make_exact_int(int, FirewallError)


def _make_exact_bool(_bool_type, _err):
    def exact_bool(value: Any, field: str) -> bool:
        if type(value) is not _bool_type:
            raise _err(f"{field} must be boolean")
        return value
    return exact_bool


_exact_bool = _make_exact_bool(bool, FirewallError)


def _make_utc(_fromisoformat, _tz, _str_type, _err):
    def utc(value: Any, field: str) -> _datetime:
        if type(value) is not _str_type or not value.endswith("Z"):
            raise _err(f"{field} must be canonical UTC Z time")
        try:
            dt = _fromisoformat(value[:-1] + "+00:00")
        except ValueError as exc:
            raise _err(f"{field} must be canonical UTC Z time") from exc
        canonical = dt.astimezone(_tz).isoformat(timespec="seconds").replace("+00:00", "Z")
        if dt.utcoffset() is None or dt.utcoffset().total_seconds() != 0 or canonical != value:
            raise _err(f"{field} must be canonical UTC Z time to whole seconds")
        return dt
    return utc


_utc = _make_utc(_datetime.fromisoformat, _timezone.utc, str, FirewallError)


def _make_utc_text(_tz):
    def utc_text(dt: _datetime) -> str:
        return dt.astimezone(_tz).isoformat(timespec="seconds").replace("+00:00", "Z")
    return utc_text


_utc_text = _make_utc_text(_timezone.utc)


def _make_process_utc_now(_clock, _fromtimestamp, _tz):
    def process_utc_now() -> _datetime:
        return _fromtimestamp(_clock(), _tz).replace(microsecond=0)
    return process_utc_now


_process_utc_now = _make_process_utc_now(_time_module.time, _datetime.fromtimestamp, _timezone.utc)


def _make_canonical_https(_urlsplit, _urlunsplit, _str_type, _len, _err):
    def canonical_https(value: Any, field: str) -> str:
        if type(value) is not _str_type or _len(value) > 512:
            raise _err(f"{field} must be bounded HTTPS URL text")
        parts = _urlsplit(value)
        if parts.scheme.lower() != "https" or not parts.hostname or parts.username or parts.password or parts.fragment:
            raise _err(f"{field} must be canonical HTTPS without credentials/fragment")
        try:
            port = parts.port
        except ValueError as exc:
            raise _err(f"{field} has invalid port syntax") from exc
        if port not in (None, 443):
            raise _err(f"{field} may not use a non-default port")
        if not parts.hostname.isascii():
            raise _err(f"{field} hostname must be ASCII")
        netloc = parts.hostname.lower()
        path = parts.path or "/"
        normalized = _urlunsplit(("https", netloc, path, parts.query, ""))
        if normalized != value:
            raise _err(f"{field} must already be canonical")
        return value
    return canonical_https


_canonical_https = _make_canonical_https(urlsplit, urlunsplit, str, len, FirewallError)


def _make_canonical_email(_email_re, _str_type, _len, _err):
    def canonical_email(value: Any, field: str) -> str:
        if type(value) is not _str_type or _len(value) > 254 or not _email_re.fullmatch(value):
            raise _err(f"{field} must be an email address")
        return value.lower()
    return canonical_email


_canonical_email = _make_canonical_email(EMAIL_RE, str, len, FirewallError)


def _make_canonical_route(_email, _https):
    def canonical_route(route_type: str, value: Any, field: str) -> str:
        if route_type == "EMAIL":
            return _email(value, field)
        return _https(value, field)
    return canonical_route


_canonical_route = _make_canonical_route(_canonical_email, _canonical_https)

del (
    _make_no_duplicate_pairs,
    _make_parse_int,
    _make_unicode_rejector,
    _make_strict_json_loads,
    _make_canonical_json,
    _make_sha256_hex,
    _make_exact_keys,
    _make_token,
    _make_digest,
    _make_exact_int,
    _make_exact_bool,
    _make_utc,
    _make_utc_text,
    _make_process_utc_now,
    _make_canonical_https,
    _make_canonical_email,
    _make_canonical_route,
)
