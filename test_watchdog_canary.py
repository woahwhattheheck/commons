#!/usr/bin/env python3
"""Durable watchdog canary leftover: an empty wake_jobs folder is not utilization."""

from __future__ import annotations

import json
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
sys.path.insert(0, ROOT)

from watchdog_canary import (
    ABSENT_ID,
    CANARY_REL,
    JOB_ID,
    PIN_SHA,
    PRESENT_ID,
    SLACK_TS,
    classify,
    load_canary,
    measure_root,
    wake_job_json_count,
)


class TestWatchdogCanary(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_empty_wake_jobs_stays_not_landed(self):
        verdict = classify(
            {
                "measured": True,
                "watchdog_present": True,
                "has_pinned_oracle": True,
                "wake_job_json_count": 0,
                "canary_present": False,
            }
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("unutilized", verdict["note"])

    def test_file_without_tick_is_candidate(self):
        verdict = classify(
            {
                "measured": True,
                "watchdog_present": True,
                "has_pinned_oracle": True,
                "wake_job_json_count": 1,
                "canary_present": True,
                "canary": {
                    "job_id": JOB_ID,
                    "result_address": PRESENT_ID,
                    "completion_predicate": {"type": "result_address_on_head"},
                },
                "ran": False,
            }
        )
        self.assertEqual(verdict["state"], "CANDIDATE")

    def test_known_present_must_stop_done(self):
        verdict = classify(
            {
                "measured": True,
                "watchdog_present": True,
                "has_pinned_oracle": True,
                "wake_job_json_count": 1,
                "canary_present": True,
                "canary": {
                    "job_id": JOB_ID,
                    "result_address": PRESENT_ID,
                    "completion_predicate": {"type": "result_address_on_head"},
                },
                "ran": True,
                "present_status": "OPEN",
                "present_action": "WAKE",
                "present_delivered_count": 1,
                "present_invoke_model": True,
                "present_process_model_invocations": 0,
                "one_sha": True,
                "absent_status": "LEASED",
                "absent_wake_count": 1,
            }
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")

    def test_live_tree_canary_utilizes_oracle(self):
        self.assertGreaterEqual(wake_job_json_count(ROOT), 1)
        job = load_canary(ROOT)
        self.assertEqual(job.get("job_id"), JOB_ID)
        self.assertEqual(job.get("result_address"), PRESENT_ID)
        self.assertEqual(
            (job.get("completion_predicate") or {}).get("type"),
            "result_address_on_head",
        )
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(row["present_status"], "DONE")
        self.assertEqual(row["present_action"], "STOP")
        self.assertEqual(row["present_delivered_count"], 0)
        self.assertFalse(row["present_invoke_model"])
        self.assertEqual(row["present_process_model_invocations"], 0)
        self.assertTrue(row["one_sha"])
        self.assertEqual(row["absent_status"], "LEASED")
        self.assertGreaterEqual(row["absent_wake_count"], 1)
        self.assertEqual(row["named_idle_bc_resume"], "UNMEASURED")
        self.assertEqual(SLACK_TS, "1787639656.279039")
        self.assertEqual(ABSENT_ID, "rivet-watchdog-canary-absent-20260825-01")
        self.assertEqual(PIN_SHA, "4fc766f59e66999eb13e7f864594f5f698e1660b")
        with open(os.path.join(ROOT, CANARY_REL), encoding="utf-8") as handle:
            durable = json.load(handle)
        self.assertEqual(durable["status"], "OPEN")
        self.assertNotEqual(durable.get("status"), "DONE")


if __name__ == "__main__":
    unittest.main()
