"""Fail-closed qualification boundary for the Colorado HCPF Hospital Portal pursuit.

Production starts with no admitted buyer source set and no admitted qualification
evidence. Runtime input cannot mint buyer authority, partner qualification,
pricing approval, signature, submission, payment, or revenue state.

Threat boundary: runtime JSON/direct objects are untrusted; the Python
process/source generation is trusted. Public APIs are sealed over one reviewed
production dependency generation and do not reread mutable module globals.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Callable, Mapping

PURSUIT_ID = "CO-HCPF-HOSPITAL-PORTAL"
PACKET_SCHEMA = "co-hcpf-hospital-portal-qualification/v1"
RECEIPT_SCHEMA = "co-hcpf-hospital-portal-qualification-receipt/v1"

MAX_JSON_BYTES = 1_000_000
MAX_JSON_DEPTH = 48
MAX_JSON_NODES = 50_000
MAX_INT_DIGITS = 16
MAX_SAFE_INT = (1 << 53) - 1

SOURCE_KEYS = frozenset(
    {
        "id",
        "authority",
        "sha256",
        "effective_at",
        "solicitation_id",
        "proposal_deadline",
        "inquiry_deadline",
        "submission_route",
        "pricing_generation",
        "annual_cap_usd",
        "funded_sfys",
        "five_year_cap_usd",
    }
)
EVIDENCE_KEYS = frozenset({"id", "party", "gate", "subject_person_id", "sha256"})
ROSTER_KEYS = frozenset({"id", "sha256", "assignments"})
PARTIES = frozenset({"OWNER", "PARTNER"})

TEAM_GATES = (
    "organizational_experience",
    "similar_projects",
    "references",
    "hospital_reporting_domain",
    "security_assessment_and_hosting",
    "hipaa_baa_compliance",
    "wcag_2_1_aa_accessibility",
    "insurance_legal",
    "staffing_transition",
    "support_operations",
)
PERSONNEL_GATES = (
    "project_lead_qualifications",
    "project_manager_qualifications",
    "web_app_lead_qualifications",
    "quality_lead_qualifications",
)
PERSONNEL_ROLE_BY_GATE = MappingProxyType(
    {
        "project_lead_qualifications": "project_lead",
        "project_manager_qualifications": "project_manager",
        "web_app_lead_qualifications": "web_app_lead",
        "quality_lead_qualifications": "quality_lead",
    }
)
REQUIRED_PERSONNEL_ROLES = tuple(PERSONNEL_ROLE_BY_GATE.values())
OWNER_CONTROL_GATES = (
    "colorado_vss_legal",
    "teaming_agreement",
    "price_approved",
    "signatory_authorized",
)
ALL_GATES = frozenset(TEAM_GATES + PERSONNEL_GATES + OWNER_CONTROL_GATES)

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

# Reviewed source-owned generations. Intentionally empty until exact current
# Colorado VSS attachment bytes and qualification evidence are retained.
_PRODUCTION_SOURCE_ROOTS: Mapping[str, Mapping[str, Any]] = MappingProxyType({})
_PRODUCTION_EVIDENCE_ROOTS: Mapping[str, Mapping[str, Any]] = MappingProxyType({})
_PRODUCTION_ROSTER_ROOTS: Mapping[str, Mapping[str, Any]] = MappingProxyType({})


class QualificationError(ValueError):
    pass


def _pairs_no_dupes(pairs, *, _error=QualificationError):
    out = {}
    for key, value in pairs:
        if key in out:
            raise _error(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_float(value: str, *, _error=QualificationError):
    raise _error(f"floating-point JSON number forbidden: {value}")


def _reject_constant(value: str, *, _error=QualificationError):
    raise _error(f"non-finite JSON number forbidden: {value}")


def _parse_int(
    value: str,
    *,
    _max_digits: int = MAX_INT_DIGITS,
    _max_safe: int = MAX_SAFE_INT,
    _error=QualificationError,
) -> int:
    digits = value[1:] if value.startswith("-") else value
    if not digits or not digits.isdigit() or len(digits) > _max_digits:
        raise _error("unsafe JSON integer")
    try:
        number = int(value)
    except ValueError as exc:
        raise _error("unsafe JSON integer") from exc
    if abs(number) > _max_safe:
        raise _error("unsafe JSON integer")
    return number


def _validate_tree(
    value: Any,
    *,
    _max_nodes: int = MAX_JSON_NODES,
    _max_depth: int = MAX_JSON_DEPTH,
    _max_safe: int = MAX_SAFE_INT,
    _max_bytes: int = MAX_JSON_BYTES,
    _error=QualificationError,
) -> None:
    stack = [(value, 0)]
    seen = set()
    nodes = 0
    utf8_bytes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > _max_nodes:
            raise _error("JSON value exceeds node limit")
        if depth > _max_depth:
            raise _error("JSON value exceeds depth limit")
        t = type(current)
        if current is None or t is bool:
            continue
        if t is int:
            if abs(current) > _max_safe:
                raise _error("unsafe JSON integer")
            continue
        if t is float:
            raise _error("floating-point value forbidden")
        if t is str:
            try:
                encoded = current.encode("utf-8", "strict")
            except UnicodeEncodeError as exc:
                raise _error("invalid Unicode string") from exc
            utf8_bytes += len(encoded)
            if utf8_bytes > _max_bytes:
                raise _error("JSON value exceeds aggregate string-byte limit")
            continue
        if t is list:
            marker = id(current)
            if marker in seen:
                raise _error("shared/cyclic JSON container")
            seen.add(marker)
            for item in reversed(current):
                stack.append((item, depth + 1))
            continue
        if t is dict:
            marker = id(current)
            if marker in seen:
                raise _error("shared/cyclic JSON container")
            seen.add(marker)
            for key, item in reversed(list(current.items())):
                if type(key) is not str:
                    raise _error("JSON object key must be string")
                try:
                    key_bytes = key.encode("utf-8", "strict")
                except UnicodeEncodeError as exc:
                    raise _error("invalid Unicode object key") from exc
                utf8_bytes += len(key_bytes)
                if utf8_bytes > _max_bytes:
                    raise _error("JSON value exceeds aggregate string-byte limit")
                stack.append((item, depth + 1))
            continue
        raise _error(f"unsupported JSON type: {t.__name__}")


def _snapshot_json(
    value: Any,
    *,
    _max_nodes: int = MAX_JSON_NODES,
    _max_depth: int = MAX_JSON_DEPTH,
    _max_safe: int = MAX_SAFE_INT,
    _max_bytes: int = MAX_JSON_BYTES,
    _error=QualificationError,
    _type=type,
    _id=id,
    _tuple=tuple,
) -> Any:
    """Detach one bounded exact-JSON generation from caller-owned containers.

    The snapshot is the only graph semantic/trust checks may inspect. A caller
    may mutate its original graph before, during, or after this copy; later
    admission, receipt, and digest logic all consume only the detached graph.
    """
    seen: set[int] = set()
    nodes = 0
    utf8_bytes = 0

    def clone(current: Any, depth: int) -> Any:
        nonlocal nodes, utf8_bytes
        nodes += 1
        if nodes > _max_nodes:
            raise _error("JSON value exceeds node limit")
        if depth > _max_depth:
            raise _error("JSON value exceeds depth limit")
        t = _type(current)
        if current is None or t is bool:
            return current
        if t is int:
            if abs(current) > _max_safe:
                raise _error("unsafe JSON integer")
            return current
        if t is float:
            raise _error("floating-point value forbidden")
        if t is str:
            try:
                encoded = current.encode("utf-8", "strict")
            except UnicodeEncodeError as exc:
                raise _error("invalid Unicode string") from exc
            utf8_bytes += len(encoded)
            if utf8_bytes > _max_bytes:
                raise _error("JSON value exceeds aggregate string-byte limit")
            return current
        if t is list:
            marker = _id(current)
            if marker in seen:
                raise _error("shared/cyclic JSON container")
            seen.add(marker)
            try:
                items = _tuple(current)
            except RuntimeError as exc:
                raise _error("input mutated during snapshot") from exc
            return [clone(item, depth + 1) for item in items]
        if t is dict:
            marker = _id(current)
            if marker in seen:
                raise _error("shared/cyclic JSON container")
            seen.add(marker)
            try:
                items = _tuple(current.items())
            except RuntimeError as exc:
                raise _error("input mutated during snapshot") from exc
            out: dict[str, Any] = {}
            for key, item in items:
                if _type(key) is not str:
                    raise _error("JSON object key must be string")
                try:
                    key_bytes = key.encode("utf-8", "strict")
                except UnicodeEncodeError as exc:
                    raise _error("invalid Unicode object key") from exc
                utf8_bytes += len(key_bytes)
                if utf8_bytes > _max_bytes:
                    raise _error("JSON value exceeds aggregate string-byte limit")
                out[key] = clone(item, depth + 1)
            return out
        raise _error(f"unsupported JSON type: {t.__name__}")

    return clone(value, 0)


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
    _error=QualificationError,
    _json_error=json.JSONDecodeError,
) -> Any:
    if type(raw) is bytes:
        if len(raw) > _max_bytes:
            raise _error("JSON input exceeds byte limit")
        try:
            text = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise _error("invalid UTF-8") from exc
    elif type(raw) is str:
        try:
            encoded = raw.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise _error("invalid UTF-8") from exc
        if len(encoded) > _max_bytes:
            raise _error("JSON input exceeds byte limit")
        text = raw
    else:
        raise _error("JSON input must be bytes or str")
    try:
        value = _loads(
            text,
            object_pairs_hook=_pairs,
            parse_float=_float,
            parse_int=_integer,
            parse_constant=_constant,
        )
    except _error:
        raise
    except (_json_error, ValueError, OverflowError, RecursionError, UnicodeError) as exc:
        raise _error("invalid JSON") from exc
    _validate(value)
    return value


def canonical_bytes(
    value: Any,
    *,
    _validate=_validate_tree,
    _dumps=json.dumps,
    _error=QualificationError,
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
        raise _error("value is not canonical JSON") from exc


def _text(value: Any, label: str, *, _error=QualificationError) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise _error(f"{label} must be a non-empty trimmed string")
    return value


def _sha(value: Any, label: str, *, _re=_SHA_RE, _error=QualificationError) -> str:
    if type(value) is not str or _re.fullmatch(value) is None:
        raise _error(f"{label} must be lowercase SHA-256 hex")
    return value


def _positive_int(
    value: Any,
    label: str,
    *,
    _max_safe=MAX_SAFE_INT,
    _error=QualificationError,
) -> int:
    if type(value) is not int or value <= 0 or value > _max_safe:
        raise _error(f"{label} must be a positive safe integer")
    return value


def _instant(
    value: Any,
    label: str,
    *,
    _text_fn=_text,
    _fromiso=datetime.fromisoformat,
    _utc=timezone.utc,
    _error=QualificationError,
) -> datetime:
    text = _text_fn(value, label)
    try:
        dt = _fromiso(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _error(f"{label} must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise _error(f"{label} must include timezone")
    return dt.astimezone(_utc)


def _exact_keys(value: Any, keys: frozenset[str] | set[str], label: str, *, _error=QualificationError):
    if type(value) is not dict or set(value) != set(keys):
        raise _error(f"{label} must contain exact keys: {sorted(keys)}")
    return value


def _validate_source_descriptor(
    value: Any,
    label: str,
    *,
    _exact=_exact_keys,
    _keys=SOURCE_KEYS,
    _text_fn=_text,
    _sha_fn=_sha,
    _instant_fn=_instant,
    _positive=_positive_int,
    _error=QualificationError,
):
    row = _exact(value, _keys, label)
    _text_fn(row["id"], f"{label}.id")
    if row["authority"] != "BUYER_SOURCE_SET":
        raise _error(f"{label}.authority must be BUYER_SOURCE_SET")
    _sha_fn(row["sha256"], f"{label}.sha256")
    effective = _instant_fn(row["effective_at"], f"{label}.effective_at")
    proposal = _instant_fn(row["proposal_deadline"], f"{label}.proposal_deadline")
    inquiry = _instant_fn(row["inquiry_deadline"], f"{label}.inquiry_deadline")
    if inquiry > proposal:
        raise _error(f"{label}.inquiry_deadline must not exceed proposal deadline")
    if effective > proposal:
        raise _error(f"{label}.effective_at must not exceed proposal deadline")
    _text_fn(row["solicitation_id"], f"{label}.solicitation_id")
    _text_fn(row["submission_route"], f"{label}.submission_route")
    _text_fn(row["pricing_generation"], f"{label}.pricing_generation")
    annual = _positive(row["annual_cap_usd"], f"{label}.annual_cap_usd")
    sfys = _positive(row["funded_sfys"], f"{label}.funded_sfys")
    total = _positive(row["five_year_cap_usd"], f"{label}.five_year_cap_usd")
    if annual * sfys != total:
        raise _error(f"{label}.pricing arithmetic inconsistent")
    return row


def _validate_evidence_descriptor(
    value: Any,
    label: str,
    *,
    _exact=_exact_keys,
    _keys=EVIDENCE_KEYS,
    _text_fn=_text,
    _sha_fn=_sha,
    _parties=PARTIES,
    _gates=ALL_GATES,
    _personnel=frozenset(PERSONNEL_GATES),
    _owner_only=frozenset(OWNER_CONTROL_GATES),
    _error=QualificationError,
):
    row = _exact(value, _keys, label)
    _text_fn(row["id"], f"{label}.id")
    if row["party"] not in _parties:
        raise _error(f"{label}.party invalid")
    if row["gate"] not in _gates:
        raise _error(f"{label}.gate invalid")
    if row["party"] == "PARTNER" and row["gate"] in _owner_only:
        raise _error(f"{label}.gate is owner-controlled")
    subject = row["subject_person_id"]
    if row["gate"] in _personnel:
        _text_fn(subject, f"{label}.subject_person_id")
    elif subject is not None:
        raise _error(f"{label}.subject_person_id must be null for non-personnel evidence")
    _sha_fn(row["sha256"], f"{label}.sha256")
    return row


def _validate_roster_descriptor(
    value: Any,
    label: str,
    *,
    _exact=_exact_keys,
    _keys=ROSTER_KEYS,
    _roles=REQUIRED_PERSONNEL_ROLES,
    _text_fn=_text,
    _sha_fn=_sha,
    _error=QualificationError,
):
    row = _exact(value, _keys, label)
    _text_fn(row["id"], f"{label}.id")
    _sha_fn(row["sha256"], f"{label}.sha256")
    assignments = row["assignments"]
    _exact(assignments, frozenset(_roles), f"{label}.assignments")
    people = []
    for role in _roles:
        people.append(_text_fn(assignments[role], f"{label}.assignments.{role}"))
    if len(set(people)) != len(people):
        raise _error(f"{label}.assignments must bind distinct people to required roles")
    return row


def _freeze_source_roots(roots: Mapping[str, Mapping[str, Any]]):
    if type(roots) not in (dict, MappingProxyType):
        raise QualificationError("source_roots must be a mapping")
    out = {}
    for key, value in roots.items():
        key = _text(key, "source_roots.id")
        row = dict(_validate_source_descriptor(dict(value), f"source_roots[{key}]"))
        if row["id"] != key:
            raise QualificationError("source root key/id mismatch")
        out[key] = row
    return out


def _freeze_evidence_roots(roots: Mapping[str, Mapping[str, Any]]):
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


def _freeze_roster_roots(roots: Mapping[str, Mapping[str, Any]]):
    if type(roots) not in (dict, MappingProxyType):
        raise QualificationError("roster_roots must be a mapping")
    out = {}
    for key, value in roots.items():
        key = _text(key, "roster_roots.id")
        row = dict(_validate_roster_descriptor(dict(value), f"roster_roots[{key}]"))
        row["assignments"] = dict(row["assignments"])
        if row["id"] != key:
            raise QualificationError("roster root key/id mismatch")
        out[key] = row
    return out


def _utc_now(_now=datetime.now, _utc=timezone.utc) -> datetime:
    return _now(_utc)


def _build_engine(
    source_roots: Mapping[str, Mapping[str, Any]],
    evidence_roots: Mapping[str, Mapping[str, Any]],
    roster_roots: Mapping[str, Mapping[str, Any]],
    clock: Callable[[], datetime],
):
    trusted_sources = _freeze_source_roots(source_roots)
    trusted_evidence = _freeze_evidence_roots(evidence_roots)
    trusted_rosters = _freeze_roster_roots(roster_roots)
    trusted_clock = clock

    # Seal this generation against ordinary module-global rebinding.
    snapshot_json = _snapshot_json
    validate_tree = _validate_tree
    exact_keys = _exact_keys
    text_fn = _text
    sha_fn = _sha
    source_validator = _validate_source_descriptor
    evidence_validator = _validate_evidence_descriptor
    roster_validator = _validate_roster_descriptor
    instant_fn = _instant
    canonical_fn = canonical_bytes
    digest_fn = hashlib.sha256
    datetime_type = datetime
    utc = timezone.utc
    packet_schema = PACKET_SCHEMA
    receipt_schema = RECEIPT_SCHEMA
    pursuit_id = PURSUIT_ID
    source_keys = SOURCE_KEYS
    evidence_keys = EVIDENCE_KEYS
    roster_keys = ROSTER_KEYS
    team_gates = tuple(TEAM_GATES)
    personnel_gates = tuple(PERSONNEL_GATES)
    personnel_role_by_gate = dict(PERSONNEL_ROLE_BY_GATE)
    owner_control_gates = tuple(OWNER_CONTROL_GATES)

    def compile_packet(packet: Any) -> dict[str, Any]:
        packet = snapshot_json(packet)
        validate_tree(packet)
        packet = exact_keys(
            packet,
            frozenset({
                "schema",
                "pursuit_id",
                "buyer_source_sets",
                "proposed_roster",
                "qualification_evidence",
            }),
            "packet",
        )
        if packet["schema"] != packet_schema:
            raise QualificationError("packet schema mismatch")
        if packet["pursuit_id"] != pursuit_id:
            raise QualificationError("pursuit_id mismatch")

        rows = packet["buyer_source_sets"]
        if type(rows) is not list:
            raise QualificationError("buyer_source_sets must be an array")
        source_ids = set()
        admitted = []
        for idx, row in enumerate(rows):
            row = exact_keys(row, source_keys, f"buyer_source_sets[{idx}]")
            sid = text_fn(row["id"], f"buyer_source_sets[{idx}].id")
            if sid in source_ids:
                raise QualificationError("duplicate buyer source set id")
            source_ids.add(sid)
            sha_fn(row["sha256"], f"{sid}.sha256")
            if row["authority"] != "BUYER_SOURCE_SET":
                continue
            source_validator(row, f"buyer_source_sets[{idx}]")
            trusted = trusted_sources.get(sid)
            if trusted is None or row != trusted:
                continue
            effective = instant_fn(row["effective_at"], f"{sid}.effective_at")
            proposal = instant_fn(row["proposal_deadline"], f"{sid}.proposal_deadline")
            inquiry = instant_fn(row["inquiry_deadline"], f"{sid}.inquiry_deadline")
            admitted.append((effective, sid, proposal, inquiry, row))

        current_source = None
        if admitted:
            admitted.sort(key=lambda item: (item[0], item[1]))
            latest_effective = admitted[-1][0]
            latest = [item for item in admitted if item[0] == latest_effective]
            if len(latest) != 1:
                raise QualificationError("ambiguous current official buyer generation")
            current_source = latest[0]

        roster_row = packet["proposed_roster"]
        current_roster = None
        if roster_row is not None:
            roster_row = roster_validator(
                exact_keys(roster_row, roster_keys, "proposed_roster"),
                "proposed_roster",
            )
            trusted_roster = trusted_rosters.get(roster_row["id"])
            if trusted_roster is not None and roster_row == trusted_roster:
                current_roster = roster_row

        evidence = packet["qualification_evidence"]
        if type(evidence) is not list:
            raise QualificationError("qualification_evidence must be an array")
        evidence_ids = set()
        owner_gates = set()
        partner_gates = set()
        admitted_evidence = []
        matched_personnel: dict[str, tuple[str, str, str]] = {}
        for idx, row in enumerate(evidence):
            row = evidence_validator(
                exact_keys(row, evidence_keys, f"qualification_evidence[{idx}]"),
                f"qualification_evidence[{idx}]",
            )
            eid = row["id"]
            if eid in evidence_ids:
                raise QualificationError("duplicate qualification evidence id")
            evidence_ids.add(eid)
            trusted = trusted_evidence.get(eid)
            if trusted is None or row != trusted:
                continue

            admitted_evidence.append(
                (
                    eid,
                    row["party"],
                    row["gate"],
                    row["subject_person_id"] or "",
                    row["sha256"],
                )
            )
            gate = row["gate"]
            if gate in personnel_gates:
                if current_roster is None:
                    continue
                role = personnel_role_by_gate[gate]
                proposed_person = current_roster["assignments"][role]
                if row["subject_person_id"] != proposed_person:
                    continue
                if gate in matched_personnel:
                    raise QualificationError(
                        f"multiple admitted personnel evidence bindings for {gate}"
                    )
                matched_personnel[gate] = (eid, row["party"], proposed_person)

            if row["party"] == "OWNER":
                owner_gates.add(gate)
            else:
                partner_gates.add(gate)

        now = trusted_clock()
        if not isinstance(now, datetime_type) or now.tzinfo is None:
            raise QualificationError("trusted clock must return aware datetime")
        now = now.astimezone(utc)

        team_union = owner_gates | partner_gates
        team_gaps = [gate for gate in team_gates if gate not in team_union]
        personnel_gaps = [gate for gate in personnel_gates if gate not in team_union]
        partner_required_gates = sorted(
            gate
            for gate in (partner_gates - owner_gates)
            if gate in set(team_gates) | set(personnel_gates)
        )
        teaming_agreement = "teaming_agreement" in owner_gates
        required_owner_controls = [
            gate
            for gate in owner_control_gates
            if gate != "teaming_agreement" or partner_required_gates
        ]
        owner_control_gaps = [
            gate for gate in required_owner_controls if gate not in owner_gates
        ]

        state = "HOLD_EVIDENCE"
        commercial_posture = "RESEARCH_HOLD"
        reason = "qualification evidence incomplete"

        if current_source is None:
            state = "HOLD_MISSING_BUYER_SOURCE"
            reason = "no source-owned current official buyer source set is admitted"
        elif now >= current_source[2]:
            state = "HOLD_DEADLINE"
            reason = "trusted process time is at or after the admitted official proposal deadline"
        elif team_gaps:
            commercial_posture = "QUALIFICATION_HOLD"
            experience = {
                "organizational_experience",
                "similar_projects",
                "references",
                "hospital_reporting_domain",
            }
            security = {
                "security_assessment_and_hosting",
                "hipaa_baa_compliance",
                "wcag_2_1_aa_accessibility",
            }
            if any(gate in experience for gate in team_gaps):
                state = "HOLD_EXPERIENCE_REFERENCES"
                reason = "team organizational experience/reference evidence incomplete"
            elif any(gate in security for gate in team_gaps):
                state = "HOLD_SECURITY_COMPLIANCE"
                reason = "team security/HIPAA/accessibility evidence incomplete"
            else:
                state = "HOLD_STAFFING_OPERATIONS"
                reason = "team insurance/staffing/support evidence incomplete"
        elif current_roster is None:
            commercial_posture = "QUALIFICATION_HOLD"
            state = "HOLD_PERSONNEL_ROSTER"
            reason = "no source-owned proposed-personnel roster is admitted"
        elif personnel_gaps:
            commercial_posture = "QUALIFICATION_HOLD"
            state = "HOLD_PERSONNEL"
            reason = "required evidence is not bound to every proposed key person"
        elif "colorado_vss_legal" not in owner_gates:
            commercial_posture = "QUALIFICATION_HOLD"
            state = "HOLD_REGISTRATION_LEGAL"
            reason = "prime-side Colorado VSS/legal evidence missing"
        elif partner_required_gates and not teaming_agreement:
            commercial_posture = "TEAMING_REQUIRED"
            state = "TEAMING_REQUIRED"
            reason = "partner evidence is required but no source-owned teaming agreement is admitted"
        elif "price_approved" not in owner_gates:
            commercial_posture = (
                "PRIME_TEAM_CANDIDATE" if partner_required_gates else "PRIME_CANDIDATE"
            )
            state = "HOLD_PRICE"
            reason = "owner-approved price evidence missing"
        elif "signatory_authorized" not in owner_gates:
            commercial_posture = (
                "PRIME_TEAM_CANDIDATE" if partner_required_gates else "PRIME_CANDIDATE"
            )
            state = "HOLD_EVIDENCE"
            reason = "owner signatory evidence missing"
        else:
            commercial_posture = (
                "PRIME_TEAM_CANDIDATE" if partner_required_gates else "PRIME_CANDIDATE"
            )
            state = "RESPONSE_READY_FOR_OWNER_REVIEW"
            reason = "source-owned buyer and qualification evidence is complete for owner review"

        normalized = {
            "schema": packet_schema,
            "pursuit_id": pursuit_id,
            "buyer_source_sets": packet["buyer_source_sets"],
            "proposed_roster": packet["proposed_roster"],
            "qualification_evidence": packet["qualification_evidence"],
        }
        input_digest = digest_fn(canonical_fn(normalized)).hexdigest()

        source_receipt = None
        if current_source is not None:
            row = current_source[4]
            source_receipt = {
                "id": row["id"],
                "sha256": row["sha256"],
                "solicitation_id": row["solicitation_id"],
                "effective_at": current_source[0].isoformat().replace("+00:00", "Z"),
                "proposal_deadline": current_source[2].isoformat().replace("+00:00", "Z"),
                "inquiry_deadline": current_source[3].isoformat().replace("+00:00", "Z"),
                "submission_route": row["submission_route"],
                "pricing_generation": row["pricing_generation"],
                "annual_cap_usd": row["annual_cap_usd"],
                "funded_sfys": row["funded_sfys"],
                "five_year_cap_usd": row["five_year_cap_usd"],
            }

        roster_receipt = None
        if current_roster is not None:
            roster_receipt = {
                "id": current_roster["id"],
                "sha256": current_roster["sha256"],
                "assignments": dict(current_roster["assignments"]),
            }
        personnel_bindings = [
            {
                "gate": gate,
                "role": personnel_role_by_gate[gate],
                "evidence_id": binding[0],
                "party": binding[1],
                "subject_person_id": binding[2],
            }
            for gate, binding in sorted(matched_personnel.items())
        ]

        result = {
            "schema": receipt_schema,
            "pursuit_id": pursuit_id,
            "evaluated_at": now.isoformat().replace("+00:00", "Z"),
            "state": state,
            "commercial_posture": commercial_posture,
            "reason": reason,
            "official_source_set": source_receipt,
            "proposed_roster": roster_receipt,
            "team_gaps": team_gaps,
            "personnel_gaps": personnel_gaps,
            "personnel_bindings": personnel_bindings,
            "owner_control_gaps": owner_control_gaps,
            "partner_required_gates": partner_required_gates,
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
                "box_upload": False,
                "payment": False,
                "revenue": False,
                "public_commons_backlink": False,
            },
        }
        receipt_payload = dict(result)
        result["receipt_sha256"] = digest_fn(canonical_fn(receipt_payload)).hexdigest()
        return result

    return compile_packet


_PRODUCTION_ENGINE = _build_engine(
    _PRODUCTION_SOURCE_ROOTS,
    _PRODUCTION_EVIDENCE_ROOTS,
    _PRODUCTION_ROSTER_ROOTS,
    _utc_now,
)


def _build_public_api(engine, strict_loader):
    production_engine = engine
    loader = strict_loader

    def compile_packet(packet: Any) -> dict[str, Any]:
        return production_engine(packet)

    def compile_json(raw: bytes | str) -> dict[str, Any]:
        return production_engine(loader(raw))

    return compile_packet, compile_json


compile_packet, compile_json = _build_public_api(_PRODUCTION_ENGINE, loads_strict)
