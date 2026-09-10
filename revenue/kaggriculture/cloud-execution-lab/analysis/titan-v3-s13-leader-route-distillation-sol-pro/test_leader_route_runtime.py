# SPDX-License-Identifier: Apache-2.0
import copy
import unittest

from leader_route_runtime import LeaderRoutePolicy, structural_signature


def obs(step=24, hands=1, quadrants=1):
    return {
        "step": step,
        "player": 0,
        "farms": [
            {"hands": [{} for _ in range(hands)], "unlocked_quadrants": list(range(quadrants))},
            {"hands": [], "unlocked_quadrants": []},
        ],
    }


def action(tag="BASE", hands=1):
    return {"farmer": [tag], "hands": [[tag] for _ in range(hands)], "market": [[tag]]}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def baseline(observation, configuration=None):
            self.calls.append(observation["step"])
            return action("BASE", len(observation["farms"][0]["hands"]))

        self.baseline = baseline
        self.tape = {
            24: {"signature": {"hands": 1, "quadrants": 1}, "action": action("LEADER", 1)},
            25: {"signature": {"hands": 1, "quadrants": 1}, "action": action("LEADER2", 1)},
        }

    def test_full_replaces_all_components_and_advances_baseline(self):
        policy = LeaderRoutePolicy(self.baseline, self.tape, mode="post24_full")
        self.assertEqual(policy.agent(obs()), action("LEADER", 1))
        self.assertEqual(self.calls, [24])
        self.assertEqual(policy.diagnostics()["activation_count"], 1)

    def test_market_only_keeps_units(self):
        policy = LeaderRoutePolicy(self.baseline, self.tape, mode="post24_market")
        result = policy.agent(obs())
        self.assertEqual(result["farmer"], ["BASE"])
        self.assertEqual(result["hands"], [["BASE"]])
        self.assertEqual(result["market"], [["LEADER"]])

    def test_units_only_keeps_market(self):
        policy = LeaderRoutePolicy(self.baseline, self.tape, mode="post24_units")
        result = policy.agent(obs())
        self.assertEqual(result["farmer"], ["LEADER"])
        self.assertEqual(result["market"], [["BASE"]])

    def test_first_day_is_never_owned(self):
        policy = LeaderRoutePolicy(self.baseline, self.tape, mode="post24_full")
        self.assertEqual(policy.agent(obs(step=23)), action("BASE", 1))
        self.assertTrue(policy.active)

    def test_mismatch_permanently_hands_off_but_baseline_keeps_advancing(self):
        policy = LeaderRoutePolicy(self.baseline, self.tape, mode="post24_full")
        self.assertEqual(policy.agent(obs(step=24, hands=2)), action("BASE", 2))
        self.assertFalse(policy.active)
        self.assertEqual(policy.handoff_step, 24)
        self.assertEqual(policy.agent(obs(step=25)), action("BASE", 1))
        self.assertEqual(self.calls, [24, 25])

    def test_step_zero_resets_prior_handoff(self):
        policy = LeaderRoutePolicy(self.baseline, self.tape, mode="post24_full")
        policy.agent(obs(step=24, hands=2))
        policy.agent(obs(step=0))
        self.assertTrue(policy.active)
        self.assertIsNone(policy.handoff_step)

    def test_market_limit_uses_official_floor(self):
        tape = copy.deepcopy(self.tape)
        tape[24]["action"]["market"] = [["A"], ["B"]]
        policy = LeaderRoutePolicy(self.baseline, tape, mode="post24_market")
        self.assertEqual(policy.agent(obs(), {"maxMarketOrdersPerTurn": 0})["market"], [["A"]])

    def test_inputs_are_not_mutated(self):
        observation = obs()
        tape = copy.deepcopy(self.tape)
        before_obs, before_tape = copy.deepcopy(observation), copy.deepcopy(tape)
        policy = LeaderRoutePolicy(self.baseline, tape, mode="post24_full")
        policy.agent(observation)
        self.assertEqual(observation, before_obs)
        self.assertEqual(tape, before_tape)

    def test_structural_signature_rejects_bad_shape(self):
        with self.assertRaises(ValueError):
            structural_signature({"step": 0})


if __name__ == "__main__":
    unittest.main()
