#!/usr/bin/env python3
"""Compile Commons revenue truth into one deterministic execution queue.

This control plane composes existing public artifacts.  It does not contact a
prospect, create a checkout, accept a scope, deliver work, or claim cash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from host import smart_outreach  # noqa: E402


CATALOG_PATH = ROOT / "revenue" / "right_now" / "catalog.json"
DIAGNOSTIC_PATH = ROOT / "revenue" / "right_now" / "diagnostic_offer.json"
OUTREACH_PATH = ROOT / "revenue" / "smart_outreach" / "candidates.json"
PAYMENT_PATH = ROOT / "revenue" / "payment_ready" / "current_receipt.json"
HUMAN_PATH = ROOT / "revenue" / "human_outcomes" / "offers.json"
SURVIVAL_PATH = ROOT / "revenue" / "production_survival" / "offer.json"
RECEIPTS_PATH = ROOT / "revenue" / "payment_ready" / "outreach_receipts"
SCHEMA_VERSION = "commons-right-now-control/v1"
DECISION_PRIORITY = {
    "READY_TO_DRAFT": 0,
    "RESEARCH_REQUIRED": 1,
    "HOLD_OCCUPIED": 2,
    "HOLD_DO_NOT_RESEND": 3,
    "HOLD_DO_NOT_CONTACT": 4,
    "DISQUALIFIED": 5,
}


class ControlError(ValueError):
    """A source artifact violates the revenue control contract."""


def canonical_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ControlError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise ControlError(f"{path} must contain one JSON object")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _positive_integer(value: Any, where: str) -> int:
    if type(value) is not int or value <= 0:
        raise ControlError(f"{where} must be a positive integer")
    return value


def validate_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "kind", "as_of", "canonical_page", "purpose",
        "truth", "ranking_rule", "portfolio", "offers",
        "preserved_long_horizon_routes",
    }
    if set(catalog) != required:
        raise ControlError("catalog fields differ from the control contract")
    if catalog["kind"] != "RIGHT_NOW_REVENUE_CATALOG":
        raise ControlError("unsupported catalog kind")
    truth = catalog["truth"]
    for field in ("collected_cash_usd", "verified_positive_replies", "accepted_scopes"):
        if type(truth.get(field)) is not int or truth[field] < 0:
            raise ControlError(f"truth.{field} must be a non-negative integer")
    if type(truth.get("active_chargeable_checkout")) is not bool:
        raise ControlError("truth.active_chargeable_checkout must be boolean")

    human = read_object(HUMAN_PATH)
    survival = read_object(SURVIVAL_PATH)
    diagnostic = read_object(DIAGNOSTIC_PATH)
    canonical = {row["id"]: row for row in human["offers"]}
    entry = survival["entry_offer"]
    canonical[entry["id"]] = entry
    canonical[diagnostic["id"]] = diagnostic
    offers = catalog["offers"]
    if not isinstance(offers, list) or not offers:
        raise ControlError("catalog.offers must be non-empty")
    if [row.get("rank") for row in offers] != list(range(1, len(offers) + 1)):
        raise ControlError("offer rank must be unique and contiguous")
    seen: set[str] = set()
    for row in offers:
        offer_id = row.get("id")
        if not isinstance(offer_id, str) or offer_id in seen:
            raise ControlError("offer ids must be unique non-empty strings")
        seen.add(offer_id)
        if offer_id not in canonical:
            raise ControlError(f"offer lacks canonical source: {offer_id}")
        price = _positive_integer(row.get("price_usd"), f"offers.{offer_id}.price_usd")
        if price != canonical[offer_id]["fixed_amount"]:
            raise ControlError(f"offer price drift: {offer_id}")
        if row.get("payment_state") != "BUYER_SPECIFIC_HANDOFF_REQUIRED":
            raise ControlError(f"unexpected payment state: {offer_id}")
        for field in (
            "delivery_window", "buyer_input", "deliverable", "start_route",
            "source", "next_external_event", "founder_bottleneck", "commons_bottleneck",
        ):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ControlError(f"offers.{offer_id}.{field} must be non-empty")
    return catalog


def payment_truth(value: dict[str, Any]) -> dict[str, Any]:
    facts = value.get("facts")
    if not isinstance(facts, dict):
        raise ControlError("payment receipt facts must be an object")
    cash = facts.get("collected_cash_usd")
    if type(cash) is not int or cash < 0:
        raise ControlError("payment receipt cash must be a non-negative integer")
    cash_claimed = value.get("cash_claimed")
    if type(cash_claimed) is not bool:
        raise ControlError("payment receipt cash_claimed must be boolean")
    processor = facts.get("processor_payment")
    return {
        "receipt_id": value.get("receipt_id"),
        "stage": value.get("stage"),
        "state": value.get("state"),
        "next_stage": value.get("next_stage"),
        "processor_payment": processor,
        "collected_cash_usd": cash,
        "cash_claimed": cash_claimed,
    }


def build_control() -> dict[str, Any]:
    catalog = validate_catalog(read_object(CATALOG_PATH))
    payment = payment_truth(read_object(PAYMENT_PATH))
    outreach = smart_outreach.build_plan(
        smart_outreach.read_object(OUTREACH_PATH), RECEIPTS_PATH
    )
    catalog_cash = catalog["truth"]["collected_cash_usd"]
    if catalog_cash != payment["collected_cash_usd"]:
        raise ControlError("cash truth differs between catalog and payment receipt")
    if payment["cash_claimed"] != (catalog_cash > 0):
        raise ControlError("cash claim is inconsistent with collected cash")

    offers = []
    for row in catalog["offers"]:
        offers.append({
            "rank": row["rank"],
            "id": row["id"],
            "name": row["name"],
            "price_usd": row["price_usd"],
            "delivery_window": row["delivery_window"],
            "start_route": row["start_route"],
            "payment_state": row["payment_state"],
            "next_external_event": row["next_external_event"],
            "founder_bottleneck": row["founder_bottleneck"],
            "commons_bottleneck": row["commons_bottleneck"],
        })

    queue = []
    for item in outreach["items"]:
        queue.append({
            "prospect_id": item["prospect_id"],
            "organization": item["organization"],
            "offer_id": outreach["offer"]["sku_id"],
            "decision": item["decision"],
            "fit_score": item["score"],
            "source_url": item["evidence"]["source_url"],
            "observed_at": item["evidence"]["observed_at"],
            "route_state": item["route"]["state"],
            "collision_receipts": item["collision_receipts"],
            "missing": item["missing"],
            "next_action": item["next_action"],
            "transport_authorized": False,
        })
    queue.sort(key=lambda row: (
        DECISION_PRIORITY.get(row["decision"], 99),
        -row["fit_score"],
        row["prospect_id"],
    ))
    for rank, item in enumerate(queue, 1):
        item["rank"] = rank

    counts = outreach["truth"]["decision_counts"]
    blockers = [
        {
            "rank": 1,
            "id": "LIVE_PAYMENT_EVIDENCE",
            "owner": "FOUNDER_OR_CONNECTED_PROCESSOR_LANE",
            "condition": "A chargeable buyer path and processor receipt are independently evidenced.",
            "current": payment["processor_payment"],
        },
        {
            "rank": 2,
            "id": "QUALIFIED_UNCONTACTED_DEMAND",
            "owner": "COMMONS_RESEARCH_AND_OUTREACH_LANES",
            "condition": "At least one non-colliding evidence-bound prospect reaches READY_TO_DRAFT.",
            "current": counts["READY_TO_DRAFT"],
        },
        {
            "rank": 3,
            "id": "BUYER_ACCEPTANCE",
            "owner": "REAL_BUYER",
            "condition": "A real buyer accepts one exact scope and delivery window.",
            "current": catalog["truth"]["accepted_scopes"],
        },
    ]

    source_paths = [
        CATALOG_PATH,
        DIAGNOSTIC_PATH,
        OUTREACH_PATH,
        PAYMENT_PATH,
        HUMAN_PATH,
        SURVIVAL_PATH,
    ]
    sources = [
        {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
        for path in source_paths
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "RIGHT_NOW_REVENUE_CONTROL",
        "as_of": catalog["as_of"],
        "truth": {
            "collected_cash_usd": catalog_cash,
            "verified_positive_replies": catalog["truth"]["verified_positive_replies"],
            "accepted_scopes": catalog["truth"]["accepted_scopes"],
            "active_chargeable_checkout": catalog["truth"]["active_chargeable_checkout"],
            "prospects_evaluated": outreach["truth"]["prospects_evaluated"],
            "ready_to_draft": counts["READY_TO_DRAFT"],
            "transport_actions": outreach["truth"]["transport_actions"],
        },
        "payment": payment,
        "offers": offers,
        "execution_queue": queue,
        "blockers": blockers,
        "preserved_portfolio": catalog["portfolio"],
        "source_receipts": sources,
    }


def validate_control(value: dict[str, Any]) -> None:
    expected = build_control()
    if value != expected:
        raise ControlError("committed control snapshot differs from compiled sources")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("compile", "validate"))
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=ROOT / "revenue" / "right_now" / "control.json",
    )
    args = parser.parse_args()
    try:
        control = build_control()
        if args.command == "compile":
            sys.stdout.write(canonical_text(control))
        else:
            validate_control(read_object(args.snapshot))
            print(
                "VALID "
                f"{len(control['offers'])} offers "
                f"{len(control['execution_queue'])} opportunities "
                f"{control['truth']['transport_actions']} transports "
                f"USD {control['truth']['collected_cash_usd']} cash"
            )
    except (ControlError, smart_outreach.OutreachError) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
