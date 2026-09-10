# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from leader_route_distillation import (
    CompileError,
    SOURCE_PIN_SCHEMA,
    compile_bank,
    emit_candidates,
    extract_seat,
    load_source_pins,
)


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


def write_replay(path: Path, value) -> bytes:
    data = json.dumps(value, allow_nan=False).encode("utf-8")
    path.write_bytes(data)
    return data


def pin_document(path: Path, value, *, teams=None, rewards=None, expected=None):
    data = path.read_bytes()
    teams = teams or list(value["info"]["TeamNames"])
    rewards = rewards or [
        float(value["steps"][-1][0]["reward"]),
        float(value["steps"][-1][1]["reward"]),
    ]
    expected = expected or [
        f"{teams[0].lower().replace(' ', '-')}-e1-s0",
        f"{teams[1].lower().replace(' ', '-')}-e1-s1",
    ]
    return {
        "schema": SOURCE_PIN_SCHEMA,
        "sources": [{
            "episode": 1,
            "json_bytes": len(data),
            "json_sha256": hashlib.sha256(data).hexdigest(),
            "frames": len(value["steps"]),
            "teams": teams,
            "rewards": rewards,
        }],
        "expected_candidates": expected,
    }


def load_pins(root: Path, document):
    path = root / "pins.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return load_source_pins(path)


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
            write_replay(root / "episode_1.json", replay("Alpha", 1000))
            write_replay(root / "episode_2.json", replay("Alpha", 2000))
            bank = compile_bank(root.glob("*.json"), max_candidates=2)
            alpha = next(row for row in bank["candidates"] if row["team"] == "Alpha")
            self.assertEqual(alpha["episode"], "2")
            self.assertEqual(alpha["reward"], 2000.0)

    def test_emit_is_deterministic_and_embeds_digest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "episode_1.json"
            write_replay(src, replay("Alpha", 1000))
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

    def test_exact_pins_bind_source_manifest_and_candidate_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            value = replay()
            src = root / "episode_1.json"
            write_replay(src, value)
            pins = load_pins(root, pin_document(src, value))
            bank = compile_bank([src], max_candidates=2, source_pins=pins)
            self.assertEqual(bank["source_pins_sha256"], pins["manifest_sha256"])
            self.assertEqual(
                [row["candidate_id"] for row in bank["candidates"]],
                ["alpha-e1-s0", "beta-e1-s1"],
            )
            self.assertEqual(bank["sources"][0]["teams"], ["Alpha", "Beta"])

    def test_pins_reject_byte_substitution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            value = replay()
            src = root / "episode_1.json"
            write_replay(src, value)
            pins = load_pins(root, pin_document(src, value))
            src.write_bytes(src.read_bytes() + b"\n")
            with self.assertRaisesRegex(CompileError, "SHA-256 mismatch"):
                compile_bank([src], max_candidates=2, source_pins=pins)

    def test_pins_reject_team_substitution_even_with_updated_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            changed = replay(team0="Mallory")
            src = root / "episode_1.json"
            write_replay(src, changed)
            document = pin_document(
                src,
                changed,
                teams=["Alpha", "Beta"],
                rewards=[1000.0, 999.0],
                expected=["alpha-e1-s0", "beta-e1-s1"],
            )
            pins = load_pins(root, document)
            with self.assertRaisesRegex(CompileError, "TeamNames mismatch"):
                compile_bank([src], max_candidates=2, source_pins=pins)

    def test_pins_reject_reward_substitution_even_with_updated_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            changed = replay(reward=1001)
            src = root / "episode_1.json"
            write_replay(src, changed)
            document = pin_document(
                src,
                changed,
                teams=["Alpha", "Beta"],
                rewards=[1000.0, 999.0],
                expected=["alpha-e1-s0", "beta-e1-s1"],
            )
            pins = load_pins(root, document)
            with self.assertRaisesRegex(CompileError, "reward mismatch"):
                compile_bank([src], max_candidates=2, source_pins=pins)

    def test_pins_reject_missing_and_extra_episode_sets(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            value = replay()
            src = root / "episode_1.json"
            write_replay(src, value)
            document = pin_document(src, value)
            document["sources"].append({**document["sources"][0], "episode": 2})
            pins = load_pins(root, document)
            with self.assertRaisesRegex(CompileError, "source episode set mismatch"):
                compile_bank([src], max_candidates=2, source_pins=pins)

    def test_pins_reject_selected_candidate_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            value = replay()
            src = root / "episode_1.json"
            write_replay(src, value)
            document = pin_document(src, value, expected=["wrong-e1-s0"])
            pins = load_pins(root, document)
            with self.assertRaisesRegex(CompileError, "selected candidate identity mismatch"):
                compile_bank([src], max_candidates=2, source_pins=pins)

    def test_exact_team_names_are_required_and_fallbacks_are_forbidden(self):
        missing = replay()
        missing.pop("info")
        with self.assertRaisesRegex(CompileError, "exact TeamNames"):
            extract_seat(missing, episode="1", seat=0, source_sha256="a" * 64)
        fallback = replay(team0="seat-0")
        with self.assertRaisesRegex(CompileError, "fallback TeamNames"):
            extract_seat(fallback, episode="1", seat=0, source_sha256="a" * 64)

    def test_nonfinite_final_reward_is_rejected(self):
        value = replay()
        value["steps"][-1][0]["reward"] = math.inf
        with self.assertRaisesRegex(CompileError, "not finite"):
            extract_seat(value, episode="1", seat=0, source_sha256="a" * 64)

    def test_negative_observation_player_is_rejected(self):
        value = replay()
        value["steps"][0][0]["observation"]["player"] = -1
        with self.assertRaisesRegex(CompileError, "lacks player farm"):
            extract_seat(value, episode="1", seat=0, source_sha256="a" * 64)

    def test_pin_loader_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "pins.json"
            path.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            with self.assertRaisesRegex(CompileError, "duplicate JSON key"):
                load_source_pins(path)


if __name__ == "__main__":
    unittest.main()
