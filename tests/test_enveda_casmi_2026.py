from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from competitions.enveda_casmi_2026.workbench import (  # noqa: E402
    SOURCE_LEDGER_SHA256, WorkbenchError, canonical, compile_report, digest,
    read_json, run_baseline, validate_sources, verify_report,
)

BASE = ROOT / "competitions" / "enveda_casmi_2026"
SOURCES = BASE / "competition_sources.json"
FIXTURE = BASE / "synthetic_fixture.json"
WORKBENCH = BASE / "workbench.py"
LEDGER = BASE / "experiment_ledger.json"
CHECKLIST = BASE / "submission_checklist.json"

class CasmiWorkbenchTests(unittest.TestCase):
    def sources(self): return json.loads(SOURCES.read_text(encoding="utf-8"))
    def fixture(self): return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_retained_source_generation_is_exact(self):
        raw = self.sources()
        self.assertEqual(digest(raw), SOURCE_LEDGER_SHA256)
        self.assertEqual(validate_sources(raw)["facts"]["prize_pool_usd"]["value"], 50000)

    def test_research_go_but_submission_rules_hold(self):
        report = compile_report(self.sources(), self.fixture())
        self.assertEqual(report["research_state"], "GO_RESEARCH_INTERNAL")
        self.assertEqual(report["submission_state"], "HOLD_RULES_SOURCE")
        self.assertIn("evaluation_metric", report["unresolved_rule_fields"])
        self.assertIn("data_license", report["unresolved_rule_fields"])
        self.assertIsNone(report["expected_value_usd"])
        self.assertFalse(report["prize_or_revenue_claimed"])

    def test_entry_and_close_milestones_remain_distinct_sources(self):
        facts = self.sources()["facts"]
        self.assertEqual(facts["entry_deadline_date"]["value"], "2026-12-07")
        self.assertEqual(facts["entry_deadline_date"]["source_class"], "KAGGLE_OFFICIAL_ANNOUNCEMENT")
        self.assertEqual(facts["competition_close_date"]["value"], "2026-12-14")
        self.assertEqual(facts["competition_close_date"]["state"], "HOST_ANNOUNCEMENT_NOT_RULES")

    def test_third_party_slug_is_discovery_only(self):
        fact = self.sources()["facts"]["candidate_competition_slug"]
        self.assertEqual(fact["state"], "DISCOVERY_ONLY")
        self.assertIsNone(fact["source_url"])

    def test_caller_cannot_promote_rules_by_rewriting_ledger(self):
        raw = self.sources()
        raw["facts"]["evaluation_metric"] = {
            "value": "CALLER_METRIC", "state": "VERIFIED_COMPETITION_RULES",
            "source_class": "CALLER", "source_url": "https://example.test", "note": "fake"
        }
        with self.assertRaises(WorkbenchError): validate_sources(raw)

    def test_boolean_prize_is_rejected(self):
        raw = self.sources(); raw["facts"]["prize_pool_usd"]["value"] = True
        with self.assertRaises(WorkbenchError): validate_sources(raw)

    def test_baseline_is_deterministic_and_perfect_on_separated_synthetic_fixture(self):
        one = run_baseline(self.fixture()); two = run_baseline(copy.deepcopy(self.fixture()))
        self.assertEqual(one, two)
        self.assertEqual(one["query_count"], 3)
        self.assertEqual(one["top1_accuracy"], 1.0)
        self.assertEqual(one["mean_reciprocal_rank"], 1.0)
        self.assertFalse(one["competition_score_claimed"])
        self.assertIn("NOT_KAGGLE_METRIC", one["metric_kind"])

    def test_competition_gated_dataset_kind_is_rejected(self):
        raw = self.fixture(); raw["dataset_kind"] = "COMPETITION"
        with self.assertRaises(WorkbenchError): run_baseline(raw)

    def test_duplicate_candidate_id_is_rejected(self):
        raw = self.fixture(); raw["candidates"].append(copy.deepcopy(raw["candidates"][0]))
        with self.assertRaises(WorkbenchError): run_baseline(raw)

    def test_missing_expected_candidate_is_rejected(self):
        raw = self.fixture(); raw["queries"][0]["expected_candidate_id"] = "C-Z"
        with self.assertRaises(WorkbenchError): run_baseline(raw)

    def test_unsorted_or_duplicate_peaks_fail_closed(self):
        for peaks in ([[[80,1],[70,2]]], [[[70,1],[70,2]]]):
            raw = self.fixture(); raw["queries"][0]["peaks"] = peaks[0]
            with self.subTest(peaks=peaks), self.assertRaises(WorkbenchError): run_baseline(raw)

    def test_nonfinite_peak_fails_closed(self):
        raw = self.fixture(); raw["queries"][0]["peaks"][0][1] = float("nan")
        with self.assertRaises(WorkbenchError): run_baseline(raw)

    def test_bool_numeric_alias_fails_closed(self):
        raw = self.fixture(); raw["mass_tolerance_da"] = True
        with self.assertRaises(WorkbenchError): run_baseline(raw)

    def test_authority_is_all_false(self):
        authority = compile_report(self.sources(), self.fixture())["authority"]
        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))

    def test_report_verifier_recompiles_semantics(self):
        report = compile_report(self.sources(), self.fixture())
        self.assertTrue(verify_report(report))
        tampered = copy.deepcopy(report); tampered["submission_state"] = "READY_FOR_OWNER_JOIN_REVIEW"
        self.assertFalse(verify_report(tampered))

    def test_recomputed_plain_hash_cannot_forge_submission_ready(self):
        tampered = copy.deepcopy(compile_report(self.sources(), self.fixture()))
        tampered["submission_state"] = "READY_FOR_OWNER_JOIN_REVIEW"
        core = copy.deepcopy(tampered); core.pop("report_sha256")
        tampered["report_sha256"] = digest(core)
        self.assertFalse(verify_report(tampered))

    def test_strict_loader_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"dup.json"; p.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaises(WorkbenchError): read_json(p)

    def test_strict_loader_rejects_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"nan.json"; p.write_text('{"a":NaN}', encoding="utf-8")
            with self.assertRaises(WorkbenchError): read_json(p)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO required")
    def test_fifo_input_fails_promptly(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"pipe"; os.mkfifo(p)
            with self.assertRaises(WorkbenchError): read_json(p)

    def test_cli_compile_verify_and_create_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)/"report.json"
            first = subprocess.run([sys.executable, str(WORKBENCH), "compile", str(SOURCES), str(FIXTURE), str(out)], capture_output=True, text=True, timeout=10)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("GO_RESEARCH_INTERNAL / HOLD_RULES_SOURCE", first.stdout)
            verify = subprocess.run([sys.executable, str(WORKBENCH), "verify", str(out)], capture_output=True, text=True, timeout=10)
            self.assertEqual(verify.returncode, 0, verify.stderr); self.assertEqual(verify.stdout.strip(), "VERIFIED")
            second = subprocess.run([sys.executable, str(WORKBENCH), "compile", str(SOURCES), str(FIXTURE), str(out)], capture_output=True, text=True, timeout=10)
            self.assertEqual(second.returncode, 2); self.assertIn("refusing non-exclusive", second.stderr)

    def test_experiment_ledger_is_synthetic_and_non_submission(self):
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        self.assertEqual(ledger["schema"], "commons.enveda-casmi-2026.experiment-ledger/v1")
        self.assertEqual(len(ledger["records"]), 1)
        row = ledger["records"][0]
        baseline = run_baseline(self.fixture())
        self.assertEqual(row["dataset_kind"], "SYNTHETIC")
        self.assertEqual(row["fixture_sha256"], baseline["fixture_sha256"])
        self.assertEqual(row["baseline_receipt_sha256"], baseline["baseline_receipt_sha256"])
        self.assertFalse(row["competition_score_claimed"])
        self.assertFalse(row["submission_used"])

    def test_submission_checklist_stays_hold_and_has_no_authority(self):
        checklist = json.loads(CHECKLIST.read_text(encoding="utf-8"))
        self.assertEqual(checklist["overall_state"], "HOLD_RULES_SOURCE")
        self.assertTrue(all(item["state"] in {"HOLD", "NOT_DONE"} for item in checklist["items"]))
        self.assertTrue(all(value is False for value in checklist["authority"].values()))

    def test_lone_surrogate_fails_canonicalization(self):
        with self.assertRaises(WorkbenchError): canonical({"x":"\ud800"})

    def test_source_fact_set_cannot_be_silently_reduced(self):
        raw = self.sources(); del raw["facts"]["eligibility"]
        with self.assertRaises(WorkbenchError): validate_sources(raw)

if __name__ == "__main__": unittest.main()
