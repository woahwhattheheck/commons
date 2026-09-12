"""Exact SELL-row grammar shared by sell-priority and pressure-priority."""
import unittest

from pressure_priority import transform as pressure_transform
from sell_priority import transform as sell_transform


PRICES = {"WHEAT": 25, "MILK": 160, "WOOL": 200}
BASE = {"WHEAT": 25, "MILK": 160, "WOOL": 200}
SLOPE = {"WHEAT": 1, "MILK": 2, "WOOL": 0}


def observation():
    return {
        "step": 10,
        "market": {
            "inventory": {"WHEAT": 0, "MILK": 0, "WOOL": 0},
            "prices": dict(PRICES),
        },
    }


def curve(item, stock, params=None):
    return max(1, BASE[item] - SLOPE[item] * stock)


class MarketPressureGrammarExactnessTests(unittest.TestCase):
    def test_malformed_quantity_aliases_are_barriers_in_both_transforms(self):
        for quantity in (True, 2.0, "2"):
            with self.subTest(quantity=quantity):
                sell_action = {
                    "market": [
                        ["SELL", "WHEAT", 1],
                        ["SELL", "MILK", quantity],
                        ["SELL", "WOOL", 1],
                    ]
                }
                self.assertEqual(
                    sell_transform(sell_action, observation()), sell_action
                )

                pressure_action = {
                    "market": [
                        ["SELL", "WOOL", 1],
                        ["SELL", "MILK", quantity],
                        ["SELL", "WHEAT", 1],
                    ]
                }
                self.assertEqual(
                    pressure_transform(
                        pressure_action, observation(), {}, quote=curve
                    ),
                    pressure_action,
                )

    def test_extra_sell_fields_are_a_barrier_in_both_transforms(self):
        malformed = ["SELL", "MILK", 2, "unexpected"]
        sell_action = {
            "market": [
                ["SELL", "WHEAT", 1],
                list(malformed),
                ["SELL", "WOOL", 1],
            ]
        }
        self.assertEqual(sell_transform(sell_action, observation()), sell_action)

        pressure_action = {
            "market": [
                ["SELL", "WOOL", 1],
                list(malformed),
                ["SELL", "WHEAT", 1],
            ]
        }
        self.assertEqual(
            pressure_transform(pressure_action, observation(), {}, quote=curve),
            pressure_action,
        )

    def test_valid_plain_integer_rows_keep_existing_behavior(self):
        sell_action = {
            "market": [
                ["SELL", "WHEAT", 1],
                ["SELL", "WOOL", 1],
            ]
        }
        self.assertEqual(
            sell_transform(sell_action, observation())["market"],
            [["SELL", "WOOL", 1], ["SELL", "WHEAT", 1]],
        )

        pressure_action = {
            "market": [
                ["SELL", "WOOL", 1],
                ["SELL", "MILK", 2],
                ["SELL", "WHEAT", 1],
            ]
        }
        self.assertEqual(
            pressure_transform(pressure_action, observation(), {}, quote=curve)["market"],
            [["SELL", "MILK", 2], ["SELL", "WHEAT", 1], ["SELL", "WOOL", 1]],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
