from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

SCHEMA = "commons.mmsd-ai-governance/v1"
OUTPUT_SCHEMA = "commons.mmsd-ai-governance-decision/v1"

AUTHORITIES = {
    "OFFICIAL_BYTES",
    "OFFICIAL_BUYER_PAGE",
    "BUYER_PAGE_CACHE",
    "BUYER_DOCUMENT_MIRROR",
    "SECONDARY_INDEX",
}
DOC_KINDS = {"RFP", "ADDENDUM", "QA", "BUYER_PAGE"}
FETCH_STATES = {"AVAILABLE", "NOT_FOUND", "INDEXED_ONLY"}
GATE_STATES = {"PASS", "PARTNER_CURABLE", "MISSING", "HOLD", "NOT_APPLICABLE"}
ROUTES = {"PRIME", "TEAM"}
OUTREACH_STATES = {"NOT_CONTACTED", "SENT_NOT_ACCEPTED", "PARTNER_REPLIED", "DECLINED"}

REQUIRED_GATES = (
    "ai_governance_delivery_experience",
    "operational_ai_or_ot_risk_experience",
    "public_sector_records_compliance",
    "stakeholder_discovery_inventory",
    "incident_vendor_governance",
    "training_change_management",
    "similar_references",
    "key_personnel",
    "required_insurance_legal",
    "signature_authority",
)

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+#/-]{0,159}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class PursuitError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def strict_json_loads(text: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise PursuitError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    def bad_constant(value: str) -> None:
        raise PursuitError(f"non-finite JSON number: {value}")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=bad_constant)
    except PursuitError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise PursuitError(f"invalid JSON: {exc}") from exc


def _exact(obj: dict[str, Any], keys: set[str], where: str) -> None:
    if set(obj) != keys:
        raise PursuitError(
            f"{where}: keys mismatch missing={sorted(keys - set(obj))} "
            f"extra={sorted(set(obj) - keys)}"
        )


def _s(value: Any, name: str, max_len: int = 300, pattern: re.Pattern[str] | None = None) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > max_len
        or any(ord(c) < 32 for c in value)
    ):
        raise PursuitError(f"{name}: invalid string")
    if pattern and not pattern.fullmatch(value):
        raise PursuitError(f"{name}: invalid format")
    return value


def _b(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise PursuitError(f"{name}: bool required")
    return value


def _t(value: Any, name: str) -> datetime:
    text = _s(value, name, 35)
    if not text.endswith("Z"):
        raise PursuitError(f"{name}: UTC Z required")
    try:
        dt = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise PursuitError(f"{name}: invalid timestamp") from exc
    if dt.microsecond:
        raise PursuitError(f"{name}: whole seconds required")
    return dt


def _nullable_t(value: Any, name: str) -> datetime | None:
    if value is None:
        return None
    return _t(value, name)


def _source(raw: Any, idx: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PursuitError(f"sources[{idx}] must be object")
    keys = {
        "source_id",
        "doc_kind",
        "generation",
        "authority",
        "source_ref",
        "content_sha256",
        "captured_at",
        "current",
        "fetch_state",
        "supersedes",
    }
    _exact(raw, keys, f"sources[{idx}]")
    out = {
        "source_id": _s(raw["source_id"], f"sources[{idx}].source_id", 100, SAFE_ID),
        "doc_kind": _s(raw["doc_kind"], f"sources[{idx}].doc_kind", 20),
        "generation": _s(raw["generation"], f"sources[{idx}].generation", 80, SAFE_ID),
        "authority": _s(raw["authority"], f"sources[{idx}].authority", 30),
        "source_ref": _s(raw["source_ref"], f"sources[{idx}].source_ref", 500),
        "content_sha256": raw["content_sha256"],
        "captured_at": _s(raw["captured_at"], f"sources[{idx}].captured_at", 35),
        "current": _b(raw["current"], f"sources[{idx}].current"),
        "fetch_state": _s(raw["fetch_state"], f"sources[{idx}].fetch_state", 30),
        "supersedes": raw["supersedes"],
    }
    if out["doc_kind"] not in DOC_KINDS:
        raise PursuitError(f"sources[{idx}].doc_kind invalid")
    if out["authority"] not in AUTHORITIES:
        raise PursuitError(f"sources[{idx}].authority invalid")
    if out["fetch_state"] not in FETCH_STATES:
        raise PursuitError(f"sources[{idx}].fetch_state invalid")
    if out["content_sha256"] is not None:
        out["content_sha256"] = _s(
            out["content_sha256"],
            f"sources[{idx}].content_sha256",
            64,
            SHA256,
        )
    if out["authority"] == "OFFICIAL_BYTES":
        if out["content_sha256"] is None or out["fetch_state"] != "AVAILABLE":
            raise PursuitError(f"sources[{idx}]: OFFICIAL_BYTES requires available digest")
    if out["supersedes"] is not None:
        out["supersedes"] = _s(
            out["supersedes"],
            f"sources[{idx}].supersedes",
            100,
            SAFE_ID,
        )
    _t(out["captured_at"], f"sources[{idx}].captured_at")
    return out


def _gate(raw: Any, idx: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PursuitError(f"gates[{idx}] must be object")
    _exact(raw, {"gate_id", "route", "state", "evidence_refs"}, f"gates[{idx}]")
    gate_id = _s(raw["gate_id"], f"gates[{idx}].gate_id", 100, SAFE_ID)
    route = _s(raw["route"], f"gates[{idx}].route", 10)
    state = _s(raw["state"], f"gates[{idx}].state", 30)
    if route not in ROUTES or state not in GATE_STATES:
        raise PursuitError(f"gates[{idx}]: enum invalid")
    refs = raw["evidence_refs"]
    if not isinstance(refs, list) or len(refs) > 30:
        raise PursuitError(f"gates[{idx}].evidence_refs invalid")
    clean_refs = [_s(v, f"gates[{idx}].evidence_refs", 160, SAFE_ID) for v in refs]
    if len(set(clean_refs)) != len(clean_refs):
        raise PursuitError(f"gates[{idx}]: duplicate evidence ref")
    if state == "PASS" and not clean_refs:
        raise PursuitError(f"gates[{idx}]: PASS requires evidence")
    return {
        "gate_id": gate_id,
        "route": route,
        "state": state,
        "evidence_refs": sorted(clean_refs),
    }


def evaluate(packet: Any, as_of: str) -> dict[str, Any]:
    now = _t(as_of, "as_of")
    if not isinstance(packet, dict):
        raise PursuitError("packet must be object")
    _exact(
        packet,
        {
            "schema",
            "opportunity_id",
            "buyer",
            "sources",
            "source_set_complete",
            "addenda_checked",
            "qa_checked",
            "deadlines",
            "gates",
            "partner",
            "outreach",
            "budget",
            "owner_release",
        },
        "packet",
    )
    if packet["schema"] != SCHEMA:
        raise PursuitError("unsupported schema")

    opportunity_id = _s(packet["opportunity_id"], "opportunity_id", 120, SAFE_ID)
    buyer = _s(packet["buyer"], "buyer", 200)
    source_set_complete = _b(packet["source_set_complete"], "source_set_complete")
    addenda_checked = _b(packet["addenda_checked"], "addenda_checked")
    qa_checked = _b(packet["qa_checked"], "qa_checked")
    owner_release = _b(packet["owner_release"], "owner_release")

    raw_sources = packet["sources"]
    if not isinstance(raw_sources, list) or not raw_sources or len(raw_sources) > 60:
        raise PursuitError("sources invalid")
    sources = [_source(v, i) for i, v in enumerate(raw_sources)]

    source_ids: dict[str, str] = {}
    by_id: dict[str, dict[str, Any]] = {}
    for source in sources:
        sid = source["source_id"]
        sd = digest(source)
        if sid in source_ids:
            if source_ids[sid] != sd:
                raise PursuitError(f"changed duplicate source_id: {sid}")
            raise PursuitError(f"duplicate source_id: {sid}")
        source_ids[sid] = sd
        by_id[sid] = source
        if _t(source["captured_at"], sid + ".captured_at") > now:
            raise PursuitError(f"future source: {sid}")
    for source in sources:
        supersedes = source["supersedes"]
        if supersedes is not None and supersedes not in by_id:
            raise PursuitError(f"unknown supersedes: {supersedes}")

    deadlines = packet["deadlines"]
    if not isinstance(deadlines, dict):
        raise PursuitError("deadlines must be object")
    _exact(
        deadlines,
        {"questions_due", "proposal_due", "proposal_due_source_id"},
        "deadlines",
    )
    question_due = _nullable_t(deadlines["questions_due"], "deadlines.questions_due")
    proposal_due = _t(deadlines["proposal_due"], "deadlines.proposal_due")
    deadline_source_id = _s(
        deadlines["proposal_due_source_id"],
        "deadlines.proposal_due_source_id",
        100,
        SAFE_ID,
    )
    if deadline_source_id not in by_id:
        raise PursuitError("proposal deadline source missing")
    if question_due is not None and proposal_due <= question_due:
        raise PursuitError("proposal deadline must follow questions deadline")

    raw_gates = packet["gates"]
    if not isinstance(raw_gates, list) or len(raw_gates) > 100:
        raise PursuitError("gates invalid")
    gates = [_gate(v, i) for i, v in enumerate(raw_gates)]
    seen: set[tuple[str, str]] = set()
    for gate in gates:
        key = (gate["gate_id"], gate["route"])
        if key in seen:
            raise PursuitError(f"duplicate gate route: {key}")
        seen.add(key)

    partner = packet["partner"]
    if not isinstance(partner, dict):
        raise PursuitError("partner must be object")
    _exact(
        partner,
        {"candidate_id", "confirmed", "commercial_workshare_agreed", "evidence_refs"},
        "partner",
    )
    candidate_id = partner["candidate_id"]
    if candidate_id is not None:
        candidate_id = _s(candidate_id, "partner.candidate_id", 120, SAFE_ID)
    partner_confirmed = _b(partner["confirmed"], "partner.confirmed")
    workshare = _b(
        partner["commercial_workshare_agreed"],
        "partner.commercial_workshare_agreed",
    )
    if workshare and not partner_confirmed:
        raise PursuitError("workshare cannot precede confirmed partner")
    partner_refs = partner["evidence_refs"]
    if not isinstance(partner_refs, list) or len(partner_refs) > 30:
        raise PursuitError("partner.evidence_refs invalid")
    partner_refs = [_s(v, "partner.evidence_refs", 160, SAFE_ID) for v in partner_refs]
    if partner_confirmed and (candidate_id is None or not partner_refs):
        raise PursuitError("confirmed partner requires identity and evidence")

    outreach = packet["outreach"]
    if not isinstance(outreach, dict):
        raise PursuitError("outreach must be object")
    _exact(outreach, {"state", "provider_receipt_id"}, "outreach")
    outreach_state = _s(outreach["state"], "outreach.state", 30)
    if outreach_state not in OUTREACH_STATES:
        raise PursuitError("outreach.state invalid")
    provider_receipt = outreach["provider_receipt_id"]
    if provider_receipt is not None:
        provider_receipt = _s(
            provider_receipt,
            "outreach.provider_receipt_id",
            160,
            SAFE_ID,
        )
    if outreach_state != "NOT_CONTACTED" and provider_receipt is None:
        raise PursuitError("observed outreach requires provider receipt")

    budget = packet["budget"]
    if not isinstance(budget, dict):
        raise PursuitError("budget must be object")
    _exact(
        budget,
        {"math_valid", "owner_approved", "pricing_structure_known", "total_cents"},
        "budget",
    )
    budget_math = _b(budget["math_valid"], "budget.math_valid")
    budget_approved = _b(budget["owner_approved"], "budget.owner_approved")
    pricing_known = _b(
        budget["pricing_structure_known"],
        "budget.pricing_structure_known",
    )
    total_cents = budget["total_cents"]
    if type(total_cents) is not int or total_cents < 0 or total_cents > 1_000_000_000:
        raise PursuitError("budget.total_cents invalid")
    if budget_approved and not budget_math:
        raise PursuitError("owner cannot approve invalid budget math")
    if budget_approved and not pricing_known:
        raise PursuitError("owner approval cannot outrun pricing structure evidence")

    deadline_source = by_id[deadline_source_id]
    deadline_authoritative = (
        deadline_source["authority"] in {"OFFICIAL_BYTES", "OFFICIAL_BUYER_PAGE"}
        and deadline_source["fetch_state"] == "AVAILABLE"
        and deadline_source["current"]
    )
    current_sources = [s for s in sources if s["current"]]
    current_official_rfp = [
        s
        for s in current_sources
        if s["doc_kind"] == "RFP"
        and s["authority"] == "OFFICIAL_BYTES"
        and s["fetch_state"] == "AVAILABLE"
    ]
    official_submission_bytes_complete = bool(current_official_rfp)
    source_ready = (
        source_set_complete
        and addenda_checked
        and qa_checked
        and official_submission_bytes_complete
        and deadline_authoritative
    )

    prime = {g["gate_id"]: g for g in gates if g["route"] == "PRIME"}
    team = {g["gate_id"]: g for g in gates if g["route"] == "TEAM"}
    missing_prime = [
        gate_id
        for gate_id in REQUIRED_GATES
        if gate_id not in prime
        or prime[gate_id]["state"] not in {"PASS", "NOT_APPLICABLE"}
    ]
    missing_team = [
        gate_id
        for gate_id in REQUIRED_GATES
        if gate_id not in team
        or team[gate_id]["state"] not in {"PASS", "NOT_APPLICABLE"}
    ]

    ready_budget = budget_math and budget_approved and pricing_known
    if now >= proposal_due:
        disposition = "EXPIRED"
    elif not source_ready:
        disposition = "SOURCE_REFRESH_REQUIRED"
    elif not missing_prime and ready_budget and owner_release:
        disposition = "PRIME_READY_FOR_OWNER_SUBMISSION_REVIEW"
    elif (
        partner_confirmed
        and workshare
        and not missing_team
        and ready_budget
        and owner_release
    ):
        disposition = "TEAM_READY_FOR_OWNER_SUBMISSION_REVIEW"
    elif partner_confirmed and workshare and not missing_team:
        disposition = "TEAMING_RESPONSE_BUILD_READY"
    elif missing_prime:
        disposition = "TEAM_PARTNER_REQUIRED"
    else:
        disposition = "PRIME_QUALIFICATION_HOLD"

    output = {
        "schema": OUTPUT_SCHEMA,
        "opportunity_id": opportunity_id,
        "buyer": buyer,
        "as_of": as_of,
        "disposition": disposition,
        "deadlines": {
            "questions_due": deadlines["questions_due"],
            "proposal_due": deadlines["proposal_due"],
            "proposal_due_source_id": deadline_source_id,
            "proposal_due_authoritative": deadline_authoritative,
        },
        "days_to_proposal": max(0.0, (proposal_due - now).total_seconds() / 86400.0),
        "source_posture": {
            "source_set_complete": source_set_complete,
            "addenda_checked": addenda_checked,
            "qa_checked": qa_checked,
            "official_submission_bytes_complete": official_submission_bytes_complete,
            "current_source_ids": sorted(s["source_id"] for s in current_sources),
            "current_unavailable_source_ids": sorted(
                s["source_id"]
                for s in current_sources
                if s["fetch_state"] != "AVAILABLE"
            ),
        },
        "qualification": {
            "missing_prime_gates": sorted(missing_prime),
            "missing_team_gates": sorted(missing_team),
        },
        "partner_posture": {
            "candidate_id": candidate_id,
            "confirmed": partner_confirmed,
            "commercial_workshare_agreed": workshare,
        },
        "outreach": {
            "state": outreach_state,
            "provider_receipt_id": provider_receipt,
        },
        "budget": {
            "math_valid": budget_math,
            "owner_approved": budget_approved,
            "pricing_structure_known": pricing_known,
            "total_cents": total_cents,
        },
        "authority": {
            "may_submit": disposition
            in {
                "PRIME_READY_FOR_OWNER_SUBMISSION_REVIEW",
                "TEAM_READY_FOR_OWNER_SUBMISSION_REVIEW",
            }
            and owner_release,
            "may_bind_contract": False,
            "may_claim_award": False,
            "may_claim_payment_or_revenue": False,
        },
    }
    receipt_body = dict(output)
    output["receipt_sha256"] = digest(receipt_body)
    return output


def verify(packet: Any, as_of: str, observed: Any) -> bool:
    try:
        expected = evaluate(packet, as_of)
    except PursuitError:
        return False
    return canonical_bytes(expected) == canonical_bytes(observed)
