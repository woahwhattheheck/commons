#!/usr/bin/env python3
"""MCP/wake leftover measures; it does not invent a live resume."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from mcp_wake import (
    JOB_ID,
    OTHER_BC,
    SURFACES,
    TEST_FILES,
    catalog_from_row,
    classify,
    grok_smoke,
    idle_resume_row,
    load_inventory,
    measure_from_rows,
    measure_root,
    verify_job,
)
from harness_wake.idle_resume import probe_idle_resume


class TestMcpWake(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_secrets_are_not_landed(self):
        row = classify({"measured": True, "secrets": True})
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("secrets", row["note"])

    def test_wake_jobs_write_is_not_landed(self):
        row = classify(
            {
                "measured": True,
                "surface_count": 4,
                "inventory": True,
                "job_tools": True,
                "job": {"ok": True, "invoke_model": False, "wrote_wake_jobs": True},
                "idle": {"state": "UNMEASURED"},
            }
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("wake_jobs", row["note"])

    def test_live_resume_is_not_landed(self):
        row = classify(
            {
                "measured": True,
                "surface_count": 4,
                "inventory": True,
                "job_tools": True,
                "job": {"ok": True, "invoke_model": False},
                "idle": {"state": "UNMEASURED", "live_resume": True},
            }
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("fail-closes", row["note"])

    def test_census_marks_inventory_and_empty_wake(self):
        measured = measure_from_rows(
            {
                "surfaces": list(SURFACES),
                "inventory": True,
                "inventory_surfaces": list(SURFACES),
                "tests": list(TEST_FILES),
                "job_tools": True,
                "wake_job_json": 0,
                "job": {
                    "ok": True,
                    "state": "TICKED",
                    "action": "STOP",
                    "reason": "NOT_DUE",
                    "invoke_model": False,
                    "wrote_wake_jobs": False,
                },
                "grok_exists": False,
                "idle": probe_idle_resume(OTHER_BC),
            }
        )
        self.assertEqual(measured["mcp"], "INTEGRATED")
        self.assertEqual(measured["wake"], "EMPTY")
        self.assertEqual(measured["grok"]["state"], "UNMEASURED")
        self.assertEqual(measured["idle"]["state"], "UNMEASURED")
        self.assertFalse(measured["idle"]["live_resume"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        self.assertFalse(measured["secrets"])
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_fragmented_without_inventory(self):
        measured = measure_from_rows(
            {
                "surfaces": list(SURFACES),
                "inventory": False,
                "wake_job_json": 0,
            }
        )
        self.assertEqual(measured["mcp"], "FRAGMENTED")
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_real_job_tick_does_not_invoke_or_write_repo(self):
        job = verify_job()
        self.assertTrue(job["ok"])
        self.assertFalse(job["invoke_model"])
        self.assertFalse(job["wrote_wake_jobs"])
        self.assertEqual(job["action"], "STOP")
        self.assertEqual(job["reason"], "NOT_DUE")
        self.assertEqual(job["job_id"], JOB_ID)
        self.assertFalse(os.path.isfile(os.path.join(ROOT, "wake_jobs", JOB_ID + ".json")))

    def test_idle_resume_fail_closes(self):
        probe = probe_idle_resume(OTHER_BC)
        row = idle_resume_row(probe)
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertFalse(row["live_resume"])
        self.assertFalse(row["invoke_model"])

    def test_grok_absent_is_unmeasured(self):
        row = grok_smoke(False)
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_inventory_loader(self):
        parsed = load_inventory(
            '{"surfaces":[{"path":"commons_mcp.py"},"mcp_server"],"job_tools":["tick_job"]}'
        )
        self.assertEqual(parsed["surfaces"], ["commons_mcp.py", "mcp_server"])
        self.assertEqual(parsed["job_tools"], ["tick_job"])
        bad = load_inventory("{")
        self.assertIn("error", bad)

    def test_live_tree_has_inventory(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["inventory"])
        self.assertGreaterEqual(row["surface_count"], 4)
        self.assertTrue(row["job_tools"])
        self.assertEqual(row["wake"], "CANDIDATE")
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        catalog = catalog_from_row(row)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertFalse(catalog["job"]["wrote_wake_jobs"])
        self.assertFalse(catalog["idle"]["live_resume"])


if __name__ == "__main__":
    unittest.main()
