#!/usr/bin/env python3
"""Tests for the per-lane memory measurement.

The thing being defended: a lane whose suite did not complete must never end up
looking cheap. Every path that fails to produce a real measurement has to say
UNKNOWN, and the tests below drive each of those paths with a lane built to
break in that specific way.

Run:  python3 -m unittest discover -v
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import measure_memory as mm

HERE = Path(__file__).resolve().parent


def make_lane(root: Path, name: str, test_source: str | None) -> Path:
    lane = root / name
    lane.mkdir(parents=True, exist_ok=True)
    if test_source is not None:
        (lane / "test_generated.py").write_text(textwrap.dedent(test_source), encoding="utf-8")
    return lane


PASSING = """
    import unittest
    class T(unittest.TestCase):
        def test_ok(self):
            self.assertTrue(True)
        def test_also_ok(self):
            self.assertEqual(1, 1)
"""

FAILING = """
    import unittest
    class T(unittest.TestCase):
        def test_fails(self):
            self.assertEqual(1, 2)
"""

UNCOLLECTABLE = """
    import unittest
    this is not valid python
"""

HUNGRY = """
    import unittest
    class T(unittest.TestCase):
        def test_allocates(self):
            blob = bytearray(40 * 1024 * 1024)
            self.assertEqual(len(blob), 40 * 1024 * 1024)
"""


class TempCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="memceil-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


class TestProbe(TempCase):
    def test_baseline_reports_a_real_positive_figure(self):
        base = mm.measure_baseline()
        self.assertEqual(base["status"], "BASELINE")
        self.assertIsInstance(base["peak_rss_bytes"], int)
        self.assertGreater(base["peak_rss_bytes"], 0)

    def test_passing_lane_is_measured(self):
        lane = make_lane(self.tmp, "good", PASSING)
        r = mm.measure_lane(lane)
        self.assertEqual(r["status"], "OK")
        self.assertEqual(r["tests_run"], 2)
        self.assertIsInstance(r["peak_rss_bytes"], int)
        self.assertGreater(r["peak_rss_bytes"], 0)

    def test_a_lane_that_allocates_more_measures_higher(self):
        """The probe must actually track allocation, not report a constant."""
        small = mm.measure_lane(make_lane(self.tmp, "small", PASSING))
        big = mm.measure_lane(make_lane(self.tmp, "big", HUNGRY))
        self.assertEqual(big["status"], "OK")
        self.assertGreater(big["peak_rss_bytes"], small["peak_rss_bytes"] + 20 * 1024 * 1024,
                           "a 40 MiB allocation did not show up in the measurement")

    def test_each_lane_is_measured_independently(self):
        """A high-water mark shared across lanes would make every lane measured
        after a heavy one inherit its peak. Fresh process per lane prevents it."""
        mm.measure_lane(make_lane(self.tmp, "big", HUNGRY))
        after = mm.measure_lane(make_lane(self.tmp, "small", PASSING))
        self.assertLess(after["peak_rss_bytes"], 30 * 1024 * 1024,
                        "the heavy lane's peak leaked into the next lane's figure")


class TestUnknownIsNeverZero(TempCase):
    def test_lane_with_no_tests_is_UNKNOWN(self):
        lane = make_lane(self.tmp, "empty", None)
        r = mm.measure_lane(lane)
        self.assertEqual(r["status"], "NO_TESTS")
        self.assertEqual(r["peak_rss_bytes"], "UNKNOWN")
        self.assertIn("not the same as using no memory", r["note"])

    def test_failing_suite_keeps_its_figure_but_reports_the_failure(self):
        """Tests failing does not invalidate the memory measurement -- the suite
        still ran to completion -- but the status must travel with it."""
        lane = make_lane(self.tmp, "failing", FAILING)
        r = mm.measure_lane(lane)
        self.assertEqual(r["status"], "TESTS_FAILED")
        self.assertEqual(r["failures"], 1)
        self.assertIsInstance(r["peak_rss_bytes"], int)

    def test_uncollectable_suite_yields_UNKNOWN_not_a_low_number(self):
        """A module that will not import gives unittest a `_FailedTest`
        placeholder, which looks like an ordinary test error. Left alone the
        lane reports a small tidy figure for an interpreter that never ran its
        code -- cheap-looking precisely because nothing happened."""
        lane = make_lane(self.tmp, "broken", UNCOLLECTABLE)
        r = mm.measure_lane(lane)
        self.assertEqual(r["status"], "COLLECTION_ERROR")
        self.assertEqual(r["peak_rss_bytes"], "UNKNOWN")
        self.assertIn("peak_rss_bytes_observed", r,
                      "what was observed should be retained, just not presented as the figure")
        self.assertTrue(r["load_failures"])

    def test_a_genuinely_failing_test_is_not_confused_with_a_broken_import(self):
        """TESTS_FAILED keeps its figure (the code ran); COLLECTION_ERROR does
        not (the code did not). The two must not collapse into each other."""
        failing = mm.measure_lane(make_lane(self.tmp, "f", FAILING))
        broken = mm.measure_lane(make_lane(self.tmp, "b", UNCOLLECTABLE))
        self.assertEqual(failing["status"], "TESTS_FAILED")
        self.assertIsInstance(failing["peak_rss_bytes"], int)
        self.assertEqual(broken["status"], "COLLECTION_ERROR")
        self.assertEqual(broken["peak_rss_bytes"], "UNKNOWN")

    def test_timeout_yields_UNKNOWN(self):
        lane = make_lane(self.tmp, "slow", """
            import time, unittest
            class T(unittest.TestCase):
                def test_slow(self):
                    time.sleep(30)
        """)
        r = mm.measure_lane(lane, timeout=2)
        self.assertEqual(r["status"], "TIMEOUT")
        self.assertEqual(r["peak_rss_bytes"], "UNKNOWN")

    def test_missing_directory_is_an_error_not_a_pass(self):
        r = mm.measure_lane(self.tmp / "does-not-exist")
        self.assertEqual(r["status"], "ERROR")
        self.assertEqual(r["peak_rss_bytes"], "UNKNOWN")


class TestSummaryAndReport(TempCase):
    def _report(self):
        make_lane(self.tmp, "uiowa_rfq_18649_a", PASSING)
        make_lane(self.tmp, "uiowa_rfq_18649_b", HUNGRY)
        make_lane(self.tmp, "uiowa_rfq_18649_c", None)
        return mm.measure_all(self.tmp, "uiowa_rfq_18649_*", timeout=60)

    def test_summary_counts_usable_and_unusable_separately(self):
        report = self._report()
        s = report["summary"]
        self.assertEqual(s["lanes_found"], 3)
        self.assertEqual(s["lanes_with_a_usable_figure"], 2)
        self.assertEqual(s["lanes_without_a_usable_figure"], 1)
        self.assertEqual(s["by_status"]["NO_TESTS"], 1)

    def test_highest_peak_is_the_hungry_lane(self):
        report = self._report()
        self.assertEqual(report["summary"]["highest_peak_lane"], "uiowa_rfq_18649_b")

    def test_unknown_lanes_do_not_drag_the_summary_toward_zero(self):
        """A NO_TESTS lane must not become the 'lowest peak'."""
        report = self._report()
        self.assertEqual(report["summary"]["lowest_peak_lane"], "uiowa_rfq_18649_a")

    def test_report_keeps_baseline_visible_rather_than_subtracting_it(self):
        report = self._report()
        text = mm.render(report)
        self.assertIn("baseline", text.lower())
        self.assertIn("every figure below includes this", text)

    def test_report_marks_unknowns_and_disclaims_scoring(self):
        report = self._report()
        text = mm.render(report)
        self.assertIn("UNKNOWN", text)
        self.assertIn("it does not mean the lane is free", text)
        self.assertIn("Not a score", text)

    def test_no_lanes_found_is_zero_lanes_and_UNKNOWN_peaks(self):
        report = mm.measure_all(self.tmp, "no_such_prefix_*", timeout=10)
        self.assertEqual(report["summary"]["lanes_found"], 0)
        self.assertEqual(report["summary"]["highest_peak_rss_bytes"], "UNKNOWN")
        mm.render(report)  # must still render

    def test_environment_is_recorded_with_the_numbers(self):
        env = mm.environment()
        for key in ("python_version", "platform", "probe", "unit_note", "measured_at_utc"):
            self.assertIn(key, env)
            self.assertTrue(env[key])


class TestProbeIsolation(TempCase):
    def test_probe_emits_only_json_on_stdout(self):
        """The parent parses stdout, so a chatty suite must not corrupt it."""
        lane = make_lane(self.tmp, "chatty", """
            import unittest
            print("this should not reach the parent's stdout")
            class T(unittest.TestCase):
                def test_prints(self):
                    print("nor should this")
                    self.assertTrue(True)
        """)
        proc = subprocess.run([sys.executable, str(HERE / "mem_probe.py"), str(lane)],
                              capture_output=True, text=True, timeout=60)
        payload = json.loads(proc.stdout.strip())
        self.assertEqual(payload["status"], "OK")
        self.assertNotIn("should not reach", proc.stdout)

    def test_probe_does_not_write_into_the_lane_it_measures(self):
        lane = make_lane(self.tmp, "readonly", PASSING)
        before = sorted(p.name for p in lane.iterdir())
        mm.measure_lane(lane)
        after = sorted(p.name for p in lane.iterdir() if p.name != "__pycache__")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
