from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = 1
MAX_SAFE_CENTS = 9_007_199_254_740_991
MAX_TEXT = 2_000
MAX_ITEMS = 200
MAX_EVIDENCE = 100
MAX_EVENTS = 200
GENESIS = "GENESIS"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
CURRENCY = re.compile(r"^[A-Z]{3}$")
EMAILISH = re.compile(r"(?i)(?:^|\s)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?:\s|$)")
PHONEISH = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?(?:\(?\d{3}\)?[ .-]?)\d{3}[ .-]?\d{4}(?!\d)")
SECRET_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)
FORBIDDEN_KEY_TOKENS = {
    "password", "passwd", "secret", "token", "api_key", "apikey", "private_key",
    "authorization", "cookie", "session", "ssn", "social_security", "card_number",
    "cvv", "email", "phone", "address", "full_name", "customer_name", "buyer_name",
}
AUTHORITY_FALSE = {
    "send_authorized": False,
    "signature_authorized": False,
    "contract_amendment_authorized": False,
    "buyer_acceptance_inferred": False,
    "checkout_authorized": False,
    "payment_authorized": False,
    "provider_write_authorized": False,
    "scheduling_authorized": False,
    "dispatch_authorized": False,
    "fulfillment_authorized": False,
    "deployment_authorized": False,
    "cash_recognized": False,
    "revenue_recognized": False,
}


class DeskError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _reject_constant(value: str) -> None:
    raise DeskError("NONFINITE_JSON_NUMBER", value)


def _reject_float(value: str) -> None:
    raise DeskError("FLOAT_JSON_NUMBER_FORBIDDEN", value)


def strict_json_loads(text: str) -> Any:
    def object_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise DeskError("DUPLICATE_JSON_KEY", key)
            out[key] = value
        return out

    try:
        return json.loads(
            text,
            object_pairs_hook=object_hook,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except DeskError:
        raise
    except (TypeError, json.JSONDecodeError) as exc:
        raise DeskError("INVALID_JSON", str(exc)) from exc


def _validate_json(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        raise DeskError("FLOAT_JSON_NUMBER_FORBIDDEN", path)
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise DeskError("NONSTRING_JSON_KEY", path)
            _validate_json(item, f"{path}.{key}")
        return
    raise DeskError("UNSUPPORTED_JSON_TYPE", f"{path}:{type(value).__name__}")


def canonical_json(value: Any) -> str:
    _validate_json(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_text(canonical_json(value))


def _object(
    value: Any,
    *,
    path: str,
    required: Iterable[str],
    optional: Iterable[str] = (),
) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise DeskError("EXPECTED_OBJECT", path)
    allowed = set(required) | set(optional)
    unknown = sorted(set(value) - allowed)
    missing = sorted(set(required) - set(value))
    if unknown:
        raise DeskError("UNKNOWN_FIELD", f"{path}:{unknown[0]}")
    if missing:
        raise DeskError("MISSING_FIELD", f"{path}:{missing[0]}")
    return value


def _list(value: Any, *, path: str, maximum: int, allow_empty: bool = True) -> list[Any]:
    if not isinstance(value, list):
        raise DeskError("EXPECTED_LIST", path)
    if not allow_empty and not value:
        raise DeskError("EMPTY_LIST", path)
    if len(value) > maximum:
        raise DeskError("LIST_TOO_LARGE", path)
    return value


def _integer(value: Any, *, path: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DeskError("EXPECTED_INTEGER", path)
    if value < minimum or value > maximum:
        raise DeskError("INTEGER_OUT_OF_RANGE", path)
    return value


def _text(value: Any, *, path: str, maximum: int = MAX_TEXT, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise DeskError("EXPECTED_STRING", path)
    normalized = unicodedata.normalize("NFC", value)
    if value != normalized:
        raise DeskError("NONCANONICAL_UNICODE", path)
    if not allow_empty and not value:
        raise DeskError("EMPTY_STRING", path)
    if len(value) > maximum:
        raise DeskError("TEXT_TOO_LONG", path)
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in value):
        raise DeskError("CONTROL_CHARACTER", path)
    return value


def _identifier(value: Any, *, path: str) -> str:
    text = _text(value, path=path, maximum=96)
    if not IDENT.fullmatch(text):
        raise DeskError("INVALID_IDENTIFIER", path)
    return text


def _digest(value: Any, *, path: str) -> str:
    text = _text(value, path=path, maximum=64)
    if not HEX64.fullmatch(text):
        raise DeskError("INVALID_SHA256", path)
    return text


def _currency(value: Any, *, path: str) -> str:
    text = _text(value, path=path, maximum=3)
    if not CURRENCY.fullmatch(text):
        raise DeskError("INVALID_CURRENCY", path)
    return text


def _timestamp(value: Any, *, path: str) -> datetime:
    text = _text(value, path=path, maximum=20)
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise DeskError("INVALID_TIMESTAMP", path) from exc
    return parsed


def _date(value: Any, *, path: str) -> date:
    text = _text(value, path=path, maximum=10)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise DeskError("INVALID_DATE", path) from exc


def _scan_sensitive(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            snake_key = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
            normalized_key = snake_key.lower().replace("-", "_").replace(" ", "_")
            tokens = {normalized_key, *normalized_key.split("_")}
            if FORBIDDEN_KEY_TOKENS & tokens:
                raise DeskError("SENSITIVE_FIELD_FORBIDDEN", f"{path}.{key}")
            _scan_sensitive(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _scan_sensitive(item, f"{path}[{index}]")
        return
    if isinstance(value, str):
        if EMAILISH.search(value) or PHONEISH.search(value):
            raise DeskError("PII_SHAPED_VALUE_FORBIDDEN", path)
        if any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS):
            raise DeskError("SECRET_SHAPED_VALUE_FORBIDDEN", path)


def _check_unique(values: Sequence[str], *, code: str, path: str) -> None:
    if len(values) != len(set(values)):
        raise DeskError(code, path)


def _parse_evidence(value: Any, *, path: str) -> list[dict[str, str]]:
    rows = _list(value, path=path, maximum=MAX_EVIDENCE, allow_empty=False)
    allowed_kinds = {"proposal", "acceptance", "scope", "schedule", "buyer_decision", "artifact", "other"}
    out: list[dict[str, str]] = []
    for index, raw in enumerate(rows):
        row_path = f"{path}[{index}]"
        row = _object(raw, path=row_path, required=("ref_id", "kind", "sha256"))
        kind = _text(row["kind"], path=f"{row_path}.kind", maximum=32)
        if kind not in allowed_kinds:
            raise DeskError("INVALID_EVIDENCE_KIND", f"{row_path}.kind")
        out.append({
            "ref_id": _identifier(row["ref_id"], path=f"{row_path}.ref_id"),
            "kind": kind,
            "sha256": _digest(row["sha256"], path=f"{row_path}.sha256"),
        })
    _check_unique([row["ref_id"] for row in out], code="DUPLICATE_EVIDENCE_REF", path=path)
    return out
