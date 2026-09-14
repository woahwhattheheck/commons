"""Current Stripe authority for the right-now revenue control plane.

Retained repository artifacts can prove historical offer identity, but they cannot
prove that a Payment Link is active *now*.  This module owns the narrow live
read boundary.  It performs one authenticated, read-only Stripe GET for the
exact Payment Link and validates the returned object before current checkout
truth may be promoted.

No function in this module creates or mutates Stripe objects, charges a buyer,
refunds money, infers a purchase, or recognizes revenue.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


STRIPE_API_BASE = "https://api.stripe.com/v1"
STRIPE_READ_KEY_ENV = "COMMONS_STRIPE_READ_KEY"
REQUEST_TIMEOUT_SECONDS = 10

CHECKOUT_AUTHORITY = {
    "offer_id": "agent-failure-autopsy-29",
    "provider": "STRIPE",
    "provider_account_id": "acct_1U6HI9ATH4EDE7XD",
    "provider_payment_link_id": "plink_1UCFbLATH4EDE7XDlTunr6iO",
    "provider_product_id": "prod_VCevsvv7skWk3e",
    "provider_price_id": "price_1UCFbHATH4EDE7XD4NNrjfUe",
    "payment_url": "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g",
    "currency": "usd",
    "unit_amount": 2900,
    "quantity": 1,
}


class StripeAuthorityError(ValueError):
    """Current Stripe authority cannot be established safely."""


def _utc_now() -> datetime:
    """Process-owned current UTC; intentionally not caller-selectable."""

    return datetime.now(timezone.utc)


def _require_dict(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StripeAuthorityError(f"{where} must be an object")
    return value


def validate_payment_link(payload: Any) -> dict[str, Any]:
    """Validate one live Stripe Payment Link readback.

    This pure validator does not establish currentness by itself.  Currentness
    comes only from :func:`fetch_current_checkout_authority`, which obtains the
    payload through an authenticated Stripe GET and stamps process-owned UTC
    after the response is received.
    """

    link = _require_dict(payload, "Stripe payment link")
    expected = CHECKOUT_AUTHORITY

    exact_top_level = {
        "id": expected["provider_payment_link_id"],
        "object": "payment_link",
        "active": True,
        "livemode": True,
        "url": expected["payment_url"],
    }
    for field, wanted in exact_top_level.items():
        if link.get(field) != wanted:
            raise StripeAuthorityError(f"Stripe payment link {field} drift")

    if link.get("currency") != expected["currency"]:
        raise StripeAuthorityError("Stripe payment link currency drift")

    metadata = _require_dict(link.get("metadata"), "Stripe payment link metadata")
    if metadata.get("commons_offer_id") != expected["offer_id"]:
        raise StripeAuthorityError("Stripe payment link offer metadata drift")

    line_items = _require_dict(link.get("line_items"), "Stripe payment link line_items")
    if line_items.get("object") != "list":
        raise StripeAuthorityError("Stripe payment link line_items object drift")
    if line_items.get("has_more") is not False:
        raise StripeAuthorityError("Stripe payment link line_items must be complete")
    rows = line_items.get("data")
    if not isinstance(rows, list) or len(rows) != 1:
        raise StripeAuthorityError("Stripe payment link must contain exactly one line item")

    row = _require_dict(rows[0], "Stripe payment link line item")
    exact_row = {
        "quantity": expected["quantity"],
        "currency": expected["currency"],
        "amount_subtotal": expected["unit_amount"],
        "amount_total": expected["unit_amount"],
        "amount_discount": 0,
    }
    for field, wanted in exact_row.items():
        if row.get(field) != wanted:
            raise StripeAuthorityError(f"Stripe payment link line item {field} drift")

    price = _require_dict(row.get("price"), "Stripe payment link price")
    exact_price = {
        "id": expected["provider_price_id"],
        "object": "price",
        "active": True,
        "livemode": True,
        "currency": expected["currency"],
        "product": expected["provider_product_id"],
        "type": "one_time",
        "recurring": None,
        "unit_amount": expected["unit_amount"],
        "unit_amount_decimal": str(expected["unit_amount"]),
    }
    for field, wanted in exact_price.items():
        if price.get(field) != wanted:
            raise StripeAuthorityError(f"Stripe payment link price {field} drift")

    price_metadata = _require_dict(price.get("metadata"), "Stripe price metadata")
    if price_metadata.get("commons_offer_id") != expected["offer_id"]:
        raise StripeAuthorityError("Stripe price offer metadata drift")

    return {
        "active": True,
        "offer_id": expected["offer_id"],
        "provider": expected["provider"],
        "provider_account_id": expected["provider_account_id"],
        "provider_payment_link_id": expected["provider_payment_link_id"],
        "provider_product_id": expected["provider_product_id"],
        "provider_price_id": expected["provider_price_id"],
        "payment_url": expected["payment_url"],
        "currency": expected["currency"].upper(),
        "amount": expected["unit_amount"] // 100,
        "authority": "AUTHENTICATED_STRIPE_CURRENT_READBACK",
    }


def _payment_link_url() -> str:
    query = urllib.parse.urlencode({"expand[]": "line_items"})
    payment_link_id = urllib.parse.quote(
        CHECKOUT_AUTHORITY["provider_payment_link_id"], safe=""
    )
    return f"{STRIPE_API_BASE}/payment_links/{payment_link_id}?{query}"


def fetch_current_checkout_authority() -> dict[str, Any]:
    """Read and validate current Payment Link state from Stripe.

    The API key is read only from ``COMMONS_STRIPE_READ_KEY``.  The key never
    appears in returned data or error messages.  Missing credentials, network
    errors, non-2xx provider responses, malformed JSON, inactive/revoked state,
    or any identity/amount drift all fail closed.
    """

    api_key = os.environ.get(STRIPE_READ_KEY_ENV)
    if not isinstance(api_key, str) or not api_key.strip():
        raise StripeAuthorityError(
            f"current Stripe readback requires {STRIPE_READ_KEY_ENV}"
        )

    request = urllib.request.Request(
        _payment_link_url(),
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Accept": "application/json",
            "User-Agent": "commons-right-now-current-authority/1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", None)
            if status != 200:
                raise StripeAuthorityError("Stripe payment link readback was not HTTP 200")
            raw = response.read()
    except StripeAuthorityError:
        raise
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as error:
        raise StripeAuthorityError("Stripe payment link readback failed") from error

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StripeAuthorityError("Stripe payment link readback was not valid JSON") from error

    authority = validate_payment_link(payload)
    observed_at = _utc_now()
    if observed_at.tzinfo is None or observed_at.utcoffset() != timezone.utc.utcoffset(observed_at):
        raise StripeAuthorityError("process clock must provide aware UTC")
    return {
        **authority,
        "observed_at_utc": observed_at.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
    }
