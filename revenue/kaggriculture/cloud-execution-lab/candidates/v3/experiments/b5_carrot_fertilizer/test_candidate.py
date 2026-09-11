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


def carrot(coverage=-1):
    return {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": coverage}


def pass_action(*, hands=None):
    return {"farmer": ["PASS"], "hands": list(hands or []), "market": [["SELL", "MILK", 2]]}


class B5CarrotFertilizerTest(unittest.TestCase):
    def setUp(self):
        m.REPORT["carrot_fertilize_requests"] = 0

    def test_eligible_pass_becomes_fertilize_without_mutating_input(self):
        obs = observation(carrot())
        action = pass_action()
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
            (carrot(), ["WATER"]),
        ):
            with self.subTest(tile=tile, command=command):
                action = {"farmer": command, "hands": [], "market": []}
                self.assertIs(m.apply_carrot_fertilizer(observation(tile), action), action)

    def test_requires_carried_fertilizer_and_incomplete_three_day_coverage(self):
        action = pass_action()
        self.assertIs(m.apply_carrot_fertilizer(observation(carrot(), fertilizer=0), action), action)
        # step 120 is day 5; coverage through day 7 is already complete.
        self.assertIs(m.apply_carrot_fertilizer(observation(carrot(7)), action), action)

    def test_duplicate_workers_on_one_tile_consume_at_most_one_request(self):
        obs = observation(carrot(), hands=[[0, 0]], hand_inventories=[{"FERTILIZER": 1}])
        action = pass_action(hands=[["PASS"]])
        result = m.apply_carrot_fertilizer(obs, action)
        self.assertEqual(result["farmer"], ["FERTILIZE"])
        self.assertEqual(result["hands"], [["PASS"]])
        self.assertEqual(m.REPORT["carrot_fertilize_requests"], 1)

    def test_bad_position_fails_closed(self):
        obs = observation(carrot())
        obs["farms"][0]["farmer"] = [99, 99]
        action = pass_action()
        self.assertIs(m.apply_carrot_fertilizer(obs, action), action)

    def test_falsey_or_malformed_farmer_command_never_becomes_pass(self):
        obs = observation(carrot())
        for bad in (None, [], "", False):
            with self.subTest(bad=bad):
                action = {"farmer": bad, "hands": [], "market": []}
                self.assertIs(m.apply_carrot_fertilizer(obs, action), action)
        missing = {"hands": [], "market": []}
        self.assertIs(m.apply_carrot_fertilizer(obs, missing), missing)

    def test_fertilizer_quantity_is_strict_nonbool_integer(self):
        action = pass_action()
        for bad in (True, 1.0, 3.7, "1", None, -1):
            with self.subTest(bad=bad):
                self.assertIs(
                    m.apply_carrot_fertilizer(observation(carrot(), fertilizer=bad), action),
                    action,
                )

    def test_fertilizer_coverage_must_be_present_strict_integer(self):
        action = pass_action()
        for bad in (True, 1.0, "1", None):
            with self.subTest(bad=bad):
                self.assertIs(
                    m.apply_carrot_fertilizer(observation(carrot(bad)), action),
                    action,
                )
        missing = {"kind": "PLANT", "crop": "CARROT"}
        self.assertIs(m.apply_carrot_fertilizer(observation(missing), action), action)

    def test_step_and_player_require_strict_nonnegative_integers(self):
        action = pass_action()
        for bad in (True, 120.0, "120", None, -1):
            with self.subTest(field="step", bad=bad):
                obs = observation(carrot())
                obs["step"] = bad
                self.assertIs(m.apply_carrot_fertilizer(obs, action), action)
        for bad in (True, 0.0, "0", None, -1):
            with self.subTest(field="player", bad=bad):
                obs = observation(carrot())
                obs["player"] = bad
                self.assertIs(m.apply_carrot_fertilizer(obs, action), action)

    def test_coordinates_require_strict_integer_pair(self):
        action = pass_action()
        for bad_position in ([True, 0], [0.0, 0], ["0", 0], [None, 0], [0], None):
            with self.subTest(position=bad_position):
                obs = observation(carrot())
                obs["farms"][0]["farmer"] = bad_position
                self.assertIs(m.apply_carrot_fertilizer(obs, action), action)

    def test_malformed_worker_carriers_preserve_exact_parent_identity(self):
        action = pass_action()

        obs = observation(carrot())
        obs["private"]["inventories"] = None
        self.assertIs(m.apply_carrot_fertilizer(obs, action), action)

        obs = observation(carrot())
        obs["private"]["inventories"] = [None]
        self.assertIs(m.apply_carrot_fertilizer(obs, action), action)

        obs = observation(carrot())
        obs["farms"][0]["hands"] = None
        self.assertIs(m.apply_carrot_fertilizer(obs, action), action)

        malformed_hands = {"farmer": ["PASS"], "hands": None, "market": []}
        self.assertIs(m.apply_carrot_fertilizer(observation(carrot()), malformed_hands), malformed_hands)

        obs = observation(carrot(), hands=[[0, 0]], hand_inventories=[])
        mismatch_action = pass_action(hands=[["PASS"]])
        self.assertIs(m.apply_carrot_fertilizer(obs, mismatch_action), mismatch_action)

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
