from __future__ import annotations

import copy
import importlib.util
import inspect
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "right_now_revenue_checkout_currentness",
    ROOT / "host" / "right_now_revenue.py",
)
assert SPEC and SPEC.loader
control = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(control)


FRESH_NOW = datetime(2026, 9, 14, 1, 40, 0, tzinfo=timezone.utc)


class RightNowCheckoutCurrentnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.readback = json.loads(
            control.CHECKOUT_CURRENT_PATH.read_text(encoding="utf-8")
        )

    def validate(self, value=None, now=FRESH_NOW):
        return control.validate_current_checkout_readback(
            self.readback if value is None else value,
            current_moment=now,
        )

    def test_exact_authenticated_readback_is_current(self) -> None:
        result = self.validate()
        self.assertEqual(result["observed_at_utc"], "2026-09-14T01:30:22Z")
        self.assertEqual(result["readback_sha256"], control.CHECKOUT_CURRENT_SHA256)
        self.assertEqual(result["max_age_seconds"], 24 * 60 * 60)

    def test_production_authority_uses_process_clock_only(self) -> None:
        signature = inspect.signature(control.build_checkout_authority)
        self.assertEqual(list(signature.parameters), ["catalog_as_of"])
        with mock.patch.object(control, "_current_utc", return_value=FRESH_NOW):
            authority = control.build_checkout_authority("2026-09-13T15:34:33Z")
        self.assertIs(authority["active"], True)
        self.assertEqual(
            authority["current_observed_at_utc"], "2026-09-14T01:30:22Z"
        )
        self.assertEqual(
            authority["current_readback_sha256"], control.CHECKOUT_CURRENT_SHA256
        )

    def test_stale_provider_readback_fails_independent_of_catalog_time(self) -> None:
        stale_now = datetime(2026, 9, 15, 1, 30, 23, tzinfo=timezone.utc)
        for catalog_as_of in (
            "2026-09-01T00:00:00Z",
            "2026-09-13T15:34:33Z",
            "2030-01-01T00:00:00Z",
        ):
            with self.subTest(catalog_as_of=catalog_as_of):
                with mock.patch.object(control, "_current_utc", return_value=stale_now):
                    with self.assertRaisesRegex(control.ControlError, "stale"):
                        control.build_checkout_authority(catalog_as_of)

    def test_future_provider_observation_fails(self) -> None:
        value = copy.deepcopy(self.readback)
        value["observed_at_utc"] = "2026-09-14T01:40:01Z"
        with self.assertRaisesRegex(control.ControlError, "future"):
            self.validate(value)

    def test_inactive_or_nonlive_provider_state_fails(self) -> None:
        cases = (
            (("payment_link", "active"), False),
            (("payment_link", "livemode"), False),
            (("line_item", "price_active"), False),
            (("line_item", "livemode"), False),
            (("livemode",), False),
        )
        for path, replacement in cases:
            with self.subTest(path=path):
                value = copy.deepcopy(self.readback)
                target = value
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = replacement
                with self.assertRaises(control.ControlError):
                    self.validate(value)

    def test_provider_identity_amount_and_contract_drift_fail(self) -> None:
        cases = (
            (("account_id",), "acct_wrong"),
            (("payment_link", "id"), "plink_wrong"),
            (("payment_link", "url"), "https://buy.stripe.com/wrong"),
            (("payment_link", "offer_id"), "wrong-offer"),
            (("payment_link", "contract_version"), "wrong-contract"),
            (("payment_link", "currency"), "eur"),
            (("line_item", "price_id"), "price_wrong"),
            (("line_item", "product_id"), "prod_wrong"),
            (("line_item", "unit_amount"), 3000),
            (("line_item", "quantity"), 2),
            (("line_item", "currency"), "eur"),
            (("line_item", "lookup_key"), "wrong"),
        )
        for path, replacement in cases:
            with self.subTest(path=path):
                value = copy.deepcopy(self.readback)
                target = value
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = replacement
                with self.assertRaises(control.ControlError):
                    self.validate(value)

    def test_provider_source_authority_drift_fails(self) -> None:
        cases = (
            ("authenticated_read", False),
            ("collector", "CALLER_JSON"),
            ("payment_link_operation", "GET /wrong"),
            ("line_items_operation", "GET /wrong"),
        )
        for field, replacement in cases:
            with self.subTest(field=field):
                value = copy.deepcopy(self.readback)
                value["source"][field] = replacement
                with self.assertRaises(control.ControlError):
                    self.validate(value)

    def test_noncanonical_observation_timestamp_fails(self) -> None:
        value = copy.deepcopy(self.readback)
        value["observed_at_utc"] = "2026-09-14T01:30:22+00:00"
        with self.assertRaisesRegex(control.ControlError, "canonical UTC seconds"):
            self.validate(value)

    def test_bool_cannot_alias_integer_amount_or_quantity(self) -> None:
        for field in ("unit_amount", "quantity"):
            with self.subTest(field=field):
                value = copy.deepcopy(self.readback)
                value["line_item"][field] = True
                with self.assertRaisesRegex(control.ControlError, field):
                    self.validate(value)

    def test_tampered_retained_file_cannot_reseal_current_authority(self) -> None:
        value = copy.deepcopy(self.readback)
        value["payment_link"]["active"] = False
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stripe_checkout_current.json"
            path.write_text(
                json.dumps(value, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            with mock.patch.object(control, "CHECKOUT_CURRENT_PATH", path):
                with mock.patch.object(control, "_current_utc", return_value=FRESH_NOW):
                    with self.assertRaisesRegex(control.ControlError, "digest drift"):
                        control.build_checkout_authority("2026-09-13T15:34:33Z")

    def test_historical_validator_remains_distinct_from_current_authority(self) -> None:
        catalog = control.read_object(control.CATALOG_PATH)
        offer = control.read_object(control.AUTOPSY_PROVIDER_PATH)
        page = control.AUTOPSY_PUBLIC_PAGE_PATH.read_text(encoding="utf-8")
        historical = control.validate_checkout_authority(
            offer,
            page,
            catalog["as_of"],
        )
        self.assertIs(historical["active"], True)
        self.assertNotIn("current_observed_at_utc", historical)

    def test_control_compilation_fails_once_current_evidence_expires(self) -> None:
        stale_now = datetime(2026, 9, 15, 1, 30, 23, tzinfo=timezone.utc)
        with mock.patch.object(control, "_current_utc", return_value=stale_now):
            with self.assertRaisesRegex(control.ControlError, "stale"):
                control.build_control()


if __name__ == "__main__":
    unittest.main()
