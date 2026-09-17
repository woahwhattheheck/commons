import copy
import hashlib
import unittest

from revenue.outbound_collision_guard import (
    AUTHORITY, GuardError, acquire, ambiguous_hold, begin_send,
    intent_fingerprint, observe_send, release_unsent, verify,
)

NOW = "2026-09-17T03:15:00Z"
LATER = "2026-09-17T03:16:00Z"
INTENT = {
    "counterparty_key": "example.com",
    "route_key": "email:sales@example.com",
    "thread_key": "gmail:abc123",
    "purpose_key": "paid-workshare:freight-qa",
}
A = {"claimant_id": "astra-z", "session_id": "chat-11"}
B = {"claimant_id": "fable-5.1", "session_id": "seat-2"}


def muse(claimant=A, fp=None, expires="2026-09-17T03:25:00Z", generation=1):
    return {
        "receipt_id": "slack:d0c1u7tuzec:1789615000.000001",
        "intent_fingerprint": fp or intent_fingerprint(INTENT),
        "selected_claimant_id": claimant["claimant_id"],
        "selected_session_id": claimant["session_id"],
        "lease_generation": generation,
        "arbitrated_at": "2026-09-17T03:14:59Z",
        "expires_at": expires,
    }


class GuardTests(unittest.TestCase):
    def waiting(self):
        return acquire(intent=INTENT, claimant=A, now=NOW, ttl_s=600)

    def ready(self):
        return acquire(intent=INTENT, claimant=A, now=NOW, ttl_s=600, muse=muse())

    def test_no_muse_waits(self):
        out = self.waiting()
        self.assertEqual(out["state"], "WAIT_MUSE")
        self.assertEqual(out["authority"], AUTHORITY)
        self.assertTrue(verify(out))

    def test_exact_muse_ready(self):
        out = self.ready()
        self.assertEqual(out["state"], "READY_SINGLE_WRITER")
        self.assertTrue(verify(out))

    def test_live_other_claimant_yields_before_muse(self):
        existing = self.waiting()["lease"]
        out = acquire(intent=INTENT, claimant=B, now=LATER, ttl_s=600, existing=existing, muse=muse(B))
        self.assertEqual(out["state"], "YIELD_EXISTING")

    def test_same_claimant_reuses_generation(self):
        old = self.waiting()["lease"]
        out = acquire(intent=INTENT, claimant=A, now=LATER, ttl_s=600, existing=old, muse=muse())
        self.assertEqual(out["lease"]["generation"], 1)
        self.assertEqual(out["state"], "READY_SINGLE_WRITER")

    def test_expired_claim_rotates_generation(self):
        old = self.waiting()["lease"]
        out = acquire(
            intent=INTENT, claimant=B, now="2026-09-17T03:30:00Z", ttl_s=600,
            existing=old, muse=muse(B, expires="2026-09-17T03:40:00Z", generation=2),
        )
        self.assertEqual(out["lease"]["generation"], 2)
        self.assertEqual(out["state"], "READY_SINGLE_WRITER")

    def test_yield_preserves_owner_lease_state(self):
        old = self.waiting()["lease"]
        out = acquire(intent=INTENT, claimant=B, now=LATER, ttl_s=600, existing=old, muse=muse(B))
        self.assertEqual(out["state"], "YIELD_EXISTING")
        self.assertEqual(out["lease"]["state"], old["state"])
        self.assertEqual(out["lease"]["claimant"], A)

    def test_stale_muse_generation_replay_fails_closed(self):
        old = self.waiting()["lease"]
        out = acquire(
            intent=INTENT, claimant=A, now="2026-09-17T03:30:00Z", ttl_s=600,
            existing=old, muse=muse(expires="2026-09-17T03:40:00Z", generation=1),
        )
        self.assertEqual(out["lease"]["generation"], 2)
        self.assertEqual(out["state"], "WAIT_MUSE")

    def test_muse_wrong_claimant_fails_closed(self):
        out = acquire(intent=INTENT, claimant=A, now=NOW, ttl_s=600, muse=muse(B))
        self.assertEqual(out["state"], "WAIT_MUSE")

    def test_muse_wrong_intent_fails_closed(self):
        bad = muse()
        bad["intent_fingerprint"] = "0" * 64
        out = acquire(intent=INTENT, claimant=A, now=NOW, ttl_s=600, muse=bad)
        self.assertEqual(out["state"], "WAIT_MUSE")

    def test_stale_muse_waits(self):
        out = acquire(
            intent=INTENT, claimant=A, now=NOW, ttl_s=600,
            muse=muse(expires="2026-09-17T03:14:59Z"),
        )
        self.assertEqual(out["state"], "WAIT_MUSE")

    def test_lease_capped_by_muse_expiry(self):
        out = acquire(
            intent=INTENT, claimant=A, now=NOW, ttl_s=600,
            muse=muse(expires="2026-09-17T03:17:00Z"),
        )
        self.assertEqual(out["lease"]["expires_at"], "2026-09-17T03:17:00Z")

    def test_attempt_is_deterministic(self):
        ready = self.ready()["lease"]
        body = hashlib.sha256(b"hello").hexdigest()
        a = begin_send(lease=ready, body_sha256=body, provider="gmail", now=LATER)
        b = begin_send(lease=a["lease"], body_sha256=body, provider="gmail", now=LATER)
        self.assertEqual(a["lease"]["attempt"], b["lease"]["attempt"])
        self.assertTrue(verify(b))

    def test_changed_body_retry_rejected(self):
        ready = self.ready()["lease"]
        a = begin_send(lease=ready, body_sha256="1" * 64, provider="gmail", now=LATER)
        with self.assertRaises(GuardError):
            begin_send(lease=a["lease"], body_sha256="2" * 64, provider="gmail", now=LATER)

    def test_changed_provider_retry_rejected(self):
        ready = self.ready()["lease"]
        a = begin_send(lease=ready, body_sha256="1" * 64, provider="gmail", now=LATER)
        with self.assertRaises(GuardError):
            begin_send(lease=a["lease"], body_sha256="1" * 64, provider="slack", now=LATER)

    def test_unknown_result_preserves_attempt(self):
        a = begin_send(lease=self.ready()["lease"], body_sha256="1" * 64, provider="gmail", now=LATER)
        rid = a["lease"]["attempt"]["attempt_id"]
        out = observe_send(
            lease=a["lease"], attempt_id=rid, provider_status="UNKNOWN",
            provider_message_id=None, now="2026-09-17T03:16:10Z",
        )
        self.assertEqual(out["state"], "READY_SINGLE_WRITER")
        self.assertEqual(out["lease"]["attempt"]["attempt_id"], rid)

    def test_unknown_then_sent_same_attempt(self):
        a = begin_send(lease=self.ready()["lease"], body_sha256="1" * 64, provider="gmail", now=LATER)
        rid = a["lease"]["attempt"]["attempt_id"]
        unknown = observe_send(
            lease=a["lease"], attempt_id=rid, provider_status="UNKNOWN",
            provider_message_id=None, now="2026-09-17T03:16:10Z",
        )
        sent = observe_send(
            lease=unknown["lease"], attempt_id=rid, provider_status="SENT",
            provider_message_id="gmail:msg-after-reconcile", now="2026-09-17T03:26:10Z",
        )
        self.assertEqual(sent["state"], "SENT_TERMINAL")
        self.assertEqual(sent["lease"]["terminal_result"]["attempt_id"], rid)

    def test_send_observation_after_lease_expiry_still_terminalizes(self):
        ready = acquire(
            intent=INTENT, claimant=A, now=NOW, ttl_s=60,
            muse=muse(expires="2026-09-17T03:16:30Z"),
        )
        a = begin_send(
            lease=ready["lease"], body_sha256="1" * 64, provider="gmail",
            now="2026-09-17T03:15:59Z",
        )
        sent = observe_send(
            lease=a["lease"], attempt_id=a["lease"]["attempt"]["attempt_id"],
            provider_status="SENT", provider_message_id="gmail:late-receipt",
            now="2026-09-17T03:17:00Z",
        )
        self.assertEqual(sent["state"], "SENT_TERMINAL")

    def test_sent_is_terminal(self):
        a = begin_send(lease=self.ready()["lease"], body_sha256="1" * 64, provider="gmail", now=LATER)
        rid = a["lease"]["attempt"]["attempt_id"]
        sent = observe_send(
            lease=a["lease"], attempt_id=rid, provider_status="SENT",
            provider_message_id="gmail:msg-1", now="2026-09-17T03:16:10Z",
        )
        self.assertEqual(sent["state"], "SENT_TERMINAL")
        again = acquire(
            intent=INTENT, claimant=B, now="2026-09-17T03:30:00Z", ttl_s=600,
            existing=sent["lease"], muse=muse(B, expires="2026-09-17T03:40:00Z"),
        )
        self.assertEqual(again["state"], "SENT_TERMINAL")

    def test_wrong_attempt_result_rejected(self):
        a = begin_send(lease=self.ready()["lease"], body_sha256="1" * 64, provider="gmail", now=LATER)
        with self.assertRaises(GuardError):
            observe_send(
                lease=a["lease"], attempt_id="nope", provider_status="SENT",
                provider_message_id="gmail:msg", now="2026-09-17T03:16:10Z",
            )

    def test_unknown_cannot_claim_message_id(self):
        a = begin_send(lease=self.ready()["lease"], body_sha256="1" * 64, provider="gmail", now=LATER)
        with self.assertRaises(GuardError):
            observe_send(
                lease=a["lease"], attempt_id=a["lease"]["attempt"]["attempt_id"],
                provider_status="UNKNOWN", provider_message_id="maybe",
                now="2026-09-17T03:16:10Z",
            )

    def test_release_unsent(self):
        out = release_unsent(lease=self.waiting()["lease"], claimant=A, now=LATER)
        self.assertEqual(out["state"], "RELEASED_UNSENT")
        self.assertTrue(verify(out))

    def test_release_other_claimant_rejected(self):
        with self.assertRaises(GuardError):
            release_unsent(lease=self.waiting()["lease"], claimant=B, now=LATER)

    def test_release_with_attempt_rejected(self):
        a = begin_send(lease=self.ready()["lease"], body_sha256="1" * 64, provider="gmail", now=LATER)
        with self.assertRaises(GuardError):
            release_unsent(lease=a["lease"], claimant=A, now="2026-09-17T03:16:10Z")

    def test_ambiguous_hold(self):
        out = ambiguous_hold(
            raw_counterparty="Acme / forwarded intro", raw_route="unknown alias",
            purpose_key="paid-workshare:qa",
        )
        self.assertEqual(out["state"], "HOLD_AMBIGUOUS_COUNTERPARTY")
        self.assertEqual(out["authority"], AUTHORITY)

    def test_generic_counterparty_rejected(self):
        bad = dict(INTENT)
        bad["counterparty_key"] = "unknown"
        with self.assertRaises(GuardError):
            acquire(intent=bad, claimant=A, now=NOW, ttl_s=600)

    def test_ambiguous_thread_rejected(self):
        bad = dict(INTENT)
        bad["thread_key"] = "unknown"
        with self.assertRaises(GuardError):
            acquire(intent=bad, claimant=A, now=NOW, ttl_s=600)

    def test_extra_intent_key_rejected(self):
        bad = dict(INTENT)
        bad["send"] = True
        with self.assertRaises(GuardError):
            acquire(intent=bad, claimant=A, now=NOW, ttl_s=600)

    def test_bool_ttl_rejected(self):
        with self.assertRaises(GuardError):
            acquire(intent=INTENT, claimant=A, now=NOW, ttl_s=True)

    def test_noncanonical_timestamp_rejected(self):
        with self.assertRaises(GuardError):
            acquire(intent=INTENT, claimant=A, now="2026-09-17T03:15:00+00:00", ttl_s=600)

    def test_receipt_tamper_detected(self):
        out = self.ready()
        bad = copy.deepcopy(out)
        bad["reason"] = "different"
        with self.assertRaises(GuardError):
            verify(bad)

    def test_authority_escalation_detected(self):
        out = self.ready()
        bad = copy.deepcopy(out)
        bad["authority"]["external_send"] = True
        with self.assertRaises(GuardError):
            verify(bad)

    def test_lease_fingerprint_tamper_detected(self):
        out = self.ready()
        bad = copy.deepcopy(out)
        bad["lease"]["fingerprint"] = "0" * 64
        with self.assertRaises(GuardError):
            verify(bad)

    def test_sent_result_tamper_detected(self):
        a = begin_send(lease=self.ready()["lease"], body_sha256="1" * 64, provider="gmail", now=LATER)
        sent = observe_send(
            lease=a["lease"], attempt_id=a["lease"]["attempt"]["attempt_id"],
            provider_status="SENT", provider_message_id="gmail:msg",
            now="2026-09-17T03:16:10Z",
        )
        bad = copy.deepcopy(sent)
        bad["lease"]["terminal_result"]["provider_message_id"] = "gmail:other"
        with self.assertRaises(GuardError):
            verify(bad)

    def test_normalization_collides_case_aliases(self):
        i2 = dict(INTENT)
        i2["counterparty_key"] = "EXAMPLE.COM"
        self.assertEqual(intent_fingerprint(INTENT), intent_fingerprint(i2))

    def test_reply_and_new_thread_are_distinct(self):
        i2 = dict(INTENT)
        i2["thread_key"] = "new:paid-workshare:freight-qa"
        self.assertNotEqual(intent_fingerprint(INTENT), intent_fingerprint(i2))


if __name__ == "__main__":
    unittest.main()
