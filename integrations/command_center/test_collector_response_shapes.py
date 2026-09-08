"""Malformed provider responses must not become complete empty work snapshots.

Uses the real collector, SQLite store and ingestion path with fixture providers.
No provider/network calls, deployment, or historical account observations.
"""
from __future__ import annotations

import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from integrations.command_center.collectors import LiveCollectors
from integrations.command_center.workstreams import WorkstreamStore

CHANNEL = {"id": "C1", "label": "work"}
CONFIG = {"github": {"enabled": False}, "slack": {"channels": [CHANNEL]}}
MESSAGE = {"ts": "1788830000.123456", "text": "Retained work", "user": "U1"}


class ScriptedProvider:
    def __init__(self, pages):
        self.pages = copy.deepcopy(pages)
        self.requests = []

    def slack(self, method, payload):
        if method != "conversations.history":
            raise AssertionError("Unexpected provider method")
        self.requests.append((method, copy.deepcopy(payload)))
        if not self.pages:
            raise AssertionError("Unexpected extra provider call")
        response = self.pages.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class SlackResponseShapeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = WorkstreamStore(self.temp.name)
        self.tick = datetime(2026, 9, 8, 2, tzinfo=timezone.utc)
        self.collect([{"ok": True, "messages": [MESSAGE], "has_more": False}])
        self.before = self.store.state()
        self.item_id = self.before["items"][0]["id"]
        self.store.update_work({"operation_id": "owner:keep", "source_id": "slack:C1",
                                "item_id": self.item_id, "priority": "high",
                                "next_action": "Keep the existing owner action"})
        self.before = self.store.state()

    def collect(self, pages, **overrides):
        self.tick += timedelta(minutes=1)
        provider = ScriptedProvider(pages)
        config = {**CONFIG, **overrides}
        result = LiveCollectors(self.store, config, equipment=provider,
                                clock=lambda: self.tick.isoformat()).collect()
        return result, provider

    def assert_retained_error(self, response, code):
        result, provider = self.collect([response])
        receipt = result["receipts"][0]
        state = self.store.state()
        self.assertEqual(receipt["status"], "source_error")
        self.assertEqual((receipt["removed"], receipt["retained"]), (0, 1))
        self.assertFalse(receipt["coverage"]["complete"])
        self.assertTrue(receipt["coverage"]["pagination_remaining"])
        self.assertEqual(state["items"], self.before["items"])
        self.assertEqual(state["sources"][0]["error"], code)
        self.assertTrue(state["sources"][0]["retained_last_good"])
        self.assertEqual(state["sources"][0]["last_good_observed_at"],
                         self.before["sources"][0]["last_good_observed_at"])
        self.assertEqual(len(provider.requests), 1)

    def test_missing_messages_is_not_empty_history(self):
        self.assert_retained_error({"ok": True}, "slack_messages_shape")

    def test_object_messages_is_not_empty_history(self):
        self.assert_retained_error({"ok": True, "messages": {}}, "slack_messages_shape")

    def test_string_messages_is_not_empty_history(self):
        self.assert_retained_error({"ok": True, "messages": ""}, "slack_messages_shape")

    def test_null_messages_is_reported_with_fixed_code(self):
        self.assert_retained_error({"ok": True, "messages": None}, "slack_messages_shape")

    def test_scalar_row_cannot_disappear_into_complete_result(self):
        self.assert_retained_error({"ok": True, "messages": [None]}, "slack_messages_shape")

    def test_missing_row_timestamp_is_not_silently_omitted(self):
        self.assert_retained_error({"ok": True, "messages": [{"text": "unkeyed"}]},
                                   "slack_messages_shape")

    def test_false_string_is_not_a_success_boolean(self):
        self.assert_retained_error({"ok": "false", "messages": []}, "slack_response_shape")

    def test_numeric_success_is_not_a_success_boolean(self):
        self.assert_retained_error({"ok": 1, "messages": []}, "slack_response_shape")

    def test_bad_metadata_container_is_fixed_error(self):
        self.assert_retained_error({"ok": True, "messages": [], "response_metadata": []},
                                   "slack_pagination_shape")

    def test_null_cursor_cannot_end_coverage(self):
        self.assert_retained_error({"ok": True, "messages": [],
                                    "response_metadata": {"next_cursor": None}},
                                   "slack_pagination_shape")

    def test_numeric_cursor_cannot_end_coverage(self):
        self.assert_retained_error({"ok": True, "messages": [],
                                    "response_metadata": {"next_cursor": 0}},
                                   "slack_pagination_shape")

    def test_nonboolean_has_more_is_not_a_completion_marker(self):
        self.assert_retained_error({"ok": True, "messages": [], "has_more": 0},
                                   "slack_pagination_shape")

    def test_missing_success_field_retains_previous_items(self):
        self.assert_retained_error({"messages": []}, "slack_response_shape")

    def test_real_provider_error_keeps_existing_error_code(self):
        self.assert_retained_error({"ok": False, "error": "not_in_channel"}, "not_in_channel")

    def test_transport_failure_retains_items_without_exception_text(self):
        self.assert_retained_error(TimeoutError("private provider detail"), "TimeoutError")
        self.assertNotIn("private provider detail", str(self.store.state()))

    def test_well_formed_empty_history_can_replace_prior_snapshot(self):
        result, provider = self.collect([{"ok": True, "messages": [], "has_more": False,
                                         "response_metadata": {"next_cursor": ""}}])
        self.assertEqual(self.store.state()["items"], [])
        self.assertEqual(result["receipts"][0]["removed"], 1)
        self.assertTrue(result["receipts"][0]["coverage"]["complete"])
        self.assertEqual(len(provider.requests), 1)

    def test_optional_pagination_fields_can_be_omitted(self):
        result, _ = self.collect([{"ok": True, "messages": []}])
        self.assertEqual(result["receipts"][0]["removed"], 1)
        self.assertTrue(result["receipts"][0]["coverage"]["complete"])

    def test_valid_recovery_reuses_existing_owner_direction(self):
        self.assert_retained_error({"ok": True}, "slack_messages_shape")
        changed = {**MESSAGE, "text": "Now updated"}
        result, _ = self.collect([{"ok": True, "messages": [changed]}])
        state = self.store.state()
        self.assertEqual(result["receipts"][0]["status"], "ingested")
        self.assertEqual(state["items"][0]["title"], "Now updated")
        self.assertEqual(state["items"][0]["owner_work"], self.before["items"][0]["owner_work"])
        self.assertFalse(state["sources"][0]["retained_last_good"])

    def test_housekeeping_omission_is_still_intentional(self):
        housekeeping = {**MESSAGE, "subtype": "channel_join"}
        result, _ = self.collect([{"ok": True, "messages": [housekeeping]}])
        self.assertEqual(self.store.state()["items"], [])
        self.assertTrue(result["receipts"][0]["coverage"]["complete"])

    def test_later_bad_page_cannot_partially_replace_prior_snapshot(self):
        new = {**MESSAGE, "ts": "1788831000.123456", "text": "New page item"}
        result, provider = self.collect([
            {"ok": True, "messages": [new], "has_more": True,
             "response_metadata": {"next_cursor": "page2"}},
            {"ok": True},
        ])
        self.assertEqual(result["receipts"][0]["status"], "source_error")
        self.assertEqual(self.store.state()["items"], self.before["items"])
        self.assertEqual(provider.requests[1][1]["cursor"], "page2")

    def test_valid_cursor_pages_still_merge(self):
        new = {**MESSAGE, "ts": "1788831000.123456", "text": "New page item"}
        result, provider = self.collect([
            {"ok": True, "messages": [new], "has_more": True,
             "response_metadata": {"next_cursor": "page2"}},
            {"ok": True, "messages": [MESSAGE], "has_more": False},
        ])
        self.assertEqual(result["receipts"][0]["received"], 2)
        self.assertTrue(result["receipts"][0]["coverage"]["complete"])
        self.assertEqual(len(self.store.state()["items"]), 2)
        self.assertEqual(provider.requests[1][1]["cursor"], "page2")

    def test_pending_threads_remain_partial_coverage(self):
        thread = {**MESSAGE, "reply_count": 2, "latest_reply": "1788831000.123456"}
        result, _ = self.collect([{"ok": True, "messages": [thread]}])
        self.assertFalse(result["receipts"][0]["coverage"]["complete"])
        self.assertEqual(self.store.state()["sources"][0]["metadata"]["threads_pending_count"], 1)

    def test_page_budget_still_preserves_unseen_previous_items(self):
        result, _ = self.collect([{"ok": True, "messages": [], "has_more": True,
                                  "response_metadata": {"next_cursor": "still-more"}}], max_pages=1)
        self.assertEqual(result["receipts"][0]["retained"], 1)
        self.assertFalse(result["receipts"][0]["coverage"]["complete"])

    def test_has_more_without_cursor_still_reports_incomplete(self):
        result, _ = self.collect([{"ok": True, "messages": [], "has_more": True}])
        self.assertEqual(result["receipts"][0]["retained"], 1)
        self.assertFalse(result["receipts"][0]["coverage"]["complete"])


if __name__ == "__main__":
    unittest.main()
