"""Fail-closed qualification boundary for Colorado CHSD RFP research.

Production starts with NO admitted buyer source and NO admitted qualification
evidence. Runtime JSON cannot promote itself by claiming an authority label.
Future positive evidence requires a reviewed source mutation that pins each
entire trusted descriptor generation, including identity, semantic role, and
artifact SHA-256.

Threat boundary: runtime JSON is untrusted; the Python process/source is trusted.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Callable, Mapping

OPPORTUNITY_ID = "CO-CHSD-PURSUIT"
PACKET_SCHEMA = "co-chsd-qualification/v1"
RECEIPT_SCHEMA = "co-chsd-qualification-receipt/v1"
MAX_JSON_BYTES = 1_000_000
MAX_JSON_DEPTH = 48
MAX_JSON_NODES = 50_000
MAX_INT_DIGITS = 16
MAX_SAFE_INT = (1 << 53) - 1

BUYER_KEYS = {
    "id", "authority", "sha256", "effective_at",
    "proposal_deadline", "solicitation_id",
}
EVIDENCE_KEYS = {"id", "party", "gate", "sha256"}
PRIME_GATES = (
    "biztalk_certification",
    "relevant_experience_3y",
    "similar_projects_3",
    "references_2",
    "colorado_vss",
    "soc2_type2",
    "health_data_security",
    "accessibility",
    "insurance",
    "staffing_operations",
)
OWNER_REVIEW_GATES = ("price_approved", "signatory_authorized")
PARTNER_CONTROL_GATES = ("teaming_agreement",)
ALL_EVIDENCE_GATES = frozenset(PRIME_GATES + OWNER_REVIEW_GATES + PARTNER_CONTROL_GATES)
PARTIES = frozenset({"OWNER", "PARTNER"})
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

# Reviewed source-owned trust roots. Production intentionally begins empty.
# A future admission pins the whole descriptor generation, not only its digest.
_PRODUCTION_BUYER_ROOTS: Mapping[str, Mapping[str, str]] = MappingProxyType({})
_PRODUCTION_EVIDENCE_ROOTS: Mapping[str, Mapping[str, str]] = MappingProxyType({})


class QualificationError(ValueError):
    pass


def _pairs_no_dupes(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise QualificationError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_float(value: str):
    raise QualificationError(f"floating-point JSON number forbidden: {value}")


def _reject_constant(value: str):
    raise QualificationError(f"non-finite JSON number forbidden: {value}")


def _parse_int(
    value: str,
    *,
    _max_digits: int = MAX_INT_DIGITS,
    _max_safe: int = MAX_SAFE_INT,
) -> int:
    digits = value[1:] if value.startswith("-") else value
    if not digits or not digits.isdigit() or len(digits) > _max_digits:
        raise QualificationError("unsafe JSON integer")
    try:
        number = int(value)
    except ValueError as exc:
        raise QualificationError("unsafe JSON integer") from exc
    if abs(number) > _max_safe:
        raise QualificationError("unsafe JSON integer")
    return number


def _validate_tree(
    value: Any,
    *,
    _max_nodes: int = MAX_JSON_NODES,
    _max_depth: int = MAX_JSON_DEPTH,
    _max_safe: int = MAX_SAFE_INT,
    _max_bytes: int = MAX_JSON_BYTES,
) -> None:
    stack = [(value, 0)]
    seen = set()
    nodes = 0
    utf8_bytes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > _max_nodes:
            raise QualificationError("JSON value exceeds node limit")
        if depth > _max_depth:
            raise QualificationError("JSON value exceeds depth limit")
        t = type(current)
        if current is None or t is bool:
            continue
        if t is int:
            if abs(current) > _max_safe:
                raise QualificationError("unsafe JSON integer")
            continue
        if t is float:
            raise QualificationError("floating-point value forbidden")
        if t is str:
            try:
                encoded = current.encode("utf-8", "strict")
            except UnicodeEncodeError as exc:
                raise QualificationError("invalid Unicode string") from exc
            utf8_bytes += len(encoded)
            if utf8_bytes > _max_bytes:
                raise QualificationError("JSON value exceeds aggregate string-byte limit")
            continue
        if t is list:
            marker = id(current)
            if marker in seen:
                raise QualificationError("shared/cyclic JSON container")
            seen.add(marker)
            for item in reversed(current):
                stack.append((item, depth + 1))
            continue
        if t is dict:
            marker = id(current)
            if marker in seen:
                raise QualificationError("shared/cyclic JSON container")
            seen.add(marker)
            for key, item in reversed(list(current.items())):
                if type(key) is not str:
                    raise QualificationError("JSON object key must be string")
                try:
                    key_bytes = key.encode("utf-8", "strict")
                except UnicodeEncodeError as exc:
                    raise QualificationError("invalid Unicode object key") from exc
                utf8_bytes += len(key_bytes)
                if utf8_bytes > _max_bytes:
                    raise QualificationError("JSON value exceeds aggregate string-byte limit")
                stack.append((item, depth + 1))
            continue
        raise QualificationError(f"unsupported JSON type: {t.__name__}")


def loads_strict(
    raw: bytes | str,
    *,
    _max_bytes: int = MAX_JSON_BYTES,
    _loads=json.loads,
    _pairs=_pairs_no_dupes,
    _float=_reject_float,
    _integer=_parse_int,
    _constant=_reject_constant,
    _validate=_validate_tree,
) -> Any:
    if type(raw) is bytes:
        if len(raw) > _max_bytes:
            raise QualificationError("JSON input exceeds byte limit")
        try:
            text = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise QualificationError("invalid UTF-8") from exc
    elif type(raw) is str:
        try:
            encoded = raw.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise QualificationError("invalid UTF-8") from exc
        if len(encoded) > _max_bytes:
            raise QualificationError("JSON input exceeds byte limit")
        text = raw
    else:
        raise QualificationError("JSON input must be bytes or str")
    try:
        value = _loads(
            text,
            object_pairs_hook=_pairs,
            parse_float=_float,
            parse_int=_integer,
            parse_constant=_constant,
        )
    except QualificationError:
        raise
    except (json.JSONDecodeError, ValueError, OverflowError, RecursionError, UnicodeError) as exc:
        raise QualificationError("invalid JSON") from exc
    _validate(value)
    return value


def canonical_bytes(
    value: Any,
    *,
    _validate=_validate_tree,
    _dumps=json.dumps,
) -> bytes:
    _validate(value)
    try:
        return _dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise QualificationError("value is not canonical JSON") from exc


def _sha(value: Any, label: str, *, _sha_re=_SHA_RE) -> str:
    if type(value) is not str or _sha_re.fullmatch(value) is None:
        raise QualificationError(f"{label} must be lowercase SHA-256 hex")
    return value


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise QualificationError(f"{label} must be a non-empty trimmed string")
    return value


def _instant(
    value: Any,
    label: str,
    *,
    _text_fn=_text,
    _fromiso=datetime.fromisoformat,
    _utc=timezone.utc,
) -> datetime:
    text = _text_fn(value, label)
    try:
        dt = _fromiso(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualificationError(f"{label} must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise QualificationError(f"{label} must include timezone")
    return dt.astimezone(_utc)


def _exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise QualificationError(f"{label} must contain exact keys: {sorted(keys)}")
    return value


def _validate_buyer_descriptor(
    value: Any,
    label: str,
    *,
    _exact=_exact_keys,
    _keys=frozenset(BUYER_KEYS),
    _text_fn=_text,
    _sha_fn=_sha,
    _instant_fn=_instant,
) -> dict[str, Any]:
    row = _exact(value, set(_keys), label)
    _text_fn(row["id"], f"{label}.id")
    if row["authority"] != "BUYER_OFFICIAL":
        raise QualificationError(f"{label}.authority must be BUYER_OFFICIAL")
    _sha_fn(row["sha256"], f"{label}.sha256")
    _instant_fn(row["effective_at"], f"{label}.effective_at")
    _instant_fn(row["proposal_deadline"], f"{label}.proposal_deadline")
    _text_fn(row["solicitation_id"], f"{label}.solicitation_id")
    return row


def _validate_evidence_descriptor(
    value: Any,
    label: str,
    *,
    _exact=_exact_keys,
    _keys=frozenset(EVIDENCE_KEYS),
    _text_fn=_text,
    _parties=frozenset(PARTIES),
    _gates=frozenset(ALL_EVIDENCE_GATES),
    _sha_fn=_sha,
) -> dict[str, Any]:
    row = _exact(value, set(_keys), label)
    _text_fn(row["id"], f"{label}.id")
    if row["party"] not in _parties:
        raise QualificationError(f"{label}.party invalid")
    if row["gate"] not in _gates:
        raise QualificationError(f"{label}.gate invalid")
    _sha_fn(row["sha256"], f"{label}.sha256")
    return row


def _freeze_buyer_roots(
    roots: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, Any]]:
    if type(roots) not in (dict, MappingProxyType):
        raise QualificationError("buyer_roots must be a mapping")
    out = {}
    for key, value in roots.items():
        key = _text(key, "buyer_roots.id")
        row = dict(_validate_buyer_descriptor(dict(value), f"buyer_roots[{key}]"))
        if row["id"] != key:
            raise QualificationError("buyer root key/id mismatch")
        out[key] = row
    return out


def _freeze_evidence_roots(
    roots: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, Any]]:
    if type(roots) not in (dict, MappingProxyType):
        raise QualificationError("evidence_roots must be a mapping")
    out = {}
    for key, value in roots.items():
        key = _text(key, "evidence_roots.id")
        row = dict(_validate_evidence_descriptor(dict(value), f"evidence_roots[{key}]"))
        if row["id"] != key:
            raise QualificationError("evidence root key/id mismatch")
        out[key] = row
    return out


def _utc_now(_now=datetime.now, _utc=timezone.utc) -> datetime:
    return _now(_utc)


def _build_engine(
    buyer_roots: Mapping[str, Mapping[str, str]],
    evidence_roots: Mapping[str, Mapping[str, str]],
    clock: Callable[[], datetime],
):
    """Build one trusted engine generation.

    This factory is private. Production captures empty reviewed descriptor roots
    and a real UTC process clock once. Tests may build synthetic reviewed
    generations without changing the public runtime API.
    """
    trusted_buyers = _freeze_buyer_roots(buyer_roots)
    trusted_evidence = _freeze_evidence_roots(evidence_roots)
    trusted_clock = clock

    # Seal the reviewed dependency generation against ordinary post-import
    # module-global rebinding. The Python process remains trusted; this is not
    # a claim against bytecode/closure-cell mutation.
    validate_tree = _validate_tree
    exact_keys = _exact_keys
    text_fn = _text
    sha_fn = _sha
    buyer_validator = _validate_buyer_descriptor
    evidence_validator = _validate_evidence_descriptor
    instant_fn = _instant
    canonical_fn = canonical_bytes
    digest_fn = hashlib.sha256
    utc = timezone.utc
    datetime_type = datetime
    packet_schema = PACKET_SCHEMA
    receipt_schema = RECEIPT_SCHEMA
    opportunity_id = OPPORTUNITY_ID
    buyer_keys = set(BUYER_KEYS)
    evidence_keys = set(EVIDENCE_KEYS)
    prime_gates = tuple(PRIME_GATES)
    owner_review_gates = tuple(OWNER_REVIEW_GATES)

    def compile_packet(packet: Any) -> dict[str, Any]:
        validate_tree(packet)
        packet = exact_keys(
            packet,
            {"schema", "opportunity_id", "buyer_sources", "qualification_evidence"},
            "packet",
        )
        if packet["schema"] != packet_schema:
            raise QualificationError("packet schema mismatch")
        if packet["opportunity_id"] != opportunity_id:
            raise QualificationError("opportunity_id mismatch")

        sources = packet["buyer_sources"]
        if type(sources) is not list:
            raise QualificationError("buyer_sources must be an array")
        admitted_sources = []
        source_ids = set()
        for idx, source in enumerate(sources):
            source = exact_keys(source, buyer_keys, f"buyer_sources[{idx}]")
            sid = text_fn(source["id"], f"buyer_sources[{idx}].id")
            if sid in source_ids:
                raise QualificationError("duplicate buyer source id")
            source_ids.add(sid)
            sha_fn(source["sha256"], f"{sid}.sha256")

            # Discovery/nonofficial rows may be retained in the runtime packet,
            # but they never enter controlling buyer authority.
            if source["authority"] != "BUYER_OFFICIAL":
                continue

            buyer_validator(source, f"buyer_sources[{idx}]")
            trusted = trusted_buyers.get(sid)
            if trusted is None or source != trusted:
                continue
            effective = instant_fn(source["effective_at"], f"{sid}.effective_at")
            deadline = instant_fn(source["proposal_deadline"], f"{sid}.proposal_deadline")
            admitted_sources.append((effective, sid, source["sha256"], deadline))

        current_buyer = None
        if admitted_sources:
            admitted_sources.sort(key=lambda row: (row[0], row[1]))
            latest_effective = admitted_sources[-1][0]
            latest = [row for row in admitted_sources if row[0] == latest_effective]
            if len(latest) != 1:
                raise QualificationError("ambiguous current official buyer generation")
            current_buyer = latest[0]

        rows = packet["qualification_evidence"]
        if type(rows) is not list:
            raise QualificationError("qualification_evidence must be an array")
        evidence_ids = set()
        satisfied = {"OWNER": set(), "PARTNER": set()}
        admitted_evidence = []
        for idx, row in enumerate(rows):
            row = evidence_validator(
                exact_keys(row, evidence_keys, f"qualification_evidence[{idx}]"),
                f"qualification_evidence[{idx}]",
            )
            eid = row["id"]
            if eid in evidence_ids:
                raise QualificationError("duplicate evidence id")
            evidence_ids.add(eid)
            trusted = trusted_evidence.get(eid)
            if trusted is None or row != trusted:
                continue
            satisfied[row["party"]].add(row["gate"])
            admitted_evidence.append(
                (eid, row["party"], row["gate"], row["sha256"])
            )

        now = trusted_clock()
        if not isinstance(now, datetime_type) or now.tzinfo is None:
            raise QualificationError("trusted clock must return aware datetime")
        now = now.astimezone(utc)

        owner_prime_gaps = [gate for gate in prime_gates if gate not in satisfied["OWNER"]]
        owner_review_gaps = [
            gate for gate in owner_review_gates if gate not in satisfied["OWNER"]
        ]
        partner_prime_gaps = [gate for gate in prime_gates if gate not in satisfied["PARTNER"]]
        teaming_agreement = "teaming_agreement" in satisfied["PARTNER"]

        commercial_posture = "RESEARCH_HOLD"
        state = "HOLD_EVIDENCE"
        reason = "qualification evidence incomplete"

        if current_buyer is None:
            state = "HOLD_MISSING_BUYER_SOURCE"
            reason = "no source-owned current official buyer generation is admitted"
        else:
            deadline = current_buyer[3]
            if now >= deadline:
                state = "HOLD_DEADLINE"
                reason = "trusted process time is at or after the admitted official deadline"
            elif owner_prime_gaps:
                commercial_posture = "TEAMING_REQUIRED"
                if not partner_prime_gaps and teaming_agreement:
                    state = "TEAMING_REQUIRED"
                    reason = "trusted partner evidence covers prime gaps; owner review of teaming path required"
                elif "biztalk_certification" in owner_prime_gaps:
                    state = "HOLD_CERTIFICATION"
                    reason = "owner-side BizTalk certification evidence missing"
                elif any(
                    gate in owner_prime_gaps
                    for gate in ("relevant_experience_3y", "similar_projects_3", "references_2")
                ):
                    state = "HOLD_EXPERIENCE_REFERENCES"
                    reason = "owner-side experience/project/reference evidence missing"
                elif any(
                    gate in owner_prime_gaps
                    for gate in ("soc2_type2", "health_data_security", "accessibility")
                ):
                    state = "HOLD_SECURITY_COMPLIANCE"
                    reason = "owner-side security/compliance evidence missing"
                elif "colorado_vss" in owner_prime_gaps:
                    state = "HOLD_REGISTRATION_LEGAL"
                    reason = "Colorado VSS evidence missing"
                elif "insurance" in owner_prime_gaps:
                    state = "HOLD_INSURANCE"
                    reason = "insurance evidence missing"
                elif "staffing_operations" in owner_prime_gaps:
                    state = "HOLD_STAFFING_OPERATIONS"
                    reason = "staffing/operations evidence missing"
            else:
                commercial_posture = "PRIME_CANDIDATE"
                if "price_approved" in owner_review_gaps:
                    state = "HOLD_PRICE"
                    reason = "owner-approved price evidence missing"
                elif owner_review_gaps:
                    state = "HOLD_EVIDENCE"
                    reason = "owner signatory evidence missing"
                else:
                    state = "PRIME_READY_FOR_OWNER_REVIEW"
                    reason = "all source-owned buyer and owner qualification evidence is admitted"

        normalized = {
            "schema": packet_schema,
            "opportunity_id": opportunity_id,
            "buyer_sources": packet["buyer_sources"],
            "qualification_evidence": packet["qualification_evidence"],
        }
        input_digest = digest_fn(canonical_fn(normalized)).hexdigest()
        source_receipt = None
        deadline_text = None
        if current_buyer is not None:
            source_receipt = {
                "id": current_buyer[1],
                "sha256": current_buyer[2],
                "effective_at": current_buyer[0].isoformat().replace("+00:00", "Z"),
            }
            deadline_text = current_buyer[3].isoformat().replace("+00:00", "Z")

        result = {
            "schema": receipt_schema,
            "opportunity_id": opportunity_id,
            "evaluated_at": now.isoformat().replace("+00:00", "Z"),
            "state": state,
            "commercial_posture": commercial_posture,
            "reason": reason,
            "official_buyer_source": source_receipt,
            "official_proposal_deadline": deadline_text,
            "owner_prime_gaps": owner_prime_gaps,
            "owner_review_gaps": owner_review_gaps,
            "partner_prime_gaps": partner_prime_gaps,
            "trusted_teaming_agreement": teaming_agreement,
            "admitted_evidence_ids": [row[0] for row in sorted(admitted_evidence)],
            "input_digest_sha256": input_digest,
            "authority": {
                "buyer_contact": False,
                "partner_contact": False,
                "muse": False,
                "provider_mutation": False,
                "sign": False,
                "submit": False,
                "payment": False,
                "revenue": False,
                "public_commons_backlink": False,
            },
        }
        receipt_payload = dict(result)
        result["receipt_sha256"] = digest_fn(canonical_fn(receipt_payload)).hexdigest()
        return result

    return compile_packet


# Capture one production generation. Runtime callers cannot supply roots or time.
_PRODUCTION_ENGINE = _build_engine(
    _PRODUCTION_BUYER_ROOTS,
    _PRODUCTION_EVIDENCE_ROOTS,
    _utc_now,
)


def _build_public_api(engine, strict_loader):
    """Seal the public API over one reviewed production dependency generation."""
    production_engine = engine
    loader = strict_loader

    def compile_packet(packet: Any) -> dict[str, Any]:
        """Compile one runtime packet using the reviewed production generation."""
        return production_engine(packet)

    def compile_json(raw: bytes | str) -> dict[str, Any]:
        """Strict raw JSON ingress using the same reviewed generation."""
        return production_engine(loader(raw))

    return compile_packet, compile_json


compile_packet, compile_json = _build_public_api(_PRODUCTION_ENGINE, loads_strict)
