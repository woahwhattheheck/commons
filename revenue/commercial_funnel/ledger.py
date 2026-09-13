from __future__ import annotations

from collections import defaultdict
from typing import Any

from .common import (
    HOLD,
    INPUT_SCHEMA,
    MAX_EVIDENCE_AGE_SECONDS,
    MAX_OPPORTUNITIES,
    PACKET_SCHEMA,
    READY,
    RECEIPT_SCHEMA,
    STAGES,
    STAGE_INDEX,
    FunnelError,
    canonical_json,
    exact_keys,
    parse_time,
    require_id,
    sha256,
    strict_loads,
    validate_json_scalars,
)
from .model import csv_bytes, markdown_bytes, metrics, normalize_opportunity


def compile_funnel(value: Any, *, as_of: str) -> dict[str, Any]:
    validate_json_scalars(value)
    root = exact_keys(value, required=("schema", "opportunities"), field="$")
    if root["schema"] != INPUT_SCHEMA:
        raise FunnelError("unsupported input schema")
    evaluated = parse_time(as_of, "as_of")
    raw_opportunities = root["opportunities"]
    if not isinstance(raw_opportunities, list) or not raw_opportunities or len(raw_opportunities) > MAX_OPPORTUNITIES:
        raise FunnelError(f"opportunities must contain 1..{MAX_OPPORTUNITIES} items")

    normalized: list[dict[str, Any]] = []
    ids: set[str] = set()
    evidence_owners: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for i, raw in enumerate(raw_opportunities):
        opp, usage = normalize_opportunity(raw, f"opportunities[{i}]", evaluated)
        if opp["id"] in ids:
            raise FunnelError(f"duplicate opportunity id: {opp['id']}")
        ids.add(opp["id"])
        normalized.append(opp)
        for key, owners in usage.items():
            evidence_owners[key].update(owners)

    cross_reused = {key: owners for key, owners in evidence_owners.items() if len(owners) > 1}
    if cross_reused:
        impacted = set().union(*cross_reused.values())
        for opp in normalized:
            if opp["id"] in impacted:
                opp["hold_reasons"] = sorted(set(opp["hold_reasons"]) | {"EVIDENCE_REUSED_ACROSS_OPPORTUNITIES"})
                opp["state"] = HOLD
                opp["next_evidence_needed"] = "REVIEW_HOLD_REASONS"

    normalized.sort(key=lambda opp: opp["id"])
    packet_metrics = metrics(normalized)
    overall = READY if packet_metrics["held_opportunity_count"] == 0 else HOLD
    digest_opportunities = []
    for raw in raw_opportunities:
        digest_opp = dict(raw)
        digest_opp["events"] = sorted(raw["events"], key=canonical_json)
        digest_opportunities.append(digest_opp)
    digest_opportunities.sort(key=lambda item: (require_id(item["id"], "opportunity.id"), canonical_json(item)))
    input_digest = sha256(canonical_json({"schema": INPUT_SCHEMA, "opportunities": digest_opportunities}))
    authority = {
        "buyer_contact_authorized": False,
        "acceptance_authorized": False,
        "contract_execution_authorized": False,
        "fulfillment_authorized": False,
        "transfer_authorized": False,
        "payment_or_provider_mutation_authorized": False,
        "cash_availability_asserted": False,
        "accounting_or_tax_authority": False,
        "revenue_recognition_authorized": False,
    }
    packet_base = {
        "schema": PACKET_SCHEMA,
        "state": overall,
        "evaluated_at": as_of,
        "max_evidence_age_seconds": MAX_EVIDENCE_AGE_SECONDS,
        "input_sha256": input_digest,
        "metrics": packet_metrics,
        "opportunities": normalized,
        "authority": authority,
    }
    json_bytes = canonical_json(packet_base)
    report_csv = csv_bytes(normalized)
    report_markdown = markdown_bytes(packet_base)
    outputs = {
        "report_json_sha256": sha256(json_bytes),
        "report_csv_sha256": sha256(report_csv),
        "report_markdown_sha256": sha256(report_markdown),
    }
    packet = dict(packet_base)
    packet["outputs"] = outputs
    packet_sha = sha256(canonical_json(packet))
    receipt_base = {
        "schema": RECEIPT_SCHEMA,
        "state": overall,
        "evaluated_at": as_of,
        "input_sha256": input_digest,
        "packet_sha256": packet_sha,
        "outputs": outputs,
        "authority": authority,
    }
    receipt = dict(receipt_base)
    receipt["receipt_sha256"] = sha256(canonical_json(receipt_base))
    return {"packet": packet, "receipt": receipt, "json": json_bytes, "csv": report_csv, "markdown": report_markdown}


def verify_compilation(value: Any, *, as_of: str, packet: Any, receipt: Any) -> bool:
    try:
        expected = compile_funnel(value, as_of=as_of)
        if not isinstance(packet, dict) or not isinstance(receipt, dict):
            return False
        if canonical_json(packet) != canonical_json(expected["packet"]):
            return False
        if canonical_json(receipt) != canonical_json(expected["receipt"]):
            return False
        receipt_without_digest = {key: val for key, val in receipt.items() if key != "receipt_sha256"}
        return receipt.get("receipt_sha256") == sha256(canonical_json(receipt_without_digest))
    except (FunnelError, TypeError, ValueError, OverflowError):
        return False


def verify_artifacts(
    value: Any,
    *,
    as_of: str,
    packet: Any,
    receipt: Any,
    report_json: bytes,
    report_csv: bytes,
    report_markdown: bytes,
) -> bool:
    """Recompile from semantic input and byte-verify every emitted artifact."""
    try:
        expected = compile_funnel(value, as_of=as_of)
        if not verify_compilation(value, as_of=as_of, packet=packet, receipt=receipt):
            return False
        return (
            report_json == expected["json"]
            and report_csv == expected["csv"]
            and report_markdown == expected["markdown"]
            and receipt.get("outputs", {}).get("report_json_sha256") == sha256(report_json)
            and receipt.get("outputs", {}).get("report_csv_sha256") == sha256(report_csv)
            and receipt.get("outputs", {}).get("report_markdown_sha256") == sha256(report_markdown)
        )
    except (FunnelError, TypeError, ValueError, OverflowError):
        return False


__all__ = [
    "HOLD",
    "INPUT_SCHEMA",
    "PACKET_SCHEMA",
    "READY",
    "RECEIPT_SCHEMA",
    "STAGES",
    "STAGE_INDEX",
    "FunnelError",
    "canonical_json",
    "compile_funnel",
    "strict_loads",
    "verify_artifacts",
    "verify_compilation",
]
