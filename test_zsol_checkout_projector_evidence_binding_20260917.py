#!/usr/bin/env python3
"""Behavioral predecessor killers for checkout/payment projector authority.

A URL plus positive booleans is not durable checkout authority.  Both exported
Python projectors must bind catalog checkout capability evidence to the exact
canonical rail/link evidence *before* they emit a public rail.  These tests
exercise project() directly so a later measure_root validator cannot mask a
positive-but-invalid projection.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "revenue" / "outcome_commerce" / "catalog.json"
SNAPSHOT_PATH = ROOT / "revenue" / "checkout_capability" / "snapshot.json"
REGISTRY_PATH = ROOT / "revenue" / "payment_capability" / "registry.json"

TARGET_SKUS = (
    "sku-tip-20260826",
    "sku-seat-20260826",
    "sku-unlock-20260826",
    "sku-monthly-tip-20260826",
    "sku-boost-20260826",
    "sku-whitebox-hour-20260826",
)
TIP = TARGET_SKUS[0]


def _load_module(rel: str, name: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checkout_capability = _load_module(
    "host/checkout_capability.py", "zsol_checkout_projector_binding"
)
payment_capability = _load_module(
    "host/payment_capability.py", "zsol_payment_projector_binding"
)


class ProjectorEvidenceBinding(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        self.snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        self.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def _listing(catalog: dict, sku: str) -> dict:
        return next(row for row in catalog["listings"] if row.get("id") == sku)

    @staticmethod
    def _checkout_rail(snapshot: dict, sku: str) -> dict:
        return next(row for row in snapshot["canonical_rails"] if row.get("sku") == sku)

    @staticmethod
    def _stripe_registry(registry: dict) -> dict:
        return next(row for row in registry["rails"] if row.get("provider") == "stripe")

    @classmethod
    def _registry_link(cls, registry: dict, sku: str) -> dict:
        rail = cls._stripe_registry(registry)
        return next(row for row in rail["canonical_links"] if row.get("sku") == sku)

    @staticmethod
    def _checkout_public(projected: dict) -> set[str]:
        return {row["sku"] for row in projected["public_rails"]}

    @staticmethod
    def _payment_public(projected: dict) -> set[str]:
        return {
            link["sku"]
            for rail in projected["public_rails"]
            for link in rail.get("public_links") or []
        }

    def _assert_target_closed(self, sku: str, *, catalog=None, snapshot=None, registry=None) -> None:
        catalog = catalog or self.catalog
        snapshot = snapshot or self.snapshot
        registry = registry or self.registry
        checkout = checkout_capability.project(snapshot, catalog)
        payment = payment_capability.project(registry, catalog)
        self.assertNotIn(sku, self._checkout_public(checkout))
        self.assertNotIn(sku, self._payment_public(payment))

    def test_baseline_six_public_rails_have_exact_evidence_binding(self) -> None:
        checkout = checkout_capability.project(self.snapshot, self.catalog)
        payment = payment_capability.project(self.registry, self.catalog)
        self.assertTrue(set(TARGET_SKUS).issubset(self._checkout_public(checkout)))
        self.assertTrue(set(TARGET_SKUS).issubset(self._payment_public(payment)))

        stripe = self._stripe_registry(self.registry)
        for sku in TARGET_SKUS:
            with self.subTest(sku=sku):
                listing = self._listing(self.catalog, sku)
                catalog_evidence = listing["checkout"]["capability_evidence"]
                checkout_rail = self._checkout_rail(self.snapshot, sku)
                checkout_evidence = checkout_rail.get("evidence") or {
                    "reference": self.snapshot["evidence"]["reference"],
                    "observed_at": self.snapshot["observed_at"],
                }
                registry_link = self._registry_link(self.registry, sku)
                registry_evidence = registry_link.get("evidence") or stripe["evidence"]
                self.assertEqual(catalog_evidence["reference"], checkout_evidence["reference"])
                self.assertEqual(catalog_evidence["observed_at"], checkout_evidence["observed_at"])
                self.assertEqual(catalog_evidence["reference"], registry_evidence["reference"])
                self.assertEqual(catalog_evidence["observed_at"], registry_evidence["observed_at"])

    def test_missing_or_forged_catalog_evidence_closes_each_public_rail(self) -> None:
        mutations = (
            ("missing", None),
            ("reference", "forged-reference"),
            ("observed_at", "1999-01-01T00:00:00Z"),
            ("observed_at", "not-a-timestamp"),
        )
        for sku in TARGET_SKUS:
            for field, value in mutations:
                with self.subTest(sku=sku, field=field, value=value):
                    catalog = copy.deepcopy(self.catalog)
                    checkout = self._listing(catalog, sku)["checkout"]
                    if field == "missing":
                        checkout.pop("capability_evidence", None)
                    else:
                        checkout["capability_evidence"][field] = value
                    self._assert_target_closed(sku, catalog=catalog)

    def test_catalog_checkout_flags_close_both_projectors(self) -> None:
        mutations = (
            ("status", "INERT"),
            ("provider", "not-stripe"),
            ("link_active", False),
            ("account_charges_enabled", False),
            ("account_payouts_enabled", False),
            ("url", "https://buy.stripe.com/forged_catalog_url"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                catalog = copy.deepcopy(self.catalog)
                self._listing(catalog, TIP)["checkout"][field] = value
                self._assert_target_closed(TIP, catalog=catalog)

    def test_checkout_provider_readiness_is_intrinsic_to_projection(self) -> None:
        mutations = (
            ("name", "not-stripe"),
            ("livemode", False),
            ("charges_enabled", False),
            ("payouts_enabled", False),
            ("currently_due", ["external_account"]),
            ("card_payments", "inactive"),
            ("transfers", "inactive"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                snapshot = copy.deepcopy(self.snapshot)
                snapshot["provider"][field] = value
                public = self._checkout_public(
                    checkout_capability.project(snapshot, self.catalog)
                )
                self.assertTrue(set(TARGET_SKUS).isdisjoint(public))

    def test_checkout_canonical_mutations_close_target(self) -> None:
        for field, value in (
            ("link_active", False),
            ("livemode", False),
            ("url", "https://donate.stripe.com/forged_rail_url"),
            ("exposure", "UNSUPPORTED"),
        ):
            with self.subTest(field=field):
                snapshot = copy.deepcopy(self.snapshot)
                self._checkout_rail(snapshot, TIP)[field] = value
                public = self._checkout_public(
                    checkout_capability.project(snapshot, self.catalog)
                )
                self.assertNotIn(TIP, public)

        for field, value in (
            ("reference", "forged-reference"),
            ("observed_at", "not-a-timestamp"),
        ):
            with self.subTest(evidence_field=field):
                snapshot = copy.deepcopy(self.snapshot)
                rail = self._checkout_rail(snapshot, TIP)
                evidence = rail.setdefault(
                    "evidence",
                    {
                        "reference": snapshot["evidence"]["reference"],
                        "observed_at": snapshot["observed_at"],
                    },
                )
                evidence[field] = value
                public = self._checkout_public(
                    checkout_capability.project(snapshot, self.catalog)
                )
                self.assertNotIn(TIP, public)

        duplicate = copy.deepcopy(self.snapshot)
        url = self._listing(self.catalog, TIP)["checkout"]["url"]
        duplicate["inert_duplicate_urls"] = list(
            duplicate.get("inert_duplicate_urls") or []
        ) + [url]
        self.assertNotIn(
            TIP,
            self._checkout_public(checkout_capability.project(duplicate, self.catalog)),
        )

    def test_payment_registry_authority_mutations_close_target(self) -> None:
        for field, value in (
            ("capability_state", "INERT"),
            ("public_presentation", "INERT"),
            ("charges_enabled", False),
            ("payouts_enabled", False),
        ):
            with self.subTest(rail_field=field):
                registry = copy.deepcopy(self.registry)
                self._stripe_registry(registry)[field] = value
                public = self._payment_public(
                    payment_capability.project(registry, self.catalog)
                )
                self.assertNotIn(TIP, public)

        registry = copy.deepcopy(self.registry)
        rail = self._stripe_registry(registry)
        rail["supported_skus"] = [sku for sku in rail["supported_skus"] if sku != TIP]
        self.assertNotIn(
            TIP,
            self._payment_public(payment_capability.project(registry, self.catalog)),
        )

        for field, value in (
            ("link_active", False),
            ("livemode", False),
            ("url", "https://donate.stripe.com/forged_registry_url"),
        ):
            with self.subTest(link_field=field):
                registry = copy.deepcopy(self.registry)
                self._registry_link(registry, TIP)[field] = value
                public = self._payment_public(
                    payment_capability.project(registry, self.catalog)
                )
                self.assertNotIn(TIP, public)

        for field, value in (
            ("reference", "forged-reference"),
            ("observed_at", "not-a-timestamp"),
        ):
            with self.subTest(link_evidence_field=field):
                registry = copy.deepcopy(self.registry)
                rail = self._stripe_registry(registry)
                link = self._registry_link(registry, TIP)
                evidence = link.setdefault("evidence", copy.deepcopy(rail["evidence"]))
                evidence[field] = value
                public = self._payment_public(
                    payment_capability.project(registry, self.catalog)
                )
                self.assertNotIn(TIP, public)

    def test_projectors_explicitly_consume_catalog_evidence_map(self) -> None:
        checkout_source = (ROOT / "host" / "checkout_capability.py").read_text(encoding="utf-8")
        payment_source = (ROOT / "host" / "payment_capability.py").read_text(encoding="utf-8")
        for source in (checkout_source, payment_source):
            self.assertIn("def catalog_checkout_evidence", source)
            self.assertIn("checkout_evidence = catalog_checkout_evidence(catalog)", source)
            self.assertIn('catalog_evidence.get("reference") == evidence.get("reference")', source)
            self.assertIn('catalog_evidence.get("observed_at") == evidence.get("observed_at")', source)


if __name__ == "__main__":
    unittest.main()
