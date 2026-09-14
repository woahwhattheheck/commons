import copy
import datetime as dt
import unittest

from lead_fence import (
    ACTIVE,
    RELEASED,
    SENT,
    ConflictError,
    LeadFence,
    claim_path,
    fingerprint,
    normalize_identity,
)

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 9, 14, 3, 55, 0, tzinfo=UTC)


class FakeClient:
    def __init__(self):
        self.store = {}
        self.counter = 0
        self.conflict_on_create = False
        self.conflict_payload = None
        self.conflict_on_update = False
        self.update_conflict_payload = None

    def _sha(self):
        self.counter += 1
        return f"sha-{self.counter}"

    def read_json(self, path):
        item = self.store.get(path)
        return None if item is None else (copy.deepcopy(item[0]), item[1])

    def create_json(self, path, payload, message):
        if self.conflict_on_create:
            self.conflict_on_create = False
            if self.conflict_payload is not None:
                self.store[path] = (copy.deepcopy(self.conflict_payload), self._sha())
            raise ConflictError("simulated create race")
        if path in self.store:
            raise ConflictError("already exists")
        sha = self._sha()
        self.store[path] = (copy.deepcopy(payload), sha)
        return f"commit-{self.counter}"

    def update_json(self, path, payload, sha, message):
        current = self.store.get(path)
        if current is None or current[1] != sha:
            raise ConflictError("stale sha")
        if self.conflict_on_update:
            self.conflict_on_update = False
            if self.update_conflict_payload is not None:
                self.store[path] = (copy.deepcopy(self.update_conflict_payload), self._sha())
            raise ConflictError("simulated update race")
        new_sha = self._sha()
        self.store[path] = (copy.deepcopy(payload), new_sha)
        return f"commit-{self.counter}"


class LeadFenceTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.fence = LeadFence(self.client, now_fn=lambda: NOW)

    def test_identity_normalization(self):
        self.assertEqual(normalize_identity(" Alice@Example.COM "), "email:alice@example.com")
        self.assertEqual(normalize_identity("mailto:Alice@Example.COM"), "email:alice@example.com")
        self.assertEqual(normalize_identity("https://www.Example.com/path?q=1"), "domain:example.com")
        self.assertEqual(normalize_identity("domain:EXAMPLE.COM."), "domain:example.com")

    def test_fingerprint_and_path_are_deterministic(self):
        a = fingerprint("Alice@Example.com")
        b = fingerprint("mailto:alice@example.COM")
        self.assertEqual(a, b)
        self.assertTrue(claim_path("Alice@Example.com").endswith(f"/{a}.json"))

    def test_new_claim_does_not_store_raw_identity(self):
        result = self.fence.claim("Alice@Example.com", "Z-A", "outreach")
        self.assertTrue(result.ok)
        self.assertEqual(result.outcome, "ACQUIRED")
        serialized = repr(result.record).lower()
        self.assertNotIn("alice@example.com", serialized)
        self.assertEqual(result.record["state"], ACTIVE)

    def test_active_claim_blocks_second_sender(self):
        first = self.fence.claim("alice@example.com", "Z-A", "campaign-a")
        second = self.fence.claim("ALICE@example.com", "Z-B", "campaign-b")
        self.assertTrue(first.ok)
        self.assertFalse(second.ok)
        self.assertEqual(second.outcome, "COLLISION")
        self.assertEqual(second.record["actor"], "Z-A")

    def test_create_race_loser_reads_winner(self):
        winner = self.fence._new_active("alice@example.com", "Z-WINNER", "campaign", 30, "test")
        self.client.conflict_on_create = True
        self.client.conflict_payload = winner
        result = self.fence.claim("alice@example.com", "Z-LOSER", "campaign")
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome, "COLLISION")
        self.assertEqual(result.record["actor"], "Z-WINNER")

    def test_expired_claim_can_be_reacquired(self):
        old_now = NOW - dt.timedelta(hours=2)
        old_fence = LeadFence(self.client, now_fn=lambda: old_now)
        old_fence.claim("alice@example.com", "Z-OLD", "campaign", ttl_minutes=30)
        result = self.fence.claim("alice@example.com", "Z-NEW", "campaign")
        self.assertTrue(result.ok)
        self.assertEqual(result.outcome, "REACQUIRED")
        self.assertEqual(result.record["actor"], "Z-NEW")
        self.assertEqual(result.record["generation"], 2)

    def test_sent_is_terminal_and_blocks_future_claims(self):
        self.fence.claim("alice@example.com", "Z-A", "campaign")
        sent = self.fence.transition("alice@example.com", "Z-A", SENT)
        self.assertTrue(sent.ok)
        later = self.fence.claim("alice@example.com", "Z-B", "other-campaign")
        self.assertFalse(later.ok)
        self.assertEqual(later.record["state"], SENT)
        release = self.fence.transition("alice@example.com", "Z-A", RELEASED)
        self.assertFalse(release.ok)
        self.assertEqual(release.outcome, SENT)

    def test_non_owner_cannot_mark_sent_or_release(self):
        self.fence.claim("alice@example.com", "Z-A", "campaign")
        for state in (SENT, RELEASED):
            result = self.fence.transition("alice@example.com", "Z-B", state)
            self.assertFalse(result.ok)
            self.assertEqual(result.outcome, "NOT_OWNER")

    def test_release_allows_reacquire(self):
        self.fence.claim("alice@example.com", "Z-A", "campaign")
        released = self.fence.transition("alice@example.com", "Z-A", RELEASED)
        self.assertTrue(released.ok)
        second = self.fence.claim("alice@example.com", "Z-B", "campaign")
        self.assertTrue(second.ok)
        self.assertEqual(second.outcome, "REACQUIRED")
        self.assertEqual(second.record["actor"], "Z-B")

    def test_reacquire_update_race_loser_does_not_overwrite_winner(self):
        old_now = NOW - dt.timedelta(hours=2)
        LeadFence(self.client, now_fn=lambda: old_now).claim("alice@example.com", "Z-OLD", "campaign", ttl_minutes=1)
        winner = self.fence._new_active("alice@example.com", "Z-WINNER", "campaign", 30, "test", previous={"generation": 1})
        self.client.conflict_on_update = True
        self.client.update_conflict_payload = winner
        result = self.fence.claim("alice@example.com", "Z-LOSER", "campaign")
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome, "COLLISION")
        self.assertEqual(result.record["actor"], "Z-WINNER")

    def test_status_reports_unclaimed_expired_and_sent(self):
        self.assertEqual(self.fence.status("nobody@example.com").outcome, "UNCLAIMED")
        old_now = NOW - dt.timedelta(hours=2)
        LeadFence(self.client, now_fn=lambda: old_now).claim("alice@example.com", "Z-A", "campaign", ttl_minutes=1)
        self.assertEqual(self.fence.status("alice@example.com").outcome, "EXPIRED")
        reacquired = self.fence.claim("alice@example.com", "Z-A", "campaign")
        self.assertTrue(reacquired.ok)
        self.fence.transition("alice@example.com", "Z-A", SENT)
        self.assertEqual(self.fence.status("alice@example.com").outcome, SENT)


if __name__ == "__main__":
    unittest.main()
