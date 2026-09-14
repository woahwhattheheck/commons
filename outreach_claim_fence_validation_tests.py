"""Hardening tests for the outreach claim fence."""

import hashlib
import io
import json
import os
import tempfile
from contextlib import redirect_stderr, redirect_stdout

import outreach_claim_fence as ocf
from outreach_claim_fence_test_support import ClaimFenceTestCase


class ClaimFenceValidationTests(ClaimFenceTestCase):
    def test_same_message_digest_with_changed_metadata_fails_closed(self):
        self.acquire()
        digest = ocf.digest_message_bytes(b"same outbound bytes")
        self.store.mark_contacted(
            target_kind="email",
            contact=self.kw["contact"],
            agent_id=self.kw["agent_id"],
            operation_id=self.kw["operation_id"],
            message_digest=digest,
            channel="email",
            compensation_path="$500 paid repair",
            cooldown_seconds=600,
        )
        with self.assertRaises(ocf.ValidationError):
            self.store.mark_contacted(
                target_kind="email",
                contact=self.kw["contact"],
                agent_id=self.kw["agent_id"],
                operation_id=self.kw["operation_id"],
                message_digest=digest,
                channel="slack",
                compensation_path="$500 paid repair",
                cooldown_seconds=600,
            )

    def test_release_replay_is_idempotent_after_release(self):
        self.acquire()
        kwargs = dict(
            target_kind="email",
            contact=self.kw["contact"],
            agent_id=self.kw["agent_id"],
            operation_id=self.kw["operation_id"],
            reason="Owner reassigned the lead",
        )
        first = self.store.release(**kwargs)
        second = self.store.release(**kwargs)
        self.assertEqual(second.action, "ALREADY_RECORDED")
        self.assertEqual(second.revision, first.revision)

    def test_compensation_path_requires_a_concrete_paid_signal(self):
        self.acquire()
        digest = ocf.digest_message_bytes(b"message")
        for weak in ("future opportunity", "maybe later", "exposure", "hope for payoff"):
            with self.subTest(weak=weak):
                with self.assertRaises(ocf.ValidationError):
                    self.store.mark_contacted(
                        target_kind="email",
                        contact=self.kw["contact"],
                        agent_id=self.kw["agent_id"],
                        operation_id=self.kw["operation_id"],
                        message_digest=digest,
                        channel="email",
                        compensation_path=weak,
                        cooldown_seconds=600,
                    )

    def test_corrupt_base64_fails_closed(self):
        self.acquire()
        original_request = self.transport.request

        def corrupt(method, url, headers, body=None):
            response = original_request(method, url, headers, body)
            if method == "GET" and response.status == 200:
                payload = json.loads(response.body.decode())
                payload["content"] = "***not-base64***"
                return ocf.HttpResponse(200, response.headers, json.dumps(payload).encode())
            return response

        self.transport.request = corrupt
        with self.assertRaises(ocf.ProtocolError):
            self.store.inspect(target_kind="email", contact=self.kw["contact"])

    def test_unknown_v1_fields_fail_closed(self):
        self.acquire()
        record, _raw, path = self.record_for()
        record["raw_contact"] = "lead@example.com"
        record = ocf._seal_record(record)
        self.transport.inject_record(path, record)
        with self.assertRaises(ocf.ProtocolError):
            self.store.inspect(target_kind="email", contact=self.kw["contact"])

    def test_opportunity_digest_mismatch_fails_closed(self):
        self.acquire()
        record, _raw, path = self.record_for()
        record["opportunity_digest"] = "0" * 64
        record = ocf._seal_record(record)
        self.transport.inject_record(path, record)
        with self.assertRaises(ocf.ProtocolError):
            self.store.inspect(target_kind="email", contact=self.kw["contact"])

    def test_active_history_requires_complete_contact_evidence(self):
        self.acquire()
        record, _raw, path = self.record_for()
        record["contact_count"] = 1
        record = ocf._seal_record(record)
        self.transport.inject_record(path, record)
        with self.assertRaises(ocf.ProtocolError):
            self.store.inspect(target_kind="email", contact=self.kw["contact"])

    def test_stored_contacted_state_requires_complete_evidence(self):
        self.acquire()
        record, _raw, path = self.record_for()
        record.update({"state": "CONTACTED", "contact_count": 1})
        record = ocf._seal_record(record)
        self.transport.inject_record(path, record)
        with self.assertRaises(ocf.ProtocolError):
            self.store.inspect(target_kind="email", contact=self.kw["contact"])

    def test_validation_rejects_weak_and_ambiguous_inputs(self):
        with self.assertRaises(ocf.ValidationError):
            ocf.normalize_target("email", "not-an-email")
        with self.assertRaises(ocf.ValidationError):
            ocf.normalize_target("domain", "localhost")
        with self.assertRaises(ocf.ValidationError):
            self.acquire(lease_seconds=59)
        with self.assertRaises(ocf.ValidationError):
            self.acquire(agent_id="spaces are unsafe")

    def test_record_canonical_digest_survives_roundtrip(self):
        self.acquire()
        record, raw, _ = self.record_for()
        self.assertEqual(record["record_digest"], ocf._record_digest(record))
        self.assertEqual(raw, ocf._canonical_json_bytes(record) + b"\n")

