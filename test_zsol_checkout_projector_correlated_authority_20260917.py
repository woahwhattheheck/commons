#!/usr/bin/env python3
"""Correlated-forgery predecessors for checkout/payment public projection.

Caller-supplied catalog + snapshot/registry objects may agree with each other and
still be false. Positive projection therefore also has to match the repository-
canonical provider authority loaded independently by each projector.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKU = "sku-tip-20260826"
FORGED_URL = "https://buy.stripe.com/forged_correlated_authority"
FORGED_REFERENCE = "forged-provider-reference"
FORGED_TIME = "2026-09-01T00:00:00Z"
STALE_TIME = "2000-01-01T00:00:00Z"


def _load_module(rel: str, name: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checkout_capability = _load_module(
    "host/checkout_capability.py", "zsol_checkout_correlated_authority"
)
payment_capability = _load_module(
    "host/payment_capability.py", "zsol_payment_correlated_authority"
)


class CorrelatedAuthorityForgery(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = json.loads(
            (ROOT / "revenue/outcome_commerce/catalog.json").read_text(encoding="utf-8")
        )
        self.snapshot = json.loads(
            (ROOT / "revenue/checkout_capability/snapshot.json").read_text(encoding="utf-8")
        )
        self.registry = json.loads(
            (ROOT / "revenue/payment_capability/registry.json").read_text(encoding="utf-8")
        )

    @staticmethod
    def _listing(catalog: dict) -> dict:
        return next(row for row in catalog["listings"] if row.get("id") == SKU)

    @staticmethod
    def _checkout_rail(snapshot: dict) -> dict:
        return next(row for row in snapshot["canonical_rails"] if row.get("sku") == SKU)

    @staticmethod
    def _stripe_rail(registry: dict) -> dict:
        return next(row for row in registry["rails"] if row.get("provider") == "stripe")

    @classmethod
    def _payment_link(cls, registry: dict) -> dict:
        rail = cls._stripe_rail(registry)
        return next(row for row in rail["canonical_links"] if row.get("sku") == SKU)

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

    def _assert_checkout_closed(self, snapshot: dict, catalog: dict) -> None:
        self.assertNotIn(
            SKU,
            self._checkout_public(checkout_capability.project(snapshot, catalog)),
        )

    def _assert_payment_closed(self, registry: dict, catalog: dict) -> None:
        self.assertNotIn(
            SKU,
            self._payment_public(payment_capability.project(registry, catalog)),
        )

    def test_canonical_authority_baseline_contains_target(self) -> None:
        checkout_authority = checkout_capability.canonical_checkout_authority()
        payment_authority = payment_capability.canonical_payment_authority()
        self.assertIn(SKU, checkout_authority)
        self.assertIn(SKU, payment_authority)
        self.assertEqual(
            checkout_authority[SKU]["url"],
            self._listing(self.catalog)["checkout"]["url"],
        )
        self.assertEqual(
            payment_authority[SKU]["url"],
            self._listing(self.catalog)["checkout"]["url"],
        )

    def test_checkout_correlated_forged_tuple_stays_inert(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        snapshot = copy.deepcopy(self.snapshot)
        checkout = self._listing(catalog)["checkout"]
        checkout["url"] = FORGED_URL
        checkout["capability_evidence"] = {
            "reference": FORGED_REFERENCE,
            "observed_at": FORGED_TIME,
        }
        rail = self._checkout_rail(snapshot)
        rail["url"] = FORGED_URL
        rail["evidence"] = {
            "reference": FORGED_REFERENCE,
            "observed_at": FORGED_TIME,
        }
        self._assert_checkout_closed(snapshot, catalog)

    def test_checkout_correlated_stale_tuple_stays_inert(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        snapshot = copy.deepcopy(self.snapshot)
        canonical = checkout_capability.canonical_checkout_authority()[SKU]
        self._listing(catalog)["checkout"]["capability_evidence"] = {
            "reference": canonical["reference"],
            "observed_at": STALE_TIME,
        }
        self._checkout_rail(snapshot)["evidence"] = {
            "reference": canonical["reference"],
            "observed_at": STALE_TIME,
        }
        self._assert_checkout_closed(snapshot, catalog)

    def test_checkout_correlated_exposure_mutation_stays_inert(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        snapshot = copy.deepcopy(self.snapshot)
        rail = self._checkout_rail(snapshot)
        rail["exposure"] = "INTAKE_FIRST" if rail.get("exposure") == "CHECKOUT_FIRST" else "CHECKOUT_FIRST"
        self._assert_checkout_closed(snapshot, catalog)

    def test_payment_correlated_forged_tuple_stays_inert(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        registry = copy.deepcopy(self.registry)
        checkout = self._listing(catalog)["checkout"]
        checkout["url"] = FORGED_URL
        checkout["capability_evidence"] = {
            "reference": FORGED_REFERENCE,
            "observed_at": FORGED_TIME,
        }
        link = self._payment_link(registry)
        link["url"] = FORGED_URL
        link["evidence"] = {
            "reference": FORGED_REFERENCE,
            "observed_at": FORGED_TIME,
        }
        self._assert_payment_closed(registry, catalog)

    def test_payment_correlated_stale_tuple_stays_inert(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        registry = copy.deepcopy(self.registry)
        canonical = payment_capability.canonical_payment_authority()[SKU]
        self._listing(catalog)["checkout"]["capability_evidence"] = {
            "reference": canonical["reference"],
            "observed_at": STALE_TIME,
        }
        self._payment_link(registry)["evidence"] = {
            "reference": canonical["reference"],
            "observed_at": STALE_TIME,
        }
        self._assert_payment_closed(registry, catalog)

    def test_payment_correlated_rail_id_mutation_stays_inert(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        registry = copy.deepcopy(self.registry)
        self._stripe_rail(registry)["id"] = "forged-stripe-rail-id"
        self._assert_payment_closed(registry, catalog)

    def test_payment_correlated_exposure_mutation_stays_inert(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        registry = copy.deepcopy(self.registry)
        link = self._payment_link(registry)
        link["exposure"] = "INTAKE_FIRST" if link.get("exposure") == "CHECKOUT_FIRST" else "CHECKOUT_FIRST"
        self._assert_payment_closed(registry, catalog)

    def test_source_retains_independent_canonical_roots(self) -> None:
        checkout_source = (ROOT / "host/checkout_capability.py").read_text(encoding="utf-8")
        payment_source = (ROOT / "host/payment_capability.py").read_text(encoding="utf-8")
        self.assertIn("def canonical_checkout_authority", checkout_source)
        self.assertIn("authority = canonical_checkout_authority()", checkout_source)
        self.assertIn("and authority_matches", checkout_source)
        self.assertIn("def canonical_payment_authority", payment_source)
        self.assertIn("authority = canonical_payment_authority()", payment_source)
        self.assertIn("and authority_matches", payment_source)
        self.assertIn('canonical.get("rail_id") == rail_id', payment_source)

    def test_correlated_predecessors_execute_under_optimized_python(self) -> None:
        module = Path(__file__).stem
        selected = [
            f"{module}.CorrelatedAuthorityForgery.test_checkout_correlated_forged_tuple_stays_inert",
            f"{module}.CorrelatedAuthorityForgery.test_checkout_correlated_stale_tuple_stays_inert",
            f"{module}.CorrelatedAuthorityForgery.test_checkout_correlated_exposure_mutation_stays_inert",
            f"{module}.CorrelatedAuthorityForgery.test_payment_correlated_forged_tuple_stays_inert",
            f"{module}.CorrelatedAuthorityForgery.test_payment_correlated_stale_tuple_stays_inert",
            f"{module}.CorrelatedAuthorityForgery.test_payment_correlated_rail_id_mutation_stays_inert",
            f"{module}.CorrelatedAuthorityForgery.test_payment_correlated_exposure_mutation_stays_inert",
        ]
        completed = subprocess.run(
            [sys.executable, "-O", "-m", "unittest", *selected],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"optimized correlated predecessors failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        self.assertIn("Ran 7 tests", completed.stderr)
        self.assertIn("OK", completed.stderr)


if __name__ == "__main__":
    unittest.main()
