#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("_plantquorum_census_under_test", HERE / "census.py")
assert SPEC is not None and SPEC.loader is not None
census = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(census)


class PlantQuorumCurrentNativeCensusTests(unittest.TestCase):
    def _engaged_fixture(self):
        tiles = [[None for _ in range(10)] for _ in range(10)]
        tiles[0][0] = {"crop": "CARROT", "stage": 1}
        obs = {
            "player": 0,
            "farms": [
                {"farmer": [0, 0], "hands": [[1, 0]], "tiles": tiles},
                {"farmer": [9, 9], "hands": [], "tiles": [[None] * 10 for _ in range(10)]},
            ],
            "private": {"seeds": {"CARROT": 1}},
        }
        action = {
            "farmer": ["PLANT", "CARROT"],
            "hands": [["PLANT", "CARROT"]],
            "market": [["SELL", "MILK", 1]],
        }
        return obs, action

    def test_real_repo_authority_is_exactly_pinned(self):
        _module, provenance = census.load_authority()
        self.assertEqual(provenance["theorem_git_blob"], census.PINNED_THEOREM_BLOB)
        self.assertEqual(provenance["engine_git_blob"], census.PINNED_ENGINE_BLOB)

    def test_observer_preserves_control_action_and_emits_candidate_witness(self):
        obs, action = self._engaged_fixture()
        before = deepcopy(action)
        control, witness = census.observe(obs, action)
        self.assertEqual(action, before)
        self.assertEqual(control, before)
        self.assertIsNot(control, action)
        self.assertTrue(witness["control_action_preserved"])
        self.assertTrue(witness["changed"])
        self.assertEqual(witness["original_action"], before)
        self.assertEqual(
            witness["candidate_action"],
            {
                "farmer": ["PASS"],
                "hands": [["PLANT", "CARROT"]],
                "market": [["SELL", "MILK", 1]],
            },
        )
        self.assertEqual(witness["theorem_report"]["changed_actors"], [0])
        crop = witness["theorem_report"]["crops"][0]
        self.assertEqual(crop["status"], "RELIEVE_SOURCE_CERTAIN_POISON")
        self.assertEqual(crop["available_seeds"], 1)
        self.assertNotEqual(
            witness["original_action_sha256"],
            witness["candidate_action_sha256"],
        )

    def test_colocation_is_ambiguous_and_stays_identity(self):
        obs, action = self._engaged_fixture()
        obs["farms"][0]["hands"] = [[0, 0]]
        control, witness = census.observe(obs, action)
        self.assertEqual(control, action)
        self.assertFalse(witness["changed"])
        self.assertEqual(witness["candidate_action"], action)
        statuses = [row["status"] for row in witness["theorem_report"]["crops"]]
        self.assertEqual(statuses, ["BLOCKED_NO_SOURCE_CERTAIN_POISON"])

    def test_zero_seed_poison_removal_is_insufficient(self):
        obs, action = self._engaged_fixture()
        obs["private"]["seeds"]["CARROT"] = 0
        control, witness = census.observe(obs, action)
        self.assertEqual(control, action)
        self.assertFalse(witness["changed"])
        crop = witness["theorem_report"]["crops"][0]
        self.assertEqual(crop["status"], "BLOCKED_POISON_REMOVAL_INSUFFICIENT")

    def _copy_authority(self, destination: Path):
        for rel in (census.THEOREM_REL, census.ENGINE_REL):
            target = destination / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(census.LAB_ROOT / rel, target)

    def test_theorem_drift_fails_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_authority(root)
            theorem = root / census.THEOREM_REL
            theorem.write_bytes(theorem.read_bytes() + b"\n# drift\n")
            with self.assertRaisesRegex(census.CensusError, "theorem drift"):
                census.load_authority(root)

    def test_engine_drift_fails_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_authority(root)
            engine = root / census.ENGINE_REL
            engine.write_bytes(engine.read_bytes() + b"\n# drift\n")
            with self.assertRaisesRegex(census.CensusError, "engine drift"):
                census.load_authority(root)

    def test_witness_original_is_detached_from_returned_control(self):
        obs, action = self._engaged_fixture()
        control, witness = census.observe(obs, action)
        control["market"].append(["HIRE"])
        self.assertEqual(witness["original_action"], action)
        self.assertNotEqual(control, witness["original_action"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
