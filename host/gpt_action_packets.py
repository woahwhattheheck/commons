#!/usr/bin/env python3
"""Compile GPT oversight packets from the right-now queue without sending mail."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "revenue" / "right_now" / "action_packets.json"
DEMAND = ROOT / "revenue" / "right_now" / "demand_ledger.json"
EXPERIMENTS = ROOT / "revenue" / "right_now" / "experiments.json"
CONTROL = ROOT / "revenue" / "right_now" / "control.json"
SEND_AUTHORIZATIONS = ROOT / "revenue" / "right_now" / "send_authorizations.json"

ALLOWED_STATUS = {
    "safe research/build action",
    "ready-to-draft",
    "ready-to-send under existing authorization",
    "owner-sensitive external action",
    "do-not-contact",
    "do-not-resend",
    "needs more evidence",
    "disqualified",
}
AUTH_SCHEMA = "commons-first-party-send-authorizations/v1"
AUTH_KIND = "FIRST_PARTY_SEND_AUTHORIZATIONS"
AUTH_FIELDS = {
    "authorization_id",
    "generation",
    "state",
    "candidate_id",
    "contact_route",
    "message_sha256",
    "issued_at",
    "expires_at",
    "confirm_before_send",
    "evidence",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class PacketError(ValueError):
    """Packet ledger drifted from the no-fiction contract."""


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PacketError(f"{path} must be an object")
    return value


def _utc_seconds(value: Any, where: str) -> datetime:
    if not isinstance(value, str):
        raise PacketError(f"{where} must be canonical UTC seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise PacketError(f"{where} must be canonical UTC seconds") from error
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise PacketError(f"{where} must be canonical UTC seconds")
    return parsed


def _trusted_now(evaluated_at: datetime | None) -> datetime:
    if evaluated_at is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    if not isinstance(evaluated_at, datetime) or evaluated_at.tzinfo is None:
        raise PacketError("evaluated_at must be an aware datetime")
    return evaluated_at.astimezone(timezone.utc).replace(microsecond=0)


def _nonempty_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PacketError(f"{where} must be a non-empty string")
    return value


def _message_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_authorizations(
    value: dict[str, Any], *, evaluated_at: datetime | None = None
) -> dict[str, Any]:
    """Validate the out-of-band first-party send-authorization ledger.

    The ledger is separate from packets so packet bytes cannot mint their own
    send authority. Only the highest generation for one candidate+route is
    current; a later REVOKED row therefore invalidates every older LIVE row.
    """
    required = {"schema_version", "kind", "as_of", "authorizations"}
    if set(value) != required:
        raise PacketError("send authorization ledger fields differ from contract")
    if value.get("schema_version") != AUTH_SCHEMA or value.get("kind") != AUTH_KIND:
        raise PacketError("unsupported send authorization ledger")
    now = _trusted_now(evaluated_at)
    as_of = _utc_seconds(value.get("as_of"), "send_authorizations.as_of")
    if as_of > now:
        raise PacketError("send authorization ledger as_of is in the future")
    rows = value.get("authorizations")
    if not isinstance(rows, list):
        raise PacketError("send authorization rows must be a list")

    by_id: dict[str, dict[str, Any]] = {}
    latest_generation: dict[tuple[str, str], int] = {}
    generations: set[tuple[str, str, int]] = set()
    for index, row in enumerate(rows):
        where = f"send_authorizations.authorizations[{index}]"
        if not isinstance(row, dict) or set(row) != AUTH_FIELDS:
            raise PacketError(f"{where} fields differ from contract")
        authorization_id = _nonempty_string(
            row.get("authorization_id"), f"{where}.authorization_id"
        )
        if authorization_id in by_id:
            raise PacketError("send authorization ids must be unique")
        generation = row.get("generation")
        if type(generation) is not int or generation <= 0:
            raise PacketError(f"{where}.generation must be a positive integer")
        state = row.get("state")
        if state not in {"LIVE", "REVOKED"}:
            raise PacketError(f"{where}.state must be LIVE or REVOKED")
        candidate_id = _nonempty_string(
            row.get("candidate_id"), f"{where}.candidate_id"
        )
        contact_route = _nonempty_string(
            row.get("contact_route"), f"{where}.contact_route"
        )
        digest = row.get("message_sha256")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise PacketError(f"{where}.message_sha256 must be lowercase SHA-256")
        issued = _utc_seconds(row.get("issued_at"), f"{where}.issued_at")
        expires = _utc_seconds(row.get("expires_at"), f"{where}.expires_at")
        if issued >= expires:
            raise PacketError(f"{where} must expire after issuance")
        if row.get("confirm_before_send") is not True:
            raise PacketError(f"{where}.confirm_before_send must be true")
        evidence = row.get("evidence")
        if (
            not isinstance(evidence, list)
            or not evidence
            or not all(isinstance(item, str) and item.strip() for item in evidence)
        ):
            raise PacketError(f"{where}.evidence must be a non-empty string list")
        generation_key = (candidate_id, contact_route, generation)
        if generation_key in generations:
            raise PacketError(
                "send authorization generation must be unique per candidate+route"
            )
        generations.add(generation_key)
        key = (candidate_id, contact_route)
        latest_generation[key] = max(latest_generation.get(key, 0), generation)
        by_id[authorization_id] = row

    return {
        "now": now,
        "by_id": by_id,
        "latest_generation": latest_generation,
    }


def _validate_ready_send(
    row: dict[str, Any], authority: dict[str, Any], *, where: str
) -> None:
    candidate_id = _nonempty_string(row.get("candidate_id"), f"{where}.candidate_id")
    if row.get("lane") != "ready-to-send":
        raise PacketError(f"{candidate_id} ready-to-send requires ready-to-send lane")
    message = _nonempty_string(
        row.get("concise_proposed_message"), f"{where}.concise_proposed_message"
    )
    contact_route = _nonempty_string(
        row.get("public_contact_route"), f"{where}.public_contact_route"
    )
    if row.get("confirm_before_send") is not True:
        raise PacketError(f"{candidate_id} ready-to-send must retain confirm_before_send")
    receipt = row.get("live_first_party_receipt")
    if not isinstance(receipt, dict) or set(receipt) != AUTH_FIELDS:
        raise PacketError(
            f"{candidate_id} ready-to-send requires an exact first-party receipt"
        )
    authorization_id = receipt.get("authorization_id")
    canonical = authority["by_id"].get(authorization_id)
    if canonical is None:
        raise PacketError(
            f"{candidate_id} send receipt is absent from canonical authorization ledger"
        )
    if receipt != canonical:
        raise PacketError(
            f"{candidate_id} send receipt differs from canonical authorization ledger"
        )
    if receipt.get("state") != "LIVE":
        raise PacketError(f"{candidate_id} send receipt is not LIVE")
    if receipt.get("candidate_id") != candidate_id:
        raise PacketError(f"{candidate_id} send receipt candidate binding mismatch")
    if receipt.get("contact_route") != contact_route:
        raise PacketError(f"{candidate_id} send receipt route binding mismatch")
    if receipt.get("message_sha256") != _message_sha256(message):
        raise PacketError(f"{candidate_id} send receipt message binding mismatch")
    key = (candidate_id, contact_route)
    if receipt.get("generation") != authority["latest_generation"].get(key):
        raise PacketError(
            f"{candidate_id} send receipt is not the current authorization generation"
        )
    issued = _utc_seconds(receipt.get("issued_at"), f"{candidate_id}.issued_at")
    expires = _utc_seconds(receipt.get("expires_at"), f"{candidate_id}.expires_at")
    now = authority["now"]
    if issued > now:
        raise PacketError(f"{candidate_id} send receipt is not active yet")
    if expires <= now:
        raise PacketError(f"{candidate_id} send receipt has expired")


def validate_packets(
    value: dict[str, Any],
    authorizations: dict[str, Any] | None = None,
    *,
    evaluated_at: datetime | None = None,
) -> None:
    if value.get("kind") != "GPT_ACTION_PACKETS":
        raise PacketError("unsupported packet kind")
    if authorizations is None:
        authorizations = read_object(SEND_AUTHORIZATIONS)
    authority = validate_authorizations(authorizations, evaluated_at=evaluated_at)
    cash = value.get("cash") or {}
    if cash.get("collected_cash_usd") != 0 or cash.get("cash_claimed") is not False:
        raise PacketError("packets must not invent cash")
    packets = value.get("packets")
    if not isinstance(packets, list) or not packets:
        raise PacketError("packets must be a non-empty list")
    seen = set()
    for index, row in enumerate(packets):
        where = f"packets[{index}]"
        if not isinstance(row, dict):
            raise PacketError(f"{where} must be an object")
        cid = row.get("candidate_id")
        if not isinstance(cid, str) or not cid or cid in seen:
            raise PacketError("packet ids must be unique non-empty strings")
        seen.add(cid)
        status = row.get("status")
        if status not in ALLOWED_STATUS:
            raise PacketError(f"unknown status: {status}")
        if row.get("lane") == "do-not-resend" and "do-not-resend" not in str(
            row.get("status")
        ):
            raise PacketError(f"{cid} DNR lane without DNR status")
        if row.get("economic_state_if_successful") in {"SETTLED", "BANK_AVAILABLE"}:
            raise PacketError("packets must not skip to cash states")
        if status == "ready-to-send under existing authorization":
            _validate_ready_send(row, authority, where=where)
        if row.get("concise_proposed_message") and status in {
            "do-not-resend",
            "do-not-contact",
        }:
            raise PacketError(f"{cid} must not carry a send body")


def validate_experiments(value: dict[str, Any]) -> None:
    rows = value.get("experiments")
    if not isinstance(rows, list) or len(rows) < 8:
        raise PacketError("need at least eight experiments")
    ids = [row.get("id") for row in rows]
    if len(ids) != len(set(ids)):
        raise PacketError("experiment ids must be unique")
    for row in rows:
        if row.get("observed_result") in {"PAID", "CASH", "SOLD"}:
            raise PacketError("experiment result invented cash")
        for field in (
            "hypothesis",
            "buyer",
            "channel",
            "offer",
            "page",
            "cta",
            "next_action",
            "success_event",
            "kill_condition",
            "observed_result",
            "source_evidence",
        ):
            if not str(row.get(field) or "").strip():
                raise PacketError(f"experiment missing {field}")


def validate_demand(value: dict[str, Any]) -> None:
    if value.get("collected_cash_usd") != 0:
        raise PacketError("demand ledger must not invent cash")
    for row in value.get("candidates") or []:
        if not row.get("url") or not row.get("source_date"):
            raise PacketError("demand rows need url and date")
        if row.get("purchasing_ability") not in {"missing", "unverified", "present"}:
            raise PacketError("purchasing_ability must stay exact")


def next_external_action(
    control: dict[str, Any],
    packets: dict[str, Any],
    authorizations: dict[str, Any] | None = None,
    *,
    evaluated_at: datetime | None = None,
) -> str:
    # Revalidate at the consumption boundary so callers cannot validate one
    # generation and later ask `next` to consume moved/stale packet bytes.
    validate_packets(packets, authorizations, evaluated_at=evaluated_at)
    for row in packets["packets"]:
        if row["status"] == "ready-to-send under existing authorization":
            return f"confirm once, then send authorized packet {row['candidate_id']}"
    for item in control.get("execution_queue") or []:
        if item.get("decision") == "READY_TO_DRAFT":
            return f"draft packet for {item['prospect_id']} without sending"
    return (
        "Keep inbound doors live (agent-triage.html, agent-rescue.html, "
        "tokenjunkielabs@gmail.com). Do not resend held prospects. "
        "Founder still must evidence a chargeable processor path."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "next"))
    args = parser.parse_args()
    try:
        packets = read_object(PACKETS)
        demand = read_object(DEMAND)
        experiments = read_object(EXPERIMENTS)
        control = read_object(CONTROL)
        authorizations = read_object(SEND_AUTHORIZATIONS)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        validate_packets(packets, authorizations, evaluated_at=now)
        validate_demand(demand)
        validate_experiments(experiments)
        if control["truth"]["collected_cash_usd"] != 0:
            raise PacketError("control cash drifted")
        if args.command == "validate":
            print(
                "VALID "
                f"{len(packets['packets'])} packets "
                f"{len(demand['candidates'])} demand "
                f"{len(experiments['experiments'])} experiments "
                "USD 0 cash"
            )
        else:
            print(
                next_external_action(
                    control, packets, authorizations, evaluated_at=now
                )
            )
    except (OSError, json.JSONDecodeError, PacketError, KeyError) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
