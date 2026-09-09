# SPDX-License-Identifier: Apache-2.0
"""Execute the real frozen and ablated optimizers on a predecessor-discriminating market path.

The concrete CARROT witness was independently found by SOL-CALIBER in later-colliding
PR #11831 and is preserved here with explicit authorship credit.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest

import materialize as target

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "runtime" / "variants" / "v2"
HEAD = "1" * 40


class RealSchedulerWitnessTests(unittest.TestCase):
    def test_future_stress_scenarios_alone_veto_real_carrot_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "ablation"
            target.materialize(
                SOURCE,
                output,
                "ablation",
                root / "receipt.json",
                HEAD,
            )
            frozen_plan, frozen_report = _optimize(SOURCE, "fulcrum_frozen_v2")
            ablated_plan, ablated_report = _optimize(
                output / "runtime",
                "fulcrum_ablated_v2",
            )

        reference = ((542, 18), (550, 2))
        self.assertEqual(reference, frozen_plan)
        self.assertEqual(list(target.V2_SCENARIOS), list(frozen_report["scenarios"]))
        self.assertEqual(0.0, frozen_report["worst_relative_gain"])

        self.assertEqual(((542, 13),), ablated_plan)
        self.assertEqual(
            list(target.ABLATION_SCENARIOS),
            list(ablated_report["scenarios"]),
        )
        self.assertEqual(1.0, ablated_report["worst_relative_gain"])
        gains = [
            scenario["relative_value"] - scenario["reference_relative_value"]
            for scenario in ablated_report["scenarios"].values()
        ]
        self.assertEqual([4.0, 1.0, 1.0], gains)
        self.assertTrue(all(gain > 0 for gain in gains))


def _load_scheduler(root: Path, module_name: str) -> types.ModuleType:
    scheduler_path = root / "scheduler.py"
    spec = importlib.util.spec_from_file_location(module_name, scheduler_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot import {scheduler_path}")
    module = importlib.util.module_from_spec(spec)
    previous_path = list(sys.path)
    old_mechanics = sys.modules.pop("mechanics", None)
    try:
        sys.path.insert(0, str(root))
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = previous_path
        sys.modules.pop("mechanics", None)
        if old_mechanics is not None:
            sys.modules["mechanics"] = old_mechanics
    return module


def _optimize(root: Path, module_name: str):
    module = _load_scheduler(root, module_name)
    return module.optimize_lot(
        item="CARROT",
        quantity=20,
        inventory=10055,
        params=module.m.MARKET_PARAMS,
        shops=["PET_CAFE"],
        config={
            "townShopSellInterval": 4,
            "townCenterSellInterval": 24,
        },
        now=542,
        dates=[542, 546, 550],
        reference=((542, 18), (550, 2)),
        rival_quantity=3,
        minimum_now=0,
        capacity_ok=None,
        last=718,
    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
