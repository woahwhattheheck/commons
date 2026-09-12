#!/usr/bin/env python3
"""Offline contracts for atomic Commons claim aliases."""

import datetime as dt
import os
import shutil
import subprocess
import tempfile
import unittest

from host import coordination_claims as claims
from host import coordination_state as cs

ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
}


def sh(root, *args):
    env = dict(os.environ)
    env.update(ENV)
    done = subprocess.run(
        ["git", "-C", root] + list(args),
        capture_output=True,
        text=True,
        env=env,
    )
    if done.returncode != 0:
        raise AssertionError("git %s failed: %s" % (args, done.stderr))
    return done.stdout.strip()


class AtomicClaimAliases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="coordination-claim-aliases-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.remote = os.path.join(self.tmp, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", self.remote], check=True)
        self.a = self.clone("a")
        self.b = self.clone("b")
        self.t0 = dt.datetime(2026, 9, 12, 23, 40, tzinfo=dt.timezone.utc)

    def clone(self, name):
        root = os.path.join(self.tmp, name)
        subprocess.run(["git", "init", "-q", root], check=True)
        sh(root, "remote", "add", "origin", self.remote)
        return cs.Git(root)

    def test_alias_set_includes_canonical_pr_and_operation(self):
        self.assertEqual(
            ["pr-13490", "titan-v5-p01-publication-custody-closure"],
            claims.alias_keys(
                "TITAN-V5-P01-PUBLICATION-CUSTODY-CLOSURE-20260912-01",
                pr=13490,
            ),
        )

    def test_different_operation_names_conflict_on_same_pr_without_partial_write(self):
        left = claims.alias_keys("OP-A-20260912-01", pr=13490)
        right = claims.alias_keys("OP-B-20260912-01", pr=13490)
        first = claims.holding_write_aliases(
            self.a, left, "Z-HELIX", "take", ttl_s=600, now=self.t0
        )
        self.assertTrue(first["ok"])

        second = claims.holding_write_aliases(
            self.b,
            right,
            "ARIADNE",
            "take",
            ttl_s=600,
            now=self.t0 + dt.timedelta(seconds=10),
        )
        self.assertFalse(second["ok"])
        self.assertEqual("Z-HELIX", second["held_by"])
        self.assertEqual(["pr-13490"], [c["key"] for c in second["conflicts"]])

        listing = cs.holdings_list(
            self.b, now=self.t0 + dt.timedelta(seconds=11)
        )
        by_key = {row["key"]: row for row in listing["holdings"]}
        self.assertIn("op-a", by_key)
        self.assertIn("pr-13490", by_key)
        self.assertNotIn("op-b", by_key)

    def test_expired_pr_alias_allows_atomic_takeover(self):
        first = claims.holding_write_aliases(
            self.a,
            claims.alias_keys("OP-A", pr=13490),
            "Z-HELIX",
            "take",
            ttl_s=60,
            now=self.t0,
        )
        self.assertTrue(first["ok"])
        second = claims.holding_write_aliases(
            self.b,
            claims.alias_keys("OP-B", pr=13490),
            "ARIADNE",
            "take",
            ttl_s=600,
            now=self.t0 + dt.timedelta(seconds=61),
        )
        self.assertTrue(second["ok"])
        self.assertEqual(
            "Z-HELIX", second["records"]["pr-13490"]["previous_holder"]
        )
        self.assertEqual(
            ["op-b", "pr-13490"], second["records"]["pr-13490"]["aliases"]
        )

    def test_nonfastforward_retry_rereads_all_aliases(self):
        seed = cs.holding_write(self.a, "seed", "BASE", "take", now=self.t0)
        self.assertTrue(seed["ok"])
        stale_tip = seed["commit"]

        won = claims.holding_write_aliases(
            self.a,
            claims.alias_keys("OP-A", pr=13490),
            "Z-HELIX",
            "take",
            now=self.t0 + dt.timedelta(seconds=1),
        )
        self.assertTrue(won["ok"])

        real = cs._remote_tip
        calls = {"n": 0}

        def stale_then_real(git, branch, remote="origin"):
            calls["n"] += 1
            return stale_tip if calls["n"] == 1 else real(git, branch, remote)

        cs._remote_tip = stale_then_real
        try:
            lost = claims.holding_write_aliases(
                self.b,
                claims.alias_keys("OP-B", pr=13490),
                "ARIADNE",
                "take",
                now=self.t0 + dt.timedelta(seconds=2),
            )
        finally:
            cs._remote_tip = real

        self.assertFalse(lost["ok"])
        self.assertEqual("Z-HELIX", lost["held_by"])
        self.assertGreaterEqual(calls["n"], 2)
        listing = cs.holdings_list(
            self.b, now=self.t0 + dt.timedelta(seconds=3)
        )
        self.assertNotIn(
            "op-b", {row["key"] for row in listing["holdings"]}
        )

    def test_release_conflict_does_not_partially_release_other_alias(self):
        keys = claims.alias_keys("OP-A", pr=13490)
        first = claims.holding_write_aliases(
            self.a, keys, "Z-HELIX", "take", ttl_s=60, now=self.t0
        )
        self.assertTrue(first["ok"])

        takeover = cs.holding_write(
            self.b,
            "pr-13490",
            "ARIADNE",
            "take",
            ttl_s=600,
            now=self.t0 + dt.timedelta(seconds=61),
        )
        self.assertTrue(takeover["ok"])

        failed = claims.holding_write_aliases(
            self.a, keys, "Z-HELIX", "release",
            now=self.t0 + dt.timedelta(seconds=62),
        )
        self.assertFalse(failed["ok"])
        self.assertEqual("ARIADNE", failed["held_by"])

        listing = cs.holdings_list(
            self.a, now=self.t0 + dt.timedelta(seconds=63)
        )
        rows = {row["key"]: row for row in listing["holdings"]}
        self.assertEqual("HELD", rows["op-a"]["state"])
        self.assertEqual("Z-HELIX", rows["op-a"]["holder"])
        self.assertEqual("ARIADNE", rows["pr-13490"]["holder"])


if __name__ == "__main__":
    unittest.main()
