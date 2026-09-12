import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("collection_scale_census", HERE / "collection_scale_census.py")
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)


def action(farmer=None, hands=None, market=None):
    return {
        "farmer": farmer if farmer is not None else ["PASS"],
        "hands": hands if hands is not None else [],
        "market": market if market is not None else [],
    }


class CollectionScaleCensusTests(unittest.TestCase):
    def test_counts_animal_pipeline(self):
        route = [
            action(market=[["BUY_ANIMAL", "GOOSE", 2], ["BUY_ANIMAL", "COW", 1]]),
            action(["PLACE", "GOOSE"], [["PLACE", "COW"]]),
            action(["FEED"], [["CARE"]]),
            action(["HARVEST"], [["COLLECT_FERTILIZER"]], [["SELL", "EGG", 3]]),
        ]
        out = m.census_route(route)
        self.assertEqual(out["animal_buys"], {"GOOSE": 2, "COW": 1, "SHEEP": 0})
        self.assertEqual(out["animal_placements"], {"GOOSE": 1, "COW": 1, "SHEEP": 0})
        self.assertEqual(out["totals"]["harvest_rows"], 1)
        self.assertEqual(out["totals"]["collect_fertilizer_rows"], 1)
        self.assertEqual(out["animal_product_sell_units"]["EGG"], 3)
        self.assertEqual(out["spans"]["buy:GOOSE"], [0, 0])

    def test_executable_market_prefix_only(self):
        market = [["SELL", "EGG", 1] for _ in range(10)] + [["BUY_ANIMAL", "SHEEP", 9]]
        out = m.census_route([action(market=market)], max_orders=10)
        self.assertEqual(out["animal_buys"]["SHEEP"], 0)
        self.assertEqual(out["animal_product_sell_units"]["EGG"], 10)

    def test_malformed_and_zero_quantities_do_not_inflate(self):
        route = [
            action(market=[["BUY_ANIMAL", "GOOSE", -3], ["BUY_ANIMAL", "COW", "x"], []]),
            {"farmer": "bad", "hands": [None, ["HARVEST"]], "market": "bad"},
        ]
        out = m.census_route(route)
        self.assertEqual(out["totals"]["animals_bought"], 0)
        self.assertEqual(out["totals"]["harvest_rows"], 1)

    def test_default_missing_quantity_is_one_for_unit_place(self):
        out = m.census_route([action(["PLACE", "SHEEP"])])
        self.assertEqual(out["animal_placements"]["SHEEP"], 1)

    def test_route_family_ranges(self):
        routes = {
            "a": [action(market=[["BUY_ANIMAL", "GOOSE", 1]]), action(["HARVEST"])],
            "b": [action(market=[["BUY_ANIMAL", "GOOSE", 3]]), action(["HARVEST"]), action(["HARVEST"])],
        }
        out = m.census_routes(routes)
        self.assertEqual(out["route_family_ranges"]["animals_bought"]["spread"], 2)
        self.assertEqual(out["route_family_ranges"]["harvest_rows"]["spread"], 1)
        self.assertEqual(out["animal_buy_ranges"]["GOOSE"]["max"], 3)
        self.assertFalse(out["decision_authority"])

    def test_empty_routes_mapping_rejected(self):
        with self.assertRaises(ValueError):
            m.census_routes({})

    def test_nonpositive_market_cap_rejected(self):
        with self.assertRaises(ValueError):
            m.census_route([], max_orders=0)

    def test_blob_hash(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.py"
            p.write_text("pass\n")
            self.assertEqual(m.git_blob_sha1(p), "41077d71a28ade541d50ce0ceb061272f6ef91e6")

    def test_collection_semantics_are_explicit(self):
        out = m.census_routes({"x": [action(["HARVEST"]), action(["COLLECT_FERTILIZER"])]})
        self.assertEqual(out["collection_semantics"]["animal_product_action"], "HARVEST")
        self.assertEqual(out["collection_semantics"]["fertilizer_action"], "COLLECT_FERTILIZER")


if __name__ == "__main__":
    unittest.main()
