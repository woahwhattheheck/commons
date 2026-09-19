#!/usr/bin/env python3
"""Tests for the claim ledger in fleet.py.

These exercise the two properties the protocol actually depends on:
a second seat cannot take a held order, and a released order becomes
available again. Everything runs against a temp ledger; nothing here
touches a real repository or network.
"""
import importlib.util
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load_fleet(root):
    """Import fleet.py with its paths redirected at a throwaway directory."""
    spec = importlib.util.spec_from_file_location(
        "fleet_under_test", os.path.join(HERE, "fleet.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT = root
    mod.LEDGER = os.path.join(root, "claims.json")
    mod.LOCK = os.path.join(root, ".fleet.lock")
    mod.LANDLOCK = os.path.join(root, ".land.lock")
    mod.STAGING = os.path.join(root, "staging")
    os.makedirs(mod.STAGING, exist_ok=True)
    return mod


class ClaimLedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fleet = load_fleet(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_first_claim_is_granted(self):
        self.assertEqual(self.fleet.claim("SEAT-A", "ORDER-001", "lane_a"), 0)

    def test_second_seat_is_denied_the_same_order(self):
        self.fleet.claim("SEAT-A", "ORDER-001", "lane_a")
        # The whole point of the ledger: a fresh channel read can still be
        # stale by the time two seats act on it, so the grant must be atomic.
        self.assertEqual(self.fleet.claim("SEAT-B", "ORDER-001", "lane_b"), 2)

    def test_holder_may_reclaim_its_own_order(self):
        self.fleet.claim("SEAT-A", "ORDER-001", "lane_a")
        # A retrying seat must not lock itself out of work it already holds.
        self.assertEqual(self.fleet.claim("SEAT-A", "ORDER-001", "lane_a"), 0)

    def test_released_order_returns_to_the_pool(self):
        self.fleet.claim("SEAT-A", "ORDER-001", "lane_a")
        self.fleet.setstate("SEAT-A", "ORDER-001", "released")
        # Yielding a lane to another vendor's swarm has to actually free it.
        self.assertEqual(self.fleet.claim("SEAT-B", "ORDER-001", "lane_b"), 0)

    def test_distinct_orders_do_not_interfere(self):
        self.assertEqual(self.fleet.claim("SEAT-A", "ORDER-001", "lane_a"), 0)
        self.assertEqual(self.fleet.claim("SEAT-B", "ORDER-002", "lane_b"), 0)

    def test_ledger_records_an_event_trail(self):
        self.fleet.claim("SEAT-A", "ORDER-001", "lane_a")
        self.fleet.setstate("SEAT-A", "ORDER-001", "landed")
        data = self.fleet._load()
        kinds = [e["ev"] for e in data["events"]]
        self.assertIn("claim", kinds)
        self.assertIn("landed", kinds)

    def test_seat_may_overwrite_paths_it_landed_itself(self):
        # The gate must not lock a seat out of amending its own work.
        self.fleet._record_owned("SEAT-A", ["lane/thing.py"])
        self.assertIn("lane/thing.py", self.fleet._owned_paths("SEAT-A"))

    def test_ownership_is_per_seat(self):
        # SEAT-B must not inherit SEAT-A's right to overwrite.
        self.fleet._record_owned("SEAT-A", ["lane/thing.py"])
        self.assertNotIn("lane/thing.py", self.fleet._owned_paths("SEAT-B"))

    def test_ownership_records_are_deduplicated(self):
        self.fleet._record_owned("SEAT-A", ["lane/thing.py"])
        self.fleet._record_owned("SEAT-A", ["lane/thing.py"])
        owned = self.fleet._load()["owned"]["SEAT-A"]
        self.assertEqual(owned.count("lane/thing.py"), 1)

    def test_land_refuses_an_empty_staging_directory(self):
        # A seat that built nothing must not produce an empty commit that
        # looks like delivered work.
        os.makedirs(os.path.join(self.tmp.name, "staging", "SEAT-A"), exist_ok=True)
        self.assertEqual(self.fleet.land("SEAT-A", "nothing built"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
