#!/usr/bin/env python3
"""Fail-closed predecessors for duplicate catalog checkout identities.

No projector may compose active state from one listing with capability evidence
from another listing carrying the same SKU, regardless of row order.
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


def _load_module(rel: str, name: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checkout_capability = _load_module(
    "host/checkout_capability.py", "zsol_checkout_duplicate_authority"
)
payment_capability = _load_module(
    "host/payment_capability.py", "zsol_payment_duplicate_authority"
)


class DuplicateCatalogAuthority(unittest.TestCase):
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
    def _checkout_public(projected: dict) -> set[str]:
        return {row["sku"] for row in projected["public_rails"]}

    @staticmethod
    def _payment_public(projected: dict) -> set[str]:
        return {
            link["sku"]
            for rail in projected["public_rails"]
            for link in rail.get("public_links") or []
        }

    def _assert_closed(self, catalog: dict) -> None:
        self.assertNotIn(SKU, checkout_capability.catalog_checkouts(catalog))
        self.assertNotIn(SKU, payment_capability.catalog_checkouts(catalog))
        self.assertNotIn(
            SKU,
            self._checkout_public(checkout_capability.project(self.snapshot, catalog)),
        )
        self.assertNotIn(
            SKU,
            self._payment_public(payment_capability.project(self.registry, catalog)),
        )

    def _split_catalog(self, donor_mutation: tuple[str, object], donor_first: bool) -> dict:
        catalog = copy.deepcopy(self.catalog)
        active = self._listing(catalog)
        donor = copy.deepcopy(active)
        active["checkout"].pop("capability_evidence", None)
        field, value = donor_mutation
        donor["checkout"][field] = value
        listings = [row for row in catalog["listings"] if row is not active]
        if donor_first:
            catalog["listings"] = [donor, active, *listings]
        else:
            catalog["listings"] = [active, donor, *listings]
        return catalog

    def test_inactive_evidence_donor_cannot_complete_active_row_in_either_order(self) -> None:
        for donor_first in (False, True):
            with self.subTest(donor_first=donor_first):
                self._assert_closed(
                    self._split_catalog(("status", "INERT"), donor_first)
                )

    def test_account_disabled_evidence_donor_cannot_complete_active_row_in_either_order(self) -> None:
        for donor_first in (False, True):
            with self.subTest(donor_first=donor_first):
                self._assert_closed(
                    self._split_catalog(("account_charges_enabled", False), donor_first)
                )

    def test_different_url_duplicate_cannot_complete_active_row_in_either_order(self) -> None:
        alternate = "https://donate.stripe.com/duplicate_authority_predecessor"
        for donor_first in (False, True):
            with self.subTest(donor_first=donor_first):
                self._assert_closed(self._split_catalog(("url", alternate), donor_first))

    def test_two_fully_active_duplicate_rows_fail_closed_in_either_order(self) -> None:
        for duplicate_first in (False, True):
            with self.subTest(duplicate_first=duplicate_first):
                catalog = copy.deepcopy(self.catalog)
                original = self._listing(catalog)
                duplicate = copy.deepcopy(original)
                others = [row for row in catalog["listings"] if row is not original]
                if duplicate_first:
                    catalog["listings"] = [duplicate, original, *others]
                else:
                    catalog["listings"] = [original, duplicate, *others]
                self._assert_closed(catalog)

    def test_unique_authoritative_row_still_projects_normally(self) -> None:
        self.assertIn(SKU, checkout_capability.catalog_checkouts(self.catalog))
        self.assertIn(SKU, payment_capability.catalog_checkouts(self.catalog))
        self.assertIn(
            SKU,
            self._checkout_public(checkout_capability.project(self.snapshot, self.catalog)),
        )
        self.assertIn(
            SKU,
            self._payment_public(payment_capability.project(self.registry, self.catalog)),
        )

    def test_duplicate_predecessors_execute_under_optimized_python(self) -> None:
        module = Path(__file__).stem
        selected = [
            f"{module}.DuplicateCatalogAuthority.test_inactive_evidence_donor_cannot_complete_active_row_in_either_order",
            f"{module}.DuplicateCatalogAuthority.test_account_disabled_evidence_donor_cannot_complete_active_row_in_either_order",
            f"{module}.DuplicateCatalogAuthority.test_different_url_duplicate_cannot_complete_active_row_in_either_order",
            f"{module}.DuplicateCatalogAuthority.test_two_fully_active_duplicate_rows_fail_closed_in_either_order",
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
            msg=f"optimized predecessors failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        self.assertIn("Ran 4 tests", completed.stderr)
        self.assertIn("OK", completed.stderr)


if __name__ == "__main__":
    unittest.main()
