import copy
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

import lifecycle as L
from make_fixture import build


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.bundle = build()

    def inspect(self):
        return L.inspect(self.bundle)

    def artifact(self, key):
        return next(x for x in self.bundle["artifacts"] if x["id"] == key)

    def rewrite(self, key, content):
        a = self.artifact(key)
        a["content"] = content
        a["sha256"] = L.sha256(content)

    def test_reference_timeline(self):
        r = self.inspect()
        self.assertEqual([x["evaluation"]["passed_cases"] for x in r["releases"]], [2, 1, 3, 3])
        self.assertEqual([x["evaluation"]["scored_cases"] for x in r["releases"]], [3, 3, 3, 3])
        self.assertEqual([x["evaluation"]["declared_cases"] for x in r["releases"]], [3, 3, 3, 4])
        self.assertAlmostEqual(r["transitions"][0]["paired_pass_rate_delta"], -1/3)
        self.assertAlmostEqual(r["transitions"][1]["paired_pass_rate_delta"], 2/3)
        self.assertEqual(r["transitions"][0]["changed_components"], ["prompt"])
        self.assertEqual(r["transitions"][1]["changed_components"], ["model"])
        self.assertEqual(r["transitions"][2]["comparison_status"], "NOT_COMPARABLE")
        self.assertIsNone(r["transitions"][2]["paired_pass_rate_delta"])
        self.assertEqual(r["releases"][3]["evaluation"]["coverage"], .75)
        self.assertTrue(all(x["rerun_status"] == "NOT_PERFORMED" for x in r["releases"]))

    def test_fixture_generator_is_deterministic(self):
        self.assertEqual(L.canonical(build()), L.canonical(build()))

    def test_tampered_model_retention_is_visible(self):
        self.bundle["releases"][0]["model"]["artifact_id"] = "code"
        self.artifact("code")["content"] += " altered"
        self.assertIn("MODEL_ARTIFACT_MISMATCH", self.inspect()["releases"][0]["lineage_gaps"])

    def test_runtime_unknown_is_not_success(self):
        r = self.inspect()["releases"][1]["runtime"]
        self.assertEqual((r["recorded_runs"], r["success"], r["error"], r["unknown"]), (3, 1, 1, 1))
        self.assertEqual(r["latency_observations"], 0)

    def test_missing_owner_and_revision_remain_visible(self):
        gaps = self.inspect()["releases"][3]["lineage_gaps"]
        self.assertIn("MODEL_REVISION_NOT_RECORDED", gaps)
        self.assertIn("SUPPORT_ROLE_NOT_RECORDED", gaps)

    def test_tampered_output_unscored(self):
        self.artifact("output-v1-a")["content"] += " "
        r = self.inspect()
        self.assertEqual(r["artifact_integrity"]["output-v1-a"], "MISMATCH")
        self.assertEqual(r["releases"][0]["evaluation"]["scored_cases"], 2)
        self.assertEqual(r["transitions"][0]["comparison_status"], "PARTIAL_COHORT")

    def test_unavailable_source_not_silent_pass(self):
        self.artifact("source-b")["content"] = None
        r = self.inspect()
        self.assertEqual(r["artifact_integrity"]["source-b"], "UNAVAILABLE")
        self.assertEqual(r["releases"][0]["evaluation"]["scored_cases"], 0)
        self.assertIsNone(r["releases"][0]["evaluation"]["pass_rate_scored"])

    def test_wrong_input_binding_unscored(self):
        self.bundle["runs"][0]["input_artifact_id"] = "input-b"
        case = self.inspect()["releases"][0]["evaluation"]["cases"][0]
        self.assertEqual(case["reason"], "INPUT_BINDING_MISMATCH")

    def test_source_not_in_release_unscored(self):
        self.bundle["releases"][0]["input_source_ids"].remove("source-a")
        self.assertEqual(self.inspect()["releases"][0]["evaluation"]["cases"][0]["reason"], "SOURCE_NOT_IN_RELEASE")

    def test_duplicate_evaluation_rejected(self):
        run = copy.deepcopy(self.bundle["runs"][0]); run["id"] = "other"
        self.bundle["runs"].append(run)
        with self.assertRaisesRegex(L.EvidenceError, "duplicate evaluation"):
            self.inspect()

    def test_duplicate_ids_rejected(self):
        self.bundle["artifacts"].append(copy.deepcopy(self.bundle["artifacts"][0]))
        with self.assertRaisesRegex(L.EvidenceError, "duplicate id"):
            self.inspect()

    def test_unresolved_reference_rejected(self):
        self.bundle["runs"][0]["release_id"] = "absent"
        with self.assertRaisesRegex(L.EvidenceError, "unresolved reference"):
            self.inspect()

    def test_timezone_required(self):
        self.bundle["releases"][0]["created_at"] = "2026-09-01T09:00:00"
        with self.assertRaisesRegex(L.EvidenceError, "UTC offset"):
            self.inspect()

    def test_equivalent_timezone_and_input_order(self):
        self.bundle["releases"][0]["created_at"] = "2026-09-01T05:00:00-04:00"
        self.bundle["releases"].reverse()
        self.bundle["events"].reverse()
        r = self.inspect()
        self.assertEqual([x["release_id"] for x in r["releases"]], ["v1", "v2", "v3", "v4"])
        self.assertEqual(r["timeline"][0]["id"], "baseline")

    def test_cycle_rejected(self):
        self.bundle["releases"][0]["parent_id"] = "v4"
        with self.assertRaisesRegex(L.EvidenceError, "parent must precede"):
            self.inspect()

    def test_cross_workflow_parent_rejected(self):
        self.bundle["releases"][1]["workflow_id"] = "different"
        with self.assertRaisesRegex(L.EvidenceError, "same workflow"):
            self.inspect()

    def test_run_before_release_rejected(self):
        self.bundle["runs"][0]["occurred_at"] = "2020-01-01T00:00:00Z"
        with self.assertRaisesRegex(L.EvidenceError, "cannot precede"):
            self.inspect()

    def test_boolean_negative_and_nonfinite_latency_rejected(self):
        for value in [True, -1, float("nan"), float("inf")]:
            self.bundle["runs"][0]["latency_ms"] = value
            with self.assertRaises(L.EvidenceError):
                self.inspect()

    def test_duplicate_and_nonfinite_json_rejected(self):
        for value in ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}']:
            with self.assertRaises(L.EvidenceError):
                L.load_json(value)

    def test_malformed_output_and_duplicate_keys_unscored(self):
        for value in ["not-json", '{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}']:
            self.rewrite("output-v1-a", value)
            self.assertEqual(self.inspect()["releases"][0]["evaluation"]["cases"][0]["status"], "UNSCORED")

    def test_boolean_does_not_equal_one(self):
        self.rewrite("expected-a", '{"value":1}')
        self.rewrite("output-v1-a", '{"value":true}')
        self.assertEqual(self.inspect()["releases"][0]["evaluation"]["cases"][0]["status"], "FAIL")

    def test_json_key_order_does_not_change_score(self):
        self.rewrite("output-v1-a", '{"deadline_days": 7, "owner": "release-duty"}')
        self.assertEqual(self.inspect()["releases"][0]["evaluation"]["cases"][0]["status"], "PASS")

    def test_unknown_evaluator_is_not_pass(self):
        self.bundle["releases"][1]["evaluator_id"] = "not-implemented"
        r = self.inspect()
        self.assertEqual(r["releases"][1]["evaluation"]["scored_cases"], 0)
        self.assertIsNone(r["transitions"][0]["paired_pass_rate_delta"])

    def test_absent_run_and_empty_cohort(self):
        self.bundle["runs"] = [r for r in self.bundle["runs"] if r["release_id"] != "v1"]
        r = self.inspect()
        self.assertEqual(r["releases"][0]["evaluation"]["unscored_cases"], 3)
        self.assertEqual(r["transitions"][0]["comparison_status"], "NO_PAIRED_EVIDENCE")
        self.bundle["releases"][0]["dataset_case_ids"] = []
        self.assertIsNone(self.inspect()["releases"][0]["evaluation"]["coverage"])

    def test_export_is_deterministic_and_lossless_json(self):
        r = self.inspect()
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory)/"a", Path(directory)/"b"
            L.export(r, a); L.export(r, b)
            for name in ["lifecycle-report.json", "lifecycle-report.md", "case-trace.csv"]:
                self.assertEqual((a/name).read_bytes(), (b/name).read_bytes())
            self.assertEqual(L.load_json((a/"lifecycle-report.json").read_text()), r)
            self.assertEqual(len(list(csv.reader(io.StringIO((a/"case-trace.csv").read_text())))), 14)

    def test_markup_and_csv_formula_text_are_inert(self):
        self.bundle["runs"][0]["id"] = '=HYPERLINK("bad")'
        self.bundle["events"][0]["summary"] = "<script>bad</script> | `bad`\nnext"
        r = self.inspect()
        rendered = L.markdown(r)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&#124;", rendered)
        with tempfile.TemporaryDirectory() as d:
            L.export(r, Path(d))
            rows = list(csv.reader(io.StringIO((Path(d)/"case-trace.csv").read_text(encoding="utf-8"))))
            self.assertTrue(rows[1][2].startswith("'="))
            self.assertEqual(r["releases"][0]["evaluation"]["cases"][0]["run_id"], '=HYPERLINK("bad")')

    def test_schema_flag_types_and_unknown_fields(self):
        for key, value in [("schema_version", True), ("synthetic", "yes"), ("extra", "oops")]:
            b = build(); b[key] = value
            with self.assertRaises(L.EvidenceError):
                L.inspect(b)

    def test_real_input_never_gets_synthetic_or_authority_claim(self):
        self.bundle["synthetic"] = False
        r = self.inspect()
        self.assertEqual(r["evidence_kind"], "UNVERIFIED_SOURCE_RETAINED_OUTPUT_RESCORING")
        self.assertNotIn("SYNTHETIC — NOT UNIVERSITY FINDINGS", L.markdown(r))
        self.assertNotIn("approval", r.keys())


if __name__ == "__main__":
    unittest.main()
