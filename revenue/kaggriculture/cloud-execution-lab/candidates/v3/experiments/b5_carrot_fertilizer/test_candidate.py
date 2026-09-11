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

    def assertIdentity(self, obs, action):
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
                self.assertIdentity(observation(tile), {"farmer": command, "hands": [], "market": []})

    def test_requires_carried_fertilizer_and_incomplete_three_day_coverage(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        self.assertIdentity(observation(carrot, fertilizer=0), {"farmer": ["PASS"], "hands": [], "market": []})
        covered = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": 7}
        self.assertIdentity(observation(covered), {"farmer": ["PASS"], "hands": [], "market": []})

    def test_duplicate_workers_on_one_tile_consume_at_most_one_request(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        obs = observation(carrot, hands=[[0, 0]], hand_inventories=[{"FERTILIZER": 1}])
        action = {"farmer": ["PASS"], "hands": [["PASS"]], "market": []}
        result = m.apply_carrot_fertilizer(obs, action)
        self.assertEqual(result["farmer"], ["FERTILIZE"])
        self.assertEqual(result["hands"], [["PASS"]])
        self.assertEqual(m.REPORT["carrot_fertilize_requests"], 1)

    def test_bad_position_is_identity(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        obs = observation(carrot)
        obs["farms"][0]["farmer"] = [99, 99]
        self.assertIdentity(obs, {"farmer": ["PASS"], "hands": [], "market": []})

    def test_atomic_validation_rejects_later_malformed_actor(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        # Actor 0 is eligible, but a later explicit PASS actor is out of bounds.
        obs = observation(carrot, hands=[[99, 99]], hand_inventories=[{"FERTILIZER": 1}])
        self.assertIdentity(obs, {"farmer": ["PASS"], "hands": [["PASS"]], "market": []})
        # Same partial-mutation killer with a malformed later inventory mapping.
        obs = observation(carrot, hands=[[0, 0]], hand_inventories=[None])
        self.assertIdentity(obs, {"farmer": ["PASS"], "hands": [["PASS"]], "market": []})
        # A malformed later explicit command is also whole-action invalid, not ignorable.
        obs = observation(carrot, hands=[[0, 0]], hand_inventories=[{"FERTILIZER": 1}])
        self.assertIdentity(obs, {"farmer": ["PASS"], "hands": [[None]], "market": []})

    def test_falsey_or_missing_command_never_fabricates_pass(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        for value in (None, [], ""):
            with self.subTest(value=value):
                self.assertIdentity(observation(carrot), {"farmer": value, "hands": [], "market": []})
        self.assertIdentity(observation(carrot), {"hands": [], "market": []})

    def test_noncanonical_integer_fields_fail_closed(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        cases = []
        for bad in (True, 1.0, "1"):
            obs = observation(carrot, fertilizer=bad); cases.append(obs)
            obs = observation(carrot); obs["step"] = bad; cases.append(obs)
            obs = observation(carrot); obs["player"] = bad; cases.append(obs)
            obs = observation(carrot); obs["farms"][0]["farmer"] = [bad, 0]; cases.append(obs)
            obs = observation(carrot); obs["farms"][0]["farmer"] = [0, bad]; cases.append(obs)
        for obs in cases:
            with self.subTest(obs=obs):
                self.assertIdentity(obs, action)

    def test_missing_or_malformed_coverage_fails_closed(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        for coverage in (None, True, 1.0, "1"):
            tile = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": coverage}
            with self.subTest(coverage=coverage):
                self.assertIdentity(observation(tile), action)
        tile = {"kind": "PLANT", "crop": "CARROT"}
        self.assertIdentity(observation(tile), action)

    def test_malformed_shapes_fail_closed(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        variants = []
        obs = observation(carrot); obs["private"]["inventories"] = None; variants.append(obs)
        obs = observation(carrot); obs["farms"][0]["hands"] = None; variants.append(obs)
        obs = observation(carrot); obs["farms"][0]["tiles"] = None; variants.append(obs)
        obs = observation(carrot); obs["private"]["inventories"] = []; variants.append(obs)
        for obs in variants:
            with self.subTest(obs=obs):
                self.assertIdentity(obs, action)

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
