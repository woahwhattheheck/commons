#!/usr/bin/env python3
"""Compile Commons revenue truth without replaying stale Stripe state as current.

The retained v3 compiler is preserved in ``_right_now_revenue_retained_v3`` for
historical/source-shape validation.  Its checked-in Stripe observation is never
allowed to mint a current ``active_chargeable_checkout`` bit here.  Current
ACTIVE exists only on the explicit authenticated provider-readback path.
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any

from host import right_now_stripe_authority
from host import _right_now_revenue_retained_v3 as _retained


# Re-export the established v3 helpers/constants so callers that import this
# module keep the same non-checkout surfaces.  Authority-sensitive functions
# below deliberately replace the retained implementations.
_REPLACED = {
    "validate_checkout_authority",
    "build_checkout_authority",
    "validate_catalog",
    "build_control",
    "validate_control",
    "main",
}
for _name in dir(_retained):
    if _name.startswith("__") or _name in _REPLACED:
        continue
    globals()[_name] = getattr(_retained, _name)

HISTORICAL_CHECKOUT_AUTHORITY = "RETAINED_HISTORICAL_STRIPE_EVIDENCE"
CURRENT_CHECKOUT_AUTHORITY = "AUTHENTICATED_STRIPE_CURRENT_READBACK"
CURRENT_CONTROL_SCHEMA_VERSION = "commons-right-now-control/v4-current"


def validate_checkout_authority(
    provider_offer: dict[str, Any],
    public_page: str,
    catalog_as_of: str,
) -> dict[str, Any]:
    """Validate retained checkout evidence as historical, never current.

    The retained v3 validator remains useful for exact provider identity,
    receipt, chronology, and public-page integrity.  Its old ``active=True``
    conclusion is intentionally stripped: repository bytes cannot prove that a
    Stripe Payment Link is still enabled now.
    """

    retained = dict(
        _retained.validate_checkout_authority(
            provider_offer,
            public_page,
            catalog_as_of,
        )
    )
    retained["active"] = False
    retained["historically_verified"] = True
    retained["authority"] = HISTORICAL_CHECKOUT_AUTHORITY
    retained["current_state"] = "AUTHENTICATED_PROVIDER_READBACK_REQUIRED"
    return retained


def build_checkout_authority(catalog_as_of: str) -> dict[str, Any]:
    """Build the non-authorizing retained checkout evidence view."""

    try:
        public_page = AUTOPSY_PUBLIC_PAGE_PATH.read_text(encoding="utf-8")
    except OSError as error:
        raise ControlError(f"cannot read {AUTOPSY_PUBLIC_PAGE_PATH}: {error}") from error
    return validate_checkout_authority(
        read_object(AUTOPSY_PROVIDER_PATH),
        public_page,
        catalog_as_of,
    )


def validate_catalog(
    catalog: dict[str, Any],
    checkout_authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate catalog structure while refusing static current-checkout truth.

    ``LIVE_PUBLIC_CHECKOUT_PAGE`` still means the public route and retained
    offer identity exist.  It no longer means Stripe has been observed active
    *now*.  The checked-in catalog therefore must not claim current ACTIVE.
    """

    if not isinstance(catalog, dict):
        raise ControlError("catalog must be an object")
    truth = catalog.get("truth")
    if not isinstance(truth, dict):
        raise ControlError("catalog.truth must be an object")
    if truth.get("active_chargeable_checkout") is not False:
        raise ControlError(
            "checked-in truth.active_chargeable_checkout must be false until authenticated Stripe readback"
        )

    historical = build_checkout_authority(catalog.get("as_of"))
    if checkout_authority is not None and checkout_authority != historical:
        raise ControlError("static checkout authority must match retained historical evidence")

    # Reuse the mature v3 structural/catalog checks without reviving its stale
    # authority conclusion.  Compatibility values exist only inside this call;
    # the original catalog and returned result remain non-authorizing.
    compatibility_catalog = copy.deepcopy(catalog)
    compatibility_catalog["truth"]["active_chargeable_checkout"] = True
    compatibility_checkout = dict(historical)
    compatibility_checkout["active"] = True
    _retained.validate_catalog(compatibility_catalog, compatibility_checkout)
    return catalog


def build_control() -> dict[str, Any]:
    """Build deterministic checked-in control with current checkout held false."""

    raw_catalog = read_object(CATALOG_PATH)
    checkout = build_checkout_authority(raw_catalog["as_of"])
    catalog = validate_catalog(raw_catalog, checkout)
    payment = payment_truth(read_object(PAYMENT_PATH))
    awards = settled_awards.summarize_ledger(
        settled_awards.read_ledger(SETTLED_AWARDS_PATH)
    )
    cash = settled_cash.summarize_ledger(
        settled_cash.read_ledger(SETTLED_CASH_PATH)
    )
    outreach = smart_outreach.build_plan(
        smart_outreach.read_object(OUTREACH_PATH), RECEIPTS_PATH
    )
    catalog_cash = catalog["truth"]["collected_cash_usd"]
    if cash["settled_usd"] != str(catalog_cash):
        raise ControlError("global cash truth differs from the settled-cash ledger")

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
            "id": "DIRECT_OFFER_PAYMENT_EVIDENCE",
            "owner": "FOUNDER_OR_CONNECTED_PROCESSOR_LANE",
            "condition": "A current Commons offer records its own chargeable buyer payment receipt.",
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
        AUTOPSY_PATH,
        AUTOPSY_PROVIDER_PATH,
        AUTOPSY_PUBLIC_PAGE_PATH,
        SETTLED_AWARDS_PATH,
        SETTLED_CASH_PATH,
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
        "as_of": _latest_as_of(catalog["as_of"], awards["as_of"], cash["as_of"]),
        "truth": {
            "collected_cash_usd": catalog_cash,
            "verified_positive_replies": catalog["truth"]["verified_positive_replies"],
            "accepted_scopes": catalog["truth"]["accepted_scopes"],
            "active_chargeable_checkout": False,
            "prospects_evaluated": outreach["truth"]["prospects_evaluated"],
            "ready_to_draft": counts["READY_TO_DRAFT"],
            "transport_actions": outreach["truth"]["transport_actions"],
            "settled_cash_receipts": cash["settled_receipts"],
            "settled_cash_usd": cash["settled_usd"],
            "cash_bank_availability_asserted": cash["bank_availability_asserted"],
            "cash_withdrawability_asserted": cash["withdrawability_asserted"],
            "paid_awards": awards["paid_awards"],
            "settled_amounts_by_currency": awards["totals_by_currency"],
            "usd_conversion_asserted": awards["usd_conversion_asserted"],
            "award_bank_availability_asserted": awards["bank_availability_asserted"],
            "award_withdrawability_asserted": awards["withdrawability_asserted"],
        },
        "payment": payment,
        "settled_cash": cash,
        "settled_awards": awards,
        "offers": offers,
        "execution_queue": queue,
        "blockers": blockers,
        "preserved_portfolio": catalog["portfolio"],
        "source_receipts": sources,
    }


def build_current_control() -> dict[str, Any]:
    """Build current control only after authenticated Stripe reacquisition."""

    current = right_now_stripe_authority.fetch_current_checkout_authority()
    if current.get("authority") != CURRENT_CHECKOUT_AUTHORITY:
        raise ControlError("current checkout authority provenance mismatch")
    if current.get("offer_id") != CHECKOUT_AUTHORITY["offer_id"]:
        raise ControlError("current checkout offer identity mismatch")
    if current.get("provider_account_id") != CHECKOUT_AUTHORITY["provider_account_id"]:
        raise ControlError("current checkout Stripe account mismatch")
    if current.get("provider_payment_link_id") != CHECKOUT_AUTHORITY["provider_payment_link_id"]:
        raise ControlError("current checkout Payment Link mismatch")
    if current.get("provider_product_id") != CHECKOUT_AUTHORITY["provider_product_id"]:
        raise ControlError("current checkout product mismatch")
    if current.get("provider_price_id") != CHECKOUT_AUTHORITY["provider_price_id"]:
        raise ControlError("current checkout price mismatch")
    if current.get("payment_url") != CHECKOUT_AUTHORITY["payment_url"]:
        raise ControlError("current checkout URL mismatch")
    if current.get("currency") != CHECKOUT_AUTHORITY["currency"]:
        raise ControlError("current checkout currency mismatch")
    if current.get("amount") != CHECKOUT_AUTHORITY["amount"]:
        raise ControlError("current checkout amount mismatch")
    if current.get("active") is not True:
        raise ControlError("current checkout is not active")

    control = copy.deepcopy(build_control())
    control["schema_version"] = CURRENT_CONTROL_SCHEMA_VERSION
    control["as_of"] = _latest_as_of(control["as_of"], current["observed_at_utc"])
    control["truth"]["active_chargeable_checkout"] = True
    control["current_checkout_authority"] = current
    return control


def validate_control(value: dict[str, Any]) -> None:
    expected = build_control()
    if value != expected:
        raise ControlError("committed control snapshot differs from compiled sources")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("compile", "validate", "current-checkout", "compile-current"),
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=ROOT / "revenue" / "right_now" / "control.json",
    )
    args = parser.parse_args()
    try:
        if args.command == "current-checkout":
            sys.stdout.write(canonical_text(right_now_stripe_authority.fetch_current_checkout_authority()))
            return 0
        if args.command == "compile-current":
            sys.stdout.write(canonical_text(build_current_control()))
            return 0

        control = build_control()
        if args.command == "compile":
            sys.stdout.write(canonical_text(control))
        else:
            validate_control(read_object(args.snapshot))
            totals = ", ".join(
                f"{row['amount']} {row['currency']}"
                for row in control["settled_awards"]["totals_by_currency"]
            )
            print(
                "VALID "
                f"{len(control['offers'])} offers "
                f"{len(control['execution_queue'])} opportunities "
                f"{control['truth']['transport_actions']} transports "
                f"USD {control['truth']['collected_cash_usd']} cash · "
                f"{control['truth']['settled_cash_receipts']} provider receipt · "
                f"{control['truth']['paid_awards']} paid award · {totals} settled · "
                "current checkout requires authenticated Stripe readback"
            )
    except (
        ControlError,
        right_now_stripe_authority.StripeAuthorityError,
        settled_awards.SettlementError,
        settled_cash.CashSettlementError,
        smart_outreach.OutreachError,
    ) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
