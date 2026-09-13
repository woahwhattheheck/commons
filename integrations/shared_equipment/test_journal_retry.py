"""Caller-driven retry proofs: temporary SQLite only, no provider traffic."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from email.utils import formatdate
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from integrations.gemini_slack.peer_tool_gateway import ToolCallStore


class JournalRetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "calls.sqlite3"
        self.now = 1_800_000_000.0
        self.store = self.new_store()

    def new_store(self):
        store = ToolCallStore(self.path, clock=lambda: self.now)
        self.addCleanup(store.close)
        return store

    @staticmethod
    def throttle(**overrides):
        return {"ok": False, "status": 429, "error": "ratelimited",
                "uncertain": False, "retry_after": 10, **overrides}

    def call(self, runner, *, store=None, name="slack_post_message", args=None):
        return (store or self.store).execute_journaled(
            "same-request", "same-call", name, {"text": "same"} if args is None else args,
            runner,
        )

    def snapshots(self):
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute(
                "SELECT attempt_number,phase,state,result_json,recorded_at,retry_at "
                "FROM tool_call_attempts ORDER BY attempt_number,phase"
            ).fetchall()

    def original(self):
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute("SELECT * FROM tool_calls").fetchone()

    def test_same_id_retries_after_deadline_and_preserves_first_receipt(self):
        calls = []
        def runner(name, args):
            calls.append((name, args))
            return self.throttle() if len(calls) == 1 else {"ok": True, "ts": "123.456"}
        first = self.call(runner)
        original, snapshots = self.original(), self.snapshots()
        self.now += 9.99
        self.assertEqual(self.call(runner), first)
        self.assertEqual(len(calls), 1)
        self.now += 0.01
        final = self.call(runner)
        self.assertEqual(final, {"ok": True, "ts": "123.456"})
        self.assertEqual(self.call(runner), final)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.original(), original)
        self.assertEqual(self.snapshots()[:2], snapshots)
        self.assertEqual([(r[0], r[1], r[2]) for r in self.snapshots()],
                         [(0, 0, "started"), (0, 1, "error"),
                          (1, 0, "started"), (1, 1, "completed")])

    def test_restart_preserves_deadline_not_a_fresh_delay(self):
        first = self.call(lambda *_: self.throttle())
        reopened = self.new_store()
        calls = []
        def runner(*_):
            calls.append(1)
            return {"ok": True}
        self.now += 8
        self.assertEqual(self.call(runner, store=reopened), first)
        self.now += 2
        self.assertEqual(self.call(runner, store=reopened), {"ok": True})
        self.assertEqual(calls, [1])

    def test_each_repeated_429_has_its_own_durable_deadline(self):
        self.call(lambda *_: self.throttle())
        self.now += 10
        self.call(lambda *_: self.throttle(retry_after=30))
        self.now += 29
        self.assertEqual(self.call(lambda *_: self.fail("early retry")), self.throttle(retry_after=30))
        self.now += 1
        self.assertEqual(self.call(lambda *_: {"ok": True}), {"ok": True})
        self.assertEqual(len(self.snapshots()), 6)

    def test_concurrent_stores_only_one_claims_due_retry(self):
        self.call(lambda *_: self.throttle())
        other = self.new_store()
        self.now += 10
        barrier = threading.Barrier(2)
        running, released, duplicate_returned = threading.Event(), threading.Event(), threading.Event()
        invocations = []
        def runner(*_):
            invocations.append(1)
            running.set()
            if not released.wait(5):
                raise RuntimeError("test release timed out")
            return {"ok": True}
        def caller(store):
            barrier.wait(timeout=5)
            result = self.call(runner, store=store)
            if result.get("uncertain"):
                duplicate_returned.set()
            return result
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(caller, store) for store in (self.store, other)]
            try:
                self.assertTrue(running.wait(5))
                self.assertTrue(duplicate_returned.wait(5))
                self.assertEqual(len(invocations), 1)
            finally:
                released.set()
            results = [future.result(timeout=5) for future in futures]
        self.assertEqual(sum(result.get("ok") is True for result in results), 1)
        self.assertEqual(len(self.snapshots()), 4)
        self.assertEqual(self.call(lambda *_: self.fail("duplicate effect")), {"ok": True})

    def test_changed_arguments_or_tool_never_claim_retry(self):
        self.call(lambda *_: self.throttle())
        self.now += 20
        for options in ({"args": {"text": "changed"}}, {"name": "slack_delete_message"}):
            with self.subTest(options=options):
                result = self.call(lambda *_: self.fail("conflicting retry"), **options)
                self.assertEqual(result["error"], "call_id_reused_with_different_arguments")
        self.assertEqual(len(self.snapshots()), 2)

    def test_arbitrary_errors_and_uncertain_429_remain_nonretryable(self):
        values = [
            {"ok": False, "status": 500, "uncertain": False, "retry_after": 1},
            {"ok": False, "error": "permission_denied", "uncertain": False},
            self.throttle(uncertain=True),
            {"ok": False, "status": 429, "retry_after": 1},
            self.throttle(uncertain="false"),
            {"ok": True, "status": 429, "uncertain": False, "retry_after": 1},
            {"ok": False, "uncertain": False, "data": self.throttle()},
            {"isError": True, "uncertain": False, "result": self.throttle(uncertain=True)},
        ]
        for i, value in enumerate(values):
            with self.subTest(value=value):
                result = self.store.execute_journaled("negative", str(i), "write", {}, lambda *_: value)
                self.now += 100
                replay = self.store.execute_journaled(
                    "negative", str(i), "write", {}, lambda *_: self.fail("unsafe retry"))
                self.assertEqual(replay, result)

    def test_nested_known_no_effect_429_and_local_deferral_are_retryable(self):
        for i, value in enumerate((
            {"isError": True, "uncertain": False, "result": self.throttle()},
            {"isError": True, "uncertain": False, "result": {
                "ok": False, "error": "ratelimited", "retry_after": "2"}},
            self.throttle(provider_contacted=False, deferral_reason="provider_cooldown"),
            self.throttle(provider_contacted=True),
        )):
            with self.subTest(value=value):
                self.store.execute_journaled("nested", str(i), "write", {}, lambda *_: value)
                self.now += 10
                result = self.store.execute_journaled("nested", str(i), "write", {}, lambda *_: {"ok": True})
                self.assertEqual(result, {"ok": True})

    def test_nested_uncertainty_globally_vetoes_outer_no_effect_429(self):
        cases = [self.throttle(retry_after=1, error_data={
            "uncertain": True, "code": "write_outcome_unknown"})]
        for key in ("result", "structuredContent", "error", "error_data"):
            for metadata in ({"uncertain": True}, {"code": "write_outcome_unknown"},
                             {"error": "write_outcome_unknown"}, {"uncertain": "false"}):
                cases.append(self.throttle(retry_after=1, **{key: metadata}))
        deep = {"uncertain": True}
        for _ in range(12):
            deep = {"error_data": deep}
        cases.append(self.throttle(retry_after=1, error_data=deep))
        for i, value in enumerate(cases):
            with self.subTest(value=value):
                result = self.store.execute_journaled("veto", str(i), "write", {}, lambda *_: value)
                self.now += 100
                replay = self.store.execute_journaled(
                    "veto", str(i), "write", {}, lambda *_: self.fail("nested ambiguous effect retried"))
                self.assertEqual(replay, result)
                with closing(sqlite3.connect(self.path)) as db:
                    attempts = db.execute(
                        "SELECT retry_at FROM tool_call_attempts WHERE request_id=? AND call_id=?",
                        ("veto", str(i)),
                    ).fetchall()
                self.assertEqual(attempts, [(None,), (None,)])

    def test_preexisting_due_attempt_still_obeys_nested_uncertainty_veto(self):
        value = self.throttle(retry_after=1, error_data={"uncertain": True})
        first = self.call(lambda *_: value)
        # Model an old journal that already assigned a deadline to this result.
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE tool_call_attempts SET retry_at=? WHERE phase=1", (self.now + 1,))
        snapshots = self.snapshots()
        self.now += 100
        self.assertEqual(self.call(lambda *_: self.fail("old ambiguous receipt retried")), first)
        self.assertEqual(self.snapshots(), snapshots)

    def test_http_date_and_absolute_deadlines(self):
        future = formatdate(self.now + 120, usegmt=True)
        self.call(lambda *_: self.throttle(retry_after=future))
        self.now += 119
        self.call(lambda *_: self.fail("HTTP date ignored"))
        self.now += 1
        self.assertEqual(self.call(lambda *_: {"ok": True}), {"ok": True})
        absolute = formatdate(self.now + 180, usegmt=True)
        self.store.execute_journaled("absolute", "id", "write", {},
                                    lambda *_: self.throttle(retry_after=2, retry_not_before=absolute))
        self.now += 179
        self.store.execute_journaled("absolute", "id", "write", {}, lambda *_: self.fail("absolute deadline ignored"))
        self.now += 1
        self.assertEqual(self.store.execute_journaled("absolute", "id", "write", {},
                                                    lambda *_: {"ok": True}), {"ok": True})

    def test_malformed_delay_uses_durable_sixty_second_fallback(self):
        for i, delay in enumerate((None, True, False, "garbage", -1, 0, float("nan"), float("inf"))):
            with self.subTest(delay=delay):
                result = self.store.execute_journaled("delay", str(i), "write", {},
                                                       lambda *_: self.throttle(retry_after=delay))
                self.now += 59
                replay = self.store.execute_journaled("delay", str(i), "write", {},
                                                     lambda *_: self.fail("tight retry"))
                self.assertEqual(json.dumps(replay, sort_keys=True), json.dumps(result, sort_keys=True))
                self.now += 1
                self.assertEqual(self.store.execute_journaled("delay", str(i), "write", {},
                                                              lambda *_: {"ok": True}), {"ok": True})

    def test_legacy_error_migrates_without_rewriting_original(self):
        raw = json.dumps(self.throttle(), separators=(",", ":"))
        digest = hashlib.sha256(b'{"text":"same"}').hexdigest()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO tool_calls VALUES(?,?,?,?,?,?,?)", (
                "same-request", "same-call", "slack_post_message", digest, "error", raw, self.now))
        original = self.original()
        self.now += 11
        self.assertEqual(self.call(lambda *_: {"ok": True}), {"ok": True})
        self.assertEqual(self.original(), original)
        self.assertEqual(self.snapshots()[0][3], raw)
        self.assertEqual(len(self.snapshots()), 3)

    def test_legacy_started_ambiguity_never_retries(self):
        digest = hashlib.sha256(b'{"text":"same"}').hexdigest()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO tool_calls VALUES(?,?,?,?,?,?,?)", (
                "same-request", "same-call", "slack_post_message", digest, "started", None, self.now))
        self.now += 10000
        result = self.call(lambda *_: self.fail("ambiguous effect retried"))
        self.assertEqual(result["error"], "tool_effect_unknown_after_interruption")
        self.assertTrue(result["uncertain"])

    def test_uncertain_retry_attempt_stops_future_retries(self):
        self.call(lambda *_: self.throttle())
        self.now += 10
        uncertain = {"isError": True, "uncertain": True, "error": "lost_response"}
        self.assertEqual(self.call(lambda *_: uncertain), uncertain)
        self.now += 10000
        self.assertEqual(self.call(lambda *_: self.fail("uncertain retry repeated")), uncertain)
        self.assertEqual(len(self.snapshots()), 4)

    def test_ordinary_success_is_still_replayed_exactly(self):
        first = {"ok": True, "result": {"status": "completed", "receipt": "unchanged"}}
        self.assertEqual(self.call(lambda *_: first), first)
        self.now += 10000
        self.assertEqual(self.call(lambda *_: self.fail("success repeated")), first)
        self.assertEqual(len(self.snapshots()), 2)


if __name__ == "__main__":
    unittest.main()
