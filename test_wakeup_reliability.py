#!/usr/bin/env python3
"""Regression tests for the universal Commons wakeup carrier."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import wakeup


JOB_ID = "codex-wakeup-retry-20260822-01"
DUE = "2026-08-22T22:00:00Z"
T0 = datetime(2026, 8, 22, 22, 1, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 8, 22, 22, 2, 0, tzinfo=timezone.utc)


class WakeupReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wakeup-reliability-")
        self.saved = (wakeup.ROOT, wakeup.now, wakeup.ntfy, wakeup.urllib.request.urlopen)
        wakeup.ROOT = self.tmp.name
        os.makedirs(os.path.join(self.tmp.name, "wakeups"), exist_ok=True)

    def tearDown(self):
        wakeup.ROOT, wakeup.now, wakeup.ntfy, wakeup.urllib.request.urlopen = self.saved
        self.tmp.cleanup()

    def write_job(self):
        path = os.path.join(self.tmp.name, "wakeups", "CODEX_LOCAL.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "from": "CODEX_LOCAL",
                "id": JOB_ID,
                "wakeup": DUE,
                "adapter": "Codex/local/GitHub Actions",
            }, f)

    def read_json(self, *parts):
        with open(os.path.join(self.tmp.name, *parts), encoding="utf-8") as f:
            return json.load(f)

    def test_failed_delivery_remains_due_and_retries(self):
        self.write_job()
        calls = []

        def fail(row, attempt_id):
            calls.append((row["id"], attempt_id))
            return False

        wakeup.ntfy = fail
        wakeup.now = lambda: T0
        self.assertEqual(wakeup.main(), 0)
        self.assertEqual(self.read_json("wakeups", "fired.json")["ids"], [])
        self.assertEqual([row["id"] for row in self.read_json("wakeups.json")["due"]], [JOB_ID])

        wakeup.now = lambda: T1
        self.assertEqual(wakeup.main(), 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.read_json("wakeups", "fired.json")["ids"], [])
        self.assertEqual([row["id"] for row in self.read_json("wakeups.json")["due"]], [JOB_ID])
        self.assertNotEqual(calls[0][1], calls[1][1])

    def test_successful_delivery_alone_becomes_fired(self):
        self.write_job()
        wakeup.now = lambda: T0
        wakeup.ntfy = lambda _row, _attempt_id: True
        self.assertEqual(wakeup.main(), 0)
        self.assertEqual(self.read_json("wakeups", "fired.json")["ids"], [JOB_ID])
        self.assertIn(JOB_ID, self.read_json("wakeups.json")["fired"])

        wakeup.now = lambda: T1
        self.assertEqual(wakeup.main(), 0)
        state = self.read_json("wakeups.json")
        self.assertEqual(state["due"], [])
        self.assertEqual(state["pending"], [])

    def test_missing_adapter_is_held_unrouted_without_delivery(self):
        path = os.path.join(self.tmp.name, "wakeups", "CODEX_LOCAL.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"from": "CODEX_LOCAL", "id": JOB_ID, "wakeup": DUE}, handle)
        calls = []
        wakeup.ntfy = lambda row, attempt_id: calls.append((row, attempt_id)) or True
        wakeup.now = lambda: T0

        self.assertEqual(wakeup.main(), 0)

        state = self.read_json("wakeups.json")
        self.assertEqual(state["due"], [])
        self.assertEqual(state["held_cursor"], [])
        self.assertEqual([row["id"] for row in state["held_unrouted"]], [JOB_ID])
        self.assertEqual(state["fired"], [])
        self.assertEqual(calls, [])

    def test_payload_keeps_stable_job_id_and_separate_attempt(self):
        captured = {}

        class Response:
            def read(self):
                return b"ok"

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return Response()

        wakeup.urllib.request.urlopen = fake_urlopen
        row = {
            "from": "CODEX_LOCAL",
            "id": JOB_ID,
            "wakeup": DUE,
            "href": "./wakeups/CODEX_LOCAL.json",
            "adapter": "Codex/local/GitHub Actions",
        }
        self.assertTrue(wakeup.ntfy(row, JOB_ID + "-attempt-01"))
        payload = captured["payload"]
        self.assertEqual(payload["id"], JOB_ID)
        self.assertEqual(payload["job_id"], JOB_ID)
        self.assertEqual(payload["attempt_id"], JOB_ID + "-attempt-01")
        self.assertNotEqual(payload["attempt_id"], payload["id"])

    def test_idle_tick_is_byte_quiet(self):
        wakeup.now = lambda: T0
        self.assertEqual(wakeup.main(), 0)
        public_path = os.path.join(self.tmp.name, "wakeups.json")
        fired_path = os.path.join(self.tmp.name, "wakeups", "fired.json")
        first_public = Path(public_path).read_bytes()
        first_fired = Path(fired_path).read_bytes()

        wakeup.now = lambda: T1
        self.assertEqual(wakeup.main(), 0)
        self.assertEqual(Path(public_path).read_bytes(), first_public)
        self.assertEqual(Path(fired_path).read_bytes(), first_fired)


if __name__ == "__main__":
    unittest.main()
