#!/usr/bin/env python3
"""Bounded Commons → Cursor self-wake test.

1. create a job
2. miss the first due event / wait for schedule
3. watchdog wakes the owning harness without Bryce
4. resume from checkpoint
5. write DONE + durable result
6. next tick exits with zero model invocation

The watchdog process never invokes a model. invoke_model is a signal to the
owning harness adapter.
"""
from __future__ import annotations

import json
import multiprocessing
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from harness_wake.callback import consume_delivery, finish_delivery
from harness_wake.cursor_adapter import claimed_paths, ntfy_payload, should_ring_issue_1316
from harness_wake.watchdog import run
from independent_commons_mcp.jobs import JobError, JobStore, utc_now
from independent_commons_mcp.server import MCPServer


JOB_ID = "ridge-self-wake-20260822-01"
RESULT_ID = "ridge-self-wake-result-20260822-01"
T0 = "2026-08-22T04:00:00Z"
DUE = "2026-08-22T04:10:00Z"
WATCHDOG = "2026-08-22T04:20:00Z"
RESUME = "2026-08-22T04:21:00Z"
AFTER = "2026-08-22T04:22:00Z"
DEADLINE = "2026-08-22T12:00:00Z"


def fields(**extra):
    data = {
        "job_id": JOB_ID,
        "owner_claim": "RIDGE",
        "harness": "cursor-slack",
        "objective": "bounded self-wake: checkpoint then DONE",
        "checkpoint": {"step": 0},
        "next_wake_at": DUE,
        "deadline": DEADLINE,
        "max_attempts": 4,
        "budget_tokens": 50,
        "backoff_seconds": 60,
        "lease_seconds": 30,
        "completion_predicate": {"type": "checkpoint_equals", "path": "step", "value": 2},
        "result_address": RESULT_ID,
    }
    data.update(extra)
    return data


def worker(store, tick, now, pages, model_calls, worker_id="cursor-ridge"):
    if not tick.get("invoke_model"):
        return "skipped"
    model_calls.append(tick.get("attempt_id") or tick["job_id"])
    job = store.get(tick["job_id"])
    step = int((job.get("checkpoint") or {}).get("step") or 0) + 1
    store.checkpoint(
        job["job_id"],
        {"step": step},
        attempt_id=tick["attempt_id"],
        lease_id=tick["lease_id"],
        next_wake_at=now,
        worker_id=worker_id,
        now=now,
    )
    if step >= 2:
        addr = job["result_address"]
        pages.add(addr)
        store.complete(
            job["job_id"],
            result={"durable": True, "step": step, "kind": "page"},
            result_address=addr,
            page_exists=lambda ident: ident in pages,
            worker_id=worker_id,
            now=now,
        )
        return "done"
    return "checkpoint"


def _process_tick(jobs_dir, barrier, queue, worker_id):
    try:
        store = JobStore(jobs_dir)
        barrier.wait()
        queue.put({"result": store.tick(JOB_ID, now=WATCHDOG, worker_id=worker_id)})
    except Exception as exc:  # pragma: no cover - returned to the parent assertion.
        queue.put({"error": type(exc).__name__, "code": getattr(exc, "code", ""), "message": str(exc)})


def _process_hold_transaction(jobs_dir, entered, release):
    store = JobStore(jobs_dir)
    with store._transaction():
        entered.set()
        release.wait(timeout=5)


def _process_cancel(jobs_dir, started, finished, queue):
    try:
        store = JobStore(jobs_dir)
        started.set()
        queue.put({"result": store.cancel(JOB_ID, reason="process cancel")})
    except Exception as exc:  # pragma: no cover - returned to the parent assertion.
        queue.put({"error": type(exc).__name__, "code": getattr(exc, "code", ""), "message": str(exc)})
    finally:
        finished.set()


def _process_consume(jobs_dir, barrier, queue, mail):
    try:
        store = JobStore(jobs_dir)
        barrier.wait()
        queue.put({"result": consume_delivery(store, mail, now=WATCHDOG, pages=set())})
    except Exception as exc:  # pragma: no cover - returned to the parent assertion.
        queue.put({"error": type(exc).__name__, "code": getattr(exc, "code", ""), "message": str(exc)})


class BoundedSelfWakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wake-jobs-")
        self.store = JobStore(self.tmp.name)
        self.pages = set()
        self.model_calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def test_six_step_self_wake_then_zero_model(self):
        created = self.store.upsert(fields())
        self.assertEqual(created["job"]["job_id"], JOB_ID)
        self.assertEqual(created["state"], "OPEN")

        missed = self.store.tick(JOB_ID, now=T0, worker_id="cursor-ridge")
        self.assertEqual(missed["action"], "STOP")
        self.assertFalse(missed["invoke_model"])
        self.assertEqual(missed["reason"], "NOT_DUE")
        self.assertEqual(self.model_calls, [])

        wake = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="cursor-ridge")
        self.assertEqual(wake["action"], "WAKE")
        self.assertTrue(wake["invoke_model"])
        self.assertEqual(wake["job_id"], JOB_ID)
        self.assertNotEqual(wake["attempt_id"], JOB_ID)
        self.assertEqual(worker(self.store, wake, WATCHDOG, self.pages, self.model_calls), "checkpoint")
        self.assertEqual(self.store.get(JOB_ID)["checkpoint"]["step"], 1)
        self.assertEqual(self.store.get(JOB_ID)["job_id"], JOB_ID)

        resume = self.store.tick(JOB_ID, now=RESUME, worker_id="cursor-ridge")
        self.assertEqual(resume["action"], "WAKE")
        self.assertTrue(resume["invoke_model"])
        self.assertEqual(worker(self.store, resume, RESUME, self.pages, self.model_calls), "done")
        done = self.store.get(JOB_ID)
        self.assertEqual(done["status"], "DONE")
        self.assertEqual(done["result_address"], RESULT_ID)
        self.assertIn(RESULT_ID, self.pages)
        self.assertEqual(done["job_id"], JOB_ID)
        self.assertTrue(all(row.get("attempt_id") != JOB_ID for row in done["event_receipts"]))

        quiet = self.store.tick(JOB_ID, now=AFTER, worker_id="cursor-ridge")
        self.assertEqual(quiet["action"], "STOP")
        self.assertFalse(quiet["invoke_model"])
        self.assertEqual(quiet["reason"], "DONE")
        self.assertEqual(len(self.model_calls), 2)

        summary = run(self.tmp.name, deliver=False, worker_id="gh-watchdog")
        self.assertEqual(summary["process_model_invocations"], 0)
        self.assertFalse(summary["invoke_model"])
        self.assertEqual(summary["wake_count"], 0)
        self.assertEqual(len(self.model_calls), 2)

    def test_complete_refuses_carrier_theatre(self):
        self.store.upsert(fields(completion_predicate={"type": "status_done"}))
        wake = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="cursor-ridge")
        self.assertTrue(wake["invoke_model"])
        with self.assertRaises(JobError) as claimed:
            self.store.complete(
                JOB_ID,
                result={"kind": "claimed"},
                result_address=RESULT_ID,
                page_exists=lambda _ident: True,
            )
        self.assertEqual(claimed.exception.code, "NOT_DURABLE")
        with self.assertRaises(JobError) as missing:
            self.store.complete(
                JOB_ID,
                result={"durable": True},
                result_address=RESULT_ID,
                page_exists=lambda _ident: False,
            )
        self.assertEqual(missing.exception.code, "NOT_DURABLE")

    def test_checkpoint_auto_done_requires_durable_page(self):
        self.store.upsert(fields(checkpoint={"step": 2}))
        missing = self.store.tick(
            JOB_ID,
            now=WATCHDOG,
            worker_id="cursor-ridge",
            page_exists=lambda _ident: False,
        )
        self.assertEqual(missing["action"], "WAKE")
        self.assertTrue(missing["invoke_model"])
        self.assertNotEqual(self.store.get(JOB_ID)["status"], "DONE")

        unchanged = self.store.tick(
            JOB_ID,
            now=RESUME,
            worker_id="cursor-ridge",
            page_exists=lambda _ident: False,
        )
        self.assertEqual(unchanged["action"], "BACKOFF")
        self.assertFalse(unchanged["invoke_model"])

        retry_at = self.store.get(JOB_ID)["next_wake_at"]
        verified = self.store.tick(
            JOB_ID,
            now=retry_at,
            worker_id="cursor-ridge",
            page_exists=lambda ident: ident == RESULT_ID,
        )
        self.assertEqual(verified["action"], "STOP")
        self.assertEqual(verified["reason"], "DONE")
        self.assertFalse(verified["invoke_model"])
        self.assertEqual(self.store.get(JOB_ID)["status"], "DONE")

    def test_verified_auto_done_closes_lease_and_records_receipt(self):
        self.store.upsert(fields(checkpoint={"step": 2}))
        leased = self.store.tick(
            JOB_ID,
            now=WATCHDOG,
            worker_id="cursor-ridge",
            page_exists=lambda _ident: False,
        )
        self.assertEqual(leased["action"], "WAKE")
        self.assertIsNotNone(self.store.get(JOB_ID)["lease"])

        verified_at = "2026-08-22T04:20:01Z"
        done = self.store.tick(
            JOB_ID,
            now=verified_at,
            worker_id="durability-verifier",
            page_exists=lambda ident: ident == RESULT_ID,
        )
        self.assertEqual(done["action"], "STOP")
        self.assertEqual(done["reason"], "DONE")
        self.assertFalse(done["invoke_model"])
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["status"], "DONE")
        self.assertIsNone(stored["lease"])
        self.assertEqual(stored["completed_at"], verified_at)
        self.assertEqual(stored["updated_at"], verified_at)
        receipt = stored["event_receipts"][-1]
        self.assertEqual(receipt["event"], "auto_complete")
        self.assertEqual(receipt["worker_id"], "durability-verifier")
        self.assertEqual(receipt["result_address"], RESULT_ID)

    def test_auto_done_revalidates_after_reentrant_cancel(self):
        self.store.upsert(fields(checkpoint={"step": 2}))

        def cancel_during_probe(_ident):
            self.store.cancel(JOB_ID, reason="owner wins")
            self.assertEqual(self.store.get(JOB_ID)["status"], "CANCELLED")
            return True

        tick = self.store.tick(
            JOB_ID,
            now=WATCHDOG,
            worker_id="durability-verifier",
            page_exists=cancel_during_probe,
        )
        self.assertEqual(tick["action"], "STOP")
        self.assertEqual(tick["reason"], "CANCELLED")
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["status"], "CANCELLED")
        self.assertEqual(stored["cancel_reason"], "owner wins")
        self.assertEqual([r for r in stored["event_receipts"] if r.get("event") == "auto_complete"], [])
        self.assertEqual(len([r for r in stored["event_receipts"] if r.get("event") == "cancel"]), 1)

    def test_complete_revalidates_after_reentrant_cancel(self):
        self.store.upsert(fields(checkpoint={"step": 2}))

        def cancel_during_probe(_ident):
            self.store.cancel(JOB_ID, reason="owner wins")
            return True

        with self.assertRaises(JobError) as conflict:
            self.store.complete(
                JOB_ID,
                result={"durable": True, "kind": "page", "step": 2},
                result_address=RESULT_ID,
                page_exists=cancel_during_probe,
                now=WATCHDOG,
            )
        self.assertEqual(conflict.exception.code, "TERMINAL")
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["status"], "CANCELLED")
        self.assertNotIn("result", stored)
        self.assertEqual([r for r in stored["event_receipts"] if r.get("event") == "complete"], [])

    def test_durability_callback_failure_is_mutation_free_and_unlocks(self):
        self.store.upsert(fields(checkpoint={"step": 2}))
        before = self.store.path_for(JOB_ID).read_bytes()

        def failed_probe(_ident):
            raise RuntimeError("truth source unavailable")

        with self.assertRaises(RuntimeError):
            self.store.tick(JOB_ID, now=WATCHDOG, page_exists=failed_probe)
        self.assertEqual(self.store.path_for(JOB_ID).read_bytes(), before)
        cancelled = self.store.cancel(JOB_ID, reason="lock was released")
        self.assertEqual(cancelled["state"], "CANCELLED")

    def test_tick_retries_exact_snapshot_after_nonterminal_probe_mutation(self):
        self.store.upsert(fields(checkpoint={"step": 2}))
        calls = []

        def mutating_probe(_ident):
            calls.append(len(calls) + 1)
            if len(calls) == 1:
                self.store.append_receipt(JOB_ID, {
                    "attempt_id": "probe-observation-0001",
                    "event": "observation",
                    "ts": WATCHDOG,
                })
            return True

        tick = self.store.tick(JOB_ID, now=WATCHDOG, page_exists=mutating_probe)
        self.assertEqual(calls, [1, 2])
        self.assertEqual(tick["reason"], "DONE")
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["status"], "DONE")
        self.assertEqual(len([
            r for r in stored["event_receipts"]
            if r.get("attempt_id") == "probe-observation-0001"
        ]), 1)
        self.assertEqual(len([r for r in stored["event_receipts"] if r.get("event") == "auto_complete"]), 1)

    def test_same_holder_live_lease_does_not_mint_or_backoff(self):
        self.store.upsert(fields())
        first = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="cursor-ridge")
        original = self.store.get(JOB_ID)
        second = self.store.tick(
            JOB_ID,
            now="2026-08-22T04:20:01Z",
            worker_id="cursor-ridge",
        )
        self.assertEqual(second["action"], "STOP")
        self.assertEqual(second["reason"], "LEASE_HELD")
        self.assertFalse(second["invoke_model"])
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["lease"], original["lease"])
        self.assertEqual(stored["attempt_count"], 1)
        self.assertEqual(len([r for r in stored["event_receipts"] if r.get("event") == "wake"]), 1)
        self.assertEqual(first["attempt_id"], stored["event_receipts"][-1]["attempt_id"])

    def test_stale_checkpoint_tokens_cannot_clear_new_live_lease(self):
        self.store.upsert(fields())
        first = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="same-worker")
        backoff = self.store.tick(JOB_ID, now=RESUME, worker_id="same-worker")
        self.assertEqual(backoff["action"], "BACKOFF")
        retry_at = self.store.get(JOB_ID)["next_wake_at"]
        second = self.store.tick(JOB_ID, now=retry_at, worker_id="same-worker")
        self.assertEqual(second["action"], "WAKE")
        before = self.store.get(JOB_ID)

        with self.assertRaises(JobError) as stale:
            self.store.checkpoint(
                JOB_ID,
                {"step": 99},
                attempt_id=first["attempt_id"],
                lease_id=first["lease_id"],
                worker_id="same-worker",
                now=retry_at,
            )
        self.assertEqual(stale.exception.code, "STALE_ATTEMPT")
        self.assertEqual(self.store.get(JOB_ID), before)

    def test_checkpoint_tokens_cannot_overwrite_same_lease_checkpoint_churn(self):
        self.store.upsert(fields())
        wake = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="same-worker")
        self.store.upsert(fields(checkpoint={"step": 42}))
        before = self.store.get(JOB_ID)
        self.assertEqual(before["status"], "LEASED")
        self.assertEqual(before["lease"]["lease_id"], wake["lease_id"])

        with self.assertRaises(JobError) as stale:
            self.store.checkpoint(
                JOB_ID,
                {"step": 1},
                attempt_id=wake["attempt_id"],
                lease_id=wake["lease_id"],
                worker_id="same-worker",
                now="2026-08-22T04:20:01Z",
            )
        self.assertEqual(stale.exception.code, "STALE_ATTEMPT")
        self.assertEqual(self.store.get(JOB_ID), before)

    def test_existing_bounded_budget_cannot_be_removed_or_raised(self):
        self.store.upsert(fields(tokens_used=50, budget_tokens=50))
        with self.assertRaises(JobError) as unlimited:
            self.store.upsert(fields(tokens_used=50, budget_tokens=0))
        self.assertEqual(unlimited.exception.code, "SCHEMA")
        with self.assertRaises(JobError) as raised:
            self.store.upsert(fields(tokens_used=50, budget_tokens=51))
        self.assertEqual(raised.exception.code, "SCHEMA")
        tick = self.store.tick(JOB_ID, now=WATCHDOG)
        self.assertEqual(tick["action"], "STOP")
        self.assertEqual(tick["reason"], "BUDGET")
        self.assertEqual(self.store.get(JOB_ID)["status"], "EXHAUSTED")

    def test_new_job_cannot_request_unlimited_zero_budget(self):
        with self.assertRaises(JobError) as unlimited:
            self.store.upsert(fields(tokens_used=999999, budget_tokens=0))
        self.assertEqual(unlimited.exception.code, "SCHEMA")
        self.assertFalse(self.store.path_for(JOB_ID).exists())

    def test_invalid_checkpoint_now_is_rejected_before_lease_logic(self):
        self.store.upsert(fields())
        wake = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="lease-owner")
        before = self.store.path_for(JOB_ID).read_bytes()
        with self.assertRaises(JobError) as invalid:
            self.store.checkpoint(
                JOB_ID,
                {"step": 1},
                attempt_id=wake["attempt_id"],
                lease_id=wake["lease_id"],
                worker_id="other-worker",
                now="not-a-time",
            )
        self.assertEqual(invalid.exception.code, "SCHEMA")
        self.assertEqual(self.store.path_for(JOB_ID).read_bytes(), before)

    def test_exact_complete_retry_is_idempotent(self):
        self.store.upsert(fields(checkpoint={"step": 2}))
        result = {"durable": True, "kind": "page", "step": 2}
        first = self.store.complete(
            JOB_ID,
            result=result,
            result_address=RESULT_ID,
            page_exists=lambda _ident: True,
            now=WATCHDOG,
        )
        before = self.store.get(JOB_ID)
        second = self.store.complete(
            JOB_ID,
            result=result,
            result_address=RESULT_ID,
            page_exists=lambda _ident: (_ for _ in ()).throw(AssertionError("retry must not re-probe")),
            now=RESUME,
        )
        after = self.store.get(JOB_ID)
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(after, before)
        self.assertEqual(len([r for r in after["event_receipts"] if r.get("event") == "complete"]), 1)
        with self.assertRaises(JobError) as conflicting:
            self.store.complete(
                JOB_ID,
                result={"durable": True, "kind": "page", "step": 99},
                result_address=RESULT_ID,
                page_exists=lambda _ident: True,
                now=RESUME,
            )
        self.assertEqual(conflicting.exception.code, "TERMINAL")

    def test_complete_retries_exact_snapshot_after_nonterminal_probe_mutation(self):
        self.store.upsert(fields(checkpoint={"step": 2}))
        calls = []

        def mutating_probe(_ident):
            calls.append(len(calls) + 1)
            if len(calls) == 1:
                self.store.append_receipt(JOB_ID, {
                    "attempt_id": "complete-observation-0001",
                    "event": "observation",
                    "ts": WATCHDOG,
                })
            return True

        completed = self.store.complete(
            JOB_ID,
            result={"durable": True, "kind": "page", "step": 2},
            result_address=RESULT_ID,
            page_exists=mutating_probe,
            now=WATCHDOG,
        )
        self.assertEqual(calls, [1, 2])
        self.assertEqual(completed["state"], "DONE")
        stored = self.store.get(JOB_ID)
        self.assertEqual(len([
            r for r in stored["event_receipts"]
            if r.get("attempt_id") == "complete-observation-0001"
        ]), 1)
        self.assertEqual(len([r for r in stored["event_receipts"] if r.get("event") == "complete"]), 1)

    def test_complete_bounded_probe_churn_returns_conflict_without_stale_write(self):
        self.store.upsert(fields(checkpoint={"step": 2}))
        calls = []

        def churning_probe(_ident):
            calls.append(len(calls) + 1)
            self.store.append_receipt(JOB_ID, {
                "attempt_id": "churn-observation-%04d" % len(calls),
                "event": "observation",
                "ts": WATCHDOG,
            })
            return True

        with self.assertRaises(JobError) as conflict:
            self.store.complete(
                JOB_ID,
                result={"durable": True, "kind": "page", "step": 2},
                result_address=RESULT_ID,
                page_exists=churning_probe,
                now=WATCHDOG,
            )
        self.assertEqual(conflict.exception.code, "CONFLICT")
        self.assertEqual(calls, [1, 2, 3, 4])
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["status"], "OPEN")
        self.assertEqual(len([r for r in stored["event_receipts"] if r.get("event") == "observation"]), 4)
        self.assertEqual([r for r in stored["event_receipts"] if r.get("event") == "complete"], [])

    def test_two_store_ticks_serialize_one_wake(self):
        self.store.upsert(fields())
        other = JobStore(self.tmp.name)
        barrier = threading.Barrier(2)

        def tick(store, worker_id):
            barrier.wait()
            return store.tick(JOB_ID, now=WATCHDOG, worker_id=worker_id)

        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(lambda args: tick(*args), [(self.store, "worker-a"), (other, "worker-b")]))
        self.assertEqual(sum(row.get("action") == "WAKE" for row in rows), 1)
        self.assertEqual(sum(row.get("reason") == "LEASE_HELD" for row in rows), 1)
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["attempt_count"], 1)
        self.assertEqual(len([r for r in stored["event_receipts"] if r.get("event") == "wake"]), 1)

    def test_two_process_ticks_serialize_one_wake(self):
        self.store.upsert(fields())
        ctx = multiprocessing.get_context()
        barrier = ctx.Barrier(2)
        queue = ctx.Queue()
        processes = [
            ctx.Process(target=_process_tick, args=(self.tmp.name, barrier, queue, "process-a")),
            ctx.Process(target=_process_tick, args=(self.tmp.name, barrier, queue, "process-b")),
        ]
        for process in processes:
            process.start()
        rows = [queue.get(timeout=5) for _ in processes]
        for process in processes:
            process.join(timeout=5)
            self.assertEqual(process.exitcode, 0)
        self.assertTrue(all("result" in row for row in rows), rows)
        results = [row["result"] for row in rows]
        self.assertEqual(sum(row.get("action") == "WAKE" for row in results), 1)
        self.assertEqual(sum(row.get("reason") == "LEASE_HELD" for row in results), 1)
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["attempt_count"], 1)
        self.assertEqual(len([r for r in stored["event_receipts"] if r.get("event") == "wake"]), 1)

    def test_process_lock_blocks_second_mutator_until_transaction_releases(self):
        self.store.upsert(fields())
        ctx = multiprocessing.get_context()
        entered = ctx.Event()
        release = ctx.Event()
        started = ctx.Event()
        finished = ctx.Event()
        queue = ctx.Queue()
        holder = ctx.Process(target=_process_hold_transaction, args=(self.tmp.name, entered, release))
        canceller = ctx.Process(target=_process_cancel, args=(self.tmp.name, started, finished, queue))
        holder.start()
        try:
            self.assertTrue(entered.wait(timeout=5))
            canceller.start()
            self.assertTrue(started.wait(timeout=5))
            self.assertFalse(finished.wait(timeout=0.2))
            release.set()
            self.assertTrue(finished.wait(timeout=5))
            row = queue.get(timeout=5)
            self.assertIn("result", row, row)
            self.assertEqual(row["result"]["state"], "CANCELLED")
        finally:
            release.set()
            holder.join(timeout=5)
            if canceller.pid is not None:
                canceller.join(timeout=5)
        self.assertEqual(holder.exitcode, 0)
        self.assertEqual(canceller.exitcode, 0)
        self.assertEqual(self.store.get(JOB_ID)["status"], "CANCELLED")

    def test_cross_store_complete_cancel_has_one_terminal_winner(self):
        self.store.upsert(fields(checkpoint={"step": 2}))
        other = JobStore(self.tmp.name)
        entered = threading.Event()
        release = threading.Event()

        def blocked_complete():
            def probe(_ident):
                entered.set()
                self.assertTrue(release.wait(timeout=2))
                return True
            try:
                return self.store.complete(
                    JOB_ID,
                    result={"durable": True, "kind": "page", "step": 2},
                    result_address=RESULT_ID,
                    page_exists=probe,
                    now=WATCHDOG,
                )
            except JobError as exc:
                return exc

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(blocked_complete)
            self.assertTrue(entered.wait(timeout=2))
            cancelled = other.cancel(JOB_ID, reason="cancel wins")
            release.set()
            completion = future.result(timeout=2)
        self.assertEqual(cancelled["state"], "CANCELLED")
        self.assertIsInstance(completion, JobError)
        self.assertEqual(completion.code, "TERMINAL")
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["status"], "CANCELLED")
        self.assertEqual(len([r for r in stored["event_receipts"] if r.get("event") == "cancel"]), 1)
        self.assertEqual([r for r in stored["event_receipts"] if r.get("event") == "complete"], [])

    def test_cross_store_cancel_cannot_overwrite_completed_winner(self):
        self.store.upsert(fields(checkpoint={"step": 2}))
        other = JobStore(self.tmp.name)
        completed = self.store.complete(
            JOB_ID,
            result={"durable": True, "kind": "page", "step": 2},
            result_address=RESULT_ID,
            page_exists=lambda _ident: True,
            now=WATCHDOG,
        )
        self.assertEqual(completed["state"], "DONE")
        with self.assertRaises(JobError) as cancelled:
            other.cancel(JOB_ID, reason="too late")
        self.assertEqual(cancelled.exception.code, "TERMINAL")
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["status"], "DONE")
        self.assertEqual(len([r for r in stored["event_receipts"] if r.get("event") == "complete"]), 1)
        self.assertEqual([r for r in stored["event_receipts"] if r.get("event") == "cancel"], [])

    def test_tick_never_rewrites_terminal_state(self):
        self.store.upsert(fields(checkpoint={"step": 2}))
        self.store.cancel(JOB_ID, reason="owner stopped it")
        cancelled = self.store.tick(
            JOB_ID,
            now=WATCHDOG,
            page_exists=lambda _ident: True,
        )
        self.assertEqual(cancelled["action"], "STOP")
        self.assertEqual(cancelled["reason"], "CANCELLED")
        self.assertEqual(self.store.get(JOB_ID)["status"], "CANCELLED")
        with self.assertRaises(JobError) as cancelled_complete:
            self.store.complete(
                JOB_ID,
                result={"durable": True, "kind": "page"},
                result_address=RESULT_ID,
                page_exists=lambda _ident: True,
            )
        self.assertEqual(cancelled_complete.exception.code, "TERMINAL")
        with self.assertRaises(JobError) as cancelled_again:
            self.store.cancel(JOB_ID, reason="second cancel")
        self.assertEqual(cancelled_again.exception.code, "TERMINAL")
        with self.assertRaises(JobError) as cancelled_blocker:
            self.store.record_blocker(JOB_ID, "external_authority", "too late")
        self.assertEqual(cancelled_blocker.exception.code, "TERMINAL")

        exhausted_id = JOB_ID + "-exhausted"
        exhausted_result = RESULT_ID + "-exhausted"
        self.store.upsert(fields(
            job_id=exhausted_id,
            result_address=exhausted_result,
            checkpoint={"step": 2},
            deadline=T0,
        ))
        first = self.store.tick(
            exhausted_id,
            now=WATCHDOG,
            page_exists=lambda _ident: False,
        )
        self.assertEqual(first["action"], "STOP")
        self.assertEqual(self.store.get(exhausted_id)["status"], "EXHAUSTED")
        still_exhausted = self.store.tick(
            exhausted_id,
            now=RESUME,
            page_exists=lambda _ident: True,
        )
        self.assertEqual(still_exhausted["action"], "STOP")
        self.assertEqual(still_exhausted["reason"], "EXHAUSTED")
        self.assertEqual(self.store.get(exhausted_id)["status"], "EXHAUSTED")
        with self.assertRaises(JobError) as exhausted_complete:
            self.store.complete(
                exhausted_id,
                result={"durable": True, "kind": "page"},
                result_address=exhausted_result,
                page_exists=lambda _ident: True,
            )
        self.assertEqual(exhausted_complete.exception.code, "TERMINAL")
        with self.assertRaises(JobError) as exhausted_cancel:
            self.store.cancel(exhausted_id, reason="too late")
        self.assertEqual(exhausted_cancel.exception.code, "TERMINAL")
        with self.assertRaises(JobError) as exhausted_blocker:
            self.store.record_blocker(exhausted_id, "external_authority", "too late")
        self.assertEqual(exhausted_blocker.exception.code, "TERMINAL")

        done_id = JOB_ID + "-done"
        done_result = RESULT_ID + "-done"
        self.store.upsert(fields(
            job_id=done_id,
            result_address=done_result,
            checkpoint={"step": 2},
        ))
        done = self.store.tick(
            done_id,
            now=WATCHDOG,
            page_exists=lambda ident: ident == done_result,
        )
        self.assertEqual(done["reason"], "DONE")
        with self.assertRaises(JobError) as done_complete:
            self.store.complete(
                done_id,
                result={"durable": True, "kind": "page"},
                result_address=done_result,
                page_exists=lambda _ident: True,
            )
        self.assertEqual(done_complete.exception.code, "TERMINAL")
        with self.assertRaises(JobError) as done_cancel:
            self.store.cancel(done_id, reason="too late")
        self.assertEqual(done_cancel.exception.code, "TERMINAL")
        with self.assertRaises(JobError) as done_blocker:
            self.store.record_blocker(done_id, "external_authority", "too late")
        self.assertEqual(done_blocker.exception.code, "TERMINAL")

    def test_audit_receipts_cannot_forge_state_or_regress_terminal_time(self):
        self.store.upsert(fields())
        self.store.cancel(JOB_ID, reason="terminal")
        before = self.store.get(JOB_ID)
        with self.assertRaises(JobError) as forged:
            self.store.append_receipt(JOB_ID, {
                "attempt_id": JOB_ID + "-a99",
                "event": "wake",
                "ts": "not-an-iso-time",
                "lease_id": "lease-forged-0001",
            })
        self.assertEqual(forged.exception.code, "SCHEMA")
        self.assertEqual(self.store.get(JOB_ID), before)

        with self.assertRaises(JobError) as invalid_time:
            self.store.append_receipt(JOB_ID, {
                "attempt_id": "observation-terminal-0001",
                "event": "observation",
                "ts": "not-an-iso-time",
            })
        self.assertEqual(invalid_time.exception.code, "SCHEMA")
        self.assertEqual(self.store.get(JOB_ID), before)

        appended = self.store.append_receipt(JOB_ID, {
            "attempt_id": "observation-terminal-0001",
            "event": "observation",
            "ts": RESUME,
        })
        after = self.store.get(JOB_ID)
        self.assertFalse(appended["idempotent"])
        self.assertEqual(after["status"], "CANCELLED")
        self.assertEqual(after["updated_at"], before["updated_at"])
        replay = self.store.append_receipt(JOB_ID, {
            "attempt_id": "observation-terminal-0001",
            "event": "observation",
            "ts": RESUME,
        })
        self.assertTrue(replay["idempotent"])
        self.assertEqual(self.store.get(JOB_ID), after)

    def test_unchanged_checkpoint_does_not_burn_a_model(self):
        self.store.upsert(fields())
        first = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="cursor-ridge")
        self.assertTrue(first["invoke_model"])
        second = self.store.tick(JOB_ID, now=RESUME, worker_id="cursor-ridge")
        self.assertEqual(second["action"], "BACKOFF")
        self.assertFalse(second["invoke_model"])
        self.assertEqual(second["reason"], "UNCHANGED_CHECKPOINT")

    def test_unchanged_blocker_stops_without_model(self):
        self.store.upsert(fields())
        self.store.record_blocker(JOB_ID, "external_authority", "need a file uploaded")
        tick = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="cursor-ridge")
        self.assertEqual(tick["action"], "STOP")
        self.assertFalse(tick["invoke_model"])
        self.assertEqual(tick["reason"], "BLOCKED_UNCHANGED")
        again = self.store.tick(JOB_ID, now=RESUME, worker_id="cursor-ridge")
        self.assertFalse(again["invoke_model"])
        self.assertEqual(again["reason"], "BLOCKED_UNCHANGED")

    def test_foreign_lease_is_not_a_model_call(self):
        self.store.upsert(fields())
        held = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="owner")
        self.assertTrue(held["invoke_model"])
        other = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="peer")
        self.assertEqual(other["action"], "STOP")
        self.assertFalse(other["invoke_model"])
        self.assertEqual(other["reason"], "LEASE_HELD")

    def test_cursor_adapter_does_not_claim_missing_doors(self):
        paths = claimed_paths()
        self.assertTrue(paths["claimed"]["slack_cursor_app"]["measured"])
        self.assertTrue(paths["claimed"]["subscribe_timer"]["measured"])
        self.assertFalse(paths["unmeasured"]["named_idle_bc_resume"]["measured"])
        self.assertFalse(paths["unmeasured"]["claude_slack_app"]["claimed"])
        self.assertTrue(should_ring_issue_1316("cursor-desktop grok bot"))
        self.assertFalse(should_ring_issue_1316("cursor-slack"))
        payload = ntfy_payload({"job_id": JOB_ID, "owner_claim": "RIDGE", "harness": "cursor-slack"}, JOB_ID + "-a01")
        self.assertEqual(payload["job_id"], JOB_ID)
        self.assertEqual(payload["id"], JOB_ID)
        self.assertEqual(payload["attempt_id"], JOB_ID + "-a01")
        self.assertNotEqual(payload["attempt_id"], payload["id"])


class FakeDeliver:
    def __init__(self, status=200):
        self.status = status
        self.calls = []

    def __call__(self, url, payload):
        self.calls.append({"url": url, "payload": payload})
        return {"status": self.status, "body": "{}"}


class SchedulerDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wake-jobs-")
        self.store = JobStore(self.tmp.name)
        self.pages = set()
        self.http = FakeDeliver()

    def tearDown(self):
        self.tmp.cleanup()

    def test_unchanged_checkpoint_wakes_after_backoff(self):
        self.store.upsert(fields())
        first = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="cursor-ridge")
        self.assertEqual(first["action"], "WAKE")
        second = self.store.tick(JOB_ID, now=RESUME, worker_id="cursor-ridge")
        self.assertEqual(second["action"], "BACKOFF")
        self.assertFalse(second["invoke_model"])
        due = self.store.get(JOB_ID)["next_wake_at"]
        third = self.store.tick(JOB_ID, now=due, worker_id="cursor-ridge")
        self.assertEqual(third["action"], "WAKE")
        self.assertTrue(third["invoke_model"])
        self.assertNotEqual(third["attempt_id"], first["attempt_id"])

    def test_upsert_cannot_set_done_or_lower_tokens(self):
        self.store.upsert(fields())
        with self.assertRaises(JobError) as done:
            self.store.upsert(fields(status="DONE"))
        self.assertEqual(done.exception.code, "SCHEMA")
        self.store.upsert(fields(tokens_used=10))
        with self.assertRaises(JobError) as down:
            self.store.upsert(fields(tokens_used=1))
        self.assertEqual(down.exception.code, "SCHEMA")
        wake = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="cursor-ridge")
        with self.assertRaises(JobError) as ckpt:
            self.store.checkpoint(
                JOB_ID,
                {"step": 1},
                attempt_id=wake["attempt_id"],
                lease_id=wake["lease_id"],
                tokens_used=0,
                worker_id="cursor-ridge",
                now=WATCHDOG,
            )
        self.assertEqual(ckpt.exception.code, "SCHEMA")

    def test_scheduler_deliver_separate_callback_then_quiet(self):
        self.store.upsert(fields())
        missed = run(self.tmp.name, deliver=True, worker_id="gh-watchdog", now=T0, http=self.http)
        self.assertEqual(missed["delivered_count"], 0)
        self.assertEqual(missed["wake_count"], 0)
        self.assertEqual(missed["process_model_invocations"], 0)
        self.assertEqual(self.http.calls, [])

        first = run(self.tmp.name, deliver=True, worker_id="gh-watchdog", now=WATCHDOG, http=self.http)
        self.assertEqual(first["wake_count"], 1)
        self.assertEqual(first["delivered_count"], 1)
        self.assertEqual(first["process_model_invocations"], 0)
        mail = first["deliveries"][0]
        self.assertEqual(mail["state"], "MAIL")
        self.assertEqual(mail["job_id"], JOB_ID)
        packed = json.loads(self.http.calls[0]["payload"])
        self.assertEqual(packed["id"], JOB_ID)
        self.assertEqual(packed["job_id"], JOB_ID)
        self.assertNotEqual(packed["attempt_id"], packed["id"])

        skipped = run(self.tmp.name, deliver=True, worker_id="gh-watchdog", now=RESUME, http=self.http)
        self.assertEqual(skipped["wake_count"], 0)
        self.assertEqual(skipped["backoff_count"], 1)
        self.assertEqual(skipped["delivered_count"], 0)
        self.assertEqual(len(self.http.calls), 1)

        retry_at = self.store.get(JOB_ID)["next_wake_at"]
        retry = run(self.tmp.name, deliver=True, worker_id="gh-watchdog", now=retry_at, http=self.http)
        self.assertEqual(retry["wake_count"], 1)
        self.assertEqual(retry["delivered_count"], 1)
        self.assertEqual(len(self.http.calls), 2)

        ckpt_now = retry_at
        claimed = consume_delivery(self.store, retry["deliveries"][0], now=ckpt_now, pages=self.pages)
        self.assertEqual(claimed["state"], "CLAIMED")
        self.assertTrue(claimed["invoke_model"])
        ack = finish_delivery(self.store, retry["deliveries"][0], now=ckpt_now, pages=self.pages)
        self.assertEqual(ack["state"], "CHECKPOINT")
        self.assertFalse(ack["invoke_model"])
        self.assertEqual(ack["step"], 1)
        self.assertEqual(ack["job_id"], JOB_ID)

        second = run(self.tmp.name, deliver=True, worker_id="gh-watchdog", now=ckpt_now, http=self.http)
        self.assertEqual(second["wake_count"], 1)
        self.assertEqual(second["delivered_count"], 1)
        done_now = ckpt_now
        claimed_done = consume_delivery(self.store, second["deliveries"][0], now=done_now, pages=self.pages)
        self.assertEqual(claimed_done["state"], "CLAIMED")
        done = finish_delivery(self.store, second["deliveries"][0], now=done_now, pages=self.pages)
        self.assertEqual(done["state"], "DONE")
        self.assertEqual(self.store.get(JOB_ID)["status"], "DONE")
        self.assertIn(RESULT_ID, self.pages)

        quiet = run(self.tmp.name, deliver=True, worker_id="gh-watchdog", now="2026-08-22T04:27:00Z", http=self.http)
        self.assertEqual(quiet["wake_count"], 0)
        self.assertEqual(quiet["delivered_count"], 0)
        self.assertEqual(quiet["process_model_invocations"], 0)
        self.assertFalse(quiet["invoke_model"])
        self.assertEqual(len(self.http.calls), 3)

    def test_watchdog_delivery_receipt_replay_uses_stable_wake_time(self):
        self.store.upsert(fields())
        first = run(
            self.tmp.name,
            deliver=True,
            worker_id="gh-watchdog",
            now=WATCHDOG,
            http=self.http,
        )
        mail = first["deliveries"][0]
        stored = self.store.get(JOB_ID)
        delivered = [
            row for row in stored["event_receipts"]
            if row.get("event") == "deliver"
        ]
        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0]["ts"], WATCHDOG)

        replay = self.store.append_receipt(JOB_ID, {
            "attempt_id": first["jobs"][0]["attempt_id"],
            "event": "deliver",
            "ts": first["jobs"][0]["now"],
            "carrier": mail.get("state"),
            "host": mail.get("host"),
            "http_status": mail.get("http_status"),
            "id": JOB_ID,
        })
        self.assertTrue(replay["idempotent"])
        after = self.store.get(JOB_ID)
        self.assertEqual(len([
            row for row in after["event_receipts"]
            if row.get("event") == "deliver"
        ]), 1)

    def test_delivery_attempt_replay_advances_checkpoint_once(self):
        self.store.upsert(fields())
        wake = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="gh-watchdog")
        mail = {"state": "MAIL", "job_id": JOB_ID, "attempt_id": wake["attempt_id"]}

        first = consume_delivery(self.store, mail, now=WATCHDOG, pages=self.pages)
        second = consume_delivery(self.store, mail, now=WATCHDOG, pages=self.pages)

        self.assertEqual(first["state"], "CLAIMED")
        self.assertTrue(first["invoke_model"])
        self.assertEqual(second["state"], "REPLAY")
        self.assertFalse(second["invoke_model"])
        claimed_state = self.store.get(JOB_ID)
        self.assertEqual(claimed_state["checkpoint"], {"step": 0})
        self.assertEqual(claimed_state["status"], "LEASED")
        held = self.store.tick(JOB_ID, now="2026-08-22T04:20:01Z", worker_id="gh-watchdog")
        self.assertEqual(held["reason"], "LEASE_HELD")
        finished = finish_delivery(self.store, mail, now=WATCHDOG, pages=self.pages)
        self.assertEqual(finished["state"], "CHECKPOINT")
        self.assertFalse(finished["invoke_model"])
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["checkpoint"], {"step": 1})
        self.assertEqual(stored["status"], "OPEN")
        self.assertEqual(len([
            r for r in stored["event_receipts"]
            if r.get("attempt_id") == wake["attempt_id"] and r.get("event") == "delivery_claim"
        ]), 1)
        self.assertEqual(len([
            r for r in stored["event_receipts"]
            if r.get("attempt_id") == wake["attempt_id"] and r.get("event") == "ack"
        ]), 1)

    def test_max_length_job_id_generated_attempt_is_consumable(self):
        long_job = "j" * 80
        long_result = "r" * 80
        self.store.upsert(fields(job_id=long_job, result_address=long_result))
        wake = self.store.tick(long_job, now=WATCHDOG, worker_id="gh-watchdog")
        self.assertEqual(len(wake["attempt_id"]), 84)
        claimed = consume_delivery(
            self.store,
            {"state": "MAIL", "job_id": long_job, "attempt_id": wake["attempt_id"]},
            now=WATCHDOG,
            pages=self.pages,
        )
        self.assertEqual(claimed["state"], "CLAIMED")
        consumed = finish_delivery(
            self.store,
            {"state": "MAIL", "job_id": long_job, "attempt_id": wake["attempt_id"]},
            now=WATCHDOG,
            pages=self.pages,
        )
        self.assertEqual(consumed["state"], "CHECKPOINT")
        self.assertEqual(self.store.get(long_job)["checkpoint"], {"step": 1})

    def test_concurrent_delivery_replay_authorizes_one_model(self):
        self.store.upsert(fields())
        wake = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="gh-watchdog")
        mail = {"state": "MAIL", "job_id": JOB_ID, "attempt_id": wake["attempt_id"]}
        other = JobStore(self.tmp.name)
        barrier = threading.Barrier(2)

        def consume(store):
            barrier.wait()
            return consume_delivery(store, mail, now=WATCHDOG, pages=self.pages)

        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(consume, [self.store, other]))
        self.assertEqual(sum(row["state"] == "CLAIMED" for row in rows), 1)
        self.assertEqual(sum(row["state"] == "REPLAY" for row in rows), 1)
        self.assertEqual(sum(bool(row["invoke_model"]) for row in rows), 1)
        claimed_state = self.store.get(JOB_ID)
        self.assertEqual(claimed_state["checkpoint"], {"step": 0})
        finished = finish_delivery(self.store, mail, now=WATCHDOG, pages=self.pages)
        self.assertEqual(finished["state"], "CHECKPOINT")
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["checkpoint"], {"step": 1})
        self.assertEqual(len([
            r for r in stored["event_receipts"]
            if r.get("attempt_id") == wake["attempt_id"] and r.get("event") == "ack"
        ]), 1)

    def test_process_delivery_replay_authorizes_one_model(self):
        self.store.upsert(fields())
        wake = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="gh-watchdog")
        mail = {"state": "MAIL", "job_id": JOB_ID, "attempt_id": wake["attempt_id"]}
        ctx = multiprocessing.get_context()
        barrier = ctx.Barrier(2)
        queue = ctx.Queue()
        processes = [
            ctx.Process(target=_process_consume, args=(self.tmp.name, barrier, queue, mail)),
            ctx.Process(target=_process_consume, args=(self.tmp.name, barrier, queue, mail)),
        ]
        for process in processes:
            process.start()
        rows = [queue.get(timeout=5) for _ in processes]
        for process in processes:
            process.join(timeout=5)
            self.assertEqual(process.exitcode, 0)
        self.assertTrue(all("result" in row for row in rows), rows)
        results = [row["result"] for row in rows]
        self.assertEqual(sum(row["state"] == "CLAIMED" for row in results), 1)
        self.assertEqual(sum(row["state"] == "REPLAY" for row in results), 1)
        self.assertEqual(sum(bool(row["invoke_model"]) for row in results), 1)
        claimed_state = self.store.get(JOB_ID)
        self.assertEqual(claimed_state["checkpoint"], {"step": 0})
        finished = finish_delivery(self.store, mail, now=WATCHDOG, pages=self.pages)
        self.assertEqual(finished["state"], "CHECKPOINT")
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["checkpoint"], {"step": 1})
        self.assertEqual(len([
            r for r in stored["event_receipts"]
            if r.get("attempt_id") == wake["attempt_id"] and r.get("event") == "ack"
        ]), 1)

    def test_stale_unclaimed_attempt_cannot_mutate_new_lease(self):
        self.store.upsert(fields())
        first = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="gh-watchdog")
        before_expired = self.store.get(JOB_ID)
        expired = consume_delivery(
            self.store,
            {"state": "MAIL", "job_id": JOB_ID, "attempt_id": first["attempt_id"]},
            now=RESUME,
            pages=self.pages,
        )
        self.assertEqual(expired["state"], "STALE_ATTEMPT")
        self.assertFalse(expired["invoke_model"])
        self.assertEqual(self.store.get(JOB_ID), before_expired)

        backoff = self.store.tick(JOB_ID, now=RESUME, worker_id="gh-watchdog")
        self.assertEqual(backoff["action"], "BACKOFF")
        second = self.store.tick(
            JOB_ID,
            now=self.store.get(JOB_ID)["next_wake_at"],
            worker_id="gh-watchdog",
        )
        self.assertEqual(second["action"], "WAKE")
        before = self.store.get(JOB_ID)

        stale = consume_delivery(
            self.store,
            {"state": "MAIL", "job_id": JOB_ID, "attempt_id": first["attempt_id"]},
            now=RESUME,
            pages=self.pages,
        )
        self.assertEqual(stale["state"], "STALE_ATTEMPT")
        self.assertFalse(stale["invoke_model"])
        self.assertEqual(self.store.get(JOB_ID), before)

    def test_failed_durability_claim_recovers_without_advancing_past_predicate(self):
        self.store.upsert(fields(checkpoint={"step": 1}))
        first_wake = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="gh-watchdog")
        first_mail = {"state": "MAIL", "job_id": JOB_ID, "attempt_id": first_wake["attempt_id"]}
        claimed = consume_delivery(self.store, first_mail, now=WATCHDOG, pages=self.pages)
        self.assertEqual(claimed["state"], "CLAIMED")
        with self.assertRaises(JobError) as missing:
            finish_delivery(
                self.store,
                first_mail,
                now=WATCHDOG,
                pages=self.pages,
                page_exists=lambda _ident: False,
            )
        self.assertEqual(missing.exception.code, "NOT_DURABLE")
        failed = self.store.get(JOB_ID)
        self.assertEqual(failed["checkpoint"], {"step": 1})
        self.assertEqual(failed["status"], "LEASED")
        self.assertEqual(len([
            r for r in failed["event_receipts"]
            if r.get("attempt_id") == first_wake["attempt_id"] and r.get("event") == "delivery_claim"
        ]), 1)
        self.assertEqual([
            r for r in failed["event_receipts"]
            if r.get("attempt_id") == first_wake["attempt_id"] and r.get("event") in {"checkpoint", "ack"}
        ], [])

        replay = consume_delivery(self.store, first_mail, now=WATCHDOG, pages=self.pages)
        self.assertEqual(replay["state"], "REPLAY")
        self.assertFalse(replay["invoke_model"])
        self.assertEqual(self.store.get(JOB_ID), failed)

        backoff = self.store.tick(JOB_ID, now=RESUME, worker_id="gh-watchdog")
        self.assertEqual(backoff["action"], "BACKOFF")
        retry_at = self.store.get(JOB_ID)["next_wake_at"]
        second_wake = self.store.tick(JOB_ID, now=retry_at, worker_id="gh-watchdog")
        self.assertEqual(second_wake["action"], "WAKE")
        claimed_retry = consume_delivery(
            self.store,
            {"state": "MAIL", "job_id": JOB_ID, "attempt_id": second_wake["attempt_id"]},
            now=retry_at,
            pages=self.pages,
        )
        self.assertEqual(claimed_retry["state"], "CLAIMED")
        done = finish_delivery(
            self.store,
            {"state": "MAIL", "job_id": JOB_ID, "attempt_id": second_wake["attempt_id"]},
            now=retry_at,
            pages=self.pages,
            page_exists=lambda _ident: True,
        )
        self.assertEqual(done["state"], "DONE")
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["checkpoint"], {"step": 2})
        self.assertEqual(stored["status"], "DONE")
        self.assertEqual(len([r for r in stored["event_receipts"] if r.get("event") == "complete"]), 1)

    def test_satisfied_checkpoint_delivery_repairs_page_without_incrementing(self):
        self.store.upsert(fields(checkpoint={"step": 2}))
        wake = self.store.tick(
            JOB_ID,
            now=WATCHDOG,
            worker_id="gh-watchdog",
            page_exists=lambda _ident: False,
        )
        self.assertEqual(wake["action"], "WAKE")
        claimed = consume_delivery(
            self.store,
            {"state": "MAIL", "job_id": JOB_ID, "attempt_id": wake["attempt_id"]},
            now=WATCHDOG,
            pages=self.pages,
        )
        self.assertEqual(claimed["state"], "CLAIMED")
        done = finish_delivery(
            self.store,
            {"state": "MAIL", "job_id": JOB_ID, "attempt_id": wake["attempt_id"]},
            now=WATCHDOG,
            pages=self.pages,
            page_exists=lambda _ident: True,
        )
        self.assertEqual(done["state"], "DONE")
        stored = self.store.get(JOB_ID)
        self.assertEqual(stored["checkpoint"], {"step": 2})
        self.assertEqual(stored["status"], "DONE")

    def test_replayed_old_attempt_does_not_disturb_new_attempt_or_done(self):
        self.store.upsert(fields())
        first_wake = self.store.tick(JOB_ID, now=WATCHDOG, worker_id="gh-watchdog")
        first_mail = {"state": "MAIL", "job_id": JOB_ID, "attempt_id": first_wake["attempt_id"]}
        first_claim = consume_delivery(self.store, first_mail, now=WATCHDOG, pages=self.pages)
        self.assertEqual(first_claim["step"], 1)
        first = finish_delivery(self.store, first_mail, now=WATCHDOG, pages=self.pages)
        self.assertEqual(first["state"], "CHECKPOINT")

        second_wake = self.store.tick(
            JOB_ID,
            now="2026-08-22T04:20:01Z",
            worker_id="gh-watchdog",
        )
        before_replay = self.store.get(JOB_ID)
        replay = consume_delivery(self.store, first_mail, now="2026-08-22T04:20:01Z", pages=self.pages)
        self.assertEqual(replay["state"], "REPLAY")
        self.assertFalse(replay["invoke_model"])
        self.assertEqual(self.store.get(JOB_ID), before_replay)

        claimed_done = consume_delivery(
            self.store,
            {"state": "MAIL", "job_id": JOB_ID, "attempt_id": second_wake["attempt_id"]},
            now="2026-08-22T04:20:01Z",
            pages=self.pages,
        )
        self.assertEqual(claimed_done["state"], "CLAIMED")
        done = finish_delivery(
            self.store,
            {"state": "MAIL", "job_id": JOB_ID, "attempt_id": second_wake["attempt_id"]},
            now="2026-08-22T04:20:01Z",
            pages=self.pages,
        )
        self.assertEqual(done["state"], "DONE")
        terminal = self.store.get(JOB_ID)
        replay_after_done = consume_delivery(
            self.store,
            first_mail,
            now="2026-08-22T04:20:02Z",
            pages=self.pages,
        )
        self.assertEqual(replay_after_done["state"], "REPLAY")
        self.assertFalse(replay_after_done["invoke_model"])
        self.assertEqual(self.store.get(JOB_ID), terminal)


class McpJobToolTests(unittest.TestCase):
    def test_tick_job_tool_never_sets_error_on_stop(self):
        tmp = tempfile.TemporaryDirectory(prefix="wake-mcp-")
        try:
            store = JobStore(tmp.name)
            store.upsert(fields(next_wake_at="2099-01-01T00:00:00Z", deadline="2099-12-31T00:00:00Z"))
            server = MCPServer(jobs=store)
            listed = server.dispatch("tools/list", {})
            names = [row["name"] for row in listed["tools"]]
            self.assertIn("tick_job", names)
            self.assertIn("upsert_job", names)
            rpc = server.handle({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "tick_job", "arguments": {"job_id": JOB_ID, "worker_id": "cursor-ridge"}},
            })
            data = rpc["result"]["structuredContent"]
            self.assertTrue(data["ok"])
            self.assertEqual(data["action"], "STOP")
            self.assertFalse(data["invoke_model"])
            self.assertFalse(rpc["result"]["isError"])
        finally:
            tmp.cleanup()

    def test_checkpoint_tool_requires_current_attempt_and_lease(self):
        tmp = tempfile.TemporaryDirectory(prefix="wake-mcp-")
        try:
            store = JobStore(tmp.name)
            store.upsert(fields(
                next_wake_at="2000-01-01T00:00:00Z",
                deadline="2099-12-31T00:00:00Z",
            ))
            now = utc_now()
            wake = store.tick(JOB_ID, now=now, worker_id="mcp-worker")
            server = MCPServer(jobs=store)
            missing = server.handle({
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "checkpoint_job",
                    "arguments": {
                        "job_id": JOB_ID,
                        "checkpoint": {"step": 1},
                        "worker_id": "mcp-worker",
                    },
                },
            })
            self.assertTrue(missing["result"]["isError"])
            self.assertEqual(missing["result"]["structuredContent"]["code"], "SCHEMA")

            accepted = server.handle({
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "checkpoint_job",
                    "arguments": {
                        "job_id": JOB_ID,
                        "checkpoint": {"step": 1},
                        "attempt_id": wake["attempt_id"],
                        "lease_id": wake["lease_id"],
                        "worker_id": "mcp-worker",
                    },
                },
            })
            self.assertFalse(accepted["result"]["isError"])
            self.assertEqual(accepted["result"]["structuredContent"]["state"], "OPEN")
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    raise SystemExit(unittest.main())
