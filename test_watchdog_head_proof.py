#!/usr/bin/env python3
"""HEAD-proof canary leftover: a Slack taking is not a wake_jobs file."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
sys.path.insert(0, ROOT)

from watchdog_head_proof import (
    JOB_ID,
    RESULT_ID,
    SLACK_TS,
    WAKE_JOBS,
    classify,
    job_fields,
    load_catalog,
    measure_root,
    mint_job,
    parse_job,
    prove_temp_tick,
)


class TestWatchdogHeadProof(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_missing_job_stays_not_landed(self):
        verdict = classify({"measured": True, "job_present": False})
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("CLAIMED", verdict["note"])
        self.assertIn(JOB_ID, verdict["note"])

    def test_wrong_predicate_is_not_landed(self):
        verdict = classify(
            {
                "measured": True,
                "job_present": True,
                "job_id": JOB_ID,
                "predicate_type": "status_done",
                "result_address": RESULT_ID,
                "status": "OPEN",
            }
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("result_address_on_head", verdict["note"])

    def test_open_correct_file_is_candidate(self):
        verdict = classify(
            {
                "measured": True,
                "job_present": True,
                "job_id": JOB_ID,
                "predicate_type": "result_address_on_head",
                "result_address": RESULT_ID,
                "status": "OPEN",
            }
        )
        self.assertEqual(verdict["state"], "CANDIDATE")
        self.assertIn("JobStore.upsert", verdict["note"])

    def test_done_correct_file_is_integrated(self):
        verdict = classify(
            {
                "measured": True,
                "job_present": True,
                "job_id": JOB_ID,
                "predicate_type": "result_address_on_head",
                "result_address": RESULT_ID,
                "status": "DONE",
            }
        )
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_upsert_fields_are_the_canary(self):
        fields = job_fields()
        self.assertEqual(fields["job_id"], JOB_ID)
        self.assertEqual(fields["result_address"], RESULT_ID)
        self.assertEqual(
            fields["completion_predicate"],
            {"type": "result_address_on_head"},
        )
        self.assertEqual(fields["owner_claim"], "SPECTER")
        self.assertEqual(fields["harness"], "github-actions-head-proof")
        self.assertNotIn("desktop", fields["harness"].lower())
        self.assertNotIn("grok bot", fields["harness"].lower())

    def test_mint_uses_upsert_and_does_not_tick(self):
        with tempfile.TemporaryDirectory(prefix="head-proof-mint-") as tmp:
            minted = mint_job(tmp)
            path = os.path.join(tmp, WAKE_JOBS, "%s.json" % JOB_ID)
            self.assertTrue(os.path.isfile(path))
            with open(path, "r", encoding="utf-8") as handle:
                job = parse_job(handle.read())
            self.assertTrue(minted["minted"])
            self.assertEqual(minted["via"], "JobStore.upsert")
            self.assertFalse(minted["ticked"])
            self.assertEqual(job["job_id"], JOB_ID)
            self.assertEqual(job["status"], "OPEN")
            self.assertEqual(job["predicate_type"], "result_address_on_head")
            self.assertEqual(job["result_address"], RESULT_ID)
            self.assertFalse(job["woke_once"])

    def test_temp_tick_is_done_stop_zero_wake(self):
        row = prove_temp_tick()
        self.assertTrue(row["ran"])
        self.assertTrue(row["temp_store"])
        self.assertFalse(row["ticked_production"])
        self.assertEqual(row["wake_count"], 0)
        self.assertEqual(row["delivered_count"], 0)
        self.assertEqual(row["process_model_invocations"], 0)
        self.assertFalse(row["invoke_model"])
        self.assertEqual(row["proof_action"], "STOP")
        self.assertEqual(row["proof_reason"], "DONE")
        self.assertEqual(row["proof_status"], "DONE")
        self.assertEqual(row["truth_reads"], 1)
        self.assertEqual(row["head_calls"], 1)

    def test_live_tree_measures_the_canonical_job_without_reminting(self):
        path = os.path.join(ROOT, WAKE_JOBS, "%s.json" % JOB_ID)
        before = os.path.isfile(path)
        row = measure_root(ROOT)
        after = os.path.isfile(path)
        self.assertEqual(before, after)
        self.assertTrue(row["measured"])
        self.assertFalse(row["ticked_production"])
        self.assertEqual(row["wake_count"], 0)
        self.assertEqual(row["proof_reason"], "DONE")
        verdict = classify(row)
        if before:
            self.assertEqual(row["job_id"], JOB_ID)
            self.assertEqual(row["predicate_type"], "result_address_on_head")
            self.assertEqual(row["result_address"], RESULT_ID)
            self.assertIn(verdict["state"], {"CANDIDATE", "INTEGRATED"})
        else:
            self.assertFalse(row["job_present"])
            self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(row["slack_ts"], SLACK_TS)
        self.assertEqual(row["named_idle_bc_resume"], "UNMEASURED")
        self.assertIn("named idle bc- resume", row["hands_off"])

    def test_catalog_hands_off_named_lanes(self):
        catalog_path = os.path.join(ROOT, "ground", "WATCHDOG_HEAD_PROOF.json")
        with open(catalog_path, "r", encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["job_id"], JOB_ID)
        self.assertEqual(catalog["result_address"], RESULT_ID)
        self.assertEqual(catalog["named_idle_bc_resume"], "UNMEASURED")
        self.assertIn("Claude testers", catalog["hands_off"])
        self.assertIn("device / Muhlnickel / Titan", catalog["hands_off"])


if __name__ == "__main__":
    unittest.main()
