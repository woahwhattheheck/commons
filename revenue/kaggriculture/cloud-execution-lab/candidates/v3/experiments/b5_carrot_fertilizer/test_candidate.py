import copy
import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).with_name("candidate.py")
spec = importlib.util.spec_from_file_location("b5_candidate_tested", PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def observation(tile=None, fertilizer=1, step=120, hands=None, hand_inventories=None):
    hands = list(hands or [])
    inventories = [{"FERTILIZER": fertilizer}, *(hand_inventories or [])]
    return {
        "step": step,
        "player": 0,
        "farms": [{"tiles": [[tile]], "farmer": [0, 0], "hands": hands}],
        "private": {"inventories": inventories},
    }


class B5CarrotFertilizerTest(unittest.TestCase):
    def setUp(self):
        m.REPORT["carrot_fertilize_requests"] = 0

    def test_eligible_pass_becomes_fertilize_without_mutating_input(self):
        obs = observation({"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1})
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 2]]}
        before = copy.deepcopy(action)
        result = m.apply_carrot_fertilizer(obs, action)
        self.assertEqual(action, before)
        self.assertEqual(result["farmer"], ["FERTILIZE"])
        self.assertEqual(result["market"], before["market"])
        self.assertEqual(m.REPORT["carrot_fertilize_requests"], 1)

    def test_noncarrot_and_nonpass_are_identity(self):
        for tile, command in (
            ({"kind": "PLANT", "crop": "WHEAT", "fertilized_until_day": -1}, ["PASS"]),
            ({"kind": "PLANT", "crop": "STRAWBERRY", "fertilized_until_day": -1}, ["PASS"]),
            ({"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}, ["WATER"]),
        ):
            with self.subTest(tile=tile, command=command):
                action = {"farmer": command, "hands": [], "market": []}
                self.assertIs(m.apply_carrot_fertilizer(observation(tile), action), action)

    def test_requires_carried_fertilizer_and_incomplete_three_day_coverage(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        self.assertIs(m.apply_carrot_fertilizer(observation(carrot, fertilizer=0), action), action)
        # step 120 is day 5; coverage through day 7 is already complete.
        covered = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": 7}
        self.assertIs(m.apply_carrot_fertilizer(observation(covered), action), action)

    def test_duplicate_workers_on_one_tile_consume_at_most_one_request(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        obs = observation(carrot, hands=[[0, 0]], hand_inventories=[{"FERTILIZER": 1}])
        action = {"farmer": ["PASS"], "hands": [["PASS"]], "market": []}
        result = m.apply_carrot_fertilizer(obs, action)
        self.assertEqual(result["farmer"], ["FERTILIZE"])
        self.assertEqual(result["hands"], [["PASS"]])
        self.assertEqual(m.REPORT["carrot_fertilize_requests"], 1)

    def test_bad_position_fails_closed(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        obs = observation(carrot)
        obs["farms"][0]["farmer"] = [99, 99]
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        self.assertIs(m.apply_carrot_fertilizer(obs, action), action)

    def test_live_baseline_tuple_is_explicit(self):
        self.assertEqual(m.LIVE_BASELINE, {
            "horizon": 8,
            "opening": 0,
            "row_order": True,
            "evening_flush": True,
            "sale_fertilizer": True,
            "cattle_early": True,
        })


if __name__ == "__main__":
    unittest.main()
