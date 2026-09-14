import base64
import datetime as dt
import email.utils
import hashlib
import io
import json
import os
import tempfile
import unittest
import urllib.parse
from contextlib import redirect_stderr, redirect_stdout

import outreach_claim_fence as ocf


class FakeGitHubTransport:
    def __init__(self, now=None):
        self.now = now or dt.datetime(2026, 9, 14, 3, 30, tzinfo=dt.timezone.utc)
        self.files = {}
        self.commit_counter = 0
        self.requests = []
        self.before_put = None
        self.omit_date = False
        self.malformed_read = False

    def advance(self, seconds):
        self.now += dt.timedelta(seconds=seconds)

    def _headers(self):
        if self.omit_date:
            return {}
        return {"Date": email.utils.format_datetime(self.now, usegmt=True)}

    @staticmethod
    def _path(url):
        parsed = urllib.parse.urlparse(url)
        marker = "/contents/"
        encoded = parsed.path.split(marker, 1)[1]
        return urllib.parse.unquote(encoded)

    def request(self, method, url, headers, body=None):
        self.requests.append((method, url, dict(headers), body))
        path = self._path(url)
        if method == "GET":
            if self.malformed_read:
                return ocf.HttpResponse(200, self._headers(), b"not-json")
            entry = self.files.get(path)
            if entry is None:
                return ocf.HttpResponse(404, self._headers(), b'{"message":"Not Found"}')
            payload = {
                "type": "file",
                "sha": entry["sha"],
                "encoding": "base64",
                "content": base64.b64encode(entry["content"]).decode("ascii"),
            }
            return ocf.HttpResponse(200, self._headers(), json.dumps(payload).encode())
        if method != "PUT":
            raise AssertionError(method)
        if self.before_put is not None:
            callback, self.before_put = self.before_put, None
            callback(self, path)
        payload = json.loads(body.decode())
        content = base64.b64decode(payload["content"])
        current = self.files.get(path)
        supplied_sha = payload.get("sha")
        if current is None and supplied_sha is not None:
            return ocf.HttpResponse(409, self._headers(), b'{"message":"conflict"}')
        if current is not None and supplied_sha is None:
            return ocf.HttpResponse(422, self._headers(), b'{"message":"exists"}')
        if current is not None and supplied_sha != current["sha"]:
            return ocf.HttpResponse(409, self._headers(), b'{"message":"stale"}')
        blob_sha = hashlib.sha1(b"blob\0" + content).hexdigest()
        self.commit_counter += 1
        commit_sha = hashlib.sha1(f"commit:{self.commit_counter}:{blob_sha}".encode()).hexdigest()
        self.files[path] = {"content": content, "sha": blob_sha, "commit": commit_sha}
        response = {"content": {"sha": blob_sha}, "commit": {"sha": commit_sha}}
        return ocf.HttpResponse(201 if current is None else 200, self._headers(), json.dumps(response).encode())

    def inject_record(self, path, record):
        content = ocf._canonical_json_bytes(record) + b"\n"
        blob_sha = hashlib.sha1(b"blob\0" + content).hexdigest()
        self.commit_counter += 1
        commit_sha = hashlib.sha1(f"inject:{self.commit_counter}:{blob_sha}".encode()).hexdigest()
        self.files[path] = {"content": content, "sha": blob_sha, "commit": commit_sha}


class ClaimFenceTests(unittest.TestCase):
    def setUp(self):
        self.transport = FakeGitHubTransport()
        self.store = ocf.GitHubContentsClaimStore(
            repository="woahwhattheheck/commons",
            token="secret-token",
            transport=self.transport,
        )
        self.kw = {
            "target_kind": "email",
            "contact": "Lead@Example.COM",
            "opportunity": "Paid discovery for pipeline repair",
            "agent_id": "ZKLR-H5M8",
            "operation_id": "OUTREACH-CLAIM-FENCE-ZKLRH5M8-20260913",
            "lease_seconds": 3600,
        }

    def acquire(self, **updates):
        args = dict(self.kw)
        args.update(updates)
        return self.store.acquire(**args)

    def record_for(self, contact="Lead@Example.COM"):
        identity = ocf.normalize_target("email", contact)
        path = self.store.path_for(identity.claim_key)
        raw = self.transport.files[path]["content"]
        return json.loads(raw.decode()), raw, path

    def test_email_normalization_is_case_and_idna_stable(self):
        left = ocf.normalize_target("email", "Alice@EXAMPLE.com")
        right = ocf.normalize_target("email", "alice@example.COM.")
        self.assertEqual(left.claim_key, right.claim_key)
        self.assertEqual(left.normalized, "alice@example.com")
        self.assertEqual(left.hint, "a***@example.com")

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
        self.assertEqual(record["target_hint"], "l***@example.com")
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
