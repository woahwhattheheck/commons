import datetime as dt
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "host"))
import review_holding_check as r

HEAD = "a" * 40
OTHER = "b" * 40
NOW = dt.datetime(2026, 9, 11, 17, 0, 0, tzinfo=dt.timezone.utc)


def holding(**overrides):
    row = {
        "schema": r.SCHEMA,
        "key": "pr-12578",
        "holder": "reviewer-seat",
        "head_sha": HEAD,
        "heartbeat_at": "2026-09-11T16:55:00Z",
        "ttl_s": 600,
        "released_at": None,
    }
    row.update(overrides)
    return row


class ReducerTests(unittest.TestCase):
    def test_absent_is_success(self):
        got = r.evaluate(None, HEAD, now=NOW)
        self.assertEqual((got["state"], got["reason"]), ("SUCCESS", "no_holding"))

    def test_live_same_head_is_pending(self):
        got = r.evaluate(holding(), HEAD, now=NOW)
        self.assertEqual(got["state"], "PENDING")
        self.assertEqual(got["remaining_s"], 300)

    def test_exact_expiry_is_success(self):
        got = r.evaluate(holding(heartbeat_at="2026-09-11T16:50:00Z"), HEAD, now=NOW)
        self.assertEqual((got["state"], got["reason"]), ("SUCCESS", "expired"))

    def test_released_is_success(self):
        got = r.evaluate(holding(released_at="2026-09-11T16:59:59Z"), HEAD, now=NOW)
        self.assertEqual((got["state"], got["reason"]), ("SUCCESS", "released"))

    def test_other_head_does_not_block(self):
        got = r.evaluate(holding(head_sha=OTHER), HEAD, now=NOW)
        self.assertEqual((got["state"], got["reason"]), ("SUCCESS", "different_head"))

    def test_bool_ttl_is_rejected(self):
        with self.assertRaises(r.InputError):
            r.evaluate(holding(ttl_s=True), HEAD, now=NOW)

    def test_future_heartbeat_is_rejected(self):
        with self.assertRaises(r.InputError):
            r.evaluate(holding(heartbeat_at="2026-09-11T17:00:01Z"), HEAD, now=NOW)

    def test_release_before_heartbeat_is_rejected(self):
        with self.assertRaises(r.InputError):
            r.evaluate(holding(released_at="2026-09-11T16:54:59Z"), HEAD, now=NOW)

    def test_bad_sha_and_ttl_cap_rejected(self):
        for row in (holding(head_sha="A" * 40), holding(ttl_s=86401)):
            with self.subTest(row=row), self.assertRaises(r.InputError):
                r.evaluate(row, HEAD, now=NOW)

    def test_duplicate_json_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "h.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write('{"schema":"commons-review-holding/v1","schema":"x"}')
            with self.assertRaises(r.InputError):
                r._load(path)


class CheckApiTests(unittest.TestCase):
    def test_pending_creates_in_progress_check(self):
        result = r.evaluate(holding(), HEAD, now=NOW)
        calls = []

        def fake(method, url, token, body=None):
            calls.append((method, url, body))
            if method == "GET":
                return {"check_runs": []}
            return {"id": 77}

        with mock.patch.object(r, "_request", side_effect=fake):
            receipt = r.publish_check(result, repo="o/r", token="t")
        self.assertEqual(receipt["status"], "in_progress")
        self.assertEqual(calls[-1][0], "POST")
        self.assertEqual(calls[-1][2]["status"], "in_progress")
        self.assertNotIn("conclusion", calls[-1][2])

    def test_success_updates_matching_check(self):
        result = r.evaluate(None, HEAD, now=NOW)
        ext = f"review-holding:{HEAD}"
        calls = []

        def fake(method, url, token, body=None):
            calls.append((method, url, body))
            if method == "GET":
                return {"check_runs": [{"id": 88, "external_id": ext, "status": "in_progress"}]}
            return {"id": 88}

        with mock.patch.object(r, "_request", side_effect=fake):
            receipt = r.publish_check(result, repo="o/r", token="t")
        self.assertEqual(receipt["action"], "updated")
        self.assertEqual(calls[-1][0], "PATCH")
        self.assertEqual(calls[-1][2]["status"], "completed")
        self.assertEqual(calls[-1][2]["conclusion"], "success")
        self.assertNotIn("head_sha", calls[-1][2])

    def test_new_live_holding_after_completed_check_creates_fresh_run(self):
        result = r.evaluate(holding(), HEAD, now=NOW)
        ext = f"review-holding:{HEAD}"
        calls = []

        def fake(method, url, token, body=None):
            calls.append((method, url, body))
            if method == "GET":
                return {"check_runs": [{"id": 99, "external_id": ext, "status": "completed", "conclusion": "success"}]}
            return {"id": 100}

        with mock.patch.object(r, "_request", side_effect=fake):
            receipt = r.publish_check(result, repo="o/r", token="t")
        self.assertEqual(receipt["action"], "created")
        self.assertEqual(calls[-1][0], "POST")
        self.assertEqual(calls[-1][2]["status"], "in_progress")


if __name__ == "__main__":
    unittest.main()
