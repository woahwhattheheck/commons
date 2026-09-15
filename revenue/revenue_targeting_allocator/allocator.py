from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any

from .schema import (
    AUTHORITY_FALSE, BUYER_STAGE_STATES, BUYER_STAGES, CANDIDATE_KEYS,
    COLLISION_STATES, CURRENCY_RE, DELIVERY_STATES, FIT_POINTS, FIT_STATES,
    FRESHNESS_STATES, HEX64_RE, INPUT_SCHEMA, MAX_CANDIDATES, OUTPUT_SCHEMA,
    RECEIPT_SCHEMA, RELATIONSHIP_STATES, REQUIRED_CANDIDATE_KEYS, ROOT_KEYS,
    ROUTE_STATES, STAGE_POINTS, TOKEN_RE, AllocationError, canonical_json_bytes,
    sha256_document, validate_input,
)

def _hold_reasons(c: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if c["commercial_value_minor"] <= 0:
        reasons.append("NON_POSITIVE_COMMERCIAL_VALUE")
    if c["route_state"] != "VERIFIED_CLEAR":
        reasons.append(f"ROUTE_{c['route_state']}")
    if c["relationship_state"] != "CLEAR":
        reasons.append(f"RELATIONSHIP_{c['relationship_state']}")
    if c["collision_state"] != "CLEAR":
        reasons.append(f"COLLISION_{c['collision_state']}")
    if c["freshness_state"] != "FRESH":
        reasons.append(f"EVIDENCE_{c['freshness_state']}")
    if c["buyer_stage_state"] != "VERIFIED":
        reasons.append(f"BUYER_STAGE_{c['buyer_stage_state']}")
    if c["fit_state"] == "UNKNOWN":
        reasons.append("FIT_UNKNOWN")
    if c["delivery_state"] != "READY":
        reasons.append(f"DELIVERY_{c['delivery_state']}")
    return sorted(reasons)


def _row(
    c: Mapping[str, Any],
    _stage_points: Mapping[str, int] = MappingProxyType(dict(STAGE_POINTS)),
    _fit_points: Mapping[str, int] = MappingProxyType(dict(FIT_POINTS)),
) -> dict[str, Any]:
    reasons = _hold_reasons(c)
    stage_points = _stage_points[c["buyer_stage"]]
    fit_points = _fit_points[c["fit_state"]]
    probability = c.get("probability_bps")
    expected_value = (
        c["commercial_value_minor"] * probability // 10_000
        if probability is not None
        else None
    )
    queue = "HOLD"
    if not reasons:
        queue = "EXPECTED_VALUE" if probability is not None else "EVIDENCE_STRENGTH"
    row: dict[str, Any] = {
        "opportunity_id": c["opportunity_id"],
        "offer_id": c["offer_id"],
        "currency": c["currency"],
        "commercial_value_minor": c["commercial_value_minor"],
        "probability_bps": probability,
        "expected_value_minor": expected_value,
        "buyer_stage": c["buyer_stage"],
        "stage_points": stage_points,
        "fit_state": c["fit_state"],
        "fit_points": fit_points,
        "queue": queue,
        "hold_reasons": reasons,
        "evidence_bundle_sha256": c["evidence_bundle_sha256"],
        "external_send_authorized": False,
        "provider_mutation_authorized": False,
        "payment_or_revenue_inferred": False,
    }
    row["row_sha256"] = sha256_document(row)
    return row


def _rank_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    expected = [r for r in rows if r["queue"] == "EXPECTED_VALUE"]
    evidence = [r for r in rows if r["queue"] == "EVIDENCE_STRENGTH"]
    holds = [r for r in rows if r["queue"] == "HOLD"]

    expected.sort(
        key=lambda r: (
            r["currency"],
            -int(r["expected_value_minor"]),
            -r["stage_points"],
            -r["fit_points"],
            -r["commercial_value_minor"],
            r["opportunity_id"],
            r["offer_id"],
        )
    )
    evidence.sort(
        key=lambda r: (
            r["currency"],
            -r["stage_points"],
            -r["fit_points"],
            -r["commercial_value_minor"],
            r["opportunity_id"],
            r["offer_id"],
        )
    )
    holds.sort(key=lambda r: (r["currency"], r["opportunity_id"], r["offer_id"]))

    result: list[dict[str, Any]] = []
    ranks: dict[tuple[str, str], int] = {}
    for r in expected:
        group = (r["currency"], r["queue"])
        ranks[group] = ranks.get(group, 0) + 1
        r = dict(r)
        r["rank"] = ranks[group]
        result.append(r)
    for r in evidence:
        group = (r["currency"], r["queue"])
        ranks[group] = ranks.get(group, 0) + 1
        r = dict(r)
        r["rank"] = ranks[group]
        result.append(r)
    for r in holds:
        r = dict(r)
        r["rank"] = None
        result.append(r)
    return result


def render_markdown(output: Mapping[str, Any]) -> str:
    lines = [
        "# Revenue Targeting Allocator",
        "",
        f"Portfolio: `{output['portfolio_id']}`",
        "",
        "> Owner-review prioritization only. No row authorizes contact, provider mutation, payment action, or revenue recognition.",
        "",
        "| Queue | Currency | Rank | Opportunity | Offer | Value minor | Probability bps | Expected minor | Buyer stage | Fit | HOLD reasons |",
        "|---|---|---:|---|---|---:|---:|---:|---|---|---|",
    ]
    for r in output["rows"]:
        reasons = ", ".join(r["hold_reasons"]) if r["hold_reasons"] else ""
        rank = "" if r["rank"] is None else str(r["rank"])
        prob = "" if r["probability_bps"] is None else str(r["probability_bps"])
        expected = "" if r["expected_value_minor"] is None else str(r["expected_value_minor"])
        lines.append(
            f"| {r['queue']} | {r['currency']} | {rank} | `{r['opportunity_id']}` | `{r['offer_id']}` | "
            f"{r['commercial_value_minor']} | {prob} | {expected} | {r['buyer_stage']} | {r['fit_state']} | {reasons} |"
        )
    lines.extend(
        [
            "",
            "Currency groups are never converted or compared through an inferred FX rate.",
            "Rows without an explicit owner-supplied probability are kept in the EVIDENCE_STRENGTH queue; no probability is invented.",
            "",
        ]
    )
    return "\n".join(lines)


def compile_portfolio(
    document: Any,
    _output_schema: str = OUTPUT_SCHEMA,
    _receipt_schema: str = RECEIPT_SCHEMA,
    _validate_input=validate_input,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    normalized = _validate_input(document)
    rows = _rank_rows([_row(c) for c in normalized["candidates"]])
    output: dict[str, Any] = {
        "schema": _output_schema,
        "portfolio_id": normalized["portfolio_id"],
        "ranking_policy": {
            "currency_policy": "NO_FX_COMPARE_WITHIN_CURRENCY_ONLY",
            "probability_policy": "EXPLICIT_OWNER_BPS_ONLY_NO_INFERENCE",
            "expected_value_formula": "floor(commercial_value_minor * probability_bps / 10000)",
            "hold_dominates_rank": True,
        },
        "counts": {
            "total": len(rows),
            "expected_value": sum(r["queue"] == "EXPECTED_VALUE" for r in rows),
            "evidence_strength": sum(r["queue"] == "EVIDENCE_STRENGTH" for r in rows),
            "hold": sum(r["queue"] == "HOLD" for r in rows),
        },
        "rows": rows,
        "external_send_authorized": False,
        "provider_mutation_authorized": False,
        "payment_or_revenue_inferred": False,
    }
    output["output_sha256"] = sha256_document(output)
    markdown = render_markdown(output)
    receipt: dict[str, Any] = {
        "schema": _receipt_schema,
        "portfolio_id": normalized["portfolio_id"],
        "input_sha256": sha256_document(normalized),
        "output_sha256": output["output_sha256"],
        "markdown_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        "counts": dict(output["counts"]),
        "external_send_authorized": False,
        "provider_mutation_authorized": False,
        "payment_or_revenue_inferred": False,
    }
    receipt["receipt_sha256"] = sha256_document(receipt)
    return output, markdown, receipt


def verify_bundle(
    document: Any,
    output: Any,
    markdown: str,
    receipt: Any,
) -> dict[str, Any]:
    if type(output) is not dict or type(receipt) is not dict or not isinstance(markdown, str):
        raise AllocationError("bundle types invalid")
    expected_output, expected_markdown, expected_receipt = compile_portfolio(document)
    if output != expected_output:
        raise AllocationError("output semantic verification failed")
    if markdown != expected_markdown:
        raise AllocationError(bmarkdown semantic verification failed")
    if receipt != expected_receipt:
        raise AllocationError("receipt semantic verification failed")
    return {
        "valid": True,
        "portfolio_id": expected_output["portfolio_id"],
        "output_sha256": expected_output["output_sha256"],
        "receipt_sha256": expected_receipt["receipt_sha256"],
        "external_send_authorized": False,
        "provider_mutation_authorized": False,
        "payment_or_revenue_inferred": False,
    }
