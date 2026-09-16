from __future__ import annotations

import copy
import importlib.util
import inspect
import json
import subprocess
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

    def test_exact_credential_host_readback_is_current(self) -> None:
        result = self.validate()
        self.assertEqual(result["observed_at_utc"], "2026-09-14T01:30:22Z")
        self.assertEqual(result["max_age_seconds"], 24 * 60 * 60)
        self.assertEqual(result["authority_boundary"], "CREDENTIAL_HOST_STRIPE_READ")
        self.assertEqual(len(result["readback_sha256"]), 64)

    def test_production_authority_reads_fixed_credential_host_and_process_clock(self) -> None:
        signature = inspect.signature(control.build_checkout_authority)
        self.assertEqual(list(signature.parameters), ["catalog_as_of"])
        self.assertTrue(control.CHECKOUT_CURRENT_COLLECTOR.is_absolute())
        self.assertEqual(
            str(control.CHECKOUT_CURRENT_COLLECTOR),
            "/usr/local/libexec/commons-stripe-current-readback",
        )
        self.assertEqual(list(inspect.signature(control._credential_host_readback).parameters), [])
        with mock.patch.object(
            control, "_credential_host_readback", return_value=copy.deepcopy(self.readback)
        ):
            with mock.patch.object(control, "_current_utc", return_value=FRESH_NOW):
                authority = control.build_checkout_authority("2026-09-13T15:34:33Z")
        self.assertIs(authority["active"], True)
        self.assertEqual(authority["current_observed_at_utc"], "2026-09-14T01:30:22Z")
        self.assertEqual(authority["current_authority_boundary"], "CREDENTIAL_HOST_STRIPE_READ")

    def test_repository_receipt_is_audit_only_not_current_authority(self) -> None:
        with mock.patch.object(
            control, "CHECKOUT_CURRENT_PATH", Path("/definitely/not/a/provider/root.json")
        ):
            with mock.patch.object(
                control, "_credential_host_readback", return_value=copy.deepcopy(self.readback)
            ):
                with mock.patch.object(control, "_current_utc", return_value=FRESH_NOW):
                    authority = control.build_checkout_authority("2026-09-13T15:34:33Z")
        self.assertTrue(authority["active"])

    def test_coherent_repo_reseal_without_credential_host_read_fails_closed(self) -> None:
        forged = copy.deepcopy(self.readback)
        forged["observed_at_utc"] = "2026-09-14T01:39:59Z"
        forged["source"]["authenticated_read"] = True
        self.assertTrue(self.validate(forged))
        with mock.patch.object(
            control,
            "_credential_host_readback",
            side_effect=control.ControlError("checkout current credential-host collector unavailable"),
        ):
            with mock.patch.object(control, "_current_utc", return_value=FRESH_NOW):
                with self.assertRaisesRegex(control.ControlError, "credential-host collector unavailable"):
                    control.build_checkout_authority("2026-09-13T15:34:33Z")

    def test_missing_or_failing_host_collector_fails_closed(self) -> None:
        with mock.patch.object(subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(control.ControlError, "collector unavailable"):
                control._credential_host_readback()
        failed = subprocess.CompletedProcess(
            [str(control.CHECKOUT_CURRENT_COLLECTOR)], 7, stdout="", stderr=""
        )
        with mock.patch.object(subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(control.ControlError, "collector failed"):
                control._credential_host_readback()

    def test_noisy_or_malformed_host_collector_fails_closed(self) -> None:
        noisy = subprocess.CompletedProcess(
            [str(control.CHECKOUT_CURRENT_COLLECTOR)],
            0,
            stdout=json.dumps(self.readback),
            stderr="warning",
        )
        with mock.patch.object(subprocess, "run", return_value=noisy):
            with self.assertRaisesRegex(control.ControlError, "emitted stderr"):
                control._credential_host_readback()
        malformed = subprocess.CompletedProcess(
            [str(control.CHECKOUT_CURRENT_COLLECTOR)],
            0,
            stdout="not-json",
            stderr="",
        )
        with mock.patch.object(subprocess, "run", return_value=malformed):
            with self.assertRaisesRegex(control.ControlError, "must be JSON"):
                control._credential_host_readback()

    def test_stale_provider_readback_fails_independent_of_catalog_time(self) -> None:
        stale_now = datetime(2026, 9, 15, 1, 30, 23, tzinfo=timezone.utc)
        for catalog_as_of in (
            "2026-09-01T00:00:00Z",
            "2026-09-13T15:34:33Z",
            "2030-01-01T00:00:00Z",
        ):
            with self.subTest(catalog_as_of=catalog_as_of):
                with mock.patch.object(
                    control,
                    "_credential_host_readback",
                    return_value=copy.deepcopy(self.readback),
                ):
                    with mock.patch.object(control, "_current_utc", return_value=stale_now):
                        with self.assertRaisesRegex(control.ControlError, "stale"):
                            control.build_checkout_authority(catalog_as_of)

    def test_future_provider_observation_fails(self) -> None:
        value = copy.deepcopy(self.readback)
        value["observed_at_utc"] = "2026-09-14T01:40:01Z"
        with self.assertRaisesRegex(control.ControlError, "future"):
            self.validate(value)

    def test_inactive_nonlive_identity_amount_and_contract_drift_fail(self) -> None:
        cases = (
            (("payment_link", "active"), False),
            (("payment_link", "livemode"), False),
            (("line_item", "price_active"), False),
            (("line_item", "livemode"), False),
            (("livemode",), False),
            (("account_id",), "acct_wrong"),
            (("payment_link", "id"), "plink_wrong"),
            (("payment_link", "url"), "https://buy.stripe.com/wrong"),
            (("payment_link", "offer_id"), "wrong-offer"),
            (("payment_link", "contract_version"), "wrong-contract"),
            (("line_item", "price_id"), "price_wrong"),
            (("line_item", "product_id"), "prod_wrong"),
            (("line_item", "unit_amount"), 3000),
            (("line_item", "quantity"), 2),
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
        for field, replacement in (
            ("authenticated_read", False),
            ("collector", "CALLER_JSON"),
            ("payment_link_operation", "GET /wrong"),
            ("line_items_operation", "GET /wrong"),
        ):
            with self.subTest(field=field):
                value = copy.deepcopy(self.readback)
                value["source"][field] = replacement
                with self.assertRaises(control.ControlError):
                    self.validate(value)

    def test_catalog_override_cannot_bypass_live_provider_read(self) -> None:
        catalog = control.read_object(control.CATALOG_PATH)
        offer = control.read_object(control.AUTOPSY_PROVIDER_PATH)
        page = control.AUTOPSY_PUBLIC_PAGE_PATH.read_text(encoding="utf-8")
        historical = control.validate_checkout_authority(offer, page, catalog["as_of"])
        stale_now = datetime(2026, 9, 15, 1, 30, 23, tzinfo=timezone.utc)
        with mock.patch.object(
            control, "_credential_host_readback", return_value=copy.deepcopy(self.readback)
        ):
            with mock.patch.object(control, "_current_utc", return_value=stale_now):
                with self.assertRaisesRegex(control.ControlError, "stale"):
                    control.validate_catalog(copy.deepcopy(catalog), historical)

    def test_control_compilation_uses_credential_host_authority(self) -> None:
        with mock.patch.object(
            control, "_credential_host_readback", return_value=copy.deepcopy(self.readback)
        ):
            with mock.patch.object(control, "_current_utc", return_value=FRESH_NOW):
                compiled = control.build_control()
        self.assertIs(compiled["truth"]["active_chargeable_checkout"], True)


if __name__ == "__main__":
    unittest.main()
