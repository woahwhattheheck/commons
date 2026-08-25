#!/usr/bin/env python3
"""Fail-closed named idle bc- resume probe. Never invokes a model."""
from __future__ import annotations

import inspect
import unittest

from harness_wake.cursor_adapter import THIS_BC
from harness_wake.idle_resume import probe_idle_resume


class IdleResumeProbeTests(unittest.TestCase):
    def test_missing_road_stays_unmeasured_without_model(self):
        row = probe_idle_resume("bc-c9544018-da63-5629-8586-67ca6393418d")
        self.assertFalse(row["ok"])
        self.assertFalse(row["invoke_model"])
        self.assertFalse(row["live_resume"])
        self.assertFalse(row["measured"])
        self.assertEqual(row["action"], "STOP")
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertEqual(row["resume_roads"], [])

    def test_this_session_is_not_a_different_run(self):
        row = probe_idle_resume(THIS_BC)
        self.assertEqual(row["state"], "NOT_OTHER_RUN")
        self.assertFalse(row["invoke_model"])
        self.assertFalse(row["live_resume"])

    def test_bad_id_stops(self):
        row = probe_idle_resume("not-a-bc")
        self.assertEqual(row["state"], "BAD_ID")
        self.assertFalse(row["invoke_model"])

    def test_injected_callable_is_not_a_resume_api(self):
        self.assertNotIn("resume", inspect.signature(probe_idle_resume).parameters)

        def fake(bc_id: str):
            return {"ok": True, "state": "FAKE_MAIL", "reason": bc_id}

        with self.assertRaises(TypeError):
            probe_idle_resume(
                "bc-d2280797-f01f-562d-be8f-a244a322c1d0",
                resume=fake,
            )


if __name__ == "__main__":
    raise SystemExit(unittest.main())
