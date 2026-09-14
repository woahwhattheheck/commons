#!/usr/bin/env python3
"""Canonical right-now revenue compiler with current Stripe checkout authority.

The frozen core preserves the historical compiler and replay contracts from the
#14135 merge.  This wrapper adds one production-only authority boundary: a
retained authenticated Stripe readback must still be fresh under process UTC
before historical checkout evidence can authorize "current" checkout truth.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from host import right_now_revenue_core as _core


# Preserve the established public module surface.  Existing callers/tests that
# import helpers from host/right_now_revenue.py continue to receive the frozen
# historical implementations unless explicitly overridden below.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


CHECKOUT_CURRENT_PATH = ROOT / "revenue" / "right_now" / "stripe_checkout_current.json"
CHECKOUT_CURRENT_SHA256 = "3ccefcbe58f9856a486475ce2321a2df3eac443207c4ac4f3badfbfc8b64dbf8"
CHECKOUT_CURRENT_MAX_AGE = timedelta(hours=24)

_HISTORICAL_VALIDATE_CHECKOUT_AUTHORITY = _core.validate_checkout_authority
_HISTORICAL_VALIDATE_CATALOG = _core.validate_catalog
_ORIGINAL_BUILD_CONTROL = _core.build_control


def _current_utc() -> datetime:
    """Return the production freshness clock.

    Deliberately accepts no caller-selected timestamp. Tests may monkeypatch the
    function object, but production CLI/library callers cannot backdate current
    authority through a function argument, catalog field, or environment value.
    """

    return datetime.now(timezone.utc)


def _exact_keys(value: Any, expected: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ControlError(f"{where} fields differ from the current checkout contract")
    return value


def validate_current_checkout_readback(
    value: dict[str, Any],
    *,
    current_moment: datetime,
) -> dict[str, Any]:
    """Validate one minimized authenticated Stripe readback against process time."""

    _exact_keys(
        value,
        {
            "schema_version",
            "account_id",
            "livemode",
            "observed_at_utc",
            "payment_link",
            "line_item",
            "source",
        },
        "checkout current readback",
    )
    if value["schema_version"] != "commons-stripe-checkout-readback/v1":
        raise ControlError("checkout current readback schema drift")
    if value["account_id"] != CHECKOUT_AUTHORITY["provider_account_id"]:
        raise ControlError("checkout current readback account drift")
    if value["livemode"] is not True:
        raise ControlError("checkout current readback must be livemode")

    source = _exact_keys(
        value["source"],
        {
            "authenticated_read",
            "collector",
            "payment_link_operation",
            "line_items_operation",
        },
        "checkout current source",
    )
    if source["authenticated_read"] is not True:
        raise ControlError("checkout current readback lacks authenticated provider authority")
    if source["collector"] != "STRIPE_API_READ":
        raise ControlError("checkout current readback collector drift")
    if source["payment_link_operation"] != "GET /v1/payment_links/{id}":
        raise ControlError("checkout current payment-link operation drift")
    if source["line_items_operation"] != "GET /v1/payment_links/{id}/line_items":
        raise ControlError("checkout current line-items operation drift")

    payment_link = _exact_keys(
        value["payment_link"],
        {"id", "active", "livemode", "currency", "url", "offer_id", "contract_version"},
        "checkout current payment_link",
    )
    expected_link = {
        "id": CHECKOUT_AUTHORITY["provider_payment_link_id"],
        "active": True,
        "livemode": True,
        "currency": "usd",
        "url": CHECKOUT_AUTHORITY["payment_url"],
        "offer_id": CHECKOUT_AUTHORITY["offer_id"],
        "contract_version": "commons-agent-failure-autopsy-offer/v1",
    }
    for field, expected in expected_link.items():
        if payment_link[field] != expected:
            raise ControlError(f"checkout current payment_link {field} drift")

    line_item = _exact_keys(
        value["line_item"],
        {
            "price_id",
            "price_active",
            "livemode",
            "product_id",
            "currency",
            "unit_amount",
            "quantity",
            "lookup_key",
        },
        "checkout current line_item",
    )
    expected_line_item = {
        "price_id": CHECKOUT_AUTHORITY["provider_price_id"],
        "price_active": True,
        "livemode": True,
        "product_id": CHECKOUT_AUTHORITY["provider_product_id"],
        "currency": "usd",
        "unit_amount": CHECKOUT_AUTHORITY["amount"] * 100,
        "quantity": 1,
        "lookup_key": "commons_agent_failure_autopsy_usd29_v1",
    }
    for field, expected in expected_line_item.items():
        actual = line_item[field]
        if field in {"unit_amount", "quantity"}:
            if type(actual) is not int or actual != expected:
                raise ControlError(f"checkout current line_item {field} drift")
        elif actual != expected:
            raise ControlError(f"checkout current line_item {field} drift")

    observed_text = value["observed_at_utc"]
    observed = _provider_utc(observed_text, "checkout current observed_at_utc")
    if observed.strftime("%Y-%m-%dT%H:%M:%SZ") != observed_text:
        raise ControlError("checkout current observed_at_utc must be canonical UTC seconds")
    if not isinstance(current_moment, datetime):
        raise ControlError("checkout current process time must be a datetime")
    if current_moment.tzinfo is None or current_moment.utcoffset() != timezone.utc.utcoffset(current_moment):
        raise ControlError("checkout current process time must be UTC")
    current_moment = current_moment.astimezone(timezone.utc)
    if observed > current_moment:
        raise ControlError("checkout current provider evidence is from the future")
    if current_moment - observed > CHECKOUT_CURRENT_MAX_AGE:
        raise ControlError("checkout current provider evidence is stale")

    return {
        "observed_at_utc": observed_text,
        "readback_sha256": CHECKOUT_CURRENT_SHA256,
        "max_age_seconds": int(CHECKOUT_CURRENT_MAX_AGE.total_seconds()),
    }


def build_checkout_authority(catalog_as_of: str) -> dict[str, Any]:
    """Require historical integrity plus fresh authenticated Stripe currentness."""

    try:
        public_page = AUTOPSY_PUBLIC_PAGE_PATH.read_text(encoding="utf-8")
    except OSError as error:
        raise ControlError(f"cannot read {AUTOPSY_PUBLIC_PAGE_PATH}: {error}") from error

    historical = _HISTORICAL_VALIDATE_CHECKOUT_AUTHORITY(
        read_object(AUTOPSY_PROVIDER_PATH),
        public_page,
        catalog_as_of,
    )

    try:
        raw_readback = CHECKOUT_CURRENT_PATH.read_bytes()
    except OSError as error:
        raise ControlError(f"cannot read {CHECKOUT_CURRENT_PATH}: {error}") from error
    normalized = raw_readback.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    actual_sha256 = hashlib.sha256(normalized).hexdigest()
    if actual_sha256 != CHECKOUT_CURRENT_SHA256:
        raise ControlError("checkout current provider readback digest drift")

    try:
        parsed_readback = json.loads(normalized.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ControlError("checkout current provider readback must be UTF-8 JSON") from error
    if not isinstance(parsed_readback, dict):
        raise ControlError("checkout current provider readback must be one JSON object")
    current = validate_current_checkout_readback(
        parsed_readback,
        current_moment=_current_utc(),
    )
    result = dict(historical)
    result["current_observed_at_utc"] = current["observed_at_utc"]
    result["current_readback_sha256"] = current["readback_sha256"]
    result["current_max_age_seconds"] = current["max_age_seconds"]
    return result


# Core functions resolve globals in the core module at call time.
_core.build_checkout_authority = build_checkout_authority


def validate_catalog(
    catalog: dict[str, Any],
    checkout_authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate catalog truth against freshly recomputed provider authority.

    ``checkout_authority`` remains in the signature for source compatibility,
    but is intentionally not trusted. A caller cannot preserve ACTIVE by
    passing a historical or fabricated authority object.
    """

    if checkout_authority is not None and not isinstance(checkout_authority, dict):
        raise ControlError("checkout authority override must be an object")
    current = build_checkout_authority(catalog.get("as_of"))
    return _HISTORICAL_VALIDATE_CATALOG(catalog, current)


_core.validate_catalog = validate_catalog


def build_control() -> dict[str, Any]:
    """Compile the established control shape after current checkout validation."""

    return _ORIGINAL_BUILD_CONTROL()


_core.build_control = build_control

# Re-export the historical helper intentionally; "historical offer integrity"
# and "right-now provider authority" are separate contracts.
validate_checkout_authority = _HISTORICAL_VALIDATE_CHECKOUT_AUTHORITY


if __name__ == "__main__":
    raise SystemExit(_core.main())
