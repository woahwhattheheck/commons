#!/usr/bin/env python3
"""Always-on reply-to-revenue composition for Commons.

Inbound from existing outreach roads is ingested once, classified truthfully,
and projected into a public funnel. Automated acknowledgements are never
buyer interest. Positive humans are surfaced with exact context and next
action. Stale contacts are monitored without resend. HARD DNR is absolute.
Cash stays USD 0 without payment evidence. This tool never sends mail,
never opens a second CRM, and never changes commercial state.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RECEIPTS_DIR = ROOT / "revenue" / "payment_ready" / "outreach_receipts"
OBSERVATIONS_PATH = ROOT / "revenue" / "reply_to_revenue" / "observations.json"
FUNNEL_PATH = ROOT / "revenue" / "reply_to_revenue" / "funnel.json"
ACCEPTANCE_TOOL = "revenue/production_survival/acceptance.py"
REPLY_INTAKE_TOOL = "revenue/production_survival/reply_intake.py"
SCHEMA_VERSION = "commons-reply-to-revenue/v1"
KIND = "REPLY_TO_REVENUE_FUNNEL"
CLASSIFICATIONS = {
    "OPT_OUT",
    "AUTO_RESPONSE",
    "NEGATIVE",
    "QUESTION",
    "POSITIVE_SCOPE",
    "NEEDS_HUMAN",
}
CLASS_TO_NEXT = {
    "OPT_OUT": "DNC/CLOSE",
    "AUTO_RESPONSE": "WAIT_FOR_HUMAN_REPLY",
    "NEGATIVE": "CLOSE",
    "QUESTION": "DRAFT_REPLY",
    "POSITIVE_SCOPE": "NEEDS_ACCEPTANCE",
    "NEEDS_HUMAN": "ESCALATE_ONLY_IF_BUYER_REQUESTS_BRYCE",
}
AUTO_ACK_MARKERS = (
    "auto-submitted",
    "automatic reply",
    "auto reply",
    "autoreply",
    "auto-replied",
    "out of office",
    "out-of-office",
    "vacation responder",
    "mailer-daemon",
    "noreply",
    "no-reply",
    "do-not-reply",
    "ticket has been created",
    "we have received your request",
    "thank you for reaching out",
    "this is an automated",
    "automated message",
    "this email is a service",
    "delivered by zendesk",
    "ai assistant",
    "ai agent",
    "this answer was composed by",
    "a human will respond",
    "rate the support you received",
    "how would you rate",
    "customer service survey",
    "csat",
)
POSITIVE_MARKERS = (
    "please invoice",
    "send the sow",
    "we want to proceed",
    "we accept the scope",
    "yes let's run the proof",
    "this is relevant, yes",
)
OPAQUE_RE = re.compile(r"^opaque:[A-Za-z0-9._:-]{8,200}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PROSPECT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,80}$")
FORBIDDEN_CLAIM_RE = re.compile(
    r"\b(replied|accepted|invoiced|authorized|settled|delivered|paid)\b",
    re.IGNORECASE,
)
PUBLIC_LIMITS = [
    "ingest each inbound event_ref once; collision on same ref with different payload hash",
    "automated acknowledgements are not buyer interest",
    "HARD DNR and completed sends are never resent",
    "stale or silent contacts are monitored without a follow-up send",
    "POSITIVE_SCOPE stops at NEEDS_ACCEPTANCE; this tool does not accept, invoice, or collect",
    "cash_usd is 0 unless a named payment evidence URL is present",
    "no mailbox send, no second CRM, no secrets, no auth gate",
]


class ReplyRevenueError(ValueError):
    """A funnel, observation, or transport plan failed closed."""


class CollisionError(ReplyRevenueError):
    """The same inbound event was presented with different bytes."""


class ResendError(ReplyRevenueError):
    """A plan would contact a HARD DNR or otherwise send mail."""


def canonical_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReplyRevenueError(f"cannot read JSON object {path}: {error}") from error
    if not isinstance(value, dict):
        raise ReplyRevenueError(f"{path} must contain one JSON object")
    return value


def parse_time(value: str) -> dt.datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = dt.datetime.fromisoformat(text)
    except (TypeError, ValueError) as error:
        raise ReplyRevenueError(f"invalid date-time: {value}") from error
    if parsed.tzinfo is None:
        raise ReplyRevenueError("date-time must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if not EMAIL_RE.fullmatch(normalized) or len(normalized) > 254:
        raise ReplyRevenueError(f"invalid email address: {value}")
    return normalized


def organization_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _exact_keys(value: dict[str, Any], expected: set[str], where: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ReplyRevenueError(
            f"{where} fields differ: missing={sorted(expected - actual)} extra={sorted(actual - expected)}"
        )


def _assert_no_forbidden_claims(blob: str) -> None:
    match = FORBIDDEN_CLAIM_RE.search(blob)
    if match:
        raise ReplyRevenueError(f"funnel emitted forbidden claim {match.group(0)!r}")


def classify_signals(
    markers: list[str],
    requested: str | None = None,
) -> dict[str, Any]:
    if not isinstance(markers, list) or not all(isinstance(item, str) and item.strip() for item in markers):
        raise ReplyRevenueError("markers must be nonempty strings")
    blob = " ".join(item.casefold() for item in markers)
    matched_auto = [marker for marker in AUTO_ACK_MARKERS if marker in blob]
    if matched_auto:
        if requested in {"POSITIVE_SCOPE", "QUESTION"}:
            reason = "auto-ack markers override a positivity or question claim"
        else:
            reason = "automated acknowledgement is not buyer interest"
        return {
            "classification": "AUTO_RESPONSE",
            "next_action": CLASS_TO_NEXT["AUTO_RESPONSE"],
            "buyer_interest": False,
            "auto_ack": True,
            "matched_markers": matched_auto,
            "reason": reason,
        }
    if requested is not None:
        if requested not in CLASSIFICATIONS:
            raise ReplyRevenueError(f"unknown classification: {requested}")
        return {
            "classification": requested,
            "next_action": CLASS_TO_NEXT[requested],
            "buyer_interest": requested == "POSITIVE_SCOPE",
            "auto_ack": False,
            "matched_markers": [],
            "reason": "operator classification with no auto-ack markers",
        }
    matched_positive = [marker for marker in POSITIVE_MARKERS if marker in blob]
    if matched_positive:
        return {
            "classification": "POSITIVE_SCOPE",
            "next_action": CLASS_TO_NEXT["POSITIVE_SCOPE"],
            "buyer_interest": True,
            "auto_ack": False,
            "matched_markers": matched_positive,
            "reason": "explicit buyer-scope language with no auto-ack markers",
        }
    return {
        "classification": "NEEDS_HUMAN",
        "next_action": CLASS_TO_NEXT["NEEDS_HUMAN"],
        "buyer_interest": False,
        "auto_ack": False,
        "matched_markers": [],
        "reason": "no auto-ack and no explicit buyer-scope language",
    }


def load_receipts(directory: Path = RECEIPTS_DIR) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        receipt = read_object(path)
        relative = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
        recipient = receipt.get("recipient_email")
        organization = receipt.get("organization") or receipt.get("target_id") or path.stem
        target_id = receipt.get("target_id")
        if not isinstance(target_id, str) or not target_id.strip():
            target_id = path.stem.split("-")[1] if "-" in path.stem else path.stem
        prospect_key = re.sub(r"[^a-z0-9._-]", "-", str(target_id).casefold())
        if not PROSPECT_RE.fullmatch(prospect_key):
            prospect_key = "contact." + sha256_text(path.name)[:12]
        dedupe = receipt.get("dedupe") if isinstance(receipt.get("dedupe"), dict) else {}
        hard_dnr = dedupe.get("do_not_resend") is True or receipt.get("provider_state") == "COMPLETED"
        cash = 0
        facts = receipt.get("facts") if isinstance(receipt.get("facts"), dict) else {}
        if type(facts.get("collected_cash_usd")) is int:
            cash = facts["collected_cash_usd"]
        receipts.append(
            {
                "path": relative,
                "receipt_id": receipt.get("receipt_id") or path.stem,
                "prospect_key": prospect_key,
                "organization": organization if isinstance(organization, str) else prospect_key,
                "recipient_email": normalize_email(recipient) if isinstance(recipient, str) else None,
                "provider_reference": receipt.get("provider_reference"),
                "provider_state": receipt.get("provider_state"),
                "response_state": receipt.get("response_state") or "UNKNOWN",
                "hard_dnr": bool(hard_dnr),
                "cash_usd": cash,
                "observed_at": receipt.get("observed_at") or receipt.get("provider_completed_at"),
            }
        )
    if not receipts:
        raise ReplyRevenueError("no canonical outreach receipts found")
    return receipts


def load_observations(path: Path = OBSERVATIONS_PATH) -> dict[str, Any]:
    value = read_object(path)
    _exact_keys(value, {"schema_version", "kind", "measured_at", "monitor", "events"}, "observations")
    if value["schema_version"] != "commons-reply-to-revenue-observations/v1":
        raise ReplyRevenueError("unsupported observations version")
    if value["kind"] != "REPLY_TO_REVENUE_OBSERVATIONS":
        raise ReplyRevenueError("unsupported observations kind")
    parse_time(value["measured_at"])
    monitor = value["monitor"]
    if not isinstance(monitor, dict):
        raise ReplyRevenueError("monitor must be an object")
    _exact_keys(
        monitor,
        {"connector", "status", "mailbox_claim", "sends", "queries", "attributed_inbound"},
        "monitor",
    )
    if type(monitor["sends"]) is not int or monitor["sends"] != 0:
        raise ReplyRevenueError("monitor.sends must be 0")
    if type(monitor["queries"]) is not int or monitor["queries"] < 0:
        raise ReplyRevenueError("monitor.queries must be a non-negative integer")
    if type(monitor["attributed_inbound"]) is not int or monitor["attributed_inbound"] < 0:
        raise ReplyRevenueError("monitor.attributed_inbound must be a non-negative integer")
    events = value["events"]
    if not isinstance(events, list):
        raise ReplyRevenueError("events must be an array")
    seen_refs: dict[str, str] = {}
    seen_hashes: dict[str, str] = {}
    cleaned: list[dict[str, Any]] = []
    fields = {
        "event_ref",
        "received_at",
        "prospect_key",
        "payload_sha256",
        "markers",
        "provider",
        "matched_receipt_id",
        "requested_classification",
    }
    for index, event in enumerate(events):
        where = f"events[{index}]"
        if not isinstance(event, dict):
            raise ReplyRevenueError(f"{where} must be an object")
        _exact_keys(event, fields, where)
        if not OPAQUE_RE.fullmatch(event["event_ref"]):
            raise ReplyRevenueError(f"{where}.event_ref is invalid")
        parse_time(event["received_at"])
        if not PROSPECT_RE.fullmatch(event["prospect_key"]):
            raise ReplyRevenueError(f"{where}.prospect_key is invalid")
        if not SHA256_RE.fullmatch(event["payload_sha256"]):
            raise ReplyRevenueError(f"{where}.payload_sha256 is invalid")
        if not isinstance(event["markers"], list):
            raise ReplyRevenueError(f"{where}.markers must be an array")
        requested = event["requested_classification"]
        if requested is not None and requested not in CLASSIFICATIONS:
            raise ReplyRevenueError(f"{where}.requested_classification is invalid")
        previous = seen_refs.get(event["event_ref"])
        if previous and previous != event["payload_sha256"]:
            raise CollisionError(f"duplicate event_ref with different payload: {event['event_ref']}")
        hashed = seen_hashes.get(event["payload_sha256"])
        if hashed and hashed != event["event_ref"]:
            raise CollisionError(f"duplicate payload_sha256 under a second event_ref")
        if event["event_ref"] in seen_refs:
            continue
        seen_refs[event["event_ref"]] = event["payload_sha256"]
        seen_hashes[event["payload_sha256"]] = event["event_ref"]
        verdict = classify_signals(event["markers"], requested)
        cleaned.append(
            {
                "event_ref": event["event_ref"],
                "received_at": event["received_at"],
                "prospect_key": event["prospect_key"],
                "payload_sha256": event["payload_sha256"],
                "provider": event["provider"],
                "matched_receipt_id": event["matched_receipt_id"],
                **verdict,
            }
        )
    if monitor["attributed_inbound"] != len(cleaned):
        raise ReplyRevenueError("monitor.attributed_inbound does not match ingested unique events")
    value = dict(value)
    value["events"] = cleaned
    return value


def _contact_rows(receipts: list[dict[str, Any]], inbound: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        key = receipt["prospect_key"]
        row = grouped.setdefault(
            key,
            {
                "prospect_key": key,
                "organization": receipt["organization"],
                "hard_dnr": False,
                "receipt_ids": [],
                "receipt_paths": [],
                "cash_usd": 0,
                "inbound_event_refs": [],
                "classifications": [],
            },
        )
        row["hard_dnr"] = row["hard_dnr"] or receipt["hard_dnr"]
        row["receipt_ids"].append(receipt["receipt_id"])
        row["receipt_paths"].append(receipt["path"])
        row["cash_usd"] += receipt["cash_usd"]
        if not isinstance(row["organization"], str) or not row["organization"].strip():
            row["organization"] = receipt["organization"]
    by_receipt = {}
    for receipt in receipts:
        by_receipt[receipt["receipt_id"]] = receipt["prospect_key"]
    for event in inbound:
        key = event["prospect_key"]
        if key not in grouped and event["matched_receipt_id"] in by_receipt:
            key = by_receipt[event["matched_receipt_id"]]
        if key not in grouped:
            grouped[key] = {
                "prospect_key": key,
                "organization": key,
                "hard_dnr": True,
                "receipt_ids": [],
                "receipt_paths": [],
                "cash_usd": 0,
                "inbound_event_refs": [],
                "classifications": [],
            }
        grouped[key]["inbound_event_refs"].append(event["event_ref"])
        grouped[key]["classifications"].append(event["classification"])
    rows = []
    for key, row in grouped.items():
        classes = row["classifications"]
        if "POSITIVE_SCOPE" in classes:
            lane = "HUMAN_POSITIVE"
            next_action = "NEEDS_ACCEPTANCE"
            handoff = ACCEPTANCE_TOOL
        elif "QUESTION" in classes:
            lane = "HUMAN_QUESTION"
            next_action = "DRAFT_REPLY"
            handoff = REPLY_INTAKE_TOOL
        elif "OPT_OUT" in classes or "NEGATIVE" in classes:
            lane = "CLOSED"
            next_action = "DNC/CLOSE" if "OPT_OUT" in classes else "CLOSE"
            handoff = None
        elif "AUTO_RESPONSE" in classes:
            lane = "AUTO_ACK_WAIT"
            next_action = "WAIT_FOR_HUMAN_REPLY"
            handoff = None
        elif "NEEDS_HUMAN" in classes:
            lane = "NEEDS_HUMAN"
            next_action = "ESCALATE_ONLY_IF_BUYER_REQUESTS_BRYCE"
            handoff = None
        else:
            lane = "NO_RESPONSE"
            next_action = "MONITOR_NO_RESEND"
            handoff = None
        rows.append(
            {
                "prospect_key": row["prospect_key"],
                "organization": row["organization"],
                "hard_dnr": True if row["hard_dnr"] or row["receipt_ids"] else row["hard_dnr"],
                "lane": lane,
                "next_action": next_action,
                "handoff": handoff,
                "receipt_count": len(row["receipt_ids"]),
                "inbound_count": len(row["inbound_event_refs"]),
                "cash_usd": row["cash_usd"],
                "resend": False,
            }
        )
    rows.sort(key=lambda item: (item["lane"], item["prospect_key"]))
    return rows


def surface_positives(contacts: list[dict[str, Any]], inbound: list[dict[str, Any]]) -> list[dict[str, Any]]:
    positives = []
    inbound_by_key: dict[str, list[dict[str, Any]]] = {}
    for event in inbound:
        inbound_by_key.setdefault(event["prospect_key"], []).append(event)
    for contact in contacts:
        if contact["lane"] != "HUMAN_POSITIVE":
            continue
        events = inbound_by_key.get(contact["prospect_key"], [])
        latest = max(events, key=lambda item: item["received_at"]) if events else None
        positives.append(
            {
                "prospect_key": contact["prospect_key"],
                "organization": contact["organization"],
                "event_ref": None if latest is None else latest["event_ref"],
                "received_at": None if latest is None else latest["received_at"],
                "next_action": "NEEDS_ACCEPTANCE",
                "handoff": ACCEPTANCE_TOOL,
                "context": "human inbound classified POSITIVE_SCOPE; auto-ack markers were absent",
                "buyer_interest": True,
            }
        )
    positives.sort(key=lambda item: item["prospect_key"])
    return positives


def build_funnel(
    receipts: list[dict[str, Any]] | None = None,
    observations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipts = receipts if receipts is not None else load_receipts()
    observations = observations if observations is not None else load_observations()
    inbound = list(observations["events"])
    contacts = _contact_rows(receipts, inbound)
    for contact in contacts:
        if contact["cash_usd"] and not contact.get("payment_evidence"):
            if contact["cash_usd"] != 0:
                raise ReplyRevenueError("cash_usd without payment evidence is forbidden")
        contact["hard_dnr"] = True
        contact["resend"] = False
    surfaces = surface_positives(contacts, inbound)
    cash = sum(contact["cash_usd"] for contact in contacts)
    if cash != 0:
        raise ReplyRevenueError("cash_usd must stay 0 without payment evidence")
    counts = {
        "canonical_receipts": len(receipts),
        "distinct_contacts": len(contacts),
        "hard_dnr_contacts": sum(1 for contact in contacts if contact["hard_dnr"]),
        "inbound_recorded": len(inbound),
        "auto_acks": sum(1 for event in inbound if event["auto_ack"]),
        "human_positive": sum(1 for contact in contacts if contact["lane"] == "HUMAN_POSITIVE"),
        "human_question": sum(1 for contact in contacts if contact["lane"] == "HUMAN_QUESTION"),
        "no_response": sum(1 for contact in contacts if contact["lane"] == "NO_RESPONSE"),
        "scope_acceptances": 0,
        "payment_evidence": 0,
        "cash_usd": 0,
        "resends": 0,
        "transport_actions": 0,
    }
    stages = [
        {"id": "SENT_COMPLETED", "count": counts["distinct_contacts"]},
        {"id": "HARD_DNR", "count": counts["hard_dnr_contacts"]},
        {"id": "INBOUND_RECORDED", "count": counts["inbound_recorded"]},
        {"id": "AUTO_ACK", "count": counts["auto_acks"]},
        {"id": "HUMAN_POSITIVE", "count": counts["human_positive"]},
        {"id": "NEEDS_ACCEPTANCE", "count": counts["human_positive"]},
        {"id": "SCOPE_ACCEPTANCE", "count": 0},
        {"id": "PAYMENT_EVIDENCE", "count": 0},
        {"id": "BANK_AVAILABLE", "count": 0},
    ]
    funnel = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "measured_at": observations["measured_at"],
        "truth": counts,
        "stages": stages,
        "contacts": contacts,
        "inbound": [
            {
                "event_ref": event["event_ref"],
                "received_at": event["received_at"],
                "prospect_key": event["prospect_key"],
                "classification": event["classification"],
                "next_action": event["next_action"],
                "auto_ack": event["auto_ack"],
                "buyer_interest": event["buyer_interest"],
                "reason": event["reason"],
                "matched_receipt_id": event["matched_receipt_id"],
            }
            for event in inbound
        ],
        "surfaces": surfaces,
        "monitor": dict(observations["monitor"]),
        "limits": list(PUBLIC_LIMITS),
        "handoffs": {
            "reply_intake": REPLY_INTAKE_TOOL,
            "acceptance": ACCEPTANCE_TOOL,
            "smart_outreach": "host/smart_outreach.py",
            "swarm_mail": "host/swarm_mail.py",
            "cash_now": "host/cash_now.py",
        },
    }
    rendered = canonical_text(funnel)
    _assert_no_forbidden_claims(rendered)
    return funnel


def assert_no_resend(funnel: dict[str, Any], *, send: bool = False) -> None:
    if send:
        raise ResendError("reply-to-revenue never sends; stale contacts are monitored without resend")
    if funnel["truth"]["resends"] != 0 or funnel["truth"]["transport_actions"] != 0:
        raise ResendError("funnel claimed a transport action")
    for contact in funnel["contacts"]:
        if contact.get("resend"):
            raise ResendError(f"contact {contact['prospect_key']} marked resend")
        if contact["hard_dnr"] is not True:
            raise ResendError(f"contact {contact['prospect_key']} is missing HARD DNR")


def validate_funnel(path: Path = FUNNEL_PATH) -> dict[str, Any]:
    expected = build_funnel()
    actual = read_object(path)
    if actual != expected:
        raise ReplyRevenueError("committed funnel snapshot differs from compiled sources")
    assert_no_resend(actual, send=False)
    if actual["truth"]["cash_usd"] != 0:
        raise ReplyRevenueError("cash_usd is not 0")
    if actual["truth"]["human_positive"] != len(actual["surfaces"]):
        raise ReplyRevenueError("positive surfaces drifted from truth")
    return actual


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    snap = subparsers.add_parser("snapshot")
    snap.add_argument("--output", type=Path)
    subparsers.add_parser("validate")
    subparsers.add_parser("surface")
    classify = subparsers.add_parser("classify")
    classify.add_argument("--markers", required=True, help="comma-separated public-safe markers")
    classify.add_argument("--requested", choices=sorted(CLASSIFICATIONS))
    monitor = subparsers.add_parser("monitor")
    monitor.add_argument("--send", action="store_true", help="illegal; always refused")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "classify":
            markers = [item.strip() for item in args.markers.split(",") if item.strip()]
            print(canonical_text(classify_signals(markers, args.requested)), end="")
            return 0
        funnel = build_funnel()
        if args.command == "validate":
            validate_funnel()
            truth = funnel["truth"]
            print(
                "VALID "
                f"{truth['distinct_contacts']} contacts "
                f"{truth['inbound_recorded']} inbound "
                f"{truth['auto_acks']} auto-acks "
                f"{truth['human_positive']} human-positive "
                f"{truth['resends']} resends "
                f"USD {truth['cash_usd']} cash"
            )
            return 0
        if args.command == "surface":
            print(canonical_text(funnel["surfaces"]), end="")
            return 0
        if args.command == "monitor":
            assert_no_resend(funnel, send=args.send)
            print(canonical_text(funnel), end="")
            return 0
        rendered = canonical_text(funnel)
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except CollisionError as error:
        print(str(error), file=sys.stderr)
        return 2
    except ResendError as error:
        print(str(error), file=sys.stderr)
        return 3
    except ReplyRevenueError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
