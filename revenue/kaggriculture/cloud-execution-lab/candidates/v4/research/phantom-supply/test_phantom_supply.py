#!/usr/bin/env python3

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import phantom_supply as ps


HERE = Path(__file__).resolve().parent
ENGINE = HERE.parents[3] / "reference" / "engine" / "kaggriculture.py"


class PhantomSupplyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine, cls.identity = ps.load_engine(ENGINE)

    def test_exact_official_engine_identity(self) -> None:
        self.assertEqual(ps.PINNED_ENGINE_GIT_BLOB, self.identity["git_blob"])
        self.assertEqual(ps.PINNED_ENGINE_SHA256, self.identity["sha256"])

    def test_source_drift_is_rejected(self) -> None:
        data = ENGINE.read_bytes()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "kaggriculture.py"
            path.write_bytes(data + b"\n# drift\n")
            with self.assertRaises(RuntimeError):
                ps.capture_engine(path)

    def test_captured_snapshot_executes_without_path_reopen(self) -> None:
        data = ps.capture_engine(ENGINE)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "captured.py"
            path.write_bytes(data)
            captured = path.read_bytes()
            path.unlink()
            namespace = ps._exec_engine_snapshot(captured)
        self.assertIn("_process_market", namespace)
        self.assertIn("_town_consume", namespace)

    def test_single_buyer_can_cross_zero_for_both_buyable_products(self) -> None:
        for item in ("WHEAT", "FERTILIZER"):
            with self.subTest(item=item):
                case = ps.run_buy_case(
                    self.engine,
                    item=item,
                    starting_inventory=0,
                    buyers=(True, False),
                )
                self.assertEqual(-1, case["ending_inventory"])
                self.assertEqual([1, 0], case["shed_units"])
                self.assertGreater(case["money_spent"][0], 0)
                self.assertEqual(0, case["money_spent"][1])

    def test_two_seats_overdraw_the_last_unit_in_one_lockstep(self) -> None:
        for item in ("WHEAT", "FERTILIZER"):
            with self.subTest(item=item):
                case = ps.run_buy_case(
                    self.engine,
                    item=item,
                    starting_inventory=1,
                    buyers=(True, True),
                )
                self.assertEqual(-1, case["ending_inventory"])
                self.assertEqual([1, 1], case["shed_units"])
                self.assertEqual(case["money_spent"][0], case["money_spent"][1])

    def test_two_seats_can_buy_from_zero_in_one_lockstep(self) -> None:
        for item in ("WHEAT", "FERTILIZER"):
            with self.subTest(item=item):
                case = ps.run_buy_case(
                    self.engine,
                    item=item,
                    starting_inventory=0,
                    buyers=(True, True),
                )
                self.assertEqual(-2, case["ending_inventory"])
                self.assertEqual([1, 1], case["shed_units"])
                self.assertEqual(case["money_spent"][0], case["money_spent"][1])

    def test_town_center_subtracts_through_zero(self) -> None:
        case = ps.run_town_center_zero_stock(self.engine)
        for item in case["town_center_products"]:
            with self.subTest(item=item):
                self.assertEqual(-1, case["ending_inventory"][item])
        self.assertEqual(0, case["ending_inventory"]["FERTILIZER"])

    def test_negative_stock_quotes_remain_finite_and_non_decreasing(self) -> None:
        points = [0, -1, -10, -100, -1000]
        for item in ("WHEAT", "FERTILIZER"):
            with self.subTest(item=item):
                quotes = [ps.next_buy_quote(self.engine, item, inv) for inv in points]
                self.assertTrue(all(type(q) is int and q > 0 for q in quotes))
                self.assertEqual(sorted(quotes), quotes)

    def test_exact_zero_stock_procurement_cost_examples(self) -> None:
        self.assertEqual(125, ps.procurement_cost_from_zero(self.engine, "WHEAT", 1))
        self.assertEqual(1_250, ps.procurement_cost_from_zero(self.engine, "WHEAT", 10))
        self.assertEqual(127_460, ps.procurement_cost_from_zero(self.engine, "WHEAT", 1000))
        self.assertEqual(2_100, ps.procurement_cost_from_zero(self.engine, "FERTILIZER", 1))
        self.assertEqual(21_011, ps.procurement_cost_from_zero(self.engine, "FERTILIZER", 10))
        self.assertEqual(2_200_100, ps.procurement_cost_from_zero(self.engine, "FERTILIZER", 1000))

    def test_full_report_is_self_consistent(self) -> None:
        report = ps.build_report(ENGINE)
        ps._validate_report(report)
        self.assertEqual("titan.v4.phantom-supply.v1", report["schema"])
        self.assertEqual("NOT_ASSESSED", report["boundaries"]["gameplay_ev"])
        self.assertFalse(report["claims"]["buy_product_supply_floor"])
        self.assertFalse(report["claims"]["negative_inventory_blocks_buy_product"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
