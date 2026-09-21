"""Assessment-time and known-empty coverage regressions for issue #16367.

All records are fictional. These exercise the retained assessor, not a second
implementation. The date grid is an exhaustive finite check, not sampled data.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "uiowa047_evidence_semantics_assessor", ROOT / "test_data_assessor.py"
)
if SPEC is None or SPEC.loader is None:
    raise ImportError("Cannot load the retained UIOWA-047 assessor")
assessor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assessor)
AS_OF = date(2026, 9, 19)

# Authored expected states; never regenerated from the implementation under test.
REHEARSAL_EXPECTATIONS = {
    "SYN-FUTURE": {"refresh_freshness": "UNKNOWN", "cleanup": "UNKNOWN"},
    "SYN-OMITTED": {"representativeness": "UNKNOWN"},
    "SYN-NULL": {"representativeness": "UNKNOWN"},
    "SYN-EMPTY": {"representativeness": "OBSERVED_GAP"},
    "SYN-STRING": {"representativeness": "UNKNOWN"},
    "SYN-MAPPING": {"representativeness": "UNKNOWN"},
    "SYN-NONSTRING": {"representativeness": "UNKNOWN"},
    "SYN-NESTED": {"representativeness": "UNKNOWN"},
    "SYN-CURRENT": {"refresh_freshness": "EVIDENCED", "cleanup": "EVIDENCED",
                    "representativeness": "EVIDENCED"},
    "SYN-CADENCE": {"refresh_freshness": "EVIDENCED"},
    "SYN-STALE": {"refresh_freshness": "OBSERVED_GAP"},
    "SYN-NOT-REQUIRED": {"cleanup": "EVIDENCED"},
}


class EvidenceSemanticsTests(unittest.TestCase):
    def payload(self, **fields):
        return {"label": "FICTIONAL evidence semantics regression",
                "as_of": AS_OF.isoformat(),
                "datasets": [{"dataset_id": "SYN-SEMANTICS", "service": "ESS",
                              "purpose": "Fictional evidence boundary", **fields}]}

    def check(self, check_id, **fields):
        report = assessor.evaluate_catalog(self.payload(**fields))
        return next(c for c in report["datasets"][0]["checks"]
                    if c["check_id"] == check_id)

    def assert_unknown(self, check_id, **fields):
        check = self.check(check_id, **fields)
        self.assertEqual(check["state"], assessor.UNKNOWN)
        self.assertTrue(check["follow_up"].strip())
        return check

    def test_future_refresh_cannot_evidence_a_past_assessment(self):
        check = self.assert_unknown("refresh_freshness", last_refreshed="2026-09-20",
                                    refresh_cadence_days=30)
        self.assertIn("2026-09-20", check["detail"])
        self.assertIn("2026-09-19", check["detail"])
        self.assertNotIn("age is -", check["detail"])

    def test_future_refresh_chronology_is_visible_even_without_valid_cadence(self):
        for cadence in (None, False, True, 0, -1, "30"):
            with self.subTest(cadence=cadence):
                check = self.assert_unknown("refresh_freshness", last_refreshed="2026-09-20",
                                            refresh_cadence_days=cadence)
                self.assertIn("after", check["detail"])
                self.assertIn("2026-09-19", check["detail"])

    def test_same_day_refresh_remains_evidenced(self):
        check = self.check("refresh_freshness", last_refreshed="2026-09-19",
                           refresh_cadence_days=1)
        self.assertEqual(check["state"], assessor.EVIDENCED)
        self.assertIn("0 days", check["detail"])

    def test_complete_refresh_date_cadence_grid(self):
        for age in range(-366, 367):
            stamp = (AS_OF - timedelta(days=age)).isoformat()
            for cadence in (1, 30, 365):
                with self.subTest(age=age, cadence=cadence):
                    expected = (assessor.UNKNOWN if age < 0 else
                                assessor.OBSERVED_GAP if age > cadence else assessor.EVIDENCED)
                    self.assertEqual(self.check("refresh_freshness", last_refreshed=stamp,
                                                refresh_cadence_days=cadence)["state"], expected)

    def test_future_cleanup_verification_is_unknown_not_completed_evidence(self):
        check = self.assert_unknown("cleanup", cleanup_required=True,
                                    cleanup_last_verified="2026-09-20")
        self.assertIn("2026-09-20", check["detail"])
        self.assertIn("2026-09-19", check["detail"])

    def test_same_day_and_earlier_cleanup_dates_remain_evidenced(self):
        for stamp in ("2026-09-19", "2026-09-18", "2024-02-29", "0001-01-01"):
            with self.subTest(stamp=stamp):
                self.assertEqual(self.check("cleanup", cleanup_required=True,
                                            cleanup_last_verified=stamp)["state"], assessor.EVIDENCED)

    def test_cleanup_date_grid(self):
        for age in range(-366, 367):
            stamp = (AS_OF - timedelta(days=age)).isoformat()
            with self.subTest(age=age):
                self.assertEqual(self.check("cleanup", cleanup_required=True,
                                            cleanup_last_verified=stamp)["state"],
                                 assessor.UNKNOWN if age < 0 else assessor.EVIDENCED)

    def test_nonapplicable_cleanup_does_not_require_a_date(self):
        for stamp in (None, "2026-09-20", "not-a-date", {}, []):
            with self.subTest(stamp=stamp):
                self.assertEqual(self.check("cleanup", cleanup_required=False,
                                            cleanup_last_verified=stamp)["state"], assessor.EVIDENCED)

    def test_future_date_does_not_invent_cleanup_applicability(self):
        for declaration in (None, 0, "true"):
            with self.subTest(declaration=declaration):
                self.assert_unknown("cleanup", cleanup_required=declaration,
                                    cleanup_last_verified="2026-09-20")

    def test_omitted_coverage_is_not_an_observed_missing_case(self):
        self.assert_unknown("representativeness", required_boundary_cases=["empty"])

    def test_null_coverage_is_not_an_observed_missing_case(self):
        self.assert_unknown("representativeness", required_boundary_cases=["empty"],
                            covered_boundary_cases=None)

    def test_explicit_empty_coverage_is_an_observed_gap(self):
        check = self.check("representativeness", required_boundary_cases=["empty"],
                           covered_boundary_cases=[])
        self.assertEqual(check["state"], assessor.OBSERVED_GAP)
        self.assertEqual(check["detail"], "Missing boundary cases: empty")

    def test_unknown_requirement_inventory_precludes_a_coverage_verdict(self):
        for required in (None, [], "empty", {"empty": True}, 1, True, ("empty",)):
            for covered in (None, [], ["empty"], [None]):
                with self.subTest(required=required, covered=covered):
                    self.assert_unknown("representativeness", required_boundary_cases=required,
                                        covered_boundary_cases=covered)

    def test_nonlist_coverage_is_not_coerced_to_case_identities(self):
        for covered in ("a", "", {"a": False}, {}, True, False, 1, 0, 1.5, ("a",), {"a"}):
            with self.subTest(covered=covered):
                self.assert_unknown("representativeness", required_boundary_cases=["a"],
                                    covered_boundary_cases=covered)

    def test_invalid_required_entries_are_unknown_without_coercion(self):
        for bad in (None, True, 1, 1.5, [], {}, "", " ", "\t\n", "\u2003"):
            with self.subTest(bad=bad):
                self.assert_unknown("representativeness", required_boundary_cases=["a", bad],
                                    covered_boundary_cases=["a", "1", "True"])

    def test_invalid_covered_entries_do_not_count_as_evidence_or_gap(self):
        for bad in (None, True, 1, 1.5, [], {}, "", " ", "\t\n", "\u2003"):
            with self.subTest(bad=bad):
                self.assert_unknown("representativeness", required_boundary_cases=["a"],
                                    covered_boundary_cases=["a", bad])

    def test_nonstring_required_and_string_covered_do_not_alias(self):
        self.assert_unknown("representativeness", required_boundary_cases=[1],
                            covered_boundary_cases=["1"])

    def test_case_identity_is_not_silently_trimmed_folded_or_normalized(self):
        for required, covered in (("A", "a"), ("a", " a"), ("a", "a "),
                                  ("\u00e9", "e\u0301")):
            with self.subTest(required=required, covered=covered):
                self.assertEqual(self.check("representativeness", required_boundary_cases=[required],
                                            covered_boundary_cases=[covered])["state"], assessor.OBSERVED_GAP)

    def test_duplicates_and_order_preserve_unique_case_count(self):
        one = self.check("representativeness", required_boundary_cases=["b", "a", "a"],
                         covered_boundary_cases=["a", "b", "b"])
        two = self.check("representativeness", required_boundary_cases=["a", "b"],
                         covered_boundary_cases=["b", "a"])
        self.assertEqual(one, two)
        self.assertEqual(one["state"], assessor.EVIDENCED)
        self.assertIn("All 2", one["detail"])

    def test_extra_valid_cases_do_not_invalidate_documented_coverage(self):
        self.assertEqual(self.check("representativeness", required_boundary_cases=["a"],
                                    covered_boundary_cases=["a", "b"])["state"], assessor.EVIDENCED)

    def test_missing_cases_are_reported_in_stable_order(self):
        check = self.check("representativeness", required_boundary_cases=["z", "b", "a", "b"],
                           covered_boundary_cases=["z"])
        self.assertEqual(check["state"], assessor.OBSERVED_GAP)
        self.assertEqual(check["detail"], "Missing boundary cases: a, b")

    def test_input_and_unknowns_are_preserved_through_evaluation(self):
        payload = self.payload(last_refreshed="2026-09-20", refresh_cadence_days=30,
                               required_boundary_cases=["a"], covered_boundary_cases=None,
                               cleanup_required=True, cleanup_last_verified="2026-09-20")
        original = deepcopy(payload)
        report = assessor.evaluate_catalog(payload)
        self.assertEqual(payload, original)
        self.assertEqual(report["summary"], {"EVIDENCED": 0, "OBSERVED_GAP": 0, "UNKNOWN": 7})
        self.assertEqual(sum(report["summary"].values()), 7)

    def test_rehearsal_has_explicit_authored_expected_states(self):
        payload = json.loads((ROOT / "fixtures/evidence_semantics.synthetic.json").read_text(encoding="utf-8"))
        self.assertIn("FICTIONAL", payload["label"])
        original = deepcopy(payload)
        report = assessor.evaluate_catalog(payload)
        self.assertEqual(payload, original)
        self.assertEqual({row["dataset_id"] for row in report["datasets"]}, set(REHEARSAL_EXPECTATIONS))
        self.assertEqual(sum(report["summary"].values()), 7 * len(REHEARSAL_EXPECTATIONS))
        for row in report["datasets"]:
            states = {check["check_id"]: check["state"] for check in row["checks"]}
            for check_id, expected in REHEARSAL_EXPECTATIONS[row["dataset_id"]].items():
                with self.subTest(dataset=row["dataset_id"], check=check_id):
                    self.assertEqual(states[check_id], expected)

    def test_real_cli_formats_retain_states_and_do_not_modify_input(self):
        source = ROOT / "fixtures/evidence_semantics.synthetic.json"
        original = source.read_bytes()
        command = [sys.executable, *(["-O"] if sys.flags.optimize else []),
                   "-B", str(ROOT / "test_data_assessor.py"), str(source)]
        with tempfile.TemporaryDirectory(prefix="uiowa047-semantic-cli-") as temp:
            for fmt in ("json", "markdown"):
                with self.subTest(fmt=fmt):
                    destination = Path(temp) / ("report." + ("json" if fmt == "json" else "md"))
                    result = subprocess.run([*command, "--format", fmt, "--output", str(destination)],
                                            capture_output=True, text=True, timeout=20, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, "")
                    raw = destination.read_bytes()
                    repeated = subprocess.run([*command, "--format", fmt], capture_output=True,
                                              text=True, timeout=20, check=False)
                    self.assertEqual(repeated.returncode, 0, repeated.stderr)
                    self.assertEqual(repeated.stdout.encode(), raw)
                    if fmt == "json":
                        report = json.loads(raw)
                        for row in report["datasets"]:
                            states = {check["check_id"]: check["state"] for check in row["checks"]}
                            for check_id, expected in REHEARSAL_EXPECTATIONS[row["dataset_id"]].items():
                                self.assertEqual(states[check_id], expected)
                    else:
                        text = raw.decode()
                        self.assertIn("FICTIONAL", text)
                        self.assertIn("| SYN-EMPTY | representativeness | OBSERVED_GAP |", text)
                        self.assertIn("| SYN-OMITTED | representativeness | UNKNOWN |", text)
                        self.assertIn("| SYN-FUTURE | refresh_freshness | UNKNOWN |", text)
                        self.assertIn("| SYN-FUTURE | cleanup | UNKNOWN |", text)
                    self.assertEqual(source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
