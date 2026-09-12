from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import harvest_window_audit as h


class HarvestWindowTests(unittest.TestCase):
    def setUp(self):
        self.report = h.build_report()
        self.by_crop = {row["crop"]: row for row in self.report["crops"]}

    def test_strawberry_source_correction_is_four(self):
        self.assertEqual(self.by_crop["STRAWBERRY"]["max_yield"], 4)

    def test_exact_mls_all_crops(self):
        self.assertEqual({k: self.by_crop[k]["max_lifespan_step"] for k in self.by_crop}, {
            "WHEAT": 120, "CARROT": 96, "TOMATO": 288, "STRAWBERRY": 408, "MELON": 312,
        })

    def test_perfect_full_observable_steps(self):
        got = {k: self.by_crop[k]["perfect_water_and_fertilizer"]["earliest_full_yield_observable_callback_step"] for k in self.by_crop}
        self.assertEqual(got, {
            "WHEAT": 97, "CARROT": 73, "TOMATO": 216, "STRAWBERRY": 288, "MELON": 193,
        })

    def test_nonongoing_same_step_attainment(self):
        self.assertEqual(self.by_crop["WHEAT"]["perfect_water_and_fertilizer"]["earliest_full_yield_attainable_during_service_action_step"], 96)
        self.assertEqual(self.by_crop["CARROT"]["perfect_water_and_fertilizer"]["earliest_full_yield_attainable_during_service_action_step"], 72)
        self.assertEqual(self.by_crop["MELON"]["perfect_water_and_fertilizer"]["earliest_full_yield_attainable_during_service_action_step"], 192)

    def test_water_only_wheat_and_carrot_never_reach_max_before_decay(self):
        self.assertIsNone(self.by_crop["WHEAT"]["water_without_fertilizer"]["earliest_full_yield_observable_callback_step"])
        self.assertEqual(self.by_crop["WHEAT"]["water_without_fertilizer"]["yield_at_mls"], 4)
        self.assertIsNone(self.by_crop["CARROT"]["water_without_fertilizer"]["earliest_full_yield_observable_callback_step"])
        self.assertEqual(self.by_crop["CARROT"]["water_without_fertilizer"]["yield_at_mls"], 3)

    def test_water_only_melon_reaches_full(self):
        x = self.by_crop["MELON"]["water_without_fertilizer"]
        self.assertEqual(x["earliest_full_yield_attainable_during_service_action_step"], 240)
        self.assertEqual(x["earliest_full_yield_observable_callback_step"], 241)
        self.assertEqual(x["yield_at_mls"], 6)

    def test_tomato_production_events(self):
        self.assertEqual(self.by_crop["TOMATO"]["production_event_observable_callback_steps"], [192, 216, 240, 264])

    def test_strawberry_production_events(self):
        self.assertEqual(self.by_crop["STRAWBERRY"]["production_event_observable_callback_steps"], [240, 288, 336, 384])

    def test_ongoing_fertilizer_fills_capacity_early_but_not_mls(self):
        self.assertEqual(self.by_crop["TOMATO"]["perfect_water_and_fertilizer"]["earliest_full_yield_observable_callback_step"], 216)
        self.assertEqual(self.by_crop["TOMATO"]["water_without_fertilizer"]["earliest_full_yield_observable_callback_step"], 264)
        self.assertEqual(self.by_crop["TOMATO"]["max_lifespan_step"], 288)
        self.assertEqual(self.by_crop["STRAWBERRY"]["perfect_water_and_fertilizer"]["earliest_full_yield_observable_callback_step"], 288)
        self.assertEqual(self.by_crop["STRAWBERRY"]["water_without_fertilizer"]["earliest_full_yield_observable_callback_step"], 384)
        self.assertEqual(self.by_crop["STRAWBERRY"]["max_lifespan_step"], 408)

    def test_exact_mls_action_remains_full_yield(self):
        for crop in self.by_crop.values():
            p = crop["perfect_water_and_fertilizer"]
            self.assertEqual(p["last_full_yield_harvest_action_step"], crop["max_lifespan_step"])
            self.assertEqual(p["first_reduced_yield_observable_callback_step"], crop["max_lifespan_step"] + 1)

    def test_perfect_decay_steps(self):
        self.assertEqual(self.by_crop["CARROT"]["perfect_water_and_fertilizer"]["decay_action_steps_if_never_harvested"], [96, 98, 100, 102])
        self.assertEqual(self.by_crop["WHEAT"]["perfect_water_and_fertilizer"]["decay_action_steps_if_never_harvested"], [120, 122, 124, 126, 128, 130])
        self.assertEqual(self.by_crop["TOMATO"]["perfect_water_and_fertilizer"]["decay_action_steps_if_never_harvested"], [288, 290, 292, 294])
        self.assertEqual(self.by_crop["MELON"]["perfect_water_and_fertilizer"]["decay_action_steps_if_never_harvested"], [312, 314, 316, 318, 320, 322])
        self.assertEqual(self.by_crop["STRAWBERRY"]["perfect_water_and_fertilizer"]["decay_action_steps_if_never_harvested"], [408, 410, 412, 414])

    def test_perfect_first_weed_observable(self):
        got = {k: self.by_crop[k]["perfect_water_and_fertilizer"]["first_weed_observable_callback_step"] for k in self.by_crop}
        self.assertEqual(got, {"WHEAT": 131, "CARROT": 103, "TOMATO": 295, "STRAWBERRY": 415, "MELON": 323})

    def test_water_only_wheat_and_carrot_rot_earlier(self):
        self.assertEqual(self.by_crop["WHEAT"]["water_without_fertilizer"]["first_weed_observable_callback_step"], 127)
        self.assertEqual(self.by_crop["CARROT"]["water_without_fertilizer"]["first_weed_observable_callback_step"], 101)

    def test_nonongoing_water_windows(self):
        self.assertEqual(self.by_crop["WHEAT"]["water_yield_window_days_inclusive"], [2, 4])
        self.assertEqual(self.by_crop["CARROT"]["water_yield_window_days_inclusive"], [2, 3])
        self.assertEqual(self.by_crop["MELON"]["water_yield_window_days_inclusive"], [6, 12])

    def test_full_callback_intervals_end_at_mls(self):
        for crop in self.by_crop.values():
            interval = crop["perfect_water_and_fertilizer"]["full_yield_callback_interval_inclusive"]
            self.assertIsNotNone(interval)
            self.assertEqual(interval[-1], crop["max_lifespan_step"])

    def test_drought_guard_is_explicit(self):
        self.assertEqual(self.report["drought_guard"]["planting_state_consecutive_unwatered"], 1)
        self.assertIn("earlier", self.report["drought_guard"]["warning"])

    def test_profitability_not_inferred(self):
        self.assertEqual(self.report["assumptions"]["economics"].split(":", 1)[0], "NOT_ASSESSED")

    def test_current_schedule_not_assessed_without_source_binding(self):
        self.assertEqual(self.report["current_v4_schedule_census"]["status"], "NOT_ASSESSED")
        self.assertIn("source-to-artifact", self.report["current_v4_schedule_census"]["reason"])

    def test_promotion_not_assessed(self):
        self.assertEqual(self.report["promotion_decision"], "NOT_ASSESSED")

    def test_bool_tpd_fails(self):
        with self.assertRaisesRegex(h.AuditError, "positive integer"):
            h.build_report(turns_per_day=True)

    def test_unpinned_report_hash_fails(self):
        with self.assertRaisesRegex(h.AuditError, "unpinned"):
            h.build_report(engine_sha256="0" * 64)

    def test_verify_engine_accepts_exact_fixture_hash(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "engine.py"
            p.write_bytes(b"pinned fixture\n")
            expected = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(h.verify_engine(p, expected_sha256=expected), expected)

    def test_verify_engine_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "engine.py"
            p.write_bytes(b"wrong\n")
            with self.assertRaisesRegex(h.AuditError, "mismatch"):
                h.verify_engine(p)

    def test_report_is_deterministic(self):
        a = json.dumps(h.build_report(), sort_keys=True)
        b = json.dumps(h.build_report(), sort_keys=True)
        self.assertEqual(a, b)

    def test_cli_hash_mismatch_returns_two_in_normal_and_optimized(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "engine.py"
            p.write_bytes(b"wrong\n")
            for args in ([sys.executable], [sys.executable, "-O"]):
                run = subprocess.run(args + [str(Path(h.__file__)), "--engine", str(p)], capture_output=True, text=True)
                self.assertEqual(run.returncode, 2)
                self.assertIn("SHA-256 mismatch", run.stderr)


if __name__ == "__main__":
    unittest.main()
