from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "right_now_revenue_checkout_authority", ROOT / "host" / "right_now_revenue.py"
)
assert SPEC and SPEC.loader
control = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(control)


class RightNowCheckoutAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = control.read_object(control.CATALOG_PATH)
        self.offer = control.read_object(control.AUTOPSY_PROVIDER_PATH)
        self.page = control.AUTOPSY_PUBLIC_PAGE_PATH.read_text(encoding="utf-8")

    def validate(self, offer=None, page=None):
        return control.validate_checkout_authority(
            self.offer if offer is None else offer,
            self.page if page is None else page,
            self.catalog["as_of"],
        )

    def test_exact_retained_provider_evidence_and_public_page_are_active(self) -> None:
        authority = self.validate()
        self.assertIs(authority["active"], True)
        self.assertEqual(authority["offer_id"], "agent-failure-autopsy-29")
        self.assertEqual(authority["provider"], "STRIPE")
        self.assertEqual(
            authority["provider_payment_link_id"],
            "plink_1UCFbLATH4EDE7XDlTunr6iO",
        )
        self.assertEqual(
            authority["provider_receipt_sha256"],
            "39ce997a58fe256b11c82963559452ec167bb8c2c7f42c67ad7ce790052e7b42",
        )

    def test_catalog_truth_reconciles_to_retained_authority(self) -> None:
        authority = self.validate()
        self.assertEqual(
            self.catalog["truth"]["active_chargeable_checkout"],
            authority["active"],
        )
        control.validate_catalog(copy.deepcopy(self.catalog), authority)

    def test_repo_authored_catalog_boolean_cannot_hide_missing_live_row(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["offers"][0]["payment_state"] = "BUYER_SPECIFIC_HANDOFF_REQUIRED"
        catalog["truth"]["active_chargeable_checkout"] = True
        with self.assertRaisesRegex(control.ControlError, "retained checkout authority"):
            control.validate_catalog(catalog, self.validate())

    def test_second_unbound_live_checkout_claim_fails_closed(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["offers"][1]["payment_state"] = "LIVE_PUBLIC_CHECKOUT_PAGE"
        catalog["offers"][1]["start_route"] = "agent-rescue.html"
        with self.assertRaises(control.ControlError):
            control.validate_catalog(catalog, self.validate())

    def test_provider_status_drift_fails_closed(self) -> None:
        offer = copy.deepcopy(self.offer)
        offer["status"] = "PUBLIC_OFFER"
        with self.assertRaisesRegex(control.ControlError, "ACTIVE_VERIFIED"):
            self.validate(offer=offer)

    def test_provider_identity_and_amount_drift_fail_closed(self) -> None:
        cases = {
            "payment_url": "https://buy.stripe.com/invented",
            "provider_payment_link_id": "plink_invented",
            "provider_receipt_sha256": "0" * 64,
            "amount": 30,
        }
        for field, replacement in cases.items():
            with self.subTest(field=field):
                offer = copy.deepcopy(self.offer)
                offer["price"][field] = replacement
                with self.assertRaisesRegex(control.ControlError, field):
                    self.validate(offer=offer)

    def test_live_mode_evidence_is_required(self) -> None:
        offer = copy.deepcopy(self.offer)
        offer["price"]["provider_account_binding"]["live_mode_verified_from_objects"] = False
        with self.assertRaisesRegex(control.ControlError, "live-mode evidence"):
            self.validate(offer=offer)

    def test_provider_evidence_cannot_postdate_catalog_boundary(self) -> None:
        offer = copy.deepcopy(self.offer)
        offer["price"]["verified_at_utc"] = "2026-09-14T00:00:00+00:00"
        with self.assertRaisesRegex(control.ControlError, "later than catalog as_of"):
            self.validate(offer=offer)

    def test_public_page_must_expose_data_checkout_anchor(self) -> None:
        page = self.page.replace(" data-checkout", "")
        with self.assertRaisesRegex(control.ControlError, "data-checkout anchor"):
            self.validate(page=page)

    def test_every_public_checkout_anchor_must_use_authoritative_base_url(self) -> None:
        page = self.page + '\n<a data-checkout href="https://buy.stripe.com/invented">bad</a>\n'
        with self.assertRaisesRegex(control.ControlError, "non-authoritative payment URL"):
            self.validate(page=page)


if __name__ == "__main__":
    unittest.main()
