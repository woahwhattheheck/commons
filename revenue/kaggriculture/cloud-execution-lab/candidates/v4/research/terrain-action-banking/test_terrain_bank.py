# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("terrain_bank", HERE / "verify_terrain_bank.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


class MathTests(unittest.TestCase):
    def test_default_horizons_are_strictly_action_dominated(self):
        result = mod.verdict()
        self.assertEqual(result["disposition"], "FALSIFIED_AS_ACTION_BANK")
        for row in result["rows"]:
            self.assertGreater(row["critical_day_action_penalty"], 0.0)
            self.assertGreater(row["total_tile_local_action_penalty"], 1.0)

    def test_30_day_exact_probability(self):
        q = mod.weed_present_probability(30)
        self.assertAlmostEqual(q, 1.0 - 0.995 ** 30)
        self.assertAlmostEqual(q, 0.13961580808530394)
        row = mod.action_accounting(30)
        self.assertAlmostEqual(row["critical_day_action_penalty"], 0.8603841919146961)
        self.assertAlmostEqual(row["total_tile_local_action_penalty"], 1.8603841919146961)

    def test_zero_day_already_favors_baseline(self):
        row = mod.action_accounting(0)
        self.assertEqual(row["baseline_future_dig_expected"], 0.0)
        self.assertEqual(row["shield_future_dig_expected"], 1.0)
        self.assertEqual(row["total_tile_local_action_penalty"], 2.0)

    def test_invalid_inputs(self):
        for bad in (-1, 1.5, True):
            with self.assertRaises(ValueError):
                mod.weed_present_probability(bad)
        for bad in (-0.1, 1.1):
            with self.assertRaises(ValueError):
                mod.weed_present_probability(2, bad)


class SourceBindingTests(unittest.TestCase):
    ENGINE = r"""
def _apply_unit_action(farm, private, idx, action, board_size, day, turns_per_day, shed_capacity=100):
    op = action[0]
    fy=fx=0
    tile = farm["tiles"][fy][fx]
    if op == "DIG":
        if tile is None:
            return
        if isinstance(tile, dict) and "animal" in tile:
            return
        farm["tiles"][fy][fx] = None
        return
    if op == "BUILD_COOP":
        if tile is not None:
            return
        farm["tiles"][fy][fx] = {"kind": "COOP"}
        return
    if op == "BUILD_PASTURE":
        if tile is not None:
            return
        farm["tiles"][fy][fx] = {"kind": "PASTURE"}
        return

def _spawn_weeds(farm, board_size, weed_chance, rng):
    for y in range(board_size):
        for x in range(board_size):
            if farm["tiles"][y][x] is None and rng.random() < weed_chance:
                farm["tiles"][y][x] = {"kind": "WEED"}

def _end_of_day(state, env, day):
    cfg = env.configuration
    weed_chance = float(get(cfg, "weedSpawnChance", 0.005))
    rng = object()
    for player_id, farm in enumerate([]):
        _spawn_weeds(farm, board_size, weed_chance, rng)
"""

    def test_authenticator_accepts_semantics_when_blob_is_bound_to_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "engine.py"
            path.write_text(self.ENGINE)
            blob = mod.git_blob_sha1(path.read_bytes())
            auth = mod.authenticate_engine(path, expected_blob=blob)
            self.assertEqual(auth["engine_blob"], blob)

    def test_source_mutants_rejected(self):
        mutants = [
            self.ENGINE.replace('is None and rng.random()', 'is not None and rng.random()'),
            self.ENGINE.replace('{"kind": "COOP"}', '{"kind": "WEED"}'),
            self.ENGINE.replace('{"kind": "PASTURE"}', '{"kind": "WEED"}'),
            self.ENGINE.replace('farm["tiles"][fy][fx] = None', 'farm["tiles"][fy][fx] = {"kind": "WEED"}'),
            self.ENGINE.replace('"weedSpawnChance", 0.005', '"weedSpawnChance", 0.05'),
        ]
        for source in mutants:
            with self.subTest(mutant=source[:40]):
                with tempfile.TemporaryDirectory() as td:
                    path = Path(td) / "engine.py"
                    path.write_text(source)
                    blob = mod.git_blob_sha1(path.read_bytes())
                    with self.assertRaises(ValueError):
                        mod.authenticate_engine(path, expected_blob=blob)

    def test_blob_drift_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "engine.py"
            path.write_text(self.ENGINE)
            with self.assertRaises(ValueError):
                mod.authenticate_engine(path, expected_blob="0" * 40)

    def test_current_official_engine_when_present(self):
        package = Path(__file__).resolve().parent
        try:
            engine = mod.locate_engine_from_package(package)
        except IndexError:
            self.skipTest("standalone development copy")
        if not engine.is_file():
            self.skipTest("official engine not present in standalone development copy")
        auth = mod.authenticate_engine(engine)
        self.assertEqual(auth["engine_blob"], mod.OFFICIAL_ENGINE_BLOB)


if __name__ == "__main__":
    unittest.main()
