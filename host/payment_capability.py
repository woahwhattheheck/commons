#!/usr/bin/env python3
"""Provider-neutral payment-capability registry and storefront failover.

Reuses checkout_capability, catalog SKUs, payment_ready money states,
reply-to-revenue cash truth, and scope-to-delivery money separation.
Never calls a provider, never stores bank/routing/tax/credentials, and
never claims cash.
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
REGISTRY = os.path.join("revenue", "payment_capability", "registry.json")
SNAPSHOT = os.path.join("revenue", "checkout_capability", "snapshot.json")
CATALOG = os.path.join("revenue", "outcome_commerce", "catalog.json")
FUNNEL = os.path.join("revenue", "reply_to_revenue", "funnel.json")
BINDINGS = os.path.join("revenue", "scope_to_delivery", "catalog_bindings.json")
PACK = os.path.join("revenue", "payment_ready", "pack.json")
STRIPE_URL_RE = re.compile(r"^https://(?:buy|donate)\.stripe\.com/[A-Za-z0-9_-]+$")
OWNER_ACTION_HOSTS = {
    "dashboard.stripe.com",
    "www.paypal.com",
    "paypal.com",
    "github.com",
    "squareup.com",
    "www.squareup.com",
}
FORBIDDEN = (
    r"\brouting[_\s-]?number\b.+\d{9}\b",
    r"\baccount[_\s-]?number\b.+\d{8,17}\b",
    r"\bIBAN\b\s*[A-Z]{2}\d{2}[A-Z0-9]{10,}",
    r"\b(?:4\d{15}|5[1-5]\d{14})\b",
    r"\bcvv\b\s*\d{3,4}\b",
    r"\bssn\b\s*\d{3}-\d{2}-\d{4}\b",
)
CANONICAL_SKUS = (
    "sku-tip-20260826",
    "sku-seat-20260826",
    "sku-unlock-20260826",
    "sku-monthly-tip-20260826",
    "sku-boost-20260826",
    "sku-whitebox-hour-20260826",
    "sku-muhlnickel-titan-20260826",
)
PUBLIC_HTML = (
    "pay.html",
    "tips.html",
    "commerce.html",
    "payment-capability.html",
    "reply-to-revenue.html",
)
REQUIRED_RAIL_FIELDS = (
    "id",
    "provider",
    "account_provenance",
    "capability_state",
    "required_owner_actions",
    "evidence",
    "supported_skus",
    "currencies",
    "settlement_destination",
    "public_presentation",
)


class RegistryError(ValueError):
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
        raise RegistryError("%s must be an offset-aware ISO-8601 timestamp" % field)
    try:
        parsed = datetime.fromisoformat(
            value[:-1] + "+00:00" if value.endswith("Z") else value
        )
    except ValueError as exc:
        raise RegistryError("%s must be a real timestamp" % field) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RegistryError("%s must include an offset" % field)
    return parsed.astimezone(timezone.utc)


def forbidden_hits(text: str) -> list[str]:
    hits = []
    for pattern in FORBIDDEN:
        if re.search(pattern, text or "", flags=re.I):
            hits.append(pattern)
    return hits


def owner_action_url_ok(url: str) -> bool:
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return False
    return parsed.hostname in OWNER_ACTION_HOSTS


def public_storefront_eligible(rail: dict[str, Any]) -> bool:
    if rail.get("capability_state") != "CHARGEABLE":
        return False
    if rail.get("public_presentation") != "EXPOSE":
        return False
    if rail.get("charges_enabled") is not True:
        return False
    if rail.get("payouts_enabled") is not True:
        return False
    evidence = rail.get("evidence") if isinstance(rail.get("evidence"), dict) else {}
    if not evidence.get("reference") or not evidence.get("observed_at"):
        return False
    _timestamp(evidence.get("observed_at"), "evidence.observed_at")
    return True


def owner_usable(rail: dict[str, Any]) -> bool:
    return rail.get("capability_state") in {
        "CHARGEABLE",
        "CHARGEABLE_ACCOUNT_OWNER_DASHBOARD",
    } and rail.get("charges_enabled") is True


def project_rail(rail: dict[str, Any]) -> dict[str, Any]:
    eligible = public_storefront_eligible(rail)
    links = rail.get("canonical_links") if isinstance(rail.get("canonical_links"), list) else []
    public_links = []
    if eligible and rail.get("provider") == "stripe":
        for link in links:
            if not isinstance(link, dict):
                continue
            url = str(link.get("url") or "")
            sku = str(link.get("sku") or "")
            if (
                link.get("link_active") is True
                and link.get("livemode") is True
                and sku in CANONICAL_SKUS
                and STRIPE_URL_RE.fullmatch(url)
            ):
                public_links.append({"sku": sku, "url": url, "exposure": link.get("exposure")})
    actions = []
    for action in rail.get("required_owner_actions") or []:
        if isinstance(action, dict) and action.get("kind") == "EXTERNAL_OWNER_ACTION":
            actions.append(
                {
                    "id": action.get("id"),
                    "label": action.get("label"),
                    "url": action.get("url") if owner_action_url_ok(str(action.get("url") or "")) else "",
                    "blocking": bool(action.get("blocking")),
                }
            )
    dest = rail.get("settlement_destination") if isinstance(rail.get("settlement_destination"), dict) else {}
    return {
        "id": str(rail.get("id") or ""),
        "provider": str(rail.get("provider") or ""),
        "capability_state": str(rail.get("capability_state") or ""),
        "public_presentation": "EXPOSE" if eligible and public_links else "INERT",
        "chargeable": eligible,
        "owner_usable": owner_usable(rail),
        "public_links": public_links if eligible else [],
        "supported_skus": list(rail.get("supported_skus") or []),
        "currencies": list(rail.get("currencies") or []),
        "settlement_status": str(dest.get("status") or "NONE"),
        "settlement_kind": str(dest.get("kind") or "unmeasured"),
        "owner_actions": actions,
        "evidence_reference": str((rail.get("evidence") or {}).get("reference") or ""),
        "evidence_observed_at": str((rail.get("evidence") or {}).get("observed_at") or ""),
    }


def project(registry: dict[str, Any]) -> dict[str, Any]:
    if registry.get("kind") != "PAYMENT_CAPABILITY_REGISTRY":
        raise RegistryError("registry kind is invalid")
    if registry.get("schema_version") != "commons-payment-capability/v1":
        raise RegistryError("registry schema_version is invalid")
    _timestamp(registry.get("observed_at"), "observed_at")
    rails = registry.get("rails") if isinstance(registry.get("rails"), list) else []
    projected = [project_rail(rail) for rail in rails if isinstance(rail, dict)]
    public = [row for row in projected if row["public_presentation"] == "EXPOSE"]
    usable = [row for row in projected if row["owner_usable"]]
    active = public[0]["id"] if public else ""
    cash = registry.get("cash") if isinstance(registry.get("cash"), dict) else {}
    intake = registry.get("intake_fallback") if isinstance(registry.get("intake_fallback"), dict) else {}
    blocking = []
    for row in projected:
        for action in row["owner_actions"]:
            if action.get("blocking") and action.get("url"):
                blocking.append(action)
    return {
        "active_storefront_rail_id": active,
        "public_rails": public,
        "owner_usable_rails": [row["id"] for row in usable],
        "inert_rails": [row["id"] for row in projected if row["public_presentation"] == "INERT"],
        "has_lawfully_chargeable_path": bool(usable),
        "has_public_storefront": bool(public),
        "failover_owner_actions": blocking,
        "collected_cash_usd": cash.get("collected_usd"),
        "authorization": str(cash.get("authorization") or ""),
        "bank_available": str(cash.get("bank_available") or ""),
        "intake_url": str(intake.get("url") or ""),
        "rails": projected,
    }


def compose_errors(root: str, registry: dict[str, Any], projected: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    snapshot = _load(root, SNAPSHOT)
    catalog = _load(root, CATALOG)
    funnel = _load(root, FUNNEL)
    bindings = _load(root, BINDINGS)
    pack = _load(root, PACK)
    provider = snapshot.get("provider") if isinstance(snapshot.get("provider"), dict) else {}
    money = snapshot.get("money") if isinstance(snapshot.get("money"), dict) else {}
    stripe = next((r for r in registry.get("rails") or [] if r.get("id") == "stripe-livemode-acct_1U6HI9ATH4EDE7XD"), {})
    if provider.get("charges_enabled") is True and stripe.get("charges_enabled") is not True:
        errors.append("registry Stripe charges_enabled must match checkout snapshot")
    if provider.get("payouts_enabled") is True and stripe.get("payouts_enabled") is not True:
        errors.append("registry Stripe payouts_enabled must match checkout snapshot")
    if money.get("collected_cash_usd") != 0 or projected["collected_cash_usd"] != 0:
        errors.append("collected cash must stay 0")
    pack_text = json.dumps(pack)
    if "BANK_AVAILABLE" not in pack_text and "NOT_LANDED" not in pack_text:
        errors.append("payment_ready pack must keep cash states")
    cash_fields = json.dumps(funnel)
    if '"cash_usd": 0' not in cash_fields and '"collected_cash_usd"' not in json.dumps(catalog.get("funnel_truth") or {}):
        errors.append("reply-to-revenue/catalog cash truth missing")
    if catalog.get("funnel_truth", {}).get("collected_cash_usd") not in ("0.00", 0, "0"):
        errors.append("catalog funnel cash must stay 0.00")
    if not isinstance(bindings.get("skus"), dict) or "sku-tip-20260826" not in (bindings.get("skus") or {}):
        errors.append("scope-to-delivery bindings must still name canonical SKUs")
    stripe_links = {link["sku"]: link["url"] for link in stripe.get("canonical_links") or []}
    by_id = {row.get("id"): row for row in catalog.get("listings") or [] if isinstance(row, dict)}
    for sku in CANONICAL_SKUS:
        listing = by_id.get(sku) or {}
        checkout = listing.get("checkout") if isinstance(listing.get("checkout"), dict) else {}
        if checkout.get("url") != stripe_links.get(sku):
            errors.append("%s catalog checkout URL must match registry canonical link" % sku)
    return errors


def html_surface_errors(root: str) -> list[str]:
    errors: list[str] = []
    stripe_url = re.compile(r"https://(?:buy|donate)\.stripe\.com/")
    paypal_me = re.compile(r"paypal\.me/", re.I)
    for name in PUBLIC_HTML:
        text = _read(root, name)
        if stripe_url.search(text):
            errors.append("%s must keep Stripe URLs out of static HTML" % name)
        if paypal_me.search(text):
            errors.append("%s must not invent a PayPal.me" % name)
        if "mailto:tokenjunkielabs@gmail.com" not in text and name in (
            "pay.html",
            "tips.html",
            "commerce.html",
            "payment-capability.html",
        ):
            errors.append("%s must keep the provider-neutral contact fallback" % name)
    text = _read(root, "payment-capability.html")
    if "js-rail-list" not in text:
        errors.append("payment-capability.html must include js-rail-list")
    if "js-owner-actions" not in text:
        errors.append("payment-capability.html must include js-owner-actions")
    if "payment-capability.js" not in text:
        errors.append("payment-capability.html must load payment-capability.js")
    js = _read(root, "payment-capability.js")
    if "capability_state" not in js:
        errors.append("payment-capability.js must branch on capability_state")
    if "EXTERNAL_OWNER_ACTION" not in js:
        errors.append("payment-capability.js must render owner one-click actions")
    pay_js = _read(root, "pay.js")
    if "payment_capability/registry.json" not in pay_js:
        errors.append("pay.js must load the provider-neutral registry for failover")
    return errors


def measure_root(root: str) -> dict[str, Any]:
    registry = _load(root, REGISTRY)
    blob = "\n".join(
        [
            _read(root, REGISTRY),
            _read(root, os.path.join("ground", "PAYMENT_CAPABILITY.md")),
            _read(root, os.path.join("host", "payment_capability.py")),
            _read(root, "payment-capability.html"),
            _read(root, "payment-capability.js"),
        ]
    )
    errors: list[str] = []
    hits = forbidden_hits(blob)
    if hits:
        errors.append("forbidden financial field pattern")
    rails = registry.get("rails") if isinstance(registry.get("rails"), list) else []
    if len(rails) < 3:
        errors.append("registry must name Stripe plus at least two failover rails")
    seen = set()
    for rail in rails:
        if not isinstance(rail, dict):
            errors.append("rail must be an object")
            continue
        for field in REQUIRED_RAIL_FIELDS:
            if field not in rail:
                errors.append("rail %s missing %s" % (rail.get("id"), field))
        rid = rail.get("id")
        if rid in seen:
            errors.append("duplicate rail id %s" % rid)
        seen.add(rid)
        evidence = rail.get("evidence") if isinstance(rail.get("evidence"), dict) else {}
        if not evidence.get("reference") or not evidence.get("observed_at"):
            errors.append("rail %s missing evidence timestamp/reference" % rid)
        dest = rail.get("settlement_destination") if isinstance(rail.get("settlement_destination"), dict) else {}
        if "status" not in dest or "kind" not in dest:
            errors.append("rail %s missing settlement destination evidence" % rid)
        for action in rail.get("required_owner_actions") or []:
            if not isinstance(action, dict):
                continue
            url = str(action.get("url") or "")
            if action.get("kind") == "EXTERNAL_OWNER_ACTION" and not owner_action_url_ok(url):
                errors.append("rail %s owner action URL is not an official provider UI" % rid)
        if rail.get("public_presentation") == "EXPOSE" and rail.get("capability_state") != "CHARGEABLE":
            errors.append("rail %s cannot EXPOSE unless CHARGEABLE" % rid)
        if rail.get("capability_state") != "CHARGEABLE" and rail.get("canonical_links"):
            # inert rails may omit links; if present they still must not be public
            pass
        if rail.get("id") != "stripe-livemode-acct_1U6HI9ATH4EDE7XD" and rail.get("public_presentation") == "EXPOSE":
            errors.append("non-Stripe rail must stay inert until a later evidence pass")
    projected = project(registry)
    if projected["collected_cash_usd"] != 0:
        errors.append("collected cash must stay 0 without BANK_AVAILABLE evidence")
    if projected["authorization"] != "NOT_LANDED" or projected["bank_available"] != "NOT_LANDED":
        errors.append("authorization/settlement/payout/bank must stay NOT_LANDED")
    if projected["intake_url"] != "mailto:tokenjunkielabs@gmail.com":
        errors.append("intake fallback must stay the public email")
    if not projected["has_lawfully_chargeable_path"]:
        errors.append("fresh Stripe evidence must keep at least one owner-usable chargeable path")
    if projected["active_storefront_rail_id"] != "stripe-livemode-acct_1U6HI9ATH4EDE7XD":
        errors.append("active public storefront must be the proven Stripe rail")
    if "paypal-wallet-unmeasured" not in projected["inert_rails"]:
        errors.append("PayPal must stay inert without owner KYC evidence")
    if not projected["failover_owner_actions"]:
        errors.append("inert rails must keep one-click owner actions")
    errors.extend(compose_errors(root, registry, projected))
    errors.extend(html_surface_errors(root))
    for rel in (
        os.path.join("ground", "PAYMENT_CAPABILITY.md"),
        os.path.join("ground", "CHECKOUT_CAPABILITY.md"),
        os.path.join("ground", "PAY.md"),
        os.path.join("ground", "STRIPE.md"),
    ):
        text = _read(root, rel)
        if "PAYMENT_CAPABILITY" not in text and rel.endswith("PAYMENT_CAPABILITY.md"):
            errors.append("%s missing title" % rel)
        if rel != os.path.join("ground", "PAYMENT_CAPABILITY.md") and "payment_capability" not in text and "PAYMENT_CAPABILITY" not in text:
            errors.append("%s must cite the payment-capability registry" % rel)
    state = "INTEGRATED" if not errors else "NOT_LANDED"
    return {
        "state": state,
        "errors": errors,
        "projected": projected,
        "registry": REGISTRY,
        "z": "" if not errors else "FINDER-FAILED",
    }


def _self_test() -> bool:
    dead = {
        "schema_version": "commons-payment-capability/v1",
        "kind": "PAYMENT_CAPABILITY_REGISTRY",
        "observed_at": "2026-08-28T16:43:00Z",
        "cash": {
            "collected_usd": 0,
            "authorization": "NOT_LANDED",
            "bank_available": "NOT_LANDED",
        },
        "intake_fallback": {
            "kind": "PROVIDER_NEUTRAL_INTAKE",
            "url": "mailto:tokenjunkielabs@gmail.com",
        },
        "rails": [
            {
                "id": "stripe-dead",
                "provider": "stripe",
                "capability_state": "INERT_CHARGES_DISABLED",
                "charges_enabled": False,
                "payouts_enabled": False,
                "public_presentation": "INERT",
                "canonical_links": [
                    {
                        "sku": "sku-tip-20260826",
                        "url": "https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08",
                        "link_active": True,
                        "livemode": True,
                    }
                ],
                "evidence": {
                    "reference": "fixture",
                    "observed_at": "2026-08-28T16:43:00Z",
                },
                "required_owner_actions": [],
                "supported_skus": [],
                "currencies": ["usd"],
                "settlement_destination": {"kind": "unmeasured", "status": "NONE"},
            },
            {
                "id": "paypal-dead",
                "provider": "paypal",
                "capability_state": "INERT_NEEDS_OWNER_KYC",
                "charges_enabled": False,
                "public_presentation": "INERT",
                "evidence": {
                    "reference": "fixture",
                    "observed_at": "2026-08-28T16:43:00Z",
                },
                "required_owner_actions": [
                    {
                        "id": "paypal-business-signup",
                        "blocking": True,
                        "kind": "EXTERNAL_OWNER_ACTION",
                        "label": "Open PayPal",
                        "url": "https://www.paypal.com/bizsignup",
                    }
                ],
                "supported_skus": [],
                "currencies": ["usd"],
                "settlement_destination": {"kind": "unmeasured", "status": "NONE"},
            },
        ],
    }
    projected = project(dead)
    if projected["has_public_storefront"] or projected["public_rails"]:
        return False
    if projected["has_lawfully_chargeable_path"]:
        return False
    if not projected["failover_owner_actions"]:
        return False
    live = {
        "schema_version": "commons-payment-capability/v1",
        "kind": "PAYMENT_CAPABILITY_REGISTRY",
        "observed_at": "2026-08-28T16:43:00Z",
        "cash": {"collected_usd": 0, "authorization": "NOT_LANDED", "bank_available": "NOT_LANDED"},
        "intake_fallback": {"url": "mailto:tokenjunkielabs@gmail.com"},
        "rails": [
            dead["rails"][0],
            {
                "id": "paypal-live-fixture",
                "provider": "paypal",
                "capability_state": "CHARGEABLE",
                "charges_enabled": True,
                "payouts_enabled": True,
                "public_presentation": "EXPOSE",
                "canonical_links": [],
                "evidence": {
                    "reference": "fixture-paypal",
                    "observed_at": "2026-08-28T16:43:00Z",
                },
                "required_owner_actions": [],
                "supported_skus": ["sku-tip-20260826"],
                "currencies": ["usd"],
                "settlement_destination": {"kind": "paypal_balance", "status": "verified"},
            },
        ],
    }
    # PayPal fixture is CHARGEABLE but has no public checkout URL of a known kind,
    # so public_presentation stays INERT. That is honest: chargeable is not a URL.
    alt = project(live)
    if alt["has_public_storefront"]:
        return False
    if "paypal-live-fixture" not in alt["owner_usable_rails"]:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project payment-capability registry")
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
