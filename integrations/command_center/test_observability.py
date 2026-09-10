#!/usr/bin/env python3
"""Contract for the observability snapshot.

The property that matters here is degradation. A dashboard that renders "0 live
seats" because a file was missing is worse than one that says it could not read
the file, so every source keeps its own status and a missing source leaves its
section null rather than empty.
"""

import json
import os
import shutil
import tempfile
import unittest

from integrations.command_center import observability


class Repo(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cc-observability-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def put(self, rel, payload):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    def complete(self):
        self.put("pulse.json", {
            "seq": 1708, "head": "abc123", "ts": "2026-09-10T19:59:02Z",
            "post_count": 12096,
            "feed": {"delta": "feed/head.json", "full": "recent.json"},
        })
        self.put("feed/head.json", {
            "count": 2,
            "covers": {"newest": "2026-09-10T19:49:51Z|newest-post"},
            "complete_since": "2026-09-09T22:03:40Z|older-post",
            "cursor_rule": "compare c as a string",
            "undated": ["no-clock"],
            "events": [
                {"c": "2026-09-10T19:49:51Z|newest-post", "from": "SEAT_A",
                 "to": "TABLE", "x": "the newest thing"},
                {"c": "2026-09-09T22:03:40Z|older-post", "from": "SEAT_B",
                 "state": "INTEGRATED", "kind": "SHIP_RECEIPT", "x": "older"},
            ],
        })
        self.put("seats.json", {
            "reference_time": "2026-09-10T20:00:00Z",
            "totals": {"seats": 3, "declared": 2, "presence_only": 1},
            "by_liveness": {"LIVE": 1, "QUIET": 1, "COLD": 1},
            "by_harness": {"harness-a": 1, "UNKNOWN": 2},
            "by_kind": {"language-model": 2, "UNKNOWN": 1},
            "context_pressure": [{"seat": "HOT", "pct": 91.0}],
            "budget_watch": [{"seat": "HOT", "remaining_pct": 5}],
            "open_cants": [
                {"seat": "HOT", "what": "no push", "need": "scope",
                 "est_minutes": 5},
                {"seat": "COLDSEAT", "what": "unscoped", "est_minutes": "UNKNOWN"},
            ],
            "unreadable_seat_files": [],
            "seats": [
                {"seat": "HOT", "derived": {"liveness": "LIVE"}},
                {"seat": "COLDSEAT", "derived": {"liveness": "COLD"}},
            ],
            "roster": [{"seat": "NAMEONLY", "liveness": "QUIET"}],
        })


class TestCompleteSnapshot(Repo):
    def setUp(self):
        super().setUp()
        self.complete()
        self.snap = observability.snapshot(self.root)

    def test_all_three_sources_read_and_nothing_is_degraded(self):
        self.assertEqual(self.snap["degraded"], [])
        self.assertTrue(all(s["ok"] for s in self.snap["sources"]))
        self.assertEqual([s["path"] for s in self.snap["sources"]],
                         ["feed/head.json", "pulse.json", "seats.json"])

    def test_pulse_carries_the_cursor_pointers(self):
        self.assertEqual(self.snap["pulse"]["seq"], 1708)
        self.assertEqual(self.snap["pulse"]["feed"]["delta"], "feed/head.json")

    def test_board_events_recover_their_ids_from_the_cursor(self):
        events = self.snap["board"]["events"]
        self.assertEqual(events[0]["id"], "newest-post")
        self.assertEqual(events[0]["from"], "SEAT_A")
        self.assertEqual(events[1]["kind"], "SHIP_RECEIPT")
        self.assertEqual(self.snap["board"]["undated"], ["no-clock"])
        # The default state is restored for display rather than left blank.
        self.assertEqual(events[0]["state"], "DURABLE_PAGE")

    def test_priced_and_unpriced_unblocks_are_separated(self):
        seats = self.snap["seats"]
        self.assertEqual([c["seat"] for c in seats["priced_unblocks"]], ["HOT"])
        self.assertEqual([c["seat"] for c in seats["unpriced_unblocks"]],
                         ["COLDSEAT"])

    def test_routable_seats_exclude_the_cold_and_the_undeclared(self):
        seats = self.snap["seats"]
        self.assertEqual([s["seat"] for s in seats["routable"]], ["HOT"])
        self.assertEqual([r["seat"] for r in seats["awake_undeclared"]],
                         ["NAMEONLY"])

    def test_headline_is_one_readable_line(self):
        self.assertEqual(
            self.snap["headline"],
            "1 live, 1 quiet, 2 events in the delta shard, 1 priced unblocks")

    def test_board_limit_caps_events_without_changing_the_count(self):
        snap = observability.snapshot(self.root, feed_limit=1)
        self.assertEqual(len(snap["board"]["events"]), 1)
        self.assertEqual(snap["board"]["count"], 2)


class TestDegradation(Repo):
    def test_a_missing_source_is_named_not_rendered_as_empty(self):
        self.complete()
        os.remove(os.path.join(self.root, "seats.json"))
        snap = observability.snapshot(self.root)
        self.assertIsNone(snap["seats"])
        self.assertEqual(snap["degraded"], ["seats.json"])
        self.assertIn("could not read seats.json", snap["headline"])
        # The sources that did read are still present and usable.
        self.assertIsNotNone(snap["board"])
        self.assertEqual(snap["pulse"]["seq"], 1708)

    def test_a_malformed_source_is_named_with_its_error(self):
        self.complete()
        with open(os.path.join(self.root, "pulse.json"), "w",
                  encoding="utf-8") as fh:
            fh.write("{ not json")
        snap = observability.snapshot(self.root)
        self.assertIsNone(snap["pulse"])
        entry = [s for s in snap["sources"] if s["path"] == "pulse.json"][0]
        self.assertFalse(entry["ok"])
        self.assertEqual(entry["error"], "JSONDecodeError")

    def test_an_empty_repository_degrades_everywhere_without_raising(self):
        snap = observability.snapshot(self.root)
        self.assertEqual(sorted(snap["degraded"]),
                         ["feed/head.json", "pulse.json", "seats.json"])
        self.assertIsNone(snap["pulse"])
        self.assertIsNone(snap["board"])
        self.assertIsNone(snap["seats"])
        self.assertTrue(snap["headline"].startswith("Partial"))

    def test_snapshot_never_mutates_the_repository(self):
        self.complete()
        before = sorted(
            (os.path.relpath(os.path.join(dirpath, name), self.root),
             os.path.getsize(os.path.join(dirpath, name)))
            for dirpath, _, names in os.walk(self.root) for name in names)
        observability.snapshot(self.root)
        after = sorted(
            (os.path.relpath(os.path.join(dirpath, name), self.root),
             os.path.getsize(os.path.join(dirpath, name)))
            for dirpath, _, names in os.walk(self.root) for name in names)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
