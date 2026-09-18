#!/usr/bin/env python3
"""Real Git graphs with live-clock and controlled-clock measurement boundaries."""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import types
import unittest
from unittest import mock

from host import main_velocity as velocity
import test_main_velocity as fixtures


class MainVelocityTimeBoundsTests(unittest.TestCase):
    # Reuse only the real repository fixture, without inheriting its test cases.
    setUp = fixtures.MainVelocityTests.setUp
    git = fixtures.MainVelocityTests.git
    set_head = fixtures.MainVelocityTests.set_head
    assert_counts = fixtures.MainVelocityTests.assert_counts

    def commit_at(self, stamp, *parents, author_at=None):
        env = dict(os.environ, GIT_AUTHOR_DATE=(author_at or stamp).isoformat(),
                   GIT_COMMITTER_DATE=stamp.isoformat())
        args = ["-c", "commit.gpgsign=false", "commit-tree", self.tree]
        for parent in parents:
            args.extend(["-p", parent])
        args.extend(["-m", "measurement boundary"])
        return self.git(*args, env=env)

    def chain(self, stamps):
        parents = ()
        for stamp in stamps:
            head = self.commit_at(stamp, *parents)
            parents = (head,)
        self.set_head(head)
        return head

    def controlled_measure(self, anchor, *, query_drift=0, resolution_delay=0):
        """Advance virtual clocks, but execute every count against real Git.

        Translate only the old relative-date arguments so baseline and candidate
        see the same virtual clock. Absolute dates pass to Git unchanged.
        """
        original = velocity._git
        clock = [anchor]
        queries = []
        now_calls = []
        relative = {since: minutes for _, since, minutes in velocity.WINDOWS}

        def now(tz):
            now_calls.append(clock[0])
            return clock[0].astimezone(tz)

        def run_git(*args):
            if args[0] == "rev-parse":
                result = original(*args)
                clock[0] += dt.timedelta(seconds=resolution_delay)
                return result
            queries.append(args)
            clock[0] += dt.timedelta(seconds=query_drift)
            translated = []
            for arg in args:
                if arg.startswith("--since-as-filter="):
                    value = arg.split("=", 1)[1]
                    if value in relative:
                        cutoff = clock[0] - dt.timedelta(minutes=relative[value])
                        arg = "--since-as-filter=" + cutoff.isoformat()
                translated.append(arg)
            return original(*translated)

        fake_dt = types.SimpleNamespace(datetime=types.SimpleNamespace(now=now),
                                        timezone=dt.timezone, timedelta=dt.timedelta)
        with mock.patch.object(velocity, "dt", fake_dt), \
                mock.patch.object(velocity, "_git", side_effect=run_git):
            result = velocity.measure()
        return result, queries, now_calls

    def test_live_clock_future_tip_is_not_recent_work(self):
        self.chain([self.now - dt.timedelta(hours=1), self.now + dt.timedelta(days=1)])
        self.assert_counts(velocity.measure(), (1, 1, 1))

    def test_live_clock_walks_through_future_intermediate(self):
        self.chain([self.now - dt.timedelta(hours=2), self.now + dt.timedelta(days=1),
                    self.now - dt.timedelta(hours=1)])
        self.assert_counts(velocity.measure(), (2, 2, 2))

    def test_all_future_cli_json_has_zero_counts_and_normal_schema(self):
        head = self.chain([self.now + dt.timedelta(days=1), self.now + dt.timedelta(days=2)])
        completed = subprocess.run([sys.executable, str(fixtures.SCRIPT), "--json"],
                                   text=True, capture_output=True, check=True)
        result = json.loads(completed.stdout)
        self.assert_counts(result, (0, 0, 0))
        self.assertEqual(result["head"], head)
        self.assertEqual(result["schema"], "commons.main-velocity.v1")
        self.assertFalse(result["high_velocity"])

    def test_all_future_cli_text_keeps_format(self):
        head = self.chain([self.now + dt.timedelta(days=1)])
        completed = subprocess.run([sys.executable, str(fixtures.SCRIPT)],
                                   text=True, capture_output=True, check=True)
        self.assertEqual(completed.stdout,
                         f"head={head} 6h=0 24h=0 7d=0 mode=range_batch\n")

    def test_inclusive_second_boundaries_for_every_window(self):
        anchor = dt.datetime(2026, 8, 15, 12, 0, tzinfo=dt.timezone.utc)
        offsets = [-604801, -604800, -86401, -86400, -21601, -21600, -1, 0, 1]
        self.chain([anchor + dt.timedelta(seconds=n) for n in offsets])
        result, _, _ = self.controlled_measure(anchor)
        self.assert_counts(result, (3, 5, 7))

    def test_query_delays_do_not_move_lower_cutoffs(self):
        anchor = dt.datetime(2026, 8, 15, 12, 0, tzinfo=dt.timezone.utc)
        self.chain([anchor - dt.timedelta(days=7) + dt.timedelta(seconds=90),
                    anchor - dt.timedelta(hours=24) + dt.timedelta(seconds=30)])
        result, _, _ = self.controlled_measure(anchor, query_drift=60)
        self.assert_counts(result, (0, 1, 2))
        self.assertEqual(result["measured_at"], anchor.isoformat())

    def test_clock_is_frozen_before_target_resolution(self):
        anchor = dt.datetime(2026, 8, 15, 12, 0, tzinfo=dt.timezone.utc)
        self.chain([anchor - dt.timedelta(hours=1), anchor + dt.timedelta(hours=1)])
        result, _, calls = self.controlled_measure(anchor, resolution_delay=86400)
        self.assertEqual(calls, [anchor])
        self.assertEqual(result["measured_at"], anchor.isoformat())
        self.assert_counts(result, (1, 1, 1))

    def test_one_second_precision_utc_anchor_binds_all_queries(self):
        anchor = dt.datetime(2026, 8, 15, 12, 0, 0, 123456, tzinfo=dt.timezone.utc)
        self.chain([anchor - dt.timedelta(hours=1)])
        result, queries, calls = self.controlled_measure(anchor)
        expected = anchor.replace(microsecond=0)
        self.assertEqual(calls, [anchor])
        self.assertEqual(result["measured_at"], expected.isoformat())
        self.assertEqual(len(queries), 3)
        for query, (_, _, minutes) in zip(queries, velocity.WINDOWS):
            lower = expected - dt.timedelta(minutes=minutes)
            self.assertIn("--since-as-filter=" + lower.isoformat(), query)
            self.assertIn("--until=" + expected.isoformat(), query)
            self.assertEqual(query[-1], result["head"])

    def test_committer_time_not_author_time_defines_window(self):
        recent = self.now - dt.timedelta(hours=1)
        future = self.now + dt.timedelta(days=1)
        first = self.commit_at(recent, author_at=future)
        self.set_head(self.commit_at(future, first, author_at=recent))
        self.assert_counts(velocity.measure(), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
