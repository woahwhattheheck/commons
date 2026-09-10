# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from materialize_pressure_certificate import (
    SCHEMA,
    git_blob_sha1,
    materialize,
    patch_source,
)


PARENT_FIXTURE = '''from __future__ import annotations
import copy
from collections.abc import Mapping
from typing import Any, Callable
from sell_priority import PRODUCTS, _quote

PriceFunction = Callable[[str, int, Mapping | None], int | float]
MAX_SCORING_UNITS = 256


def lot_pressure(order, market, quote):
    if not isinstance(order, list) or len(order) != 3 or order[0] != "SELL":
        return None
    item, quantity = order[1], order[2]
    if item not in PRODUCTS or quantity != 1:
        return None
    stock = market["inventory"][item]
    return max(0.0, float(quote(item, stock, None) - quote(item, stock + 1, None)))


def transform(action: dict, observation: Mapping,
              configuration: Mapping | None = None, *, quote: PriceFunction,
              rival_supply: Mapping[str, int] | None = None) -> dict:
    """Sort contiguous supported SELL lots by public rival-flow delay exposure.

    Preserve all orders, quantities, duplicate lots, economic barriers,
    executable-prefix boundaries and unit instructions. Known empty slots can
    move only inside a wholly eligible sale-only prefix.
    """
    if not isinstance(action, dict) or not isinstance(action.get("market", []), list):
        raise ValueError("parent policy must return an object with a market list")
    result = copy.deepcopy(action)
    market = observation["market"]
    orders = result["market"]
    scores = [lot_pressure(order, market, quote) for order in orders]
    start = 0
    end = len(orders)
    while start < end:
        if scores[start] is None:
            start += 1
            continue
        stop = start + 1
        while stop < end and scores[stop] is not None:
            stop += 1
        ranked = sorted(zip(orders[start:stop], scores[start:stop]), key=lambda p: -p[1])
        orders[start:stop] = [order for order, _ in ranked]
        start = stop
    return result
'''

SELL_PRIORITY_STUB = '''PRODUCTS = frozenset(("TOMATO", "MILK"))
def _quote(order, prices):
    return prices.get(order[1])
'''

MECHANICS_STUB = '''def market_price(item, inventory, params=None):
    del params
    return {"TOMATO": 60, "MILK": 169}[item] - max(0, inventory - 10000)
'''


class MaterializerTests(unittest.TestCase):
    def test_patch_is_exact_default_off_and_compiles(self):
        patched = patch_source(PARENT_FIXTURE)
        compile(patched, "pressure_priority.py", "exec")
        self.assertIn("from pressure_zero_exposure import stable_certified_partition", patched)
        self.assertIn("zero_exposure_bound: int | None = None", patched)
        self.assertIn("if zero_exposure_bound is None:", patched)
        self.assertEqual(patched.count("stable_certified_partition("), 1)

    def test_missing_or_duplicate_anchor_rejects(self):
        with self.assertRaisesRegex(ValueError, "import anchor count"):
            patch_source(PARENT_FIXTURE.replace("from sell_priority import PRODUCTS, _quote", ""))
        duplicate = PARENT_FIXTURE + "\nfrom sell_priority import PRODUCTS, _quote\n"
        with self.assertRaisesRegex(ValueError, "import anchor count"):
            patch_source(duplicate)

    def test_materializer_binds_inputs_and_emits_strict_receipt(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "pressure_priority_parent.py"
            helper = root / "pressure_zero_exposure.py"
            mechanics = root / "mechanics.py"
            output = root / "pressure_priority.py"
            receipt_path = root / "RECEIPT.json"
            source.write_text(PARENT_FIXTURE, encoding="utf-8")
            helper.write_text(Path("pressure_zero_exposure.py").read_text(), encoding="utf-8")
            mechanics.write_text(MECHANICS_STUB, encoding="utf-8")
            expected = git_blob_sha1(source.read_bytes())
            expected_mechanics = git_blob_sha1(mechanics.read_bytes())
            receipt = materialize(
                source,
                helper,
                mechanics,
                output,
                receipt_path,
                expected_parent_git_blob_sha1=expected,
                expected_mechanics_git_blob_sha1=expected_mechanics,
            )
            self.assertEqual(receipt["schema"], SCHEMA)
            self.assertTrue(receipt["certificate_mode_default_off"])
            self.assertFalse(receipt["canonical_runtime_mutated"])
            self.assertEqual(json.loads(receipt_path.read_text()), receipt)
            self.assertEqual(source.read_text(), PARENT_FIXTURE)
            json.dumps(receipt, allow_nan=False)

    def test_parent_blob_drift_rejects_before_output(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.py"
            helper = root / "helper.py"
            mechanics = root / "mechanics.py"
            output = root / "output.py"
            receipt = root / "receipt.json"
            source.write_text(PARENT_FIXTURE, encoding="utf-8")
            helper.write_text(Path("pressure_zero_exposure.py").read_text(), encoding="utf-8")
            mechanics.write_text(MECHANICS_STUB, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "parent git blob drift"):
                materialize(
                    source,
                    helper,
                    mechanics,
                    output,
                    receipt,
                    expected_parent_git_blob_sha1="0" * 40,
                    expected_mechanics_git_blob_sha1=git_blob_sha1(mechanics.read_bytes()),
                )
            self.assertFalse(output.exists())
            self.assertFalse(receipt.exists())

    def test_output_hardlink_alias_is_rejected(self):
        if not hasattr(os, "link"):
            self.skipTest("hard links unavailable")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.py"
            helper = root / "helper.py"
            mechanics = root / "mechanics.py"
            output = root / "output.py"
            receipt = root / "receipt.json"
            source.write_text(PARENT_FIXTURE, encoding="utf-8")
            helper.write_text(Path("pressure_zero_exposure.py").read_text(), encoding="utf-8")
            mechanics.write_text(MECHANICS_STUB, encoding="utf-8")
            os.link(source, output)
            with self.assertRaisesRegex(ValueError, "output aliases an input"):
                materialize(
                    source,
                    helper,
                    mechanics,
                    output,
                    receipt,
                    expected_parent_git_blob_sha1=git_blob_sha1(source.read_bytes()),
                    expected_mechanics_git_blob_sha1=git_blob_sha1(mechanics.read_bytes()),
                )

    def test_materialized_postimage_kills_plateau_counterexample(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "pressure_priority_parent.py"
            helper = root / "pressure_zero_exposure.py"
            mechanics = root / "mechanics.py"
            output = root / "pressure_priority.py"
            receipt = root / "receipt.json"
            (root / "sell_priority.py").write_text(SELL_PRIORITY_STUB, encoding="utf-8")
            source.write_text(PARENT_FIXTURE, encoding="utf-8")
            helper.write_text(Path("pressure_zero_exposure.py").read_text(), encoding="utf-8")
            mechanics.write_text(MECHANICS_STUB, encoding="utf-8")
            materialize(
                source,
                helper,
                mechanics,
                output,
                receipt,
                expected_parent_git_blob_sha1=git_blob_sha1(source.read_bytes()),
                expected_mechanics_git_blob_sha1=git_blob_sha1(mechanics.read_bytes()),
            )

            sys.path.insert(0, str(root))
            try:
                spec = importlib.util.spec_from_file_location("materialized_pressure", output)
                self.assertIsNotNone(spec)
                self.assertIsNotNone(spec.loader)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            finally:
                sys.path.remove(str(root))
                sys.modules.pop("pressure_zero_exposure", None)
                sys.modules.pop("sell_priority", None)

            stock = 9999
            curves = {
                "TOMATO": [60, 60, 57],
                "MILK": [169, 160, 150],
            }

            def quote(item, at, _params):
                return curves[item][at - stock]

            observation = {
                "market": {
                    "prices": {"TOMATO": 60, "MILK": 169},
                    "inventory": {"TOMATO": stock, "MILK": stock},
                    "params": None,
                }
            }
            parent = {
                "market": [["SELL", "TOMATO", 1], ["SELL", "MILK", 1]]
            }
            proxy = module.transform(parent, observation, quote=quote)
            repaired = module.transform(
                parent,
                observation,
                quote=quote,
                zero_exposure_bound=2,
            )
            self.assertEqual(proxy["market"][0][1], "MILK")
            self.assertEqual(repaired, parent)
            self.assertEqual(parent["market"][0][1], "TOMATO")


if __name__ == "__main__":
    unittest.main()
