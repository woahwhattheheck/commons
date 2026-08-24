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
import tempfile
import unittest

from harness_wake.callback import consume_delivery
from harness_wake.cursor_adapter import claimed_paths, ntfy_payload, should_ring_issue_1316
from harness_wake.watchdog import run
from independent_commons_mcp.jobs import JobError, JobStore
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
    store.checkpoint(job["job_id"], {"step": step}, next_wake_at=now, worker_id=worker_id, now=now)
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
        self.store.tick(JOB_ID, now=WATCHDOG, worker_id="cursor-ridge")
        with self.assertRaises(JobError) as ckpt:
            self.store.checkpoint(JOB_ID, {"step": 1}, tokens_used=0, worker_id="cursor-ridge", now=WATCHDOG)
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

        ckpt_now = "2026-08-22T04:25:00Z"
        ack = consume_delivery(self.store, retry["deliveries"][0], now=ckpt_now, pages=self.pages)
        self.assertEqual(ack["state"], "CHECKPOINT")
        self.assertEqual(ack["step"], 1)
        self.assertEqual(ack["job_id"], JOB_ID)

        second = run(self.tmp.name, deliver=True, worker_id="gh-watchdog", now=ckpt_now, http=self.http)
        self.assertEqual(second["wake_count"], 1)
        self.assertEqual(second["delivered_count"], 1)
        done_now = "2026-08-22T04:26:00Z"
        done = consume_delivery(self.store, second["deliveries"][0], now=done_now, pages=self.pages)
        self.assertEqual(done["state"], "DONE")
        self.assertEqual(self.store.get(JOB_ID)["status"], "DONE")
        self.assertIn(RESULT_ID, self.pages)

        quiet = run(self.tmp.name, deliver=True, worker_id="gh-watchdog", now="2026-08-22T04:27:00Z", http=self.http)
        self.assertEqual(quiet["wake_count"], 0)
        self.assertEqual(quiet["delivered_count"], 0)
        self.assertEqual(quiet["process_model_invocations"], 0)
        self.assertFalse(quiet["invoke_model"])
        self.assertEqual(len(self.http.calls), 3)


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


if __name__ == "__main__":
    raise SystemExit(unittest.main())
