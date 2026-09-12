#!/usr/bin/env python3
"""Offline contract tests for host/claim_pr.py."""

import datetime as dt
import os
import shutil
import subprocess
import tempfile
import unittest

from host import claim_pr
from host import coordination_state as cs


class CanonicalPrClaimTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="claim-pr-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.remote = os.path.join(self.tmp, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", self.remote], check=True)
        self.a = self._client("a")
        self.b = self._client("b")
        self.t0 = dt.datetime(2026, 9, 12, 23, 30, tzinfo=dt.timezone.utc)

    def _client(self, name):
        root = os.path.join(self.tmp, name)
        subprocess.run(["git", "init", "-q", root], check=True)
        subprocess.run(["git", "-C", root, "remote", "add", "origin", self.remote], check=True)
        return cs.Git(root)

    def test_pr_key_is_canonical_and_rejects_alias_inputs(self):
        self.assertEqual("pr-13492", claim_pr.pr_key(13492))
        for value in (0, -1, True, "13492"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                claim_pr.pr_key(value)

    def test_same_pr_two_seats_has_one_live_holder(self):
        first = claim_pr.write_pr_holding(
            self.a, 13492, "ASTRA-A", "take", ttl_s=600, now=self.t0
        )
        self.assertTrue(first["ok"])
        self.assertEqual("pr-13492", first["key"])

        second = claim_pr.write_pr_holding(
            self.b, 13492, "ASTRA-B", "take", ttl_s=600,
            now=self.t0 + dt.timedelta(seconds=30),
        )
        self.assertFalse(second["ok"])
        self.assertEqual("pr-13492", second["key"])
        self.assertEqual("ASTRA-A", second["held_by"])

    def test_different_prs_do_not_collide(self):
        one = claim_pr.write_pr_holding(
            self.a, 13492, "ASTRA-A", "take", ttl_s=600, now=self.t0
        )
        two = claim_pr.write_pr_holding(
            self.b, 13493, "ASTRA-B", "take", ttl_s=600,
            now=self.t0 + dt.timedelta(seconds=1),
        )
        self.assertTrue(one["ok"])
        self.assertTrue(two["ok"])
        self.assertEqual(("pr-13492", "pr-13493"), (one["key"], two["key"]))

    def test_release_allows_successor_to_take_same_pr(self):
        first = claim_pr.write_pr_holding(
            self.a, 13492, "ASTRA-A", "take", ttl_s=600, now=self.t0
        )
        self.assertTrue(first["ok"])
        released = claim_pr.write_pr_holding(
            self.a, 13492, "ASTRA-A", "release", ttl_s=600,
            now=self.t0 + dt.timedelta(seconds=10),
        )
        self.assertTrue(released["ok"])
        successor = claim_pr.write_pr_holding(
            self.b, 13492, "ASTRA-B", "take", ttl_s=600,
            now=self.t0 + dt.timedelta(seconds=20),
        )
        self.assertTrue(successor["ok"])
        self.assertEqual("ASTRA-A", successor["record"]["previous_holder"])

    def test_invalid_action_holder_and_ttl_fail_before_git_write(self):
        bad = [
            {"action": "steal", "holder": "ASTRA", "ttl_s": 600},
            {"action": "take", "holder": "", "ttl_s": 600},
            {"action": "take", "holder": "ASTRA", "ttl_s": 0},
            {"action": "take", "holder": "ASTRA", "ttl_s": 7201},
            {"action": "take", "holder": "ASTRA", "ttl_s": True},
        ]
        for kwargs in bad:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                claim_pr.write_pr_holding(self.a, 13492, now=self.t0, **kwargs)


if __name__ == "__main__":
    unittest.main()
