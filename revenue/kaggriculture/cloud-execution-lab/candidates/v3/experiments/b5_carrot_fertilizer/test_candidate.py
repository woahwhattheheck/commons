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
        self.assertIs(m.apply_carrot_fertilizer(obs, action), action)
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
                action = {"farmer": command, "hands": [], "market": []}
                self.assert_identity(observation(tile), action)

    def test_requires_carried_fertilizer_and_incomplete_three_day_coverage(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        self.assert_identity(observation(carrot, fertilizer=0), action)
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
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        self.assert_identity(obs, action)

    def test_falsey_or_malformed_parent_command_never_becomes_pass(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        for command in ([], None, "", False):
            with self.subTest(command=command):
                self.setUp()
                action = {"farmer": command, "hands": [], "market": []}
                self.assert_identity(observation(carrot), action)

    def test_integer_like_values_fail_closed(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        for value in (True, 1.0, "1", None):
            with self.subTest(field="fertilizer", value=value):
                self.setUp()
                self.assert_identity(observation(carrot, fertilizer=value), action)
        for value in (True, 7.0, "7", None):
            with self.subTest(field="coverage", value=value):
                self.setUp()
                tile = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": value}
                self.assert_identity(observation(tile), action)
        missing = {"kind": "PLANT", "crop": "CARROT"}
        self.setUp()
        self.assert_identity(observation(missing), action)
        for value in (True, 120.0, "120", None):
            with self.subTest(field="step", value=value):
                self.setUp()
                self.assert_identity(observation(carrot, step=value), action)
        for value in (True, 0.0, "0", None):
            with self.subTest(field="player", value=value):
                self.setUp()
                obs = observation(carrot)
                obs["player"] = value
                self.assert_identity(obs, action)
        for position in ([True, 0], [0.0, 0], ["0", 0], [None, 0]):
            with self.subTest(field="position", value=position):
                self.setUp()
                obs = observation(carrot)
                obs["farms"][0]["farmer"] = position
                self.assert_identity(obs, action)

    def test_malformed_shapes_fail_closed(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        cases = []
        obs = observation(carrot); obs["private"] = None; cases.append(obs)
        obs = observation(carrot); obs["private"]["inventories"] = None; cases.append(obs)
        obs = observation(carrot); obs["private"]["inventories"][0] = None; cases.append(obs)
        obs = observation(carrot); obs["farms"][0]["hands"] = None; cases.append(obs)
        obs = observation(carrot); obs["farms"][0]["tiles"] = None; cases.append(obs)
        for obs in cases:
            with self.subTest(obs=obs):
                self.setUp()
                self.assert_identity(obs, action)
        for broken in (
            {"farmer": ["PASS"], "hands": None, "market": []},
            {"farmer": ["PASS"], "market": []},
            {"hands": [], "market": []},
        ):
            with self.subTest(action=broken):
                self.setUp()
                self.assert_identity(observation(carrot), broken)

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
