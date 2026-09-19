"""Deterministic, offline acceptance and malformed-record tests."""
from __future__ import annotations

import csv
import io
import json
import math
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

if __package__:
    from .contract import InvalidRecord, SCHEMA, check
    from .example import build
    from .lifecycle import analyze, digest, export, load, main, markdown
else:
    from contract import InvalidRecord, SCHEMA, check
    from example import build
    from lifecycle import analyze, digest, export, load, main, markdown


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.data = build()

    def test_expected_rehearsal_metrics(self):
        report = analyze(self.data)
        a, b, partial, drift = report["comparisons"]
        self.assertEqual(a["metrics"]["passed"]["delta"], -25)
        self.assertEqual(a["metrics"]["repair_seconds"]["delta"], 45)
        self.assertEqual(a["metrics"]["latency_ms"]["delta"], -250)
        self.assertEqual(b["metrics"]["passed"]["delta"], 50)
        self.assertEqual(b["metrics"]["repair_seconds"]["delta"], -75)
        self.assertEqual(b["metrics"]["latency_ms"]["delta"], 200)
        self.assertEqual(b["changed_fields"], ["model", "prompt_id", "source_ids"])
        self.assertEqual(partial["state"], "partial")
        self.assertEqual(drift["state"], "not_comparable")
        self.assertEqual(report["replay_state"], "not_executed")
        self.assertEqual(report["data_status"], "synthetic")

    def test_unknown_not_zero(self):
        report = analyze(self.data)
        metric = report["runs"][3]["metrics"]["passed"]
        self.assertEqual((metric["value"], metric["measured"], metric["unknown"]), (100, 3, 1))
        self.assertIsNone(report["comparisons"][2]["metrics"]["passed"]["delta"])
        self.assertIn("measurement_coverage_differs", report["comparisons"][2]["metrics"]["passed"]["reasons"])

    def test_cohort_not_comparable_even_apparent_improvement(self):
        m = analyze(self.data)["comparisons"][-1]["metrics"]["passed"]
        self.assertFalse(m["comparable"])
        self.assertEqual(set(m["reasons"]), {"kind_differs", "cohort_differs", "dataset_id_digest_differs", "case_population_differs", "measurement_coverage_differs"})

    def test_missing_material_and_ownership_are_separate(self):
        report = analyze(self.data)
        self.assertEqual(report["versions"][-1]["gaps"], ["source-unknown:digest_unknown", "model_revision_unknown", "support_owner_unknown"])
        self.assertEqual(report["runs"][-1]["missing_outputs"], ["z"])
        self.assertEqual(report["incidents"][-1]["evidence_state"], "incomplete")
        self.assertEqual(report["incidents"][0]["state"], "reported_resolved")

    def test_digest_tampering_rejected(self):
        self.data["artifacts"][0]["content"] += " changed"
        with self.assertRaisesRegex(InvalidRecord, "digest mismatch"):
            analyze(self.data)

    def test_declared_digest_not_byte_verification(self):
        self.data["artifacts"][6]["content"] = None  # unknown source already has no digest
        fixed = next(a for a in self.data["artifacts"] if a["id"] == "dataset-fixed")
        fixed["content"] = None
        pair = analyze(self.data)["comparisons"][0]
        self.assertEqual(pair["state"], "comparable")
        self.assertEqual(pair["context_basis"], "declared_or_unknown_digests")

    def test_unknown_comparison_digest_prevents_delta(self):
        next(a for a in self.data["artifacts"] if a["id"] == "dataset-fixed")["sha256"] = None
        m = analyze(self.data)["comparisons"][0]["metrics"]["passed"]
        self.assertIsNone(m["delta"])
        self.assertIn("dataset_id_digest_unknown", m["reasons"])

    def test_duplicate_ids_rejected_in_every_collection(self):
        for collection in ("artifacts", "versions", "runs", "comparisons", "incidents"):
            with self.subTest(collection=collection):
                data = build()
                data[collection].append(data[collection][0].copy())
                with self.assertRaisesRegex(InvalidRecord, "duplicate"):
                    analyze(data)

    def test_duplicate_case_rejected(self):
        self.data["runs"][0]["cases"].append(self.data["runs"][0]["cases"][0].copy())
        with self.assertRaisesRegex(InvalidRecord, "duplicate"):
            analyze(self.data)

    def test_dangling_and_wrong_kind_references(self):
        for key in ("missing-prompt", "config"):
            self.data["versions"][0]["prompt_id"] = key
            with self.subTest(key=key), self.assertRaises(InvalidRecord):
                analyze(self.data)

    def test_parent_cycle_and_cross_workflow_rejected(self):
        self.data["versions"][0]["parent_id"] = "v4"
        with self.assertRaisesRegex(InvalidRecord, "parent"):
            analyze(self.data)
        self.data = build()
        self.data["versions"][1]["workflow_id"] = "other"
        with self.assertRaisesRegex(InvalidRecord, "parent"):
            analyze(self.data)

    def test_invalid_timestamps_rejected(self):
        for bad in ("2026-09-19", "2026-09-19T12:00:00", "2026-02-30T12:00:00Z", "2026-09-19T12:00:00+24:00"):
            with self.subTest(bad=bad):
                self.data["as_of"] = bad
                with self.assertRaises(InvalidRecord):
                    analyze(self.data)

    def test_future_and_pre_version_run_rejected(self):
        for when in ("2026-10-01T12:00:00Z", "2026-08-01T12:00:00Z"):
            self.data["runs"][0]["observed_at"] = when
            with self.subTest(when=when), self.assertRaises(InvalidRecord):
                analyze(self.data)

    def test_unavailable_at_time_of_use_rejected(self):
        self.data["artifacts"][0]["captured_at"] = "2026-09-19T11:00:00Z"
        with self.assertRaisesRegex(InvalidRecord, "captured after"):
            analyze(self.data)

    def test_nonfinite_negative_boolean_measurement_rejected(self):
        for value in (math.nan, math.inf, -1, True, "12"):
            with self.subTest(value=value):
                self.data["runs"][0]["cases"][0]["repair_seconds"] = value
                with self.assertRaises(InvalidRecord):
                    analyze(self.data)

    def test_empty_measurements_not_perfect(self):
        for run in self.data["runs"][:2]:
            for case in run["cases"]:
                case["passed"] = None
        m = analyze(self.data)["comparisons"][0]["metrics"]["passed"]
        self.assertIsNone(m["baseline"]["value"])
        self.assertIsNone(m["delta"])
        self.assertIn("no_measured_cases", m["reasons"])

    def test_empty_dataset_supported_without_invented_findings(self):
        for key in ("artifacts", "versions", "runs", "comparisons", "incidents"):
            self.data[key] = []
        report = analyze(self.data)
        self.assertEqual(report["versions"], [])
        self.assertEqual(report["comparisons"], [])

    def test_wrong_followup_rejected(self):
        self.data["incidents"][0]["followup_comparison_id"] = "prompt-trial"
        with self.assertRaisesRegex(InvalidRecord, "follow-up"):
            analyze(self.data)

    def test_resolution_before_opening_rejected(self):
        self.data["incidents"][0]["resolved_at"] = "2026-09-01T00:00:00Z"
        with self.assertRaisesRegex(InvalidRecord, "resolution"):
            analyze(self.data)

    def test_schema_rejects_extra_missing_and_wrong_types(self):
        for mutation in (lambda d: d.update(surprise=True), lambda d: d.pop("runs"), lambda d: d.update(schema_version=True)):
            data = build()
            mutation(data)
            with self.assertRaises(InvalidRecord):
                analyze(data)

    def test_json_duplicate_properties_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"runs": [], "runs": []}')
            with self.assertRaisesRegex(InvalidRecord, "duplicate JSON property"):
                load(path)
            path.write_text('{"value": NaN}')
            with self.assertRaisesRegex(InvalidRecord, "non-finite"):
                load(path)

    def test_timezone_equivalence_and_case_order(self):
        old = analyze(self.data)
        self.data["as_of"] = "2026-09-19T08:00:00-04:00"
        self.data["runs"][1]["cases"].reverse()
        self.assertEqual(analyze(self.data)["comparisons"], old["comparisons"])

    def test_alias_dataset_with_identical_bytes_is_comparable(self):
        a = next(a for a in self.data["artifacts"] if a["id"] == "dataset-fixed").copy()
        a["id"] = "dataset-alias"
        self.data["artifacts"].append(a)
        self.data["runs"][1]["dataset_id"] = a["id"]
        self.assertEqual(analyze(self.data)["comparisons"][0]["state"], "comparable")

    def test_csv_unicode_multiline_and_formula_display(self):
        self.data["versions"][0]["change_reason"] = "=SUM(A1:A2)\nFictional café | 再現"
        report = analyze(self.data)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            export(report, target)
            with (target / "timeline.csv").open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[0]["description"], "'" + self.data["versions"][0]["change_reason"])
            self.assertEqual(json.loads((target / "review.json").read_text())["versions"][0]["change_reason"], self.data["versions"][0]["change_reason"])
        self.assertIn("&#124;", markdown(report))
        self.assertIn("<br>", markdown({**report, "versions": [{**report["versions"][0], "gaps": ["a\nb"]}]}))

    def test_deterministic_export_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = root / "record.json"
            record.write_text(json.dumps(self.data), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(record), "--out", str(root / "a")]), 0)
                self.assertEqual(main([str(record), "--out", str(root / "b")]), 0)
            for name in ("review.json", "review.md", "timeline.csv"):
                self.assertEqual((root / "a" / name).read_bytes(), (root / "b" / name).read_bytes())
            record.write_text("not JSON")
            with redirect_stderr(io.StringIO()) as error:
                self.assertEqual(main([str(record), "--out", str(root / "bad")]), 2)
            self.assertIn("INVALID:", error.getvalue())
            self.assertFalse((root / "bad").exists())

    def test_machine_schema_available(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["--schema"]), 0)
        self.assertEqual(json.loads(output.getvalue()), SCHEMA)
        check(build())


    def test_late_investigation_not_evidence_for_prior_resolution(self):
        for artifact in self.data["artifacts"]:
            if artifact["kind"] == "investigation":
                artifact["captured_at"] = "2026-09-18T13:00:00Z"
        with self.assertRaisesRegex(InvalidRecord, "after its recorded use"):
            analyze(self.data)

    def test_late_correction_or_followup_not_resolution_support(self):
        self.data["incidents"][0]["resolved_at"] = "2026-09-14T13:00:00Z"
        with self.assertRaisesRegex(InvalidRecord, "corrective version follows"):
            analyze(self.data)
        self.data["incidents"][0]["resolved_at"] = "2026-09-15T13:00:00Z"
        with self.assertRaisesRegex(InvalidRecord, "follow-up follows"):
            analyze(self.data)

    def test_numeric_extremes_are_finite_or_explained(self):
        self.data["runs"][0]["cases"][0]["latency_ms"] = 10 ** 1000
        with self.assertRaises(InvalidRecord):
            analyze(self.data)
        for case in self.data["runs"][0]["cases"]:
            case["latency_ms"] = 1e308
        self.assertEqual(analyze(self.data)["runs"][0]["metrics"]["latency_ms"]["value"], 1e308)

    def test_nonstandard_offset_is_not_silently_normalized(self):
        self.data["as_of"] = "2026-09-19T12:00:00+03:60"
        with self.assertRaises(InvalidRecord):
            analyze(self.data)

    def test_package_imports_ignore_unrelated_generic_modules(self):
        root = str(Path(__file__).resolve().parent.parent)
        package = Path(__file__).resolve().parent.name
        code = ("import sys,types; sys.path.insert(0," + repr(root) + "); "
                "sys.modules['contract']=types.ModuleType('contract'); "
                "sys.modules['lifecycle']=types.ModuleType('lifecycle'); "
                "sys.modules['example']=types.ModuleType('example'); "
                "from " + package + ".example import build; "
                "from " + package + ".lifecycle import analyze; "
                "print(analyze(build())['replay_state'])")
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "not_executed")


if __name__ == "__main__":
    unittest.main()
