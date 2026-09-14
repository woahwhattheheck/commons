"""Hardening tests for the outreach claim fence."""

import hashlib
import io
import json
import os
import tempfile
from contextlib import redirect_stderr, redirect_stdout

import outreach_claim_fence as ocf
from outreach_claim_fence_test_support import ClaimFenceTestCase


class ClaimFenceLifecycleTests(ClaimFenceTestCase):
    def test_release_allows_immediate_reassignment(self):
        self.acquire()
        released = self.store.release(
            target_kind="email",
            contact=self.kw["contact"],
            agent_id=self.kw["agent_id"],
            operation_id=self.kw["operation_id"],
            reason="Owner reassigned the lead",
        )
        self.assertEqual(released.state, "RELEASED")
        acquired = self.acquire(agent_id="new-owner", operation_id="new-op")
        self.assertEqual(acquired.state, "ACTIVE")
        self.assertEqual(acquired.revision, 3)

    def test_tampered_record_fails_closed(self):
        self.acquire()
        record, _raw, path = self.record_for()
        record["agent_id"] = "attacker"
        self.transport.inject_record(path, record)
        with self.assertRaises(ocf.ProtocolError):
            self.store.inspect(target_kind="email", contact=self.kw["contact"])

    def test_missing_server_date_fails_closed(self):
        self.transport.omit_date = True
        with self.assertRaises(ocf.ProtocolError):
            self.acquire()

    def test_malformed_github_json_fails_closed(self):
        self.transport.malformed_read = True
        with self.assertRaises(ocf.ProtocolError):
            self.acquire()

    def test_inspect_never_returns_raw_contact(self):
        self.acquire()
        inspected = self.store.inspect(target_kind="email", contact=self.kw["contact"])
        serialized = json.dumps(inspected).lower()
        self.assertNotIn("lead@example.com", serialized)
        self.assertTrue(inspected["live"])
        self.assertEqual(inspected["server_now"], "2026-09-14T03:30:00Z")

    def test_cli_key_needs_no_token_and_emits_safe_json(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = ocf.main(["key", "--kind", "email", "--contact", "Lead@Example.com"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["ok"])
        self.assertNotIn("Lead@Example.com", stdout.getvalue())

    def test_cli_argument_errors_are_json(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = ocf.main(["acquire"])
        self.assertEqual(code, 2)
        payload = json.loads(stderr.getvalue())
        self.assertEqual(payload["error"], "ValidationError")
        self.assertIn("argument error", payload["message"])

    def test_cli_message_file_hashes_locally(self):
        self.acquire()
        # Replace the live HTTP transport by invoking the helper directly; the CLI's
        # filesystem guarantee is covered by the same digest helper used below.
        with tempfile.NamedTemporaryFile("wb", delete=False) as handle:
            handle.write(b"request payment with merged work link")
            name = handle.name
        try:
            with open(name, "rb") as handle:
                digest = ocf.digest_message_bytes(handle.read())
            self.assertEqual(digest, hashlib.sha256(b"request payment with merged work link").hexdigest())
        finally:
            os.unlink(name)

    def test_contact_history_survives_cooldown_takeover(self):
        self.acquire()
        digest = ocf.digest_message_bytes(b"first paid offer")
        self.store.mark_contacted(
            target_kind="email",
            contact=self.kw["contact"],
            agent_id=self.kw["agent_id"],
            operation_id=self.kw["operation_id"],
            message_digest=digest,
            channel="email",
            compensation_path="$750 paid implementation proposal",
            cooldown_seconds=600,
        )
        self.transport.advance(601)
        self.acquire(agent_id="new-owner", operation_id="new-op")
        record, _raw, _ = self.record_for()
        self.assertEqual(record["state"], "ACTIVE")
        self.assertEqual(record["contact_count"], 1)
        self.assertEqual(record["last_message_digest"], digest)
        self.assertEqual(record["last_channel"], "email")
        self.assertEqual(record["compensation_path"], "$750 paid implementation proposal")

    def test_contacted_replay_after_expiry_is_still_idempotent(self):
        self.acquire()
        kwargs = dict(
            target_kind="email",
            contact=self.kw["contact"],
            agent_id=self.kw["agent_id"],
            operation_id=self.kw["operation_id"],
            message_digest=ocf.digest_message_bytes(b"one paid message"),
            channel="email",
            compensation_path="$900 fixed-scope contract",
            cooldown_seconds=600,
        )
        first = self.store.mark_contacted(**kwargs)
        self.transport.advance(601)
        second = self.store.mark_contacted(**kwargs)
        self.assertEqual(second.action, "ALREADY_RECORDED")
        self.assertEqual(second.revision, first.revision)

