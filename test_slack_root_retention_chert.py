"""Synthetic root coverage through the real collector, budget and SQLite store.

No live account, transcript, network request or provider mutation. The existing
production classes are imported unchanged; only provider responses are fixtures.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest

from integrations.command_center.collectors import LiveCollectors
from integrations.command_center.workstreams import WorkstreamStore
from test_slack_root_observations_chert import (
    CHANNEL, ROOT, FIRST, CHILD, page, parent, reply, broadcast,
)

OBSERVED = "2026-09-19T15:00:00Z"


class SyntheticProvider:
    def __init__(self, responses):
        self.responses = copy.deepcopy(responses)
        self.calls = []

    def slack(self, method, params):
        if method not in ("conversations.history", "conversations.replies"):
            raise AssertionError("Unexpected provider mutation")
        self.calls.append((method, copy.deepcopy(params)))
        if not self.responses:
            raise AssertionError("Unexpected extra provider read")
        return self.responses.pop(0)


class StoreRetentionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = WorkstreamStore(self.directory.name)
        self.spec = {"id": CHANNEL, "label": "Synthetic work", "project": "fixture"}

    def collector(self, responses):
        provider = SyntheticProvider(responses)
        config = {"github": {"enabled": False}, "slack": {
            "channels": [self.spec], "workspace_url": "https://fixture.slack.com",
            "max_threads_per_channel": 1}, "page_size": 100}
        collector = LiveCollectors(self.store, config, equipment=provider,
                                   clock=lambda: OBSERVED)
        return collector, provider

    def seed(self):
        collector, _ = self.collector([
            page([parent(2)]), page([parent(2), reply(FIRST), reply()])])
        result = collector.collect()
        self.assertTrue(result["receipts"][0]["coverage"]["complete"])
        first_id = "slack:" + CHANNEL + ":" + FIRST
        self.store.update_work({"operation_id": "synthetic-owner-direction",
            "source_id": "slack:" + CHANNEL, "item_id": first_id,
            "next_action": "Retain this fictional owner direction"})
        return first_id

    def assert_retained(self, item_id, result):
        receipt = result["receipts"][0]
        self.assertFalse(receipt["coverage"]["complete"])
        self.assertEqual(receipt["removed"], 0)
        items = {row["id"]: row for row in self.store.state()["items"]}
        self.assertIn(item_id, items)
        self.assertEqual(items[item_id]["owner_work"]["next_action"],
                         "Retain this fictional owner direction")

    def test_nested_prior_count_preserves_owner_work(self):
        item_id = self.seed()
        collector, provider = self.collector([
            page([broadcast(2)]), page([parent(1), reply()])])
        result = collector.collect()
        self.assert_retained(item_id, result)
        self.assertEqual(result["receipts"][0]["retained"], 1)
        self.assertEqual(len(provider.calls), 2)

    def test_zero_count_known_latest_preserves_owner_work(self):
        item_id = self.seed()
        collector, _ = self.collector([page([parent(0)]), page([parent(0)])])
        result = collector.collect()
        self.assert_retained(item_id, result)
        self.assertEqual(result["receipts"][0]["retained"], 2)

    def test_nested_reply_page_count_preserves_owner_work(self):
        item_id = self.seed()
        nested = {**broadcast(2), "thread_ts": ROOT}
        collector, _ = self.collector([page([parent(1)]), page([parent(1), nested])])
        self.assert_retained(item_id, collector.collect())

    def test_nested_reply_page_anchor_preserves_owner_work(self):
        item_id = self.seed()
        nested = {**broadcast(1, latest=FIRST), "thread_ts": ROOT}
        collector, _ = self.collector([page([parent(1)]), page([parent(1), nested])])
        self.assert_retained(item_id, collector.collect())

    def test_broadcast_type_change_preserves_owner_work(self):
        item_id = self.seed()
        initial = {"ts": CHILD, "subtype": "thread_broadcast", "reply_count": 0,
                   "text": "Synthetic work note"}
        changed = {key: value for key, value in initial.items() if key != "subtype"}
        collector, _ = self.collector([page([initial], "p2"), page([changed])])
        self.assert_retained(item_id, collector.collect())

    def test_unknown_root_roundtrips_nullable_metadata_without_erasing_work(self):
        item_id = self.seed()
        unknown = {"ts": CHILD, "subtype": "thread_broadcast", "text": "Synthetic work note"}
        collector, provider = self.collector([page([unknown])])
        result = collector.collect()
        self.assert_retained(item_id, result)
        state = json.loads(json.dumps(self.store.state()))
        item = next(row for row in state["items"] if row["id"].endswith(CHILD))
        self.assertIsNone(item["refs"]["thread_ts"])
        self.assertIsNone(item["refs"]["reply_count"])
        self.assertEqual(item["refs"]["root_resolution"], "UNKNOWN")
        self.assertEqual(state["sources"][0]["status"], "degraded")
        self.assertIsNone(state["sources"][0]["error"])
        self.assertEqual(len(provider.calls), 1)

    def test_satisfied_nested_evidence_roundtrips_and_can_remove_unobserved_rows(self):
        obsolete = "1699999900.000004"
        collector, _ = self.collector([page([{
            "ts": obsolete, "reply_count": 0, "text": "Synthetic previous record"}])])
        collector.collect()
        collector, _ = self.collector([
            page([broadcast(2)]), page([parent(2), reply(FIRST), reply()])])
        result = collector.collect()
        self.assertTrue(result["receipts"][0]["coverage"]["complete"])
        self.assertEqual(result["receipts"][0]["removed"], 1)
        items = self.store.state()["items"]
        self.assertEqual(len(items), 3)
        self.assertTrue(all(row["refs"]["thread_ts"] == ROOT for row in items))
        self.assertTrue(all(not row["id"].endswith(obsolete) for row in items))

    def test_rate_limit_preserves_work_and_real_budget_cooldown_across_collectors(self):
        item_id = self.seed()
        collector, provider = self.collector([
            page([broadcast(2)]), {"ok": False, "error": "ratelimited", "retry_after": 120}])
        collector.request_budget.clock = lambda: 1700001000
        result = collector.collect()
        self.assert_retained(item_id, result)
        self.assertEqual(result["request_budget"]["rate_limit_responses"], 1)
        self.assertEqual(len(provider.calls), 2)
        later, later_provider = self.collector([page([broadcast(2)])])
        later.request_budget.clock = lambda: 1700001060
        result = later.collect()
        self.assert_retained(item_id, result)
        self.assertEqual(len(later_provider.calls), 1)
        self.assertEqual(result["request_budget"]["deferred_reads"], 1)


if __name__ == "__main__":
    unittest.main()
