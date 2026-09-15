from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

REGISTRY_SCHEMA = "opportunity-identity-alias-registry/v1"
OBSERVATION_SCHEMA = "opportunity-identity-alias-observation/v1"
RESULT_SCHEMA = "opportunity-identity-alias-result/v1"

STATUS_RESOLVED = "RESOLVED_CANONICAL_OPPORTUNITY"
STATUS_UNRESOLVED = "UNRESOLVED_ALIAS"
STATUS_AMBIGUOUS = "AMBIGUOUS_ALIAS_SET"

_REGISTRY_KEYS = {"schema", "generation", "previous_registry_sha256", "opportunities"}
_OPPORTUNITY_KEYS = {"canonical_opportunity_key", "buyer_key", "aliases"}
_ALIAS_KEYS = {"kind", "value"}
_OBSERVATION_KEYS = {"schema", "buyer_key", "aliases"}
_RESULT_KEYS = {
    "schema", "status", "buyer_key", "canonical_opportunity_key",
    "registry_generation", "registry_sha256", "alias_set_sha256",
}
_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_OFFICIAL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:/-]{0,199}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_ALIAS_KINDS = {"official_id", "authority_url"}


class ContractError(ValueError):
    """Raised when registry, observation, or result bytes violate the v1 contract."""


def _reject_constant(value: str) -> None:
    raise ContractError(f"non-finite JSON number is not allowed: {value}")


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _loads_strict(raw: bytes) -> Any:
    if not isinstance(raw, (bytes, bytearray)):
        raise ContractError("JSON input must be bytes")
    try:
        text = bytes(raw).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("JSON must be UTF-8") from exc
    try:
        return json.loads(text, object_pairs_hook=_pairs_no_duplicates, parse_constant=_reject_constant)
    except ContractError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ContractError("invalid JSON") from exc


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContractError("value is not canonicalizable JSON") from exc


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if not isinstance(value, Mapping):
        raise ContractError(f"{label} must be an object")
    keys = set(value)
    if keys != expected:
        missing = sorted(expected - keys)
        extra = sorted(keys - expected)
        raise ContractError(f"{label} keys mismatch; missing={missing}, extra={extra}")


def _normalize_token(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{label} must be a string")
    normalized = value.strip().lower()
    if not _TOKEN_RE.fullmatch(normalized):
        raise ContractError(f"{label} is not a valid machine token")
    return normalized


def _normalize_canonical_key(value: Any) -> str:
    key = _normalize_token(value, "canonical_opportunity_key")
    if not key.startswith("opp_"):
        raise ContractError("canonical_opportunity_key must start with 'opp_'")
    return key


def _normalize_buyer_key(value: Any) -> str:
    key = _normalize_token(value, "buyer_key")
    if not key.startswith("buyer_"):
        raise ContractError("buyer_key must start with 'buyer_'")
    return key


def _normalize_official_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ContractError("official_id alias value must be a string")
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    normalized = re.sub(r"\s+", "-", normalized)
    if not _OFFICIAL_ID_RE.fullmatch(normalized):
        raise ContractError("official_id alias contains unsupported characters")
    return normalized


def _normalize_authority_url(value: Any) -> str:
    if not isinstance(value, str):
        raise ContractError("authority_url alias value must be a string")
    candidate = unicodedata.normalize("NFKC", value).strip()
    try:
        parsed = urlsplit(candidate)
    except ValueError as exc:
        raise ContractError("authority_url alias is invalid") from exc
    if parsed.scheme.lower() != "https":
        raise ContractError("authority_url alias must use https")
    if parsed.username is not None or parsed.password is not None:
        raise ContractError("authority_url alias must not contain userinfo")
    if parsed.fragment:
        raise ContractError("authority_url alias must not contain a fragment")
    if not parsed.hostname:
        raise ContractError("authority_url alias must contain a host")
    try:
        host = parsed.hostname.encode("idna").decode("ascii").lower()
        port = parsed.port
    except (UnicodeError, ValueError) as exc:
        raise ContractError("authority_url alias host/port is invalid") from exc
    if not host or any(ch.isspace() for ch in host):
        raise ContractError("authority_url alias host is invalid")
    netloc = host if port in (None, 443) else f"{host}:{port}"
    path = parsed.path or "/"
    return urlunsplit(("https", netloc, path, parsed.query, ""))


def normalize_alias(value: Any) -> dict[str, str]:
    _require_exact_keys(value, _ALIAS_KEYS, "alias")
    kind = value["kind"]
    if kind not in _ALLOWED_ALIAS_KINDS:
        raise ContractError(f"unsupported alias kind: {kind!r}")
    raw = value["value"]
    normalized = _normalize_official_id(raw) if kind == "official_id" else _normalize_authority_url(raw)
    return {"kind": kind, "value": normalized}


def _normalize_aliases(value: Any, *, require_nonempty: bool = True) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ContractError("aliases must be an array")
    aliases = [normalize_alias(item) for item in value]
    aliases.sort(key=lambda item: (item["kind"], item["value"]))
    if require_nonempty and not aliases:
        raise ContractError("aliases must not be empty")
    for left, right in zip(aliases, aliases[1:]):
        if left == right:
            raise ContractError("duplicate normalized alias")
    return aliases


def _normalize_registry_object(value: Any) -> dict[str, Any]:
    _require_exact_keys(value, _REGISTRY_KEYS, "registry")
    if value["schema"] != REGISTRY_SCHEMA:
        raise ContractError("unsupported registry schema")
    generation = value["generation"]
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
        raise ContractError("registry generation must be a positive integer")
    previous = value["previous_registry_sha256"]
    if generation == 1:
        if previous is not None:
            raise ContractError("generation 1 must have null previous_registry_sha256")
    elif not isinstance(previous, str) or not _SHA256_RE.fullmatch(previous):
        raise ContractError("later generations require a lowercase SHA-256 previous digest")
    opportunities_raw = value["opportunities"]
    if not isinstance(opportunities_raw, list):
        raise ContractError("registry opportunities must be an array")
    opportunities: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    alias_owner: dict[tuple[str, str, str], str] = {}
    for item in opportunities_raw:
        _require_exact_keys(item, _OPPORTUNITY_KEYS, "opportunity")
        canonical_key = _normalize_canonical_key(item["canonical_opportunity_key"])
        buyer_key = _normalize_buyer_key(item["buyer_key"])
        aliases = _normalize_aliases(item["aliases"])
        if canonical_key in seen_keys:
            raise ContractError("duplicate canonical_opportunity_key")
        seen_keys.add(canonical_key)
        for alias in aliases:
            index_key = (buyer_key, alias["kind"], alias["value"])
            prior = alias_owner.get(index_key)
            if prior is not None and prior != canonical_key:
                raise ContractError("one normalized alias maps to multiple canonical opportunities for a buyer")
            alias_owner[index_key] = canonical_key
        opportunities.append({
            "canonical_opportunity_key": canonical_key,
            "buyer_key": buyer_key,
            "aliases": aliases,
        })
    opportunities.sort(key=lambda item: item["canonical_opportunity_key"])
    return {
        "schema": REGISTRY_SCHEMA,
        "generation": generation,
        "previous_registry_sha256": previous,
        "opportunities": opportunities,
    }


def compile_initial_registry(value: Any) -> bytes:
    normalized = _normalize_registry_object(value)
    if normalized["generation"] != 1 or normalized["previous_registry_sha256"] is not None:
        raise ContractError("initial registry must be generation 1 with null previous digest")
    return canonical_json_bytes(normalized)


def parse_registry(raw: bytes) -> dict[str, Any]:
    loaded = _loads_strict(raw)
    normalized = _normalize_registry_object(loaded)
    canonical = canonical_json_bytes(normalized)
    if bytes(raw) != canonical:
        raise ContractError("registry bytes are not in canonical form")
    return normalized


def registry_sha256(raw: bytes) -> str:
    parse_registry(raw)
    return hashlib.sha256(bytes(raw)).hexdigest()


def compile_transition(previous_raw: bytes, next_value: Any) -> bytes:
    previous = parse_registry(previous_raw)
    normalized = _normalize_registry_object(next_value)
    if normalized["generation"] != previous["generation"] + 1:
        raise ContractError("registry generation must advance by exactly one")
    expected_previous = hashlib.sha256(bytes(previous_raw)).hexdigest()
    if normalized["previous_registry_sha256"] != expected_previous:
        raise ContractError("previous_registry_sha256 does not match exact previous bytes")
    previous_by_key = {item["canonical_opportunity_key"]: item for item in previous["opportunities"]}
    next_by_key = {item["canonical_opportunity_key"]: item for item in normalized["opportunities"]}
    for canonical_key, old in previous_by_key.items():
        new = next_by_key.get(canonical_key)
        if new is None:
            raise ContractError("existing canonical opportunity may not be removed in v1")
        if new["buyer_key"] != old["buyer_key"]:
            raise ContractError("existing canonical opportunity buyer may not be reassigned in v1")
        old_aliases = {(a["kind"], a["value"]) for a in old["aliases"]}
        new_aliases = {(a["kind"], a["value"]) for a in new["aliases"]}
        if not old_aliases.issubset(new_aliases):
            raise ContractError("existing aliases may not be removed or rewritten in v1")
    return canonical_json_bytes(normalized)


def normalize_observation(value: Any) -> dict[str, Any]:
    _require_exact_keys(value, _OBSERVATION_KEYS, "observation")
    if value["schema"] != OBSERVATION_SCHEMA:
        raise ContractError("unsupported observation schema")
    return {
        "schema": OBSERVATION_SCHEMA,
        "buyer_key": _normalize_buyer_key(value["buyer_key"]),
        "aliases": _normalize_aliases(value["aliases"]),
    }


def _result_for(observation: Mapping[str, Any], registry: Mapping[str, Any], registry_raw: bytes) -> dict[str, Any]:
    buyer_key = observation["buyer_key"]
    index: dict[tuple[str, str, str], str] = {}
    for opportunity in registry["opportunities"]:
        for alias in opportunity["aliases"]:
            index[(opportunity["buyer_key"], alias["kind"], alias["value"])] = opportunity["canonical_opportunity_key"]
    found: list[str] = []
    has_unknown = False
    for alias in observation["aliases"]:
        canonical = index.get((buyer_key, alias["kind"], alias["value"]))
        if canonical is None:
            has_unknown = True
        else:
            found.append(canonical)
    unique = sorted(set(found))
    if has_unknown:
        status, canonical_key = STATUS_UNRESOLVED, None
    elif len(unique) == 1:
        status, canonical_key = STATUS_RESOLVED, unique[0]
    else:
        status, canonical_key = STATUS_AMBIGUOUS, None
    alias_bytes = canonical_json_bytes(observation["aliases"])
    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "buyer_key": buyer_key,
        "canonical_opportunity_key": canonical_key,
        "registry_generation": registry["generation"],
        "registry_sha256": hashlib.sha256(bytes(registry_raw)).hexdigest(),
        "alias_set_sha256": hashlib.sha256(alias_bytes).hexdigest(),
    }


def resolve_against(observation: Any, registry_raw: bytes) -> dict[str, Any]:
    normalized_observation = normalize_observation(observation)
    registry = parse_registry(registry_raw)
    return _result_for(normalized_observation, registry, registry_raw)


def _normalize_result(value: Any) -> dict[str, Any]:
    _require_exact_keys(value, _RESULT_KEYS, "result")
    if value["schema"] != RESULT_SCHEMA:
        raise ContractError("unsupported result schema")
    status = value["status"]
    if status not in {STATUS_RESOLVED, STATUS_UNRESOLVED, STATUS_AMBIGUOUS}:
        raise ContractError("invalid result status")
    buyer_key = _normalize_buyer_key(value["buyer_key"])
    canonical = value["canonical_opportunity_key"]
    if status == STATUS_RESOLVED:
        canonical = _normalize_canonical_key(canonical)
    elif canonical is not None:
        raise ContractError("unresolved/ambiguous result must have null canonical_opportunity_key")
    generation = value["registry_generation"]
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
        raise ContractError("result registry_generation must be positive integer")
    for field in ("registry_sha256", "alias_set_sha256"):
        if not isinstance(value[field], str) or not _SHA256_RE.fullmatch(value[field]):
            raise ContractError(f"{field} must be a lowercase SHA-256 digest")
    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "buyer_key": buyer_key,
        "canonical_opportunity_key": canonical,
        "registry_generation": generation,
        "registry_sha256": value["registry_sha256"],
        "alias_set_sha256": value["alias_set_sha256"],
    }


def verify_result(observation: Any, registry_raw: bytes, result: Any) -> bool:
    try:
        expected = resolve_against(observation, registry_raw)
        normalized = _normalize_result(result)
    except (ContractError, TypeError, ValueError):
        return False
    return normalized == expected


def _current_registry_bytes() -> bytes:
    return Path(__file__).with_name("registry.json").read_bytes()


def resolve_current(observation: Any) -> dict[str, Any]:
    return resolve_against(observation, _current_registry_bytes())


def verify_current(observation: Any, result: Any) -> bool:
    return verify_result(observation, _current_registry_bytes(), result)
