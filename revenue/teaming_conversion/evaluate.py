from __future__ import annotations

from datetime import datetime
from typing import Any

from .assets import evaluate_assets
from .common import DISPOSITIONS, RECEIPT_SCHEMA, ControlError, _format_time, _require_as_of, digest_object
from .evidence import evaluate_evidence
from .parse import _parse_input
from .policy import parse_policy_with_asset_rules
from .qualification import evaluate_qualification


def evaluate(
    packet: dict[str, Any],
    policy: dict[str, Any],
    as_of: datetime,
    *,
    custody_mode: str,
    input_sha256: str,
    policy_sha256: str,
) -> dict[str, Any]:
    parsed = _parse_input(packet)
    parsed_policy = parse_policy_with_asset_rules(policy)
    now = _require_as_of(as_of)

    evidence = evaluate_evidence(parsed, parsed_policy, now)
    asset_state = evaluate_assets(
        parsed, parsed_policy, evidence["assets"], evidence["releases"], now
    )
    qualification = evaluate_qualification(
        parsed_policy, evidence["gates"], evidence["commitments"]
    )

    blockers = sorted(set(evidence["blockers"] + asset_state["blockers"]))
    asset_blockers = asset_state["asset_blockers"]
    qualification_blockers = qualification["qualification_blockers"]
    current = evidence["current"]

    clarification_codes: list[str] = []
    interpretation: str | None = None
    if current is not None:
        interpretation = current["interpretation"]
        clarification_codes = sorted(current["clarification_codes"])

    if blockers or current is None:
        disposition = "HOLD"
    elif interpretation == "DECLINED":
        disposition = "DECLINED"
    elif interpretation in {"AMBIGUOUS", "REQUESTED_MORE_INFO"}:
        disposition = "NEEDS_CLARIFICATION"
    elif qualification_blockers:
        disposition = "QUALIFICATION_BLOCKED"
    elif asset_blockers:
        disposition = "ASSET_PREP_REQUIRED"
    elif interpretation in {"POSITIVE_CONTINUE", "CONDITIONAL_INTEREST"}:
        disposition = "FOLLOWUP_READY"
    else:
        disposition = "HOLD"
        blockers = sorted(set(blockers + ["unsupported_current_interpretation"]))

    if current is None:
        current_projection = None
    else:
        current_projection = {
            "observation_id": current["observation_id"],
            "message_id": current["message_id"],
            "sender_ref": current["sender_ref"],
            "sender_role": current["sender_role"],
            "received_at": _format_time(current["received_at"]),
            "content_sha256": current["content_sha256"],
            "source_class": current["source_class"],
            "interpretation": current["interpretation"],
            "clarification_codes": clarification_codes,
        }

    talking_points: list[str] = []
    for asset in asset_state["safe_assets"]:
        talking_points.extend(asset["safe_snippets"])
    for item in qualification["approved_commitments"]:
        if item["safe_fact"] is not None:
            talking_points.append(str(item["safe_fact"]))
    talking_points = sorted(set(talking_points))

    opportunity = evidence["opportunity"]
    payload = {
        "evaluated_at": _format_time(now),
        "custody_mode": custody_mode,
        "input_sha256": input_sha256,
        "policy_sha256": policy_sha256,
        "opportunity": {
            "opportunity_id": opportunity["opportunity_id"],
            "counterparty_ref": opportunity["counterparty_ref"],
            "thread_id": opportunity["thread_id"],
            "source_digest": opportunity["source_digest"],
            "source_checked_at": _format_time(opportunity["source_checked_at"]),
        },
        "disposition": disposition,
        "current_observation": current_projection,
        "safe_assets": asset_state["safe_assets"],
        "approved_commitments": qualification["approved_commitments"],
        "clarification_codes": clarification_codes,
        "blockers": blockers,
        "asset_blockers": asset_blockers,
        "qualification_blockers": qualification_blockers,
        "owner_actions": qualification["owner_actions"],
        "talking_points": talking_points,
        "authority": {
            "owner_review_only": True,
            "contact_authorized": False,
            "send_authorized": False,
            "portal_action_authorized": False,
            "proposal_or_submission_authorized": False,
            "commercial_commitment_authorized": False,
            "contract_or_signature_authorized": False,
            "spend_or_payment_authorized": False,
            "award_or_acceptance_claim_authorized": False,
            "cash_or_revenue_claim_authorized": False,
        },
    }
    if disposition not in DISPOSITIONS:
        raise ControlError("internal disposition invariant failed")
    return {
        "schema_version": RECEIPT_SCHEMA,
        "payload": payload,
        "receipt_sha256": digest_object(payload),
    }
