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

    def assert_identity(self, obs, action):
        before = copy.deepcopy(action)
        result = m.apply_carrot_fertilizer(obs, action)
        self.assertIs(result, action)
        self.assertEqual(action, before)
        self.assertEqual(m.REPORT["carrot_fertilize_requests"], 0)

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
                self.assert_identity(
                    observation(tile),
                    {"farmer": command, "hands": [], "market": []},
                )

    def test_requires_carried_fertilizer_and_complete_typed_coverage(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        self.assert_identity(observation(carrot, fertilizer=0), action)
        # step 120 is day 5; coverage through day 7 is already complete.
        covered = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": 7}
        self.assert_identity(observation(covered), action)

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
        self.assert_identity(obs, {"farmer": ["PASS"], "hands": [], "market": []})

    def test_falsey_or_missing_farmer_row_never_synthesizes_pass(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        obs = observation(carrot)
        for value in ([], None, "", 0, False):
            with self.subTest(value=value):
                action = {"farmer": value, "hands": [], "market": []}
                self.assert_identity(obs, action)
        self.assert_identity(obs, {"hands": [], "market": []})

    def test_coercible_fertilizer_and_coverage_types_fail_closed(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        base_tile = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        for fertilizer in (True, 1.0, "1"):
            with self.subTest(field="fertilizer", value=fertilizer):
                self.assert_identity(observation(base_tile, fertilizer=fertilizer), action)
        for coverage in (True, 1.0, "1", None):
            with self.subTest(field="coverage", value=coverage):
                tile = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": coverage}
                self.assert_identity(observation(tile), action)
        missing = {"kind": "PLANT", "crop": "CARROT"}
        self.assert_identity(observation(missing), action)

    def test_player_step_and_coordinate_types_are_strict(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        for field, values in (("player", (True, 0.0, "0")), ("step", (True, 120.0, "120"))):
            for value in values:
                with self.subTest(field=field, value=value):
                    obs = observation(carrot)
                    obs[field] = value
                    self.assert_identity(obs, action)
        for coords in ((True, 0), (0.0, 0), ("0", 0), (0, False), (0, 0.0), (0, "0")):
            with self.subTest(coords=coords):
                obs = observation(carrot)
                obs["farms"][0]["farmer"] = list(coords)
                self.assert_identity(obs, action)

    def test_malformed_actor_shapes_or_cardinality_fail_closed_atomically(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        action = {"farmer": ["PASS"], "hands": [], "market": []}

        obs = observation(carrot)
        obs["private"]["inventories"] = "bad"
        self.assert_identity(obs, action)

        obs = observation(carrot)
        obs["farms"][0]["hands"] = [[0, 0]]
        # Action/inventory cardinality no longer proves which actor the extra state belongs to.
        self.assert_identity(obs, action)

        obs = observation(carrot)
        obs["private"]["inventories"][0] = []
        self.assert_identity(obs, action)

        bad_action = {"farmer": ["PASS"], "hands": None, "market": []}
        self.assert_identity(observation(carrot), bad_action)

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
