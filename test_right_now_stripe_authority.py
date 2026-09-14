from __future__ import annotations

import copy
import importlib.util
import json
import os
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "right_now_stripe_authority", ROOT / "host" / "right_now_stripe_authority.py"
)
assert SPEC and SPEC.loader
stripe_authority = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stripe_authority)


def valid_payment_link() -> dict:
    return {
        "id": "plink_1UCFbLATH4EDE7XDlTunr6iO",
        "object": "payment_link",
        "active": True,
        "livemode": True,
        "url": "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g",
        "currency": "usd",
        "metadata": {"commons_offer_id": "agent-failure-autopsy-29"},
        "line_items": {
            "object": "list",
            "has_more": False,
            "data": [
                {
                    "quantity": 1,
                    "currency": "usd",
                    "amount_subtotal": 2900,
                    "amount_total": 2900,
                    "amount_discount": 0,
                    "price": {
                        "id": "price_1UCFbHATH4EDE7XD4NNrjfUe",
                        "object": "price",
                        "active": True,
                        "livemode": True,
                        "currency": "usd",
                        "product": "prod_VCevsvv7skWk3e",
                        "type": "one_time",
                        "recurring": None,
                        "unit_amount": 2900,
                        "unit_amount_decimal": "2900",
                        "metadata": {"commons_offer_id": "agent-failure-autopsy-29"},
                    },
                }
            ],
        },
    }


class FakeResponse:
    def __init__(self, payload: bytes, status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self.payload


class StripeCheckoutAuthorityTests(unittest.TestCase):
    def test_exact_current_payment_link_validates(self) -> None:
        authority = stripe_authority.validate_payment_link(valid_payment_link())
        self.assertIs(authority["active"], True)
        self.assertEqual(authority["offer_id"], "agent-failure-autopsy-29")
        self.assertEqual(authority["amount"], 29)
        self.assertEqual(authority["currency"], "USD")
        self.assertEqual(
            authority["authority"], "AUTHENTICATED_STRIPE_CURRENT_READBACK"
        )

    def test_inactive_or_non_live_link_fails_closed(self) -> None:
        for field, value in (("active", False), ("livemode", False)):
            with self.subTest(field=field):
                payload = valid_payment_link()
                payload[field] = value
                with self.assertRaisesRegex(stripe_authority.StripeAuthorityError, field):
                    stripe_authority.validate_payment_link(payload)

    def test_payment_link_identity_and_url_drift_fail_closed(self) -> None:
        cases = {
            "id": "plink_wrong",
            "url": "https://buy.stripe.com/wrong",
            "currency": "cad",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                payload = valid_payment_link()
                payload[field] = value
                with self.assertRaises(stripe_authority.StripeAuthorityError):
                    stripe_authority.validate_payment_link(payload)

    def test_offer_metadata_is_required_on_link_and_price(self) -> None:
        payload = valid_payment_link()
        payload["metadata"]["commons_offer_id"] = "other"
        with self.assertRaisesRegex(stripe_authority.StripeAuthorityError, "offer metadata"):
            stripe_authority.validate_payment_link(payload)

        payload = valid_payment_link()
        payload["line_items"]["data"][0]["price"]["metadata"]["commons_offer_id"] = "other"
        with self.assertRaisesRegex(stripe_authority.StripeAuthorityError, "price offer metadata"):
            stripe_authority.validate_payment_link(payload)

    def test_line_item_list_must_be_complete_and_exactly_one(self) -> None:
        payload = valid_payment_link()
        payload["line_items"]["has_more"] = True
        with self.assertRaisesRegex(stripe_authority.StripeAuthorityError, "complete"):
            stripe_authority.validate_payment_link(payload)

        payload = valid_payment_link()
        payload["line_items"]["data"].append(copy.deepcopy(payload["line_items"]["data"][0]))
        with self.assertRaisesRegex(stripe_authority.StripeAuthorityError, "exactly one"):
            stripe_authority.validate_payment_link(payload)

    def test_line_item_amount_and_quantity_drift_fail_closed(self) -> None:
        for field, value in (
            ("quantity", 2),
            ("amount_subtotal", 3000),
            ("amount_total", 3000),
            ("amount_discount", 1),
        ):
            with self.subTest(field=field):
                payload = valid_payment_link()
                payload["line_items"]["data"][0][field] = value
                with self.assertRaisesRegex(stripe_authority.StripeAuthorityError, field):
                    stripe_authority.validate_payment_link(payload)

    def test_price_identity_state_and_amount_drift_fail_closed(self) -> None:
        cases = {
            "id": "price_wrong",
            "active": False,
            "livemode": False,
            "currency": "cad",
            "product": "prod_wrong",
            "type": "recurring",
            "recurring": {"interval": "month"},
            "unit_amount": 3000,
            "unit_amount_decimal": "3000",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                payload = valid_payment_link()
                payload["line_items"]["data"][0]["price"][field] = value
                with self.assertRaisesRegex(stripe_authority.StripeAuthorityError, field):
                    stripe_authority.validate_payment_link(payload)

    def test_missing_read_credential_fails_closed(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                stripe_authority.StripeAuthorityError,
                stripe_authority.STRIPE_READ_KEY_ENV,
            ):
                stripe_authority.fetch_current_checkout_authority()

    def test_authenticated_fetch_stamps_process_owned_current_utc(self) -> None:
        payload = json.dumps(valid_payment_link()).encode("utf-8")
        seen: dict[str, object] = {}

        def fake_urlopen(request, timeout):
            seen["url"] = request.full_url
            seen["authorization"] = request.get_header("Authorization")
            seen["timeout"] = timeout
            return FakeResponse(payload)

        fixed_now = datetime(2026, 9, 14, 1, 31, 47, tzinfo=timezone.utc)
        with mock.patch.dict(
            os.environ,
            {stripe_authority.STRIPE_READ_KEY_ENV: "rk_live_test_secret"},
            clear=True,
        ), mock.patch.object(
            stripe_authority.urllib.request, "urlopen", side_effect=fake_urlopen
        ), mock.patch.object(stripe_authority, "_utc_now", return_value=fixed_now):
            authority = stripe_authority.fetch_current_checkout_authority()

        self.assertEqual(
            authority["observed_at_utc"], "2026-09-14T01:31:47Z"
        )
        self.assertEqual(
            authority["authority"], "AUTHENTICATED_STRIPE_CURRENT_READBACK"
        )
        self.assertIn("/v1/payment_links/plink_1UCFbLATH4EDE7XDlTunr6iO", seen["url"])
        self.assertIn("expand%5B%5D=line_items", seen["url"])
        self.assertEqual(seen["authorization"], "Bearer rk_live_test_secret")
        self.assertEqual(seen["timeout"], stripe_authority.REQUEST_TIMEOUT_SECONDS)

    def test_non_200_malformed_and_network_errors_fail_closed(self) -> None:
        key_env = {stripe_authority.STRIPE_READ_KEY_ENV: "rk_live_test_secret"}
        with mock.patch.dict(os.environ, key_env, clear=True), mock.patch.object(
            stripe_authority.urllib.request,
            "urlopen",
            return_value=FakeResponse(b"{}", status=503),
        ):
            with self.assertRaisesRegex(stripe_authority.StripeAuthorityError, "HTTP 200"):
                stripe_authority.fetch_current_checkout_authority()

        with mock.patch.dict(os.environ, key_env, clear=True), mock.patch.object(
            stripe_authority.urllib.request,
            "urlopen",
            return_value=FakeResponse(b"not-json"),
        ):
            with self.assertRaisesRegex(stripe_authority.StripeAuthorityError, "valid JSON"):
                stripe_authority.fetch_current_checkout_authority()

        with mock.patch.dict(os.environ, key_env, clear=True), mock.patch.object(
            stripe_authority.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("down"),
        ):
            with self.assertRaisesRegex(stripe_authority.StripeAuthorityError, "readback failed"):
                stripe_authority.fetch_current_checkout_authority()

    def test_errors_never_echo_the_read_credential(self) -> None:
        secret = "rk_live_do_not_echo"
        with mock.patch.dict(
            os.environ,
            {stripe_authority.STRIPE_READ_KEY_ENV: secret},
            clear=True,
        ), mock.patch.object(
            stripe_authority.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("provider unavailable"),
        ):
            try:
                stripe_authority.fetch_current_checkout_authority()
            except stripe_authority.StripeAuthorityError as error:
                self.assertNotIn(secret, str(error))
            else:
                self.fail("expected StripeAuthorityError")


if __name__ == "__main__":
    unittest.main()
