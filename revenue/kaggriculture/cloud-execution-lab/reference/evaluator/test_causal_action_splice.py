from __future__ import annotations

import io
from pathlib import Path
import tarfile
import tempfile
import unittest

import evaluate as ev
import causal_action_splice as splice


class FakeActor:
    def __init__(self, spec, cache, loader, rng_seed, startup_timeout=10.0):
        self.spec = spec
        self.ready = {"kind": "ready"}
        self.calls = 0

    def act(self, observation, configuration, timeout):
        step = int(observation["step"])
        self.calls += 1
        if self.spec == "candidate":
            amount = 2 if step == 1 else 1
        elif self.spec in ("baseline", "identical"):
            amount = 1
        else:
            amount = 0
        return {"kind": "action", "action": {"move": amount}}

    def close(self):
        pass

    def report(self):
        return {"calls": self.calls}


class FakeEngine:
    specification = {
        "configuration": {
            "episodeSteps": {"default": 3},
            "turnsPerDay": {"default": 2},
        }
    }

    def interpreter(self, state, env):
        if not state[0].observation:
            env.configuration.seed = None
            env.info["total"] = [0, 0]
            for seat in range(2):
                state[seat].observation = ev.Struct(
                    player=seat,
                    step=0,
                    farms=[{"money": 0.0}, {"money": 0.0}],
                )
            return
        totals = env.info["total"]
        for seat in range(2):
            totals[seat] += int(state[seat].action["move"])
        step = int(state[0].observation.step)
        farms = [{"money": float(totals[0])}, {"money": float(totals[1])}]
        for seat in range(2):
            state[seat].observation = ev.Struct(
                player=seat,
                step=step + 1,
                farms=farms,
            )
        if step + 1 >= env.configuration.episodeSteps:
            for seat in range(2):
                state[seat].status = "DONE"
                state[seat].reward = float(totals[seat])


class CausalActionSpliceTests(unittest.TestCase):
    def common(self):
        return dict(
            engine=FakeEngine(),
            baseline_spec="baseline",
            candidate_spec="candidate",
            opponent_spec="opponent",
            cache=Path("."),
            loader=Path("loader.py"),
            seed=7,
            focal_seat=0,
            actor_factory=FakeActor,
        )

    def test_supported_first_divergence(self):
        cell = splice.evaluate_cell(**self.common())
        self.assertEqual(cell["classification"], "supported")
        self.assertEqual(cell["divergence"]["step"], 1)
        self.assertEqual(cell["divergence"]["differing_paths"], ["$.move"])
        self.assertEqual(
            cell["effects"]["candidate_action_on_baseline"]["margin"], 1.0
        )
        self.assertEqual(
            cell["effects"]["candidate_action_on_candidate"]["margin"], 1.0
        )
        self.assertTrue(cell["replay"]["candidate_prefix_reproduced"])
        self.assertTrue(cell["replay"]["candidate_replay_same_trace"])

    def test_dormant_candidate(self):
        values = self.common()
        values["candidate_spec"] = "identical"
        cell = splice.evaluate_cell(**values)
        self.assertEqual(cell["classification"], "dormant")
        self.assertIsNone(cell["divergence"])
        self.assertIsNone(cell["effects"])

    def test_differing_paths_is_structural_and_stable(self):
        before = {"market": [["SELL", "WHEAT", 1]], "farmer": ["PASS"]}
        after = {
            "market": [["SELL", "WHEAT", 2], ["SELL", "CORN", 1]],
            "farmer": ["PASS"],
        }
        self.assertEqual(
            splice.differing_paths(before, after),
            ["$.market[0][2]", "$.market[1]"],
        )

    def test_archive_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "bad.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                info = tarfile.TarInfo("../escape.py")
                data = b"bad"
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            with self.assertRaisesRegex(ValueError, "escapes destination"):
                splice.extract_agent_archive(archive_path, root / "out")
            self.assertFalse((root / "escape.py").exists())

    def test_archive_requires_root_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "no-main.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                info = tarfile.TarInfo("other.py")
                data = b"pass\n"
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            with self.assertRaisesRegex(ValueError, "root main.py"):
                splice.extract_agent_archive(archive_path, root / "out")


if __name__ == "__main__":
    unittest.main()
