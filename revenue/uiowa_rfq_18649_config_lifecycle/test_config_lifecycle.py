"""Regression cases for the supplied-evidence model, not live infrastructure tests."""
from __future__ import annotations
import copy
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
if __package__:
    from . import config_lifecycle as assess
    from .synthetic_config import packet
else:
    import config_lifecycle as assess
    from synthetic_config import packet


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.data = packet()

    def result(self, cid="STUDENT"):
        return next(c for c in assess.analyze(self.data)["components"] if c["id"] == cid)

    def component(self, cid="STUDENT"):
        return next(c for c in self.data["components"] if c["id"] == cid)

    def exercise(self, eid="STUDENT_REBUILD"):
        return next(e for e in self.data["exercises"] if e["id"] == eid)

    def test_manual_can_demonstrate_current_snapshot(self):
        result = self.result()
        self.assertEqual(result["rebuild_status"], "demonstrated_current_snapshot")
        self.assertEqual(result["dependency_plan"]["dependency_first_order"], ["BASE", "STUDENT"])

    def test_automation_does_not_remove_gaps(self):
        result = self.result("RESEARCH")
        self.assertEqual(result["rebuild_status"], "preparation_gaps")
        self.assertIn("dependency_not_in_inventory:BUILD_CACHE_NOT_SUPPLIED", result["blockers"])
        self.assertIn("dependency_retired:RETIRED_BRIDGE", result["blockers"])
        self.assertEqual(result["criteria"]["recipe"]["status"], "reported_only")

    def test_old_success_and_in_place_repair_do_not_prove_current_rebuild(self):
        result = self.result("SIGNIN")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["rebuild_status"], "current_rebuild_not_demonstrated")
        self.assertFalse(result["exercises"][0]["current_manifest"])
        self.assertIn("not_a_from_scratch_rebuild", result["exercises"][1]["reasons"])

    def test_manual_and_automated_have_equal_evidence_rules(self):
        before = self.result()["rebuild_status"]
        self.component()["recipe_mode"] = "automated"
        self.assertEqual(before, self.result()["rebuild_status"])

    def test_shared_gap_propagates_without_new_source_invention(self):
        self.component("BASE")["revision"] = None
        for cid in ("BASE", "STUDENT", "SIGNIN"):
            self.assertIn("BASE:configuration:unknown", self.result(cid)["blockers"])

    def test_cycle_has_no_executable_order(self):
        self.component("BASE")["dependencies"] = ["STUDENT"]
        result = self.result()
        self.assertEqual(result["dependency_plan"]["dependency_first_order"], [])
        self.assertTrue(any("cycle" in p for p in result["blockers"]))

    def test_diamond_dependency_is_not_cycle(self):
        self.component()["dependencies"].append("SIGNIN")
        graph = self.result()["dependency_plan"]
        self.assertEqual(graph["problems"], [])
        self.assertEqual(graph["dependency_first_order"], ["BASE", "SIGNIN", "STUDENT"])

    def test_unknown_dependency_inventory_is_not_empty(self):
        self.component("BASE")["dependencies"] = None
        self.assertIn("dependency_inventory_unknown:BASE", self.result()["blockers"])

    def test_partial_collection_never_silently_complete(self):
        self.data["inventory_coverage"] = "partial"
        self.assertIn("collection_scope_not_complete", self.result()["blockers"])

    def test_empty_and_unknown_input_inventory_differ(self):
        self.component()["inputs"] = []
        self.assertEqual(self.result()["criteria"]["inputs"]["status"], "documented")
        self.component()["inputs"] = None
        self.assertEqual(self.result()["criteria"]["inputs"]["status"], "unknown")

    def test_exact_manifest_closure_required(self):
        self.exercise()["manifest"]["UNRELATED"] = "r1"
        self.assertEqual(self.result()["rebuild_status"], "current_rebuild_not_demonstrated")

    def test_fixture_locators_resolve_exact_source(self):
        for source in self.data["sources"]:
            index = int(source["locator"].rsplit("/", 1)[1])
            self.assertIs(source, self.data["sources"][index])

    def test_exercise_cannot_predate_current_revision(self):
        self.exercise()["on"] = "2026-08-30"
        self.assertIn("exercise_predates_current_revision:STUDENT", self.result()["exercises"][0]["reasons"])

    def test_extra_execution_component_not_hidden(self):
        self.exercise()["executed_steps"]["UNRELATED"] = ["provision"]
        self.assertEqual(self.result()["rebuild_status"], "current_rebuild_not_demonstrated")

    def test_missing_required_step_not_demonstrated(self):
        self.exercise()["executed_steps"]["BASE"] = ["provision"]
        self.assertEqual(self.result()["rebuild_status"], "current_rebuild_not_demonstrated")

    def test_unknown_business_check_not_success(self):
        self.exercise()["checks"]["service_behavior"] = "unknown"
        self.assertEqual(self.result()["rebuild_status"], "current_rebuild_not_demonstrated")

    def test_no_business_check_definition(self):
        self.component()["checks"] = []
        self.assertIn("STUDENT:business_checks_unknown", self.result()["blockers"])

    def test_extra_failed_check_cannot_be_hidden(self):
        self.exercise()["checks"]["data_loss"] = "fail"
        self.assertEqual(self.result()["rebuild_status"], "current_rebuild_not_demonstrated")

    def test_latest_failure_supersedes_old_success(self):
        later = copy.deepcopy(self.exercise())
        later.update(id="LATER", on="2026-09-13")
        later["checks"]["service_behavior"] = "fail"
        self.data["exercises"].append(later)
        self.assertEqual(self.result()["rebuild_status"], "current_rebuild_not_demonstrated")

    def test_same_day_disagreement_retained_without_fake_order(self):
        other = copy.deepcopy(self.exercise())
        other["id"] = "OTHER"
        other["checks"]["service_behavior"] = "fail"
        self.data["exercises"].append(other)
        self.assertEqual(self.result()["rebuild_status"], "conflicting_latest_exercises")

    def test_reported_exercise_not_artifact(self):
        sid = self.exercise()["evidence"][0]
        next(s for s in self.data["sources"] if s["id"] == sid)["kind"] = "interview"
        self.assertEqual(self.result()["rebuild_status"], "current_rebuild_not_demonstrated")

    def test_artifact_cannot_predate_exercise(self):
        self.exercise()["on"] = "2026-09-14"
        reasons = self.result()["exercises"][0]["reasons"]
        self.assertIn("exercise_artifact_predates_exercise_or_is_absent", reasons)

    def test_unresolved_source_id_diagnosed(self):
        self.component()["config_evidence"] = ["NOT_SUPPLIED"]
        self.assertEqual(self.result()["criteria"]["configuration"]["status"], "unresolved_reference")

    def test_selected_horizon_explicit_and_effective(self):
        self.data["evidence_max_age_days"] = 1
        self.assertEqual(self.result()["criteria"]["configuration"]["status"], "stale_only")

    def test_changed_revision_records_conflict(self):
        extra = copy.deepcopy(self.component()["changes"][0])
        extra.update(id="newer", revision="r2", on="2026-09-15")
        self.component()["changes"].append(extra)
        self.assertEqual(self.result()["criteria"]["change_trace"]["status"], "conflicting_records")

    def test_rejected_and_accepted_review_conflict(self):
        extra = copy.deepcopy(self.component()["changes"][0])
        extra.update(id="reject", review_outcome="rejected")
        self.component()["changes"].append(extra)
        self.assertEqual(self.result()["criteria"]["change_trace"]["status"], "conflicting_records")

    def test_retirement_with_consumer_needs_followup(self):
        retired = self.result("RETIRED_BRIDGE")
        self.assertEqual(retired["retirement"]["status"], "follow_up_required")
        self.assertEqual(retired["retirement"]["observed_active_consumers"], ["RESEARCH"])
        self.assertEqual(retired["rebuild_status"], "not_applicable_retired")

    def test_orphan_exercise_not_discarded(self):
        self.exercise()["target"] = "NOT_IN_INVENTORY"
        self.assertIn("STUDENT_REBUILD", assess.analyze(self.data)["orphan_exercises"])

    def test_duplicate_and_nonfinite_json_rejected(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
            with self.assertRaises(assess.InputError):
                assess.loads(raw)

    def test_duplicate_component_rejected(self):
        self.data["components"].append(copy.deepcopy(self.component()))
        with self.assertRaises(assess.InputError):
            assess.analyze(self.data)

    def test_unknown_fields_and_bool_horizon_rejected(self):
        self.data["unused"] = True
        with self.assertRaises(assess.InputError):
            assess.analyze(self.data)
        del self.data["unused"]
        self.data["evidence_max_age_days"] = True
        with self.assertRaises(assess.InputError):
            assess.analyze(self.data)

    def test_future_and_invalid_dates_rejected(self):
        for day in ("2026-09-20", "2026-02-30", "20260901"):
            self.data["sources"][0]["observed_on"] = day
            with self.assertRaises(assess.InputError):
                assess.analyze(self.data)

    def test_deterministic_reports_and_source_hashes(self):
        first = assess.analyze(self.data)
        self.assertEqual(first, assess.analyze(copy.deepcopy(self.data)))
        self.assertEqual(assess.markdown(first), assess.markdown(first))
        self.data["sources"][0]["excerpt"] += " changed"
        second = assess.analyze(self.data)
        self.assertNotEqual(first["input_sha256"], second["input_sha256"])
        source_id = self.data["sources"][0]["id"]
        old_hash = next(s["excerpt_sha256"] for s in first["sources"] if s["id"] == source_id)
        new_hash = next(s["excerpt_sha256"] for s in second["sources"] if s["id"] == source_id)
        self.assertNotEqual(old_hash, new_hash)

    def test_unicode_multiline_and_formula_safe_csv(self):
        self.component()["owner_role"] = "=DANGEROUS()"
        self.data["sources"][0]["excerpt"] = "Fictional café | & <tag>\nsecond line"
        report = assess.analyze(self.data)
        rows = list(csv.DictReader(io.StringIO(assess.worksheet(report))))
        self.assertEqual(len(rows), 40)
        self.assertTrue(next(r for r in rows if r["component_id"] == "STUDENT")["proposed_owner_role"].startswith("'="))
        self.assertIn("café \\| &amp; &lt;tag&gt;<br>second line", assess.markdown(report))

    def test_cli_roundtrip_and_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_path = root / "packet.json"
            packet_path.write_text(json.dumps(self.data), encoding="utf-8")
            out = root / "report"
            command = [sys.executable, str(Path(assess.__file__)), str(packet_path), "--out", str(out)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = (out / "report.json").read_text()
            self.assertEqual(json.loads(saved), assess.analyze(self.data))
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(saved, (out / "report.json").read_text())

    def test_cli_malformed_input_has_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src, dst = root / "bad.json", root / "output"
            src.write_text('{"x": 1, "x": 2}')
            result = subprocess.run([sys.executable, str(Path(assess.__file__)), str(src), "--out", str(dst)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(dst.exists())


if __name__ == "__main__":
    unittest.main()
