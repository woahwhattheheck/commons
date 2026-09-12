import ast
import hashlib
import unittest
from pathlib import Path

import fert_warehouse as F

ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def engine_path() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "reference" / "engine" / "kaggriculture.py"
        if candidate.is_file():
            return candidate
    return None


def load_commit_unit():
    path = engine_path()
    if path is None:
        raise unittest.SkipTest("repository-mounted official engine unavailable")
    source = path.read_bytes()
    if git_blob(source) != ENGINE_BLOB:
        raise AssertionError("official engine source drift")
    tree = ast.parse(source.decode("utf-8"), filename=str(path))
    node = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_commit_unit"), None)
    if node is None:
        raise AssertionError("official engine missing _commit_unit")
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["_commit_unit"]


class FertWarehouseTests(unittest.TestCase):
    def test_no_floor_dump_without_actual_overflow(self):
        private = {"shed": {"FERTILIZER": 60, "WHEAT": 20}, "inventories": [{}, {}]}
        self.assertEqual(F.projected_eod_overflow(private), 0)
        self.assertEqual(F.decide(private, 1), {"mode": "hold", "orders": []})

    def test_floor_liquidation_is_limited_to_projected_overflow(self):
        private = {
            "shed": {"FERTILIZER": 60, "WHEAT": 30},
            "inventories": [{"MELON": 8}, {"FERTILIZER": 7}],
        }
        self.assertEqual(F.projected_eod_overflow(private), 5)
        self.assertEqual(F.decide(private, 1), {
            "mode": "overflow_liquidation",
            "orders": [["SELL", "FERTILIZER", 5]],
        })

    def test_hand_fertilizer_is_not_claimed_sellable(self):
        private = {
            "shed": {"FERTILIZER": 0, "WHEAT": 95},
            "inventories": [{"FERTILIZER": 10}],
        }
        self.assertEqual(F.projected_eod_overflow(private), 5)
        self.assertEqual(F.overflow_liquidation_quantity(private, 1), 0)
        self.assertEqual(F.decide(private, 1), {"mode": "hold", "orders": []})

    def test_revenue_mode_sells_only_shed_fertilizer(self):
        private = {
            "shed": {"FERTILIZER": 9},
            "inventories": [{"FERTILIZER": 50}],
        }
        self.assertEqual(F.revenue_sell_quantity(private, 100), 9)
        self.assertEqual(F.decide(private, 100)["orders"], [["SELL", "FERTILIZER", 9]])

    def test_malformed_numeric_aliases_fail_closed(self):
        private = {"shed": {"FERTILIZER": True}, "inventories": [{}]}
        self.assertEqual(F.decide(private, 1), {"mode": "hold", "orders": []})
        self.assertEqual(F.decide({"shed": {}, "inventories": "bad"}, 100), {"mode": "hold", "orders": []})

    def test_official_engine_floor_sale_is_not_storage(self):
        commit = load_commit_unit()
        farm = {"money": 0}
        private = {"shed": {"FERTILIZER": 2}}
        market = {"inventory": {"FERTILIZER": 10_500}}
        self.assertTrue(commit("SELL", "FERTILIZER", 1, farm, private, market, 100))
        self.assertEqual(private["shed"]["FERTILIZER"], 1)
        self.assertEqual(market["inventory"]["FERTILIZER"], 10_500)
        self.assertTrue(commit("BUY_PRODUCT", "FERTILIZER", 1, farm, private, market, 100))
        self.assertEqual(private["shed"]["FERTILIZER"], 2)
        self.assertEqual(market["inventory"]["FERTILIZER"], 10_499)

    def test_official_engine_positive_price_sale_roundtrips_inventory(self):
        commit = load_commit_unit()
        farm = {"money": 10}
        private = {"shed": {"FERTILIZER": 1}}
        market = {"inventory": {"FERTILIZER": 10_490}}
        self.assertTrue(commit("SELL", "FERTILIZER", 2, farm, private, market, 100))
        self.assertEqual(market["inventory"]["FERTILIZER"], 10_491)
        self.assertTrue(commit("BUY_PRODUCT", "FERTILIZER", 2, farm, private, market, 100))
        self.assertEqual(market["inventory"]["FERTILIZER"], 10_490)

    def test_overflow_liquidation_never_exceeds_shed_fertilizer(self):
        private = {
            "shed": {"FERTILIZER": 3, "WHEAT": 97},
            "inventories": [{"MELON": 50}],
        }
        self.assertEqual(F.projected_eod_overflow(private), 50)
        self.assertEqual(F.overflow_liquidation_quantity(private, 1), 3)


if __name__ == "__main__":
    unittest.main()
