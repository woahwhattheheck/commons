#!/usr/bin/env python3
"""Regression tests for provider-state drift during outbound lease takeover."""
from __future__ import annotations

import datetime as dt
import unittest

from revenue.outbound_mutex.lease import (
    PreflightFailed,
    acquire,
    fingerprint,
    release,
    takeover,
)

UTC = dt.timezone.utc
T0 = dt.datetime(2026, 9, 14, 3, 50, 0, tzinfo=UTC)


class TakeoverProviderSnapshotTests(unittest.TestCase):
    def _claim(self, *, ttl_seconds: int = 60):
        return acquire(
            opportunity="paid-pilot",
            channel="email",
            destination="buyer@example.invalid",
            holder="worker-a",
            provider_snapshot="provider-generation-p1",
            now=T0,
            ttl_seconds=ttl_seconds,
        )

    def test_expired_takeover_rejects_provider_drift_after_unfinalized_send(self):
        lease = self._claim(ttl_seconds=1)
        with self.assertRaisesRegex(PreflightFailed, "provider state changed"):
            takeover(
                lease,
                holder="worker-b",
                provider_snapshot="provider-generation-p2",
                now=T0 + dt.timedelta(seconds=2),
            )

    def test_released_takeover_rejects_provider_drift_after_unfinalized_send(self):
        lease = self._claim()
        released = release(
            lease,
            holder="worker-a",
            reason="worker stopped before durable send finalization",
            now=T0 + dt.timedelta(seconds=1),
        )
        with self.assertRaisesRegex(PreflightFailed, "provider state changed"):
            takeover(
                released,
                holder="worker-b",
                provider_snapshot="provider-generation-p2",
                now=T0 + dt.timedelta(seconds=2),
            )

    def test_expired_takeover_with_unchanged_provider_remains_allowed(self):
        lease = self._claim(ttl_seconds=1)
        taken = takeover(
            lease,
            holder="worker-b",
            provider_snapshot="provider-generation-p1",
            now=T0 + dt.timedelta(seconds=2),
        )
        self.assertEqual(taken.holder, "worker-b")
        self.assertEqual(taken.generation, lease.generation + 1)
        self.assertEqual(taken.provider_snapshot, fingerprint("provider-generation-p1"))

    def test_released_takeover_with_unchanged_provider_remains_allowed(self):
        lease = self._claim()
        released = release(
            lease,
            holder="worker-a",
            reason="unsent handoff",
            now=T0 + dt.timedelta(seconds=1),
        )
        taken = takeover(
            released,
            holder="worker-b",
            provider_snapshot="provider-generation-p1",
            now=T0 + dt.timedelta(seconds=2),
        )
        self.assertEqual(taken.holder, "worker-b")
        self.assertEqual(taken.generation, released.generation + 1)
        self.assertEqual(taken.provider_snapshot, lease.provider_snapshot)
        self.assertIsNone(taken.released_at)
        self.assertIsNone(taken.release_reason)


if __name__ == "__main__":
    unittest.main()
