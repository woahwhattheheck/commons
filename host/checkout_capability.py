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


def catalog_checkouts(catalog: dict[str, Any]) -> dict[str, str]:
    """Return only catalog entries that carry a fully proven Stripe checkout."""
    out: dict[str, str] = {}
    for listing in catalog.get("listings") or []:
        if not isinstance(listing, dict) or not isinstance(listing.get("id"), str):
            continue
        checkout = listing.get("checkout") if isinstance(listing.get("checkout"), dict) else {}
        url = checkout.get("url")
        if (
            checkout.get("status") == "ACTIVE_CHARGEABLE"
            and checkout.get("provider") == "stripe"
            and checkout.get("link_active") is True
            and checkout.get("account_charges_enabled") is True
            and checkout.get("account_payouts_enabled") is True
            and isinstance(url, str)
            and STRIPE_URL_RE.fullmatch(url)
        ):
            out[listing["id"]] = url
    return out


def project_rail(
    provider: dict[str, Any],
    rail: dict[str, Any],
    inert: set[str],
    checkouts: dict[str, str],
    default_evidence: dict[str, Any],
) -> dict[str, Any]:
    url = str(rail.get("url") or "")
    sku = str(rail.get("sku") or "")
    evidence = rail.get("evidence") if isinstance(rail.get("evidence"), dict) else default_evidence
    evidence_ready = bool(evidence.get("reference") and evidence.get("observed_at"))
    if evidence_ready:
        try:
            _timestamp(evidence["observed_at"], "%s.evidence.observed_at" % sku)
        except CapabilityError:
            evidence_ready = False
    ready = (
        account_ready(provider)
        and rail.get("link_active") is True
        and rail.get("livemode") is True
        and bool(STRIPE_URL_RE.fullmatch(url))
        and url not in inert
        and checkouts.get(sku) == url
        and evidence_ready
    )
    exposure = str(rail.get("exposure") or "")
    if ready and exposure == "CHECKOUT_FIRST":
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
        "evidence_reference": str(evidence.get("reference") or ""),
        "evidence_observed_at": str(evidence.get("observed_at") or ""),
    }


def project(snapshot: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
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
    snapshot_evidence = snapshot.get("evidence") if isinstance(snapshot.get("evidence"), dict) else {}
    default_evidence = {
        "reference": snapshot_evidence.get("reference"),
        "observed_at": snapshot.get("observed_at"),
    }
    checkouts = catalog_checkouts(catalog)
    projected = [
        project_rail(provider, rail, inert, checkouts, default_evidence)
        for rail in rails
        if isinstance(rail, dict)
    ]
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
    expected = {row["sku"]: row for row in projected["public_rails"]}
    by_id = {}
    for listing in catalog.get("listings") or []:
        if isinstance(listing, dict) and listing.get("id"):
            by_id[listing["id"]] = listing
    active = catalog_checkouts(catalog)
    for sku in active:
        listing = by_id[sku]
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
        if cap.get("reference") != row.get("evidence_reference"):
            errors.append("%s capability_evidence.reference must match its rail evidence" % sku)
        if cap.get("observed_at") != row.get("evidence_observed_at"):
            errors.append("%s capability_evidence.observed_at must match its rail evidence" % sku)
        if not isinstance(funnel, dict):
            errors.append("%s funnel missing" % sku)
            continue
        if funnel.get("conversion", {}).get("mode") != "ACTIVE_STRIPE_LINK":
            errors.append("%s conversion.mode must be ACTIVE_STRIPE_LINK" % sku)
        if funnel.get("conversion", {}).get("status") != "ACTIVE_CHARGEABLE":
            errors.append("%s conversion.status must be ACTIVE_CHARGEABLE" % sku)
        if row.get("public") == "EXPOSE_CHECKOUT":
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
    projected = project(snapshot, catalog)
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
    expected_checkout_first = {
        sku
        for sku in catalog_checkouts(catalog)
        if (catalog.get("funnels") or {}).get(sku, {}).get("readiness") == "READY_FOR_CHECKOUT"
    }
    if set(projected["checkout_first_skus"]) != expected_checkout_first:
        errors.append("checkout-first SKUs must match READY_FOR_CHECKOUT catalog entries")
    errors.extend(catalog_checkout_errors(catalog, snapshot, projected))
    errors.extend(html_surface_errors(root))
    for listing in catalog.get("listings") or []:
        sku = listing.get("id")
        if sku not in catalog_checkouts(catalog):
            continue
        source = listing.get("source_artifact") if isinstance(listing.get("source_artifact"), dict) else {}
        path = str(source.get("path") or "")
        if not (path.startswith("land/") and path.endswith(".md")):
            continue
        path = path.replace("/", os.sep)
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
    catalog = {
        "listings": [
            {
                "id": "sku-tip-20260826",
                "checkout": {
                    "status": "ACTIVE_CHARGEABLE",
                    "provider": "stripe",
                    "url": "https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08",
                    "link_active": True,
                    "account_charges_enabled": True,
                    "account_payouts_enabled": True,
                },
            }
        ]
    }
    projected = project(dead, catalog)
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
