#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import tempfile
import unittest

import counter_ambush_burst as b

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE / "counter_ambush.py"


class ApexBurstTests(unittest.TestCase):
    def test_source_real_burst_values(self):
        report = b.authenticated_apex_report(BASE)
        burst = report["source_real_max_shop_drain"]
        self.assertEqual(report["authenticated_events"], [[499, 8], [500, 8], [501, 8]])
        self.assertEqual(burst["own_early_gross"], 905)
        self.assertEqual(burst["own_post_burst_gross"], 661)
        self.assertEqual(burst["own_timing_gain"], 244)
        self.assertEqual(burst["cumulative_rival_suppression"], 367)
        self.assertEqual(burst["gross_relative_margin_swing"], 611)
        self.assertFalse(burst["decision_authority"])

    def test_town_drain_occurs_between_second_and_third_dump(self):
        report = b.authenticated_apex_report(BASE)
        rows = report["source_real_max_shop_drain"]["events"]
        self.assertEqual([row["step"] for row in rows], [499, 500, 501])
        self.assertEqual([row["town_drain_after"] for row in rows], [0, 8, 0])
        self.assertEqual([row["rival_suppression"] for row in rows], [121, 123, 123])

    def test_burst_is_not_three_isolated_dumps(self):
        report = b.authenticated_apex_report(BASE)
        self.assertEqual(report["isolated_first_event_swing"], 242)
        self.assertEqual(report["naive_three_times_isolated_swing"], 726)
        self.assertEqual(report["source_real_max_shop_drain"]["gross_relative_margin_swing"], 611)
        self.assertEqual(report["burst_minus_naive_isolated"], -115)

    def test_pinned_base_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "counter_ambush.py"
            path.write_bytes(BASE.read_bytes() + b"\n# drift\n")
            with self.assertRaisesRegex(b.BurstError, "base drift"):
                b.load_pinned_base(path)

    def test_event_steps_must_be_strictly_increasing(self):
        for events in (
            ((499, 8), (499, 8)),
            ((500, 8), (499, 8)),
        ):
            with self.subTest(events=events):
                with self.assertRaisesRegex(b.BurstError, "strictly increasing"):
                    b.normalize_events(events)

    def test_event_units_fail_closed(self):
        for events in (
            ((499, 0),),
            ((499, -1),),
            ((499, True),),
        ):
            with self.subTest(events=events):
                with self.assertRaises(b.BurstError):
                    b.normalize_events(events)

    def test_pre_step_must_touch_burst(self):
        base = b.load_pinned_base(BASE)
        with self.assertRaisesRegex(b.BurstError, "exactly one callback"):
            b.burst_counterfactual(
                base,
                item="STRAWBERRY",
                starting_inventory=10000,
                own_units=8,
                events=b.AUTHENTICATED_APEX_STRAWBERRY_BURST,
                pre_step=497,
            )

    def test_empty_events_rejected(self):
        with self.assertRaisesRegex(b.BurstError, "nonempty event"):
            b.normalize_events(())


if __name__ == "__main__":
    unittest.main()
