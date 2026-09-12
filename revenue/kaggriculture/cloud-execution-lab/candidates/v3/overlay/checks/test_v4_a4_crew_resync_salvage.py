# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve()
DOCS = HERE.parents[2] / "docs"
SPEC = importlib.util.spec_from_file_location(
    "v4_salvage_a4_crew_resync", DOCS / "v4_salvage_a4_crew_resync.py"
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)


class A4CrewResyncSalvageTests(unittest.TestCase):
    def test_exact_late_second_hire_shape_rebuilds_same_day(self):
        state = {"jobs_built_day": 12, "jobs_built_crew": (1,)}
        self.assertTrue(mod.crew_jobs_stale(state, day=12, crew=[1, 2]))

    def test_unchanged_same_day_crew_reuses_jobs(self):
        state = {"jobs_built_day": 12, "jobs_built_crew": (1, 2)}
        self.assertFalse(mod.crew_jobs_stale(state, day=12, crew=[1, 2]))

    def test_day_rollover_rebuilds(self):
        state = {"jobs_built_day": 12, "jobs_built_crew": (1, 2)}
        self.assertTrue(mod.crew_jobs_stale(state, day=13, crew=[1, 2]))

    def test_missing_build_metadata_rebuilds_valid_active_crew(self):
        self.assertTrue(mod.crew_jobs_stale({}, day=12, crew=[1]))

    def test_empty_or_malformed_crew_cannot_create_work(self):
        state = {"jobs_built_day": 12, "jobs_built_crew": ()}
        self.assertFalse(mod.crew_jobs_stale(state, day=12, crew=[]))
        self.assertFalse(mod.crew_jobs_stale(state, day=12, crew=[True]))
        self.assertFalse(mod.crew_jobs_stale(state, day=12, crew=[1, 1]))
        self.assertFalse(mod.crew_jobs_stale(state, day=12, crew=[-1]))

    def test_invalid_day_or_state_fail_closed(self):
        self.assertFalse(mod.crew_jobs_stale(None, day=12, crew=[1]))
        self.assertFalse(mod.crew_jobs_stale({}, day=True, crew=[1]))
        self.assertFalse(mod.crew_jobs_stale({}, day=-1, crew=[1]))

    def test_mark_records_exact_tuple(self):
        state = {}
        self.assertTrue(mod.mark_crew_jobs_built(state, day=12, crew=[1, 2]))
        self.assertEqual(state, {"jobs_built_day": 12, "jobs_built_crew": (1, 2)})
        self.assertFalse(mod.crew_jobs_stale(state, day=12, crew=[1, 2]))
        self.assertTrue(mod.crew_jobs_stale(state, day=12, crew=[1, 2, 3]))

    def test_failed_mark_does_not_mutate(self):
        state = {"sentinel": 1}
        self.assertFalse(mod.mark_crew_jobs_built(state, day=12, crew=[False]))
        self.assertEqual(state, {"sentinel": 1})


if __name__ == "__main__":
    unittest.main()
