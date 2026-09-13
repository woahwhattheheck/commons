#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from typing import Any

from .common import (
    INPUT_SCHEMA, POLICY_SCHEMA, RECEIPT_SCHEMA, ControlError, DuplicateKeyError,
    _parse_time, _reject_unknown, _require_dict, _require_sha256, canonical_bytes,
    digest_bytes, digest_object, parse_json_bytes, read_bounded_regular, write_exclusive_regular,
)
from .evaluate import evaluate


def compile_control(packet: dict[str, Any], policy: dict[str, Any], *, as_of: datetime) -> dict[str, Any]:
    if type(packet) is not dict or type(policy) is not dict:
        raise ControlError("packet and policy must be objects")
    packet_bytes = canonical_bytes(packet)
    policy_bytes = canonical_bytes(policy)
    return evaluate(
        packet, policy, as_of,
        custody_mode="canonical_objects",
        input_sha256=digest_bytes(packet_bytes),
        policy_sha256=digest_bytes(policy_bytes),
    )


def compile_bytes(input_bytes: bytes, policy_bytes: bytes, *, as_of: datetime) -> dict[str, Any]:
    packet = parse_json_bytes(input_bytes, "input")
    policy = parse_json_bytes(policy_bytes, "policy")
    return evaluate(
        packet, policy, as_of,
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
    normalized = parse_receipt_bytes(canonical_bytes(receipt))
    payload = _require_dict(normalized["payload"], "receipt.payload")
    if payload.get("custody_mode") != "canonical_objects":
        raise ControlError("receipt custody_mode is not canonical_objects")
    as_of = _parse_time(payload.get("evaluated_at"), "receipt.payload.evaluated_at")
    expected = compile_control(packet, policy, as_of=as_of)
    if canonical_bytes(expected) != canonical_bytes(normalized):
        raise ControlError("receipt does not recompile from packet, policy, and evaluated_at")
    return normalized


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
        "# Teaming Conversion Owner Review", "",
        f"- Disposition: `{payload['disposition']}`",
        f"- Opportunity: `{opp['opportunity_id']}`",
        f"- Counterparty: `{opp['counterparty_ref']}`",
        f"- Thread: `{opp['thread_id']}`",
        f"- Evaluated: `{payload['evaluated_at']}`",
        f"- Receipt SHA-256: `{normalized['receipt_sha256']}`", "",
        "> Owner review only. This artifact authorizes no contact, send, proposal/submission, commercial commitment, contract/signature, spend/payment, award/acceptance claim, cash assertion, or revenue recognition.",
        "", "## Current retained reply",
    ]
    if current is None:
        lines.append("- No uniquely current retained reply is available.")
    else:
        lines += [
            f"- Observation: `{current['observation_id']}` / message `{current['message_id']}`",
            f"- Received: `{current['received_at']}`",
            f"- Owner-reviewed interpretation: `{current['interpretation']}`",
            f"- Source class: `{current['source_class']}`",
            f"- Content SHA-256: `{current['content_sha256']}`",
        ]
    lines += ["", "## Prospect-safe assets"]
    if payload["safe_assets"]:
        for asset in payload["safe_assets"]:
            lines.append(
                f"- `{asset['asset_id']}` — {_md_escape(asset['title'])} (`{asset['version']}`, `{asset['release_class']}`)"
            )
    else:
        lines.append("- None.")
    lines += ["", "## Prospect-safe talking points"]
    lines += [f"- {_md_escape(point)}" for point in payload["talking_points"]] or ["- None."]
    lines += ["", "## Clarifications / blockers"]
    combined = (
        list(payload["clarification_codes"]) + list(payload["blockers"])
        + list(payload["asset_blockers"]) + list(payload["qualification_blockers"])
    )
    lines += [f"- `{item}`" for item in sorted(set(combined))] or ["- None."]
    lines += ["", "## Owner actions"]
    lines += [f"- {_md_escape(action)}" for action in payload["owner_actions"]] or ["- None recorded."]
    lines.append("")
    return "\n".join(lines)
