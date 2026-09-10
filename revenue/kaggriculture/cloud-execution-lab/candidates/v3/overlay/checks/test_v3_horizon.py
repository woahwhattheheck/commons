# SPDX-License-Identifier: Apache-2.0
"""Contracts for the measured bounded-horizon residual-reference lane."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from horizon_residual import force_residual_at_horizon  # noqa: E402
import frozen_selected  # noqa: E402
import scheduler  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402


class PureReferenceContracts(unittest.TestCase):
    def test_flag_off_is_exact_canonical_coalescing(self):
        source = [(9, 2), (4, 1), (9, 3)]
        before = list(source)
        result, report = force_residual_at_horizon(source, 7, 12, item="MILK")
        self.assertEqual(result, ((4, 1), (9, 5)))
        self.assertEqual(source, before)
        self.assertFalse(report["enabled"])
        self.assertFalse(report["changed"])

    def test_only_unscheduled_residual_is_appended(self):
        source = [(10, 4), (12, 3), (15, 2)]
        result, report = force_residual_at_horizon(
            source, 5, 18, item="MILK", enabled=True
        )
        self.assertEqual(result, ((10, 4), (12, 3), (15, 2), (18, 5)))
        self.assertEqual(report["reason"], "HORIZON_RESIDUAL_APPENDED")
        self.assertEqual(sum(q for _t, q in result), 14)

    def test_existing_horizon_row_is_coalesced_without_moving_prior_intent(self):
        result, _report = force_residual_at_horizon(
            [(10, 4), (18, 2), (12, 3)], 5, 18, enabled=True
        )
        self.assertEqual(result, ((10, 4), (12, 3), (18, 7)))

    def test_zero_residual_is_identity(self):
        result, report = force_residual_at_horizon(
            [(10, 4), (12, 3)], 0, 18, enabled=True
        )
        self.assertEqual(result, ((10, 4), (12, 3)))
        self.assertFalse(report["changed"])

    def test_active_invalid_inputs_fail_closed_at_caller_boundary(self):
        seller = scheduler.SellScheduler.__new__(scheduler.SellScheduler)
        seller.diagnostics = {}
        result = seller._v3_horizon_reference(
            {"titan_v3": {"horizon_residual": True}},
            [(10, 4)],
            -1,
            18,
            "MILK",
        )
        self.assertEqual(result, ((10, 4),))
        report = seller.diagnostics["v3_horizon_residual"][-1]
        self.assertEqual(report["reason"], "HORIZON_RESIDUAL_ERROR_ValueError")


class PackageWiringContracts(unittest.TestCase):
    def test_config_key_parses_and_ships_off(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIn("horizon_residual", data)
        self.assertIs(data["horizon_residual"], False)
        self.assertIs(Features(**data).horizon_residual, False)

    def test_runtime_transports_only_the_enabled_key(self):
        self.assertFalse(TitanAgent(Features())._v3_active())
        agent = TitanAgent(Features(horizon_residual=True))
        self.assertTrue(agent._v3_active())
        cfg = agent._v3_config()
        self.assertTrue(cfg["horizon_residual"])
        self.assertFalse(cfg["e11_rival_sell"])
        self.assertFalse(cfg["rival_model"])
        self.assertFalse(cfg["e20_hire_guard"])

    def test_both_seller_paths_share_the_same_measured_boundary(self):
        config = {"titan_v3": {"horizon_residual": True}}
        expected = ((10, 4), (12, 3), (18, 5))
        for cls in (scheduler.SellScheduler, frozen_selected.FrozenSelected):
            with self.subTest(cls=cls.__name__):
                seller = cls.__new__(cls)
                seller.diagnostics = {}
                result = seller._v3_horizon_reference(
                    config, [(10, 4), (12, 3)], 5, 18, "MILK"
                )
                self.assertEqual(result, expected)
                self.assertTrue(
                    seller.diagnostics["v3_horizon_residual"][-1]["changed"]
                )

    def test_disabled_boundary_is_the_exact_predecessor_reference(self):
        for cls in (scheduler.SellScheduler, frozen_selected.FrozenSelected):
            seller = cls.__new__(cls)
            seller.diagnostics = {}
            source = [(12, 3), (10, 4), (12, 2)]
            self.assertEqual(
                seller._v3_horizon_reference({}, source, 99, 18, "MILK"),
                ((10, 4), (12, 5)),
            )
            self.assertNotIn("v3_horizon_residual", seller.diagnostics)

    def test_exact_source_seams_are_single_and_distinct(self):
        sched = (ROOT / "scheduler.py").read_text(encoding="utf-8")
        frozen = (ROOT / "frozen_selected.py").read_text(encoding="utf-8")
        self.assertEqual(
            sched.count(
                "reference=self._v3_horizon_reference(config,reference,rem,end,item)"
            ),
            1,
        )
        self.assertEqual(
            frozen.count(
                "reference=self._v3_horizon_reference(config,reference,rem,item_end,item)"
            ),
            1,
        )
        self.assertNotIn(".95*self.single", sched)
        self.assertNotIn(".95*self.single", frozen)


if __name__ == "__main__":
    unittest.main(verbosity=2)
