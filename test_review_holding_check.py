import datetime as dt
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path
import sys
import urllib.parse

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


def evaluate(record, *, generation=1):
    return r.evaluate(record, HEAD, now=NOW, generation=generation)


class ReducerTests(unittest.TestCase):
    def test_absent_is_success(self):
        got = evaluate(None)
        self.assertEqual((got["state"], got["reason"]), ("SUCCESS", "no_holding"))
        self.assertEqual(got["generation"], 1)

    def test_live_same_head_is_pending(self):
        got = evaluate(holding())
        self.assertEqual(got["state"], "PENDING")
        self.assertEqual(got["remaining_s"], 300)

    def test_exact_expiry_is_success(self):
        got = evaluate(holding(heartbeat_at="2026-09-11T16:50:00Z"))
        self.assertEqual((got["state"], got["reason"]), ("SUCCESS", "expired"))

    def test_released_is_success(self):
        got = evaluate(holding(released_at="2026-09-11T16:59:59Z"))
        self.assertEqual((got["state"], got["reason"]), ("SUCCESS", "released"))

    def test_other_head_does_not_block(self):
        got = evaluate(holding(head_sha=OTHER))
        self.assertEqual((got["state"], got["reason"]), ("SUCCESS", "different_head"))

    def test_bool_ttl_is_rejected(self):
        with self.assertRaises(r.InputError):
            evaluate(holding(ttl_s=True))

    def test_future_heartbeat_is_rejected(self):
        with self.assertRaises(r.InputError):
            evaluate(holding(heartbeat_at="2026-09-11T17:00:01Z"))

    def test_release_before_heartbeat_is_rejected(self):
        with self.assertRaises(r.InputError):
            evaluate(holding(released_at="2026-09-11T16:54:59Z"))

    def test_bad_sha_ttl_cap_and_generation_are_rejected(self):
        for row in (holding(head_sha="A" * 40), holding(ttl_s=86401)):
            with self.subTest(row=row), self.assertRaises(r.InputError):
                evaluate(row)
        for generation in (-1, True, r.MAX_GENERATION + 1):
            with self.subTest(generation=generation), self.assertRaises(r.InputError):
                r.evaluate(holding(), HEAD, now=NOW, generation=generation)
        for text in ("", "+1", "01", "-1", "1.0", "x"):
            with self.subTest(text=text), self.assertRaises(r.InputError):
                r._generation_text(text)

    def test_duplicate_json_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "h.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write('{"schema":"commons-review-holding/v1","schema":"x"}')
            with self.assertRaises(r.InputError):
                r._load(path)


class FakeChecksApi:
    def __init__(self):
        self.runs = []
        self.next_id = 100
        self.calls = []

    def __call__(self, method, url, token, body=None):
        self.calls.append((method, url, body))
        if method == "GET":
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            page = int(query.get("page", ["1"])[0])
            per_page = int(query.get("per_page", ["100"])[0])
            start = (page - 1) * per_page
            return {
                "total_count": len(self.runs),
                "check_runs": [dict(row) for row in self.runs[start:start + per_page]],
            }
        if method == "POST":
            row = dict(body)
            row["id"] = self.next_id
            self.next_id += 1
            self.runs.append(row)
            return dict(row)
        if method == "PATCH":
            run_id = int(url.rsplit("/", 1)[1])
            for row in self.runs:
                if row["id"] == run_id:
                    row.update(body)
                    return dict(row)
            raise AssertionError(f"unknown check run id {run_id}")
        raise AssertionError(method)

    def generation_run(self, generation):
        ext = r._external_id(HEAD, generation)
        rows = [row for row in self.runs if row.get("external_id") == ext]
        return max(rows, key=lambda row: row["id"])


class CheckApiTests(unittest.TestCase):
    def test_pending_creates_in_progress_check(self):
        result = evaluate(holding(), generation=7)
        api = FakeChecksApi()
        with mock.patch.object(r, "_request", side_effect=api):
            receipt = r.publish_check(result, repo="o/r", token="t")
        self.assertEqual(receipt["status"], "in_progress")
        self.assertEqual(receipt["generation"], 7)
        self.assertEqual(api.calls[-1][0], "POST")
        self.assertEqual(api.calls[-1][2]["status"], "in_progress")
        self.assertEqual(
            api.calls[-1][2]["external_id"],
            f"review-holding:{HEAD}:g7",
        )
        self.assertNotIn("conclusion", api.calls[-1][2])

    def test_newer_success_creates_then_supersedes_older_pending(self):
        api = FakeChecksApi()
        with mock.patch.object(r, "_request", side_effect=api):
            r.publish_check(evaluate(holding(), generation=1), repo="o/r", token="t")
            receipt = r.publish_check(evaluate(None, generation=2), repo="o/r", token="t")
        self.assertEqual(receipt["action"], "created")
        self.assertEqual(api.generation_run(2)["conclusion"], "success")
        self.assertEqual(api.generation_run(1)["status"], "completed")
        self.assertEqual(api.generation_run(1)["conclusion"], "success")

    def test_delayed_old_success_cannot_clear_newer_pending(self):
        api = FakeChecksApi()
        old_success = evaluate(None, generation=1)
        newer_pending = evaluate(holding(), generation=2)
        with mock.patch.object(r, "_request", side_effect=api):
            r.publish_check(old_success, repo="o/r", token="t")
            r.publish_check(newer_pending, repo="o/r", token="t")
            receipt = r.publish_check(old_success, repo="o/r", token="t")
        self.assertEqual(receipt["action"], "ignored_stale")
        self.assertEqual(receipt["authoritative_generation"], 2)
        self.assertEqual(api.generation_run(2)["status"], "in_progress")

    def test_delayed_old_pending_cannot_resurrect_after_release(self):
        api = FakeChecksApi()
        old_pending = evaluate(holding(), generation=1)
        released = evaluate(
            holding(released_at="2026-09-11T16:59:59Z"),
            generation=2,
        )
        with mock.patch.object(r, "_request", side_effect=api):
            r.publish_check(old_pending, repo="o/r", token="t")
            r.publish_check(released, repo="o/r", token="t")
            receipt = r.publish_check(old_pending, repo="o/r", token="t")
        self.assertEqual(receipt["action"], "ignored_stale")
        self.assertEqual(receipt["authoritative_generation"], 2)
        self.assertEqual(api.generation_run(2)["status"], "completed")
        self.assertEqual(api.generation_run(2)["conclusion"], "success")

    def test_same_generation_conflict_is_rejected_without_mutation(self):
        api = FakeChecksApi()
        pending = evaluate(holding(), generation=3)
        conflicting_success = evaluate(None, generation=3)
        with mock.patch.object(r, "_request", side_effect=api):
            r.publish_check(pending, repo="o/r", token="t")
            before = [dict(row) for row in api.runs]
            with self.assertRaisesRegex(RuntimeError, "generation conflict"):
                r.publish_check(conflicting_success, repo="o/r", token="t")
        self.assertEqual(api.runs, before)

    def test_same_generation_replay_is_idempotent(self):
        api = FakeChecksApi()
        pending = evaluate(holding(), generation=4)
        with mock.patch.object(r, "_request", side_effect=api):
            first = r.publish_check(pending, repo="o/r", token="t")
            second = r.publish_check(pending, repo="o/r", token="t")
        self.assertEqual(first["action"], "created")
        self.assertEqual(second["action"], "unchanged")
        self.assertEqual(len(api.runs), 1)

    def test_new_live_holding_after_completed_clear_needs_newer_generation(self):
        api = FakeChecksApi()
        with mock.patch.object(r, "_request", side_effect=api):
            r.publish_check(evaluate(None, generation=5), repo="o/r", token="t")
            receipt = r.publish_check(
                evaluate(holding(), generation=6),
                repo="o/r",
                token="t",
            )
        self.assertEqual(receipt["action"], "created")
        self.assertEqual(api.generation_run(6)["status"], "in_progress")


if __name__ == "__main__":
    unittest.main()
