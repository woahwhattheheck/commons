# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from rng_shop_robustness import shop_draw, stable_shop_intervals


class LossReplayReachabilityReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(
            (HERE / "loss_replay_reachability_receipt.json").read_text(encoding="utf-8")
        )

    def test_all_rows_are_engine_final_ticks(self):
        for case in self.receipt["cases"]:
            with self.subTest(episode=case["episode_id"], day=case["day"]):
                self.assertEqual((case["step"] + 1) % case["turns_per_day"], 0)
                self.assertEqual(case["step"] // case["turns_per_day"], case["day"])
                self.assertEqual(case["hour"], case["turns_per_day"] - 1)

    def test_recorded_unlocks_match_exact_cursor_model(self):
        for case in self.receipt["cases"]:
            with self.subTest(episode=case["episode_id"], day=case["day"]):
                self.assertEqual(
                    shop_draw(
                        case["seed"],
                        case["day"],
                        case["pre_action_none_counts"],
                    ),
                    case["recorded_added_shop"],
                )

    def test_distilled_unit_topology_intervals_are_self_consistent(self):
        for case in self.receipt["cases"]:
            topology = case["unit_topology"]
            self.assertEqual(topology["base_empty"], case["pre_action_none_counts"][0])
            self.assertEqual(
                topology["unit_only_interval"],
                [
                    topology["base_empty"] - topology["distinct_fillable_empty_positions"],
                    topology["base_empty"] + topology["distinct_clearable_nonempty_positions"],
                ],
            )

    def test_cash_alone_land_counterfactuals_reach_bakery(self):
        positive_cases = [
            case for case in self.receipt["cases"]
            if "fixed_replay_action_counterfactual" in case
        ]
        self.assertEqual(len(positive_cases), 2)

        for case in positive_cases:
            with self.subTest(episode=case["episode_id"], day=case["day"]):
                land = case["next_land"]
                cf = case["fixed_replay_action_counterfactual"]
                self.assertTrue(land["cash_alone_covers"])
                self.assertGreaterEqual(case["our_money"], land["cost"])
                self.assertEqual(case["actual_unit_none_delta"], 0)
                self.assertEqual(case["actual_rival_unit_none_delta"], 0)
                self.assertEqual(
                    cf["our_pre_eod_none"],
                    case["pre_action_none_counts"][0] + land["locked_tiles"],
                )
                self.assertEqual(
                    cf["rival_pre_eod_none"],
                    case["pre_action_none_counts"][1],
                )
                self.assertEqual(
                    cf["total_pre_eod_none"],
                    cf["our_pre_eod_none"] + cf["rival_pre_eod_none"],
                )
                self.assertEqual(
                    shop_draw(
                        case["seed"],
                        case["day"],
                        (cf["our_pre_eod_none"], cf["rival_pre_eod_none"]),
                    ),
                    cf["predicted_added_shop"],
                )
                self.assertEqual(cf["predicted_added_shop"], "BAKERY")
                lo, hi = cf["stable_total_none_window"]
                self.assertLessEqual(lo, cf["total_pre_eod_none"])
                self.assertGreaterEqual(hi, cf["total_pre_eod_none"])
                intervals = stable_shop_intervals(case["seed"], case["day"], lo, hi)
                self.assertEqual(intervals, ((lo, hi, "BAKERY"),))

    def test_day5_is_not_mislabeled_cash_alone_land_reachable(self):
        day5 = self.receipt["cases"][0]
        self.assertEqual(day5["day"], 5)
        self.assertFalse(day5["next_land"]["cash_alone_covers"])
        self.assertLess(day5["our_money"], day5["next_land"]["cost"])
        self.assertNotIn("fixed_replay_action_counterfactual", day5)


if __name__ == "__main__":
    unittest.main()
