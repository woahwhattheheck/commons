#!/usr/bin/env python3
"""Contract for reconcile/build_sync.py and its one consumer.

build_sync fills the sync.json rows CODEX_SOL specified; staleness_alarm posts
when a row reads STALE or GAP. These tests build fixtures on disk, run the real
builder, and hand its output to the real alarm, so the two cannot drift apart.
Nothing here asserts the live board's current state: a test that pins today's
state goes red the day the board moves.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "reconcile"))

import build_sync  # noqa: E402
import host_offload.staleness_alarm as alarm  # noqa: E402

STATES = {"SYNCED", "STALE", "GAP", "UNMEASURED"}


def rec(rid, durable, **extra):
    out = {"id": rid, "durable_ts": durable, "from": "X", "to": "TABLE"}
    out.update(extra)
    return out


class Repo(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="build-sync-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "feed"))
        self.put("pulse.json", {"seq": 7, "head": "abc123",
                                "ts": "2026-09-10T20:00:00Z"})

    def put(self, rel, value):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(value, fh)

    def recent(self, *records):
        self.put("recent.json", list(records))

    def shard(self, name, newest):
        self.put("feed/%s.json" % name,
                 {"covers": {"newest": newest, "oldest": newest}, "events": []})

    def sinks(self, now=None):
        payload = build_sync.build(self.root, now)
        return payload, {s["name"]: s for s in payload["sinks"]}


class TestFeedShards(Repo):
    def test_shards_cut_from_the_newest_recent_read_synced(self):
        self.recent(rec("a", "2026-09-10T19:00:00Z"),
                    rec("b", "2026-09-10T19:30:00Z"))
        self.shard("head", "2026-09-10T19:30:00Z|b")
        self.shard("window", "2026-09-10T19:30:00Z|b")
        _, rows = self.sinks()
        for name in ("feed/head.json", "feed/window.json"):
            self.assertEqual(rows[name]["state"], "SYNCED")
            self.assertEqual(rows[name]["missing_count"], 0)
            self.assertEqual(rows[name]["gap_seconds"], 0)

    def test_a_shard_left_behind_by_a_lost_push_reads_gap(self):
        self.recent(rec("a", "2026-09-10T19:00:00Z"),
                    rec("b", "2026-09-10T19:30:00Z"),
                    rec("c", "2026-09-10T19:40:00Z"))
        self.shard("head", "2026-09-10T19:00:00Z|a")
        self.shard("window", "2026-09-10T19:40:00Z|c")
        _, rows = self.sinks()
        head = rows["feed/head.json"]
        self.assertEqual(head["state"], "GAP")
        self.assertEqual(head["missing_count"], 2)
        self.assertEqual(head["gap_seconds"], 2400)
        self.assertEqual(head["latest_source_ts"], "2026-09-10T19:40:00Z")
        self.assertEqual(head["latest_durable_ts"], "2026-09-10T19:00:00Z")
        self.assertEqual(rows["feed/window.json"]["state"], "SYNCED")

    def test_events_sharing_the_boundary_second_are_counted_by_cursor(self):
        """Many records share one durable_ts; the id breaks the tie."""
        self.recent(rec("a", "2026-09-10T19:00:00Z"),
                    rec("b", "2026-09-10T19:00:00Z"))
        self.shard("head", "2026-09-10T19:00:00Z|a")
        self.shard("window", "2026-09-10T19:00:00Z|b")
        _, rows = self.sinks()
        self.assertEqual(rows["feed/head.json"]["state"], "GAP")
        self.assertEqual(rows["feed/head.json"]["missing_count"], 1)
        self.assertEqual(rows["feed/window.json"]["state"], "SYNCED")

    def test_a_missing_shard_beside_a_live_source_is_a_gap_not_an_unknown(self):
        self.recent(rec("a", "2026-09-10T19:00:00Z"))
        self.shard("window", "2026-09-10T19:00:00Z|a")
        _, rows = self.sinks()
        self.assertEqual(rows["feed/head.json"]["state"], "GAP")
        self.assertIn("feed/head.json MISSING", rows["feed/head.json"]["detail"])

    def test_an_unreadable_source_is_unmeasured_never_synced(self):
        self.shard("head", "2026-09-10T19:00:00Z|a")
        _, rows = self.sinks()
        self.assertEqual(rows["feed/head.json"]["state"], "UNMEASURED")
        with open(os.path.join(self.root, "recent.json"), "w") as fh:
            fh.write("{broken")
        _, rows = self.sinks()
        self.assertEqual(rows["feed/head.json"]["state"], "UNMEASURED")
        self.assertIn("UNREADABLE", rows["feed/head.json"]["detail"])


class TestSeatCensus(Repo):
    def census(self, rows):
        self.put("seats.json", {"reference_time": "2026-09-10T19:59:00Z",
                                "inputs": {"posts.json": {"state": "READ",
                                                          "rows": rows}}})

    def test_census_that_read_every_post_is_synced(self):
        self.put("posts.json", [rec("a", "t"), rec("b", "t")])
        self.census(2)
        _, rows = self.sinks()
        self.assertEqual(rows["seats.json"]["state"], "SYNCED")

    def test_census_built_from_an_older_posts_json_is_a_gap(self):
        self.put("posts.json", [rec("a", "t"), rec("b", "t"), rec("c", "t")])
        self.census(1)
        _, rows = self.sinks()
        self.assertEqual(rows["seats.json"]["state"], "GAP")
        self.assertEqual(rows["seats.json"]["missing_count"], 2)

    def test_a_census_that_does_not_say_what_it_read_is_unmeasured(self):
        self.put("posts.json", [rec("a", "t")])
        self.put("seats.json", {"reference_time": "2026-09-10T19:59:00Z"})
        _, rows = self.sinks()
        self.assertEqual(rows["seats.json"]["state"], "UNMEASURED")


class TestSlack(Repo):
    def landed(self, *native):
        self.put("posts.json", [
            rec("s%d" % i, "2026-09-10T19:00:00Z",
                observed_event="slack:C0BRGMDQB6G:%s:1" % ts)
            for i, ts in enumerate(native)] + [rec("other", "t")])

    def observe(self, source_ts, observed_at):
        self.put("reconcile/observations/slack-commons.json",
                 {"sink": "slack:C0BRGMDQB6G", "latest_source_ts": source_ts,
                  "observed_at": observed_at, "observer": "TEST"})

    def test_without_an_observation_slack_is_unmeasured_with_its_landed_edge(self):
        self.landed("1789080000.000100", "1789083600.000200")
        _, rows = self.sinks()
        slack = rows["slack:C0BRGMDQB6G"]
        self.assertEqual(slack["state"], "UNMEASURED")
        self.assertEqual(slack["latest_durable_ts"], "2026-09-10T23:40:00Z")
        self.assertIn("2 landed posts", slack["detail"])

    def test_a_fresh_observation_well_ahead_of_landing_reads_stale(self):
        self.landed("1789080000.000100")          # 2026-09-10T22:40:00Z
        self.observe("1789090000.000100", "2026-09-11T01:30:00Z")
        _, rows = self.sinks(now="2026-09-11T01:31:00Z")
        slack = rows["slack:C0BRGMDQB6G"]
        self.assertEqual(slack["state"], "STALE")
        self.assertEqual(slack["gap_seconds"], 10000)

    def test_a_fresh_observation_close_behind_reads_synced(self):
        self.landed("1789080000.000100")
        self.observe("1789080600.000100", "2026-09-10T22:55:00Z")
        _, rows = self.sinks(now="2026-09-10T23:00:00Z")
        self.assertEqual(rows["slack:C0BRGMDQB6G"]["state"], "SYNCED")

    def test_an_old_observation_proves_nothing_and_reads_unmeasured(self):
        self.landed("1789080000.000100")
        self.observe("1789090000.000100", "2026-09-10T10:00:00Z")
        _, rows = self.sinks(now="2026-09-11T01:00:00Z")
        self.assertEqual(rows["slack:C0BRGMDQB6G"]["state"], "UNMEASURED")


class TestTheAlarmReadsWhatTheBuilderWrites(Repo):
    def test_gap_rows_alarm_and_quiet_rows_do_not(self):
        self.recent(rec("a", "2026-09-10T19:00:00Z"),
                    rec("b", "2026-09-10T19:30:00Z"))
        self.shard("head", "2026-09-10T19:00:00Z|a")       # GAP
        self.shard("window", "2026-09-10T19:30:00Z|b")     # SYNCED
        self.put("posts.json", [rec("a", "t")])
        self.put("seats.json", {"inputs": {"posts.json": {"state": "READ",
                                                          "rows": 1}}})  # SYNCED
        payload = build_sync.write(self.root)              # slack UNMEASURED
        with open(os.path.join(self.root, "sync.json"), encoding="utf-8") as fh:
            on_disk = json.load(fh)
        self.assertEqual(on_disk, payload)
        stale = alarm.stale_sinks(on_disk, now=1789080000, threshold_seconds=300)
        self.assertEqual([s["sink"] for s in stale], ["feed/head.json"])
        self.assertEqual(stale[0]["missing_count"], 1)

    def test_a_fully_synced_board_keeps_the_alarm_quiet(self):
        self.recent(rec("a", "2026-09-10T19:00:00Z"))
        self.shard("head", "2026-09-10T19:00:00Z|a")
        self.shard("window", "2026-09-10T19:00:00Z|a")
        self.put("posts.json", [rec("a", "t")])
        self.put("seats.json", {"inputs": {"posts.json": {"state": "READ",
                                                          "rows": 1}}})
        stale = alarm.stale_sinks(build_sync.build(self.root), now=1789080000)
        self.assertEqual(stale, [])


class TestShape(Repo):
    def test_contract_fields_and_byte_stability(self):
        self.recent(rec("a", "2026-09-10T19:00:00Z"))
        payload, _ = self.sinks()
        self.assertEqual(payload["schema"], "commons-sync/v1")
        self.assertEqual(payload["generated_at"], "2026-09-10T20:00:00Z")
        self.assertEqual(payload["source_sha"], "abc123")
        for sink in payload["sinks"]:
            self.assertEqual(set(sink), {
                "name", "state", "latest_source_ts", "latest_durable_ts",
                "gap_seconds", "missing_count", "detail"})
            self.assertIn(sink["state"], STATES)
        self.assertEqual(json.dumps(build_sync.build(self.root), sort_keys=True),
                         json.dumps(build_sync.build(self.root), sort_keys=True))

    def test_the_live_tree_builds_rows_of_the_contract_shape(self):
        """Shape only; the live board's state is whatever it is today."""
        payload = build_sync.build(HERE)
        self.assertEqual(payload["schema"], "commons-sync/v1")
        self.assertTrue(payload["sinks"])
        for sink in payload["sinks"]:
            self.assertIn(sink["state"], STATES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
