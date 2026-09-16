from __future__ import annotations

from datetime import datetime
from typing import Any

from .schema import (
    MANDATORY_PRIME_GATES,
    PROPOSAL_DEADLINE,
    QUESTION_DEADLINE,
    REPORT_SCHEMA,
    QualificationError,
    _canonical_time,
    canonical_bytes,
    dt,
    sha256_bytes,
    utc_now_string,
    validate_packet,
)


def _evidence_reasons(prefix: str, evidence: dict[str, Any], now: datetime) -> list[str]:
    status = evidence["status"]
    if status != "VERIFIED":
        return [f"{prefix}_{status}"]
    reasons: list[str] = []
    if dt(evidence["observed_at"]) > now:
        reasons.append(f"{prefix}_FROM_FUTURE")
    if dt(evidence["valid_until"]) < now:
        reasons.append(f"{prefix}_STALE")
    return reasons


def _compile_at(packet: Any, evaluated_at: str) -> dict[str, Any]:
    evaluated_at = _canonical_time(evaluated_at, name="evaluated_at")
    now = dt(evaluated_at)
    normalized = validate_packet(packet)
    input_sha = sha256_bytes(canonical_bytes(normalized))

    reasons: set[str] = set()
    source_rows: list[dict[str, Any]] = []
    for source in normalized["sources"]:
        source_reasons: list[str] = []
        if source["status"] != "BOUND":
            source_reasons.append(f"{source['source_id']}_{source['status']}")
        elif dt(source["captured_at"]) > now:
            source_reasons.append(f"{source['source_id']}_FROM_FUTURE")
        source_rows.append({
            "source_id": source["source_id"],
            "status": source["status"],
            "sha256": source["sha256"],
            "size_bytes": source["size_bytes"],
            "reasons": sorted(source_reasons),
        })
        reasons.update(source_reasons)

    status_reasons = _evidence_reasons("OPPORTUNITY_STATUS", normalized["status_evidence"], now)
    addenda_reasons = _evidence_reasons("ADDENDA_CENSUS", normalized["addenda_census"], now)
    reasons.update(status_reasons)
    reasons.update(addenda_reasons)

    gate_by_id = {row["gate_id"]: row["evidence"] for row in normalized["gates"]}
    gate_rows: list[dict[str, Any]] = []
    missing_prime: list[str] = []
    for gate_id in MANDATORY_PRIME_GATES:
        evidence = gate_by_id.get(gate_id)
        if evidence is None:
            state = "MISSING"
            gate_reasons = [f"GATE_{gate_id}_MISSING"]
            artifact_id = digest = authority_ref = valid_until = None
        else:
            state = evidence["status"]
            gate_reasons = _evidence_reasons(f"GATE_{gate_id}", evidence, now)
            artifact_id = evidence["artifact_id"]
            digest = evidence["sha256"]
            authority_ref = evidence["authority_ref"]
            valid_until = evidence["valid_until"]
        if state != "VERIFIED" or gate_reasons:
            missing_prime.append(gate_id)
        gate_rows.append({
            "gate_id": gate_id,
            "status": state,
            "artifact_id": artifact_id,
            "sha256": digest,
            "authority_ref": authority_ref,
            "valid_until": valid_until,
            "reasons": sorted(gate_reasons),
        })
        if state == "CONFLICT" or any(reason.endswith("_FROM_FUTURE") or reason.endswith("_STALE") for reason in gate_reasons):
            reasons.update(gate_reasons)

    seam = normalized["specialist_seam"]
    seam_reasons = _evidence_reasons("SPECIALIST_SEAM", seam["evidence"], now)
    seam_ready = bool(seam["scope_ids"]) and not seam_reasons and seam["evidence"]["status"] == "VERIFIED"

    deadline_reached = now >= dt(PROPOSAL_DEADLINE)
    opportunity_terminal = normalized["opportunity_status"] in {"CANCELLED", "CLOSED"}
    source_blocked = any(row["status"] != "BOUND" or row["reasons"] for row in source_rows)
    evidence_conflict = any(
        token.endswith("_CONFLICT") or token.endswith("_STALE") or token.endswith("_FROM_FUTURE")
        for token in reasons
    )

    if opportunity_terminal:
        disposition = "NO_BID"
        reasons.add(f"OPPORTUNITY_{normalized['opportunity_status']}")
    elif deadline_reached:
        disposition = "NO_BID"
        reasons.add("PROPOSAL_DEADLINE_REACHED")
    elif source_blocked or status_reasons or addenda_reasons or evidence_conflict:
        disposition = "HOLD"
    elif not missing_prime:
        disposition = "PRIME_READY"
    elif seam_ready:
        disposition = "TEAMING_ONLY"
        reasons.add("PRIME_GATES_UNSATISFIED")
    else:
        disposition = "HOLD"
        reasons.add("SPECIALIST_SEAM_UNVERIFIED")

    question_window = "OPEN" if now < dt(QUESTION_DEADLINE) else "CLOSED"
    proposal_window = "OPEN" if now < dt(PROPOSAL_DEADLINE) else "CLOSED"
    authority = {
        "buyer_contact_authorized": False,
        "partner_contact_authorized": False,
        "question_submission_authorized": False,
        "proposal_submission_authorized": False,
        "signature_authorized": False,
        "pricing_committed": False,
        "insurance_attested": False,
        "reference_claim_authorized": False,
        "spend_authorized": False,
        "contract_authorized": False,
        "payment_authorized": False,
        "revenue_recognized": False,
    }
    core = {
        "schema": REPORT_SCHEMA,
        "opportunity_id": normalized["opportunity_id"],
        "evaluated_at": evaluated_at,
        "input_sha256": input_sha,
        "disposition": disposition,
        "reasons": sorted(reasons),
        "windows": {
            "question_deadline": QUESTION_DEADLINE,
            "question_window": question_window,
            "proposal_deadline": PROPOSAL_DEADLINE,
            "proposal_window": proposal_window,
        },
        "sources": source_rows,
        "prime_gates": gate_rows,
        "missing_prime_gates": sorted(missing_prime),
        "specialist_seam": {
            "state": "VERIFIED" if seam_ready else "HOLD",
            "scope_ids": seam["scope_ids"],
            "evidence_sha256": sha256_bytes(canonical_bytes(seam["evidence"])),
            "proposed_fee_usd": seam["proposed_fee_usd"],
            "commercial_state": "PROPOSED_NOT_ACCEPTED" if seam["proposed_fee_usd"] is not None else "UNPRICED",
            "reasons": sorted(seam_reasons),
        },
        "authority": authority,
    }
    markdown = render_markdown_core(core)
    report = {**core, "markdown_sha256": sha256_bytes(markdown.encode("utf-8"))}
    report["receipt_sha256"] = sha256_bytes(canonical_bytes(report))
    return report


def compile_at(packet: Any, evaluated_at: str) -> dict[str, Any]:
    return _compile_at(packet, evaluated_at)


def compile_current(packet: Any) -> dict[str, Any]:
    return _compile_at(packet, utc_now_string())


def verify_historical(packet: Any, report: Any) -> bool:
    if type(report) is not dict or type(report.get("evaluated_at")) is not str:
        return False
    try:
        expected = _compile_at(packet, report["evaluated_at"])
        return canonical_bytes(expected) == canonical_bytes(report)
    except QualificationError:
        return False


def _semantic_projection(report: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "opportunity_id",
        "input_sha256",
        "disposition",
        "reasons",
        "windows",
        "sources",
        "prime_gates",
        "missing_prime_gates",
        "specialist_seam",
        "authority",
    ]
    return {key: report.get(key) for key in keys}


def verify_current(packet: Any, report: Any) -> bool:
    if not verify_historical(packet, report):
        return False
    try:
        current = compile_current(packet)
    except QualificationError:
        return False
    return canonical_bytes(_semantic_projection(current)) == canonical_bytes(_semantic_projection(report))


def render_markdown_core(core: dict[str, Any]) -> str:
    lines = [
        "# Stockton PUR 27-007 qualification receipt",
        "",
        f"Disposition: **{core['disposition']}**",
        f"Evaluated: `{core['evaluated_at']}`",
        f"Input: `{core['input_sha256']}`",
        "",
        "## Source custody",
    ]
    for source in core["sources"]:
        digest = source["sha256"] or "unbound"
        reasons = ", ".join(source["reasons"]) if source["reasons"] else "none"
        lines.append(f"- `{source['source_id']}` — `{source['status']}` — `{digest}` — reasons: {reasons}")
    lines.extend(["", "## Prime blockers"])
    if not core["missing_prime_gates"]:
        lines.append("- No mandatory prime gate is missing in this packet.")
    else:
        for gate_id in core["missing_prime_gates"]:
            lines.append(f"- `{gate_id}`")
    lines.extend([
        "",
        "## Specialist seam",
        f"State: **{core['specialist_seam']['state']}**; commercial state: `{core['specialist_seam']['commercial_state']}`.",
    ])
    for scope_id in core["specialist_seam"]["scope_ids"]:
        lines.append(f"- `{scope_id}`")
    lines.extend([
        "",
        "## Authority ceiling",
        "This receipt authorizes no buyer or partner contact, question, bid, signature, price commitment, insurance/reference assertion, spend, contract, payment, or revenue recognition.",
        "",
    ])
    return "\n".join(lines)


def render_markdown(report: dict[str, Any]) -> str:
    core_keys = [
        "schema",
        "opportunity_id",
        "evaluated_at",
        "input_sha256",
        "disposition",
        "reasons",
        "windows",
        "sources",
        "prime_gates",
        "missing_prime_gates",
        "specialist_seam",
        "authority",
    ]
    return render_markdown_core({key: report[key] for key in core_keys})
