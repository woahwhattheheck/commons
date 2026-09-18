"""Thread visibility through the real collector, request budget and SQLite store."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import threading
import unittest

from integrations.command_center.collectors import LiveCollectors
from integrations.command_center.slack_threads import SlackReadFailure, read_channel
from integrations.command_center.workstreams import WorkstreamStore

CHANNEL = {"id": "C1", "label": "specialist", "project": "real-work"}
ROOT = "1789458000.000001"
REPLY = "1789458001.000002"
OLDER = "1789400000.000003"


def message(ts=ROOT, **fields):
    return {"ts": ts, "text": "Observed work", "user": "U1", **fields}


def parent(count=1, **fields):
    return message(**{"reply_count": count, "latest_reply": REPLY, **fields})


def reply(ts=REPLY, **fields):
    return message(ts, **{"thread_ts": ROOT, **fields})


def page(rows, cursor="", **fields):
    return {"ok": True, "messages": rows, "response_metadata": {"next_cursor": cursor}, **fields}


class Provider:
    def __init__(self, responses):
        self.responses = copy.deepcopy(responses)
        self.calls = []

    def slack(self, method, payload):
        if method not in {"conversations.history", "conversations.replies"}:
            raise AssertionError("Provider mutation is forbidden")
        self.calls.append((method, copy.deepcopy(payload)))
        response = self.responses.pop(0)
        if callable(response):
            response = response()
        if isinstance(response, Exception):
            raise response
        return response


class ThreadTests(unittest.TestCase):
    def read(self, pages, **kwargs):
        provider = Provider(pages)
        result = read_channel(provider.slack, "C1", page_size=100, max_pages=2, **kwargs)
        return result, provider

    def test_default_makes_no_reply_requests(self):
        (rows, meta, complete), provider = self.read([page([parent()])])
        self.assertEqual(len(rows), 1)
        self.assertFalse(complete)
        self.assertEqual(meta["threads_pending_count"], 1)
        self.assertFalse(meta["thread_expansion_enabled"])
        self.assertEqual(len(provider.calls), 1)

    def test_complete_reply_import_and_root_echo_dedup(self):
        (rows, meta, complete), provider = self.read([
            page([parent()]), page([parent(), reply(text="TAKE this task")])], max_threads=1)
        self.assertTrue(complete)
        self.assertEqual({row["ts"] for row in rows}, {ROOT, REPLY})
        self.assertEqual(meta["threads_complete_count"], 1)
        self.assertEqual(meta["threads_pending_count"], 0)
        self.assertEqual(provider.calls[1], ("conversations.replies", {"channel": "C1", "ts": ROOT, "limit": 100}))

    def test_reply_pages_and_broadcast_share_one_identity(self):
        later = "1789458002.000001"
        root = parent(count=2, latest_reply=later)
        (rows, meta, complete), provider = self.read([
            page([root, reply(subtype="thread_broadcast")]),
            page([root, reply()], "next"), page([reply(), reply(later)])], max_threads=1)
        self.assertTrue(complete)
        self.assertEqual(len(rows), 3)
        self.assertEqual(meta["thread_coverage"][0]["observed_replies"], 2)
        self.assertEqual(provider.calls[2][1]["cursor"], "next")

    def test_broadcast_with_unseen_root_expands_root(self):
        (rows, _, complete), _ = self.read([page([reply()]), page([parent(), reply()])], max_threads=1)
        self.assertTrue(complete)
        self.assertEqual({row["ts"] for row in rows}, {ROOT, REPLY})

    def test_count_mismatch_does_not_authorize_complete_replacement(self):
        for root in (parent(count=2), parent(count=0)):
            with self.subTest(root=root):
                (_, meta, complete), _ = self.read([page([parent()]), page([root])], max_threads=1)
                self.assertFalse(complete)
                self.assertEqual(meta["thread_coverage"][0]["reason"], "reply_evidence_mismatch")

    def test_latest_reply_must_actually_be_observed(self):
        (_, meta, complete), _ = self.read([page([parent()]), page([parent(), reply("1789458000.999999")])], max_threads=1)
        self.assertFalse(complete)
        self.assertEqual(meta["thread_coverage"][0]["reason"], "reply_evidence_mismatch")

    def test_missing_parent_or_count_is_not_complete(self):
        for history, replies in (([parent()], [reply()]), ([reply()], [message(), reply()])):
            with self.subTest(history=history):
                (_, _, complete), _ = self.read([page(history), page(replies)], max_threads=1)
                self.assertFalse(complete)

    def test_wrong_thread_response_is_rejected_without_losing_history(self):
        for row in (message(REPLY), reply(thread_ts=OLDER), parent(thread_ts=OLDER)):
            with self.subTest(row=row):
                (rows, meta, complete), _ = self.read([page([parent()]), page([row])], max_threads=1)
                self.assertEqual(rows, [parent()])
                self.assertFalse(complete)
                self.assertEqual(meta["thread_coverage"][0]["error"]["code"], "slack_thread_identity")

    def test_changing_thread_evidence_across_pages_is_incomplete(self):
        for pages, enabled in (([page([parent(count=2)], "next"), page([parent()])], 0),
                ([page([parent()]), page([parent(count=2), reply()], "next"), page([parent()])], 1)):
            with self.subTest(pages=pages):
                (_, meta, complete), _ = self.read(pages, max_threads=enabled)
                self.assertFalse(complete)
                report = meta["thread_coverage"][0] if enabled else meta["history"]
                self.assertEqual(report["reason"], "thread_evidence_changed")

    def test_thread_cap_prioritizes_latest_reply_deterministically(self):
        old = message(OLDER, reply_count=1, latest_reply="1789457999.000001")
        for history in ([old, parent()], [parent(), old]):
            with self.subTest(history=history):
                (_, meta, complete), provider = self.read([page(history), page([parent(), reply()])], max_threads=1)
                self.assertEqual(provider.calls[1][1]["ts"], ROOT)
                self.assertFalse(complete)
                self.assertEqual(meta["threads_pending"], [{"thread_ts": OLDER, "reply_count": 1, "latest_reply": "1789457999.000001"}])

    def test_reply_page_cap_is_visible(self):
        (_, meta, complete), provider = self.read([page([parent()]), page([parent()], "next")], max_threads=1, max_thread_pages=1)
        self.assertFalse(complete)
        self.assertEqual(meta["thread_coverage"][0]["reason"], "page_limit")
        self.assertEqual(meta["thread_coverage"][0]["next_cursor"], "next")
        self.assertEqual(len(provider.calls), 2)

    def test_cursor_cycle_stops_without_duplicating_rows(self):
        (rows, meta, complete), provider = self.read([page([message()], "same"), page([message()], "same")])
        self.assertFalse(complete)
        self.assertEqual(len(rows), 1)
        self.assertEqual(meta["history"]["reason"], "cursor_cycle")
        self.assertEqual(len(provider.calls), 2)

    def test_has_more_without_cursor_is_incomplete(self):
        (_, meta, complete), _ = self.read([page([], has_more=True)])
        self.assertFalse(complete)
        self.assertEqual(meta["history"]["reason"], "cursor_missing")

    def test_provider_limited_history_never_becomes_complete(self):
        for pages in ([page([], is_limited=True)], [page([], "next", is_limited=True), page([])]):
            with self.subTest(pages=pages):
                (_, meta, complete), _ = self.read(pages)
                self.assertFalse(complete)
                self.assertTrue(meta["history"]["is_limited"])

    def test_later_history_failure_retains_prior_page_and_hides_exception_text(self):
        (rows, meta, complete), _ = self.read([page([message()], "next"), TimeoutError("private-account-secret")])
        self.assertEqual(rows, [message()])
        self.assertFalse(complete)
        self.assertEqual(meta["history"]["error"], {"code": "slack_read_failed"})
        self.assertNotIn("private-account-secret", json.dumps(meta))

    def test_first_history_failure_keeps_existing_source_error_path(self):
        with self.assertRaises(TimeoutError):
            self.read([TimeoutError("not persisted")])
        with self.assertRaises(SlackReadFailure):
            self.read([{"ok": True}])

    def test_later_malformed_reply_page_retains_valid_reply_page(self):
        (rows, meta, complete), _ = self.read([page([parent(count=2)]), page([parent(count=2), reply()], "next"), {"ok": True}], max_threads=1)
        self.assertFalse(complete)
        self.assertEqual({row["ts"] for row in rows}, {ROOT, REPLY})
        self.assertEqual(meta["thread_coverage"][0]["error"]["code"], "slack_messages_shape")

    def test_one_thread_failure_does_not_erase_other_thread_success(self):
        other_reply = "1789400001.000001"
        other = message(OLDER, reply_count=1, latest_reply=other_reply)
        (rows, meta, complete), provider = self.read([page([parent(), other]),
            {"ok": False, "error": "missing_scope"},
            page([other, message(other_reply, thread_ts=OLDER)])], max_threads=2)
        self.assertFalse(complete)
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual(meta["threads_complete_count"], 1)
        self.assertIn(other_reply, {row["ts"] for row in rows})
        self.assertEqual(meta["thread_coverage"][0]["error"]["code"], "missing_scope")

    def test_invalid_message_fields_cannot_silently_erase_work(self):
        bad = [message(ts=True), message(ts="nan"), message(ts="999999999999"),
               message(reply_count=True), message(reply_count=-1), message(reply_count="2"),
               message(edited=None), message(edited={"ts": "bad"}), message(text={}),
               message(thread_ts=[]), message(latest_reply=12), message(subtype=[]),
               message(user={}), message(bot_id=[])]
        for row in bad:
            with self.subTest(row=row), self.assertRaises(SlackReadFailure):
                self.read([page([row])])

    def test_bad_pagination_fields_fail_closed(self):
        for fields in ({"is_limited": 1}, {"has_more": "false"}, {"response_metadata": None},
                       {"response_metadata": {"next_cursor": "x" * 4001}}):
            with self.subTest(fields=fields), self.assertRaises(SlackReadFailure):
                self.read([{**page([]), **fields}])

    def test_provider_row_count_bound_is_enforced(self):
        provider = Provider([page([message(), reply()])])
        with self.assertRaises(SlackReadFailure):
            read_channel(provider.slack, "C1", page_size=1, max_pages=1)

    def test_pending_list_is_bounded_without_hiding_count(self):
        roots = [message(str(1789458000 + i), reply_count=1) for i in range(101)]
        (_, meta, complete), _ = self.read([page(roots[:100], "next"), page(roots[100:])])
        self.assertFalse(complete)
        self.assertEqual(meta["threads_pending_count"], 101)
        self.assertEqual(len(meta["threads_pending"]), 100)
        self.assertTrue(meta["threads_pending_truncated"])

    def test_invalid_bounds_make_no_provider_requests(self):
        for key, value in (("max_threads", True), ("max_threads", -1), ("max_threads", 9),
                           ("max_thread_pages", 0), ("max_thread_pages", 11)):
            provider = Provider([])
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                read_channel(provider.slack, "C1", page_size=100, max_pages=2, **{key: value})
            self.assertEqual(provider.calls, [])


class CollectorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = WorkstreamStore(self.temp.name)

    def collector(self, responses, *, expansion=1, **options):
        provider = Provider(responses)
        config = {"github": {"enabled": False}, "slack": {"channels": [CHANNEL],
            "workspace_url": "https://fixture.slack.com", "max_threads_per_channel": expansion}, **options}
        collector = LiveCollectors(self.store, config, equipment=provider, clock=lambda: "2026-09-15T08:00:00Z")
        return collector, provider

    def seed(self):
        collector, _ = self.collector([page([message(OLDER)])])
        collector.collect()
        item_id = "slack:C1:" + OLDER
        self.store.update_work({"operation_id": "owner:keep", "source_id": "slack:C1", "item_id": item_id, "next_action": "Keep this owner direction"})
        return copy.deepcopy(self.store.state()["items"][0])

    def test_real_store_imports_reply_with_identity_link_and_actual_activity(self):
        collector, _ = self.collector([page([parent()]), page([parent(), reply(text="Claim in a quiet thread")])])
        result = collector.collect()
        rows = {row["id"]: row for row in self.store.state()["items"]}
        item = rows["slack:C1:" + REPLY]
        self.assertEqual(item["refs"]["thread_ts"], ROOT)
        self.assertEqual(item["url"], "https://fixture.slack.com/archives/C1/p" + REPLY.replace(".", ""))
        self.assertEqual(item["title"], "Claim in a quiet thread")
        self.assertEqual(item["activity_observed_at"], "2026-09-15T07:40:01.000002Z")
        self.assertTrue(result["receipts"][0]["coverage"]["complete"])
        self.assertEqual(result["request_budget"]["observed_attempts"], 2)

    def test_partial_history_adds_new_rows_and_preserves_old_owner_work(self):
        before = self.seed()
        collector, _ = self.collector([page([message()], "next"), TimeoutError("private-detail")])
        receipt = collector.collect()["receipts"][0]
        rows = {row["id"]: row for row in self.store.state()["items"]}
        self.assertEqual(rows[before["id"]], before)
        self.assertIn("slack:C1:" + ROOT, rows)
        self.assertEqual((receipt["changed"], receipt["removed"], receipt["retained"]), (1, 0, 1))
        source = self.store.state()["sources"][0]
        self.assertEqual(source["status"], "degraded")
        self.assertIsNone(source["error"])
        self.assertFalse(source["coverage"]["complete"])
        self.assertNotIn("private-detail", json.dumps(source))

    def test_reply_rate_limit_preserves_observed_rows_and_cooldown_survives_restart(self):
        before = self.seed()
        collector, provider = self.collector([page([parent(count=2)]), page([parent(count=2), reply()], "next"), {"ok": False, "error": "ratelimited", "retry_after": 120}])
        collector.request_budget.clock = lambda: 1789459200
        result = collector.collect()
        rows = {row["id"]: row for row in self.store.state()["items"]}
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[before["id"]], before)
        self.assertEqual(result["receipts"][0]["changed"], 2)
        self.assertEqual(result["request_budget"]["rate_limit_responses"], 1)
        self.assertEqual(len(provider.calls), 3)
        coverage = result["sources"][0]["metadata"]["thread_coverage"][0]
        self.assertEqual(coverage["error"]["code"], "slack_rate_limited")
        self.assertIn("retry_not_before", coverage["error"])
        restarted, provider2 = self.collector([page([parent(count=2)])])
        restarted.request_budget.clock = lambda: 1789459201
        again = restarted.collect()
        self.assertEqual(len(provider2.calls), 1)
        self.assertEqual(again["request_budget"]["deferred_reads"], 1)
        self.assertEqual(len(self.store.state()["items"]), 3)
        self.assertEqual(again["sources"][0]["metadata"]["thread_coverage"][0]["error"]["code"], "collector_read_deferred")

    def test_first_history_deferred_does_not_replace_source_snapshot(self):
        self.seed()
        before = self.store.state()["sources"][0]
        collector, provider = self.collector([])
        collector.request_budget.rate_limited("slack:conversations.history", 60)
        result = collector.collect()
        self.assertEqual(provider.calls, [])
        self.assertEqual(result["receipts"], [])
        self.assertEqual(result["deferred_sources"][0]["scope"], "slack:conversations.history")
        self.assertEqual(self.store.state()["sources"][0]["observed_at"], before["observed_at"])

    def test_cancellation_after_history_preserves_fresh_parent(self):
        event = threading.Event()
        def first():
            event.set()
            return page([parent()])
        collector, provider = self.collector([first])
        collector.cancel_event = event
        result = collector.collect()
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(result["receipts"][0]["received"], 1)
        self.assertEqual(len(self.store.state()["items"]), 1)
        self.assertEqual(result["sources"][0]["metadata"]["thread_coverage"][0]["error"]["code"], "refresh_cancelled")

    def test_direct_batch_digest_binds_degraded_status_and_coverage(self):
        collector, _ = self.collector([page([parent()]), TimeoutError("hidden")])
        batch = collector._slack(CHANNEL)
        payload = {key: value for key, value in batch.items() if key != "operation_id"}
        digest = "collect:" + hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        self.assertEqual(batch["operation_id"], digest)
        self.assertEqual(batch["source"]["status"], "degraded")
        self.assertTrue(self.store.ingest(batch)["ok"])
        self.assertTrue(self.store.ingest(batch)["replayed"])

    def test_complete_snapshot_may_remove_old_items_but_partial_never_does(self):
        self.seed()
        collector, _ = self.collector([page([parent()]), page([parent(), reply()])])
        receipt = collector.collect()["receipts"][0]
        self.assertEqual(receipt["removed"], 1)
        self.assertEqual(len(self.store.state()["items"]), 2)

    def test_reply_summary_is_redacted_by_existing_store_policy(self):
        collector, _ = self.collector([page([parent()]), page([parent(), reply(text="password=fictional-secret")])])
        collector.collect()
        self.assertNotIn("fictional-secret", json.dumps(self.store.state()))

    def test_constructor_rejects_invalid_thread_configuration(self):
        for value in (True, -1, 9, 1.5, "1", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.collector([], expansion=value)


if __name__ == "__main__":
    unittest.main()
