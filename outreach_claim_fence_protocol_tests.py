"""Concurrency, ownership, lifecycle, and privacy tests."""

import datetime as dt
import hashlib
import json

import outreach_claim_fence as ocf
from outreach_claim_fence_test_support import ClaimFenceTestCase


class ClaimFenceProtocolTests(ClaimFenceTestCase):
    def test_email_normalization_is_case_and_idna_stable(self):
        left = ocf.normalize_target("email", "Alice@EXAMPLE.com")
        right = ocf.normalize_target("email", "alice@example.COM.")
        self.assertEqual(left.claim_key, right.claim_key)
        self.assertEqual(left.normalized, "alice@example.com")
        self.assertEqual(left.hint, "a***@e***.c***")

    def test_domain_target_is_never_persisted_verbatim(self):
        receipt = self.store.acquire(
            target_kind="domain",
            contact="Sensitive-Lead.Example",
            opportunity="Paid domain migration discovery",
            agent_id=self.kw["agent_id"],
            operation_id=self.kw["operation_id"],
            lease_seconds=3600,
        )
        path = self.store.path_for(receipt.claim_key)
        raw = self.transport.files[path]["content"]
        record = json.loads(raw.decode())
        self.assertEqual(record["target_hint"], "s***.e***")
        self.assertNotIn(b"sensitive-lead.example", raw.lower())

    def test_contact_scope_blocks_campaign_aliases(self):
        first = self.acquire()
        self.assertEqual(first.action, "ACQUIRED")
        with self.assertRaises(ocf.ClaimConflict):
            self.acquire(
                opportunity="Different campaign name",
                agent_id="another-agent",
                operation_id="another-operation",
            )

    def test_acquire_writes_no_raw_email_or_token(self):
        receipt = self.acquire()
        record, raw, path = self.record_for()
        self.assertEqual(record["state"], "ACTIVE")
        self.assertEqual(record["target_hint"], "l***@e***.c***")
        self.assertNotIn(b"lead@example.com", raw.lower())
        self.assertNotIn(b"secret-token", raw)
        self.assertEqual(receipt.path, path)
        self.assertTrue(ocf._HEX_64.fullmatch(record["record_digest"]))

    def test_authorization_header_is_sent_but_never_persisted(self):
        self.acquire()
        first_headers = self.transport.requests[0][2]
        self.assertEqual(first_headers["Authorization"], "Bearer secret-token")
        _record, raw, _path = self.record_for()
        self.assertNotIn(b"Bearer", raw)

    def test_repeated_acquire_by_same_operation_is_idempotent(self):
        first = self.acquire()
        writes_before = sum(method == "PUT" for method, *_ in self.transport.requests)
        second = self.acquire()
        writes_after = sum(method == "PUT" for method, *_ in self.transport.requests)
        self.assertEqual(second.action, "ALREADY_OWNED")
        self.assertEqual(second.record_digest, first.record_digest)
        self.assertEqual(writes_before, writes_after)

    def test_live_competitor_receives_safe_conflict(self):
        self.acquire()
        with self.assertRaises(ocf.ClaimConflict) as caught:
            self.acquire(agent_id="Z-OTHER", operation_id="OTHER-OP")
        self.assertEqual(caught.exception.details["agent_id"], "ZKLR-H5M8")
        self.assertNotIn("Lead@", json.dumps(caught.exception.safe_payload()))

    def test_simultaneous_create_has_one_winner(self):
        identity = ocf.normalize_target("email", self.kw["contact"])
        path = self.store.path_for(identity.claim_key)

        def competing_write(transport, actual_path):
            self.assertEqual(actual_path, path)
            now = transport.now
            record = ocf._seal_record(
                {
                    "schema": ocf.SCHEMA,
                    "claim_key": identity.claim_key,
                    "target_kind": "email",
                    "target_hint": identity.hint,
                    "state": "ACTIVE",
                    "revision": 1,
                    "agent_id": "race-winner",
                    "operation_id": "race-op",
                    "opportunity_label": "Paid competing bid",
                    "opportunity_digest": hashlib.sha256(b"paid competing bid").hexdigest(),
                    "claimed_at": ocf._format_timestamp(now),
                    "last_action_at": ocf._format_timestamp(now),
                    "lease_expires_at": ocf._format_timestamp(now + dt.timedelta(hours=1)),
                    "prior_record_digest": None,
                    "record_digest": "",
                    "contact_count": 0,
                    "last_contacted_at": None,
                    "last_message_digest": None,
                    "last_channel": None,
                    "compensation_path": None,
                    "release_reason": None,
                }
            )
            transport.inject_record(path, record)

        self.transport.before_put = competing_write
        with self.assertRaises(ocf.ClaimConflict) as caught:
            self.acquire()
        self.assertEqual(caught.exception.details["agent_id"], "race-winner")
        record, _raw, _ = self.record_for()
        self.assertEqual(record["agent_id"], "race-winner")

    def test_expired_claim_can_be_taken_over_with_digest_link(self):
        first = self.acquire(lease_seconds=60)
        self.transport.advance(61)
        second = self.acquire(agent_id="Z-NEW", operation_id="NEW-OP")
        record, _raw, _ = self.record_for()
        self.assertEqual(second.action, "ACQUIRED")
        self.assertEqual(record["revision"], 2)
        self.assertEqual(record["prior_record_digest"], first.record_digest)
        self.assertEqual(record["agent_id"], "Z-NEW")

    def test_stale_takeover_loses_to_intervening_owner(self):
        self.acquire(lease_seconds=60)
        self.transport.advance(61)
        identity = ocf.normalize_target("email", self.kw["contact"])
        path = self.store.path_for(identity.claim_key)

        def other_takeover(transport, actual_path):
            self.assertEqual(actual_path, path)
            current = json.loads(transport.files[path]["content"].decode())
            now = transport.now
            replacement = dict(current)
            replacement.update(
                {
                    "revision": current["revision"] + 1,
                    "prior_record_digest": current["record_digest"],
                    "agent_id": "intervening-owner",
                    "operation_id": "intervening-op",
                    "opportunity_label": "Paid emergency repair",
                    "opportunity_digest": hashlib.sha256(b"paid emergency repair").hexdigest(),
                    "claimed_at": ocf._format_timestamp(now),
                    "last_action_at": ocf._format_timestamp(now),
                    "lease_expires_at": ocf._format_timestamp(now + dt.timedelta(hours=1)),
                    "state": "ACTIVE",
                    "contact_count": 0,
                    "last_contacted_at": None,
                    "last_message_digest": None,
                    "last_channel": None,
                    "compensation_path": None,
                    "release_reason": None,
                }
            )
            replacement = ocf._seal_record(replacement)
            transport.inject_record(path, replacement)

        self.transport.before_put = other_takeover
        with self.assertRaises(ocf.ClaimConflict) as caught:
            self.acquire(agent_id="would-lose", operation_id="would-lose-op")
        self.assertEqual(caught.exception.details["agent_id"], "intervening-owner")

    def test_renew_requires_exact_owner_and_live_lease(self):
        self.acquire(lease_seconds=60)
        with self.assertRaises(ocf.OwnershipError):
            self.store.renew(
                target_kind="email",
                contact=self.kw["contact"],
                agent_id="other",
                operation_id=self.kw["operation_id"],
                lease_seconds=3600,
            )
        self.transport.advance(61)
        with self.assertRaises(ocf.OwnershipError):
            self.store.renew(
                target_kind="email",
                contact=self.kw["contact"],
                agent_id=self.kw["agent_id"],
                operation_id=self.kw["operation_id"],
                lease_seconds=3600,
            )

    def test_mark_contacted_is_digest_only_and_requires_paid_path(self):
        self.acquire()
        body = b"We found and fixed the defect. Bounty requested."
        digest = ocf.digest_message_bytes(body)
        with self.assertRaises(ocf.ValidationError):
            self.store.mark_contacted(
                target_kind="email",
                contact=self.kw["contact"],
                agent_id=self.kw["agent_id"],
                operation_id=self.kw["operation_id"],
                message_digest=digest,
                channel="email",
                compensation_path="free",
                cooldown_seconds=600,
            )
        receipt = self.store.mark_contacted(
            target_kind="email",
            contact=self.kw["contact"],
            agent_id=self.kw["agent_id"],
            operation_id=self.kw["operation_id"],
            message_digest=digest,
            channel="email",
            compensation_path="$2,500 paid discovery proposal",
            cooldown_seconds=600,
        )
        record, raw, _ = self.record_for()
        self.assertEqual(receipt.state, "CONTACTED")
        self.assertEqual(record["last_message_digest"], digest)
        self.assertEqual(record["compensation_path"], "$2,500 paid discovery proposal")
        self.assertNotIn(body, raw)
        self.assertEqual(record["contact_count"], 1)

    def test_contacted_replay_is_idempotent(self):
        self.acquire()
        digest = ocf.digest_message_bytes(b"same message")
        kwargs = dict(
            target_kind="email",
            contact=self.kw["contact"],
            agent_id=self.kw["agent_id"],
            operation_id=self.kw["operation_id"],
            message_digest=digest,
            channel="email",
            compensation_path="$500 implementation offer",
            cooldown_seconds=600,
        )
        first = self.store.mark_contacted(**kwargs)
        writes_before = sum(method == "PUT" for method, *_ in self.transport.requests)
        second = self.store.mark_contacted(**kwargs)
        writes_after = sum(method == "PUT" for method, *_ in self.transport.requests)
        self.assertEqual(first.revision, second.revision)
        self.assertEqual(second.action, "ALREADY_RECORDED")
        self.assertEqual(writes_before, writes_after)

    def test_contact_cooldown_blocks_then_allows_takeover(self):
        self.acquire()
        self.store.mark_contacted(
            target_kind="email",
            contact=self.kw["contact"],
            agent_id=self.kw["agent_id"],
            operation_id=self.kw["operation_id"],
            message_digest=ocf.digest_message_bytes(b"paid pitch"),
            channel="email",
            compensation_path="$1,000 fixed-scope implementation",
            cooldown_seconds=600,
        )
        with self.assertRaises(ocf.ClaimConflict):
            self.acquire(agent_id="other", operation_id="other-op")
        self.transport.advance(601)
        takeover = self.acquire(agent_id="other", operation_id="other-op")
        self.assertEqual(takeover.state, "ACTIVE")
        record, _raw, _ = self.record_for()
        self.assertEqual(record["revision"], 3)
        self.assertEqual(record["contact_count"], 1)
