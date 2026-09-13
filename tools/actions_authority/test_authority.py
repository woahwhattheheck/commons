from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from .authority import classify
from .cli import main
from .common import EvidenceError, parse_json_bytes

HEAD = "a" * 40
NOW = datetime(2026, 9, 13, 8, 30, tzinfo=timezone.utc)


def job(status="completed", conclusion="success", runner="GitHub Actions 1", started="2026-09-13T08:20:02Z", steps=None, job_id=11):
    if steps is None and status == "completed" and conclusion == "success":
        steps = [{"name": "test", "status": "completed", "conclusion": "success"}]
    return {"job_id": job_id, "name": "test", "status": status, "conclusion": conclusion,
            "runner_name": runner, "started_at": started,
            "completed_at": "2026-09-13T08:21:00Z" if status == "completed" else None, "steps": steps}


def run(workflow="CI", *, run_id=1, status="completed", conclusion="success", jobs=None):
    return {"run_id": run_id, "workflow": workflow, "head_sha": HEAD, "status": status,
            "conclusion": conclusion, "created_at": "2026-09-13T08:20:00Z",
            "started_at": "2026-09-13T08:20:01Z" if status in {"in_progress", "completed"} else None,
            "completed_at": "2026-09-13T08:21:01Z" if status == "completed" else None,
            "jobs": [job()] if jobs is None else jobs}


def payload(*runs, required=None):
    return {"schema_version": "commons-actions-evidence/v1", "repository": "acme/widget",
            "head_sha": HEAD, "captured_at": "2026-09-13T08:25:00Z",
            "required_workflows": required or ["CI"], "runs": list(runs)}


class AuthorityTests(unittest.TestCase):
    def test_green_is_only_merge_authority(self):
        receipt = classify(payload(run()), now=NOW)
        self.assertEqual(receipt["decision"], "TERMINAL_GREEN")
        self.assertTrue(receipt["merge_authorized"])
        self.assertFalse(receipt["runner_exception_candidate"])

    def test_red_dominates_green(self):
        failed = run("Delivery", run_id=2, conclusion="failure", jobs=[job(conclusion="failure")])
        receipt = classify(payload(run(), failed, required=["CI", "Delivery"]), now=NOW)
        self.assertEqual(receipt["decision"], "TERMINAL_RED")
        self.assertFalse(receipt["merge_authorized"])

    def test_queued_and_cancelled_zero_step_are_backlog_candidates(self):
        for status, conclusion in [("queued", None), ("completed", "cancelled")]:
            with self.subTest(status=status):
                z = job(status=status, conclusion=conclusion, runner=None, started=None, steps=None)
                evidence = payload(run(status=status, conclusion=conclusion, jobs=[z]))
                receipt = classify(evidence, now=NOW)
                self.assertEqual(receipt["decision"], "WAIT_RUNNER_BACKLOG")
                self.assertTrue(receipt["runner_exception_candidate"])
                self.assertFalse(receipt["merge_authorized"])

    def test_cancelled_after_runner_start_is_hold(self):
        z = job(status="completed", conclusion="cancelled", runner="runner-1", started="2026-09-13T08:20:05Z", steps=[])
        receipt = classify(payload(run(conclusion="cancelled", jobs=[z])), now=NOW)
        self.assertEqual(receipt["decision"], "HOLD")

    def test_missing_and_in_progress_are_waits(self):
        missing = classify(payload(run(), required=["CI", "Delivery"]), now=NOW)
        self.assertEqual(missing["decision"], "WAIT_MISSING")
        active = job(status="in_progress", conclusion=None, runner="runner-1", started="2026-09-13T08:20:05Z", steps=[])
        waiting = classify(payload(run(status="in_progress", conclusion=None, jobs=[active])), now=NOW)
        self.assertEqual(waiting["decision"], "WAIT_EXECUTION")

    def test_conflicting_success_or_skipped_required_holds(self):
        failed = job(conclusion="failure", steps=[{"name": "test", "status": "completed", "conclusion": "failure"}])
        self.assertEqual(classify(payload(run(jobs=[failed])), now=NOW)["decision"], "HOLD")
        skipped = job(conclusion="skipped", runner=None, started=None, steps=[])
        self.assertEqual(classify(payload(run(conclusion="skipped", jobs=[skipped])), now=NOW)["decision"], "HOLD")

    def test_exact_head_single_attempt_and_fresh_snapshot_required(self):
        cases = []
        wrong = payload(run()); wrong["runs"][0]["head_sha"] = "b" * 40; cases.append(wrong)
        cases.append(payload(run(run_id=1), run(run_id=2)))
        stale = payload(run()); stale["captured_at"] = "2026-09-13T07:00:00Z"; cases.append(stale)
        future = payload(run()); future["captured_at"] = "2026-09-13T09:00:00Z"; cases.append(future)
        for evidence in cases:
            with self.subTest(evidence=evidence.get("captured_at")):
                with self.assertRaises(EvidenceError):
                    classify(evidence, now=NOW)

    def test_snapshot_rejects_run_or_job_times_after_capture(self):
        late = run(status="queued", conclusion=None, jobs=[job(status="queued", conclusion=None, runner=None, started=None, steps=None)]); late["created_at"] = "2026-09-13T08:31:00Z"
        with self.assertRaisesRegex(EvidenceError, "after the evidence capture"):
            classify(payload(late), now=NOW)
        late_job = run(); late_job["jobs"][0]["completed_at"] = "2026-09-13T08:31:00Z"
        with self.assertRaisesRegex(EvidenceError, "after the evidence capture"):
            classify(payload(late_job), now=NOW)

    def test_strict_json_and_unknown_fields(self):
        with self.assertRaises(EvidenceError):
            parse_json_bytes(b'{"schema_version":"x","schema_version":"y"}')
        evidence = payload(run()); evidence["trust_me"] = True
        with self.assertRaises(EvidenceError):
            classify(evidence, now=NOW)

    def test_extra_workflow_is_ignored_but_audited(self):
        receipt = classify(payload(run(), run("Optional", run_id=2)), now=NOW)
        self.assertEqual(receipt["decision"], "TERMINAL_GREEN")
        self.assertEqual(receipt["ignored_extra_workflows"], ["Optional"])

    def test_cli_create_exclusive_hold_and_symlink_fences(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); src = root / "evidence.json"; out = root / "receipt.json"
            src.write_text(json.dumps(payload(run())), encoding="utf-8")
            self.assertEqual(main([str(src), "--out", str(out), "--now", "2026-09-13T08:30:00Z"]), 0)
            self.assertEqual(main([str(src), "--out", str(out), "--now", "2026-09-13T08:30:00Z"]), 2)
            if hasattr(os, "symlink"):
                link = root / "link.json"
                try:
                    link.symlink_to(src.name)
                except (OSError, NotImplementedError):
                    return
                self.assertEqual(main([str(link), "--out", str(root / "other.json"), "--now", "2026-09-13T08:30:00Z"]), 2)

    def test_receipt_digest_is_key_order_and_evaluation_time_stable(self):
        evidence = payload(run())
        reparsed = parse_json_bytes(json.dumps(evidence).encode())
        first = classify(evidence, now=NOW)
        later = classify(reparsed, now=datetime(2026, 9, 13, 8, 31, tzinfo=timezone.utc))
        self.assertNotEqual(first["evaluated_at"], later["evaluated_at"])
        self.assertEqual(first["receipt_digest"], later["receipt_digest"])


if __name__ == "__main__":
    unittest.main()
