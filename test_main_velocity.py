#!/usr/bin/env python3
"""Exercise velocity measurements against real temporary Git commit graphs."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from host import main_velocity as velocity


SCRIPT = Path(velocity.__file__).resolve()


class MainVelocityTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="commons-velocity-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        previous_cwd = Path.cwd()
        self.addCleanup(os.chdir, previous_cwd)
        os.chdir(self.root)
        # Isolate the fixture from the caller's Git directory, identity and config.
        environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        environment.update({
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "Commons velocity test",
            "GIT_AUTHOR_EMAIL": "velocity@example.invalid",
            "GIT_COMMITTER_NAME": "Commons velocity test",
            "GIT_COMMITTER_EMAIL": "velocity@example.invalid",
        })
        patch = mock.patch.dict(os.environ, environment, clear=True)
        patch.start()
        self.addCleanup(patch.stop)
        self.git("init", "-q")
        self.tree = self.git("mktree", input_text="")
        self.now = dt.datetime.now(dt.timezone.utc)

    def git(self, *args, input_text=None, env=None):
        return subprocess.run(
            ["git", *args], input=input_text, text=True, capture_output=True,
            check=True, env=env,
        ).stdout.strip()

    def commit(self, age_hours, *parents):
        stamp = (self.now - dt.timedelta(hours=age_hours)).isoformat()
        env = dict(os.environ, GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
        args = ["-c", "commit.gpgsign=false", "commit-tree", self.tree]
        for parent in parents:
            args.extend(["-p", parent])
        args.extend(["-m", "controlled timestamp graph"])
        return self.git(*args, env=env)

    def set_head(self, commit):
        self.git("update-ref", "refs/heads/main", commit)
        self.git("symbolic-ref", "HEAD", "refs/heads/main")

    def inverted_graph(self):
        ancestor = self.commit(1)
        middle = self.commit(240, ancestor)
        head = self.commit(0.5, middle)
        self.set_head(head)
        return ancestor, middle, head

    def assert_counts(self, result, expected):
        self.assertEqual(
            {label: row["commits"] for label, row in result["windows"].items()},
            dict(zip(("6h", "24h", "7d"), expected)),
        )

    def test_recent_ancestor_is_not_hidden_by_old_intermediate(self):
        _, _, head = self.inverted_graph()
        result = velocity.measure()
        self.assertEqual(result["head"], head)
        self.assert_counts(result, (2, 2, 2))

    def test_old_target_still_walks_to_recent_ancestor(self):
        ancestor, middle, _ = self.inverted_graph()
        result = velocity.measure(middle)
        self.assertEqual(result["head"], middle)
        self.assert_counts(result, (1, 1, 1))
        self.assertNotEqual(result["head"], ancestor)

    def test_monotonic_history_preserves_distinct_windows(self):
        head = self.commit(240)
        for age in (48, 12, 1):
            head = self.commit(age, head)
        self.set_head(head)
        self.assert_counts(velocity.measure(), (1, 2, 3))

    def test_merge_graph_counts_shared_recent_ancestor_once(self):
        ancestor = self.commit(1)
        middle = self.commit(240, ancestor)
        left = self.commit(0.5, middle)
        right = self.commit(0.25, middle)
        merge = self.commit(0.1, left, right)
        self.set_head(merge)
        self.assert_counts(velocity.measure(), (4, 4, 4))

    def test_only_target_reachable_commits_are_counted(self):
        ancestor, _, _ = self.inverted_graph()
        other = self.commit(0.1, ancestor)
        self.git("update-ref", "refs/heads/unmerged", other)
        self.assert_counts(velocity.measure(), (2, 2, 2))
        self.assert_counts(velocity.measure("refs/heads/unmerged"), (2, 2, 2))

    def test_all_old_graph_returns_zero_and_default_mode(self):
        root = self.commit(480)
        self.set_head(self.commit(240, root))
        result = velocity.measure()
        self.assert_counts(result, (0, 0, 0))
        self.assertFalse(result["high_velocity"])
        self.assertEqual(result["integration_mode"], "range_batch")

    def test_correct_count_drives_threshold_and_json_cli(self):
        _, _, head = self.inverted_graph()
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--target", head,
             "--high-velocity-per-hour", "0.08", "--json"],
            text=True, capture_output=True, check=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["schema"], "commons.main-velocity.v1")
        self.assertEqual(result["target"], head)
        self.assert_counts(result, (2, 2, 2))
        self.assertEqual(result["windows"]["24h"]["commits_per_hour"], 0.08)
        self.assertEqual(result["windows"]["6h"]["commits_per_minute"], 0.0056)
        self.assertTrue(result["high_velocity"])
        self.assertEqual(result["integration_mode"], "coalesce_ranges")
        self.assertIsNotNone(dt.datetime.fromisoformat(result["measured_at"]).tzinfo)

    def test_text_cli_preserves_format(self):
        head = self.commit(1)
        self.set_head(head)
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)], text=True, capture_output=True, check=True,
        )
        self.assertEqual(
            completed.stdout,
            f"head={head} 6h=1 24h=1 7d=1 mode=range_batch\n",
        )

    def test_ref_is_resolved_once_before_window_queries(self):
        _, _, frozen = self.inverted_graph()
        moved = self.commit(0.1, frozen)
        original = velocity._git

        def git_with_moving_ref(*args):
            output = original(*args)
            if args[0] == "rev-parse":
                self.set_head(moved)
            return output

        with mock.patch.object(velocity, "_git", side_effect=git_with_moving_ref) as calls:
            result = velocity.measure()
        self.assertEqual(result["head"], frozen)
        self.assert_counts(result, (2, 2, 2))
        self.assertEqual(calls.call_count, 4)
        self.assertEqual(self.git("rev-parse", "HEAD"), moved)

    def recent_history(self, count):
        head = self.commit(2)
        for _ in range(count - 1):
            head = self.commit(1, head)
        self.set_head(head)
        return head

    def test_rounding_down_does_not_hide_above_threshold_rate(self):
        self.recent_history(1)
        result = velocity.measure(high_velocity_per_hour=0.041)
        self.assertEqual(result["windows"]["24h"]["commits_per_hour"], 0.04)
        self.assertTrue(result["high_velocity"])
        self.assertEqual(result["integration_mode"], "coalesce_ranges")

    def test_rounding_up_does_not_invent_above_threshold_rate(self):
        self.recent_history(4)
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--high-velocity-per-hour", "0.168", "--json"],
            text=True, capture_output=True, check=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["windows"]["24h"]["commits_per_hour"], 0.17)
        self.assertFalse(result["high_velocity"])
        self.assertEqual(result["integration_mode"], "range_batch")

    def test_exact_threshold_is_inclusive_before_display_rounding(self):
        self.recent_history(3)
        at_threshold = velocity.measure(high_velocity_per_hour=0.125)
        self.assertEqual(at_threshold["windows"]["24h"]["commits_per_hour"], 0.12)
        self.assertTrue(at_threshold["high_velocity"])
        self.assertEqual(at_threshold["integration_mode"], "coalesce_ranges")
        above_threshold = velocity.measure(high_velocity_per_hour=0.126)
        self.assertFalse(above_threshold["high_velocity"])
        self.assertEqual(above_threshold["integration_mode"], "range_batch")

    def test_unknown_target_keeps_git_error(self):
        self.set_head(self.commit(1))
        with self.assertRaises(subprocess.CalledProcessError):
            velocity.measure("missing-ref")


if __name__ == "__main__":
    unittest.main()
