# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
import unittest

import optimizer_witness as witness
import transcription_audit as audit


class ProxyOptimizer:
    @staticmethod
    def absorption(item, step, shops, config):
        return witness.absorption(item, step)

    @staticmethod
    def optimize_lot(**kwargs):
        report = witness.optimize_strict(
            kwargs["item"],
            kwargs["quantity"],
            now=kwargs["now"],
            end=kwargs["dates"][-1],
            inventory=kwargs["inventory"],
            rival=kwargs["rival_quantity"],
        )
        info = deepcopy(report)
        info.pop("optimizer_internal_key", None)
        info.pop("total_relative_gain", None)
        info.pop("scenario_deltas", None)
        info.pop("dates", None)
        return tuple(tuple(row) for row in report["plan"]), info


class BadPlanOptimizer(ProxyOptimizer):
    @staticmethod
    def optimize_lot(**kwargs):
        plan, info = ProxyOptimizer.optimize_lot(**kwargs)
        return ((kwargs["now"], kwargs["quantity"]),), info


def proxy_mechanics():
    return SimpleNamespace(
        PRODUCTS=["WHEAT", *witness.PRODUCT_ORDER, "FERTILIZER"],
        MARKET_I0=witness.MARKET_I0,
        PRICE_FLOOR=witness.PRICE_FLOOR,
        HINGE_GAIN=witness.HINGE_GAIN,
        SHOPS=deepcopy(witness.SHOPS),
        MARKET_PARAMS=deepcopy(witness.MARKET_PARAMS),
        market_price=lambda item, inventory, params=None: witness.market_price(item, inventory),
    )


class TranscriptionAuditTests(unittest.TestCase):
    def kwargs(self):
        return dict(
            inventories=(10000,),
            rival_quantities=(4,),
            quantities=(3,),
            products=("MILK",),
            now=10,
            end=18,
            price_inventories=(9999, 10000, 10001),
            absorption_steps=(0, 4, 10, 12, 18, 24),
        )

    def test_matching_proxy_passes_declared_grid(self):
        value = audit.audit_modules(proxy_mechanics(), ProxyOptimizer, **self.kwargs())
        self.assertTrue(value["parity"])
        self.assertEqual(value["checks"]["optimizer_cases"], 1)
        self.assertEqual(value["classification"], "FULL_GRID_CANONICAL_TRANSCRIPTION_PARITY")

    def test_market_parameter_drift_fails_closed(self):
        mechanics = proxy_mechanics()
        mechanics.MARKET_PARAMS["MILK"]["base"] += 1
        with self.assertRaisesRegex(audit.TranscriptionError, "MARKET_PARAMS"):
            audit.audit_modules(mechanics, ProxyOptimizer, **self.kwargs())

    def test_optimizer_plan_drift_fails_closed(self):
        with self.assertRaisesRegex(audit.TranscriptionError, "plan"):
            audit.audit_modules(proxy_mechanics(), BadPlanOptimizer, **self.kwargs())


if __name__ == "__main__":
    unittest.main(verbosity=2)
