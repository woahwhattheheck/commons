"""Offline acceptance for UIOWA-085. Run with normal and optimized Python."""
import copy
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("uiowa085_planner", ROOT / "planner.py")
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)


class RoadmapTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "synthetic.json").read_text(encoding="utf-8"))

    def rows(self, report=None):
        return {row["id"]: row for row in (report or planner.build(self.data))["recommendations"]}

    def rec(self, rid):
        return next(row for row in self.data["recommendations"] if row["id"] == rid)

    def test_exact_dependency_bounds_and_cross_phase_range(self):
        rows = self.rows()
        self.assertEqual(rows["R-01"]["finish_day"], {"low": 10, "high": 20})
        self.assertEqual(rows["R-02"]["start_day"], {"low": 60, "high": 60})
        self.assertEqual(rows["R-04"]["start_day"], {"low": 80, "high": 100})
        self.assertEqual(rows["R-04"]["finish_day"], {"low": 100, "high": 130})
        self.assertEqual(rows["R-04"]["possible_start_phases"], ["0-90", "90-180"])
        self.assertIn("PREFERRED_PHASE_RANGE_RISK", rows["R-04"]["flags"])
        self.assertEqual(rows["R-05"]["start_day"], {"low": 180, "high": 180})

    def test_unknown_duration_propagates_without_zero_estimate(self):
        rows = self.rows()
        self.assertEqual(rows["R-06"]["finish_day"], {"low": 90, "high": None})
        self.assertEqual(rows["R-07"]["start_day"], {"low": 180, "high": None})
        self.assertEqual(rows["R-07"]["finish_day"], {"low": 190, "high": None})
        self.assertIn("UNKNOWN_PREREQUISITE_FINISH", rows["R-07"]["flags"])
        self.assertTrue(rows["R-07"]["timing_incomplete"])

    def test_half_open_phase_boundaries(self):
        self.assertEqual([planner.phase(day) for day in (0, 89, 90, 179, 180)],
                         ["0-90", "0-90", "90-180", "90-180", "180+"])
        self.rec("R-01")["duration_days"] = {"low": 90, "high": 90}
        rows = self.rows()
        self.assertEqual(rows["R-01"]["possible_execution_phases"], ["0-90"])
        self.assertEqual(rows["R-02"]["start_day"], {"low": 90, "high": 90})

    def test_zero_duration_is_a_milestone_not_missing(self):
        self.rec("R-01")["duration_days"] = {"low": 0, "high": 0}
        row = self.rows()["R-01"]
        self.assertEqual(row["finish_day"], {"low": 0, "high": 0})
        self.assertFalse(row["timing_incomplete"])

    def test_capacity_pressure_is_not_a_resource_leveled_schedule(self):
        result = planner.build(self.data)
        item = next(r for r in result["role_capacity_review"] if r["owner_role"] == "Service-reliability lead" and r["phase"] == "0-90")
        self.assertEqual(item["status"], "EXCEEDS_ASSUMPTIONS")
        self.assertEqual(item["demand_hours"], {"low": 70, "high": 90})
        self.assertEqual(self.rows(result)["R-02"]["start_day"], {"low": 60, "high": 60})

    def test_unknown_unallocated_work_prevents_clean_capacity_claim(self):
        self.rec("R-03")["effort_phase"] = None
        result = planner.build(self.data)
        items = [r for r in result["role_capacity_review"] if r["owner_role"] == "Identity-operations lead"]
        self.assertTrue(items)
        self.assertTrue(all(r["status"] == "UNKNOWN" for r in items))
        self.assertTrue(all("R-03" in r["unallocated_recommendation_ids"] for r in items))

    def test_known_minimum_overload_survives_unknown_demand(self):
        self.assertEqual(planner.budget_status({"low": 70, "high": None}, {"low": 40, "high": 60}), "EXCEEDS_ASSUMPTIONS")
        self.assertEqual(planner.budget_status({"low": 0, "high": None}, {"low": 40, "high": 60}), "UNKNOWN")
        self.assertEqual(planner.budget_status({"low": 20, "high": 50}, {"low": 40, "high": 60}), "RANGE_OVERLAP")
        self.assertEqual(planner.budget_status({"low": 20, "high": 40}, {"low": 40, "high": 60}), "WITHIN_ASSUMPTIONS")

    def test_independent_pairs_respect_transitive_dependencies(self):
        pairs = planner.build(self.data)["dependency_independent_pairs"]
        self.assertIn(["R-01", "R-03"], pairs)
        self.assertIn(["R-04", "R-06"], pairs)
        self.assertNotIn(["R-01", "R-05"], pairs)
        self.assertNotIn(["R-06", "R-07"], pairs)

    def test_maturity_is_an_unvalidated_hypothesis(self):
        self.rec("R-01")["maturity_hypothesis"]["target"] = 5
        rows = self.rows()
        self.assertEqual(rows["R-01"]["hypothesis_state"], "REVIEW_PROGRESSION_SCOPE")
        self.assertEqual(rows["R-01"]["maturity_hypothesis"]["target"], 5)
        self.assertEqual(rows["R-06"]["hypothesis_state"], "UNKNOWN_BASELINE_OR_TARGET")
        self.assertEqual(rows["R-05"]["hypothesis_state"], "ONE_TO_TWO_LEVEL_HYPOTHESIS_NOT_VALIDATED")

    def test_early_effort_conflict_is_visible(self):
        self.rec("R-05")["effort_phase"] = "0-90"
        self.rec("R-05")["preferred_phase"] = "0-90"
        flags = self.rows()["R-05"]["flags"]
        self.assertIn("EFFORT_BEFORE_EARLIEST_START", flags)
        self.assertIn("PREFERRED_PHASE_OUTSIDE_EARLIEST_RANGE", flags)

    def test_revised_duration_changes_downstream_phase_range(self):
        original = self.rows()["R-04"]
        self.rec("R-02")["duration_days"]["high"] = 25
        revised = self.rows()["R-04"]
        self.assertEqual(original["possible_start_phases"], ["0-90", "90-180"])
        self.assertEqual(revised["possible_start_phases"], ["0-90"])
        self.assertEqual(revised["start_day"], {"low": 80, "high": 85})

    def test_findings_and_exact_source_locators_survive(self):
        row = self.rows()["R-04"]
        self.assertEqual(row["finding_ids"], ["F-IAM", "F-RIS"])
        self.assertEqual(row["source_refs"], ["synthetic-evidence.md#iam-review-records", "synthetic-evidence.md#ris-recovery-records"])

    def test_source_hash_is_canonical_and_report_is_reproducible(self):
        left = planner.build(self.data)
        right = planner.build(dict(reversed(list(self.data.items()))))
        canonical = json.dumps(self.data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        self.assertEqual(left["source_sha256"], hashlib.sha256(canonical.encode()).hexdigest())
        self.assertEqual(left, right)
        for renderer in (planner.render_csv, planner.render_html, planner.render_markdown):
            self.assertEqual(renderer(left), renderer(right))

    def test_snapshot_is_independent_of_input_and_output_mutations(self):
        result = planner.build(self.data)
        retained = copy.deepcopy(result["source_input"])
        self.rec("R-01")["assumptions"].append("later caller edit")
        result["recommendations"][0]["maturity_hypothesis"]["target"] = 5
        self.assertEqual(result["source_input"], retained)

    def test_extensions_are_retained_not_silently_dropped(self):
        self.data["integration_notes"] = {"register_version": "draft-7", "reviewer": None}
        self.assertEqual(planner.build(self.data)["source_input"]["integration_notes"], self.data["integration_notes"])

    def test_html_text_is_inert_and_unicode_preserved(self):
        self.rec("R-01")["title"] = '<script>alert("x")</script> | café Ω\nnext'
        rendered = planner.render_html(planner.build(self.data))
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("café Ω", rendered)
        self.assertIn('scope="col"', rendered)
        self.assertIn('scope="row"', rendered)
        self.assertIn('<caption>', rendered)

    def test_csv_unknown_lists_multiline_and_formula_text(self):
        self.rec("R-01")["title"] = '=SUM(1,2)\nsecond | Ω'
        result = planner.build(self.data)
        rows = {row["id"]: row for row in csv.DictReader(io.StringIO(planner.render_csv(result)))}
        self.assertEqual(rows["R-01"]["title"], "'=SUM(1,2)\nsecond | Ω")
        self.assertEqual(rows["R-06"]["effort_high"], "UNKNOWN")
        self.assertEqual(rows["R-07"]["start_high"], "UNKNOWN")
        self.assertEqual(json.loads(rows["R-04"]["depends_on"]), ["R-02", "R-03"])
        self.assertEqual(result["source_input"]["recommendations"][0]["title"], '=SUM(1,2)\nsecond | Ω')

    def test_cycle_and_dangling_references_are_actionable(self):
        self.rec("R-01")["depends_on"] = ["R-05"]
        with self.assertRaisesRegex(planner.InputError, "cycle.*R-01"):
            planner.build(self.data)
        self.rec("R-01")["depends_on"] = ["MISSING"]
        with self.assertRaisesRegex(planner.InputError, "dangling prerequisite"):
            planner.build(self.data)
        self.rec("R-01")["depends_on"] = []
        self.rec("R-01")["finding_ids"] = ["MISSING"]
        with self.assertRaisesRegex(planner.InputError, "dangling finding"):
            planner.build(self.data)

    def test_duplicate_ids_capacities_and_keys_are_rejected(self):
        duplicate = copy.deepcopy(self.data)
        duplicate["recommendations"].append(copy.deepcopy(duplicate["recommendations"][0]))
        with self.assertRaisesRegex(planner.InputError, "duplicate id"):
            planner.build(duplicate)
        self.data["role_capacity"].append(copy.deepcopy(self.data["role_capacity"][0]))
        with self.assertRaisesRegex(planner.InputError, "duplicate"):
            planner.build(self.data)
        with self.assertRaisesRegex(planner.InputError, "duplicate JSON key"):
            planner.strict_json('{"x":1,"x":2}')

    def test_invalid_numeric_values_and_implicit_unknown_are_rejected(self):
        for value in (True, -1, 1.5, "10"):
            data = copy.deepcopy(self.data)
            data["recommendations"][0]["not_before_day"] = value
            with self.subTest(value=value), self.assertRaises(planner.InputError):
                planner.build(data)
        self.rec("R-01")["duration_days"] = {"low": 20, "high": 10}
        with self.assertRaisesRegex(planner.InputError, "low exceeds high"):
            planner.build(self.data)
        del self.rec("R-01")["duration_days"]
        with self.assertRaisesRegex(planner.InputError, "explicit null"):
            planner.build(self.data)
        with self.assertRaisesRegex(planner.InputError, "nonfinite"):
            planner.strict_json('{"x":NaN}')

    def test_empty_draft_does_not_invent_work_or_findings(self):
        self.data.update(findings=[], recommendations=[], role_capacity=[])
        result = planner.build(self.data)
        self.assertEqual(result["recommendations"], [])
        self.assertEqual(result["role_capacity_review"], [])
        self.assertEqual(result["status"], "DRAFT_PLANNING_NOT_A_COMMITMENT")

    def test_cli_writes_four_reproducible_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = [sys.executable, str(ROOT / "planner.py"), str(ROOT / "synthetic.json"), "--out-dir", tmp]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            before = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
            self.assertEqual(set(before), {"roadmap.json", "roadmap.csv", "roadmap.md", "roadmap.html"})
            self.assertEqual(json.loads(before["roadmap.json"])["source_input"], self.data)
            again = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertEqual(before, {p.name: p.read_bytes() for p in Path(tmp).iterdir()})

    def test_cli_invalid_input_has_no_outputs_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"x":1,"x":2}', encoding="utf-8")
            out = Path(tmp) / "out"
            result = subprocess.run([sys.executable, str(ROOT / "planner.py"), str(path), "--out-dir", str(out)], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(out.exists())
            self.assertIn("duplicate JSON key", result.stderr)

    def test_cli_does_not_replace_source_with_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "roadmap.json"
            original = json.dumps(self.data)
            path.write_text(original, encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "planner.py"), str(path), "--out-dir", tmp], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(path.read_text(encoding="utf-8"), original)
            self.assertIn("overwrite source input", result.stderr)


if __name__ == "__main__":
    unittest.main()
