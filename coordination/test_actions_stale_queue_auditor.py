from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "actions_stale_queue_auditor.py"

spec = importlib.util.spec_from_file_location("actions_stale_queue_auditor", MODULE_PATH)
assert spec and spec.loader
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40


def pr(number=1, state="CLOSED", current_head_sha=SHA_B):
    return {
        "number": number,
        "state": state,
        "current_head_sha": current_head_sha,
    }


def run(
    *,
    run_id=100,
    event="pull_request",
    status="queued",
    head_branch="feature",
    head_sha=SHA_A,
    complete=True,
    sources=None,
    pull_requests=None,
):
    return {
        "run_id": run_id,
        "workflow": "tests",
        "event": event,
        "status": status,
        "head_branch": head_branch,
        "head_sha": head_sha,
        "provenance": {
            "complete": complete,
            "sources": sources
            if sources is not None
            else ["RUN_DIRECT", "BRANCH_QUERY", "COMMIT_QUERY"],
            "pull_requests": pull_requests
            if pull_requests is not None
            else [pr()],
        },
    }


def packet(runs=None):
    return {
        "schema": auditor.INPUT_SCHEMA,
        "repository": "woahwhattheheck/commons",
        "default_branch": "main",
        "observed_at": "2026-09-17T20:50:00Z",
        "runs": runs if runs is not None else [run()],
    }


class ActionsStaleQueueAuditorTests(unittest.TestCase):
    def decision(self, one_run):
        report = auditor.build_report(packet([one_run]))
        auditor.verify_report(report)
        return report["rows"][0]

    def test_closed_pr_is_safe_candidate(self):
        row = self.decision(
            run(pull_requests=[pr(state="CLOSED", current_head_sha=SHA_A)])
        )
        self.assertEqual(row["decision"], "SAFE_TO_CANCEL")
        self.assertTrue(row["requires_live_reread"])

    def test_open_stale_head_is_safe_candidate(self):
        row = self.decision(
            run(pull_requests=[pr(state="OPEN", current_head_sha=SHA_B)])
        )
        self.assertEqual(row["decision"], "SAFE_TO_CANCEL")

    def test_open_current_head_holds(self):
        row = self.decision(
            run(pull_requests=[pr(state="OPEN", current_head_sha=SHA_A)])
        )
        self.assertEqual(row["decision"], "HOLD")
        self.assertIn("OPEN_PR_CURRENT_HEAD", row["reasons"])

    def test_mixed_closed_and_current_open_holds(self):
        row = self.decision(
            run(
                pull_requests=[
                    pr(1, "CLOSED", SHA_A),
                    pr(2, "OPEN", SHA_A),
                ]
            )
        )
        self.assertEqual(row["decision"], "HOLD")
        self.assertIn("OPEN_PR_CURRENT_HEAD", row["reasons"])

    def test_main_branch_holds(self):
        row = self.decision(run(head_branch="main"))
        self.assertEqual(row["decision"], "HOLD")
        self.assertIn("DEFAULT_BRANCH", row["reasons"])

    def test_manual_and_nonqueued_hold(self):
        row = self.decision(run(event="workflow_dispatch", status="completed"))
        self.assertEqual(row["decision"], "HOLD")
        self.assertIn("EVENT_NOT_PULL_REQUEST", row["reasons"])
        self.assertIn("RUN_NOT_QUEUED", row["reasons"])

    def test_empty_or_incomplete_provenance_holds(self):
        row = self.decision(run(complete=False, sources=[], pull_requests=[]))
        self.assertEqual(row["decision"], "HOLD")
        self.assertIn("PROVENANCE_INCOMPLETE", row["reasons"])
        self.assertIn("PROVENANCE_SOURCES_INCOMPLETE", row["reasons"])
        self.assertIn("PROVENANCE_EMPTY", row["reasons"])

    def test_missing_resolution_source_holds(self):
        row = self.decision(
            run(sources=["RUN_DIRECT", "BRANCH_QUERY"], pull_requests=[pr()])
        )
        self.assertEqual(row["decision"], "HOLD")
        self.assertIn("PROVENANCE_SOURCES_INCOMPLETE", row["reasons"])

    def test_multiple_open_stale_prs_are_safe(self):
        row = self.decision(
            run(
                pull_requests=[
                    pr(10, "OPEN", SHA_B),
                    pr(11, "OPEN", SHA_C),
                ]
            )
        )
        self.assertEqual(row["decision"], "SAFE_TO_CANCEL")
        self.assertEqual(row["associated_pr_numbers"], [10, 11])

    def test_report_exact_recompile_and_tamper_rejection(self):
        report = auditor.build_report(packet())
        self.assertTrue(auditor.verify_report(report))
        tampered = copy.deepcopy(report)
        tampered["rows"][0]["head_sha"] = SHA_C
        unsigned = dict(tampered)
        unsigned.pop("report_receipt")
        tampered["report_receipt"] = auditor.sha256_hex(
            auditor.canonical_json(unsigned)
        )
        with self.assertRaisesRegex(auditor.AuditError, "semantic recompile mismatch"):
            auditor.verify_report(tampered)

    def test_authority_false_vs_zero_is_rejected_even_if_resealed(self):
        report = auditor.build_report(packet())
        report["authority"]["cancel_run_authorized"] = 0
        unsigned = dict(report)
        unsigned.pop("report_receipt")
        report["report_receipt"] = auditor.sha256_hex(auditor.canonical_json(unsigned))
        with self.assertRaisesRegex(auditor.AuditError, "literal false"):
            auditor.verify_report(report)

    def test_bool_int_alias_in_run_id_rejected(self):
        data = packet()
        data["runs"][0]["run_id"] = True
        with self.assertRaisesRegex(auditor.AuditError, "exact integer"):
            auditor.build_report(data)

    def test_provenance_complete_zero_rejected(self):
        data = packet()
        data["runs"][0]["provenance"]["complete"] = 0
        with self.assertRaisesRegex(auditor.AuditError, "exact boolean"):
            auditor.build_report(data)

    def test_direct_unsafe_integer_rejected(self):
        data = packet()
        data["runs"][0]["run_id"] = auditor.MAX_SAFE_INTEGER + 1
        with self.assertRaises(auditor.AuditError):
            auditor.build_report(data)

    def test_raw_huge_integer_rejected_without_interpreter_valueerror(self):
        raw = json.dumps(packet()).replace(
            '"run_id": 100', '"run_id": ' + "9" * 5000
        )
        with self.assertRaises(auditor.AuditError):
            auditor.loads_strict(raw)

    def test_raw_duplicate_key_rejected(self):
        raw = '{"schema":"x","schema":"y"}'
        with self.assertRaisesRegex(auditor.AuditError, "duplicate JSON key"):
            auditor.loads_strict(raw)

    def test_raw_float_rejected(self):
        with self.assertRaisesRegex(auditor.AuditError, "floating point"):
            auditor.loads_strict('{"x":1.25}')

    def test_deep_direct_packet_rejected_as_auditerror(self):
        value = None
        for _ in range(auditor.MAX_JSON_DEPTH + 2):
            value = [value]
        with self.assertRaisesRegex(auditor.AuditError, "nesting"):
            auditor.build_report(value)

    def test_large_node_direct_packet_fails_before_full_copy(self):
        data = packet()
        data["bomb"] = [None] * auditor.MAX_JSON_NODES
        with self.assertRaises(auditor.AuditError):
            auditor.build_report(data)

    def test_cli_compile_verify_and_huge_int_rc2_no_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            input_path = td / "input.json"
            report_path = td / "report.json"
            input_path.write_text(json.dumps(packet()), encoding="utf-8")
            compiled = subprocess.run(
                [sys.executable, str(MODULE_PATH), "compile", str(input_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            report_path.write_text(compiled.stdout, encoding="utf-8")
            verified = subprocess.run(
                [sys.executable, str(MODULE_PATH), "verify", str(report_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertEqual(verified.stdout.strip(), '{"valid":true}')

            hostile = td / "hostile.json"
            hostile.write_text(
                json.dumps(packet()).replace(
                    '"run_id": 100', '"run_id": ' + "9" * 5000
                ),
                encoding="utf-8",
            )
            failed = subprocess.run(
                [sys.executable, str(MODULE_PATH), "compile", str(hostile)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(failed.returncode, 2)
            self.assertIn("AUDIT_ERROR:", failed.stderr)
            audit_tail = failed.stderr[failed.stderr.rfind("AUDIT_ERROR:") :]
            self.assertNotIn("Traceback", audit_tail)


if __name__ == "__main__":
    unittest.main()
