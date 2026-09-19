"""Independent synthetic observations for #16326; no Slack or network calls.

Run from the repository root with python [-O] -m unittest -v
 test_slack_root_observations_chert. Fixtures are invented provider observations,
not copies of private Slack traffic. No claim or provider-write authority is
inferred from complete coverage.
"""
from __future__ import annotations

import copy
import itertools
import unittest

from integrations.command_center.slack_threads import read_channel, read_thread_context

ROOT = "1700000000.000001"
FIRST = "1700000010.000002"
CHILD = "1700000020.000003"
OTHER = "1700000015.000004"
CHANNEL = "CDEMO"


def page(rows, cursor=""):
    return {"ok": True, "messages": copy.deepcopy(rows),
            "response_metadata": {"next_cursor": cursor}}


def parent(count, latest=CHILD):
    return {"ts": ROOT, "reply_count": count, "latest_reply": latest,
            "text": "Synthetic work order"}


def reply(stamp=CHILD):
    return {"ts": stamp, "thread_ts": ROOT, "text": "Synthetic work note"}


def broadcast(count=2, latest=CHILD, stamp=CHILD):
    return {"ts": stamp, "subtype": "thread_broadcast",
            "root": parent(count, latest), "text": "Synthetic work note"}


class Provider:
    def __init__(self, pages):
        self.pages = copy.deepcopy(pages)
        self.calls = []

    def read(self, method, params):
        if method not in ("conversations.history", "conversations.replies"):
            raise AssertionError("Unexpected provider mutation")
        self.calls.append((method, copy.deepcopy(params)))
        if not self.pages:
            raise AssertionError("Unexpected extra read")
        return self.pages.pop(0)


def channel(history, thread_pages=(), **options):
    provider = Provider([page(history), *thread_pages])
    result = read_channel(provider.read, CHANNEL, page_size=100, max_pages=2,
                          max_threads=options.get("max_threads", 1),
                          max_thread_pages=options.get("max_thread_pages", 2))
    return result, provider


class RootObservationTests(unittest.TestCase):
    def test_zero_count_cannot_hide_a_known_latest_reply(self):
        (rows, metadata, complete), provider = channel([parent(0)], [page([parent(0)])])
        self.assertFalse(complete)
        self.assertEqual({row["ts"] for row in rows}, {ROOT})
        self.assertEqual(metadata["threads_pending_count"], 1)
        self.assertEqual(provider.calls[-1][1]["ts"], ROOT)

    def test_zero_count_known_latest_remains_pending_without_expansion(self):
        (_, metadata, complete), provider = channel([parent(0)], max_threads=0)
        self.assertFalse(complete)
        self.assertEqual(metadata["threads_pending_count"], 1)
        self.assertEqual(len(provider.calls), 1)

    def test_later_observation_can_supply_the_previously_missing_reply(self):
        (rows, metadata, complete), provider = channel(
            [parent(0)], [page([parent(1), reply()])])
        self.assertTrue(complete)
        self.assertEqual({row["ts"] for row in rows}, {ROOT, CHILD})
        self.assertEqual(metadata["threads_complete_count"], 1)
        self.assertEqual(len(provider.calls), 2)

    def test_latest_anchor_without_count_cannot_disappear_as_plain_message(self):
        target = {"ts": ROOT, "latest_reply": CHILD, "text": "Synthetic work order"}
        (_, metadata, complete), _ = channel([target])
        self.assertFalse(complete)
        self.assertGreater(metadata["unresolved_thread_roots_count"], 0)

    def test_nested_root_count_survives_channel_expansion(self):
        (_, metadata, complete), _ = channel([broadcast(2)], [page([parent(1), reply()])])
        self.assertFalse(complete)
        self.assertEqual(metadata["thread_coverage"][0]["expected_replies"], 2)

    def test_nested_root_count_survives_direct_context_read(self):
        provider = Provider([page([parent(1), reply()])])
        _, metadata, complete = read_thread_context(provider.read, CHANNEL, broadcast(2))
        self.assertFalse(complete)
        self.assertEqual(metadata["expected_replies"], 2)
        self.assertEqual(provider.calls[0][1]["ts"], ROOT)

    def test_nested_latest_anchor_survives_channel_expansion(self):
        (_, metadata, complete), _ = channel(
            [broadcast(2, latest=FIRST)], [page([parent(2), reply(OTHER), reply()])])
        self.assertFalse(complete)
        self.assertEqual(metadata["thread_coverage"][0]["observed_replies"], 2)

    def test_nested_latest_anchor_survives_direct_context_read(self):
        provider = Provider([page([parent(2), reply(OTHER), reply()])])
        _, metadata, complete = read_thread_context(provider.read, CHANNEL,
                                                   broadcast(2, latest=FIRST))
        self.assertFalse(complete)
        self.assertEqual(metadata["observed_replies"], 2)

    def test_nested_and_top_level_counts_are_combined_not_last_wins(self):
        history = [parent(1), broadcast(3)]
        for ordering in itertools.permutations(history):
            with self.subTest(order=[row["ts"] for row in ordering]):
                (_, metadata, complete), _ = channel(
                    list(ordering), [page([parent(2), reply(FIRST), reply()])])
                self.assertFalse(complete)
                self.assertEqual(metadata["thread_coverage"][0]["expected_replies"], 3)

    def test_multiple_broadcast_counts_are_order_independent(self):
        history = [broadcast(3), broadcast(2, stamp=FIRST)]
        for ordering in itertools.permutations(history):
            with self.subTest(order=[row["ts"] for row in ordering]):
                (_, metadata, complete), _ = channel(
                    list(ordering), [page([parent(2), reply(FIRST), reply()])])
                self.assertFalse(complete)
                self.assertEqual(metadata["thread_coverage"][0]["expected_replies"], 3)

    def test_multiple_nested_anchors_must_all_be_observed(self):
        later = "1700000030.000005"
        missing = "1700000005.000006"
        history = [broadcast(3, latest=missing, stamp=FIRST), broadcast(3, latest=CHILD)]
        for ordering in itertools.permutations(history):
            with self.subTest(order=[row["ts"] for row in ordering]):
                (_, _, complete), _ = channel(list(ordering), [page([
                    parent(3, latest=later), reply(FIRST), reply(), reply(later)])])
                self.assertFalse(complete)

    def test_all_known_nested_evidence_can_be_satisfied(self):
        history = [broadcast(2, latest=FIRST), parent(2)]
        for ordering in itertools.permutations(history):
            with self.subTest(order=[row["ts"] for row in ordering]):
                (rows, metadata, complete), _ = channel(
                    list(ordering), [page([parent(2), reply(FIRST), reply()])])
                self.assertTrue(complete)
                self.assertEqual({row["ts"] for row in rows}, {ROOT, FIRST, CHILD})
                self.assertEqual(metadata["threads_pending_count"], 0)

    def test_direct_satisfied_nested_evidence_retains_no_authority_flags(self):
        provider = Provider([page([parent(2), reply(FIRST), reply()])])
        _, metadata, complete = read_thread_context(provider.read, CHANNEL, broadcast(2))
        self.assertTrue(complete)
        self.assertFalse(metadata["claim_authority"])
        self.assertFalse(metadata["provider_write_authority"])

    def test_invalid_nested_counts_cannot_be_silently_dropped(self):
        for value in (True, -1, "2", 2.0, None, 2147483648):
            with self.subTest(value=value):
                target = broadcast(value)
                (_, _, complete), _ = channel([target], [page([parent(1), reply()])])
                self.assertFalse(complete)
                provider = Provider([page([parent(1), reply()])])
                _, _, complete = read_thread_context(provider.read, CHANNEL, target)
                self.assertFalse(complete)

    def test_invalid_nested_latest_cannot_be_silently_dropped(self):
        for value in (True, "bad", [], "999999999999"):
            with self.subTest(value=value):
                target = broadcast(1, latest=value)
                (_, _, complete), _ = channel([target], [page([parent(1), reply()])])
                self.assertFalse(complete)
                provider = Provider([page([parent(1), reply()])])
                _, _, complete = read_thread_context(provider.read, CHANNEL, target)
                self.assertFalse(complete)

    def test_absent_optional_nested_evidence_remains_supported(self):
        target = broadcast()
        target["root"] = {"ts": ROOT}
        (_, _, complete), _ = channel([target], [page([parent(1), reply()])])
        self.assertTrue(complete)

    def test_broadcast_subtype_cannot_disappear_between_history_pages(self):
        first = {"ts": CHILD, "subtype": "thread_broadcast", "reply_count": 0,
                 "text": "Synthetic work note"}
        second = {key: value for key, value in first.items() if key != "subtype"}
        provider = Provider([page([first], "p2"), page([second])])
        _, metadata, complete = read_channel(provider.read, CHANNEL, page_size=100,
                                             max_pages=2, max_threads=1)
        self.assertFalse(complete)
        self.assertFalse(metadata["history_complete"])
        self.assertEqual(len(provider.calls), 2)

    def test_explicit_subtype_transition_is_not_silently_complete(self):
        first = {"ts": CHILD, "subtype": "thread_broadcast", "reply_count": 0,
                 "text": "Synthetic work note"}
        second = {**first, "subtype": "message"}
        provider = Provider([page([first], "p2"), page([second])])
        _, metadata, complete = read_channel(provider.read, CHANNEL, page_size=100,
                                             max_pages=2, max_threads=1)
        self.assertFalse(complete)
        self.assertFalse(metadata["history_complete"])

    def test_unchanged_paginated_root_remains_complete(self):
        row = {"ts": ROOT, "reply_count": 0, "text": "Synthetic work order"}
        provider = Provider([page([row], "p2"), page([row])])
        rows, _, complete = read_channel(provider.read, CHANNEL, page_size=100,
                                        max_pages=2, max_threads=1)
        self.assertTrue(complete)
        self.assertEqual(rows, [row])

    def test_provider_observations_are_not_mutated(self):
        responses = [page([broadcast(2)]), page([parent(2), reply(FIRST), reply()])]
        before = copy.deepcopy(responses)
        pending = list(responses)
        def read(method, params):
            return pending.pop(0)
        _, _, complete = read_channel(read, CHANNEL, page_size=100,
                                       max_pages=2, max_threads=1)
        self.assertTrue(complete)
        self.assertEqual(responses, before)

    def test_root_anchor_fanout_respects_existing_thread_cap(self):
        roots = [{"ts": str(1700000000 + i), "reply_count": 0,
                  "latest_reply": str(1700000100 + i)} for i in range(3)]
        (_, metadata, complete), provider = channel(roots, [page([])])
        self.assertFalse(complete)
        self.assertEqual(metadata["threads_observed_count"], 3)
        self.assertEqual(metadata["threads_read_count"], 1)
        self.assertEqual(len(provider.calls), 2)

    def test_reply_page_nested_count_survives_channel_expansion(self):
        nested = {**broadcast(3), "thread_ts": ROOT}
        (_, metadata, complete), _ = channel([parent(1)], [page([parent(1), nested])])
        self.assertFalse(complete)
        self.assertEqual(metadata["thread_coverage"][0]["expected_replies"], 3)

    def test_reply_page_nested_count_survives_direct_context_read(self):
        nested = {**broadcast(3), "thread_ts": ROOT}
        provider = Provider([page([parent(1), nested])])
        _, metadata, complete = read_thread_context(provider.read, CHANNEL, parent(1))
        self.assertFalse(complete)
        self.assertEqual(metadata["expected_replies"], 3)

    def test_reply_page_nested_latest_survives_channel_expansion(self):
        nested = {**broadcast(1, latest=FIRST), "thread_ts": ROOT}
        (_, metadata, complete), _ = channel([parent(1)], [page([parent(1), nested])])
        self.assertFalse(complete)
        self.assertEqual(metadata["thread_coverage"][0]["expected_replies"], 1)

    def test_reply_page_nested_latest_survives_direct_context_read(self):
        nested = {**broadcast(1, latest=FIRST), "thread_ts": ROOT}
        provider = Provider([page([parent(1), nested])])
        _, metadata, complete = read_thread_context(provider.read, CHANNEL, parent(1))
        self.assertFalse(complete)
        self.assertEqual(metadata["expected_replies"], 1)

    def test_satisfied_nested_reply_page_evidence_can_be_complete(self):
        nested = {**broadcast(2, latest=FIRST), "thread_ts": ROOT}
        (_, metadata, complete), _ = channel(
            [parent(1)], [page([parent(2), reply(FIRST), nested])])
        self.assertTrue(complete)
        self.assertEqual(metadata["thread_coverage"][0]["expected_replies"], 2)

    def test_count_and_anchor_missingness_matrix(self):
        for prior_count, observed_count, anchor_missing in itertools.product(
                (1, 2, 3), (1, 2, 3), (False, True)):
            stamps = [CHILD, FIRST, OTHER][:observed_count]
            anchor = "1700000005.000006" if anchor_missing else CHILD
            expected_complete = observed_count >= prior_count and not anchor_missing
            with self.subTest(prior=prior_count, observed=observed_count,
                              anchor_missing=anchor_missing):
                (_, metadata, complete), _ = channel([broadcast(prior_count, anchor)],
                    [page([parent(observed_count), *[reply(ts) for ts in stamps]])])
                self.assertEqual(complete, expected_complete)
                self.assertEqual(metadata["thread_coverage"][0]["expected_replies"],
                                 max(prior_count, observed_count))


if __name__ == "__main__":
    unittest.main()
