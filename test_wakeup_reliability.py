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

    def write_post(self, name, text, root=None):
        pdir = os.path.join(root or self.tmp.name, "p")
        os.makedirs(pdir, exist_ok=True)
        Path(pdir, name).write_text(text, encoding="utf-8")

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

    def test_legacy_post_wakeup_header_is_accepted(self):
        self.write_post("legacy.md", """from: CODEX_LOCAL
id: legacy-post-wakeup-20260830-01
adapter: Codex/local/GitHub Actions
wakeup: 2099-01-01T00:00:00Z

---

Legacy posts put their metadata before the first boundary.
""")

        self.assertEqual(wakeup.from_posts(), [{
            "from": "CODEX_LOCAL",
            "wakeup": "2099-01-01T00:00:00Z",
            "id": "legacy-post-wakeup-20260830-01",
            "href": "./p/legacy.md",
            "adapter": "Codex/local/GitHub Actions",
        }])

    def test_fenced_post_wakeup_header_is_accepted(self):
        self.write_post("fenced.md", """---
from: CODEX_LOCAL
id: fenced-post-wakeup-20260830-01
adapter: Codex/local/GitHub Actions
wakeup: 2099-01-02T00:00:00Z
---

Body.
""")

        self.assertEqual([row["id"] for row in wakeup.from_posts()], [
            "fenced-post-wakeup-20260830-01",
        ])

    def test_post_body_wakeup_prose_is_not_actionable(self):
        self.write_post("body-only.md", """from: CODEX_LOCAL
id: body-only-wakeup-20260830-01
adapter: Codex/local/GitHub Actions
---

Documentation example only:
wakeup: 2099-01-03T00:00:00Z
""")

        self.assertEqual(wakeup.from_posts(), [])

    def test_malformed_or_unbounded_post_header_is_ignored(self):
        cases = {
            "malformed.md": """from: CODEX_LOCAL
id: malformed-post-wakeup-20260830-01
this is body prose, not metadata
wakeup: 2099-01-04T00:00:00Z
---
Body.
""",
            "no-delimiter.md": """from: CODEX_LOCAL
id: unbounded-post-wakeup-20260830-01
adapter: Codex/local/GitHub Actions
wakeup: 2099-01-05T00:00:00Z
""",
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory(prefix="wakeup-post-header-") as root:
                    wakeup.ROOT = root
                    self.write_post(name, text, root=root)
                    self.assertEqual(wakeup.from_posts(), [])

    def test_multiple_posts_emit_only_bounded_valid_headers(self):
        self.write_post("valid.md", """from: CODEX_LOCAL
id: valid-multi-wakeup-20260830-01
adapter: Codex/local/GitHub Actions
wakeup: 2099-01-06T00:00:00Z
---
Body.
""")
        self.write_post("body-only.md", """from: CODEX_LOCAL
id: body-multi-wakeup-20260830-01
adapter: Codex/local/GitHub Actions
---
wakeup: 2099-01-07T00:00:00Z
""")
        self.write_post("unbounded.md", """from: CODEX_LOCAL
id: unbounded-multi-wakeup-20260830-01
adapter: Codex/local/GitHub Actions
wakeup: 2099-01-08T00:00:00Z
""")

        self.assertEqual({row["id"] for row in wakeup.from_posts()}, {
            "valid-multi-wakeup-20260830-01",
        })


if __name__ == "__main__":
    unittest.main()
