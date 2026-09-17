from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from revenue.outbound_collision_replay_guard.engine import (
    ATTEMPT_SCHEMA,
    LEDGER_SCHEMA,
    MUSE_SCHEMA,
    REQUEST_SCHEMA,
    RESULT_SCHEMA,
    GuardError,
    _cli,
    authority_flags,
    canonical_json,
    empty_ledger,
    load_json,
    sha256,
    transition,
    verify_transition,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64


def ledger_raw(value=None):
    return canonical_json(empty_ledger() if value is None else value)


def request(ledger: bytes, *, operation="CLAIM", claimant="agent-a", session="sess-a", generation=None, body=SHA_A, resolution="EXACT", thread="thread-1", mode="REPLY", now="2026-09-17T03:10:00Z", muse=None, attempt=None, result=None):
    return {
        "schema": REQUEST_SCHEMA,
        "evaluation_time": now,
        "operation": operation,
        "expected_ledger_sha256": sha256(ledger),
        "claimant_id": claimant,
        "session_id": session,
        "lease_ttl_seconds": 600,
        "generation": generation,
        "intent": {
            "counterparty_key": "org-example",
            "counterparty_resolution": resolution,
            "observed_aliases": ["org-example", "sales@example.invalid"],
            "provider": "gmail",
            "thread_scope_key": thread,
            "thread_mode": mode,
            "purpose_key": "paid-scope-followup",
            "body_sha256": body,
        },
        "muse": muse,
        "send_attempt": attempt,
        "send_result": result,
    }


def raw_request(*args, **kwargs):
    return canonical_json(request(*args, **kwargs))


def do(ledger, **kwargs):
    req = raw_request(ledger, **kwargs)
    after, receipt = transition(ledger, req)
    return after, load_json(receipt, "receipt"), req, receipt


def rec(ledger):
    return load_json(ledger, "ledger")["records"][0]


def muse_for(record, now="2026-09-17T03:10:05Z", expires="2026-09-17T03:15:00Z"):
    return {
        "schema": MUSE_SCHEMA,
        "receipt_id": "muse-1",
        "fingerprint": record["fingerprint"],
        "claimant_id": record["claimant_id"],
        "session_id": record["session_id"],
        "generation": record["generation"],
        "body_sha256": record["body_sha256"],
        "selected": True,
        "observed_at": now,
        "expires_at": expires,
        "source_uri": "slack:muse-dm/1",
        "source_sha256": SHA_B,
    }


def attempt_for(record, attempted="2026-09-17T03:10:10Z"):
    return {
        "schema": ATTEMPT_SCHEMA,
        "attempt_id": "attempt-1",
        "fingerprint": record["fingerprint"],
        "generation": record["generation"],
        "body_sha256": record["body_sha256"],
        "attempted_at": attempted,
        "provider_request_id": "gmail-request-1",
        "source_uri": "sender:attempt/1",
        "source_sha256": SHA_C,
    }


def result_for(record, status="ACCEPTED", observed="2026-09-17T03:10:15Z"):
    attempt = record["send_attempt"]
    return {
        "schema": RESULT_SCHEMA,
        "result_id": "result-1-" + status.lower(),
        "attempt_id": attempt["attempt_id"],
        "fingerprint": record["fingerprint"],
        "generation": record["generation"],
        "body_sha256": record["body_sha256"],
        "status": status,
        "observed_at": observed,
        "provider_message_id": "provider-msg-1" if status == "ACCEPTED" else None,
        "source_uri": "provider:result/1",
        "source_sha256": SHA_D,
    }


class GuardTests(unittest.TestCase):
    def test_claim_creates_single_writer(self):
        before = ledger_raw()
        after, receipt, req, rb = do(before)
        self.assertEqual(receipt["decision_state"], "CLAIMED")
        self.assertTrue(receipt["mutation"])
        self.assertEqual(rec(after)["generation"], 1)
        self.assertEqual(verify_transition(before, req, after, rb), "EXACT_OUTBOUND_GUARD_TRANSITION_MATCH")
        self.assertTrue(all(v is False for v in receipt["authority"].values()))

    def test_simultaneous_agents_same_base_need_cas(self):
        before = ledger_raw()
        after_a, receipt_a, _, _ = do(before, claimant="agent-a", session="sa")
        after_b, receipt_b, _, _ = do(before, claimant="agent-b", session="sb")
        self.assertEqual(receipt_a["before_ledger_sha256"], receipt_b["before_ledger_sha256"])
        self.assertNotEqual(after_a, after_b)
        stale_req = raw_request(after_b, claimant="agent-b", session="sb")
        stale_obj = load_json(stale_req)
        stale_obj["expected_ledger_sha256"] = receipt_b["before_ledger_sha256"]
        with self.assertRaisesRegex(GuardError, "stale ledger precondition"):
            transition(after_a, canonical_json(stale_obj))

    def test_second_agent_yields_live_lease(self):
        first, _, _, _ = do(ledger_raw())
        second, receipt, _, _ = do(first, claimant="agent-b", session="sb", now="2026-09-17T03:10:30Z")
        self.assertEqual(receipt["decision_state"], "YIELD_EXISTING")
        self.assertFalse(receipt["mutation"])
        self.assertEqual(second, first)

    def test_ambiguous_counterparty_holds_without_mutation(self):
        before = ledger_raw()
        after, receipt, _, _ = do(before, resolution="AMBIGUOUS")
        self.assertEqual(receipt["decision_state"], "HOLD_AMBIGUOUS_COUNTERPARTY")
        self.assertEqual(after, before)

    def test_reply_vs_new_thread_collision_holds(self):
        first, _, _, _ = do(ledger_raw(), thread="thread-1", mode="REPLY")
        after, receipt, _, _ = do(first, claimant="agent-b", session="sb", thread="new-thread-slot", mode="NEW_THREAD")
        self.assertEqual(receipt["decision_state"], "HOLD_AMBIGUOUS_COUNTERPARTY")
        self.assertEqual(after, first)

    def test_same_holder_claim_idempotent(self):
        first, _, _, _ = do(ledger_raw())
        after, receipt, _, _ = do(first, now="2026-09-17T03:10:30Z")
        self.assertEqual(receipt["decision_state"], "CLAIMED")
        self.assertFalse(receipt["mutation"])
        self.assertEqual(after, first)

    def test_body_change_advances_generation_and_invalidates_muse(self):
        first, _, _, _ = do(ledger_raw())
        after, receipt, _, _ = do(first, body=SHA_E, now="2026-09-17T03:10:30Z")
        self.assertEqual(receipt["decision_state"], "WAIT_MUSE")
        self.assertEqual(rec(after)["generation"], 2)
        self.assertEqual(rec(after)["body_sha256"], SHA_E)
        self.assertIsNone(rec(after)["muse"])

    def test_muse_exact_makes_ready_but_not_send_authority(self):
        claimed, _, _, _ = do(ledger_raw())
        record = rec(claimed)
        muse = muse_for(record)
        ready, receipt, _, _ = do(claimed, operation="APPLY_MUSE", generation=1, muse=muse, now="2026-09-17T03:10:06Z")
        self.assertEqual(receipt["decision_state"], "READY_SINGLE_WRITER")
        self.assertEqual(rec(ready)["state"], "READY_SINGLE_WRITER")
        self.assertFalse(receipt["authority"]["external_send_authorized"])
        self.assertFalse(receipt["authority"]["muse_authority_minted"])

    def test_stale_muse_waits(self):
        claimed, _, _, _ = do(ledger_raw())
        record = rec(claimed)
        muse = muse_for(record, now="2026-09-17T03:10:04Z", expires="2026-09-17T03:10:05Z")
        after, receipt, _, _ = do(claimed, operation="APPLY_MUSE", generation=1, muse=muse, now="2026-09-17T03:10:06Z")
        self.assertEqual(receipt["decision_state"], "WAIT_MUSE")
        self.assertEqual(after, claimed)

    def test_muse_wrong_generation_waits(self):
        claimed, _, _, _ = do(ledger_raw())
        muse = muse_for(rec(claimed))
        muse["generation"] = 2
        _, receipt, _, _ = do(claimed, operation="APPLY_MUSE", generation=1, muse=muse, now="2026-09-17T03:10:06Z")
        self.assertEqual(receipt["decision_state"], "WAIT_MUSE")

    def test_muse_wrong_body_waits(self):
        claimed, _, _, _ = do(ledger_raw())
        muse = muse_for(rec(claimed))
        muse["body_sha256"] = SHA_E
        _, receipt, _, _ = do(claimed, operation="APPLY_MUSE", generation=1, muse=muse, now="2026-09-17T03:10:06Z")
        self.assertEqual(receipt["decision_state"], "WAIT_MUSE")

    def test_record_attempt_requires_ready(self):
        claimed, _, _, _ = do(ledger_raw())
        attempt = attempt_for(rec(claimed))
        after, receipt, _, _ = do(claimed, operation="RECORD_SEND_ATTEMPT", generation=1, attempt=attempt, now="2026-09-17T03:10:11Z")
        self.assertEqual(receipt["decision_state"], "WAIT_MUSE")
        self.assertEqual(after, claimed)

    def _attempted(self):
        claimed, _, _, _ = do(ledger_raw())
        muse = muse_for(rec(claimed))
        ready, _, _, _ = do(claimed, operation="APPLY_MUSE", generation=1, muse=muse, now="2026-09-17T03:10:06Z")
        attempt = attempt_for(rec(ready))
        attempted, receipt, _, _ = do(ready, operation="RECORD_SEND_ATTEMPT", generation=1, attempt=attempt, now="2026-09-17T03:10:11Z")
        self.assertEqual(receipt["decision_state"], "CLAIMED")
        return attempted

    def test_second_send_attempt_blocked(self):
        attempted = self._attempted()
        other = attempt_for(rec(attempted))
        other["attempt_id"] = "attempt-2"
        other["provider_request_id"] = "gmail-request-2"
        after, receipt, _, _ = do(attempted, operation="RECORD_SEND_ATTEMPT", generation=1, attempt=other, now="2026-09-17T03:10:20Z")
        self.assertEqual(receipt["decision_state"], "WAIT_MUSE")  # state is CLAIMED, so no retry path
        self.assertEqual(after, attempted)

    def test_changed_body_after_attempt_blocked(self):
        attempted = self._attempted()
        after, receipt, _, _ = do(attempted, body=SHA_E, now="2026-09-17T03:10:20Z")
        self.assertEqual(receipt["decision_state"], "CLAIMED")
        self.assertEqual(after, attempted)

    def test_unknown_result_blocks_release_and_retry(self):
        attempted = self._attempted()
        result = result_for(rec(attempted), "UNKNOWN")
        unknown, receipt, _, _ = do(attempted, operation="RECORD_SEND_RESULT", generation=1, result=result, now="2026-09-17T03:10:16Z")
        self.assertEqual(receipt["decision_state"], "CLAIMED")
        released, release_receipt, _, _ = do(unknown, operation="RELEASE", generation=1, now="2026-09-17T03:10:20Z")
        self.assertEqual(release_receipt["decision_state"], "CLAIMED")
        self.assertEqual(released, unknown)

    def test_accepted_result_is_terminal(self):
        attempted = self._attempted()
        result = result_for(rec(attempted), "ACCEPTED")
        sent, receipt, _, _ = do(attempted, operation="RECORD_SEND_RESULT", generation=1, result=result, now="2026-09-17T03:10:16Z")
        self.assertEqual(receipt["decision_state"], "SENT_TERMINAL")
        replay, replay_receipt, _, _ = do(sent, claimant="agent-b", session="sb", now="2026-09-17T03:10:30Z")
        self.assertEqual(replay_receipt["decision_state"], "SENT_TERMINAL")
        self.assertEqual(replay, sent)

    def test_rejected_result_requires_fresh_muse(self):
        attempted = self._attempted()
        result = result_for(rec(attempted), "REJECTED")
        rejected, receipt, _, _ = do(attempted, operation="RECORD_SEND_RESULT", generation=1, result=result, now="2026-09-17T03:10:16Z")
        self.assertEqual(receipt["decision_state"], "WAIT_MUSE")
        self.assertIsNone(rec(rejected)["muse"])

    def test_release_unsent(self):
        claimed, _, _, _ = do(ledger_raw())
        released, receipt, _, _ = do(claimed, operation="RELEASE", generation=1, now="2026-09-17T03:10:30Z")
        self.assertEqual(receipt["decision_state"], "RELEASED_UNSENT")
        self.assertEqual(rec(released)["state"], "RELEASED_UNSENT")

    def test_released_unsent_can_be_reclaimed_immediately(self):
        claimed, _, _, _ = do(ledger_raw())
        released, _, _, _ = do(claimed, operation="RELEASE", generation=1, now="2026-09-17T03:10:30Z")
        reclaimed, receipt, _, _ = do(released, claimant="agent-b", session="sb", now="2026-09-17T03:10:31Z")
        self.assertEqual(receipt["decision_state"], "CLAIMED")
        self.assertEqual(rec(reclaimed)["generation"], 2)
        self.assertEqual(rec(reclaimed)["claimant_id"], "agent-b")

    def test_rejected_send_can_release_then_reclaim_new_generation(self):
        attempted = self._attempted()
        result = result_for(rec(attempted), "REJECTED")
        rejected, _, _, _ = do(attempted, operation="RECORD_SEND_RESULT", generation=1, result=result, now="2026-09-17T03:10:16Z")
        released, release_receipt, _, _ = do(rejected, operation="RELEASE", generation=1, now="2026-09-17T03:10:17Z")
        self.assertEqual(release_receipt["decision_state"], "RELEASED_UNSENT")
        reclaimed, receipt, _, _ = do(released, now="2026-09-17T03:10:18Z")
        self.assertEqual(receipt["decision_state"], "CLAIMED")
        self.assertEqual(rec(reclaimed)["generation"], 2)
        self.assertIsNone(rec(reclaimed)["send_attempt"])
        self.assertIsNone(rec(reclaimed)["send_result"])

    def test_expired_safe_claim_reclaimed_new_generation(self):
        claimed, _, _, _ = do(ledger_raw(), now="2026-09-17T03:00:00Z")
        reclaimed, receipt, _, _ = do(claimed, claimant="agent-b", session="sb", now="2026-09-17T03:20:01Z")
        self.assertEqual(receipt["decision_state"], "CLAIMED")
        self.assertEqual(rec(reclaimed)["generation"], 2)
        self.assertEqual(rec(reclaimed)["claimant_id"], "agent-b")

    def test_expired_unresolved_attempt_not_stolen(self):
        attempted = self._attempted()
        value = load_json(attempted)
        value["records"][0]["lease_expires_at"] = "2026-09-17T03:10:12Z"
        value["records"][0]["updated_at"] = "2026-09-17T03:10:11Z"
        attempted = ledger_raw(value)
        after, receipt, _, _ = do(attempted, claimant="agent-b", session="sb", now="2026-09-17T03:20:00Z")
        self.assertEqual(receipt["decision_state"], "YIELD_EXISTING")
        self.assertEqual(after, attempted)

    def test_recover_dead_claimant_advances_generation(self):
        claimed, _, _, _ = do(ledger_raw(), now="2026-09-17T03:00:00Z")
        recovered, receipt, _, _ = do(claimed, operation="RECOVER", claimant="agent-b", session="sb", generation=None, now="2026-09-17T03:20:01Z")
        self.assertEqual(receipt["decision_state"], "CLAIMED")
        self.assertEqual(rec(recovered)["generation"], 2)

    def test_generation_mismatch_blocks_mutation(self):
        claimed, _, _, _ = do(ledger_raw())
        after, receipt, _, _ = do(claimed, operation="HEARTBEAT", generation=2, now="2026-09-17T03:10:30Z")
        self.assertEqual(receipt["decision_state"], "YIELD_EXISTING")
        self.assertEqual(after, claimed)

    def test_duplicate_keys_float_nan_rejected(self):
        with self.assertRaises(GuardError):
            load_json(b'{"schema":"x","schema":"y"}')
        for raw in [b'{"x":1.5}', b'{"x":NaN}', b'{"x":Infinity}']:
            with self.assertRaises(GuardError):
                load_json(raw)

    def test_noncanonical_ledger_rejected(self):
        raw = b'{"records": [], "schema": "' + LEDGER_SCHEMA.encode() + b'"}\n'
        with self.assertRaisesRegex(GuardError, "canonical"):
            transition(raw, raw_request(ledger_raw()))

    def test_tampered_after_and_receipt_rejected(self):
        before = ledger_raw()
        after, receipt, req, rb = do(before)
        tampered = load_json(after)
        tampered["records"][0]["state"] = "READY_SINGLE_WRITER"
        with self.assertRaisesRegex(GuardError, "after ledger mismatch"):
            verify_transition(before, req, canonical_json(tampered), rb)
        tampered_r = load_json(rb)
        tampered_r["decision_state"] = "SENT_TERMINAL"
        with self.assertRaisesRegex(GuardError, "receipt mismatch"):
            verify_transition(before, req, after, canonical_json(tampered_r))

    def test_cli_transition_verify_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            before = ledger_raw()
            req = raw_request(before)
            lp = root / "ledger.json"
            rp = root / "request.json"
            out = root / "after.json"
            receipt = root / "receipt.json"
            lp.write_bytes(before)
            rp.write_bytes(req)
            self.assertEqual(_cli(["transition", str(lp), str(rp), "--ledger-out", str(out), "--receipt", str(receipt)]), 0)
            self.assertEqual(_cli(["verify", str(lp), str(rp), str(out), str(receipt)]), 0)
            self.assertEqual(_cli(["transition", str(lp), str(rp), "--ledger-out", str(out), "--receipt", str(receipt)]), 2)

    def test_cli_rejects_symlink_input(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real = root / "real.json"
            link = root / "link.json"
            req = root / "request.json"
            out = root / "after.json"
            receipt = root / "receipt.json"
            before = ledger_raw()
            real.write_bytes(before)
            req.write_bytes(raw_request(before))
            link.symlink_to(real)
            self.assertEqual(_cli(["transition", str(link), str(req), "--ledger-out", str(out), "--receipt", str(receipt)]), 2)


if __name__ == "__main__":
    unittest.main()
