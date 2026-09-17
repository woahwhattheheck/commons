#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from host.product_lifecycle_guard import (
    LifecycleError,
    canonical_checkout_identity,
    check_repo,
    load_json_bytes,
    validate_registry,
)

URL = "https://buy.stripe.com/exampleABC123"
SOURCE = "revenue/example_offer/offer.json"


def registry(state: str = "RETIRED", *, url: str = URL, source: str = SOURCE):
    return {
        "schema": "commons.product-lifecycle.v1",
        "products": [
            {
                "id": "example-product",
                "state": state,
                "checkout_urls": [url],
                "catalog_sources": [source],
                "effective_at": "2026-09-17T20:00:00Z" if state == "RETIRED" else None,
                "provenance": "test",
                "note": "fixture",
            }
        ],
    }


class ProductLifecycleGuardTests(unittest.TestCase):
    def make_repo(self, doc=None):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "revenue/product_lifecycle").mkdir(parents=True)
        (root / "revenue/outcome_commerce").mkdir(parents=True)
        (root / "host").mkdir(parents=True)
        (root / "p").mkdir()
        (root / "by").mkdir()
        (root / "d").mkdir()
        (root / "revenue/product_lifecycle/registry.json").write_text(
            json.dumps(doc if doc is not None else registry(), sort_keys=True),
            encoding="utf-8",
        )
        return td, root

    def test_retired_checkout_on_active_root_html_is_rejected(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        (root / "storefront.html").write_text(
            f'<a data-checkout href="{URL}">buy</a>', encoding="utf-8"
        )
        rows = check_repo(root)
        self.assertEqual(1, len(rows))
        self.assertEqual(("example-product", "storefront.html", "checkout_url"),
                         (rows[0].product_id, rows[0].path, rows[0].kind))

    def test_historical_receipts_are_not_scanned(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        for base in ("p", "by", "d"):
            (root / base / "receipt.html").write_text(URL, encoding="utf-8")
        self.assertEqual((), check_repo(root))

    def test_retiring_is_non_blocking_until_cleanup_composes(self):
        td, root = self.make_repo(registry("RETIRING"))
        self.addCleanup(td.cleanup)
        (root / "storefront.html").write_text(URL, encoding="utf-8")
        (root / "host/payment_capability.py").write_text(repr(URL), encoding="utf-8")
        self.assertEqual((), check_repo(root))

    def test_normalized_checkout_alias_is_rejected(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        alias = "HTTPS://BUY.STRIPE.COM/exampleABC123/"
        (root / "storefront.html").write_text(alias, encoding="utf-8")
        rows = check_repo(root)
        self.assertEqual(1, len(rows))
        self.assertEqual(URL, rows[0].identity)

    def test_percent_encoded_path_alias_is_rejected(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        alias = "https://buy.stripe.com/example%41BC123"
        (root / "storefront.html").write_text(alias, encoding="utf-8")
        self.assertEqual(1, len(check_repo(root)))

    def test_catalog_source_in_active_generator_is_rejected(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        (root / "revenue/outcome_commerce/catalog.json").write_text(
            json.dumps({"integration_sources": [SOURCE]}), encoding="utf-8"
        )
        rows = check_repo(root)
        self.assertEqual(1, len(rows))
        self.assertEqual("catalog_source", rows[0].kind)

    def test_catalog_source_in_historical_receipt_remains_legal(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        (root / "p/receipt.html").write_text(SOURCE, encoding="utf-8")
        self.assertEqual((), check_repo(root))

    def test_duplicate_product_id_rejected(self):
        doc = registry()
        doc["products"].append(dict(doc["products"][0]))
        with self.assertRaisesRegex(LifecycleError, "duplicate product id"):
            validate_registry(doc)

    def test_duplicate_normalized_checkout_identity_rejected_across_products(self):
        doc = registry()
        other = dict(doc["products"][0])
        other["id"] = "second-product"
        other["checkout_urls"] = ["HTTPS://BUY.STRIPE.COM/exampleABC123/"]
        other["catalog_sources"] = ["revenue/second/offer.json"]
        doc["products"].append(other)
        with self.assertRaisesRegex(LifecycleError, "checkout identity shared"):
            validate_registry(doc)

    def test_duplicate_checkout_identity_rejected_within_product(self):
        doc = registry()
        doc["products"][0]["checkout_urls"] = [
            URL,
            "HTTPS://BUY.STRIPE.COM/exampleABC123/",
        ]
        with self.assertRaisesRegex(LifecycleError, "within example-product"):
            validate_registry(doc)

    def test_invalid_state_rejected(self):
        doc = registry()
        doc["products"][0]["state"] = "DELETED"
        with self.assertRaisesRegex(LifecycleError, "invalid lifecycle state"):
            validate_registry(doc)

    def test_retired_requires_effective_at(self):
        doc = registry()
        doc["products"][0]["effective_at"] = None
        with self.assertRaisesRegex(LifecycleError, "requires effective_at"):
            validate_registry(doc)

    def test_registry_duplicate_json_key_rejected(self):
        raw = b'{"schema":"commons.product-lifecycle.v1","schema":"x","products":[]}'
        with self.assertRaisesRegex(LifecycleError, "duplicate JSON key"):
            load_json_bytes(raw)

    def test_registry_float_rejected(self):
        raw = b'{"schema":"commons.product-lifecycle.v1","products":[],"x":1.5}'
        with self.assertRaisesRegex(LifecycleError, "floating-point"):
            load_json_bytes(raw)

    def test_unknown_keys_rejected(self):
        doc = registry()
        doc["products"][0]["authority"] = "send-money"
        with self.assertRaisesRegex(LifecycleError, "unknown keys"):
            validate_registry(doc)

    def test_catalog_source_path_traversal_rejected(self):
        doc = registry(source="../p/receipt.json")
        with self.assertRaisesRegex(LifecycleError, "normalized repository-relative"):
            validate_registry(doc)

    def test_checkout_query_fragment_rejected_in_registry(self):
        doc = registry(url=URL + "?utm=stale")
        with self.assertRaisesRegex(LifecycleError, "query/fragment"):
            validate_registry(doc)

    def test_checkout_identity_has_no_assert_dependency(self):
        self.assertEqual(URL, canonical_checkout_identity(URL))


if __name__ == "__main__":
    unittest.main()
