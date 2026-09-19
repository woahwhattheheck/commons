#!/usr/bin/env python3
"""Tests for the dedup strategies and the measurement harness.

The contract being defended: every strategy returns each distinct item exactly
once, in FIRST-SEEN order. A faster function that reorders the result is broken,
not optimized, so equivalence is asserted before any timing is trusted.

Run:  python3 -m unittest discover -v
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import bench_dedup
import dedup

HASHABLE_CASES = {
    "empty": [],
    "single": ["a"],
    "no_duplicates": ["a", "b", "c"],
    "all_identical": ["a", "a", "a", "a"],
    "duplicates_interleaved": ["a", "b", "a", "c", "b", "a"],
    "first_seen_order_matters": ["c", "a", "b", "a", "c"],
    "numbers": [3, 1, 2, 1, 3, 3],
    "mixed_types": ["1", 1, "1", 1, True],
    "unicode": ["中文", "café", "中文", "cafe"],
    "empty_strings": ["", "a", "", "b"],
    "none_values": [None, "a", None],
}


class TestAllStrategiesAgree(unittest.TestCase):
    def test_every_strategy_matches_the_current_behaviour(self):
        """`list_scan` is what the kit does today, so it is the reference."""
        for case, items in HASHABLE_CASES.items():
            expected = dedup.dedup_list_scan(items)
            for name, (fn, _) in dedup.STRATEGIES.items():
                with self.subTest(case=case, strategy=name):
                    self.assertEqual(fn(items), expected)

    def test_first_seen_order_is_preserved_not_just_membership(self):
        """A set-based rewrite that returns the right ITEMS in the wrong ORDER
        would pass a naive test. It must not pass this one."""
        items = ["zebra", "apple", "mango", "apple", "zebra"]
        for name, (fn, _) in dedup.STRATEGIES.items():
            with self.subTest(strategy=name):
                self.assertEqual(fn(items), ["zebra", "apple", "mango"])
                self.assertNotEqual(fn(items), sorted(set(items)))

    def test_result_contains_no_duplicates_and_loses_nothing(self):
        items = ["a", "b", "a", "c", "b"]
        for name, (fn, _) in dedup.STRATEGIES.items():
            with self.subTest(strategy=name):
                out = fn(items)
                self.assertEqual(len(out), len(set(out)))
                self.assertEqual(set(out), set(items))

    def test_input_is_not_mutated(self):
        items = ["a", "b", "a"]
        for name, (fn, _) in dedup.STRATEGIES.items():
            with self.subTest(strategy=name):
                copy = list(items)
                fn(items)
                self.assertEqual(items, copy)

    def test_works_on_a_generator_not_just_a_list(self):
        for name, (fn, _) in dedup.STRATEGIES.items():
            with self.subTest(strategy=name):
                self.assertEqual(fn(x for x in ["a", "b", "a"]), ["a", "b"])


class TestUnhashableElements(unittest.TestCase):
    """Why the recommendation is not simply "use a set"."""

    UNHASHABLE = [{"a": 1}, {"a": 1}, {"b": 2}, [1, 2], [1, 2]]

    def test_the_fast_strategies_refuse_unhashable_input(self):
        """Documenting the real limit: adopting these blindly breaks such a site."""
        for name in ("dict_fromkeys", "set_aside"):
            with self.subTest(strategy=name):
                fn, requires_hashable = dedup.STRATEGIES[name]
                self.assertTrue(requires_hashable)
                with self.assertRaises(TypeError):
                    fn(self.UNHASHABLE)

    def test_current_form_and_recommendation_both_handle_unhashable_input(self):
        expected = dedup.dedup_list_scan(self.UNHASHABLE)
        self.assertEqual(expected, [{"a": 1}, {"b": 2}, [1, 2]])
        self.assertEqual(dedup.ordered_unique(self.UNHASHABLE), expected)

    def test_mixed_hashable_and_unhashable_input(self):
        items = ["a", {"k": 1}, "a", {"k": 1}, "b", [1], [1]]
        self.assertEqual(dedup.ordered_unique(items), dedup.dedup_list_scan(items))

    def test_recommended_strategy_is_one_that_survives_unhashable_input(self):
        fn, requires_hashable = dedup.STRATEGIES[dedup.RECOMMENDED]
        self.assertFalse(requires_hashable)
        fn(self.UNHASHABLE)  # must not raise


class TestHarness(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dedup-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_input_generation_is_deterministic(self):
        self.assertEqual(bench_dedup.make_input(50), bench_dedup.make_input(50))
        self.assertNotEqual(bench_dedup.make_input(50), bench_dedup.make_input(51))

    def test_input_has_the_requested_number_of_distinct_items(self):
        items = bench_dedup.make_input(40)
        self.assertEqual(len(set(items)), 40)
        self.assertEqual(len(items), 40 * bench_dedup.DUPLICATION_FACTOR)

    def test_measurement_produces_real_positive_timings(self):
        rows = bench_dedup.measure(["list_scan", "ordered_unique"], [10, 50], repeats=3)
        self.assertEqual(len(rows), 2)
        for row in rows:
            for name in ("list_scan", "ordered_unique"):
                d = row["strategies"][name]
                self.assertGreater(d["seconds_min"], 0.0)
                self.assertGreater(d["peak_bytes"], 0)
                self.assertEqual(d["samples"], 3)

    def test_measurement_aborts_when_a_strategy_disagrees(self):
        """The equivalence gate must actually gate. Swap in a fast wrong answer
        and confirm the harness refuses to publish timings for it."""
        original = dedup.STRATEGIES["ordered_unique"]
        dedup.STRATEGIES["ordered_unique"] = (lambda items: [], False)
        try:
            with self.assertRaises(SystemExit) as ctx:
                bench_dedup.measure(["list_scan", "ordered_unique"], [10], repeats=1)
            self.assertIn("disagreed", str(ctx.exception))
        finally:
            dedup.STRATEGIES["ordered_unique"] = original

    def test_crossover_returns_UNKNOWN_when_no_measured_point_qualifies(self):
        """An unreached threshold is UNKNOWN, never an extrapolated number."""
        rows = [{"distinct_items": 10, "input_length": 30, "strategies": {
            "list_scan": {"seconds_min": 1.0}, "fast": {"seconds_min": 1.0}}}]
        cx = bench_dedup.find_crossover(rows, "list_scan", "fast", factor=2.0)
        self.assertEqual(cx["distinct_items"], "UNKNOWN")
        self.assertEqual(cx["speedup"], "UNKNOWN")

    def test_crossover_reports_a_measured_point_when_one_qualifies(self):
        rows = [
            {"distinct_items": 10, "strategies": {"list_scan": {"seconds_min": 1.0},
                                                  "fast": {"seconds_min": 0.9}}},
            {"distinct_items": 20, "strategies": {"list_scan": {"seconds_min": 4.0},
                                                  "fast": {"seconds_min": 1.0}}},
        ]
        cx = bench_dedup.find_crossover(rows, "list_scan", "fast", factor=2.0)
        self.assertEqual(cx["distinct_items"], 20)
        self.assertAlmostEqual(cx["speedup"], 4.0)

    def test_hashability_report_is_produced_by_running_not_by_declaring(self):
        report = bench_dedup.hashability_report()
        self.assertFalse(report["dict_fromkeys"]["works_on_unhashable"])
        self.assertIn("TypeError", report["dict_fromkeys"]["error"])
        self.assertTrue(report["ordered_unique"]["works_on_unhashable"])
        self.assertTrue(report["list_scan"]["works_on_unhashable"])

    def test_missing_scan_results_yields_UNKNOWN_not_zero(self):
        """A scan file that isn't there must not be reported as 'no sites'."""
        info = bench_dedup.load_scan_sites(self.tmp / "nope.json")
        self.assertFalse(info["available"])
        self.assertIn("UNKNOWN", info["note"])
        self.assertNotIn("site_count", info)

    def test_present_scan_results_are_counted(self):
        payload = {"environment": {"scanned_at_utc": "2026-09-19T00:00:00Z"},
                   "findings": [
                       {"pattern": "P1_list_membership_in_loop", "file": "a/b.py",
                        "line": 3, "source": "if x not in seen:"},
                       {"pattern": "P2_read_all_then_slice", "file": "a/c.py",
                        "line": 9, "source": "p.read_text()[:500]"}]}
        path = self.tmp / "kit_scan_results.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        info = bench_dedup.load_scan_sites(path)
        self.assertTrue(info["available"])
        self.assertEqual(info["site_count"], 1)
        self.assertIn("UNKNOWN", info["input_sizes"])

    def test_rendered_report_keeps_site_input_sizes_unknown(self):
        report = {
            "environment": bench_dedup.environment(),
            "strategy_order": ["list_scan", "ordered_unique"],
            "measurements": bench_dedup.measure(["list_scan", "ordered_unique"], [10], repeats=2),
            "crossovers": {"ordered_unique vs list_scan (2x faster)":
                           {"distinct_items": "UNKNOWN", "speedup": "UNKNOWN"}},
            "hashability": bench_dedup.hashability_report(),
            "scan_sites": {"available": False, "note": "not found; site count UNKNOWN."},
        }
        text = bench_dedup.render(report)
        self.assertIn("UNKNOWN", text)
        self.assertIn("not a verdict on any site", text)
        self.assertIn("No lane, seat or person is scored", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
