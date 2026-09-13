#!/usr/bin/env python3
"""Compose outbound send-guard truth with route-lifecycle truth.

The base guard protects buyer/offer dedupe and reply-only semantics. The route
lifecycle protects the exact provider-message/email route after delivery,
complaint, unsubscribe, or DSN evidence arrives. This module makes those two
read-only authorities one fail-closed decision without granting any side
effect authority.

It deliberately recomputes both receipts from source evidence. A caller cannot
supply a claimed route receipt and have it trusted. DSN rows inside route
lifecycle evidence remain subject to the existing dsn_authority source-binding
contract before insertion into that evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from tools.outbound_send_guard import guard, route_lifecycle

SCHEMA = "outbound-send-route-composed-receipt/v1"
SEND_CAPABLE = frozenset({"ALLOW_NEW", "REPLY_ONLY"})


class ComposeError(guard.GuardError):
    """The two authority surfaces cannot be composed safely."""


def _same_file_or_alias(a: Path, b: Path) -> bool:
    try:
        if a.resolve(strict=False) == b.resolve(strict=False):
            return True
    except OSError as exc:
        raise ComposeError(f"cannot resolve path identity: {exc}") from exc
    try:
        return os.path.samefile(a, b)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ComposeError(f"cannot compare path identity: {exc}") from exc


def _read(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ComposeError(f"cannot read {label} {path}: {exc}") from exc


def _latest_mail_outbound(
    evidence: dict[str, Any], recipient: str, generated_at: Any
) -> tuple[dict[str, Any], Any] | None:
    """Return the latest exact provider-mailbox outbound for this route.

    `guard.evaluate` has already strictly validated the evidence snapshot before
    this helper is called, so this function only projects the validated rows.
    """
    candidates: list[tuple[Any, str, dict[str, Any]]] = []
    for row in evidence["mailbox"]["messages"]:
        if row["direction"] != "outbound":
            continue
        if guard.normalize_email(row["counterparty"], "mailbox counterparty") != recipient:
            continue
        observed = guard.parse_time(row["observed_at"], "mailbox observed_at")
        if observed <= generated_at:
            candidates.append((observed, row["message_id"], row))
    if not candidates:
        return None
    observed, _, row = max(candidates, key=lambda item: (item[0], item[1]))
    return row, observed


def _compose_decision(base: str, route: str | None) -> str:
    """Route truth may only demote, never promote, the base guard decision."""
    if base == "DO_NOT_RESEND":
        return base
    if route == "BLOCK_ROUTE":
        return "DO_NOT_RESEND"
    if base == "HOLD":
        return base
    if route == "HOLD_ROUTE":
        return "HOLD"
    return base


def evaluate(
    intent_raw: dict[str, Any],
    evidence_raw: dict[str, Any],
    route_raw: dict[str, Any] | None = None,
    *,
    intent_sha256: str | None = None,
    evidence_sha256: str | None = None,
    route_sha256: str | None = None,
) -> dict[str, Any]:
    """Return one fail-closed composed receipt.

    When the base guard could lead to an outbound action (`ALLOW_NEW` or
    `REPLY_ONLY`) and a prior outbound exists, route-lifecycle evidence is
    mandatory for the *latest* provider-mailbox outbound. Its `as_of` must equal
    the base evidence `generated_at`, preventing a stale pre-DSN lookup from
    being reused against a fresher guard snapshot.
    """
    if type(intent_raw) is not dict or type(evidence_raw) is not dict:
        raise ComposeError("intent and evidence must be objects")
    if route_raw is not None and type(route_raw) is not dict:
        raise ComposeError("route evidence must be an object when supplied")

    # Freeze caller-owned structures before either authority is evaluated.
    intent = deepcopy(intent_raw)
    evidence = deepcopy(evidence_raw)
    route = None if route_raw is None else deepcopy(route_raw)

    base_receipt = guard.evaluate(
        intent,
        evidence,
        intent_sha256=intent_sha256,
        evidence_sha256=evidence_sha256,
    )
    base_payload = base_receipt["payload"]
    base_decision = base_payload["decision"]
    recipient = base_payload["intent"]["recipient"]
    generated_at = guard.parse_time(
        base_payload["evidence"]["generated_at"], "base evidence generated_at"
    )
    latest_base_at = (
        None
        if base_payload["latest_outbound_at"] is None
        else guard.parse_time(base_payload["latest_outbound_at"], "base latest_outbound_at")
    )
    mail_target = _latest_mail_outbound(evidence, recipient, generated_at)

    route_required = base_decision in SEND_CAPABLE and latest_base_at is not None
    route_status = "NOT_APPLICABLE"
    route_receipt: dict[str, Any] | None = None
    route_decision: str | None = None
    target_message_id: str | None = None
    target_sent_at: str | None = None
    reasons = list(base_payload["reasons"])

    # The base guard may derive its latest outbound from Slack alone. A route
    # lifecycle cannot be source-bound without an exact provider message.
    if latest_base_at is not None:
        if mail_target is None or mail_target[1] < latest_base_at:
            route_status = "PROVIDER_MESSAGE_UNAVAILABLE"
            if route_required:
                reasons.append(
                    "latest outbound lacks exact provider-mailbox evidence required for route lifecycle"
                )
        else:
            if mail_target[1] > latest_base_at:
                raise ComposeError("provider-mailbox latest outbound exceeds base guard latest outbound")
            target_message_id = str(mail_target[0]["message_id"])
            target_sent_at = guard.format_time(mail_target[1])
            route_status = "MISSING" if route is None else "EVALUATED"

    if route is not None:
        if latest_base_at is None:
            raise ComposeError("route evidence supplied but base guard has no prior outbound")
        if target_message_id is None or mail_target is None or mail_target[1] != latest_base_at:
            raise ComposeError("route evidence cannot bind to the base guard latest outbound")
        try:
            route_receipt = route_lifecycle.evaluate(route, source_sha256=route_sha256)
        except route_lifecycle.RouteError as exc:
            raise ComposeError(f"route evidence is invalid: {exc}") from exc
        route_payload = route_receipt["payload"]
        route_info = route_payload["route"]
        if guard.normalize_email(route_info["recipient"], "route recipient") != recipient:
            raise ComposeError("route evidence recipient does not match intent route")
        if route_info["provider_message_id"] != target_message_id:
            raise ComposeError("route evidence does not bind the latest provider message")
        if guard.parse_time(route_info["sent_at"], "route sent_at") != mail_target[1]:
            raise ComposeError("route evidence sent_at does not match provider-mailbox evidence")
        if guard.parse_time(route_info["as_of"], "route as_of") != generated_at:
            raise ComposeError("route evidence as_of must equal base evidence generated_at")
        route_decision = route_payload["decision"]
        route_status = "EVALUATED"
        reasons.append(f"latest route lifecycle decision is {route_decision}")
    elif route_required and route_status != "PROVIDER_MESSAGE_UNAVAILABLE":
        reasons.append("route-lifecycle evidence is required for the latest prior outbound")

    if route_required and route_receipt is None:
        final_decision = "HOLD"
    else:
        final_decision = _compose_decision(base_decision, route_decision)

    authority = base_payload["authority"]
    if route_receipt is not None and route_receipt["payload"]["authority"] == "unknown":
        authority = "unknown"
    if route_required and route_receipt is None and authority == "complete":
        authority = "partial"

    payload = {
        "schema_version": SCHEMA,
        "intent": deepcopy(base_payload["intent"]),
        "decision": final_decision,
        "authority": authority,
        "base_guard": {
            "decision": base_decision,
            "receipt_sha256": base_receipt["receipt_sha256"],
            "latest_outbound_at": base_payload["latest_outbound_at"],
            "latest_inbound_at": base_payload["latest_inbound_at"],
        },
        "route_lifecycle": {
            "required": route_required,
            "status": route_status,
            "target_provider_message_id": target_message_id,
            "target_sent_at": target_sent_at,
            "decision": route_decision,
            "receipt_sha256": None if route_receipt is None else route_receipt["receipt_sha256"],
            "source_evidence_sha256": (
                None
                if route_receipt is None
                else route_receipt["payload"]["source_evidence_sha256"]
            ),
        },
        "reasons": reasons,
        "reply_message_id": (
            base_payload["reply_message_id"] if final_decision == "REPLY_ONLY" else None
        ),
        "side_effects_authorized": False,
    }
    return {
        "payload": payload,
        "receipt_sha256": guard.digest_object(payload),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compose outbound guard and route-lifecycle evidence without authorizing a send"
    )
    parser.add_argument("--intent", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--route-evidence", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        inputs = [args.intent, args.evidence]
        if args.route_evidence is not None:
            inputs.append(args.route_evidence)
        for index, left in enumerate(inputs):
            for right in inputs[index + 1 :]:
                if _same_file_or_alias(left, right):
                    raise ComposeError("intent, evidence, and route evidence must be distinct files")
        if args.out is not None and any(_same_file_or_alias(args.out, item) for item in inputs):
            raise ComposeError("output must not alias an input")

        intent_bytes = _read(args.intent, "intent")
        evidence_bytes = _read(args.evidence, "evidence")
        intent = guard.parse_json_bytes(intent_bytes, "intent")
        evidence = guard.parse_json_bytes(evidence_bytes, "evidence")
        route_bytes: bytes | None = None
        route_obj: dict[str, Any] | None = None
        if args.route_evidence is not None:
            route_bytes = _read(args.route_evidence, "route evidence")
            route_obj = route_lifecycle.parse_json_bytes(route_bytes, "route evidence")

        receipt = evaluate(
            intent,
            evidence,
            route_obj,
            intent_sha256=hashlib.sha256(intent_bytes).hexdigest(),
            evidence_sha256=hashlib.sha256(evidence_bytes).hexdigest(),
            route_sha256=(
                None if route_bytes is None else hashlib.sha256(route_bytes).hexdigest()
            ),
        )
        encoded = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        if args.out is None:
            sys.stdout.buffer.write(encoded)
        else:
            guard._atomic_write(args.out, encoded)
        return {"ALLOW_NEW": 0, "REPLY_ONLY": 3, "HOLD": 4, "DO_NOT_RESEND": 5}[
            receipt["payload"]["decision"]
        ]
    except (ComposeError, guard.GuardError, route_lifecycle.RouteError) as exc:
        print(f"outbound-route-guard: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
