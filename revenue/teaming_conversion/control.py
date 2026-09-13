#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from typing import Any

from .common import (
    DISPOSITIONS, INPUT_SCHEMA, POLICY_SCHEMA, RECEIPT_SCHEMA, ControlError, DuplicateKeyError, _dedupe_or_conflict, _format_time, _json_ready,
    _parse_time, _reject_unknown, _require_as_of, _require_dict, _require_sha256, canonical_bytes,
    digest_bytes, digest_object, parse_json_bytes, read_bounded_regular, write_exclusive_regular,
)
from .parse import _parse_input, _parse_policy

def _evaluate(
    packet: dict[str, Any],
    policy: dict[str, Any],
    as_of: datetime,
    *,
    custody_mode: str,
    input_sha256: str,
    policy_sha256: str,
) -> dict[str, Any]:
    parsed = _parse_input(packet)
    parsed_policy = _parse_policy(policy)
    now = _require_as_of(as_of)
    blockers: list[str] = []
    owner_actions: list[str] = []

    opportunity = parsed["opportunity"]
    future_skew = parsed_policy["max_future_skew_seconds"]
    source_checked_at = opportunity["source_checked_at"]
    if (source_checked_at - now).total_seconds() > future_skew:
        blockers.append("opportunity_source_from_future")
    elif (now - source_checked_at).total_seconds() > parsed_policy["max_source_age_seconds"]:
        blockers.append("opportunity_source_stale")

    observations, obs_conflicts = _dedupe_or_conflict(
        parsed["observations"], id_key="observation_id", extra_unique_key="message_id", label="observation"
    )
    blockers.extend(obs_conflicts)
    for obs in observations:
        if obs["thread_id"] != opportunity["thread_id"]:
            blockers.append(f"cross_thread_observation:{obs['observation_id']}")
        delta_future = (obs["received_at"] - now).total_seconds()
        if delta_future > future_skew:
            blockers.append(f"future_observation:{obs['observation_id']}")
    obs_by_id = {obs["observation_id"]: obs for obs in observations}
    for obs in observations:
        predecessor_id = obs["supersedes_observation_id"]
        if predecessor_id is None:
            continue
        predecessor = obs_by_id.get(predecessor_id)
        if predecessor is None:
            blockers.append(f"unknown_superseded_observation:{obs['observation_id']}")
        elif predecessor["received_at"] >= obs["received_at"]:
            blockers.append(f"invalid_supersession_chronology:{obs['observation_id']}")

    current: dict[str, Any] | None = None
    if observations:
        ordered = sorted(observations, key=lambda row: (row["received_at"], row["observation_id"]))
        latest_time = ordered[-1]["received_at"]
        latest = [row for row in ordered if row["received_at"] == latest_time]
        if len(latest) != 1:
            blockers.append("ambiguous_latest_observation")
        else:
            current = latest[0]
            if (now - current["received_at"]).total_seconds() > parsed_policy["max_reply_age_seconds"]:
                blockers.append("current_observation_stale")

    assets, asset_conflicts = _dedupe_or_conflict(
        parsed["assets"], id_key="asset_id", extra_unique_key=None, label="asset"
    )
    blockers.extend(asset_conflicts)
    releases, release_conflicts = _dedupe_or_conflict(
        parsed["release_records"], id_key="release_id", extra_unique_key=None, label="release"
    )
    blockers.extend(release_conflicts)
    gates, gate_conflicts = _dedupe_or_conflict(
        parsed["qualification_gates"], id_key="gate_id", extra_unique_key=None, label="gate"
    )
    blockers.extend(gate_conflicts)
    commitments, commitment_conflicts = _dedupe_or_conflict(
        parsed["commitments"], id_key="commitment_id", extra_unique_key=None, label="commitment"
    )
    blockers.extend(commitment_conflicts)

    for release in releases:
        if (release["approved_at"] - now).total_seconds() > future_skew:
            blockers.append(f"future_release_record:{release['release_id']}")

    asset_by_id = {asset["asset_id"]: asset for asset in assets}
    gate_by_id = {gate["gate_id"]: gate for gate in gates}

    required_asset_ids: list[str] = []
    seen_required_assets: set[str] = set()
    for asset in assets:
        if asset["required_for_followup"] and asset["asset_id"] not in seen_required_assets:
            seen_required_assets.add(asset["asset_id"])
            required_asset_ids.append(asset["asset_id"])
    for asset_id in parsed_policy["required_asset_ids"] + parsed["requested_asset_ids"]:
        if asset_id not in seen_required_assets:
            seen_required_assets.add(asset_id)
            required_asset_ids.append(asset_id)

    safe_assets: list[dict[str, Any]] = []
    asset_blockers: list[str] = []
    for asset_id in sorted(required_asset_ids):
        asset = asset_by_id.get(asset_id)
        if asset is None:
            asset_blockers.append(f"required_asset_missing:{asset_id}")
            continue
        if asset["prep_state"] != "READY":
            asset_blockers.append(f"required_asset_not_ready:{asset_id}")
            continue
        if asset["release_class"] == "INTERNAL_ONLY":
            asset_blockers.append(f"required_asset_internal_only:{asset_id}")
            continue
        if asset["release_class"] == "OWNER_APPROVAL_REQUIRED":
            matching = [
                r
                for r in releases
                if r["asset_id"] == asset_id
                and r["asset_version"] == asset["version"]
                and r["asset_sha256"] == asset["sha256"]
                and (r["approved_at"] - now).total_seconds() <= future_skew
            ]
            if not matching:
                asset_blockers.append(f"required_asset_owner_release_missing:{asset_id}")
                continue
        safe_assets.append(
            {
                "asset_id": asset["asset_id"],
                "title": asset["title"],
                "version": asset["version"],
                "sha256": asset["sha256"],
                "release_class": asset["release_class"],
                "safe_snippets": list(asset["safe_snippets"]),
            }
        )

    # Also allow optional already-safe assets in the owner brief, but never INTERNAL_ONLY.
    safe_ids = {a["asset_id"] for a in safe_assets}
    for asset in sorted(assets, key=lambda row: row["asset_id"]):
        if asset["asset_id"] in safe_ids or asset["prep_state"] != "READY":
            continue
        if asset["release_class"] in {"PROSPECT_SAFE_SUMMARY", "PROSPECT_SAFE_PUBLIC_REFERENCE"}:
            safe_assets.append(
                {
                    "asset_id": asset["asset_id"],
                    "title": asset["title"],
                    "version": asset["version"],
                    "sha256": asset["sha256"],
                    "release_class": asset["release_class"],
                    "safe_snippets": list(asset["safe_snippets"]),
                }
            )
        elif asset["release_class"] == "OWNER_APPROVAL_REQUIRED":
            matching = [
                r
                for r in releases
                if r["asset_id"] == asset["asset_id"]
                and r["asset_version"] == asset["version"]
                and r["asset_sha256"] == asset["sha256"]
                and (r["approved_at"] - now).total_seconds() <= future_skew
            ]
            if matching:
                safe_assets.append(
                    {
                        "asset_id": asset["asset_id"],
                        "title": asset["title"],
                        "version": asset["version"],
                        "sha256": asset["sha256"],
                        "release_class": asset["release_class"],
                        "safe_snippets": list(asset["safe_snippets"]),
                    }
                )

    qualification_blockers: list[str] = []
    for gate in sorted(gates, key=lambda row: row["gate_id"]):
        if gate["mandatory"] and gate["state"] in {"BLOCKED", "UNKNOWN"}:
            qualification_blockers.append(f"mandatory_gate_{gate['state'].lower()}:{gate['gate_id']}")
            if gate["owner_action"]:
                owner_actions.append(gate["owner_action"])
        elif gate["mandatory"] and gate["state"] == "CURABLE" and gate["owner_action"]:
            owner_actions.append(gate["owner_action"])
    for gate_id in parsed_policy["required_clear_gate_ids"]:
        gate = gate_by_id.get(gate_id)
        if gate is None:
            qualification_blockers.append(f"required_clear_gate_missing:{gate_id}")
        elif gate["state"] != "CLEAR":
            qualification_blockers.append(f"required_clear_gate_not_clear:{gate_id}:{gate['state']}")
            if gate["owner_action"]:
                owner_actions.append(gate["owner_action"])

    approved_commitments: list[dict[str, Any]] = []
    for commitment in sorted(commitments, key=lambda row: row["commitment_id"]):
        if commitment["required_for_followup"] and not commitment["approved"]:
            qualification_blockers.append(
                f"required_commitment_not_approved:{commitment['commitment_id']}:{commitment['kind']}"
            )
        if commitment["approved"]:
            approved_commitments.append(
                {
                    "commitment_id": commitment["commitment_id"],
                    "kind": commitment["kind"],
                    "safe_fact": commitment["safe_fact"],
                    "approval_ref": commitment["approval_ref"],
                }
            )

    blockers = sorted(set(blockers))
    asset_blockers = sorted(set(asset_blockers))
    qualification_blockers = sorted(set(qualification_blockers))
    owner_actions = sorted(set(owner_actions))

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
        blockers.append("unsupported_current_interpretation")

    current_projection: dict[str, Any] | None
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
    for asset in sorted(safe_assets, key=lambda row: row["asset_id"]):
        talking_points.extend(asset["safe_snippets"])
    for item in approved_commitments:
        if item["safe_fact"] is not None:
            talking_points.append(str(item["safe_fact"]))
    talking_points = sorted(set(talking_points))

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
        "safe_assets": sorted(safe_assets, key=lambda row: row["asset_id"]),
        "approved_commitments": approved_commitments,
        "clarification_codes": clarification_codes,
        "blockers": blockers,
        "asset_blockers": asset_blockers,
        "qualification_blockers": qualification_blockers,
        "owner_actions": owner_actions,
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


def compile_control(packet: dict[str, Any], policy: dict[str, Any], *, as_of: datetime) -> dict[str, Any]:
    if type(packet) is not dict or type(policy) is not dict:
        raise ControlError("packet and policy must be objects")
    packet_bytes = canonical_bytes(packet)
    policy_bytes = canonical_bytes(policy)
    return _evaluate(
        packet,
        policy,
        as_of,
        custody_mode="canonical_objects",
        input_sha256=digest_bytes(packet_bytes),
        policy_sha256=digest_bytes(policy_bytes),
    )


def compile_bytes(input_bytes: bytes, policy_bytes: bytes, *, as_of: datetime) -> dict[str, Any]:
    packet = parse_json_bytes(input_bytes, "input")
    policy = parse_json_bytes(policy_bytes, "policy")
    return _evaluate(
        packet,
        policy,
        as_of,
        custody_mode="exact_json_bytes",
        input_sha256=digest_bytes(input_bytes),
        policy_sha256=digest_bytes(policy_bytes),
    )


def parse_receipt_bytes(raw: bytes) -> dict[str, Any]:
    receipt = parse_json_bytes(raw, "receipt")
    _reject_unknown(receipt, {"schema_version", "payload", "receipt_sha256"}, "receipt")
    if receipt.get("schema_version") != RECEIPT_SCHEMA:
        raise ControlError(f"receipt.schema_version must equal {RECEIPT_SCHEMA!r}")
    payload = _require_dict(receipt.get("payload"), "receipt.payload")
    digest = _require_sha256(receipt.get("receipt_sha256"), "receipt.receipt_sha256")
    if digest_object(payload) != digest:
        raise ControlError("receipt payload digest mismatch")
    return receipt


def verify_control(
    packet: dict[str, Any], policy: dict[str, Any], receipt: dict[str, Any]
) -> dict[str, Any]:
    normalized_receipt = parse_receipt_bytes(canonical_bytes(receipt))
    payload = _require_dict(normalized_receipt["payload"], "receipt.payload")
    if payload.get("custody_mode") != "canonical_objects":
        raise ControlError("receipt custody_mode is not canonical_objects")
    as_of = _parse_time(payload.get("evaluated_at"), "receipt.payload.evaluated_at")
    expected = compile_control(packet, policy, as_of=as_of)
    if canonical_bytes(expected) != canonical_bytes(normalized_receipt):
        raise ControlError("receipt does not recompile from packet, policy, and evaluated_at")
    return normalized_receipt


def verify_bytes(input_bytes: bytes, policy_bytes: bytes, receipt_bytes: bytes) -> dict[str, Any]:
    receipt = parse_receipt_bytes(receipt_bytes)
    payload = _require_dict(receipt["payload"], "receipt.payload")
    if payload.get("custody_mode") != "exact_json_bytes":
        raise ControlError("receipt custody_mode is not exact_json_bytes")
    as_of = _parse_time(payload.get("evaluated_at"), "receipt.payload.evaluated_at")
    expected = compile_bytes(input_bytes, policy_bytes, as_of=as_of)
    if canonical_bytes(expected) != canonical_bytes(receipt):
        raise ControlError("receipt does not recompile from exact input bytes, policy bytes, and evaluated_at")
    return receipt


def _md_escape(value: str) -> str:
    out = value
    for ch in ("\\", "`", "*", "_", "[", "]", "<", ">", "#", "|"):
        out = out.replace(ch, "\\" + ch)
    return out


def render_markdown(receipt: dict[str, Any]) -> str:
    normalized = parse_receipt_bytes(canonical_bytes(receipt))
    payload = normalized["payload"]
    opp = payload["opportunity"]
    current = payload["current_observation"]
    lines = [
        "# Teaming Conversion Owner Review",
        "",
        f"- Disposition: `{payload['disposition']}`",
        f"- Opportunity: `{opp['opportunity_id']}`",
        f"- Counterparty: `{opp['counterparty_ref']}`",
        f"- Thread: `{opp['thread_id']}`",
        f"- Evaluated: `{payload['evaluated_at']}`",
        f"- Receipt SHA-256: `{normalized['receipt_sha256']}`",
        "",
        "> Owner review only. This artifact authorizes no contact, send, proposal/submission, commercial commitment, contract/signature, spend/payment, award/acceptance claim, cash assertion, or revenue recognition.",
        "",
        "## Current retained reply",
    ]
    if current is None:
        lines.append("- No uniquely current retained reply is available.")
    else:
        lines.extend(
            [
                f"- Observation: `{current['observation_id']}` / message `{current['message_id']}`",
                f"- Received: `{current['received_at']}`",
                f"- Owner-reviewed interpretation: `{current['interpretation']}`",
                f"- Source class: `{current['source_class']}`",
                f"- Content SHA-256: `{current['content_sha256']}`",
            ]
        )
    lines.extend(["", "## Prospect-safe assets"])
    if payload["safe_assets"]:
        for asset in payload["safe_assets"]:
            lines.append(
                f"- `{asset['asset_id']}` — {_md_escape(asset['title'])} (`{asset['version']}`, `{asset['release_class']}`)"
            )
    else:
        lines.append("- None.")
    lines.extend(["", "## Prospect-safe talking points"])
    if payload["talking_points"]:
        for point in payload["talking_points"]:
            lines.append(f"- {_md_escape(point)}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Clarifications / blockers"])
    combined = (
        list(payload["clarification_codes"])
        + list(payload["blockers"])
        + list(payload["asset_blockers"])
        + list(payload["qualification_blockers"])
    )
    if combined:
        for item in sorted(set(combined)):
            lines.append(f"- `{item}`")
    else:
        lines.append("- None.")
    lines.extend(["", "## Owner actions"])
    if payload["owner_actions"]:
        for action in payload["owner_actions"]:
            lines.append(f"- {_md_escape(action)}")
    else:
        lines.append("- None recorded.")
    lines.append("")
    return "\n".join(lines)
