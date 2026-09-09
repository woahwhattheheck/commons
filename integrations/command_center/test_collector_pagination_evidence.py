"""GitHub count and short-page evidence must agree before replacing a source."""
from __future__ import annotations

import copy
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from integrations.command_center.collectors import LiveCollectors, SourceFailure
from integrations.command_center.workstreams import WorkstreamStore


class Pages:
    def __init__(self, responses):
        self.responses = copy.deepcopy(responses)
        self.requests = []

    def github(self, endpoint, *, method="GET"):
        if method != "GET":
            raise AssertionError("Provider writes are outside collection")
        self.requests.append(endpoint)
        return self.responses.pop(0)


class GitHubPageEvidenceTests(unittest.TestCase):
    def pages(self, responses, *, key="items", size=3, max_pages=2):
        provider = Pages(responses)
        collector = LiveCollectors(None, {"page_size": size, "max_pages": max_pages}, equipment=provider)
        result = collector._pages("search/issues?q=fixture", key)
        return result, provider

    def test_short_page_with_more_total_is_incomplete(self):
        (rows, complete), provider = self.pages([{"items": [{"id": 1}], "total_count": 5}])
        self.assertEqual(rows, [{"id": 1}])
        self.assertFalse(complete)
        self.assertEqual(len(provider.requests), 1)

    def test_empty_page_with_more_total_is_incomplete(self):
        (rows, complete), _ = self.pages([{"items": [], "total_count": 5}])
        self.assertEqual(rows, [])
        self.assertFalse(complete)

    def test_short_last_page_uses_accumulated_count(self):
        (rows, complete), provider = self.pages([
            {"items": [{"id": 1}, {"id": 2}, {"id": 3}], "total_count": 8},
            {"items": [{"id": 4}], "total_count": 8},
        ])
        self.assertEqual(len(rows), 4)
        self.assertFalse(complete)
        self.assertEqual(parse_qs(urlsplit(provider.requests[1]).query)["page"], ["2"])

    def test_exact_total_with_short_last_page_is_complete(self):
        (rows, complete), _ = self.pages([
            {"items": [{"id": 1}, {"id": 2}, {"id": 3}], "total_count": 4},
            {"items": [{"id": 4}], "total_count": 4},
        ])
        self.assertEqual(len(rows), 4)
        self.assertTrue(complete)

    def test_exact_total_at_budget_is_complete(self):
        (_, complete), _ = self.pages([{"items": [1, 2, 3], "total_count": 3}], max_pages=1)
        self.assertTrue(complete)

    def test_more_total_at_budget_remains_incomplete(self):
        (_, complete), _ = self.pages([{"items": [1, 2, 3], "total_count": 4}], max_pages=1)
        self.assertFalse(complete)

    def test_zero_total_with_empty_page_is_complete(self):
        (_, complete), _ = self.pages([{"items": [], "total_count": 0}])
        self.assertTrue(complete)

    def test_list_endpoint_short_page_needs_no_total(self):
        (rows, complete), _ = self.pages([[1]], key=None)
        self.assertEqual(rows, [1])
        self.assertTrue(complete)

    def test_list_endpoint_at_page_budget_is_not_complete(self):
        (_, complete), _ = self.pages([[1, 2, 3]], key=None, max_pages=1)
        self.assertFalse(complete)

    def test_optional_total_can_be_omitted(self):
        (_, complete), _ = self.pages([{"items": [1]}])
        self.assertTrue(complete)

    def test_incomplete_flag_persists_across_pages(self):
        (_, complete), _ = self.pages([
            {"items": [1, 2, 3], "total_count": 4, "incomplete_results": True},
            {"items": [4], "total_count": 4, "incomplete_results": False},
        ])
        self.assertFalse(complete)

    def test_boolean_total_is_not_an_integer_count(self):
        with self.assertRaisesRegex(SourceFailure, "github_pagination_shape"):
            self.pages([{"items": [], "total_count": True}])

    def test_negative_total_is_not_completion_evidence(self):
        with self.assertRaisesRegex(SourceFailure, "github_pagination_shape"):
            self.pages([{"items": [], "total_count": -1}])

    def test_string_total_is_not_completion_evidence(self):
        with self.assertRaisesRegex(SourceFailure, "github_pagination_shape"):
            self.pages([{"items": [], "total_count": "5"}])

    def test_null_total_is_not_an_omitted_count(self):
        with self.assertRaisesRegex(SourceFailure, "github_pagination_shape"):
            self.pages([{"items": [], "total_count": None}])

    def test_nonboolean_incomplete_flag_is_rejected(self):
        with self.assertRaisesRegex(SourceFailure, "github_pagination_shape"):
            self.pages([{"items": [], "total_count": 0, "incomplete_results": 0}])

    def test_malformed_rows_keep_existing_shape_error(self):
        with self.assertRaisesRegex(SourceFailure, "github_response_shape"):
            self.pages([{"items": {}, "total_count": 0}])

    def test_overlapping_page_id_does_not_fake_total_completion(self):
        (rows, complete), _ = self.pages([
            {"items": [{"id": 1}, {"id": 2}, {"id": 3}], "total_count": 4},
            {"items": [{"id": 3}], "total_count": 4},
        ])
        self.assertEqual([row["id"] for row in rows], [1, 2, 3])
        self.assertFalse(complete)

    def test_overlapping_page_id_is_emitted_once_when_total_is_met(self):
        (rows, complete), _ = self.pages([
            {"items": [{"id": 1}, {"id": 2}, {"id": 3}], "total_count": 4},
            {"items": [{"id": 3}, {"id": 4}], "total_count": 4},
        ])
        self.assertEqual([row["id"] for row in rows], [1, 2, 3, 4])
        self.assertTrue(complete)

    def test_truncated_pr_search_retains_real_store_records_and_owner_work(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorkstreamStore(directory)
            source = {"id": "github:prs", "provider": "GitHub", "scope": {"author_or_owner": "fixture"},
                      "observed_at": "2026-09-08T02:00:00Z", "status": "live", "coverage": {"complete": True}}
            item = {"id": "github:pr:fixture/project#1", "title": "Previously recorded work", "kind": "pull_request"}
            store.ingest({"operation_id": "initial", "source": source, "items": [item]})
            store.update_work({"operation_id": "owner:next", "source_id": "github:prs",
                               "item_id": item["id"], "next_action": "Preserve next action"})
            before = store.state()["items"]
            provider = Pages([{"items": [], "total_count": 5, "incomplete_results": False}] * 4)
            collector = LiveCollectors(store, {}, equipment=provider, clock=lambda: "2026-09-08T02:01:00Z")
            receipt = store.ingest(collector._pull_requests("fixture"))
            self.assertFalse(receipt["coverage"]["complete"])
            self.assertEqual((receipt["removed"], receipt["retained"]), (0, 1))
            self.assertEqual(store.state()["items"], before)


if __name__ == "__main__":
    unittest.main()
