"""Fail-closed pursuit gate for Hamilton County RFP 065-26/JW.

Discovery mirrors can guide investigation but cannot establish buyer requirements,
deadlines, teaming permission, submission authority, or qualification evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

OPPORTUNITY_ID = "065-26/JW"
BUYER_CONTROL_FIELDS = {
    "response_deadline", "question_deadline", "submission_mechanics",
    "teaming_rules", "evaluation_criteria", "mandatory_requirements",
}
SOURCE_AUTHORITIES = {
    "OFFICIAL_PORTAL_ENTRY", "OFFICIAL_CONTROLLING_PACKET", "OFFICIAL_ADDENDUM",
    "MIRROR", "INTERNAL_EVIDENCE",
}
PRIME_GATES = (
    "submission_mechanics", "eligibility", "security_compliance",
    "past_performance", "insurance_legal", "pricing",
)
SPECIALIST_GATES = ("integration_engineering", "validation_evidence", "delivery_capacity")
ALL_GATES = PRIME_GATES + SPECIALIST_GATES + ("partner_prime",)
EVIDENCE_CLASSES = {
    "submission_mechanics": {"OFFICIAL_REQUIREMENT"},
    "eligibility": {"OFFICIAL_REQUIREMENT", "OWNER_QUALIFICATION"},
    "security_compliance": {"OFFICIAL_REQUIREMENT", "OWNER_QUALIFICATION"},
    "past_performance": {"OWNER_QUALIFICATION"},
    "insurance_legal": {"OFFICIAL_REQUIREMENT", "OWNER_QUALIFICATION"},
    "pricing": {"OFFICIAL_REQUIREMENT", "OWNER_PRICING"},
    "integration_engineering": {"OWNER_CAPABILITY"},
    "validation_evidence": {"OWNER_CAPABILITY"},
    "delivery_capacity": {"OWNER_CAPACITY"},
    "partner_prime": {"PARTNER_DUE_DILIGENCE"},
}
OFFICIAL_EVIDENCE_CLASSES = {"OFFICIAL_REQUIREMENT"}


class GateError(ValueError):
    pass


def _pairs_no_dupes(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise GateError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value):
    raise GateError(f"non-finite JSON number: {value}")


def loads_strict(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_pairs_no_dupes, parse_constant=_reject_constant)
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError(str(exc)) from exc


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise GateError(f"{label} must be a JSON boolean")
    return value


def _str(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise GateError(f"{label} must be a non-empty string")
    return value


def _time(value: str, label: str) -> datetime:
    _str(value, label)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GateError(f"{label} must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise GateError(f"{label} must include timezone")
    return dt.astimezone(timezone.utc)


def _sha(value: Any, label: str) -> str:
    value = _str(value, label)
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise GateError(f"{label} must be lowercase sha256 hex")
    return value


def _source_index(ledger: Mapping[str, Any]):
    if type(ledger) is not dict or ledger.get("opportunity_id") != OPPORTUNITY_ID:
        raise GateError("source ledger opportunity_id mismatch")
    sources = ledger.get("sources")
    if type(sources) is not list:
        raise GateError("sources must be an array")
    out = {}
    for idx, source in enumerate(sources):
        if type(source) is not dict:
            raise GateError(f"sources[{idx}] must be an object")
        sid = _str(source.get("id"), f"sources[{idx}].id")
        if sid in out:
            raise GateError(f"duplicate source id: {sid}")
        authority = _str(source.get("authority"), f"{sid}.authority")
        if authority not in SOURCE_AUTHORITIES:
            raise GateError(f"unsupported source authority: {authority}")
        retrieved = _bool(source.get("retrieved"), f"{sid}.retrieved")
        _str(source.get("url"), f"{sid}.url")
        _time(source.get("observed_at"), f"{sid}.observed_at")
        claims = source.get("claims", {})
        controls = source.get("controls", [])
        if type(claims) is not dict:
            raise GateError(f"{sid}.claims must be object")
        if type(controls) is not list or any(type(x) is not str for x in controls):
            raise GateError(f"{sid}.controls must be string array")
        if authority in {"MIRROR", "INTERNAL_EVIDENCE", "OFFICIAL_PORTAL_ENTRY"}:
            forbidden = BUYER_CONTROL_FIELDS.intersection(controls)
            if forbidden:
                raise GateError(f"{sid} cannot control buyer fields as {authority}: {sorted(forbidden)}")
        if retrieved:
            _sha(source.get("content_sha256"), f"{sid}.content_sha256")
        out[sid] = source
    return out


def _official_value(sources, field):
    values = []
    for sid, source in sources.items():
        if not source["retrieved"] or source["authority"] not in {"OFFICIAL_CONTROLLING_PACKET", "OFFICIAL_ADDENDUM"}:
            continue
        if field in source.get("controls", []) and field in source.get("claims", {}):
            values.append((source["claims"][field], sid))
    if not values:
        return None, None
    first = values[0][0]
    if any(value != first for value, _ in values[1:]):
        raise GateError(f"conflicting official authority for {field}")
    return first, ",".join(sorted(sid for _, sid in values))


def _evidence_index(manifest: Mapping[str, Any], sources):
    if type(manifest) is not dict or manifest.get("opportunity_id") != OPPORTUNITY_ID:
        raise GateError("evidence manifest opportunity_id mismatch")
    rows = manifest.get("evidence")
    if type(rows) is not list:
        raise GateError("evidence manifest evidence must be an array")
    out = {}
    for idx, row in enumerate(rows):
        if type(row) is not dict:
            raise GateError(f"evidence[{idx}] must be object")
        eid = _str(row.get("id"), f"evidence[{idx}].id")
        if eid in out:
            raise GateError(f"duplicate evidence id: {eid}")
        if row.get("opportunity_id") != OPPORTUNITY_ID:
            raise GateError(f"{eid}.opportunity_id mismatch")
        rid = _str(row.get("requirement_id"), f"{eid}.requirement_id")
        if rid not in EVIDENCE_CLASSES:
            raise GateError(f"{eid}.requirement_id unsupported")
        evidence_class = _str(row.get("evidence_class"), f"{eid}.evidence_class")
        if evidence_class not in EVIDENCE_CLASSES[rid]:
            raise GateError(f"{eid}.evidence_class not admissible for {rid}")
        content_sha = _sha(row.get("content_sha256"), f"{eid}.content_sha256")
        source_id = _str(row.get("source_id"), f"{eid}.source_id")
        source = sources.get(source_id)
        if source is None or not source["retrieved"]:
            raise GateError(f"{eid}.source_id must resolve to retained source")
        if source.get("content_sha256") != content_sha:
            raise GateError(f"{eid}.content_sha256 does not bind source")
        authority = source["authority"]
        if evidence_class in OFFICIAL_EVIDENCE_CLASSES:
            if authority not in {"OFFICIAL_CONTROLLING_PACKET", "OFFICIAL_ADDENDUM"}:
                raise GateError(f"{eid} official evidence must bind official controlling source")
        elif authority != "INTERNAL_EVIDENCE":
            raise GateError(f"{eid} owner/partner evidence must bind INTERNAL_EVIDENCE source")
        out[eid] = {
            "id": eid,
            "opportunity_id": OPPORTUNITY_ID,
            "requirement_id": rid,
            "evidence_class": evidence_class,
            "content_sha256": content_sha,
            "source_id": source_id,
        }
    return out


def _requirements_index(requirements, evidence):
    if type(requirements) is not dict or requirements.get("opportunity_id") != OPPORTUNITY_ID:
        raise GateError("requirements opportunity_id mismatch")
    rows = requirements.get("requirements")
    if type(rows) is not list:
        raise GateError("requirements must be an array")
    out = {}
    consumed = set()
    for idx, row in enumerate(rows):
        if type(row) is not dict:
            raise GateError(f"requirement[{idx}] must be object")
        rid = _str(row.get("id"), f"requirement[{idx}].id")
        if rid not in ALL_GATES:
            raise GateError(f"unsupported requirement id: {rid}")
        if rid in out:
            raise GateError(f"duplicate requirement id: {rid}")
        state = _str(row.get("state"), f"{rid}.state")
        if state not in {"PROVEN", "GAP", "UNKNOWN", "NOT_APPLICABLE"}:
            raise GateError(f"unsupported requirement state: {state}")
        refs = row.get("evidence")
        if type(refs) is not list or any(type(x) is not str or not x for x in refs):
            raise GateError(f"{rid}.evidence must be string array")
        if len(refs) != len(set(refs)):
            raise GateError(f"{rid}.evidence contains duplicate refs")
        if state == "PROVEN":
            if not refs:
                raise GateError(f"{rid} PROVEN requires retained evidence")
            for ref in refs:
                item = evidence.get(ref)
                if item is None:
                    raise GateError(f"{rid} evidence ref not retained: {ref}")
                if item["requirement_id"] != rid:
                    raise GateError(f"{rid} evidence ref bound to different requirement: {ref}")
                consumed.add(ref)
        elif refs:
            raise GateError(f"{rid} non-PROVEN requirement must not retain positive evidence refs")
        out[rid] = row
    missing = sorted(set(ALL_GATES) - set(out))
    if missing:
        raise GateError(f"missing requirement rows: {missing}")
    unbound = sorted(set(evidence) - consumed)
    if unbound:
        raise GateError(f"retained evidence has no matching PROVEN requirement: {unbound}")
    return out


def _proven(gates, rid):
    row = gates.get(rid)
    return bool(row and row.get("state") == "PROVEN")


def compile_pursuit(
    ledger: Mapping[str, Any],
    requirements: Mapping[str, Any],
    evidence_manifest: Mapping[str, Any],
    *,
    now: str,
):
    now_dt = _time(now, "now")
    sources = _source_index(ledger)
    evidence = _evidence_index(evidence_manifest, sources)
    gates = _requirements_index(requirements, evidence)
    controlling = sorted(
        sid for sid, src in sources.items()
        if src["retrieved"] and src["authority"] == "OFFICIAL_CONTROLLING_PACKET"
    )
    official_packet = bool(controlling)
    deadline_raw, deadline_source = _official_value(sources, "response_deadline")
    teaming_raw, teaming_source = _official_value(sources, "teaming_rules")
    submission_raw, submission_source = _official_value(sources, "submission_mechanics")

    decision = "HOLD"
    reasons = []
    deadline_open = False
    if not official_packet:
        reasons.append("CONTROLLING_PACKET_NOT_ACQUIRED")

    if deadline_raw is None:
        reasons.append("RESPONSE_DEADLINE_UNCONTROLLED")
    else:
        if type(deadline_raw) is not str:
            raise GateError("official response_deadline must be string")
        deadline_dt = _time(deadline_raw, "official response_deadline")
        if now_dt >= deadline_dt:
            decision = "NO_BID"
            reasons.append("OFFICIAL_RESPONSE_DEADLINE_PASSED")
        else:
            deadline_open = True

    missing_prime = [rid for rid in PRIME_GATES if not _proven(gates, rid)]
    missing_specialist = [rid for rid in SPECIALIST_GATES if not _proven(gates, rid)]

    if decision != "NO_BID":
        if not official_packet or not deadline_open:
            decision = "HOLD"
        elif submission_raw is None:
            decision = "HOLD"
            reasons.append("SUBMISSION_MECHANICS_UNCONTROLLED")
        elif not missing_prime:
            decision = "PRIME"
        elif teaming_raw is True and not missing_specialist and _proven(gates, "partner_prime"):
            decision = "TEAMING"
        else:
            decision = "HOLD"
            if teaming_raw is None:
                reasons.append("TEAMING_RULES_UNCONTROLLED")
            elif teaming_raw is False:
                reasons.append("TEAMING_NOT_ALLOWED_BY_RETAINED_OFFICIAL_AUTHORITY")
            if missing_specialist:
                reasons.append("SPECIALIST_EVIDENCE_GAPS")
            if not _proven(gates, "partner_prime"):
                reasons.append("PARTNER_PRIME_NOT_PROVEN")

    if decision in {"HOLD", "TEAMING"} and missing_prime:
        reasons.append("PRIME_GATES_UNPROVEN")

    mirrors = [
        {"source_id": sid, "claims": src.get("claims", {}), "authority": "DISCOVERY_ONLY_NOT_BUYER_CONTROL"}
        for sid, src in sorted(sources.items()) if src["authority"] == "MIRROR"
    ]
    work_orders = []
    if "CONTROLLING_PACKET_NOT_ACQUIRED" in reasons:
        work_orders.append({"id": "RECOVER_CONTROLLING_RFP_PACKET", "priority": 1,
                            "stop_condition": "exact official packet/addenda retained with sha256 and reviewed"})
    if "RESPONSE_DEADLINE_UNCONTROLLED" in reasons:
        work_orders.append({"id": "BIND_OFFICIAL_RESPONSE_DEADLINE", "priority": 2,
                            "stop_condition": "official packet/addendum controls a parseable future response_deadline"})
    if "TEAMING_RULES_UNCONTROLLED" in reasons:
        work_orders.append({"id": "BIND_TEAMING_AND_SUBCONTRACT_RULES", "priority": 3,
                            "stop_condition": "official packet/addendum controls teaming_rules"})
    if missing_prime:
        work_orders.append({"id": "CLOSE_PRIME_QUALIFICATION_GAPS", "priority": 4, "gates": missing_prime,
                            "stop_condition": "each gate proven from retained bound evidence or prime posture abandoned"})
    if decision == "HOLD" and not missing_specialist:
        work_orders.append({"id": "PREPARE_PAID_SPECIALIST_TEAMING_SCOPE", "priority": 5,
                            "stop_condition": "official teaming permission plus evidence-backed prime partner"})

    evidence_bindings = {
        rid: sorted(gates[rid]["evidence"])
        for rid in ALL_GATES
        if gates[rid]["state"] == "PROVEN"
    }
    packet = {
        "schema": "hamilton-065-26-jw-pursuit/v2",
        "opportunity_id": OPPORTUNITY_ID,
        "evaluation_time": now_dt.isoformat().replace("+00:00", "Z"),
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "inputs": {
            "source_ledger_sha256": digest(ledger),
            "requirements_sha256": digest(requirements),
            "evidence_manifest_sha256": digest(evidence_manifest),
        },
        "authority": {
            "official_packet_sources": controlling,
            "response_deadline_source": deadline_source,
            "teaming_rules_source": teaming_source,
            "submission_mechanics_source": submission_source,
            "mirror_can_control_buyer_terms": False,
        },
        "evidence_bindings": evidence_bindings,
        "gaps": {"prime": missing_prime, "specialist": missing_specialist},
        "mirror_intelligence": mirrors,
        "work_orders": sorted(work_orders, key=lambda x: (x["priority"], x["id"])),
        "external_authority": {
            "county_contact": False, "portal_registration": False, "question_submission": False,
            "proposal_submission": False, "signature": False, "pricing_commitment": False,
            "partner_representation": False, "award": False, "payment": False, "revenue": False,
        },
    }
    packet["receipt_sha256"] = digest(packet)
    return packet


def verify_receipt(
    packet: Mapping[str, Any],
    ledger: Mapping[str, Any],
    requirements: Mapping[str, Any],
    evidence_manifest: Mapping[str, Any],
    *,
    now: str,
) -> bool:
    if type(packet) is not dict:
        return False
    try:
        expected = compile_pursuit(ledger, requirements, evidence_manifest, now=now)
    except (GateError, TypeError, ValueError):
        return False
    return canonical_bytes(packet) == canonical_bytes(expected)


def _read(path: Path):
    raw = path.read_bytes()
    if len(raw) > 2_000_000:
        raise GateError(f"{path} exceeds 2MB")
    try:
        return loads_strict(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise GateError(f"{path} is not utf-8") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--now", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    packet = compile_pursuit(
        _read(args.ledger),
        _read(args.requirements),
        _read(args.evidence),
        now=args.now,
    )
    encoded = canonical_bytes(packet) + b"\n"
    if args.out:
        args.out.write_bytes(encoded)
    else:
        print(encoded.decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
