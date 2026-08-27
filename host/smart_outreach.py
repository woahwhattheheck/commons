#!/usr/bin/env python3
"""Deterministic, evidence-bound outreach planning for Commons.

The planner composes current first-party research, canonical outreach receipts,
the existing offer catalog, and Swarm Mail's later transport seam.  It never
contacts a prospect.  Its job is to make collision, qualification, and draft
readiness explicit before any transport process can observe a message.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "revenue" / "smart_outreach" / "candidates.json"
DEFAULT_RECEIPTS = ROOT / "revenue" / "payment_ready" / "outreach_receipts"
SCHEMA_VERSION = "commons-smart-outreach/v1"
DECISIONS = {
    "READY_TO_DRAFT",
    "RESEARCH_REQUIRED",
    "HOLD_OCCUPIED",
    "HOLD_DO_NOT_RESEND",
    "HOLD_DO_NOT_CONTACT",
    "DISQUALIFIED",
}
PAIN_TERMS = {
    "audit",
    "disconnect",
    "duplicate",
    "failure",
    "idempotent",
    "incident",
    "issue",
    "observability",
    "production",
    "recovery",
    "reliability",
    "replay",
    "reset",
    "rollback",
    "timeout",
    "trace",
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,120}$")


class OutreachError(ValueError):
    """The planner input is incomplete or internally contradictory."""


def canonical_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise OutreachError(f"cannot read JSON object {path}: {error}") from error
    if not isinstance(value, dict):
        raise OutreachError(f"{path} must contain one JSON object")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], where: str) -> None:
    actual = set(value)
    if actual != expected:
        raise OutreachError(
            f"{where} fields differ: missing={sorted(expected-actual)} extra={sorted(actual-expected)}"
        )


def _parse_time(value: str) -> dt.datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = dt.datetime.fromisoformat(text)
    except (TypeError, ValueError) as error:
        raise OutreachError(f"invalid date-time: {value}") from error
    if parsed.tzinfo is None:
        raise OutreachError("date-time must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if not EMAIL_RE.fullmatch(normalized) or len(normalized) > 254:
        raise OutreachError(f"invalid email address: {value}")
    return normalized


def organization_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def validate_input(value: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(value, {"schema_version", "kind", "generated_at", "offer", "prospects"}, "input")
    if value["schema_version"] != SCHEMA_VERSION or value["kind"] != "SMART_OUTREACH_CANDIDATES":
        raise OutreachError("unsupported input version or kind")
    _parse_time(value["generated_at"])
    offer = value["offer"]
    if not isinstance(offer, dict):
        raise OutreachError("offer must be an object")
    _exact_keys(
        offer,
        {"sku_id", "name", "price_usd", "proof_url", "intake_url"},
        "offer",
    )
    if not IDENTIFIER_RE.fullmatch(str(offer["sku_id"])):
        raise OutreachError("offer.sku_id is invalid")
    if type(offer["price_usd"]) is not int or offer["price_usd"] <= 0:
        raise OutreachError("offer.price_usd must be one positive integer")
    for field in ("name", "proof_url", "intake_url"):
        if not isinstance(offer[field], str) or not offer[field].strip():
            raise OutreachError(f"offer.{field} must be non-empty")
    for field in ("proof_url", "intake_url"):
        if not offer[field].startswith("https://"):
            raise OutreachError(f"offer.{field} must be an https URL")
    prospects = value["prospects"]
    if not isinstance(prospects, list) or not prospects:
        raise OutreachError("prospects must be a non-empty array")
    fields = {
        "prospect_id",
        "organization",
        "recipient_email",
        "evidence",
        "owner_role",
        "route",
        "proof_hypothesis",
        "occupied_by",
        "do_not_contact",
        "disqualifiers",
    }
    seen: set[str] = set()
    for index, prospect in enumerate(prospects):
        where = f"prospects[{index}]"
        if not isinstance(prospect, dict):
            raise OutreachError(f"{where} must be an object")
        _exact_keys(prospect, fields, where)
        prospect_id = prospect["prospect_id"]
        if not isinstance(prospect_id, str) or not IDENTIFIER_RE.fullmatch(prospect_id):
            raise OutreachError(f"{where}.prospect_id is invalid")
        if prospect_id in seen:
            raise OutreachError(f"duplicate prospect_id: {prospect_id}")
        seen.add(prospect_id)
        if not isinstance(prospect["organization"], str) or not prospect["organization"].strip():
            raise OutreachError(f"{where}.organization must be non-empty")
        if prospect["recipient_email"] is not None:
            normalize_email(prospect["recipient_email"])
        evidence = prospect["evidence"]
        if not isinstance(evidence, dict):
            raise OutreachError(f"{where}.evidence must be an object")
        _exact_keys(evidence, {"source_url", "observed_at", "exact_quote"}, f"{where}.evidence")
        if not isinstance(evidence["source_url"], str) or not evidence["source_url"].startswith("https://"):
            raise OutreachError(f"{where}.evidence.source_url must be an https URL")
        _parse_time(evidence["observed_at"])
        if not isinstance(evidence["exact_quote"], str) or not evidence["exact_quote"].strip():
            raise OutreachError(f"{where}.evidence.exact_quote must be non-empty")
        route = prospect["route"]
        if not isinstance(route, dict):
            raise OutreachError(f"{where}.route must be an object")
        _exact_keys(route, {"kind", "value", "state"}, f"{where}.route")
        if route["state"] not in {"VERIFIED", "UNVERIFIED"}:
            raise OutreachError(f"{where}.route.state is invalid")
        if route["value"] is not None and not isinstance(route["value"], str):
            raise OutreachError(f"{where}.route.value must be text or null")
        if type(prospect["do_not_contact"]) is not bool:
            raise OutreachError(f"{where}.do_not_contact must be boolean")
        if not isinstance(prospect["disqualifiers"], list) or not all(
            isinstance(item, str) and item.strip() for item in prospect["disqualifiers"]
        ):
            raise OutreachError(f"{where}.disqualifiers must contain non-empty strings")
        for field in ("owner_role", "proof_hypothesis", "occupied_by"):
            if prospect[field] is not None and not isinstance(prospect[field], str):
                raise OutreachError(f"{where}.{field} must be text or null")
    return value


def receipt_index(directory: Path) -> dict[str, dict[str, list[str]]]:
    emails: dict[str, list[str]] = {}
    organizations: dict[str, list[str]] = {}
    for path in sorted(directory.glob("*.json")):
        receipt = read_object(path)
        dedupe = receipt.get("dedupe")
        if not isinstance(dedupe, dict) or dedupe.get("do_not_resend") is not True:
            continue
        relative = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
        recipient = receipt.get("recipient_email")
        if isinstance(recipient, str):
            emails.setdefault(normalize_email(recipient), []).append(relative)
        organization = receipt.get("organization")
        if isinstance(organization, str) and organization.strip():
            organizations.setdefault(organization_key(organization), []).append(relative)
    return {"emails": emails, "organizations": organizations}


def score_prospect(prospect: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    score = 30
    reasons = ["first-party https source and exact quote recorded"]
    missing: list[str] = []
    words = set(re.findall(r"[a-z]+", prospect["evidence"]["exact_quote"].casefold()))
    pain_hits = sorted(words & PAIN_TERMS)
    pain_score = min(25, len(pain_hits) * 5)
    score += pain_score
    if pain_hits:
        reasons.append("specific pain terms: " + ", ".join(pain_hits))
    else:
        missing.append("an observable production failure phrase")
    if isinstance(prospect["owner_role"], str) and prospect["owner_role"].strip():
        score += 15
        reasons.append("relevant owner role identified")
    else:
        missing.append("a relevant owner role")
    route = prospect["route"]
    if route["state"] == "VERIFIED" and isinstance(route["value"], str) and route["value"].strip():
        score += 20
        reasons.append("first-party route verified")
    else:
        missing.append("a verified first-party route")
    if isinstance(prospect["proof_hypothesis"], str) and prospect["proof_hypothesis"].strip():
        score += 10
        reasons.append("binary proof hypothesis recorded")
    else:
        missing.append("a binary proof hypothesis")
    return min(score, 100), reasons, missing


def _draft(prospect: dict[str, Any], offer: dict[str, Any]) -> dict[str, str]:
    quote = prospect["evidence"]["exact_quote"].strip()
    hypothesis = prospect["proof_hypothesis"].strip()
    subject = f"One bounded proof for {prospect['organization']}"
    body = (
        f"You wrote: \u201c{quote}\u201d\n\n"
        f"Commons can test one public-safe binary question: {hypothesis}\n\n"
        f"The single offer is {offer['name']} at ${offer['price_usd']:,}: {offer['intake_url']}\n"
        f"Measured method: {offer['proof_url']}\n\n"
        "Is that failure still active? If not relevant, reply no or opt out and I will close it."
    )
    return {"subject": subject, "body": body}


def classify(
    prospect: dict[str, Any],
    offer: dict[str, Any],
    receipts: dict[str, dict[str, list[str]]],
) -> dict[str, Any]:
    score, reasons, missing = score_prospect(prospect)
    collisions: list[str] = []
    recipient = prospect["recipient_email"]
    if isinstance(recipient, str):
        collisions.extend(receipts["emails"].get(normalize_email(recipient), []))
    collisions.extend(receipts["organizations"].get(organization_key(prospect["organization"]), []))
    collisions = sorted(set(collisions))

    if prospect["do_not_contact"]:
        decision = "HOLD_DO_NOT_CONTACT"
        next_action = "retain suppression; no draft and no transport handoff"
    elif collisions:
        decision = "HOLD_DO_NOT_RESEND"
        next_action = "retain canonical receipt suppression; no draft and no transport handoff"
    elif isinstance(prospect["occupied_by"], str) and prospect["occupied_by"].strip():
        decision = "HOLD_OCCUPIED"
        next_action = "coordinate with the named lane; do not create a second draft"
    elif prospect["disqualifiers"]:
        decision = "DISQUALIFIED"
        next_action = "archive the reasons; do not draft"
    elif missing or score < 70:
        decision = "RESEARCH_REQUIRED"
        next_action = "complete the listed research gaps, then rerun this planner"
    else:
        decision = "READY_TO_DRAFT"
        next_action = "record the private draft in Swarm Mail; this planner does not dispatch"

    return {
        "prospect_id": prospect["prospect_id"],
        "organization": prospect["organization"],
        "recipient_email": recipient,
        "score": score,
        "decision": decision,
        "reasons": reasons,
        "missing": missing,
        "collision_receipts": collisions,
        "occupied_by": prospect["occupied_by"],
        "disqualifiers": list(prospect["disqualifiers"]),
        "evidence": dict(prospect["evidence"]),
        "route": dict(prospect["route"]),
        "owner_role": prospect["owner_role"],
        "draft": _draft(prospect, offer) if decision == "READY_TO_DRAFT" else None,
        "next_action": next_action,
    }


def build_plan(value: dict[str, Any], receipt_directory: Path = DEFAULT_RECEIPTS) -> dict[str, Any]:
    source = validate_input(value)
    receipts = receipt_index(receipt_directory)
    items = [classify(prospect, source["offer"], receipts) for prospect in source["prospects"]]
    priority = {"READY_TO_DRAFT": 0, "RESEARCH_REQUIRED": 1}
    items.sort(key=lambda item: (priority.get(item["decision"], 2), -item["score"], item["prospect_id"]))
    for rank, item in enumerate(items, 1):
        item["rank"] = rank
    counts = {decision: sum(item["decision"] == decision for item in items) for decision in sorted(DECISIONS)}
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "SMART_OUTREACH_PLAN",
        "generated_at": source["generated_at"],
        "offer": dict(source["offer"]),
        "truth": {
            "prospects_evaluated": len(items),
            "decision_counts": counts,
            "drafts_created": counts["READY_TO_DRAFT"],
            "transport_actions": 0,
            "contacts_claimed": 0,
            "cash_usd": 0,
        },
        "items": items,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "validate"):
        child = subparsers.add_parser(command)
        child.add_argument("--input", type=Path, default=DEFAULT_INPUT)
        child.add_argument("--receipts", type=Path, default=DEFAULT_RECEIPTS)
        if command == "plan":
            child.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = build_plan(read_object(args.input), args.receipts)
    if args.command == "validate":
        print(
            f"VALID {plan['truth']['prospects_evaluated']} prospects "
            f"{plan['truth']['drafts_created']} drafts 0 transport actions"
        )
        return 0
    rendered = canonical_text(plan)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
