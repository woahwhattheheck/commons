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
            # This reference is intentionally a historical bake reference. The
            # observability reader must not trust its liveness values as current.
            "reference_time": "2026-09-10T20:00:00Z",
            "reference_source": "newest input timestamp unless --now was given",
            "liveness_bands_s": {"LIVE": 900, "QUIET": 3600, "STALE": 86400},
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
                {"seat": "HOT",
                 "declared": {"heartbeat": "2026-09-10T19:55:00Z"},
                 "derived": {"liveness": "LIVE", "heartbeat_age_s": 0}},
                {"seat": "COLDSEAT",
                 "declared": {"heartbeat": "2026-09-01T00:00:00Z"},
                 "derived": {"liveness": "COLD", "heartbeat_age_s": 0}},
            ],
            "roster": [
                {"seat": "NAMEONLY", "heartbeat": "2026-09-10T19:20:00Z",
                 "liveness": "LIVE", "heartbeat_age_s": 0}
            ],
        })
        self.put("feed/github.json", {
            "schema": "commons-github-state/v1",
            "repository": "o/r",
            "counts": {"open_pull_requests": 106, "open_issues": 3,
                       "runs_queued": 2275, "runs_in_progress": 18},
            "queue_depth_per_runner": 126.4,
            "pulls_listed": 100,
            "newest_pulls": [{"number": 12094, "title": "newest",
                              "author": "who", "draft": False,
                              "created_at": "2026-09-10T21:26:14Z",
                              "branch": "b"}],
            "longest_open": [],
            "drafts": 12,
            "undatable_pulls": [],
            "degraded": [],
            "unchanged_since": "2026-09-10T21:30:00Z",
        })


class TestCompleteSnapshot(Repo):
    def setUp(self):
        super().setUp()
        self.complete()
        self.now = "2026-09-10T20:05:00Z"
        self.snap = observability.snapshot(self.root, now=self.now)

    def test_every_source_reads_and_nothing_is_degraded(self):
        self.assertEqual(self.snap["degraded"], [])
        self.assertTrue(all(s["ok"] for s in self.snap["sources"]))
        self.assertEqual([s["path"] for s in self.snap["sources"]],
                         ["feed/github.json", "feed/head.json", "pulse.json",
                          "seats.json"])

    def test_repository_state_travels_through_untouched(self):
        repo = self.snap["repository"]
        self.assertEqual(repo["counts"]["runs_queued"], 2275)
        self.assertEqual(repo["queue_depth_per_runner"], 126.4)
        self.assertEqual(repo["newest_pulls"][0]["number"], 12094)
        self.assertNotIn("age_hours", repo["newest_pulls"][0])

    def test_pulse_carries_the_cursor_pointers(self):
        self.assertEqual(self.snap["pulse"]["seq"], 1708)
        self.assertEqual(self.snap["pulse"]["feed"]["delta"], "feed/head.json")

    def test_board_events_recover_their_ids_from_the_cursor(self):
        events = self.snap["board"]["events"]
        self.assertEqual(events[0]["id"], "newest-post")
        self.assertEqual(events[0]["from"], "SEAT_A")
        self.assertEqual(events[1]["kind"], "SHIP_RECEIPT")
        self.assertEqual(self.snap["board"]["undated"], ["no-clock"])
        self.assertEqual(events[0]["state"], "DURABLE_PAGE")

    def test_priced_and_unpriced_unblocks_are_separated(self):
        seats = self.snap["seats"]
        self.assertEqual([c["seat"] for c in seats["priced_unblocks"]], ["HOT"])
        self.assertEqual([c["seat"] for c in seats["unpriced_unblocks"]],
                         ["COLDSEAT"])

    def test_routable_seats_use_read_time_not_baked_liveness(self):
        seats = self.snap["seats"]
        self.assertEqual([s["seat"] for s in seats["routable"]], ["HOT"])
        self.assertEqual([r["seat"] for r in seats["awake_undeclared"]],
                         ["NAMEONLY"])
        self.assertEqual(seats["reference_time"], self.now)
        self.assertEqual(seats["baked_reference_time"], "2026-09-10T20:00:00Z")
        self.assertEqual(seats["reference_source"], "read-time heartbeat derivation")

    def test_headline_is_one_readable_line(self):
        self.assertEqual(
            self.snap["headline"],
            "1 live, 1 quiet, 2 events in the delta shard, 1 priced unblocks")

    def test_board_limit_caps_events_without_changing_the_count(self):
        snap = observability.snapshot(self.root, feed_limit=1, now=self.now)
        self.assertEqual(len(snap["board"]["events"]), 1)
        self.assertEqual(snap["board"]["count"], 2)


class TestReadTimeLiveness(Repo):
    def test_unchanged_bake_ages_live_to_quiet_to_stale_to_cold(self):
        self.complete()
        path = os.path.join(self.root, "seats.json")
        with open(path, "rb") as fh:
            before = fh.read()

        cases = [
            ("2026-09-10T20:05:00Z", "LIVE", True),
            ("2026-09-10T20:20:00Z", "QUIET", True),
            ("2026-09-10T21:00:01Z", "STALE", False),
            ("2026-09-11T19:55:01Z", "COLD", False),
        ]
        for now, expected, routable in cases:
            snap = observability.snapshot(self.root, now=now)
            hot = [s for s in snap["seats"]["seats"] if s["seat"] == "HOT"][0]
            self.assertEqual(hot["derived"]["liveness"], expected, now)
            routed = [s["seat"] for s in snap["seats"]["routable"]]
            self.assertEqual("HOT" in routed, routable, now)

        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), before,
                             "read-time aging must not mutate the stable bake")

    def test_future_heartbeat_clamps_to_live_zero_age(self):
        self.complete()
        seats = json.loads(open(os.path.join(self.root, "seats.json"),
                                encoding="utf-8").read())
        seats["seats"][0]["declared"]["heartbeat"] = "2026-09-11T00:00:00Z"
        self.put("seats.json", seats)
        snap = observability.snapshot(self.root, now="2026-09-10T20:00:00Z")
        hot = [s for s in snap["seats"]["seats"] if s["seat"] == "HOT"][0]
        self.assertEqual(hot["derived"]["liveness"], "LIVE")
        self.assertEqual(hot["derived"]["heartbeat_age_s"], 0)


class TestDegradation(Repo):
    def test_a_missing_source_is_named_not_rendered_as_empty(self):
        self.complete()
        os.remove(os.path.join(self.root, "seats.json"))
        snap = observability.snapshot(self.root)
        self.assertIsNone(snap["seats"])
        self.assertEqual(snap["degraded"], ["seats.json"])
        self.assertIn("could not read seats.json", snap["headline"])
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
                         ["feed/github.json", "feed/head.json", "pulse.json",
                          "seats.json"])
        self.assertIsNone(snap["pulse"])
        self.assertIsNone(snap["board"])
        self.assertIsNone(snap["seats"])
        self.assertIsNone(snap["repository"])
        self.assertTrue(snap["headline"].startswith("Partial"))

    def test_repository_state_can_be_absent_while_the_rest_reads(self):
        self.complete()
        os.remove(os.path.join(self.root, "feed", "github.json"))
        snap = observability.snapshot(self.root, now="2026-09-10T20:05:00Z")
        self.assertIsNone(snap["repository"])
        self.assertEqual(snap["degraded"], ["feed/github.json"])
        self.assertIsNotNone(snap["board"])
        self.assertIsNotNone(snap["seats"])

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
