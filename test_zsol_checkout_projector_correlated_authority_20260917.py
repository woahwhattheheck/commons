#!/usr/bin/env python3
"""Retained predecessors for two-sided checkout/payment authority forgery.

Pairwise agreement between caller-supplied catalog and snapshot/registry objects is
not authority. Positive projection must also match a caller-independent retained
canonical root.
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
CATALOG_PATH = ROOT / "revenue" / "outcome_commerce" / "catalog.json"
SNAPSHOT_PATH = ROOT / "revenue" / "checkout_capability" / "snapshot.json"
REGISTRY_PATH = ROOT / "revenue" / "payment_capability" / "registry.json"
SKU = "sku-tip-20260826"
FORGED_URL = "https://buy.stripe.com/correlated_authority_forgery"
FORGED_REFERENCE = "forged-provider-receipt:correlated-authority"
FORGED_OBSERVED_AT = "2026-09-17T08:00:00Z"
STALE_OBSERVED_AT = "1999-01-01T00:00:00Z"


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


class CorrelatedAuthorityPredecessors(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        self.snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        self.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def _listing(catalog: dict) -> dict:
        return next(row for row in catalog["listings"] if row.get("id") == SKU)

    @staticmethod
    def _checkout_rail(snapshot: dict) -> dict:
        return next(row for row in snapshot["canonical_rails"] if row.get("sku") == SKU)

    @staticmethod
    def _stripe_registry(registry: dict) -> dict:
        return next(row for row in registry["rails"] if row.get("provider") == "stripe")

    @classmethod
    def _registry_link(cls, registry: dict) -> dict:
        rail = cls._stripe_registry(registry)
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

    def _forge_catalog(self, *, url: str, reference: str, observed_at: str) -> dict:
        catalog = copy.deepcopy(self.catalog)
        checkout = self._listing(catalog)["checkout"]
        checkout["url"] = url
        checkout["capability_evidence"] = {
            "reference": reference,
            "observed_at": observed_at,
        }
        return catalog

    def test_correlated_checkout_url_reference_timestamp_forgery_is_inert(self) -> None:
        catalog = self._forge_catalog(
            url=FORGED_URL,
            reference=FORGED_REFERENCE,
            observed_at=FORGED_OBSERVED_AT,
        )
        snapshot = copy.deepcopy(self.snapshot)
        rail = self._checkout_rail(snapshot)
        rail["url"] = FORGED_URL
        rail["evidence"] = {
            "reference": FORGED_REFERENCE,
            "observed_at": FORGED_OBSERVED_AT,
        }
        projected = checkout_capability.project(snapshot, catalog)
        self.assertNotIn(SKU, self._checkout_public(projected))

    def test_correlated_payment_url_reference_timestamp_forgery_is_inert(self) -> None:
        catalog = self._forge_catalog(
            url=FORGED_URL,
            reference=FORGED_REFERENCE,
            observed_at=FORGED_OBSERVED_AT,
        )
        registry = copy.deepcopy(self.registry)
        link = self._registry_link(registry)
        link["url"] = FORGED_URL
        link["evidence"] = {
            "reference": FORGED_REFERENCE,
            "observed_at": FORGED_OBSERVED_AT,
        }
        projected = payment_capability.project(registry, catalog)
        self.assertNotIn(SKU, self._payment_public(projected))

    def test_correlated_checkout_stale_but_parseable_evidence_is_inert(self) -> None:
        canonical_url = self._listing(self.catalog)["checkout"]["url"]
        catalog = self._forge_catalog(
            url=canonical_url,
            reference=FORGED_REFERENCE,
            observed_at=STALE_OBSERVED_AT,
        )
        snapshot = copy.deepcopy(self.snapshot)
        rail = self._checkout_rail(snapshot)
        rail["evidence"] = {
            "reference": FORGED_REFERENCE,
            "observed_at": STALE_OBSERVED_AT,
        }
        projected = checkout_capability.project(snapshot, catalog)
        self.assertNotIn(SKU, self._checkout_public(projected))

    def test_correlated_payment_stale_but_parseable_evidence_is_inert(self) -> None:
        canonical_url = self._listing(self.catalog)["checkout"]["url"]
        catalog = self._forge_catalog(
            url=canonical_url,
            reference=FORGED_REFERENCE,
            observed_at=STALE_OBSERVED_AT,
        )
        registry = copy.deepcopy(self.registry)
        link = self._registry_link(registry)
        link["evidence"] = {
            "reference": FORGED_REFERENCE,
            "observed_at": STALE_OBSERVED_AT,
        }
        projected = payment_capability.project(registry, catalog)
        self.assertNotIn(SKU, self._payment_public(projected))

    def test_baseline_canonical_tuple_still_projects(self) -> None:
        self.assertIn(
            SKU,
            self._checkout_public(checkout_capability.project(self.snapshot, self.catalog)),
        )
        self.assertIn(
            SKU,
            self._payment_public(payment_capability.project(self.registry, self.catalog)),
        )

    def test_correlated_predecessors_execute_under_optimized_python(self) -> None:
        module = Path(__file__).stem
        selected = [
            f"{module}.CorrelatedAuthorityPredecessors.test_correlated_checkout_url_reference_timestamp_forgery_is_inert",
            f"{module}.CorrelatedAuthorityPredecessors.test_correlated_payment_url_reference_timestamp_forgery_is_inert",
            f"{module}.CorrelatedAuthorityPredecessors.test_correlated_checkout_stale_but_parseable_evidence_is_inert",
            f"{module}.CorrelatedAuthorityPredecessors.test_correlated_payment_stale_but_parseable_evidence_is_inert",
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
        self.assertIn("Ran 4 tests", completed.stderr)
        self.assertIn("OK", completed.stderr)


if __name__ == "__main__":
    unittest.main()
