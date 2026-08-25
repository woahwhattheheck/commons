#!/usr/bin/env python3
"""MCP/wake real-job leftover: a Slack pivot is not a completed job."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
sys.path.insert(0, ROOT)

from mcp_wake_job import (
    AFTER,
    JOB_ID,
    JOBS,
    RESULT_ID,
    SLACK_TS,
    WATCHDOG,
    WORKFLOW,
    classify,
    load_catalog,
    measure_root,
    parse_jobs,
    parse_watchdog,
    run_real_job,
    wake_job_json_count,
)


class TestMcpWakeJob(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_missing_contract_stays_not_landed(self):
        verdict = classify({"measured": True, "jobs_present": False})
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("CLAIMED", verdict["note"])

    def test_files_without_run_are_candidate(self):
        verdict = classify(
            {
                "measured": True,
                "jobs_present": True,
                "watchdog_present": True,
                "workflow_present": True,
                "has_result_address_on_head": True,
                "has_page_exists": True,
                "ran": False,
                "wrote_wake_jobs": False,
            }
        )
        self.assertEqual(verdict["state"], "CANDIDATE")
        self.assertIn("not a completed job", verdict["note"])

    def test_wake_jobs_write_is_not_landed(self):
        verdict = classify(
            {
                "measured": True,
                "jobs_present": True,
                "watchdog_present": True,
                "workflow_present": True,
                "has_result_address_on_head": True,
                "has_page_exists": True,
                "ran": True,
                "wrote_wake_jobs": True,
            }
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("wake_jobs/", verdict["note"])

    def test_missing_page_accept_is_not_landed(self):
        verdict = classify(
            {
                "measured": True,
                "jobs_present": True,
                "watchdog_present": True,
                "workflow_present": True,
                "has_result_address_on_head": True,
                "has_page_exists": True,
                "ran": True,
                "wrote_wake_jobs": False,
                "missing_page_refused": False,
            }
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("missing page", verdict["note"])

    def test_done_plus_refuse_is_integrated(self):
        verdict = classify(
            {
                "measured": True,
                "jobs_present": True,
                "watchdog_present": True,
                "workflow_present": True,
                "has_result_address_on_head": True,
                "has_page_exists": True,
                "ran": True,
                "wrote_wake_jobs": False,
                "missing_page_refused": True,
                "done_status": "DONE",
                "after_invoke_model": False,
                "watchdog_invoke_model": False,
                "watchdog_process_model_invocations": 0,
            }
        )
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_real_job_refuses_missing_page_then_completes(self):
        row = run_real_job()
        self.assertTrue(row["ran"])
        self.assertTrue(row["temp_store"])
        self.assertFalse(row["wrote_wake_jobs"])
        self.assertTrue(row["missing_page_refused"])
        self.assertEqual(row["missing_code"], "NOT_DURABLE")
        self.assertTrue(row["due_invoke_model"])
        self.assertEqual(row["done_status"], "DONE")
        self.assertFalse(row["after_invoke_model"])
        self.assertFalse(row["watchdog_invoke_model"])
        self.assertEqual(row["watchdog_process_model_invocations"], 0)
        self.assertIn("%s.json" % JOB_ID, row["temp_job_files"])
        self.assertEqual(RESULT_ID, "rivet-ship-mcp-wake-job-20260825-01")
        self.assertEqual(AFTER, "2026-08-25T06:21:00Z")

    def test_live_tree_runs_the_real_job(self):
        before = wake_job_json_count(ROOT)
        row = measure_root(ROOT)
        after = wake_job_json_count(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["jobs_present"])
        self.assertTrue(row["watchdog_present"])
        self.assertTrue(row["workflow_present"])
        self.assertTrue(row["catalog_present"])
        self.assertTrue(row["has_result_address_on_head"])
        self.assertTrue(row["has_page_exists"])
        self.assertTrue(row["ran"])
        self.assertFalse(row["wrote_wake_jobs"])
        self.assertEqual(before, after)
        verdict = classify(row)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertIn("JOJO MCP inventory", row["hands_off"])
        self.assertIn("RIDGE/PLUMB named external-wake canary", row["hands_off"])
        self.assertEqual(row["slack_ts"], SLACK_TS)

    def test_catalog_hands_off_named_lanes(self):
        catalog_path = os.path.join(ROOT, "ground", "MCP_WAKE_JOB.json")
        with open(catalog_path, "r", encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertFalse(catalog["wrote_wake_jobs"])
        self.assertIn("JOJO idle-resume", catalog["hands_off"])
        self.assertIn("named idle bc- resume", catalog["hands_off"])

    def test_live_contract_keeps_the_durable_gate(self):
        with open(os.path.join(ROOT, JOBS), "r", encoding="utf-8") as handle:
            jobs = parse_jobs(handle.read())
        self.assertTrue(jobs["has_result_address_on_head"])
        self.assertTrue(jobs["has_page_exists"])
        self.assertTrue(jobs["has_not_durable"])
        with open(os.path.join(ROOT, WATCHDOG), "r", encoding="utf-8") as handle:
            watchdog = parse_watchdog(handle.read())
        self.assertTrue(watchdog["watchdog_never_model"])
        self.assertTrue(os.path.isfile(os.path.join(ROOT, WORKFLOW)))


if __name__ == "__main__":
    unittest.main()
