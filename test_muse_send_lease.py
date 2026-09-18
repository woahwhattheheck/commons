from __future__ import annotations

import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from coordination import muse_send_lease as m


class MuseSendLeaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "lease.sqlite3")
        self.identity = dict(
            operation_key="ACME-PAID-WORKSHARE-ZSOL-20260917",
            counterparty="Acme Example",
            route="sales@example.test",
            purpose="paid reconciliation workshare",
        )
        self.session = "zsol-1447:session-a"

    def tearDown(self):
        self.tmp.cleanup()

    def issue(self, *, now=1000, ttl=60, session=None, operation_key=None):
        identity = dict(self.identity)
        if operation_key is not None:
            identity["operation_key"] = operation_key
        return m._issue_at(
            self.db,
            **identity,
            seat="Z-Sol-1447",
            session_nonce=session or self.session,
            ttl_seconds=ttl,
            now_s=now,
        )

    def consume(self, lease, *, now=1001, session=None, **overrides):
        identity = dict(self.identity)
        identity.update(overrides)
        return m._consume_at(
            self.db,
            lease_id=lease["lease_id"],
            **identity,
            session_nonce=session or self.session,
            now_s=now,
        )

    def assert_no_capability(self, value):
        self.assertNotIn("go_token", value)
        self.assertNotIn("go_token_sha256", value)

    def test_selected_lease_is_not_send_authority_until_consume_go(self):
        lease = self.issue()
        self.assertEqual(lease["status"], m.LEASED)
        self.assertEqual(lease["send_gate"], "HOLD_UNTIL_CONSUME_GO")
        self.assert_no_capability(lease)
        for key in (
            "provider_send_independently_verified",
            "buyer_acceptance_authority",
            "contract_authority",
            "payment_authority",
            "cash_authority",
            "revenue_authority",
        ):
            self.assertFalse(lease[key])

        go = self.consume(lease)
        self.assertEqual(go["decision"], "GO")
        self.assertEqual(go["status"], m.CONSUMED)
        self.assertEqual(go["send_gate"], "GO_ONCE")
        self.assertTrue(go["go_token"])
        self.assertNotIn("go_token_sha256", go)

        replay = self.consume(lease, now=1002)
        self.assertEqual(replay["decision"], "HOLD_ALREADY_CONSUMED")
        self.assertEqual(replay["send_gate"], "HOLD")
        self.assert_no_capability(replay)

    def test_wrong_session_and_changed_route_never_get_go(self):
        lease = self.issue()
        wrong = self.consume(lease, session="zsol-1447:session-b")
        self.assertEqual(wrong["decision"], "HOLD_SESSION_MISMATCH")
        self.assert_no_capability(wrong)
        self.assertEqual(m.status(self.db, lease_id=lease["lease_id"])["status"], m.LEASED)
        with self.assertRaisesRegex(m.LeaseError, "route mismatch"):
            self.consume(lease, route="other@example.test")

    def test_duplicate_semantic_key_converges_on_original_session_lease(self):
        first = self.issue(session="session-a")
        second = self.issue(now=1001, session="session-b")
        self.assertEqual(second["decision"], "EXISTING_LEASE")
        self.assertEqual(second["lease_id"], first["lease_id"])
        self.assertEqual(second["selected_session"], "session-a")
        self.assertEqual(second["send_gate"], "HOLD")
        self.assert_no_capability(second)

    def test_duplicate_issue_after_consume_does_not_disclose_capability(self):
        lease = self.issue(session="session-a")
        go = self.consume(lease, session="session-a")
        self.assertIn("go_token", go)
        duplicate = self.issue(now=1002, session="session-b")
        self.assertEqual(duplicate["status"], m.CONSUMED)
        self.assertEqual(duplicate["decision"], "EXISTING_LEASE")
        self.assert_no_capability(duplicate)

    def test_status_during_consumed_state_does_not_disclose_capability(self):
        lease = self.issue()
        self.consume(lease)
        result = m.status(self.db, lease_id=lease["lease_id"])
        self.assertEqual(result["status"], m.CONSUMED)
        self.assert_no_capability(result)
        for event in result["audit"]:
            self.assertNotIn("go_token", event["payload"])
            self.assertNotIn("go_token_sha256", event["payload"])

    def test_two_simultaneous_consumers_receive_exactly_one_go(self):
        lease = self.issue(now=1000, ttl=120)
        barrier = threading.Barrier(3)
        results = []
        errors = []
        lock = threading.Lock()

        def worker():
            try:
                barrier.wait()
                result = m._consume_at(
                    self.db,
                    lease_id=lease["lease_id"],
                    **self.identity,
                    session_nonce=self.session,
                    now_s=1001,
                )
                with lock:
                    results.append(result)
            except Exception as exc:  # pragma: no cover
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(errors, errors)
        self.assertEqual(len(results), 2)
        self.assertEqual(sum(result["decision"] == "GO" for result in results), 1)
        self.assertEqual(sum(result["decision"] == "HOLD_ALREADY_CONSUMED" for result in results), 1)
        self.assertEqual(sum("go_token" in result for result in results), 1)
        for result in results:
            self.assertNotIn("go_token_sha256", result)

    def test_commit_is_exactly_idempotent_and_changed_tuple_fails(self):
        lease = self.issue()
        go = self.consume(lease)
        first = m._commit_at(
            self.db,
            lease_id=lease["lease_id"],
            session_nonce=self.session,
            go_token=go["go_token"],
            provider="gmail",
            provider_message_id="msg-1",
            now_s=1002,
        )
        self.assertEqual(first["status"], m.SENT)
        self.assertEqual(first["decision"], "COMMIT_RECORDED")
        self.assert_no_capability(first)
        second = m._commit_at(
            self.db,
            lease_id=lease["lease_id"],
            session_nonce=self.session,
            go_token=go["go_token"],
            provider="gmail",
            provider_message_id="msg-1",
            now_s=1003,
        )
        self.assertEqual(second["decision"], "COMMIT_ALREADY_RECORDED")
        self.assert_no_capability(second)
        with self.assertRaisesRegex(m.LeaseError, "tuple mismatch"):
            m._commit_at(
                self.db,
                lease_id=lease["lease_id"],
                session_nonce=self.session,
                go_token=go["go_token"],
                provider="gmail",
                provider_message_id="msg-2",
                now_s=1004,
            )

    def test_public_readback_cannot_forge_commit(self):
        lease = self.issue()
        go = self.consume(lease)
        readback = m.status(self.db, lease_id=lease["lease_id"])
        self.assert_no_capability(readback)
        with self.assertRaisesRegex(m.LeaseError, "session/go token mismatch"):
            m._commit_at(
                self.db,
                lease_id=lease["lease_id"],
                session_nonce=readback["selected_session"],
                go_token="forged-from-public-readback",
                provider="gmail",
                provider_message_id="forged-msg",
                now_s=1002,
            )
        committed = m._commit_at(
            self.db,
            lease_id=lease["lease_id"],
            session_nonce=self.session,
            go_token=go["go_token"],
            provider="gmail",
            provider_message_id="real-msg",
            now_s=1002,
        )
        self.assertEqual(committed["status"], m.SENT)

    def test_provider_receipt_cannot_be_reused_across_leases(self):
        first = self.issue(operation_key="GEN-A")
        first_identity = dict(self.identity, operation_key="GEN-A")
        first_go = m._consume_at(
            self.db,
            lease_id=first["lease_id"],
            **first_identity,
            session_nonce=self.session,
            now_s=1001,
        )
        m._commit_at(
            self.db,
            lease_id=first["lease_id"],
            session_nonce=self.session,
            go_token=first_go["go_token"],
            provider="gmail",
            provider_message_id="provider-receipt-1",
            now_s=1002,
        )

        second = self.issue(now=1010, operation_key="GEN-B", session="session-b")
        second_identity = dict(self.identity, operation_key="GEN-B")
        second_go = m._consume_at(
            self.db,
            lease_id=second["lease_id"],
            **second_identity,
            session_nonce="session-b",
            now_s=1011,
        )
        with self.assertRaisesRegex(m.LeaseError, "already bound"):
            m._commit_at(
                self.db,
                lease_id=second["lease_id"],
                session_nonce="session-b",
                go_token=second_go["go_token"],
                provider="gmail",
                provider_message_id="provider-receipt-1",
                now_s=1012,
            )

    def test_consumed_expiry_holds_for_provider_reconciliation(self):
        lease = self.issue(now=1000, ttl=5)
        go = self.consume(lease, now=1001)
        late_commit = m._commit_at(
            self.db,
            lease_id=lease["lease_id"],
            session_nonce=self.session,
            go_token=go["go_token"],
            provider="gmail",
            provider_message_id="late-msg",
            now_s=1006,
        )
        self.assertEqual(late_commit["decision"], "HOLD_NEEDS_RECONCILIATION")
        self.assertEqual(late_commit["status"], m.HOLD_NEEDS_RECONCILIATION)
        self.assertIsNone(late_commit["provider_message_id"])
        self.assert_no_capability(late_commit)

        reconciled = m._reconcile_at(
            self.db,
            lease_id=lease["lease_id"],
            provider_seen=True,
            provider="gmail",
            provider_message_id="late-msg",
            note="authenticated Gmail census located exact SENT message",
            now_s=1007,
        )
        self.assertEqual(reconciled["status"], m.SENT)
        self.assertEqual(reconciled["decision"], "RECONCILED_PROVIDER_SEEN")
        self.assertFalse(reconciled["provider_send_independently_verified"])
        self.assert_no_capability(reconciled)

    def test_consumed_expiry_with_no_provider_observation_stays_hold(self):
        lease = self.issue(now=1000, ttl=2)
        self.consume(lease, now=1001)
        expired = m._expire_at(self.db, lease_id=lease["lease_id"], now_s=1002)
        self.assertEqual(expired["status"], m.HOLD_NEEDS_RECONCILIATION)
        self.assert_no_capability(expired)
        reconciled = m._reconcile_at(
            self.db,
            lease_id=lease["lease_id"],
            provider_seen=False,
            provider=None,
            provider_message_id=None,
            note="provider census found no send receipt",
            now_s=1003,
        )
        self.assertEqual(reconciled["status"], m.HOLD_RECONCILED_NO_SEND)
        self.assertEqual(reconciled["send_gate"], "HOLD_NEW_GENERATION_REQUIRED")
        self.assert_no_capability(reconciled)
        duplicate = self.issue(now=1004, session="new-session")
        self.assertEqual(duplicate["lease_id"], lease["lease_id"])
        self.assertEqual(duplicate["send_gate"], "HOLD")
        self.assert_no_capability(duplicate)

    def test_unconsumed_expiry_does_not_silently_reissue(self):
        lease = self.issue(now=1000, ttl=1)
        expired = m._expire_at(self.db, lease_id=lease["lease_id"], now_s=1001)
        self.assertEqual(expired["status"], m.HOLD_EXPIRED_UNCONSUMED)
        self.assert_no_capability(expired)
        again = self.issue(now=1002, session="different")
        self.assertEqual(again["lease_id"], lease["lease_id"])
        self.assertEqual(again["status"], m.HOLD_EXPIRED_UNCONSUMED)
        self.assert_no_capability(again)

    def test_audit_readback_verifies_hash_chain_and_detects_audit_tamper(self):
        lease = self.issue()
        go = self.consume(lease)
        m._commit_at(
            self.db,
            lease_id=lease["lease_id"],
            session_nonce=self.session,
            go_token=go["go_token"],
            provider="gmail",
            provider_message_id="msg-chain",
            now_s=1002,
        )
        good = m.status(self.db, lease_id=lease["lease_id"])
        self.assertEqual(
            [e["event_type"] for e in good["audit"]],
            ["LEASE_ISSUED", "LEASE_CONSUMED_GO", "PROVIDER_RECEIPT_COMMITTED"],
        )
        self.assertEqual(good["audit_head_sha256"], good["audit"][-1]["receipt_sha256"])

        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE send_lease_audit SET payload_json=? WHERE audit_id=2", ('{"tampered":true}',))
        conn.commit()
        conn.close()
        with self.assertRaisesRegex(m.LeaseError, "digest mismatch"):
            m.status(self.db, lease_id=lease["lease_id"])

    def test_row_tamper_is_detected_before_status_or_commit_authority(self):
        lease = self.issue()
        go = self.consume(lease)
        conn = sqlite3.connect(self.db)
        conn.execute(
            "UPDATE send_leases SET go_token_sha256=? WHERE lease_id=?",
            ("0" * 64, lease["lease_id"]),
        )
        conn.commit()
        conn.close()
        with self.assertRaisesRegex(m.LeaseError, "row diverges"):
            m.status(self.db, lease_id=lease["lease_id"])
        with self.assertRaisesRegex(m.LeaseError, "row diverges"):
            m._commit_at(
                self.db,
                lease_id=lease["lease_id"],
                session_nonce=self.session,
                go_token=go["go_token"],
                provider="gmail",
                provider_message_id="tamper-msg",
                now_s=1002,
            )

    def test_row_status_tamper_is_detected_before_consume(self):
        lease = self.issue()
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE send_leases SET status=? WHERE lease_id=?", (m.CONSUMED, lease["lease_id"]))
        conn.commit()
        conn.close()
        with self.assertRaisesRegex(m.LeaseError, "status diverges"):
            self.consume(lease)

    def test_database_never_stores_plaintext_go_token(self):
        lease = self.issue()
        go = self.consume(lease)
        conn = sqlite3.connect(self.db)
        row = conn.execute("SELECT * FROM send_leases WHERE lease_id=?", (lease["lease_id"],)).fetchone()
        columns = [d[0] for d in conn.execute("SELECT * FROM send_leases LIMIT 0").description]
        conn.close()
        self.assertNotIn("go_token", columns)
        stored = dict(zip(columns, row))
        self.assertNotIn(go["go_token"], {str(v) for v in stored.values()})
        self.assertEqual(stored["go_token_sha256"], m._token_digest(go["go_token"]))

    def test_process_clock_entrypoint_is_bound_against_later_time_module_rebind(self):
        original = m.time.time_ns
        try:
            m.time.time_ns = lambda: 1
            lease = m.issue_current(
                self.db,
                **self.identity,
                seat="Z-Sol-1447",
                session_nonce=self.session,
                ttl_seconds=60,
            )
        finally:
            m.time.time_ns = original
        self.assertGreater(lease["issued_at_s"], 1)

    def test_bool_ttl_invisible_and_non_nfc_identity_fail_closed(self):
        with self.assertRaises(m.LeaseError):
            self.issue(ttl=True)
        with self.assertRaises(m.LeaseError):
            m._issue_at(
                self.db,
                operation_key="\u200b",
                counterparty="Acme",
                route="sales@example.test",
                purpose="paid work",
                seat="Z-Sol-1447",
                session_nonce=self.session,
                ttl_seconds=60,
                now_s=1000,
            )
        with self.assertRaisesRegex(m.LeaseError, "NFC"):
            m._issue_at(
                self.db,
                operation_key="Cafe\u0301",
                counterparty="Acme",
                route="sales@example.test",
                purpose="paid work",
                seat="Z-Sol-1447",
                session_nonce=self.session,
                ttl_seconds=60,
                now_s=1000,
            )


if __name__ == "__main__":
    unittest.main()
