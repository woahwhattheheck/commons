import copy
import unittest

from terminal_fertilizer import make_agent


def obs(step=716, player=0, pos=(4, 4), fert=True, animal="COW"):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[pos[1]][pos[0]] = {
        "kind": "PASTURE",
        "animal": animal,
        "fertilizer_available": fert,
    }
    return {
        "step": step,
        "player": player,
        "farms": [{"tiles": tiles, "farmer": list(pos), "hands": []}],
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
            self.assertEqual(a(obs(step=step))["farmer"], ["COLLECT_FERTILIZER"])

    def test_outside_window_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 1]]}
        a = make_agent(parent_with(action))
        self.assertEqual(a(obs(step=715)), action)

    def test_never_overrides_non_pass(self):
        for cmd in (["CARE"], ["FEED"], ["DROP"], ["PLACE", "MILK", 1], ["HARVEST"]):
            a = make_agent(parent_with({"farmer": cmd, "hands": [], "market": []}))
            self.assertEqual(a(obs())["farmer"], cmd)

    def test_requires_shed_adjacent_animal_true_fert(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        for o in (obs(pos=(1, 1)), obs(fert=False), obs(fert=1), obs(animal=None)):
            a = make_agent(parent_with(action))
            self.assertEqual(a(o)["farmer"], ["PASS"])

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
        self.assertEqual(a(obs(step=718))["market"], terminal["market"])
        calls = {
            716: {"farmer": ["PASS"], "hands": [], "market": []},
            718: terminal,
        }

        def parent(o, _cfg=None):
            return copy.deepcopy(calls[o["step"]])

        a = make_agent(parent)
        a(obs(step=716))
        self.assertEqual(
            a(obs(step=718))["market"],
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
        a(obs(step=716))
        a(obs(step=0))
        self.assertEqual(a(obs(step=718))["market"], calls[718]["market"])

    def test_malformed_fails_open(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        a = make_agent(parent_with(action))
        bad = obs()
        bad["player"] = True
        self.assertEqual(a(bad), action)


if __name__ == "__main__":
    unittest.main()
