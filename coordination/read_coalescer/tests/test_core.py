from __future__ import annotations

import dataclasses
from contextlib import closing
import json
import multiprocessing
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from coordination.read_coalescer.core import (Broker, InvalidInput, Lease, Page, Policy,
    ProviderFailure, RateLimited, ReadRequest, canonical, digest, strict_loads)


class Clock:
    def __init__(self, value=1000):
        self.value = value
    def __call__(self):
        return self.value
    def advance(self, amount):
        self.value += amount


def request(**overrides):
    values = dict(provider="slack", app="A1", workspace="T1", method="conversations.history",
                  access_scope="actor1-epoch1", params={"channel": "C1", "limit": 10})
    values.update(overrides)
    return ReadRequest.make(**values)


POLICY = Policy(min_interval_ms=0, lease_ms=1000, failure_backoff_ms=500,
                max_cache_ttl_ms=5000, max_payload_bytes=16384)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "state.db"
        self.clock = Clock()
        self.broker = Broker(self.path, POLICY, self.clock)
        self.req = request()

    def dispatched(self, req=None):
        acquired = self.broker.acquire(req or self.req)
        self.assertEqual(acquired.status, "ACQUIRED")
        self.assertTrue(self.broker.begin_dispatch(acquired.lease))
        return acquired.lease

    def test_request_identity_canonical_and_frozen(self):
        params = {"channel": "C1", "limit": 10}
        first = request(params=params)
        second = request(params={"limit": 10, "channel": "C1"})
        self.assertEqual(first.key, second.key)
        params["channel"] = "C2"
        self.assertEqual(first.params["channel"], "C1")
        self.assertNotEqual(first.key, request(params=params).key)

    def test_visibility_separates_cache_but_not_quota(self):
        other = request(access_scope="actor2-epoch1")
        self.assertNotEqual(self.req.key, other.key)
        self.assertEqual(self.req.bucket, other.bucket)
        self.broker.publish(self.dispatched(), Page({"ok": True, "secret": "scope1-only"}), ttl_ms=1000)
        result = self.broker.acquire(other)
        self.assertEqual(result.status, "ACQUIRED")
        self.assertIsNone(result.page)

    def test_provider_app_workspace_method_all_partition_quotas(self):
        for name, value in (("provider", "other"), ("app", "A2"), ("workspace", "T2"), ("method", "users.list")):
            with self.subTest(name=name):
                other = request(**{name: value})
                self.assertNotEqual(self.req.bucket, other.bucket)
                self.assertNotEqual(self.req.key, other.key)

    def test_cursor_window_limit_are_part_of_identity(self):
        for field, value in (("cursor", "next"), ("oldest", "123.100"), ("latest", "124.000"), ("limit", 9)):
            params = self.req.params
            params[field] = value
            self.assertNotEqual(self.req.key, request(params=params).key)

    def test_credential_fields_and_secret_metadata_rejected(self):
        for params in ({"token": "s"}, {"nested": [{"Authorization": "s"}]}):
            with self.assertRaises(InvalidInput):
                request(params=params)
        with self.assertRaises(InvalidInput):
            request(access_scope="xoxb-this-is-not-a-scope")

    def test_duplicate_read_waits_without_lease(self):
        first = self.broker.acquire(self.req)
        second = self.broker.acquire(self.req)
        self.assertEqual(first.status, "ACQUIRED")
        self.assertEqual(second.reason, "SAME_READ_IN_FLIGHT")
        self.assertIsNone(second.lease)
        self.assertIsNone(second.page)

    def test_success_reused_and_payload_copied(self):
        payload = {"ok": True, "messages": ["one"]}
        outcome = self.broker.publish(self.dispatched(), Page(payload, False, "page2"), ttl_ms=1000)
        payload["messages"].append("mutated")
        cached = self.broker.acquire(self.req)
        self.assertEqual(outcome.page.payload["messages"], ["one"])
        self.assertEqual(cached.status, "CACHE")
        self.assertEqual(cached.page.next_cursor, "page2")
        self.assertFalse(cached.page.collection_end)
        self.assertEqual(outcome.payload_sha256, cached.payload_sha256)
        self.assertFalse(cached.public_dict()["workspace_census_complete"])
        self.assertFalse(cached.public_dict()["send_authorized"])

    def test_unknown_and_query_end_remain_distinct_from_census(self):
        for end in (None, False, True):
            with tempfile.TemporaryDirectory() as tmp:
                b = Broker(Path(tmp)/"s.db", POLICY, self.clock)
                result = b.read_once(self.req, lambda _: Page({"ok": True, "messages": []}, end), ttl_ms=1000)
                self.assertIs(result.page.collection_end, end)
                self.assertFalse(result.public_dict()["workspace_census_complete"])

    def test_cache_ttl_exact_expiry(self):
        self.broker.publish(self.dispatched(), Page({"ok": True}), ttl_ms=1000)
        self.clock.advance(999)
        self.assertEqual(self.broker.acquire(self.req).status, "CACHE")
        self.clock.advance(1)
        self.assertEqual(self.broker.acquire(self.req).status, "ACQUIRED")

    def test_max_age_can_require_new_read(self):
        self.broker.publish(self.dispatched(), Page({"ok": True}), ttl_ms=1000)
        self.clock.advance(101)
        self.assertEqual(self.broker.acquire(self.req, max_age_ms=100).status, "ACQUIRED")

    def test_clock_rollback_does_not_return_future_cache(self):
        self.broker.publish(self.dispatched(), Page({"ok": True}), ttl_ms=1000)
        self.clock.advance(-1)
        self.assertNotEqual(self.broker.acquire(self.req).status, "CACHE")

    def test_zero_ttl_not_reused(self):
        calls = []
        for _ in range(2):
            self.broker.read_once(self.req, lambda _: (calls.append(1) or Page({"ok": True})), ttl_ms=0)
        self.assertEqual(len(calls), 2)

    def test_shared_cooldown_blocks_other_visibility_and_channel(self):
        result = self.broker.fail(self.dispatched(), RateLimited(20_000))
        self.assertEqual(result.retry_at_ms, 21_000)
        second = Broker(self.path, POLICY, self.clock)
        other = request(access_scope="actor2", params={"channel": "C2"})
        self.assertEqual(second.acquire(other).reason, "PROVIDER_COOLDOWN")
        self.assertEqual(second.acquire(request(workspace="T2")).status, "ACQUIRED")
        self.assertEqual(second.acquire(request(method="users.list")).status, "ACQUIRED")

    def test_429_never_returns_empty_success_and_never_retries(self):
        calls = []
        def reader(_):
            calls.append(1)
            raise RateLimited(2500)
        result = self.broker.read_once(self.req, reader, ttl_ms=1000)
        self.assertEqual(result.status, "WAIT")
        self.assertEqual(result.reason, "RATE_LIMITED")
        self.assertIsNone(result.page)
        self.broker.read_once(self.req, reader, ttl_ms=1000)
        self.assertEqual(calls, [1])
        self.assertEqual(self.broker.stats()["rows"]["cache"], 0)

    def test_cooldown_boundary_not_shortened(self):
        self.broker.fail(self.dispatched(), RateLimited(2500))
        self.clock.advance(2499)
        self.assertEqual(self.broker.acquire(self.req).status, "WAIT")
        self.clock.advance(1)
        self.assertEqual(self.broker.acquire(self.req).status, "ACQUIRED")

    def test_fresh_cache_available_during_method_cooldown(self):
        self.broker.publish(self.dispatched(), Page({"ok": True}), ttl_ms=5000)
        other = request(params={"channel": "C2"})
        lease = self.dispatched(other)
        self.broker.fail(lease, RateLimited(5000))
        self.assertEqual(self.broker.acquire(self.req).status, "CACHE")

    def test_duplicate_429_does_not_extend_cooldown(self):
        lease = self.dispatched()
        self.broker.fail(lease, RateLimited(2000))
        self.clock.advance(500)
        result = self.broker.fail(lease, RateLimited(9999))
        self.assertEqual(result.status, "DISCARDED")
        self.assertEqual(self.broker.acquire(self.req).retry_at_ms, 3000)
        self.assertEqual(self.broker.stats()["counters"]["provider_429s"], 1)

    def test_unstarted_attempt_cannot_report_provider_429(self):
        lease = self.broker.acquire(self.req).lease
        self.assertEqual(self.broker.fail(lease, RateLimited(2000)).status, "DISCARDED")
        self.assertEqual(self.broker.stats()["counters"].get("provider_429s", 0), 0)

    def test_lease_exact_expiry_and_new_owner_fences_old_success(self):
        old = self.dispatched()
        self.clock.advance(POLICY.lease_ms)
        new = self.dispatched()
        self.assertNotEqual(old.token, new.token)
        self.assertEqual(self.broker.publish(old, Page({"ok": True, "v": "old"}), ttl_ms=1000).status, "DISCARDED")
        self.broker.publish(new, Page({"ok": True, "v": "new"}), ttl_ms=1000)
        self.assertEqual(self.broker.acquire(self.req).page.payload["v"], "new")

    def test_expired_without_successor_still_cannot_publish(self):
        old = self.dispatched()
        self.clock.advance(POLICY.lease_ms)
        self.assertEqual(self.broker.publish(old, Page({"ok": True}), ttl_ms=1000).status, "DISCARDED")
        self.assertEqual(self.broker.stats()["rows"]["cache"], 0)

    def test_late_429_still_blocks_method_not_successor_cache(self):
        old = self.dispatched()
        self.clock.advance(POLICY.lease_ms)
        new = self.dispatched()
        self.broker.fail(old, RateLimited(5000))
        self.broker.publish(new, Page({"ok": True, "version": "new"}), ttl_ms=1000)
        self.assertEqual(self.broker.acquire(self.req).status, "CACHE")
        self.assertEqual(self.broker.acquire(request(params={"channel": "C2"})).reason, "PROVIDER_COOLDOWN")

    def test_late_shorter_429_does_not_shorten_existing_embargo(self):
        old = self.dispatched()
        self.clock.advance(POLICY.lease_ms)
        new = self.dispatched()
        self.broker.fail(new, RateLimited(50_000))
        self.broker.fail(old, RateLimited(1000))
        self.assertEqual(self.broker.acquire(self.req).retry_at_ms, 52_000)

    def test_new_429_cancels_issued_not_started_work(self):
        old = self.dispatched()
        self.clock.advance(POLICY.lease_ms)
        new = self.broker.acquire(self.req).lease
        self.broker.fail(old, RateLimited(5000))
        self.assertFalse(self.broker.begin_dispatch(new))
        self.assertEqual(self.broker.stats()["counters"]["provider_dispatches"], 1)

    def test_begin_dispatch_only_once(self):
        lease = self.dispatched()
        self.assertFalse(self.broker.begin_dispatch(lease))
        self.assertEqual(self.broker.publish(lease, Page({"ok": True}), ttl_ms=1000).status, "FETCHED")

    def test_publish_only_once_and_requires_dispatch(self):
        lease = self.broker.acquire(self.req).lease
        self.assertEqual(self.broker.publish(lease, Page({"ok": True}), ttl_ms=1000).status, "DISCARDED")
        self.assertTrue(self.broker.begin_dispatch(lease))
        self.broker.publish(lease, Page({"ok": True}), ttl_ms=1000)
        self.assertEqual(self.broker.publish(lease, Page({"ok": True, "changed": 1}), ttl_ms=1000).status, "DISCARDED")
        self.assertNotIn("changed", self.broker.acquire(self.req).page.payload)

    def test_forged_or_transplanted_lease_is_not_a_receipt(self):
        lease = self.dispatched()
        for changed in (dataclasses.replace(lease, token="invented"),
                        dataclasses.replace(lease, bucket=request(workspace="T2").bucket),
                        dataclasses.replace(lease, expires_at_ms=lease.expires_at_ms + 1)):
            with self.assertRaises(InvalidInput):
                self.broker.fail(changed, RateLimited(5000))

    def test_failures_backoff_by_key_not_empty_cache(self):
        self.broker.fail(self.dispatched(), ProviderFailure("TIMEOUT"))
        result = self.broker.acquire(self.req)
        self.assertEqual(result.reason, "TIMEOUT")
        self.assertIsNone(result.page)
        self.assertEqual(self.broker.acquire(request(params={"channel": "C2"})).status, "ACQUIRED")

    def test_raw_exception_secrets_not_stored(self):
        def broken(_):
            raise RuntimeError("SECRET-XOXB-do-not-store")
        result = self.broker.read_once(self.req, broken, ttl_ms=1000)
        self.assertEqual(result.reason, "READ_EXCEPTION")
        with closing(sqlite3.connect(self.path)) as con:
            text = "\n".join(con.iterdump())
        self.assertNotIn("SECRET-XOXB", text)
        self.assertNotIn("SECRET-XOXB", repr(result))

    def test_invalid_callback_page_is_failure_not_cache(self):
        cases = [lambda _: None, lambda _: Page({"ok": False}),
                 lambda _: Page({"ok": True}, True, "cursor"),
                 lambda _: Page({"ok": True, "value": 1.5}),
                 lambda _: Page({"ok": True, "value": "x"*20_000})]
        for reader in cases:
            with tempfile.TemporaryDirectory() as tmp:
                b = Broker(Path(tmp)/"s.db", POLICY, self.clock)
                result = b.read_once(self.req, reader, ttl_ms=1000)
                self.assertEqual(result.status, "ERROR")
                self.assertEqual(b.stats()["rows"]["cache"], 0)

    def test_invalid_ttl_rejected_before_provider_call(self):
        calls = []
        for ttl in (-1, True, 5001):
            with self.assertRaises(InvalidInput):
                self.broker.read_once(self.req, lambda _: calls.append(1), ttl_ms=ttl)
        self.assertEqual(calls, [])

    def test_policy_is_shared_and_cannot_silently_drift(self):
        Broker(self.path, POLICY, self.clock)
        with self.assertRaises(InvalidInput):
            Broker(self.path, dataclasses.replace(POLICY, min_interval_ms=1), self.clock)

    def test_database_symlink_or_public_mode_rejected(self):
        link = Path(self.temp.name)/"link.db"
        link.symlink_to(self.path)
        with self.assertRaises(InvalidInput):
            Broker(link, POLICY, self.clock)
        os.chmod(self.path, 0o644)
        with self.assertRaises(InvalidInput):
            Broker(self.path, POLICY, self.clock)

    def test_cache_corruption_not_silently_empty_or_refetched(self):
        self.broker.publish(self.dispatched(), Page({"ok": True}), ttl_ms=1000)
        with closing(sqlite3.connect(self.path)) as con:
            con.execute("UPDATE cache SET page='{}'")
            con.commit()
        with self.assertRaises(InvalidInput):
            self.broker.acquire(self.req)

    def test_minimum_start_spacing_tracks_actual_dispatch(self):
        path = Path(self.temp.name)/"spacing.db"
        policy = dataclasses.replace(POLICY, min_interval_ms=100)
        b = Broker(path, policy, self.clock)
        first = b.acquire(self.req).lease
        self.clock.advance(500)
        self.assertTrue(b.begin_dispatch(first))
        b.publish(first, Page({"ok": True}), ttl_ms=1000)
        wait = b.acquire(request(params={"channel": "C2"}))
        self.assertEqual(wait.reason, "METHOD_START_SPACING")
        self.assertEqual(wait.retry_at_ms, 1600)

    def test_delayed_older_issued_read_cannot_break_dispatch_spacing(self):
        path = Path(self.temp.name)/"parallel.db"
        policy = dataclasses.replace(POLICY, min_interval_ms=100, max_inflight_per_bucket=2)
        b = Broker(path, policy, self.clock)
        first = b.acquire(self.req).lease
        self.clock.advance(100)
        second = b.acquire(request(params={"channel": "C2"})).lease
        self.assertTrue(b.begin_dispatch(second))
        self.assertFalse(b.begin_dispatch(first))

    def test_inflight_limit_applies_to_distinct_reads(self):
        self.dispatched()
        result = self.broker.acquire(request(params={"channel": "C2"}))
        self.assertEqual(result.reason, "METHOD_IN_FLIGHT")

    def test_maintenance_preserves_live_leases_then_removes_expired_state(self):
        lease = self.dispatched()
        self.assertEqual(self.broker.maintain(retain_ms=1000)["attempts"], 0)
        self.broker.publish(lease, Page({"ok": True}), ttl_ms=1000)
        self.clock.advance(2001)
        removed = self.broker.maintain(retain_ms=1000)
        self.assertEqual(removed["attempts"], 1)
        self.assertEqual(removed["cache"], 1)
        with self.assertRaises(InvalidInput):
            self.broker.fail(lease, RateLimited(1))

    def test_clock_rollback_during_read_discards_success(self):
        lease = self.dispatched()
        self.clock.advance(-1)
        self.assertEqual(self.broker.publish(lease, Page({"ok": True}), ttl_ms=1000).status, "DISCARDED")
        self.assertEqual(self.broker.stats()["rows"]["cache"], 0)

    def test_quota_cardinality_stops_at_capacity(self):
        path = Path(self.temp.name)/"quota-budget.db"
        b = Broker(path, dataclasses.replace(POLICY, max_records=1), self.clock)
        b.read_once(self.req, lambda _: Page({"ok": True}), ttl_ms=1000)
        result = b.acquire(request(workspace="T2"))
        self.assertEqual(result.reason, "MAINTENANCE_REQUIRED")
        self.assertEqual(b.stats()["rows"]["quotas"], 1)

    def test_cache_byte_budget_evicts_oldest_not_new_page(self):
        path = Path(self.temp.name)/"budget.db"
        policy = dataclasses.replace(POLICY, max_payload_bytes=256, max_cache_bytes=256)
        b = Broker(path, policy, self.clock)
        first = b.read_once(self.req, lambda _: Page({"ok": True, "data": "é"*50}), ttl_ms=1000)
        other = request(params={"channel": "C2"})
        b.read_once(other, lambda _: Page({"ok": True, "data": "é"*50}), ttl_ms=1000)
        self.assertEqual(first.status, "FETCHED")
        self.assertEqual(b.acquire(other).status, "CACHE")
        self.assertEqual(b.acquire(self.req).status, "ACQUIRED")
        self.assertLessEqual(b.stats()["cached_payload_bytes"], 256)
        self.assertEqual(b.stats()["counters"]["cache_budget_evictions"], 1)

    def test_capacity_returns_explicit_error_no_provider_callback(self):
        path = Path(self.temp.name)/"capacity.db"
        policy = dataclasses.replace(POLICY, max_records=1)
        b = Broker(path, policy, self.clock)
        b.read_once(self.req, lambda _: Page({"ok": True}), ttl_ms=1000)
        result = b.acquire(request(params={"channel": "C2"}))
        self.assertEqual(result.status, "ERROR")
        self.assertEqual(result.reason, "MAINTENANCE_REQUIRED")


class JSONTests(unittest.TestCase):
    def test_canonical_json_accepts_exact_supported_values(self):
        value = {"none": None, "truth": True, "int": 2**64, "nested": ["héllo", {"a": 1}]}
        self.assertEqual(strict_loads(canonical(value)), value)

    def test_strict_json_hostiles(self):
        for raw in ('{"a":1,"a":2}', '{"a":1.0}', '{"a":NaN}', '{"a":Infinity}',
                    '{"a":"\\ud800"}', '{"a":' + '9'*100 + '}', '['*40 + '0' + ']'*40):
            with self.subTest(raw=raw[:30]), self.assertRaises(InvalidInput):
                strict_loads(raw)

    def test_nonjson_types_cycles_and_nonstring_keys(self):
        cycle = []
        cycle.append(cycle)
        for value in (1.0, float("nan"), {1: "a"}, (1, 2), cycle, 10**10_000):
            with self.assertRaises(InvalidInput):
                canonical(value)

    def test_invalid_utf8_and_oversize(self):
        for raw in (b'"\xff"', b'"' + b'x'*100 + b'"'):
            with self.assertRaises(InvalidInput):
                strict_loads(raw, 64)


# Spawn, rather than fork, verifies independent Python processes + connections.
def parallel_worker(path, barrier, counter, results):
    try:
        b = Broker(path)
        req = request()
        barrier.wait(timeout=30)
        def read(_):
            with counter.get_lock():
                counter.value += 1
            time.sleep(0.20)
            return Page({"ok": True, "messages": ["synthetic-race"]}, True)
        deadline = time.monotonic() + 20
        waits = 0
        while time.monotonic() < deadline:
            result = b.read_once(req, read, ttl_ms=30_000)
            if result.status in ("CACHE", "FETCHED"):
                results.put({"status": result.status, "sha": result.payload_sha256, "waits": waits})
                return
            if result.status != "WAIT":
                raise RuntimeError(result.reason)
            waits += 1
            time.sleep(0.025)
        raise RuntimeError("race deadline exceeded")
    except BaseException as exc:
        results.put({"error": type(exc).__name__ + ":" + str(exc)})


class ProcessTests(unittest.TestCase):
    def test_twelve_processes_share_one_provider_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp)/"race.db")
            Broker(path)
            ctx = multiprocessing.get_context("spawn")
            workers = 12
            barrier, counter, queue = ctx.Barrier(workers), ctx.Value("i", 0), ctx.Queue()
            processes = [ctx.Process(target=parallel_worker, args=(path, barrier, counter, queue)) for _ in range(workers)]
            try:
                for process in processes:
                    process.start()
                results = [queue.get(timeout=40) for _ in processes]
                for process in processes:
                    process.join(timeout=5)
                self.assertTrue(all(process.exitcode == 0 for process in processes), results)
                self.assertFalse(any("error" in item for item in results), results)
                self.assertEqual(counter.value, 1)
                self.assertEqual(sum(r["status"] == "FETCHED" for r in results), 1)
                self.assertEqual(len({r["sha"] for r in results}), 1)
                self.assertEqual(Broker(path).stats()["counters"]["provider_dispatches"], 1)
            finally:
                for process in processes:
                    if process.is_alive():
                        process.terminate()
                    process.join(timeout=5)
                queue.close()


if __name__ == "__main__":
    unittest.main()
