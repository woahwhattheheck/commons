#!/usr/bin/env python3
"""Exact-engine product-domain contracts for pressure-delay certificates."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))

import pressure_delay_invariance as candidate  # noqa: E402


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


mechanics = _load_module(
    "_titan_pressure_product_domain_mechanics",
    ROOT / "revenue/kaggriculture/cloud-execution-lab/mechanics.py",
)
EXACT_PRODUCTS = tuple(mechanics.PRODUCTS)


def _sell(product: str, quantity: int, tag: str) -> dict[str, object]:
    return {
        "action": "SELL",
        "type": product,
        "quantity": quantity,
        "tag": tag,
    }


class PressureProductDomainTests(unittest.TestCase):
    def test_carrier_domain_equals_exact_engine_domain(self) -> None:
        self.assertEqual(candidate.PRODUCTS, EXACT_PRODUCTS)
        self.assertEqual(len(candidate.PRODUCTS), 9)
        self.assertNotIn("CORN", candidate.PRODUCTS)
        self.assertIn("STRAWBERRY", candidate.PRODUCTS)
        self.assertIn("FERTILIZER", candidate.PRODUCTS)

    def test_every_exact_product_reaches_receipt_and_certificate_apis(self) -> None:
        quote = lambda product, stock: mechanics.market_price(product, stock)
        for product in EXACT_PRODUCTS:
            with self.subTest(product=product):
                receipt = candidate.exact_sale_receipt(
                    product,
                    mechanics.MARKET_I0,
                    3,
                    quote,
                )
                self.assertIsInstance(receipt, int)
                self.assertGreater(receipt, 0)
                certificate = candidate.certify_delay_invariance(
                    product,
                    mechanics.MARKET_I0,
                    3,
                    0,
                    quote,
                )
                self.assertTrue(certificate.safe)
                self.assertEqual(certificate.product, product)
                self.assertEqual(certificate.baseline_receipt, receipt)

    def test_every_exact_product_can_be_promoted_across_a_flat_safe_lot(self) -> None:
        inventory = {product: 0 for product in EXACT_PRODUCTS}
        bounds = {product: 4 for product in EXACT_PRODUCTS}
        for index, exposed_product in enumerate(EXACT_PRODUCTS):
            neutral_product = EXACT_PRODUCTS[(index + 1) % len(EXACT_PRODUCTS)]
            neutral = _sell(neutral_product, 2, "neutral")
            exposed = _sell(exposed_product, 1, "exposed")
            pressures = {product: 0 for product in EXACT_PRODUCTS}
            pressures[exposed_product] = 1
            with self.subTest(product=exposed_product):
                result = candidate.certified_pressure_partition(
                    [neutral, exposed],
                    pressure_by_product=pressures,
                    inventory=inventory,
                    max_rival_units=bounds,
                    price_by_stock=lambda _product, _stock: 7,
                )
                self.assertEqual(result.actions, (exposed, neutral))
                self.assertTrue(result.changed)
                self.assertEqual(result.decisions[0].kind, "demotable")
                self.assertEqual(result.decisions[1].kind, "promoted")

    def test_non_engine_corn_is_rejected_and_splits_segments(self) -> None:
        quote = lambda _product, _stock: 7
        self.assertIsNone(candidate.exact_sale_receipt("CORN", 0, 1, quote))
        before = _sell("WHEAT", 1, "before")
        corn = _sell("CORN", 1, "invalid-corn")
        after = _sell("MILK", 1, "after")
        result = candidate.certified_pressure_partition(
            [before, corn, after],
            pressure_by_product={product: int(product == "MILK") for product in EXACT_PRODUCTS},
            inventory={product: 0 for product in EXACT_PRODUCTS},
            max_rival_units={product: 4 for product in EXACT_PRODUCTS},
            price_by_stock=quote,
        )
        self.assertEqual(result.actions, (before, corn, after))
        self.assertFalse(result.changed)
        self.assertEqual(result.decisions[1].kind, "barrier")


if __name__ == "__main__":
    unittest.main(verbosity=2)
