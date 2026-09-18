"""Fail-closed qualification boundary for Colorado CHSD RFP research.

Production starts with NO admitted buyer source and NO admitted qualification
evidence. Runtime JSON cannot promote itself by claiming an authority label.
Future positive evidence requires a reviewed source mutation that pins exact
ids to exact SHA-256 digests.

Threat boundary: runtime JSON is untrusted; the Python process/source is trusted.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Callable, Mapping

OPPORTUNITY_ID = "RFPFHLA20270000013"
PACKET_SCHEMA = "co-chsd-qualification/v1"
RECEIPT_SCHEMA = "co-chsd-qualification-receipt/v1"
MAX_JSON_BYTES = 1_000_000
MAX_JSON_DEPTH = 48
MAX_JSON_NODES = 50_000
MAX_INT_DIGITS = 16
MAX_SAFE_INT = (1 << 53) - 1

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
# Future official-source/evidence admissions are source changes, never packet data.
_PRODUCTION_BUYER_ROOTS: Mapping[str, str] = MappingProxyType({})
_PRODUCTION_EVIDENCE_ROOTS: Mapping[str, str] = MappingProxyType({})


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


def _parse_int(value: str) -> int:
    digits = value[1:] if value.startswith("-") else value
    if not digits or not digits.isdigit() or len(digits) > MAX_INT_DIGITS:
        raise QualificationError("unsafe JSON integer")
    try:
        number = int(value)
    except ValueError as exc:
        raise QualificationError("unsafe JSON integer") from exc
    if abs(number) > MAX_SAFE_INT:
        raise QualificationError("unsafe JSON integer")
    return number


def _validate_tree(value: Any) -> None:
    stack = [(value, 0)]
    seen = set()
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise QualificationError("JSON value exceeds node limit")
        if depth > MAX_JSON_DEPTH:
            raise QualificationError("JSON value exceeds depth limit")
        t = type(current)
        if current is None or t is bool:
            continue
        if t is int:
            if abs(current) > MAX_SAFE_INT:
                raise QualificationError("unsafe JSON integer")
            continue
        if t is float:
            raise QualificationError("floating-point value forbidden")
        if t is str:
            try:
                current.encode("utf-8", "strict")
            except UnicodeEncodeError as exc:
                raise QualificationError("invalid Unicode string") from exc
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
                stack.append((item, depth + 1))
            continue
        raise QualificationError(f"unsupported JSON type: {t.__name__}")


def loads_strict(raw: bytes | str) -> Any:
    if type(raw) is bytes:
        if len(raw) > MAX_JSON_BYTES:
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
        if len(encoded) > MAX_JSON_BYTES:
            raise QualificationError("JSON input exceeds byte limit")
        text = raw
    else:
        raise QualificationError("JSON input must be bytes or str")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_no_dupes,
            parse_float=_reject_float,
            parse_int=_parse_int,
            parse_constant=_reject_constant,
        )
    except QualificationError:
        raise
    except (json.JSONDecodeError, ValueError, OverflowError, RecursionError, UnicodeError) as exc:
        raise QualificationError("invalid JSON") from exc
    _validate_tree(value)
    return value


def canonical_bytes(value: Any) -> bytes:
    _validate_tree(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise QualificationError("value is not canonical JSON") from exc


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise QualificationError(f"{label} must be lowercase SHA-256 hex")
    return value


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise QualificationError(f"{label} must be a non-empty trimmed string")
    return value


def _instant(value: Any, label: str) -> datetime:
    text = _text(value, label)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualificationError(f"{label} must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise QualificationError(f"{label} must include timezone")
    return dt.astimezone(timezone.utc)


def _exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise QualificationError(f"{label} must contain exact keys: {sorted(keys)}")
    return value


def _freeze_roots(roots: Mapping[str, str], label: str) -> dict[str, str]:
    if type(roots) not in (dict, MappingProxyType):
        raise QualificationError(f"{label} must be a mapping")
    out = {}
    for key, value in roots.items():
        key = _text(key, f"{label}.id")
        out[key] = _sha(value, f"{label}[{key}]")
    return out


def _build_engine(
    buyer_roots: Mapping[str, str],
    evidence_roots: Mapping[str, str],
    clock: Callable[[], datetime],
):
    """Build one trusted engine generation.

    This factory is private. Production captures empty reviewed roots and the real
    UTC process clock once. Tests may build synthetic reviewed generations.
    """
    trusted_buyers = _freeze_roots(buyer_roots, "buyer_roots")
    trusted_evidence = _freeze_roots(evidence_roots, "evidence_roots")
    trusted_clock = clock

    def compile_packet(packet: Any) -> dict[str, Any]:
        _validate_tree(packet)
        packet = _exact_keys(
            packet,
            {"schema", "opportunity_id", "buyer_sources", "qualification_evidence"},
            "packet",
        )
        if packet["schema"] != PACKET_SCHEMA:
            raise QualificationError("packet schema mismatch")
        if packet["opportunity_id"] != OPPORTUNITY_ID:
            raise QualificationError("opportunity_id mismatch")

        sources = packet["buyer_sources"]
        if type(sources) is not list:
            raise QualificationError("buyer_sources must be an array")
        admitted_sources = []
        source_ids = set()
        for idx, source in enumerate(sources):
            source = _exact_keys(
                source,
                {
                    "id", "authority", "sha256", "effective_at",
                    "proposal_deadline", "solicitation_id",
                },
                f"buyer_sources[{idx}]",
            )
            sid = _text(source["id"], f"buyer_sources[{idx}].id")
            if sid in source_ids:
                raise QualificationError("duplicate buyer source id")
            source_ids.add(sid)
            digest = _sha(source["sha256"], f"{sid}.sha256")
            if source["authority"] != "BUYER_OFFICIAL":
                continue
            if source["solicitation_id"] != OPPORTUNITY_ID:
                raise QualificationError(f"{sid}.solicitation_id mismatch")
            effective = _instant(source["effective_at"], f"{sid}.effective_at")
            deadline = _instant(source["proposal_deadline"], f"{sid}.proposal_deadline")
            if trusted_buyers.get(sid) != digest:
                continue
            admitted_sources.append((effective, sid, digest, deadline))

        current_buyer = None
        if admitted_sources:
            admitted_sources.sort(key=lambda row: (row[0], row[1]))
            latest_effective = admitted_sources[-1][0]
            latest = [row for row in admitted_sources if row[0] == latest_effective]
            deadlines = {row[3] for row in latest}
            if len(deadlines) != 1:
                raise QualificationError("conflicting current official buyer generation")
            current_buyer = latest[-1]

        rows = packet["qualification_evidence"]
        if type(rows) is not list:
            raise QualificationError("qualification_evidence must be an array")
        evidence_ids = set()
        satisfied = {"OWNER": set(), "PARTNER": set()}
        admitted_evidence = []
        for idx, row in enumerate(rows):
            row = _exact_keys(
                row,
                {"id", "party", "gate", "sha256"},
                f"qualification_evidence[{idx}]",
            )
            eid = _text(row["id"], f"qualification_evidence[{idx}].id")
            if eid in evidence_ids:
                raise QualificationError("duplicate evidence id")
            evidence_ids.add(eid)
            party = row["party"]
            gate = row["gate"]
            if party not in PARTIES:
                raise QualificationError(f"{eid}.party invalid")
            if gate not in ALL_EVIDENCE_GATES:
                raise QualificationError(f"{eid}.gate invalid")
            digest = _sha(row["sha256"], f"{eid}.sha256")
            if trusted_evidence.get(eid) != digest:
                continue
            satisfied[party].add(gate)
            admitted_evidence.append((eid, party, gate, digest))

        now = trusted_clock()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise QualificationError("trusted clock must return aware datetime")
        now = now.astimezone(timezone.utc)

        owner_prime_gaps = [gate for gate in PRIME_GATES if gate not in satisfied["OWNER"]]
        owner_review_gaps = [
            gate for gate in OWNER_REVIEW_GATES if gate not in satisfied["OWNER"]
        ]
        partner_prime_gaps = [gate for gate in PRIME_GATES if gate not in satisfied["PARTNER"]]
        teaming_agreement = "teaming_agreement" in satisfied["PARTNER"]

        commercial_posture = "PRIME_CANDIDATE"
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
            elif "price_approved" in owner_review_gaps:
                state = "HOLD_PRICE"
                reason = "owner-approved price evidence missing"
            elif owner_review_gaps:
                state = "HOLD_EVIDENCE"
                reason = "owner signatory evidence missing"
            else:
                state = "PRIME_READY_FOR_OWNER_REVIEW"
                reason = "all source-owned buyer and owner qualification evidence is admitted"

        normalized = {
            "schema": PACKET_SCHEMA,
            "opportunity_id": OPPORTUNITY_ID,
            "buyer_sources": packet["buyer_sources"],
            "qualification_evidence": packet["qualification_evidence"],
        }
        input_digest = hashlib.sha256(canonical_bytes(normalized)).hexdigest()
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
            "schema": RECEIPT_SCHEMA,
            "opportunity_id": OPPORTUNITY_ID,
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
        result["receipt_sha256"] = hashlib.sha256(canonical_bytes(receipt_payload)).hexdigest()
        return result

    return compile_packet


# Capture one production generation. Runtime callers cannot supply roots or time.
_PRODUCTION_ENGINE = _build_engine(
    _PRODUCTION_BUYER_ROOTS,
    _PRODUCTION_EVIDENCE_ROOTS,
    datetime.now,
)


def compile_packet(packet: Any) -> dict[str, Any]:
    """Compile one runtime packet using the reviewed production generation."""
    return _PRODUCTION_ENGINE(packet)


def compile_json(raw: bytes | str) -> dict[str, Any]:
    """Strict raw JSON ingress."""
    return _PRODUCTION_ENGINE(loads_strict(raw))
