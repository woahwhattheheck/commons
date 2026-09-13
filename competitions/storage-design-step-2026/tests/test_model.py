import json
import unittest
from decimal import Decimal
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "model"))
from production_model import ModelError, compare, parse_scenario


def fixture(name):
    return json.loads((HERE / "model" / name).read_text(encoding="utf-8"))


class ProductionModelTests(unittest.TestCase):
    def test_synthetic_comparison_is_exact_and_reduces_exposure(self):
        result = compare(
            parse_scenario(fixture("example_baseline.synthetic.json")),
            parse_scenario(fixture("example_candidate.synthetic.json")),
        )
        self.assertEqual(result["baseline"]["conversion_cost_usd"], "11194.00")
        self.assertEqual(result["candidate"]["conversion_cost_usd"], "10142.00")
        self.assertEqual(result["delta"]["conversion_cost_usd"], "-1052.00")
        self.assertEqual(result["delta"]["conversion_cost_reduction_pct"], "9.40")
        self.assertLess(Decimal(result["candidate"]["single_source_value_pct"]), Decimal(result["baseline"]["single_source_value_pct"]))
        self.assertIn("Synthetic scenario only", result["truth_boundary"])

    def test_rejects_money_float_bool_aliases_and_non_synthetic_authority(self):
        raw = fixture("example_baseline.synthetic.json")
        raw["components"][0]["unit_cost_usd"] = 2.5
        with self.assertRaises(ModelError):
            parse_scenario(raw)

        raw = fixture("example_baseline.synthetic.json")
        raw["components"][0]["quantity"] = True
        with self.assertRaises(ModelError):
            parse_scenario(raw)

        raw = fixture("example_baseline.synthetic.json")
        raw["authority"] = "QUOTE_BACKED"
        with self.assertRaises(ModelError):
            parse_scenario(raw)

    def test_rejects_duplicate_component_identity_and_rating_mismatch(self):
        raw = fixture("example_baseline.synthetic.json")
        raw["components"][1]["name"] = raw["components"][0]["name"].upper()
        with self.assertRaises(ModelError):
            parse_scenario(raw)

        base = parse_scenario(fixture("example_baseline.synthetic.json"))
        raw = fixture("example_candidate.synthetic.json")
        raw["energy_kwh"] = "120"
        with self.assertRaises(ModelError):
            compare(base, parse_scenario(raw))


if __name__ == "__main__":
    unittest.main()
