from __future__ import annotations

import unittest

from b5_current_safe import B5CurrentABI


class B5ReceiptParityTests(unittest.TestCase):
    def test_jit_activation_retains_submitted_public_step(self):
        tiles = [[{} for _ in range(10)] for _ in range(10)]
        tiles[2][2] = {
            "kind": "PLANT",
            "crop": "CARROT",
            "planted_day": 0,
            "yield_units": 0,
            "fertilized_until_day": 1,
            "watered_today": False,
        }
        observation = {
            "step": 50,
            "player": 0,
            "farms": [
                {"farmer": [2, 2], "hands": [], "tiles": tiles},
                {"farmer": [0, 0], "hands": [], "tiles": []},
            ],
            "private": {"inventories": [{"FERTILIZER": 1}], "shed": {}},
        }
        selected = {"farmer": ["PASS"], "hands": [], "market": []}
        next_authored = {"farmer": ["WATER"], "hands": [], "market": []}

        result, report = B5CurrentABI(jit=True).transform(
            observation,
            selected,
            next_authored=next_authored,
            next_authored_step=51,
        )

        self.assertEqual(result["farmer"], ["FERTILIZE"])
        self.assertEqual(len(report["jit_activations"]), 1)
        activation = report["jit_activations"][0]
        self.assertEqual(activation["step"], 50)
        self.assertEqual(activation["worker"], 0)
        self.assertEqual(activation["crop"], "CARROT")
        self.assertEqual(activation["position"], [2, 2])
        self.assertEqual(activation["fertilizer_before"], 1)
        self.assertEqual(
            activation["reason"], "literal_pass_before_same_worker_yield_water"
        )


if __name__ == "__main__":
    unittest.main()
