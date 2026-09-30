import ast
import unittest
from pathlib import Path

import sproutloop


class SproutloopPureTests(unittest.TestCase):
    def test_git_blob_id(self):
        self.assertEqual(sproutloop.git_blob_id(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_market_price_reference_points(self):
        params = {
            "MELON": {"base": 250, "I0": 10000, "T": 300, "below_func": "log", "below_target": .2,
                      "above_func": "sq", "above_target": 3.6},
        }
        self.assertEqual(sproutloop.market_price("MELON", 10000, params), 250)
        self.assertEqual(sproutloop.market_price("MELON", 10100, params), 150)
        self.assertEqual(sproutloop.market_price("MELON", 10130, params), 81)
        self.assertEqual(sproutloop.market_price("MELON", 10131, params), 78)

    def test_cycle_budget(self):
        self.assertEqual(sproutloop.LAST_STEP // sproutloop.CYCLE_CALLBACKS, 179)


class SproutloopContractMutationTests(unittest.TestCase):
    def test_initial_yield_contract_accepts_exact_shape(self):
        tree = ast.parse("def _new_plant(cd):\n    return {'yield_units': 0 if cd['ongoing'] else 1}\n")
        sproutloop._initial_yield_contract(tree)

    def test_initial_yield_contract_rejects_zero_nonongoing(self):
        tree = ast.parse("def _new_plant(cd):\n    return {'yield_units': 0 if cd['ongoing'] else 0}\n")
        with self.assertRaises(ValueError):
            sproutloop._initial_yield_contract(tree)

    def test_harvest_contract_rejects_age_gate(self):
        tree = ast.parse(
            "def _apply_unit_action(op, tile, inv):\n"
            "    if op == 'HARVEST':\n"
            "        if tile['planted_day'] > 0: return\n"
            "        units = tile['yield_units']\n"
            "        tile['yield_units'] = 0\n"
            "        _inv_add(inv, tile['crop'], units)\n"
        )
        with self.assertRaises(ValueError):
            sproutloop._harvest_contract(tree)

    def test_harvest_contract_accepts_no_age_gate(self):
        tree = ast.parse(
            "def _apply_unit_action(op, tile, inv):\n"
            "    if op == 'HARVEST':\n"
            "        units = tile['yield_units']\n"
            "        tile['yield_units'] = 0\n"
            "        _inv_add(inv, tile['crop'], units)\n"
        )
        sproutloop._harvest_contract(tree)

    def test_unit_before_market_rejects_reverse_order(self):
        tree = ast.parse(
            "def interpreter():\n"
            "    _process_market(None, None)\n"
            "    _apply_unit_action()\n"
        )
        with self.assertRaises(ValueError):
            sproutloop._unit_before_market_contract(tree)

    def test_unit_before_market_accepts_order(self):
        tree = ast.parse(
            "def interpreter():\n"
            "    for _ in [0]: _apply_unit_action()\n"
            "    _process_market(None, None)\n"
        )
        self.assertEqual(sproutloop._unit_before_market_contract(tree), "interpreter")


class SproutloopSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        here = Path(__file__).resolve()
        root = next((p for p in here.parents if p.name == "cloud-execution-lab"), None)
        cls.engine = (root / "reference" / "engine" / "kaggriculture.py") if root else None

    def test_current_engine_contract_and_economics(self):
        if self.engine is None or not self.engine.exists():
            self.skipTest("repository engine not available in isolated source-only run")
        report = sproutloop.analyze_engine_bytes(self.engine.read_bytes())
        rows = {r["crop"]: r for r in report["crops"]}
        self.assertEqual(set(rows), {"WHEAT", "CARROT", "MELON"})
        self.assertEqual(rows["MELON"]["base_spread"], 170)
        self.assertEqual(rows["MELON"]["profitable_consecutive_quotes_capped_719"], 131)
        self.assertEqual(rows["MELON"]["market_only_gross_profit_at_cycle_cap"], 14868)
        self.assertEqual(rows["CARROT"]["profitable_consecutive_quotes_capped_719"], 158)
        self.assertEqual(rows["WHEAT"]["single_worker_profitable_units"], 179)
        self.assertFalse(report["decision_authority"])

    def test_engine_blob_constant_is_full_sha1(self):
        self.assertRegex(sproutloop.EXPECTED_ENGINE_BLOB, r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
