#!/usr/bin/env python3
"""Project public checkout rails from measured provider truth.

A Stripe URL becomes a public checkout anchor only when livemode,
charges_enabled, payouts_enabled, and that exact link active=true are
all proven. Duplicate or unverified URLs stay inert. This module never
calls Stripe, never stores bank data, and never claims cash.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any


ROOT_DEFAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join("revenue", "checkout_capability", "snapshot.json")
CATALOG = os.path.join("revenue", "outcome_commerce", "catalog.json")
STRIPE_URL_RE = re.compile(r"^https://(?:buy|donate)\.stripe\.com/[A-Za-z0-9_-]+$")
FORBIDDEN = (
    r"\brouting[_\s-]?number\b.+\d{9}\b",
    r"\baccount[_\s-]?number\b.+\d{8,17}\b",
    r"\bIBAN\b\s*[A-Z]{2}\d{2}[A-Z0-9]{10,}",
    r"\b(?:4\d{15}|5[1-5]\d{14})\b",
    r"\bcvv\b\s*\d{3,4}\b",
    r"\bssn\b\s*\d{3}-\d{2}-\d{4}\b",
)
CHECKOUT_FIRST = ("sku-tip-20260826", "sku-monthly-tip-20260826")
CANONICAL_SKUS = (
    "sku-tip-20260826",
    "sku-seat-20260826",
    "sku-unlock-20260826",
    "sku-monthly-tip-20260826",
    "sku-boost-20260826",
    "sku-whitebox-hour-20260826",
    "sku-muhlnickel-titan-20260826",
)


class CapabilityError(ValueError):
    pass


def _read(root: str, rel: str) -> str:
    path = os.path.join(root, rel)
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _load(root: str, rel: str) -> Any:
    return json.loads(_read(root, rel))


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not (
        value.endswith("Z") or re.search(r"[+-]\d\d:\d\d$", value)
    ):
        raise CapabilityError("%s must be an offset-aware ISO-8601 timestamp" % field)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise CapabilityError("%s must be a real timestamp" % field) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CapabilityError("%s must include an offset" % field)
    return parsed.astimezone(timezone.utc)


def forbidden_hits(text: str) -> list[str]:
    hits = []
    for pattern in FORBIDDEN:
        if re.search(pattern, text or "", flags=re.I):
            hits.append(pattern)
    return hits


def account_ready(provider: dict[str, Any]) -> bool:
    return (
        provider.get("name") == "stripe"
        and provider.get("livemode") is True
        and provider.get("charges_enabled") is True
        and provider.get("payouts_enabled") is True
        and list(provider.get("currently_due") or []) == []
        and provider.get("card_payments") == "active"
        and provider.get("transfers") == "active"
    )


def project_rail(provider: dict[str, Any], rail: dict[str, Any], inert: set[str]) -> dict[str, Any]:
    url = str(rail.get("url") or "")
    sku = str(rail.get("sku") or "")
    ready = (
        account_ready(provider)
        and rail.get("link_active") is True
        and rail.get("livemode") is True
        and bool(STRIPE_URL_RE.fullmatch(url))
        and url not in inert
        and sku in CANONICAL_SKUS
    )
    exposure = str(rail.get("exposure") or "")
    if ready and exposure == "CHECKOUT_FIRST" and sku in CHECKOUT_FIRST:
        public = "EXPOSE_CHECKOUT"
    elif ready and exposure == "INTAKE_FIRST":
        public = "EXPOSE_INTAKE_THEN_CHECKOUT"
    else:
        public = "INERT"
    return {
        "sku": sku,
        "url": url if ready else "",
        "stored_url": url,
        "link_active": bool(rail.get("link_active") is True),
        "public": public,
        "chargeable": ready,
        "payout_capable": bool(provider.get("payouts_enabled") is True),
    }


def project(snapshot: dict[str, Any]) -> dict[str, Any]:
    if snapshot.get("kind") != "CHECKOUT_CAPABILITY_SNAPSHOT":
        raise CapabilityError("snapshot kind is invalid")
    if snapshot.get("schema_version") != "commons-checkout-capability/v1":
        raise CapabilityError("snapshot schema_version is invalid")
    _timestamp(snapshot.get("observed_at"), "observed_at")
    provider = snapshot.get("provider") if isinstance(snapshot.get("provider"), dict) else {}
    money = snapshot.get("money") if isinstance(snapshot.get("money"), dict) else {}
    rails = snapshot.get("canonical_rails") if isinstance(snapshot.get("canonical_rails"), list) else []
    inert = set(snapshot.get("inert_duplicate_urls") or [])
    owner = snapshot.get("owner_action") if isinstance(snapshot.get("owner_action"), dict) else {}
    fallback = snapshot.get("fallback") if isinstance(snapshot.get("fallback"), dict) else {}
    projected = [project_rail(provider, rail, inert) for rail in rails if isinstance(rail, dict)]
    public = [row for row in projected if row["public"] != "INERT"]
    checkout_first = [row for row in public if row["public"] == "EXPOSE_CHECKOUT"]
    cash = money.get("collected_cash_usd")
    return {
        "account_ready": account_ready(provider),
        "charges_enabled": bool(provider.get("charges_enabled") is True),
        "payouts_enabled": bool(provider.get("payouts_enabled") is True),
        "collected_cash_usd": cash if isinstance(cash, int) else None,
        "public_rails": public,
        "checkout_first_skus": [row["sku"] for row in checkout_first],
        "inert_urls": sorted(inert),
        "owner_action_id": str(owner.get("id") or ""),
        "fallback_url": str(fallback.get("url") or ""),
        "fallback_kind": str(fallback.get("kind") or ""),
        "authorization": str(money.get("authorization") or ""),
        "bank_available": str(money.get("bank_available") or ""),
    }


def catalog_checkout_errors(catalog: dict[str, Any], snapshot: dict[str, Any], projected: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    evidence = snapshot.get("evidence") if isinstance(snapshot.get("evidence"), dict) else {}
    expected = {row["sku"]: row for row in projected["public_rails"]}
    by_id = {}
    for listing in catalog.get("listings") or []:
        if isinstance(listing, dict) and listing.get("id"):
            by_id[listing["id"]] = listing
    for sku in CANONICAL_SKUS:
        listing = by_id.get(sku)
        if not listing:
            errors.append("catalog missing listing %s" % sku)
            continue
        checkout = listing.get("checkout") if isinstance(listing.get("checkout"), dict) else {}
        funnel = (catalog.get("funnels") or {}).get(sku) if isinstance(catalog.get("funnels"), dict) else {}
        row = expected.get(sku)
        if not row:
            errors.append("projection missing %s" % sku)
            continue
        if checkout.get("status") != "ACTIVE_CHARGEABLE":
            errors.append("%s checkout status must be ACTIVE_CHARGEABLE" % sku)
        if checkout.get("provider") != "stripe":
            errors.append("%s provider must be stripe" % sku)
        if checkout.get("url") != row["stored_url"]:
            errors.append("%s checkout url must match the canonical recorded URL" % sku)
        if checkout.get("link_active") is not True:
            errors.append("%s link_active must be true" % sku)
        if checkout.get("account_charges_enabled") is not True:
            errors.append("%s account_charges_enabled must be true" % sku)
        if checkout.get("account_payouts_enabled") is not True:
            errors.append("%s account_payouts_enabled must be true" % sku)
        cap = checkout.get("capability_evidence") if isinstance(checkout.get("capability_evidence"), dict) else {}
        if cap.get("reference") != evidence.get("reference"):
            errors.append("%s capability_evidence.reference must match the snapshot" % sku)
        if cap.get("observed_at") != snapshot.get("observed_at"):
            errors.append("%s capability_evidence.observed_at must match the snapshot" % sku)
        if not isinstance(funnel, dict):
            errors.append("%s funnel missing" % sku)
            continue
        if funnel.get("conversion", {}).get("mode") != "ACTIVE_STRIPE_LINK":
            errors.append("%s conversion.mode must be ACTIVE_STRIPE_LINK" % sku)
        if funnel.get("conversion", {}).get("status") != "ACTIVE_CHARGEABLE":
            errors.append("%s conversion.status must be ACTIVE_CHARGEABLE" % sku)
        if sku in CHECKOUT_FIRST:
            if funnel.get("readiness") != "READY_FOR_CHECKOUT":
                errors.append("%s must be READY_FOR_CHECKOUT" % sku)
            if funnel.get("measurement", {}).get("dom_action") != "checkout-open":
                errors.append("%s measurement.dom_action must be checkout-open" % sku)
        else:
            if funnel.get("readiness") != "READY_FOR_QUALIFICATION":
                errors.append("%s must be READY_FOR_QUALIFICATION" % sku)
            if funnel.get("measurement", {}).get("dom_action") != "qualification-open":
                errors.append("%s measurement.dom_action must be qualification-open" % sku)
    return errors


def html_surface_errors(root: str) -> list[str]:
    errors: list[str] = []
    stripe_url = re.compile(r"https://(?:buy|donate)\.stripe\.com/")
    for name in ("pay.html", "tips.html", "commerce.html"):
        text = _read(root, name)
        if stripe_url.search(text):
            errors.append("%s must keep Stripe URLs out of static HTML" % name)
        if "js-checkout-slot" not in text:
            errors.append("%s must include js-checkout-slot for catalog-driven rails" % name)
        if "mailto:tokenjunkielabs@gmail.com" not in text:
            errors.append("%s must keep the provider-neutral contact fallback" % name)
    return errors


def measure_root(root: str) -> dict[str, Any]:
    snapshot = _load(root, SNAPSHOT)
    catalog = _load(root, CATALOG)
    blob = "\n".join(
        [
            _read(root, SNAPSHOT),
            _read(root, os.path.join("ground", "CHECKOUT_CAPABILITY.md")),
            _read(root, os.path.join("host", "checkout_capability.py")),
        ]
    )
    projected = project(snapshot)
    errors = []
    hits = forbidden_hits(blob)
    if hits:
        errors.append("forbidden financial field pattern")
    if projected["collected_cash_usd"] != 0:
        errors.append("collected cash must stay 0 without BANK_AVAILABLE evidence")
    if projected["authorization"] != "NOT_LANDED" or projected["bank_available"] != "NOT_LANDED":
        errors.append("authorization/settlement/payout/bank must stay NOT_LANDED")
    if projected["owner_action_id"] != "NONE":
        errors.append("blocking owner action must stay NONE while currently_due is empty")
    if projected["fallback_kind"] != "PROVIDER_NEUTRAL_INTAKE":
        errors.append("fallback must be provider-neutral intake")
    if projected["fallback_url"] != "mailto:tokenjunkielabs@gmail.com":
        errors.append("fallback contact must stay the public email")
    if set(projected["checkout_first_skus"]) != set(CHECKOUT_FIRST):
        errors.append("checkout-first SKUs must be tip and monthly-tip")
    errors.extend(catalog_checkout_errors(catalog, snapshot, projected))
    errors.extend(html_surface_errors(root))
    for sku in CANONICAL_SKUS:
        path = os.path.join("land", "%s.md" % sku)
        text = _read(root, path)
        if "status: ACTIVE_CHARGEABLE" not in text:
            errors.append("%s must record ACTIVE_CHARGEABLE" % path)
        if "account_payouts_enabled: true" not in text:
            errors.append("%s must record payouts_enabled" % path)
        if "link_active: true" not in text:
            errors.append("%s must record link_active true" % path)
        if "Recorded URL (not a checkout):" in text:
            errors.append("%s must not still call a verified URL a non-checkout" % path)
    state = "INTEGRATED" if not errors else "NOT_LANDED"
    return {
        "state": state,
        "errors": errors,
        "projected": projected,
        "snapshot": SNAPSHOT,
        "z": "" if not errors else "FINDER-FAILED",
    }


def _self_test() -> bool:
    dead = {
        "schema_version": "commons-checkout-capability/v1",
        "kind": "CHECKOUT_CAPABILITY_SNAPSHOT",
        "observed_at": "2026-08-28T16:10:00Z",
        "provider": {
            "name": "stripe",
            "livemode": True,
            "charges_enabled": False,
            "payouts_enabled": False,
            "currently_due": ["external_account"],
            "card_payments": "inactive",
            "transfers": "inactive",
        },
        "canonical_rails": [
            {
                "sku": "sku-tip-20260826",
                "url": "https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08",
                "link_active": True,
                "livemode": True,
                "exposure": "CHECKOUT_FIRST",
            }
        ],
        "inert_duplicate_urls": [],
    }
    projected = project(dead)
    if projected["account_ready"] or projected["public_rails"]:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project public checkout rails")
    parser.add_argument("--root", default=ROOT_DEFAULT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return 0 if _self_test() else 1
    row = measure_root(args.root)
    json.dump(row, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if row.get("state") == "INTEGRATED" else 1


if __name__ == "__main__":
    sys.exit(main())
