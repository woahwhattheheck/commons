import copy
import unittest

from terminal_fertilizer import make_agent


STANDARD = {"episodeSteps": 720, "turnsPerDay": 24}


def obs(step=716, player=0, pos=(4, 4), fert=True, animal="COW", hands=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[pos[1]][pos[0]] = {
        "kind": "PASTURE",
        "animal": animal,
        "fertilizer_available": fert,
    }
    hand_positions = [] if hands is None else [list(value) for value in hands]
    for hand_pos in hand_positions:
        x, y = hand_pos
        tiles[y][x] = {
            "kind": "COOP",
            "animal": "GOOSE",
            "fertilizer_available": True,
        }
    return {
        "step": step,
        "player": player,
        "farms": [{"tiles": tiles, "farmer": list(pos), "hands": hand_positions}],
    }


def parent_with(action):
    frozen = copy.deepcopy(action)

    def parent(_obs, _cfg=None):
        return copy.deepcopy(frozen)

    return parent


class T(unittest.TestCase):
    def test_collects_literal_pass_on_exact_terminal_steps(self):
        for step in (716, 717):
            a = make_agent(parent_with({"farmer": ["PASS"], "hands": [], "market": []}))
            self.assertEqual(a(obs(step=step), STANDARD)["farmer"], ["COLLECT_FERTILIZER"])

    def test_outside_window_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 1]]}
        a = make_agent(parent_with(action))
        self.assertEqual(a(obs(step=715), STANDARD), action)

    def test_never_overrides_non_pass(self):
        for cmd in (["CARE"], ["FEED"], ["DROP"], ["PLACE", "MILK", 1], ["HARVEST"]):
            a = make_agent(parent_with({"farmer": cmd, "hands": [], "market": []}))
            self.assertEqual(a(obs(), STANDARD)["farmer"], cmd)

    def test_missing_empty_or_malformed_parent_commands_are_identity(self):
        cases = (
            {"hands": [], "market": []},
            {"farmer": None, "hands": [], "market": []},
            {"farmer": [], "hands": [], "market": []},
            {"farmer": [False], "hands": [], "market": []},
            {"farmer": ["PASS"], "market": []},
            {"farmer": ["PASS"], "hands": [None], "market": []},
            {"farmer": ["PASS"], "hands": [[]], "market": []},
        )
        for action in cases:
            with self.subTest(action=action):
                a = make_agent(parent_with(action))
                observation = obs(hands=[(5, 5)]) if action.get("hands") else obs()
                self.assertEqual(a(observation, STANDARD), action)

    def test_action_hand_cardinality_must_match_represented_hands(self):
        observation = obs(hands=[(5, 5)])
        too_few = {"farmer": ["PASS"], "hands": [], "market": []}
        a = make_agent(parent_with(too_few))
        self.assertEqual(a(observation, STANDARD), too_few)

        exact = {"farmer": ["CARE"], "hands": [["PASS"]], "market": []}
        a = make_agent(parent_with(exact))
        self.assertEqual(a(observation, STANDARD)["hands"], [["COLLECT_FERTILIZER"]])

    def test_requires_shed_adjacent_animal_true_fert(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        for o in (obs(pos=(1, 1)), obs(fert=False), obs(fert=1), obs(animal=None)):
            a = make_agent(parent_with(action))
            self.assertEqual(a(o, STANDARD)["farmer"], ["PASS"])

    def test_explicit_standard_terminal_timing_is_required(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        bad_configs = (
            None,
            {},
            {"episodeSteps": 720},
            {"turnsPerDay": 24},
            {"episodeSteps": True, "turnsPerDay": 24},
            {"episodeSteps": 720.0, "turnsPerDay": 24},
            {"episodeSteps": 719, "turnsPerDay": 24},
            {"episodeSteps": 720, "turnsPerDay": True},
            {"episodeSteps": 720, "turnsPerDay": 24.0},
            {"episodeSteps": 720, "turnsPerDay": 23},
        )
        for config in bad_configs:
            with self.subTest(config=config):
                a = make_agent(parent_with(action))
                self.assertEqual(a(obs(), config), action)
        a = make_agent(parent_with(action))
        self.assertEqual(a(obs(), dict(STANDARD))["farmer"], ["COLLECT_FERTILIZER"])

    def test_nonstandard_timing_does_not_leave_collection_provenance(self):
        calls = {
            716: {"farmer": ["PASS"], "hands": [], "market": []},
            718: {
                "farmer": ["PASS"],
                "hands": [],
                "market": [["SELL", "FERTILIZER", 1], ["SELL", "WHEAT", 1]],
            },
        }

        def parent(o, _cfg=None):
            return copy.deepcopy(calls[o["step"]])

        a = make_agent(parent)
        a(obs(step=716), {"episodeSteps": 719, "turnsPerDay": 24})
        self.assertEqual(a(obs(step=718), STANDARD)["market"], calls[718]["market"])

    def test_trails_only_after_collection(self):
        terminal = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [
                ["SELL", "FERTILIZER", 2],
                ["SELL", "WOOL", 4],
                ["SELL", "WHEAT", 2],
            ],
        }
        a = make_agent(parent_with(terminal))
        self.assertEqual(a(obs(step=718), STANDARD)["market"], terminal["market"])
        calls = {
            716: {"farmer": ["PASS"], "hands": [], "market": []},
            718: terminal,
        }

        def parent(o, _cfg=None):
            return copy.deepcopy(calls[o["step"]])

        a = make_agent(parent)
        a(obs(step=716), STANDARD)
        self.assertEqual(
            a(obs(step=718), STANDARD)["market"],
            [
                ["SELL", "WOOL", 4],
                ["SELL", "WHEAT", 2],
                ["SELL", "FERTILIZER", 2],
            ],
        )

    def test_rewind_resets_collection_provenance(self):
        calls = {
            716: {"farmer": ["PASS"], "hands": [], "market": []},
            718: {
                "farmer": ["PASS"],
                "hands": [],
                "market": [["SELL", "FERTILIZER", 1], ["SELL", "WHEAT", 1]],
            },
            0: {"farmer": ["PASS"], "hands": [], "market": []},
        }

        def parent(o, _cfg=None):
            return copy.deepcopy(calls[o["step"]])

        a = make_agent(parent)
        a(obs(step=716), STANDARD)
        a(obs(step=0), STANDARD)
        self.assertEqual(a(obs(step=718), STANDARD)["market"], calls[718]["market"])

    def test_malformed_observation_fails_closed(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        a = make_agent(parent_with(action))
        bad = obs()
        bad["player"] = True
        self.assertEqual(a(bad, STANDARD), action)


if __name__ == "__main__":
    unittest.main()
