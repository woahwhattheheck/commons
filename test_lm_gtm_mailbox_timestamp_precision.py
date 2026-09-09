"""Integer-millisecond fidelity through the real mailbox snapshot consumer."""
from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import random
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "mailbox_timestamp_subject",
    Path(__file__).resolve().parent / "host" / "lm_gtm_mailbox_observations.py",
)
assert SPEC and SPEC.loader
mailbox = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mailbox)

EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
MIN_MILLIS = -62135596800000
MAX_MILLIS = 253402300799999


def message(millis, *, mid="reply", thread="conversation", labels=None):
    return {
        "id": mid,
        "thread_id": thread,
        "internal_date": millis,
        "label_ids": [] if labels is None else labels,
    }


def packet(messages, buyer_ids):
    return mailbox.observe_buyer_replies(
        "synthetic-subject",
        {"messages": messages, "buyer_message_ids": buyer_ids},
        [{
            "subject_id": "synthetic-subject",
            "type": "SENT_AWAITING_REPLY",
            "source_paths": ["gmail:sent"],
        }],
    )


class MailboxTimestampPrecisionTests(unittest.TestCase):
    def assert_exact(self, millis):
        result = mailbox._message(message(millis))
        parsed = dt.datetime.fromisoformat(result["ts"].replace("Z", "+00:00"))
        delta = parsed - EPOCH
        # Integer inverse; deliberately do not use timestamp()/total_seconds().
        micros = ((delta.days * 86400 + delta.seconds) * 1000000
                  + delta.microseconds)
        self.assertEqual(micros, int(millis) * 1000, result["ts"])
        self.assertEqual(result["milliseconds"], int(millis))
        self.assertTrue(result["ts"].endswith("Z"))
        self.assertEqual(parsed.microsecond % 1000, 0)
        return result

    def test_current_date_and_epoch_output_unchanged(self):
        cases = {
            0: "1970-01-01T00:00:00Z",
            1000: "1970-01-01T00:00:01Z",
            1: "1970-01-01T00:00:00.001000Z",
            -1: "1969-12-31T23:59:59.999000Z",
            1788866200123: "2026-09-08T11:16:40.123000Z",
        }
        for millis, expected in cases.items():
            with self.subTest(millis=millis):
                self.assertEqual(self.assert_exact(millis)["ts"], expected)

    def test_large_positive_millisecond_is_not_rounded(self):
        self.assertEqual(self.assert_exact(8640000000123)["ts"],
                         "2243-10-17T00:00:00.123000Z")

    def test_large_negative_millisecond_is_not_rounded(self):
        self.assertEqual(self.assert_exact(MIN_MILLIS + 1)["ts"],
                         "0001-01-01T00:00:00.001000Z")

    def test_representable_range_endpoints(self):
        self.assertEqual(self.assert_exact(MIN_MILLIS)["ts"],
                         "0001-01-01T00:00:00Z")
        self.assertEqual(self.assert_exact(MAX_MILLIS)["ts"],
                         "9999-12-31T23:59:59.999000Z")

    def test_neighboring_milliseconds_near_range_end(self):
        values = [self.assert_exact(MAX_MILLIS - n)["ts"] for n in range(32)]
        self.assertEqual(len(set(values)), 32)
        self.assertEqual(values, sorted(values, reverse=True))

    def test_deterministic_millisecond_grid(self):
        rng = random.Random(20260908)
        for _ in range(2048):
            self.assert_exact(rng.randint(MIN_MILLIS, MAX_MILLIS))

    def test_integer_and_string_forms_are_identical(self):
        for millis in (MIN_MILLIS + 1, -1, 0, 1788866200123, MAX_MILLIS):
            with self.subTest(millis=millis):
                self.assertEqual(self.assert_exact(millis), self.assert_exact(str(millis)))

    def test_camelcase_and_connector_result_keep_exact_time(self):
        actual = mailbox._message({"result": {
            "id": "reply", "threadId": "conversation",
            "internalDate": str(MAX_MILLIS), "labelIds": ["INBOX"],
        }})
        self.assertEqual(actual["ts"], "9999-12-31T23:59:59.999000Z")
        self.assertEqual(actual["labels"], frozenset({"INBOX"}))

    def test_unsupported_input_types_remain_errors(self):
        for value in (None, True, False, 1.0, [], {}, b"1000"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "internal_date milliseconds"):
                    mailbox._message(message(value))

    def test_malformed_and_out_of_range_values_remain_errors(self):
        for value in ("", "not-a-date", "1.25", "1e3", MIN_MILLIS - 1,
                      MAX_MILLIS + 1, 10 ** 100, -(10 ** 100)):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "invalid internal_date"):
                    mailbox._message(message(value))

    def test_original_message_not_mutated(self):
        source = message(str(MAX_MILLIS), labels=["INBOX"])
        source["body"] = "synthetic private body"
        before = copy.deepcopy(source)
        normalized = mailbox._message(source)
        self.assertEqual(source, before)
        self.assertNotIn("body", normalized)

    def test_public_projection_keeps_exact_reply_time(self):
        result = packet([
            message(str(MAX_MILLIS - 2), mid="sent", labels=["SENT"]),
            message(str(MAX_MILLIS), labels=["INBOX"]),
        ], ["reply"])
        self.assertEqual(result["status"], "BUYER_REPLY_OBSERVED")
        self.assertEqual(result["replies"][0]["ts"],
                         "9999-12-31T23:59:59.999000Z")
        self.assertEqual(result["replies"][0]["source_ref"], "gmail:reply")
        self.assertEqual(result["scope"], "SUPPLIED_MESSAGES_ONLY")

    def test_public_order_and_equal_time_id_tiebreak_stay_unchanged(self):
        result = packet([
            message(1000, mid="sent", labels=["SENT"]),
            message(1002, mid="reply-z"),
            message(1001, mid="reply-early"),
            message(1002, mid="reply-a"),
            message(999, mid="before"),
        ], ["reply-z", "reply-early", "reply-a", "before"])
        self.assertEqual(result["inbound_buyer_message_ids"],
                         ["reply-early", "reply-a", "reply-z"])
        self.assertEqual(result["unmatched_buyer_message_ids"], ["before"])

    def test_duplicate_snapshot_is_idempotent_and_not_mutated(self):
        messages = [message(1000, mid="sent", labels=["SENT"]),
                    message(1001), message("1001")]
        before = copy.deepcopy(messages)
        result = packet(messages, ["reply", "reply"])
        self.assertEqual(result, packet(messages[:2], ["reply"]))
        self.assertEqual(len(result["replies"]), 1)
        self.assertEqual(messages, before)

    def test_conflicting_duplicate_milliseconds_remain_errors(self):
        with self.assertRaisesRegex(ValueError, "conflicting identity metadata"):
            packet([message(1000), message(1001)], ["reply"])

    def test_label_union_and_missing_outbound_contracts_unchanged(self):
        result = packet([
            message(1000, mid="sent", labels=["SENT"]),
            message(1001), message(1001, labels=["DRAFT"]),
        ], ["reply"])
        self.assertEqual(result["status"], "NO_BUYER_REPLY_IN_SNAPSHOT")
        self.assertEqual(result["replies"], [])
        self.assertEqual(packet([message(1001)], ["reply"])["status"],
                         "OUTBOUND_CONTEXT_MISSING")


if __name__ == "__main__":
    unittest.main()
