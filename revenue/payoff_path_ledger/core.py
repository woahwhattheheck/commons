from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

SCHEMA_INPUT = "commons-payoff-path-input/v2"
SCHEMA_RECEIPT = "commons-payoff-path-receipt/v4"
COMPILER_ID = "commons.payoff-path-ledger/v4"
EVIDENCE_AUTH_ENV = "PAYOFF_PATH_EVIDENCE_AUTHORITY_KEY_HEX"
MAX_SAFE_INT = 10**15
MAX_TEXT = 4096
MAX_ROWS = 256
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 4096
MAX_JSON_INPUT_BYTES = 4 * 1024 * 1024
MAX_EVIDENCE_AGE = timedelta(days=90)

PAYOFF_CLASSES = frozenset({
    "BUG_BOUNTY", "COMPETITION_PRIZE", "PAID_DISCOVERY", "PARTNER_WORKSHARE",
    "PRODUCT_CONVERSION", "PAID_WORK", "STRATEGIC_UNPAID",
})
CASH_TERM_CLASSES = frozenset({
    "BUG_BOUNTY", "COMPETITION_PRIZE", "PAID_DISCOVERY", "PARTNER_WORKSHARE", "PAID_WORK",
})
EVIDENCE_CLASSES = PAYOFF_CLASSES | frozenset({"GENERIC_CONTEXT"})
OUTCOME_KINDS = frozenset({"ACTIVE_DUPLICATE", "SETTLED"})
SCOPE_STATUSES = frozenset({"COMPLETE", "PARTIAL"})
AMOUNT_MODES = frozenset({"EXACT", "AMOUNT_UNKNOWN"})
STATES = frozenset({
    "PAYOFF_BOUND", "PAID_WORK", "STRATEGIC_UNPAID_BOUNDED",
    "HOLD_ALREADY_SETTLED", "HOLD_ACTIVE_DUPLICATE", "HOLD_NO_PAYOFF_PATH",
    "HOLD_STALE", "HOLD_EXPIRED", "HOLD_UNKNOWN_COMPENSATION",
    "HOLD_UNBOUNDED_STRATEGIC", "HOLD_EVIDENCE_CONFLICT", "HOLD_INCOMPLETE_EVIDENCE",
})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,255}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class GateError(ValueError):
    pass


def _reject_float(_: str, _err=GateError) -> Any:
    raise _err("floating-point JSON is not allowed")


def _reject_constant(_: str, _err=GateError) -> Any:
    raise _err("non-finite JSON is not allowed")


def _parse_int(token: str, _max=MAX_SAFE_INT, _int=int, _len=len, _abs=abs, _err=GateError) -> int:
    if _len(token.lstrip("-")) > 16:
        raise _err("integer outside safe domain")
    value = _int(token)
    if _abs(value) > _max:
        raise _err("integer outside safe domain")
    return value


def _pairs(pairs: list[tuple[str, Any]], _err=GateError) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise _err("duplicate JSON key")
        out[key] = value
    return out


def _freeze_json(
    value: Any,
    path: str = "$",
    _type=type,
    _bool_type=bool,
    _int_type=int,
    _str_type=str,
    _list_type=list,
    _dict_type=dict,
    _len=len,
    _abs=abs,
    _max_int=MAX_SAFE_INT,
    _max_text=MAX_TEXT,
    _max_rows=MAX_ROWS,
    _max_depth=MAX_JSON_DEPTH,
    _max_nodes=MAX_JSON_NODES,
    _unicode_error=UnicodeError,
    _recursion_error=RecursionError,
    _err=GateError,
) -> Any:
    nodes = [0]

    def walk(node: Any, node_path: str, depth: int) -> Any:
        if depth > _max_depth:
            raise _err("JSON nesting exceeds depth limit")
        nodes[0] += 1
        if nodes[0] > _max_nodes:
            raise _err("JSON graph exceeds node limit")
        node_type = _type(node)
        if node is None or node_type is _bool_type:
            return node
        if node_type is _int_type:
            if _abs(node) > _max_int:
                raise _err("integer outside safe domain")
            return node
        if node_type is _str_type:
            if _len(node) > _max_text:
                raise _err("text too long")
            try:
                node.encode("utf-8", "strict")
            except _unicode_error as exc:
                raise _err("invalid UTF-8 text") from exc
            return node
        if node_type is _list_type:
            if _len(node) > _max_rows:
                raise _err("collection too large")
            return [walk(child, f"{node_path}[]", depth + 1) for child in node]
        if node_type is _dict_type:
            if _len(node) > _max_rows:
                raise _err("mapping too large")
            out: dict[str, Any] = {}
            for key, child in node.items():
                if _type(key) is not _str_type:
                    raise _err("object key must be exact str")
                nodes[0] += 1
                if nodes[0] > _max_nodes:
                    raise _err("JSON graph exceeds node limit")
                if _len(key) > _max_text:
                    raise _err("text too long")
                try:
                    key.encode("utf-8", "strict")
                except _unicode_error as exc:
                    raise _err("invalid UTF-8 text") from exc
                out[key] = walk(child, f"{node_path}.{key}", depth + 1)
            return out
        raise _err(f"non-JSON value at {node_path}")

    try:
        return walk(value, path, 0)
    except _recursion_error as exc:
        raise _err("JSON nesting exceeds recursion safety boundary") from exc


def loads_strict_json(
    raw: bytes | str,
    _loads=json.loads,
    _pairs_hook=_pairs,
    _reject_float_fn=_reject_float,
    _parse_int_fn=_parse_int,
    _reject_constant_fn=_reject_constant,
    _freeze=_freeze_json,
    _json_decode_error=json.JSONDecodeError,
    _bytes_type=bytes,
    _str_type=str,
    _type=type,
    _len=len,
    _max_input_bytes=MAX_JSON_INPUT_BYTES,
    _unicode_error=UnicodeError,
    _other_errors=(ValueError, TypeError, RecursionError),
    _err=GateError,
) -> Any:
    try:
        if _type(raw) is _bytes_type:
            if _len(raw) > _max_input_bytes:
                raise _err("JSON input exceeds byte limit")
            text = raw.decode("utf-8", "strict")
        elif _type(raw) is _str_type:
            # UTF-8 byte length is always >= character length, so reject a
            # definitely oversized str before allocating its encoded copy.
            if _len(raw) > _max_input_bytes:
                raise _err("JSON input exceeds byte limit")
            encoded = raw.encode("utf-8", "strict")
            if _len(encoded) > _max_input_bytes:
                raise _err("JSON input exceeds byte limit")
            text = raw
        else:
            raise _err("JSON input must be bytes or exact str")
    except _unicode_error as exc:
        raise _err("invalid UTF-8") from exc
    try:
        value = _loads(
            text,
            object_pairs_hook=_pairs_hook,
            parse_float=_reject_float_fn,
            parse_int=_parse_int_fn,
            parse_constant=_reject_constant_fn,
        )
        return _freeze(value)
    except _err:
        raise
    except (_json_decode_error, *_other_errors) as exc:
        raise _err("invalid JSON") from exc


def _canonical_bytes(
    value: Any,
    _freeze=_freeze_json,
    _dumps=json.dumps,
    _unicode_error=UnicodeError,
    _other_errors=(ValueError, TypeError, RecursionError),
    _err=GateError,
) -> bytes:
    frozen = _freeze(value)
    try:
        return _dumps(frozen, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8", "strict")
    except (_unicode_error, *_other_errors) as exc:
        raise _err("cannot canonicalize JSON") from exc


def _sha(value: Any, _canonical=_canonical_bytes, _sha256=hashlib.sha256) -> str:
    return _sha256(_canonical(value)).hexdigest()


def _exact_keys(obj: Any, keys: set[str], label: str, _type=type, _dict_type=dict, _set=set, _err=GateError) -> dict[str, Any]:
    if _type(obj) is not _dict_type:
        raise _err(f"{label} must be object")
    if _set(obj) != keys:
        raise _err(f"{label} keys mismatch")
    return obj


def _text(value: Any, label: str, *, _type=type, _str_type=str, _len=len, _max=MAX_TEXT, _unicode_error=UnicodeError, _err=GateError) -> str:
    if _type(value) is not _str_type or not value:
        raise _err(f"{label} must be nonempty exact str")
    if _len(value) > _max:
        raise _err(f"{label} too long")
    try:
        value.encode("utf-8", "strict")
    except _unicode_error as exc:
        raise _err(f"{label} invalid UTF-8") from exc
    return value


def _identifier(value: Any, label: str, _text_fn=_text, _id_re=_ID, _err=GateError) -> str:
    value = _text_fn(value, label)
    if not _id_re.fullmatch(value):
        raise _err(f"{label} invalid")
    return value


def _digest(value: Any, label: str, _text_fn=_text, _hex_re=_HEX64, _err=GateError) -> str:
    value = _text_fn(value, label)
    if not _hex_re.fullmatch(value):
        raise _err(f"{label} must be lowercase sha256")
    return value


def _timestamp(value: Any, label: str, _text_fn=_text, _ts_re=_TS, _strptime=datetime.strptime, _utc=timezone.utc, _value_error=ValueError, _err=GateError) -> datetime:
    value = _text_fn(value, label)
    if not _ts_re.fullmatch(value):
        raise _err(f"{label} must be whole-second UTC")
    try:
        dt = _strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_utc)
    except _value_error as exc:
        raise _err(f"{label} invalid timestamp") from exc
    if dt.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise _err(f"{label} noncanonical timestamp")
    return dt


def _format_ts(dt: datetime, _datetime_type=datetime, _type=type, _utc=timezone.utc, _err=GateError) -> str:
    if _type(dt) is not _datetime_type or dt.tzinfo is None or dt.utcoffset() is None:
        raise _err("evaluation time must be exact timezone-aware datetime")
    return dt.astimezone(_utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _positive_int(value: Any, label: str, _type=type, _int_type=int, _max=MAX_SAFE_INT, _err=GateError) -> int:
    if _type(value) is not _int_type or value <= 0 or value > _max:
        raise _err(f"{label} must be positive safe integer")
    return value


def _load_host_key(
    _getenv=os.environ.get,
    _key_name=EVIDENCE_AUTH_ENV,
    _hex_re=_HEX64,
    _type=type,
    _str_type=str,
    _bytes_fromhex=bytes.fromhex,
    _err=GateError,
) -> bytes | None:
    raw = _getenv(_key_name)
    if raw is None:
        return None
    if _type(raw) is not _str_type or not _hex_re.fullmatch(raw):
        raise _err("host evidence authority key must be exactly 32 bytes of lowercase hex")
    return _bytes_fromhex(raw)


# Authority generation is established exactly once when this module is
# initialized. Public validation/compile/verify paths bind to this immutable
# bytes object in function defaults below. Later process-environment mutation
# cannot substitute a new evidence-signing authority.
_INITIAL_EVIDENCE_AUTHORITY_KEY = _load_host_key()


def _evidence_tag(kind: str, row_without_tag: dict[str, Any], key: bytes, _canonical=_canonical_bytes, _hmac_new=hmac.new, _sha256=hashlib.sha256) -> str:
    payload = {"domain": "commons-payoff-path-evidence/v2", "kind": kind, "row": row_without_tag}
    return _hmac_new(key, _canonical(payload), _sha256).hexdigest()


def _verify_evidence_tag(kind: str, row: dict[str, Any], key: bytes, _digest_fn=_digest, _tag_fn=_evidence_tag, _compare=hmac.compare_digest, _err=GateError) -> None:
    tag = _digest_fn(row["auth_tag_hex"], "auth_tag_hex")
    unsigned = {k: v for k, v in row.items() if k != "auth_tag_hex"}
    if not _compare(tag, _tag_fn(kind, unsigned, key)):
        raise _err("evidence authentication failed")


def _validate_term(row: Any, key: bytes, _exact=_exact_keys, _id=_identifier, _dig=_digest, _ts=_timestamp, _pos=_positive_int, _classes=EVIDENCE_CLASSES, _modes=AMOUNT_MODES, _currency=_CURRENCY, _verify_tag=_verify_evidence_tag, _type=type, _str_type=str, _err=GateError) -> dict[str, Any]:
    row = _exact(row, {
        "evidence_id", "subject_work_id", "subject_generation_sha256", "evidence_class",
        "source_id", "source_sha256", "observed_at_utc", "valid_until_utc",
        "amount_mode", "amount_minor", "currency", "auth_tag_hex",
    }, "term evidence")
    _id(row["evidence_id"], "evidence_id")
    _id(row["subject_work_id"], "term subject_work_id")
    _dig(row["subject_generation_sha256"], "term subject generation")
    if row["evidence_class"] not in _classes:
        raise _err("invalid evidence_class")
    _id(row["source_id"], "source_id")
    _dig(row["source_sha256"], "source sha256")
    _ts(row["observed_at_utc"], "observed_at_utc")
    if row["valid_until_utc"] is not None:
        _ts(row["valid_until_utc"], "valid_until_utc")
    if row["amount_mode"] not in _modes:
        raise _err("invalid amount_mode")
    if row["amount_mode"] == "EXACT":
        _pos(row["amount_minor"], "amount_minor")
        if _type(row["currency"]) is not _str_type or not _currency.fullmatch(row["currency"]):
            raise _err("currency must be three uppercase letters")
    elif row["amount_minor"] is not None or row["currency"] is not None:
        raise _err("AMOUNT_UNKNOWN must not carry amount/currency")
    _verify_tag("TERM", row, key)
    return row


def _validate_outcome(row: Any, key: bytes, _exact=_exact_keys, _id=_identifier, _dig=_digest, _ts=_timestamp, _kinds=OUTCOME_KINDS, _verify_tag=_verify_evidence_tag, _err=GateError) -> dict[str, Any]:
    row = _exact(row, {
        "event_id", "subject_work_id", "subject_generation_sha256", "kind",
        "source_id", "source_sha256", "observed_at_utc", "auth_tag_hex",
    }, "outcome evidence")
    _id(row["event_id"], "event_id")
    _id(row["subject_work_id"], "outcome subject_work_id")
    _dig(row["subject_generation_sha256"], "outcome subject generation")
    if row["kind"] not in _kinds:
        raise _err("invalid outcome kind")
    _id(row["source_id"], "outcome source_id")
    _dig(row["source_sha256"], "outcome source sha256")
    _ts(row["observed_at_utc"], "outcome observed_at_utc")
    _verify_tag("OUTCOME", row, key)
    return row


def _validate_plan(plan: Any, _exact=_exact_keys, _text_fn=_text, _pos=_positive_int, _ts=_timestamp) -> dict[str, Any] | None:
    if plan is None:
        return None
    plan = _exact(plan, {"milestone", "effort_ceiling_hours", "review_by_utc"}, "conversion_plan")
    _text_fn(plan["milestone"], "conversion milestone")
    _pos(plan["effort_ceiling_hours"], "effort ceiling")
    _ts(plan["review_by_utc"], "review_by_utc")
    return plan


def _evidence_census_digest(packet: dict[str, Any], _sha_fn=_sha) -> str:
    return _sha_fn({"term_evidence": packet["term_evidence"], "outcome_evidence": packet["outcome_evidence"]})


def _validate_scope_attestation(
    attestation: Any,
    packet: dict[str, Any],
    key: bytes | None,
    now: datetime,
    _exact=_exact_keys,
    _id=_identifier,
    _dig=_digest,
    _ts=_timestamp,
    _tag_fn=_evidence_tag,
    _compare=hmac.compare_digest,
    _census=_evidence_census_digest,
    _max_age=MAX_EVIDENCE_AGE,
    _err=GateError,
) -> tuple[bool, list[str]]:
    if attestation is None:
        return False, ["SCOPE_ATTESTATION_MISSING"]
    attestation = _exact(attestation, {
        "attestation_id", "subject_work_id", "subject_generation_sha256",
        "census_source_id", "census_source_sha256", "evidence_census_sha256",
        "observed_at_utc", "valid_until_utc", "auth_tag_hex",
    }, "scope_attestation")
    _id(attestation["attestation_id"], "scope attestation id")
    _id(attestation["subject_work_id"], "scope subject_work_id")
    _dig(attestation["subject_generation_sha256"], "scope subject generation")
    _id(attestation["census_source_id"], "scope census_source_id")
    _dig(attestation["census_source_sha256"], "scope census_source_sha256")
    _dig(attestation["evidence_census_sha256"], "scope evidence_census_sha256")
    observed = _ts(attestation["observed_at_utc"], "scope observed_at_utc")
    valid_until = _ts(attestation["valid_until_utc"], "scope valid_until_utc")
    _dig(attestation["auth_tag_hex"], "scope auth_tag_hex")

    reasons: list[str] = []
    if key is None:
        reasons.append("SCOPE_AUTHORITY_UNAVAILABLE")
    else:
        unsigned = {k: v for k, v in attestation.items() if k != "auth_tag_hex"}
        if not _compare(attestation["auth_tag_hex"], _tag_fn("SCOPE", unsigned, key)):
            reasons.append("SCOPE_ATTESTATION_AUTH_INVALID")
    if attestation["subject_work_id"] != packet["subject_work_id"] or attestation["subject_generation_sha256"] != packet["subject_generation_sha256"]:
        reasons.append("SCOPE_SUBJECT_GENERATION_MISMATCH")
    if attestation["evidence_census_sha256"] != _census(packet):
        reasons.append("SCOPE_CENSUS_MISMATCH")
    if valid_until < observed:
        reasons.append("SCOPE_VALIDITY_CONFLICT")
    if observed > now:
        reasons.append("SCOPE_ATTESTATION_FUTURE")
    if now - observed > _max_age:
        reasons.append("SCOPE_ATTESTATION_STALE")
    if now >= valid_until:
        reasons.append("SCOPE_ATTESTATION_EXPIRED")
    return not reasons, reasons


def _validate_packet_structure(
    packet: Any,
    _freeze=_freeze_json,
    _exact=_exact_keys,
    _id=_identifier,
    _dig=_digest,
    _classes=PAYOFF_CLASSES,
    _scopes=SCOPE_STATUSES,
    _plan=_validate_plan,
    _schema=SCHEMA_INPUT,
    _max_rows=MAX_ROWS,
    _type=type,
    _list_type=list,
    _len=len,
    _err=GateError,
) -> dict[str, Any]:
    packet = _freeze(packet)
    packet = _exact(packet, {
        "schema", "subject_work_id", "subject_generation_sha256", "payoff_class",
        "evidence_scope_status", "scope_attestation", "term_evidence", "outcome_evidence",
        "conversion_plan",
    }, "packet")
    if packet["schema"] != _schema:
        raise _err("wrong input schema")
    _id(packet["subject_work_id"], "subject_work_id")
    _dig(packet["subject_generation_sha256"], "subject generation")
    if packet["payoff_class"] not in _classes:
        raise _err("invalid payoff_class")
    if packet["evidence_scope_status"] not in _scopes:
        raise _err("invalid evidence_scope_status")
    if _type(packet["term_evidence"]) is not _list_type or _len(packet["term_evidence"]) > _max_rows:
        raise _err("term_evidence must be bounded list")
    if _type(packet["outcome_evidence"]) is not _list_type or _len(packet["outcome_evidence"]) > _max_rows:
        raise _err("outcome_evidence must be bounded list")
    if packet["evidence_scope_status"] == "PARTIAL" and packet["scope_attestation"] is not None:
        raise _err("PARTIAL scope must not carry completeness attestation")
    _plan(packet["conversion_plan"])
    return packet


def _validate_packet(
    packet: Any,
    now: datetime,
    _structure=_validate_packet_structure,
    _authority_key=_INITIAL_EVIDENCE_AUTHORITY_KEY,
    _term=_validate_term,
    _outcome=_validate_outcome,
    _scope=_validate_scope_attestation,
    _sha256=hashlib.sha256,
    _set_type=set,
    _env_name=EVIDENCE_AUTH_ENV,
    _err=GateError,
) -> tuple[dict[str, Any], str | None, bool, list[str]]:
    packet = _structure(packet)
    key = _authority_key
    if (packet["term_evidence"] or packet["outcome_evidence"]) and key is None:
        raise _err(f"host evidence authority unavailable: {_env_name}")

    identities = _set_type()
    if key is not None:
        for row in packet["term_evidence"]:
            _term(row, key)
            if row["evidence_id"] in identities:
                raise _err("duplicate evidence identity")
            identities.add(row["evidence_id"])
        for row in packet["outcome_evidence"]:
            _outcome(row, key)
            if row["event_id"] in identities:
                raise _err("duplicate evidence identity")
            identities.add(row["event_id"])

    if packet["evidence_scope_status"] == "COMPLETE":
        scope_valid, scope_reasons = _scope(packet["scope_attestation"], packet, key, now)
    else:
        scope_valid, scope_reasons = False, ["EVIDENCE_SCOPE_PARTIAL"]
    fingerprint = None if key is None else _sha256(key).hexdigest()
    return packet, fingerprint, scope_valid, scope_reasons


def _receipt_projection(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": receipt["schema"], "compiler_id": receipt["compiler_id"],
        "subject_work_id": receipt["subject_work_id"], "subject_generation_sha256": receipt["subject_generation_sha256"],
        "payoff_class": receipt["payoff_class"], "state": receipt["state"], "reasons": receipt["reasons"],
        "input_digest_sha256": receipt["input_digest_sha256"], "term_fingerprint_sha256": receipt["term_fingerprint_sha256"],
        "conversion_plan_fingerprint_sha256": receipt["conversion_plan_fingerprint_sha256"],
        "scope_attestation_fingerprint_sha256": receipt["scope_attestation_fingerprint_sha256"],
        "evidence_authority_key_fingerprint_sha256": receipt["evidence_authority_key_fingerprint_sha256"],
        "authority": receipt["authority"],
    }


def _compile_at(
    packet: Any,
    now: datetime,
    _validate=_validate_packet,
    _ts=_timestamp,
    _fmt=_format_ts,
    _sha_fn=_sha,
    _cash_classes=CASH_TERM_CLASSES,
    _utc=timezone.utc,
    _max_age=MAX_EVIDENCE_AGE,
    _receipt_schema=SCHEMA_RECEIPT,
    _compiler_id=COMPILER_ID,
    _type=type,
    _datetime_type=datetime,
    _any=any,
    _len=len,
    _set_type=set,
    _err=GateError,
) -> dict[str, Any]:
    if _type(now) is not _datetime_type or now.tzinfo is None or now.utcoffset() is None:
        raise _err("evaluation time must be exact timezone-aware datetime")
    now = now.astimezone(_utc).replace(microsecond=0)
    packet, authority_key_fingerprint, scope_valid, scope_reasons = _validate(packet, now)
    subject = packet["subject_work_id"]
    generation = packet["subject_generation_sha256"]
    payoff_class = packet["payoff_class"]
    reasons: list[str] = []
    conflict = stale = expired = future = False
    exact_terms: list[dict[str, Any]] = []
    matching_terms: list[dict[str, Any]] = []

    for row in packet["term_evidence"]:
        if row["subject_work_id"] != subject or row["subject_generation_sha256"] != generation:
            conflict = True
            continue
        observed = _ts(row["observed_at_utc"], "observed_at_utc")
        if observed > now:
            future = True
        if now - observed > _max_age:
            stale = True
        if row["valid_until_utc"] is not None:
            valid_until = _ts(row["valid_until_utc"], "valid_until_utc")
            if valid_until < observed:
                conflict = True
            if now >= valid_until:
                expired = True
        if row["evidence_class"] == payoff_class:
            matching_terms.append(row)
            if row["amount_mode"] == "EXACT":
                exact_terms.append(row)
        elif row["evidence_class"] != "GENERIC_CONTEXT":
            conflict = True

    outcomes = _set_type()
    for row in packet["outcome_evidence"]:
        if row["subject_work_id"] != subject or row["subject_generation_sha256"] != generation:
            conflict = True
            continue
        observed = _ts(row["observed_at_utc"], "outcome observed_at_utc")
        if observed > now:
            future = True
        if now - observed > _max_age:
            stale = True
        outcomes.add(row["kind"])

    economics = {(row["amount_minor"], row["currency"]) for row in exact_terms}
    if _len(economics) > 1:
        conflict = True
    if exact_terms and _any(row["amount_mode"] == "AMOUNT_UNKNOWN" for row in matching_terms):
        conflict = True

    plan = packet["conversion_plan"]
    if plan is not None and now >= _ts(plan["review_by_utc"], "review_by_utc"):
        expired = True

    if conflict or future:
        state = "HOLD_EVIDENCE_CONFLICT"
        if conflict:
            reasons.append("EVIDENCE_CONFLICT")
        if future:
            reasons.append("FUTURE_EVIDENCE")
    elif "SETTLED" in outcomes:
        state = "HOLD_ALREADY_SETTLED"
        reasons.append("EXACT_WORK_GENERATION_SETTLED")
    elif "ACTIVE_DUPLICATE" in outcomes:
        state = "HOLD_ACTIVE_DUPLICATE"
        reasons.append("ACTIVE_DUPLICATE_OR_CUSTODY_CONFLICT")
    elif not scope_valid:
        state = "HOLD_INCOMPLETE_EVIDENCE"
        reasons.extend(scope_reasons or ["EVIDENCE_SCOPE_UNAUTHENTICATED"])
    elif expired:
        state = "HOLD_EXPIRED"
        reasons.append("PAYOFF_PATH_EXPIRED")
    elif stale:
        state = "HOLD_STALE"
        reasons.append("PAYOFF_EVIDENCE_STALE")
    elif payoff_class in _cash_classes:
        if not matching_terms:
            state = "HOLD_NO_PAYOFF_PATH"
            reasons.append("NO_CLASS_BOUND_COMPENSATION_TERM")
        elif _any(row["amount_mode"] == "AMOUNT_UNKNOWN" for row in matching_terms):
            state = "HOLD_UNKNOWN_COMPENSATION"
            reasons.append("COMPENSATION_AMOUNT_UNKNOWN")
        elif not exact_terms:
            state = "HOLD_NO_PAYOFF_PATH"
            reasons.append("NO_EXACT_COMPENSATION_TERM")
        elif payoff_class == "PAID_WORK":
            state = "PAID_WORK"
            reasons.append("AUTHENTICATED_CURRENT_PAID_WORK_TERM")
        else:
            state = "PAYOFF_BOUND"
            reasons.append("AUTHENTICATED_CURRENT_COMPENSATION_TERM")
    elif payoff_class == "PRODUCT_CONVERSION":
        if matching_terms:
            if _any(row["amount_mode"] == "AMOUNT_UNKNOWN" for row in matching_terms):
                state = "HOLD_UNKNOWN_COMPENSATION"
                reasons.append("COMPENSATION_AMOUNT_UNKNOWN")
            elif exact_terms:
                state = "PAYOFF_BOUND"
                reasons.append("AUTHENTICATED_CURRENT_PRODUCT_CONVERSION_CASH_TERM")
            else:
                state = "HOLD_NO_PAYOFF_PATH"
                reasons.append("NO_EXACT_PRODUCT_CONVERSION_TERM")
        elif plan is not None:
            state = "PAYOFF_BOUND"
            reasons.append("AUTHENTICATED_SCOPE_BOUNDED_PRODUCT_CONVERSION_MILESTONE")
        else:
            state = "HOLD_UNBOUNDED_STRATEGIC"
            reasons.append("PRODUCT_CONVERSION_REQUIRES_CASH_TERM_OR_BOUNDED_PLAN")
    elif payoff_class == "STRATEGIC_UNPAID":
        if plan is None:
            state = "HOLD_UNBOUNDED_STRATEGIC"
            reasons.append("STRATEGIC_UNPAID_REQUIRES_BOUNDED_PLAN")
        else:
            state = "STRATEGIC_UNPAID_BOUNDED"
            reasons.append("AUTHENTICATED_SCOPE_BOUNDED_STRATEGIC_CONVERSION_PLAN")
    else:
        state = "HOLD_INCOMPLETE_EVIDENCE"
        reasons.append("UNHANDLED_PAYOFF_CLASS")

    receipt: dict[str, Any] = {
        "schema": _receipt_schema,
        "compiler_id": _compiler_id,
        "subject_work_id": subject,
        "subject_generation_sha256": generation,
        "payoff_class": payoff_class,
        "evaluated_at_utc": _fmt(now),
        "state": state,
        "reasons": reasons,
        "input_digest_sha256": _sha_fn(packet),
        "term_fingerprint_sha256": _sha_fn(packet["term_evidence"]),
        "conversion_plan_fingerprint_sha256": None if plan is None else _sha_fn(plan),
        "scope_attestation_fingerprint_sha256": None if packet["scope_attestation"] is None else _sha_fn(packet["scope_attestation"]),
        "evidence_authority_key_fingerprint_sha256": authority_key_fingerprint,
        "authority": {
            "contact_authorized": False,
            "muse_election_authorized": False,
            "terms_acceptance_authorized": False,
            "contract_or_signature_authorized": False,
            "submission_authorized": False,
            "invoice_or_receivable_authorized": False,
            "payment_or_funds_movement_authorized": False,
            "cash_receipt_proven": False,
            "revenue_recognized": False,
            "tax_or_accounting_conclusion": False,
            "provider_or_account_mutation_authorized": False,
        },
    }
    receipt["receipt_digest_sha256"] = _sha_fn(receipt)
    return receipt


def _validate_receipt_shape(
    receipt: Any,
    _freeze=_freeze_json,
    _exact=_exact_keys,
    _id=_identifier,
    _dig=_digest,
    _ts=_timestamp,
    _states=STATES,
    _classes=PAYOFF_CLASSES,
    _sha_fn=_sha,
    _schema=SCHEMA_RECEIPT,
    _compiler_id=COMPILER_ID,
    _type=type,
    _list_type=list,
    _str_type=str,
    _dict_type=dict,
    _bool_type=bool,
    _set=set,
    _all=all,
    _any=any,
    _dict_ctor=dict,
    _err=GateError,
) -> dict[str, Any]:
    receipt = _freeze(receipt)
    receipt = _exact(receipt, {
        "schema", "compiler_id", "subject_work_id", "subject_generation_sha256", "payoff_class",
        "evaluated_at_utc", "state", "reasons", "input_digest_sha256", "term_fingerprint_sha256",
        "conversion_plan_fingerprint_sha256", "scope_attestation_fingerprint_sha256",
        "evidence_authority_key_fingerprint_sha256", "authority", "receipt_digest_sha256",
    }, "receipt")
    if receipt["schema"] != _schema or receipt["compiler_id"] != _compiler_id:
        raise _err("wrong receipt schema/compiler")
    _id(receipt["subject_work_id"], "receipt subject_work_id")
    _dig(receipt["subject_generation_sha256"], "receipt subject generation")
    if receipt["payoff_class"] not in _classes:
        raise _err("receipt payoff_class invalid")
    _ts(receipt["evaluated_at_utc"], "receipt evaluated_at_utc")
    if receipt["state"] not in _states:
        raise _err("receipt state invalid")
    if _type(receipt["reasons"]) is not _list_type or not receipt["reasons"] or not _all(_type(x) is _str_type and x for x in receipt["reasons"]):
        raise _err("receipt reasons invalid")
    _dig(receipt["input_digest_sha256"], "input digest")
    _dig(receipt["term_fingerprint_sha256"], "term fingerprint")
    for field in ("conversion_plan_fingerprint_sha256", "scope_attestation_fingerprint_sha256", "evidence_authority_key_fingerprint_sha256"):
        if receipt[field] is not None:
            _dig(receipt[field], field)

    authority = receipt["authority"]
    keys = {
        "contact_authorized", "muse_election_authorized", "terms_acceptance_authorized",
        "contract_or_signature_authorized", "submission_authorized", "invoice_or_receivable_authorized",
        "payment_or_funds_movement_authorized", "cash_receipt_proven", "revenue_recognized",
        "tax_or_accounting_conclusion", "provider_or_account_mutation_authorized",
    }
    if _type(authority) is not _dict_type or _set(authority) != keys:
        raise _err("authority ceiling keys mismatch")
    if _any(_type(authority[key]) is not _bool_type or authority[key] is not False for key in keys):
        raise _err("authority ceiling must be exact false booleans")
    _dig(receipt["receipt_digest_sha256"], "receipt digest")
    without = _dict_ctor(receipt)
    digest = without.pop("receipt_digest_sha256")
    if _sha_fn(without) != digest:
        raise _err("receipt digest mismatch")
    return receipt


def verify_integrity(packet: Any, receipt: Any, _freeze=_freeze_json, _validate_receipt=_validate_receipt_shape, _ts=_timestamp, _compile=_compile_at, _canonical=_canonical_bytes) -> bool:
    frozen_packet = _freeze(packet)
    frozen_receipt = _validate_receipt(receipt)
    evaluated = _ts(frozen_receipt["evaluated_at_utc"], "receipt evaluated_at_utc")
    expected = _compile(frozen_packet, evaluated)
    return _canonical(expected) == _canonical(frozen_receipt)


def _verify_current_at(packet: Any, receipt: Any, now: datetime, _freeze=_freeze_json, _validate_receipt=_validate_receipt_shape, _ts=_timestamp, _compile=_compile_at, _canonical=_canonical_bytes, _projection=_receipt_projection, _utc=timezone.utc, _type=type, _datetime_type=datetime, _err=GateError) -> bool:
    frozen_packet = _freeze(packet)
    frozen_receipt = _validate_receipt(receipt)
    evaluated = _ts(frozen_receipt["evaluated_at_utc"], "receipt evaluated_at_utc")
    if _type(now) is not _datetime_type or now.tzinfo is None or now.utcoffset() is None:
        raise _err("evaluation time must be exact timezone-aware datetime")
    now = now.astimezone(_utc).replace(microsecond=0)
    if evaluated > now:
        return False
    expected_historical = _compile(frozen_packet, evaluated)
    if _canonical(expected_historical) != _canonical(frozen_receipt):
        return False
    current = _compile(frozen_packet, now)
    return _canonical(_projection(current)) == _canonical(_projection(frozen_receipt))


def _make_compile_current(compile_at, freeze, process_now, utc):
    def compile_current(packet: Any) -> dict[str, Any]:
        return compile_at(freeze(packet), process_now(utc))
    return compile_current


def _make_verify_current(verify_at, freeze, process_now, utc):
    def verify_current(packet: Any, receipt: Any) -> bool:
        return verify_at(freeze(packet), freeze(receipt), process_now(utc))
    return verify_current


compile_current = _make_compile_current(_compile_at, _freeze_json, datetime.now, timezone.utc)
verify_current = _make_verify_current(_verify_current_at, _freeze_json, datetime.now, timezone.utc)
del _make_compile_current
del _make_verify_current

# The public validator already captured the immutable authority bytes above.
# Remove the module-global binding so ordinary name replacement cannot become
# a second semantic authority surface.
del _INITIAL_EVIDENCE_AUTHORITY_KEY
