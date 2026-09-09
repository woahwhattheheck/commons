#!/usr/bin/env python3
"""Exact provider milliseconds and real in-memory reply-projection regressions."""
from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import random
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "mailbox_milliseconds_under_test", ROOT / "host" / "lm_gtm_mailbox_observations.py"
)
assert SPEC and SPEC.loader
mailbox = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mailbox)
EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
LOWER_MS = -62135596800000
UPPER_MS = 253402300799999


def message(mid="reply", millis=1788866000123, labels=None, thread="thread"):
    return {
        "id": mid,
        "thread_id": thread,
        "internal_date": str(millis),
        "label_ids": ["INBOX"] if labels is None else list(labels),
    }


def event(mid="sent", subject="subject"):
    return {
        "subject_id": subject,
        "type": "SENT_AWAITING_REPLY",
        "source_paths": ["gmail:" + mid],
    }


def observe(messages, buyers, events=None):
    return mailbox.observe_buyer_replies(
        "subject",
        {"messages": messages, "buyer_message_ids": buyers},
        [event()] if events is None else events,
    )


class ExactMillisecondsTests(unittest.TestCase):
    def assert_milliseconds(self, millis):
        parsed = mailbox._message(message(millis=millis))
        stamp = dt.datetime.fromisoformat(parsed["ts"].replace("Z", "+00:00"))
        delta = stamp - EPOCH
        actual_us = ((delta.days * 86400 + delta.seconds) * 1000000
                     + delta.microseconds)
        self.assertEqual(actual_us, millis * 1000)
        self.assertEqual(parsed["milliseconds"], millis)
        self.assertEqual(stamp.microsecond % 1000, 0)
        self.assertTrue(parsed["ts"].endswith("Z"))

    def test_current_date_literal(self):
        self.assertEqual(mailbox._message(message())["ts"],
                         "2026-09-08T11:13:20.123000Z")

    def test_first_date_plus_one_millisecond_literal(self):
        self.assertEqual(mailbox._message(message(millis=LOWER_MS + 1))["ts"],
                         "0001-01-01T00:00:00.001000Z")

    def test_last_date_last_millisecond_literal(self):
        self.assertEqual(mailbox._message(message(millis=UPPER_MS))["ts"],
                         "9999-12-31T23:59:59.999000Z")

    def test_far_positive_date_literal(self):
        self.assertEqual(mailbox._message(message(millis=100000000000001))["ts"],
                         "5138-11-16T09:46:40.001000Z")

    def test_epoch_neighbors(self):
        for millis in (-1001, -1000, -999, -1, 0, 1, 999, 1000, 1001):
            with self.subTest(millis=millis):
                self.assert_milliseconds(millis)

    def test_supported_range_endpoints(self):
        for millis in (LOWER_MS, UPPER_MS - 999):
            with self.subTest(millis=millis):
                self.assert_milliseconds(millis)

    def test_deterministic_supported_range_round_trip(self):
        rng = random.Random(20260908)
        for _ in range(2000):
            millis = rng.randint(LOWER_MS, UPPER_MS)
            # No subtests: retain one clear failure rather than 2,000 log entries.
            self.assert_milliseconds(millis)

    def test_all_milliseconds_in_a_current_second(self):
        for offset in range(1000):
            self.assert_milliseconds(1788866000000 + offset)

    def test_integer_and_string_provider_forms(self):
        raw = message(millis=UPPER_MS)
        numeric = dict(raw, internal_date=UPPER_MS)
        self.assertEqual(mailbox._message(raw), mailbox._message(numeric))

    def test_camel_case_and_wrapped_connector_forms(self):
        snake = message(millis=UPPER_MS)
        camel = {
            "id": snake["id"], "threadId": snake["thread_id"],
            "internalDate": snake["internal_date"], "labelIds": snake["label_ids"],
        }
        expected = mailbox._message(snake)
        self.assertEqual(mailbox._message(camel), expected)
        self.assertEqual(mailbox._message({"result": camel}), expected)

    def test_out_of_range_is_existing_value_error(self):
        for millis in (LOWER_MS - 1, UPPER_MS + 1, 10**100, -(10**100)):
            with self.subTest(millis=millis):
                with self.assertRaisesRegex(ValueError, "invalid internal_date"):
                    mailbox._message(message(millis=millis))

    def test_bad_date_input_keeps_existing_diagnostics(self):
        for value in (True, False, None, 1.0, [], {}):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "internal_date milliseconds"):
                    mailbox._message(dict(message(), internal_date=value))
        for value in ("", "nonsense", "1.5", "2026-09-08T00:00:00Z"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "invalid internal_date"):
                    mailbox._message(dict(message(), internal_date=value))


class ReplyProjectionTests(unittest.TestCase):
    def test_end_to_end_exact_reply_at_upper_range(self):
        result = observe([
            message("sent", UPPER_MS - 1, ["SENT"]),
            message("reply", UPPER_MS),
        ], ["reply"])
        self.assertEqual(result["status"], "BUYER_REPLY_OBSERVED")
        self.assertEqual(result["replies"][0]["ts"], "9999-12-31T23:59:59.999000Z")
        self.assertEqual(result["scope"], "SUPPLIED_MESSAGES_ONLY")
        self.assertEqual(result["outbound_message_ids"], ["sent"])

    def test_reply_order_and_equal_time_id_tiebreak_are_preserved(self):
        result = observe([
            message("sent", UPPER_MS - 3, ["SENT"]),
            message("z", UPPER_MS),
            message("b", UPPER_MS - 1),
            message("a", UPPER_MS - 1),
        ], ["z", "b", "a"])
        self.assertEqual(result["inbound_buyer_message_ids"], ["a", "b", "z"])

    def test_pre_anchor_other_thread_and_sent_draft_are_excluded(self):
        result = observe([
            message("sent", 1000, ["SENT"]),
            message("before", 999), message("other", 1001, thread="other"),
            message("outgoing", 1001, ["SENT"]),
            message("draft", 1001, ["DRAFT"]), message("reply", 1000),
        ], ["before", "other", "outgoing", "draft", "reply"])
        self.assertEqual(result["inbound_buyer_message_ids"], ["reply"])
        self.assertEqual(result["unmatched_buyer_message_ids"],
                         ["before", "draft", "other", "outgoing"])

    def test_duplicate_labels_remain_conservatively_unioned(self):
        result = observe([
            message("sent", 0, ["SENT"]),
            message("reply", 1, ["INBOX"]), message("reply", 1, ["DRAFT"]),
        ], ["reply"])
        self.assertEqual(result["status"], "NO_BUYER_REPLY_IN_SNAPSHOT")
        self.assertEqual(result["inbound_buyer_message_ids"], [])

    def test_duplicate_identity_conflict_remains_an_error(self):
        for duplicate in (message("reply", 2), message("reply", 1, thread="other")):
            with self.subTest(duplicate=duplicate):
                with self.assertRaisesRegex(ValueError, "conflicting identity"):
                    observe([message("reply", 1), duplicate], ["reply"])

    def test_missing_and_unrelated_outbound_context(self):
        for events in ([], [event(subject="other")]):
            with self.subTest(events=events):
                result = observe([message("sent", 0, ["SENT"]),
                                  message("reply", 1)], ["reply"], events)
                self.assertEqual(result["status"], "OUTBOUND_CONTEXT_MISSING")

    def test_snapshot_is_not_mutated_and_private_content_is_not_copied(self):
        raw = message("reply", 1)
        raw.update(body="synthetic private body", headers={"From": "buyer@example.test"},
                   attachments=["private attachment marker"])
        snapshot = {"messages": [message("sent", 0, ["SENT"]), raw],
                    "buyer_message_ids": ["reply", "reply"]}
        original = copy.deepcopy(snapshot)
        events = [event()]
        original_events = copy.deepcopy(events)
        first = mailbox.observe_buyer_replies("subject", snapshot, events)
        second = mailbox.observe_buyer_replies("subject", snapshot, events)
        self.assertEqual(first, second)
        self.assertEqual(snapshot, original)
        self.assertEqual(events, original_events)
        rendered = json.dumps(first)
        for secret in ("synthetic private body", "buyer@example.test",
                       "private attachment marker"):
            self.assertNotIn(secret, rendered)

    def test_missing_caller_identified_record_stays_an_error(self):
        with self.assertRaisesRegex(ValueError, "every supplied buyer_message_id"):
            observe([], ["missing"])


if __name__ == "__main__":
    unittest.main()
