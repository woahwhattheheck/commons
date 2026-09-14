from __future__ import annotations
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ablation"))

from harness import BASELINE, DEFAULT_VARIANTS, ExperimentPlan
from sage_runner import LevelSwitchDoorEnv, run_plan


class SageRunnerContractTests(unittest.TestCase):
    def test_translated_level_reset_tracks_level_index(self):
        for level in range(3):
            env = LevelSwitchDoorEnv(0, level)
            obs = env.reset()
            self.assertEqual(obs.levels_completed, level)

    def test_small_sweep_is_complete_and_coordinate_ablation_expands_candidates(self):
        p = ExperimentPlan("small", DEFAULT_VARIANTS, (0,), (0,), 12, "mock", "test")
        rows = run_plan(p)
        self.assertEqual(len(rows), len(DEFAULT_VARIANTS))
        by_name = {row.variant: row for row in rows}
        self.assertGreater(
            by_name["all_grid_coordinates"].coordinate_candidates_considered,
            by_name[BASELINE.name].coordinate_candidates_considered,
        )

    def test_animation_ablation_never_observes_more_frames(self):
        p = ExperimentPlan("animation", DEFAULT_VARIANTS, (0,), (0,), 32, "mock", "test")
        rows = {row.variant: row for row in run_plan(p)}
        self.assertLessEqual(
            rows["settled_frame"].animation_frames_observed,
            rows[BASELINE.name].animation_frames_observed,
        )


if __name__ == "__main__":
    unittest.main()
