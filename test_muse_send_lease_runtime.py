"""Real SQLite runtime regressions for Commons' existing Muse lease coordinator.

All data is synthetic. No network or message provider is called. Capability
values are kept in process memory only and excluded from subprocess reports.
"""
from __future__ import annotations

import importlib.util
import json
import multiprocessing
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from coordination import muse_send_lease as m

IDENTITY = dict(operation_key="ARGOSY-RUNTIME-SYNTHETIC", counterparty="Example Test",
                route="recipient@example.test", purpose="synthetic runtime validation")
SESSION = "argosy-synthetic-session"


class MutableClock:
    def __init__(self, value):
        self.value = value
        self.samples = []

    def __call__(self):
        self.samples.append(self.value)
        return self.value


class SequenceClock:
    def __init__(self, *values):
        self.values = iter(values)

    def __call__(self):
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return value


class CursorProxy:
    def __init__(self, inner, after_row):
        self.inner = inner
        self.after_row = after_row

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def fetchone(self):
        row = self.inner.fetchone()
        self.after_row()
        return row


class ConnectionProxy:
    """Test-only SQLite instrumentation installed BEFORE runtime capture."""
    def __init__(self, inner, controls):
        self.inner = inner
        self.controls = controls

    def __getattr__(self, name):
        return getattr(self.inner, name)

    @property
    def row_factory(self):
        return self.inner.row_factory

    @row_factory.setter
    def row_factory(self, value):
        self.inner.row_factory = value

    def execute(self, sql, *args):
        before_begin = self.controls.get("before_begin")
        if sql == "BEGIN IMMEDIATE" and before_begin is not None:
            before_begin.set()
        if sql.lstrip().startswith("INSERT INTO send_lease_audit") and self.controls.get("fail_audit"):
            raise RuntimeError("synthetic audit failure")
        cursor = self.inner.execute(sql, *args)
        after_row = self.controls.get("after_row")
        if sql == "SELECT * FROM send_leases WHERE lease_id=?" and after_row is not None:
            return CursorProxy(cursor, after_row)
        return cursor

    def commit(self):
        mode = self.controls.get("commit_mode")
        if mode == "before":
            raise sqlite3.OperationalError("synthetic pre-commit failure")
        self.inner.commit()
        if mode == "after":
            raise sqlite3.OperationalError("synthetic outcome-unknown commit")


def isolated_runtime(controls):
    """Load exact source with a synthetic connection factory bound at import.

    Do not mutate captured function defaults/closures or weaken production seals.
    The normal import is used by the independent process-race workers.
    """
    raw_connect = sqlite3.connect

    def connect(*args, **kwargs):
        return ConnectionProxy(raw_connect(*args, **kwargs), controls)

    spec = importlib.util.spec_from_file_location("_argosy_runtime_under_test", m.__file__)
    module = importlib.util.module_from_spec(spec)
    with patch.object(sqlite3, "connect", connect):
        spec.loader.exec_module(module)
    return module


def process_consumer(db, lease_id, start, ready, output):
    ready.put(True)
    if not start.wait(15):
        output.put({"error": "start timeout"})
        return
    try:
        answer = m.consume_current(db, lease_id=lease_id, **IDENTITY, session_nonce=SESSION)
        output.put({"decision": answer["decision"], "has_token": "go_token" in answer,
                    "status": answer["status"], "optimized": sys.flags.optimize})
    except Exception as exc:
        output.put({"error": type(exc).__name__})


def process_issuer(db, session, start, ready, output):
    ready.put(True)
    if not start.wait(15):
        output.put({"error": "start timeout"})
        return
    try:
        answer = m.issue_current(db, **IDENTITY, seat="Z-Argosy", session_nonce=session)
        output.put({"decision": answer["decision"], "lease_id": answer["lease_id"],
                    "selected_session": answer["selected_session"],
                    "has_token": "go_token" in answer, "optimized": sys.flags.optimize})
    except Exception as exc:
        output.put({"error": type(exc).__name__})


class MuseRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "lease.sqlite3")
        self.controls = {}
        self.m = isolated_runtime(self.controls)

    def issue(self, now=1000, ttl=10):
        return self.m._issue_at(self.db, **IDENTITY, seat="Z-Argosy", session_nonce=SESSION,
                           ttl_seconds=ttl, now_s=now)

    def consume(self, lease, now=1001):
        return self.m._consume_at(self.db, lease_id=lease["lease_id"], **IDENTITY,
                             session_nonce=SESSION, now_s=now)

    def commit_kwargs(self, lease, go):
        return dict(lease_id=lease["lease_id"], session_nonce=SESSION,
                    go_token=go["go_token"], provider="synthetic-provider",
                    provider_message_id="synthetic-message-1")

    def run_behind_writer_lock(self, clock, action, new_time):
        """A real SQLite lock; an event removes timing/sleep assumptions."""
        blocker = sqlite3.connect(self.db, isolation_level=None)
        blocker.execute("BEGIN IMMEDIATE")
        before_begin = threading.Event()
        answers, failures = [], []
        def worker():
            try:
                answers.append(action())
            except BaseException as exc:
                failures.append(exc)

        thread = threading.Thread(target=worker)
        try:
            self.controls["before_begin"] = before_begin
            thread.start()
            self.assertTrue(before_begin.wait(5), "worker never reached write-lock acquisition")
            clock.value = new_time
            blocker.commit()
            thread.join(10)
            self.assertFalse(thread.is_alive(), "worker did not complete after lock release")
        finally:
            self.controls.pop("before_begin", None)
            if blocker.in_transaction:
                blocker.rollback()
            blocker.close()
            if thread.is_alive():
                thread.join(10)
        if failures:
            raise failures[0]
        self.assertEqual(len(answers), 1)
        return answers[0]

    def test_issue_ttl_starts_after_write_lock_acquisition(self):
        self.issue()
        clock = MutableClock(1001)
        issue, *_ = self.m._bind_current_api(clock)
        other = dict(IDENTITY, operation_key="ARGOSY-SECOND-SYNTHETIC")
        answer = self.run_behind_writer_lock(
            clock, lambda: issue(self.db, **other, seat="Z-Argosy", session_nonce=SESSION,
                                 ttl_seconds=2), 1005)
        self.assertEqual(answer["issued_at_s"], 1005)
        self.assertEqual(answer["expires_at_s"], 1007)
        self.assertEqual(clock.samples[0], 1005)

    def test_consume_waiting_past_expiry_returns_no_go(self):
        lease = self.issue(ttl=2)
        clock = MutableClock(1001)
        _, consume, *_ = self.m._bind_current_api(clock)
        answer = self.run_behind_writer_lock(
            clock, lambda: consume(self.db, lease_id=lease["lease_id"], **IDENTITY,
                                   session_nonce=SESSION), 1003)
        self.assertEqual(answer["status"], self.m.HOLD_EXPIRED_UNCONSUMED)
        self.assertEqual(answer["send_gate"], "HOLD")
        self.assertNotIn("go_token", answer)
        self.assertEqual(clock.samples[0], 1003)

    def test_commit_waiting_past_expiry_requires_reconciliation(self):
        lease = self.issue(ttl=4)
        go = self.consume(lease)
        clock = MutableClock(1002)
        _, _, commit, *_ = self.m._bind_current_api(clock)
        answer = self.run_behind_writer_lock(
            clock, lambda: commit(self.db, **self.commit_kwargs(lease, go)), 1005)
        self.assertEqual(answer["status"], self.m.HOLD_NEEDS_RECONCILIATION)
        self.assertIsNone(answer["provider_message_id"])
        self.assertNotIn("go_token", answer)

    def test_expire_samples_after_waiting_for_writer(self):
        lease = self.issue(ttl=2)
        clock = MutableClock(1001)
        _, _, _, expire, _ = self.m._bind_current_api(clock)
        answer = self.run_behind_writer_lock(
            clock, lambda: expire(self.db, lease_id=lease["lease_id"]), 1003)
        self.assertEqual(answer["status"], self.m.HOLD_EXPIRED_UNCONSUMED)

    def test_reconcile_uses_post_lock_expiry(self):
        lease = self.issue(ttl=3)
        self.consume(lease)
        clock = MutableClock(1002)
        *_, reconcile = self.m._bind_current_api(clock)
        answer = self.run_behind_writer_lock(
            clock, lambda: reconcile(self.db, lease_id=lease["lease_id"], provider_seen=False,
                                     note="Synthetic no-provider census"), 1004)
        self.assertEqual(answer["status"], self.m.HOLD_RECONCILED_NO_SEND)
        self.assertEqual(answer["send_gate"], "HOLD_NEW_GENERATION_REQUIRED")
        self.assertNotIn("go_token", answer)

    def status_during_writer(self, writer_action, expected_old, expected_new):
        fetched, writer_done = threading.Event(), threading.Event()
        failures = []
        main_id = threading.get_ident()

        def after_row():
            if threading.get_ident() == main_id:
                fetched.set()
                if not writer_done.wait(5):
                    raise RuntimeError("concurrent writer did not complete")

        def writer():
            try:
                if not fetched.wait(5):
                    raise RuntimeError("reader did not fetch")
                writer_action()
            except BaseException as exc:
                failures.append(exc)
            finally:
                writer_done.set()

        thread = threading.Thread(target=writer)
        self.controls["after_row"] = after_row
        thread.start()
        try:
            old = self.m.status(self.db, lease_id=self.lease["lease_id"])
        finally:
            thread.join(10)
            self.controls.pop("after_row", None)
        self.assertFalse(thread.is_alive())
        self.assertFalse(failures, [type(e).__name__ for e in failures])
        self.assertEqual(old["status"], expected_old)
        self.assertEqual(old["audit"][-1]["next_status"], expected_old)
        new = self.m.status(self.db, lease_id=self.lease["lease_id"])
        self.assertEqual(new["status"], expected_new)
        self.assertEqual(new["audit"][-1]["next_status"], expected_new)
        self.assertNotIn("go_token", old)
        self.assertNotIn("go_token", new)

    def test_status_snapshot_is_coherent_across_concurrent_consume(self):
        self.lease = self.issue()
        self.status_during_writer(lambda: self.consume(self.lease), self.m.LEASED, self.m.CONSUMED)

    def test_status_snapshot_is_coherent_across_concurrent_commit(self):
        self.lease = self.issue()
        go = self.consume(self.lease)
        self.status_during_writer(
            lambda: self.m._commit_at(self.db, **self.commit_kwargs(self.lease, go), now_s=1002),
            self.m.CONSUMED, self.m.SENT)

    def test_handoff_expired_after_durable_consume_suppresses_token(self):
        lease = self.issue(ttl=2)
        _, consume, *_ = self.m._bind_current_api(SequenceClock(1001, 1002))
        answer = consume(self.db, lease_id=lease["lease_id"], **IDENTITY, session_nonce=SESSION)
        self.assertEqual(answer["status"], self.m.HOLD_NEEDS_RECONCILIATION)
        self.assertNotIn("go_token", answer)
        self.assertEqual(answer["send_gate"], "HOLD")
        state = self.m.status(self.db, lease_id=lease["lease_id"])
        self.assertEqual([a["event_type"] for a in state["audit"]],
                         ["LEASE_ISSUED", "LEASE_CONSUMED_GO", "LEASE_EXPIRED"])

    def test_handoff_clock_rollback_never_returns_token(self):
        lease = self.issue()
        _, consume, *_ = self.m._bind_current_api(SequenceClock(1001, 999))
        with self.assertRaises(self.m.LeaseError):
            consume(self.db, lease_id=lease["lease_id"], **IDENTITY, session_nonce=SESSION)
        state = self.m.status(self.db, lease_id=lease["lease_id"])
        self.assertEqual(state["status"], self.m.CONSUMED)
        self.assertEqual(self.consume(lease, now=1002)["send_gate"], "HOLD")

    def test_handoff_invalid_clock_never_returns_token(self):
        for value in (True, 1.5, -1, 2**54):
            with self.subTest(value=value):
                self.db = str(Path(self.tmp.name) / f"invalid-{type(value).__name__}-{str(value)}.db")
                lease = self.issue()
                _, consume, *_ = self.m._bind_current_api(SequenceClock(1001, value))
                with self.assertRaises(self.m.LeaseError):
                    consume(self.db, lease_id=lease["lease_id"], **IDENTITY, session_nonce=SESSION)
                self.assertEqual(self.m.status(self.db, lease_id=lease["lease_id"])["status"], self.m.CONSUMED)

    def test_handoff_clock_failure_preserves_consumed_no_retry_state(self):
        lease = self.issue()
        _, consume, *_ = self.m._bind_current_api(SequenceClock(1001, RuntimeError("clock unavailable")))
        with self.assertRaisesRegex(RuntimeError, "clock unavailable"):
            consume(self.db, lease_id=lease["lease_id"], **IDENTITY, session_nonce=SESSION)
        self.assertEqual(self.consume(lease, now=1002)["send_gate"], "HOLD")

    def test_live_handoff_preserves_single_capability(self):
        lease = self.issue()
        _, consume, *_ = self.m._bind_current_api(SequenceClock(1001, 1001))
        answer = consume(self.db, lease_id=lease["lease_id"], **IDENTITY, session_nonce=SESSION)
        self.assertEqual(answer["send_gate"], "GO_ONCE")
        self.assertIn("go_token", answer)
        self.assertNotIn("go_token_sha256", answer)
        self.assertNotIn("go_token", self.consume(lease, now=1002))

    def test_audit_failure_rolls_back_entire_consume(self):
        lease = self.issue()
        self.controls["fail_audit"] = True
        try:
            with self.assertRaisesRegex(RuntimeError, "audit failure"):
                self.consume(lease)
        finally:
            self.controls.pop("fail_audit", None)
        state = self.m.status(self.db, lease_id=lease["lease_id"])
        self.assertEqual(state["status"], self.m.LEASED)
        self.assertEqual(len(state["audit"]), 1)
        self.assertEqual(self.consume(lease)["decision"], "GO")

    def test_pre_commit_failure_rolls_back_and_allows_one_fresh_consume(self):
        lease = self.issue()
        self.controls["commit_mode"] = "before"
        try:
            with self.assertRaises(sqlite3.OperationalError):
                self.consume(lease)
        finally:
            self.controls.pop("commit_mode", None)
        self.assertEqual(self.m.status(self.db, lease_id=lease["lease_id"])["status"], self.m.LEASED)
        self.assertEqual(self.consume(lease)["decision"], "GO")

    def test_outcome_unknown_commit_never_reissues_go(self):
        lease = self.issue()
        self.controls["commit_mode"] = "after"
        try:
            with self.assertRaises(sqlite3.OperationalError):
                self.consume(lease)
        finally:
            self.controls.pop("commit_mode", None)
        state = self.m.status(self.db, lease_id=lease["lease_id"])
        self.assertEqual(state["status"], self.m.CONSUMED)
        self.assertEqual(len(state["audit"]), 2)
        self.assertEqual(self.consume(lease, now=1002)["send_gate"], "HOLD")

    def test_expiry_exact_boundary_and_control_before_boundary(self):
        for offset, expected in ((1, "GO_ONCE"), (2, "HOLD"), (3, "HOLD")):
            with self.subTest(offset=offset):
                self.db = str(Path(self.tmp.name) / f"expiry-{offset}.db")
                lease = self.issue(ttl=2)
                self.assertEqual(self.consume(lease, now=1000+offset)["send_gate"], expected)

    def test_consume_clock_before_issue_cannot_mutate(self):
        lease = self.issue()
        with self.assertRaises(self.m.LeaseError):
            self.consume(lease, now=999)
        self.assertEqual(self.m.status(self.db, lease_id=lease["lease_id"])["status"], self.m.LEASED)

    def test_commit_clock_before_consume_cannot_mutate(self):
        lease = self.issue()
        go = self.consume(lease, now=1002)
        with self.assertRaises(self.m.LeaseError):
            self.m._commit_at(self.db, **self.commit_kwargs(lease, go), now_s=1001)
        self.assertEqual(self.m.status(self.db, lease_id=lease["lease_id"])["status"], self.m.CONSUMED)

    def test_equal_second_issue_consume_commit_is_valid(self):
        lease = self.issue()
        go = self.consume(lease, now=1000)
        answer = self.m._commit_at(self.db, **self.commit_kwargs(lease, go), now_s=1000)
        self.assertEqual(answer["status"], self.m.SENT)

    def test_current_api_rejects_caller_supplied_now(self):
        with self.assertRaises(TypeError):
            self.m.issue_current(self.db, **IDENTITY, seat="Z-Argosy", session_nonce=SESSION, now_s=1)
        self.assertFalse(Path(self.db).exists())

    def test_invalid_static_now_rejected_before_creating_database(self):
        with self.assertRaises(self.m.LeaseError):
            self.issue(now=True)
        self.assertFalse(Path(self.db).exists())

    def test_expiry_integer_overflow_is_rejected(self):
        with self.assertRaises(self.m.LeaseError):
            self.issue(now=2**53-1, ttl=1)

    def run_process_race(self, target, args_for, count=8):
        ctx = multiprocessing.get_context("spawn")
        start, ready, output = ctx.Event(), ctx.Queue(), ctx.Queue()
        processes = [ctx.Process(target=target, args=(*args_for(i), start, ready, output)) for i in range(count)]
        try:
            for process in processes:
                process.start()
            for _ in processes:
                self.assertTrue(ready.get(timeout=15))
            start.set()
            answers = [output.get(timeout=15) for _ in processes]
            for process in processes:
                process.join(10)
                self.assertEqual(process.exitcode, 0)
            self.assertFalse([a for a in answers if "error" in a])
            self.assertTrue(all(a["optimized"] == sys.flags.optimize for a in answers))
            return answers
        finally:
            start.set()
            for process in processes:
                if process.pid is not None:
                    if process.is_alive():
                        process.terminate()
                    process.join(5)
            for q in (ready, output):
                q.close()
                q.join_thread()

    def test_eight_independent_processes_receive_exactly_one_go(self):
        lease = self.m.issue_current(self.db, **IDENTITY, seat="Z-Argosy", session_nonce=SESSION)
        answers = self.run_process_race(process_consumer, lambda i: (self.db, lease["lease_id"]))
        self.assertEqual(sum(a["decision"] == "GO" for a in answers), 1)
        self.assertEqual(sum(a["has_token"] for a in answers), 1)
        self.assertEqual(sum(a["decision"] == "HOLD_ALREADY_CONSUMED" for a in answers), 7)

    def test_eight_process_issuers_converge_to_one_lease(self):
        self.m._connect(self.db).close()  # Explicit initialized deployment store, not a per-worker database.
        answers = self.run_process_race(process_issuer, lambda i: (self.db, f"synthetic-{i}"))
        self.assertEqual(sum(a["decision"] == "LEASE_ISSUED" for a in answers), 1)
        self.assertEqual(len({a["lease_id"] for a in answers}), 1)
        self.assertEqual(len({a["selected_session"] for a in answers}), 1)
        self.assertFalse(any(a["has_token"] for a in answers))

    def test_worker_exit_after_consume_does_not_permit_retry(self):
        lease = self.m.issue_current(self.db, **IDENTITY, seat="Z-Argosy", session_nonce=SESSION)
        code = (
            "import json, os, sys; from coordination import muse_send_lease as m; "
            "m.consume_current(sys.argv[1], lease_id=sys.argv[2], "
            "**json.loads(sys.argv[3]), session_nonce=sys.argv[4]); "
            "os._exit(17 if sys.flags.optimize == int(sys.argv[5]) else 18)"
        )
        flags = ["-" + "O" * sys.flags.optimize] if sys.flags.optimize else []
        answer = subprocess.run([sys.executable, *flags, "-c", code, self.db, lease["lease_id"],
                                 json.dumps(IDENTITY), SESSION, str(sys.flags.optimize)], capture_output=True,
                                timeout=15, cwd=Path(__file__).resolve().parent)
        self.assertEqual(answer.returncode, 17)
        self.assertEqual(answer.stdout, b"")
        self.assertEqual(answer.stderr, b"")
        replay = self.m.consume_current(self.db, lease_id=lease["lease_id"], **IDENTITY, session_nonce=SESSION)
        self.assertEqual(replay["send_gate"], "HOLD")
        self.assertNotIn("go_token", replay)

    def test_no_provider_or_revenue_authority_is_added(self):
        lease = self.issue()
        go = self.consume(lease)
        committed = self.m._commit_at(self.db, **self.commit_kwargs(lease, go), now_s=1002)
        for answer in (lease, go, committed):
            for name in ("provider_send_independently_verified", "buyer_acceptance_authority",
                         "contract_authority", "payment_authority", "cash_authority", "revenue_authority"):
                self.assertIs(answer[name], False)


if __name__ == "__main__":
    unittest.main()
