#!/usr/bin/env python3
"""Contract for host/feed_delta.py — the seq-keyed delta shards.

The self-test inside the module covers ordering, cursors and shard shape. This
covers the parts that only exist on disk: writing, no-op byte stability, the
fail-closed path when the bake is unreadable, and the reader helper.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from host import feed_delta  # noqa: E402


def bake(n=5, start=10):
    """A small recent.json-shaped bake, newest last so order is not free."""
    rows = []
    for i in range(n):
        rows.append({
            "id": "post-%02d" % i,
            "from": "SEAT%d" % (i % 2),
            "to": "TABLE",
            "ts": "2026-09-10T%02d:00:00Z" % (start + i),
            "durable_ts": "2026-09-10T%02d:30:00Z" % (start + i),
            "state": "DURABLE_PAGE",
            "body": "body of post %d " % i + "z" * 400,
        })
    return rows


class TempRepo(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="feed-delta-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def write(self, name, payload):
        with open(os.path.join(self.root, name), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    def read(self, rel):
        with open(os.path.join(self.root, rel), encoding="utf-8") as fh:
            return fh.read()


class TestSelfContract(unittest.TestCase):
    def test_module_self_test_passes(self):
        self.assertEqual(feed_delta.self_test(), 0)


class TestWrite(TempRepo):
    def test_writes_both_shards_and_orders_newest_first(self):
        self.write("recent.json", bake())
        self.write("pulse.json", {"seq": 42, "head": "deadbeef",
                                  "ts": "2026-09-10T20:00:00Z"})
        written, report = feed_delta.write_shards(self.root)
        self.assertEqual(sorted(written),
                         ["feed/head.json", "feed/window.json"])

        head = json.loads(self.read("feed/head.json"))
        self.assertEqual(head["schema"], feed_delta.SCHEMA)
        self.assertEqual(head["source"]["pulse_seq"], 42)
        self.assertEqual(head["source"]["head"], "deadbeef")
        cursors = [e["c"] for e in head["events"]]
        self.assertEqual(cursors, sorted(cursors, reverse=True))
        self.assertEqual(head["count"], 5)
        self.assertEqual(head["complete_since"], cursors[-1])

        window = json.loads(self.read("feed/window.json"))
        self.assertEqual(window["count"], 5)
        self.assertTrue(all("x" not in e for e in window["events"]))
        self.assertEqual(window["excerpt_chars"], 0)
        self.assertTrue(any("x" in e for e in head["events"]))

    def test_head_is_far_smaller_than_a_full_bake_read(self):
        """The whole point: the cheap check must have a cheap answer."""
        rows = bake(400, start=0)
        for i, row in enumerate(rows):
            row["durable_ts"] = "2026-09-%02dT00:%02d:00Z" % (1 + i // 60, i % 60)
        self.write("recent.json", rows)
        self.write("pulse.json", {"seq": 1})
        feed_delta.write_shards(self.root)
        full = os.path.getsize(os.path.join(self.root, "recent.json"))
        head = os.path.getsize(os.path.join(self.root, "feed", "head.json"))
        self.assertLess(head * 5, full,
                        "head shard should be a fraction of the full bake")

    def test_rebuild_with_unchanged_inputs_is_byte_identical(self):
        self.write("recent.json", bake())
        self.write("pulse.json", {"seq": 1})
        feed_delta.write_shards(self.root)
        first = self.read("feed/head.json")
        written, report = feed_delta.write_shards(self.root)
        self.assertEqual(written, [], "a no-op rebuild must not rewrite")
        self.assertEqual(self.read("feed/head.json"), first)
        self.assertTrue(all(not row["changed"] for row in report))

    def test_new_post_advances_the_shard(self):
        rows = bake()
        self.write("recent.json", rows)
        self.write("pulse.json", {"seq": 1})
        feed_delta.write_shards(self.root)
        before = json.loads(self.read("feed/head.json"))["covers"]["newest"]
        rows.append({"id": "post-new", "from": "SEAT9",
                     "ts": "2026-09-11T00:00:00Z",
                     "durable_ts": "2026-09-11T00:30:00Z", "body": "new"})
        self.write("recent.json", rows)
        written, _ = feed_delta.write_shards(self.root)
        self.assertIn("feed/head.json", written)
        after = json.loads(self.read("feed/head.json"))
        self.assertNotEqual(after["covers"]["newest"], before)
        self.assertTrue(after["covers"]["newest"].endswith("|post-new"))


class TestHonesty(TempRepo):
    def test_unreadable_bake_writes_nothing_and_fails(self):
        with open(os.path.join(self.root, "recent.json"), "w",
                  encoding="utf-8") as fh:
            fh.write("{ not json")
        with self.assertRaises(SystemExit) as caught:
            feed_delta.write_shards(self.root)
        self.assertEqual(caught.exception.code, 2)
        self.assertFalse(os.path.exists(os.path.join(self.root, "feed")))

    def test_empty_bake_is_not_published_as_a_quiet_board(self):
        self.write("recent.json", [])
        with self.assertRaises(SystemExit):
            feed_delta.write_shards(self.root)

    def test_undated_records_are_named_not_dropped(self):
        rows = bake(2)
        rows.append({"id": "no-clock", "from": "SEAT", "body": "x"})
        self.write("recent.json", rows)
        self.write("pulse.json", {"seq": 1})
        feed_delta.write_shards(self.root)
        head = json.loads(self.read("feed/head.json"))
        self.assertEqual(head["undated"], ["no-clock"])
        self.assertEqual(head["count"], 2)
        self.assertEqual(head["source"]["records"], 3)
        self.assertEqual(head["source"]["dated"], 2)

    def test_missing_pulse_still_builds(self):
        self.write("recent.json", bake())
        feed_delta.write_shards(self.root)
        head = json.loads(self.read("feed/head.json"))
        self.assertIsNone(head["source"]["pulse_seq"])
        self.assertEqual(head["count"], 5)


class TestReader(TempRepo):
    def setUp(self):
        super().setUp()
        self.write("recent.json", bake())
        self.write("pulse.json", {"seq": 9})
        feed_delta.write_shards(self.root)
        self.head = json.loads(self.read("feed/head.json"))

    def test_since_returns_only_newer_events(self):
        cursors = [e["c"] for e in self.head["events"]]
        result = feed_delta.since(cursors[2], self.root)
        self.assertEqual(result["state"], "COMPLETE")
        self.assertEqual(result["count"], 2)
        self.assertEqual([e["c"] for e in result["events"]], cursors[:2])
        self.assertEqual(result["pulse_seq"], 9)

    def test_current_cursor_returns_nothing(self):
        newest = self.head["covers"]["newest"]
        self.assertEqual(feed_delta.since(newest, self.root)["count"], 0)

    def test_empty_cursor_returns_everything_in_the_shard(self):
        result = feed_delta.since("", self.root)
        self.assertEqual(result["count"], self.head["count"])
        self.assertEqual(result["state"], "COMPLETE")

    def test_gap_wider_than_shard_is_declared_not_silently_short(self):
        result = feed_delta.since("2000-01-01T00:00:00Z|ancient", self.root)
        self.assertEqual(result["state"], "GAP_EXCEEDS_SHARD")
        self.assertEqual(result["complete_since"], self.head["complete_since"])

    def test_missing_shard_reports_finder_failed_not_empty(self):
        os.remove(os.path.join(self.root, "feed", "head.json"))
        result = feed_delta.since("", self.root)
        self.assertEqual(result["state"], "FINDER-FAILED")
        self.assertEqual(result["events"], [])


class TestCursor(unittest.TestCase):
    def test_events_sharing_a_landing_second_both_survive(self):
        rows = [
            {"id": "b", "durable_ts": "2026-09-10T10:00:00Z"},
            {"id": "a", "durable_ts": "2026-09-10T10:00:00Z"},
        ]
        payload = feed_delta.build(rows, {}, "head", 60, 0)
        self.assertEqual(payload["count"], 2)
        cursors = [e["c"] for e in payload["events"]]
        self.assertEqual(cursors, sorted(cursors, reverse=True))
        # A reader holding the older of the two still sees the newer one.
        remaining = [c for c in cursors if c > cursors[1]]
        self.assertEqual(remaining, [cursors[0]])

    def test_landing_order_not_author_order(self):
        """A late-ingested older post must not be skipped by a newer cursor."""
        rows = [
            {"id": "recent-author", "ts": "2026-09-10T09:00:00Z",
             "durable_ts": "2026-09-10T09:05:00Z"},
            {"id": "old-author-late-landing", "ts": "2026-09-01T00:00:00Z",
             "durable_ts": "2026-09-10T09:10:00Z"},
        ]
        payload = feed_delta.build(rows, {}, "head", 60, 0)
        self.assertTrue(
            payload["events"][0]["c"].endswith("|old-author-late-landing"),
            "landing time orders the feed, so a late arrival is not missed")

    def test_id_recovery_survives_a_pipe_in_the_id(self):
        payload = feed_delta.build(
            [{"id": "we|ird", "durable_ts": "2026-09-10T10:00:00Z"}],
            {}, "head", 60, 0)
        self.assertEqual(payload["events"][0]["c"].split("|", 1)[1], "we|ird")

    def test_author_time_carried_only_when_it_differs(self):
        same = feed_delta.build(
            [{"id": "x", "ts": "2026-09-10T10:00:00Z",
              "durable_ts": "2026-09-10T10:00:00Z"}], {}, "head", 60, 0)
        self.assertNotIn("ts", same["events"][0])
        differs = feed_delta.build(
            [{"id": "x", "ts": "2026-09-10T08:00:00Z",
              "durable_ts": "2026-09-10T10:00:00Z"}], {}, "head", 60, 0)
        self.assertEqual(differs["events"][0]["ts"], "2026-09-10T08:00:00Z")


if __name__ == "__main__":
    unittest.main(verbosity=2)
