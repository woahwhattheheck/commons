from datetime import datetime, timedelta, timezone
import unittest

from batch import MemoizingTransport, ReceiptCache, candidate_fingerprint, process_batch
from models import Candidate, Response
from receipt import receipt_hash

NOW = datetime(2026, 9, 13, 7, 40, tzinfo=timezone.utc)


class UnderlyingTransport:
    def __init__(self):
        self.calls = []

    def fetch(self, url, *, accept):
        self.calls.append((url, accept))
        return Response(url=url, status=200, headers={}, body=b"{}")


def candidate(url="https://board.example/bounty/1", canonical="https://github.com/acme/repo/issues/7", amount="500"):
    return Candidate.validated(
        candidate_url=url,
        platform="fixture",
        advertised_amount=amount,
        currency="USD",
        canonical_url=canonical,
        max_age_days=30,
    )


def receipt_for(item, status="actionable"):
    value = {
        "schema": "funded-work-freshness/v1",
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "candidate": {
            "url": item.candidate_url,
            "platform": item.platform,
            "advertised_amount": item.advertised_amount,
            "currency": item.currency,
            "canonical_url_hint": item.canonical_url,
        },
        "canonical": {"url": item.canonical_url, "state": "open"},
        "freshness_status": status,
        "route": "qualified_for_human_claim_decision" if status == "actionable" else "reject",
        "reasons": ["fixture"],
    }
    value["receipt_sha256"] = receipt_hash(value)
    return value


class BatchTests(unittest.TestCase):
    def test_exact_duplicate_evaluated_once(self):
        item = candidate()
        calls = []

        def evaluator(candidate, transport, *, observed_at):
            calls.append(candidate)
            return receipt_for(candidate)

        report, _ = process_batch([item, item], UnderlyingTransport(), observed_at=NOW, evaluator=evaluator)
        self.assertEqual(1, len(calls))
        self.assertEqual(1, report["stats"]["batch_duplicate_hits"])
        self.assertEqual("batch_duplicate", report["items"][1]["source"])
        self.assertEqual(0, report["items"][1]["duplicate_of"])

    def test_same_canonical_shares_http_response_without_sharing_policy(self):
        first = candidate(url="https://a.example/1", amount="500")
        second = candidate(url="https://b.example/2", amount="750")
        underlying = UnderlyingTransport()

        def evaluator(item, transport, *, observed_at):
            transport.fetch("https://api.github.com/repos/acme/repo/issues/7", accept="application/json")
            return receipt_for(item)

        report, _ = process_batch([first, second], underlying, observed_at=NOW, evaluator=evaluator)
        self.assertEqual(1, len(underlying.calls))
        self.assertEqual(1, report["stats"]["http_network_fetches"])
        self.assertEqual(1, report["stats"]["http_memo_hits"])
        self.assertEqual([0, 1], report["canonical_groups"][first.canonical_url])
        self.assertEqual("500", report["items"][0]["receipt"]["candidate"]["advertised_amount"])
        self.assertEqual("750", report["items"][1]["receipt"]["candidate"]["advertised_amount"])

    def test_fresh_persistent_cache_skips_evaluator(self):
        item = candidate()
        cache = ReceiptCache()
        cache.put(item, receipt_for(item, status="occupied"), cached_at=NOW - timedelta(seconds=10))

        def fail(*args, **kwargs):
            raise AssertionError("evaluator should not run")

        report, _ = process_batch(
            [item], UnderlyingTransport(), observed_at=NOW, cache=cache, cache_ttl_seconds=60, evaluator=fail
        )
        self.assertEqual("persistent_cache", report["items"][0]["source"])
        self.assertEqual(1, report["stats"]["persistent_cache_hits"])
        self.assertEqual(0, report["stats"]["fresh_evaluations"])

    def test_actionable_persistent_cache_is_never_reused(self):
        item = candidate()
        cache = ReceiptCache()
        cache.put(item, receipt_for(item), cached_at=NOW - timedelta(seconds=1))
        calls = []

        def evaluator(candidate, transport, *, observed_at):
            calls.append(candidate)
            return receipt_for(candidate, status="occupied")

        report, _ = process_batch(
            [item], UnderlyingTransport(), observed_at=NOW, cache=cache,
            cache_ttl_seconds=60, evaluator=evaluator
        )
        self.assertEqual("fresh", report["items"][0]["source"])
        self.assertEqual(1, len(calls))

    def test_expired_or_corrupt_cache_forces_fresh_evaluation(self):
        item = candidate()
        cache = ReceiptCache()
        old = receipt_for(item)
        cache.put(item, old, cached_at=NOW - timedelta(seconds=61))
        calls = []

        def evaluator(candidate, transport, *, observed_at):
            calls.append(candidate)
            return receipt_for(candidate, status="occupied")

        report, cache = process_batch(
            [item], UnderlyingTransport(), observed_at=NOW, cache=cache, cache_ttl_seconds=60, evaluator=evaluator
        )
        self.assertEqual(1, len(calls))
        self.assertEqual("fresh", report["items"][0]["source"])
        key = candidate_fingerprint(item)
        cache.entries[key]["receipt"]["freshness_status"] = "actionable"
        report, _ = process_batch(
            [item], UnderlyingTransport(), observed_at=NOW + timedelta(seconds=1), cache=cache,
            cache_ttl_seconds=60, evaluator=evaluator
        )
        self.assertEqual("fresh", report["items"][0]["source"])
        self.assertEqual(2, len(calls))

    def test_cache_bound_keeps_newest_entries(self):
        cache = ReceiptCache()
        items = [candidate(url=f"https://board.example/{i}") for i in range(3)]
        for index, item in enumerate(items):
            cache.put(item, receipt_for(item), cached_at=NOW + timedelta(seconds=index))
        payload = cache.to_payload(max_entries=2)
        self.assertEqual(2, len(payload["entries"]))
        self.assertNotIn(candidate_fingerprint(items[0]), payload["entries"])


if __name__ == "__main__":
    unittest.main()
