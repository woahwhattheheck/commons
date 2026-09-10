# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from leader_route_distillation import CompileError, compile_bank, emit_candidates, extract_seat


def observation(step, hands=1, quadrants=1):
    return {
        "step": step,
        "player": 0,
        "farms": [
            {"hands": [{} for _ in range(hands)], "unlocked_quadrants": list(range(quadrants))},
            {"hands": [], "unlocked_quadrants": []},
        ],
    }


def action(tag="PASS", hands=1):
    return {"farmer": [tag], "hands": [[tag] for _ in range(hands)], "market": []}


def replay(team0="Alpha", reward=1000, frames=702):
    steps = []
    steps.append([
        {"observation": observation(0), "action": None, "reward": 0},
        {"observation": {**observation(0), "player": 1}, "action": None, "reward": 0},
    ])
    for i in range(1, frames):
        steps.append([
            {"observation": observation(i), "action": action(f"A{i-1}"), "reward": reward if i == frames - 1 else 0},
            {"observation": {**observation(i), "player": 1}, "action": action(f"B{i-1}"), "reward": reward - 1 if i == frames - 1 else 0},
        ])
    return {"info": {"TeamNames": [team0, "Beta"]}, "steps": steps}


class CompilerTests(unittest.TestCase):
    def test_frame_action_is_bound_to_previous_observation(self):
        value = replay(frames=702)
        row = extract_seat(value, episode="1", seat=0, source_sha256="a" * 64)
        self.assertEqual(row["tape"]["0"]["action"]["farmer"], ["A0"])
        self.assertEqual(row["tape"]["0"]["signature"], {"hands": 1, "quadrants": 1})
        self.assertEqual(row["actions"], 701)

    def test_rejects_short_replay(self):
        with self.assertRaises(CompileError):
            extract_seat(replay(frames=10), episode="1", seat=0, source_sha256="a" * 64)

    def test_highest_reward_per_team_is_selected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "episode_1.json").write_text(json.dumps(replay("Alpha", 1000)), encoding="utf-8")
            (root / "episode_2.json").write_text(json.dumps(replay("Alpha", 2000)), encoding="utf-8")
            bank = compile_bank(root.glob("*.json"), max_candidates=2)
            alpha = next(row for row in bank["candidates"] if row["team"] == "Alpha")
            self.assertEqual(alpha["episode"], "2")
            self.assertEqual(alpha["reward"], 2000.0)

    def test_emit_is_deterministic_and_embeds_digest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "episode_1.json"
            src.write_text(json.dumps(replay("Alpha", 1000)), encoding="utf-8")
            bank = compile_bank([src], max_candidates=1)
            runtime = Path(__file__).with_name("leader_route_runtime.py")
            baseline = root / "baseline.py"
            baseline.write_text("def agent(obs, configuration=None):\n return {'farmer':['PASS'],'hands':[['PASS']],'market':[]}\n", encoding="utf-8")
            one, two = root / "one", root / "two"
            m1 = emit_candidates(bank, runtime, baseline, one)
            m2 = emit_candidates(bank, runtime, baseline, two)
            self.assertEqual([r["python_sha256"] for r in m1["arms"]], [r["python_sha256"] for r in m2["arms"]])
            self.assertEqual(len(m1["arms"]), 3)
            for row in m1["arms"]:
                self.assertEqual(hashlib.sha256((one / row["path"]).read_bytes()).hexdigest(), row["python_sha256"])


if __name__ == "__main__":
    unittest.main()
