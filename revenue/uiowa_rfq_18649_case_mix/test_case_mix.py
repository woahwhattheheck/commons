"""Independent exact-arithmetic and command-line checks for the case-mix lab."""
import copy
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

try:
    from . import case_mix as cm
except ImportError:
    import case_mix as cm


class CaseMixTests(unittest.TestCase):
    def setUp(self):
        self.packet = cm.demo()

    def test_reversal_has_independently_calculated_rates(self):
        result = cm.analyze(self.packet)
        a, b = result["groups"]
        self.assertEqual(a["raw"]["point"], "91/110")
        self.assertEqual(b["raw"]["point"], "23/40")
        self.assertEqual(a["standardized"]["point"], "1/2")
        self.assertEqual(b["standardized"]["point"], "29/40")
        pair = result["comparisons"][0]
        self.assertEqual(pair["raw"]["order"], "A_HIGHER")
        self.assertEqual(pair["standardized"]["order"], "B_HIGHER")
        self.assertEqual(pair["uniform_reversal"], "ROBUST_WITHIN_SUPPLIED_OUTCOME_BOUNDS")
        self.assertEqual({r["order"] for r in pair["strata"]}, {"B_HIGHER"})
        self.assertEqual(pair["standardized"]["difference"]["point"], "-9/40")

    def test_unknowns_stay_in_denominator_and_can_leave_robust_order(self):
        result = cm.analyze(cm.demo("missing-outcomes"))
        b = result["groups"][1]
        self.assertEqual(b["recorded_eligible"], 120)
        self.assertEqual(b["totals"]["unknown"], 20)
        self.assertEqual(b["raw"], {"low": "23/40", "high": "89/120", "point": None})
        self.assertEqual(b["standardized"], {"low": "29/40", "high": "33/40", "point": None})
        self.assertEqual(result["comparisons"][0]["uniform_reversal"], "ROBUST_WITHIN_SUPPLIED_OUTCOME_BOUNDS")

    def test_missing_category_is_not_dropped_or_renormalized(self):
        result = cm.analyze(cm.demo("missing-category"))
        b = result["groups"][1]
        self.assertEqual(b["reference_coverage"], "1/2")
        self.assertEqual(b["standardized"], {"low": "19/40", "high": "39/40", "point": None})
        self.assertEqual(result["comparisons"][0]["standardized"]["order"], "UNRESOLVED")
        self.assertEqual(result["comparisons"][0]["uniform_reversal"], "NOT_ASSESSABLE")

    def test_zero_weight_missing_category_does_not_block_point(self):
        packet = cm.demo("missing-category")
        packet["reference"]["weights"] = {"routine": "1", "complex": "0"}
        b = cm.analyze(packet)["groups"][1]
        self.assertEqual(b["reference_coverage"], "1")
        self.assertEqual(b["standardized"]["point"], "19/20")
        self.assertEqual(b["strata"][0]["state"], "ABSENT_STRATUM")

    def test_no_records_are_unknown_not_zero_rate(self):
        self.packet["groups"][0]["rows"] = []
        result = cm.analyze(self.packet)
        a = result["groups"][0]
        self.assertEqual(a["standardized"], {"low": "0", "high": "1", "point": None})
        self.assertEqual(a["reference_coverage"], "0")
        self.assertIsNone(result["comparisons"][0]["raw"])

    def test_explicit_zero_denominator_is_visible(self):
        row = self.packet["groups"][0]["rows"][0]
        row.update(events=0, non_events=0, unknown=0)
        a = cm.analyze(self.packet)["groups"][0]
        routine = next(r for r in a["strata"] if r["stratum"] == "routine")
        self.assertEqual(routine["state"], "NO_ELIGIBLE_RECORDS")
        self.assertIsNone(a["standardized"]["point"])

    def test_definition_mismatch_suppresses_pairwise_comparison(self):
        pair = cm.analyze(cm.demo("incompatible-definition"))["comparisons"][0]
        self.assertEqual(pair["eligibility"], "NOT_COMPARABLE")
        self.assertIn("DEFINITION_MISMATCH:event_definition", pair["reasons"])
        self.assertIsNone(pair["raw"])
        self.assertIsNone(pair["standardized"])

    def test_every_measurement_axis_participates_in_comparability(self):
        changes = {"event_definition": "different", "eligible_definition": "different", "strata_definition": "different",
                   "unit": "ticket", "window_start": "2026-01-02", "window_end": "2026-04-02",
                   "direction": "lower_is_better", "measure_class": "unknown"}
        for field, value in changes.items():
            with self.subTest(field=field):
                packet = copy.deepcopy(self.packet)
                packet["groups"][1]["metric"][field] = value
                pair = cm.analyze(packet)["comparisons"][0]
                self.assertIn("DEFINITION_MISMATCH:" + field, pair["reasons"])
                self.assertIsNone(pair["standardized"])

    def test_matching_targets_are_not_observed_outcomes(self):
        for g in self.packet["groups"]:
            g["metric"]["measure_class"] = "target"
        self.assertEqual(cm.analyze(self.packet)["comparisons"][0]["reasons"], ["NON_OUTCOME_MEASURE"])

    def test_lower_is_better_does_not_relabel_higher_rate_as_better(self):
        for g in self.packet["groups"]:
            g["metric"]["direction"] = "lower_is_better"
        pair = cm.analyze(self.packet)["comparisons"][0]
        self.assertEqual(pair["raw"]["order"], "A_HIGHER")
        self.assertNotIn("winner", pair)

    def test_equal_and_overlapping_ranges_are_separate(self):
        self.packet["groups"][1]["rows"] = copy.deepcopy(self.packet["groups"][0]["rows"])
        pair = cm.analyze(self.packet)["comparisons"][0]
        self.assertEqual(pair["standardized"]["order"], "EQUAL")
        for g in self.packet["groups"]:
            for row in g["rows"]:
                row.update(events=0, non_events=0, unknown=10)
        pair = cm.analyze(self.packet)["comparisons"][0]
        self.assertEqual(pair["standardized"]["order"], "UNRESOLVED")
        self.assertEqual(pair["standardized"]["difference"], {"low": "-1", "high": "1", "point": None})

    def test_all_small_unknown_completions_lie_in_reported_bounds(self):
        self.packet["reference"]["weights"] = {"routine": "1/3", "complex": "2/3"}
        for g in self.packet["groups"]:
            g["rows"][0].update(events=2, non_events=1, unknown=3)
            g["rows"][1].update(events=1, non_events=2, unknown=2)
        report = cm.analyze(self.packet)["groups"][0]
        bounds = report["standardized"]
        values = [Fraction(1, 3) * Fraction(2 + i, 6) + Fraction(2, 3) * Fraction(1 + j, 5)
                  for i in range(4) for j in range(3)]
        self.assertEqual(Fraction(bounds["low"]), min(values))
        self.assertEqual(Fraction(bounds["high"]), max(values))
        self.assertTrue(all(Fraction(bounds["low"]) <= v <= Fraction(bounds["high"]) for v in values))

    def test_common_mix_sensitivity_is_explicit(self):
        expected = {"0": ("1/10", "1/2"), "1/2": ("1/2", "29/40"), "1": ("9/10", "19/20")}
        for routine, rates in expected.items():
            with self.subTest(weight=routine):
                self.packet["reference"]["weights"] = {"routine": routine, "complex": str(1 - Fraction(routine))}
                groups = cm.analyze(self.packet)["groups"]
                self.assertEqual(tuple(g["standardized"]["point"] for g in groups), rates)

    def test_original_input_and_source_locators_survive_without_mutation(self):
        before = copy.deepcopy(self.packet)
        result = cm.analyze(self.packet)
        self.assertEqual(self.packet, before)
        self.assertEqual(result["input"], before)
        result["input"]["groups"][0]["rows"][0]["sources"].append("changed-after-analysis")
        self.assertEqual(self.packet, before)

    def test_deterministic_output_and_ordered_comparisons(self):
        one = cm.analyze(self.packet)
        self.assertEqual(cm.canonical(one), cm.canonical(cm.analyze(self.packet)))
        self.packet["groups"].reverse()
        for g in self.packet["groups"]:
            g["rows"].reverse()
        two = cm.analyze(self.packet)
        self.assertEqual(one["groups"], two["groups"])
        self.assertEqual(one["comparisons"], two["comparisons"])
        self.assertNotEqual(one["input_sha256"], two["input_sha256"])

    def test_more_than_two_groups_have_all_distinct_pairs(self):
        third = copy.deepcopy(self.packet["groups"][0])
        third["id"] = "C"
        self.packet["groups"].append(third)
        result = cm.analyze(self.packet)
        self.assertEqual([(p["a"], p["b"]) for p in result["comparisons"]], [("A", "B"), ("A", "C"), ("B", "C")])

    def test_bad_counts_are_rejected(self):
        for bad in (True, False, -1, 1.0, "1", None, 10**9 + 1):
            with self.subTest(value=bad):
                packet = copy.deepcopy(self.packet)
                packet["groups"][0]["rows"][0]["events"] = bad
                with self.assertRaises(cm.InputError):
                    cm.analyze(packet)

    def test_duplicate_groups_rows_and_unknown_categories_are_rejected(self):
        for kind in ("group", "row", "category"):
            packet = copy.deepcopy(self.packet)
            if kind == "group":
                packet["groups"][1]["id"] = "A"
            elif kind == "row":
                packet["groups"][0]["rows"].append(copy.deepcopy(packet["groups"][0]["rows"][0]))
            else:
                packet["groups"][0]["rows"][0]["stratum"] = "unmapped"
            with self.subTest(kind=kind), self.assertRaises(cm.InputError):
                cm.analyze(packet)

    def test_weights_are_exact_explicit_and_not_renormalized(self):
        for weights in ({"routine": "0.5", "complex": "0.499999999"},
                        {"routine": "1/0", "complex": "1"},
                        {"routine": "-1", "complex": "2"},
                        {"routine": 0.5, "complex": 0.5},
                        {"routine": "NaN", "complex": "1"}):
            with self.subTest(weights=weights):
                packet = copy.deepcopy(self.packet)
                packet["reference"]["weights"] = weights
                with self.assertRaises(cm.InputError):
                    cm.analyze(packet)
        self.packet["reference"]["weights"] = {"routine": "0.5", "complex": "0.5"}
        self.assertEqual(cm.analyze(self.packet)["groups"][0]["standardized"]["point"], "1/2")

    def test_absent_unknown_field_is_not_coerced_to_zero(self):
        del self.packet["groups"][0]["rows"][0]["unknown"]
        with self.assertRaises(cm.InputError):
            cm.analyze(self.packet)

    def test_invalid_windows_and_noncanonical_dates_are_rejected(self):
        for start, end in (("2026-04-01", "2026-01-01"), ("2026-01-01", "2026-01-01"),
                           ("2026-02-30", "2026-04-01"), ("20260101", "2026-04-01")):
            with self.subTest(start=start, end=end):
                packet = copy.deepcopy(self.packet)
                packet["groups"][0]["metric"].update(window_start=start, window_end=end)
                with self.assertRaises(cm.InputError):
                    cm.analyze(packet)

    def test_source_locator_and_population_context_are_required(self):
        for field in ("sources", "population_note", "synthetic"):
            packet = copy.deepcopy(self.packet)
            if field == "sources":
                packet["groups"][0]["rows"][0][field] = []
            elif field == "synthetic":
                packet[field] = "false"
            else:
                packet[field] = ""
            with self.subTest(field=field), self.assertRaises(cm.InputError):
                cm.analyze(packet)

    def test_strict_json_and_size_errors(self):
        for text in ('{"a":1,"a":2}', '{"value":NaN}', '{"value":Infinity}', '{', b'\xff', ' ' * (cm.LIMIT + 1)):
            with self.subTest(text=str(text)[:30]), self.assertRaises(cm.InputError):
                cm.loads(text)

    def test_markdown_escapes_labels_sources_and_preserves_unknowns(self):
        self.packet["groups"][0]["label"] = '<script>bad</script>|line\nnext'
        self.packet["groups"][0]["rows"][0]["sources"] = ['<img src=x onerror=bad>|source']
        output = cm.markdown(cm.analyze(self.packet))
        self.assertNotIn('<script>', output)
        self.assertNotIn('<img', output)
        self.assertIn('\\|line<br>next', output)
        self.assertIn('not confidence intervals', output)
        self.assertIn('SYNTHETIC REHEARSAL', output)
        output = cm.markdown(cm.analyze(cm.demo('missing-category')))
        self.assertIn('ABSENT_STRATUM', output)
        self.assertIn('UNRESOLVED', output)

    def test_false_synthetic_marker_is_not_certified_as_real_evidence(self):
        self.packet['synthetic'] = False
        output = cm.markdown(cm.analyze(self.packet))
        self.assertIn('provenance not independently verified', output)
        self.assertNotIn('SYNTHETIC REHEARSAL', output)

    def test_peer_csv_preserves_every_field_and_does_not_invent_counts(self):
        headers = ['peer', 'metric_or_measure', 'period_or_window', 'denominator_or_scope', 'measure_class', 'comparison_status', 'source_url', 'extension']
        source = dict(zip(headers, ['Fictional IT', '89.9%', 'historical', 'raw count unknown', 'observed historical outcome', 'historical_not_current_benchmark', 'synthetic:table', 'line one\nline two']))
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerow(source)
        report = cm.audit_peer_csv(stream.getvalue())
        self.assertEqual(report['record_count'], 1)
        self.assertEqual(report['records'][0]['source'], source)
        self.assertEqual(report['records'][0]['numeric_conversion'], 'NOT_ATTEMPTED')

    def test_peer_csv_malformed_headers_and_rows_fail(self):
        for text in ('a,a\n1,2\n', 'a,b\n1,2\n'):
            with self.assertRaises(cm.InputError):
                cm.audit_peer_csv(text)


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(Path(cm.__file__).resolve()), *args], text=True, capture_output=True, timeout=15)

    def test_all_four_actual_demo_commands(self):
        for case in ('reversal', 'missing-outcomes', 'missing-category', 'incompatible-definition'):
            with self.subTest(case=case):
                run = self.run_cli('demo', '--case', case, '--format', 'json')
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertTrue(json.loads(run.stdout)['synthetic'])

    def test_export_input_and_compare_roundtrip_is_byte_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'editable.json'
            exported = self.run_cli('demo', '--format', 'input')
            self.assertEqual(exported.returncode, 0, exported.stderr)
            path.write_text(exported.stdout, encoding='utf-8')
            before = path.read_bytes()
            run = self.run_cli('compare', str(path), '--format', 'json')
            demo = self.run_cli('demo', '--format', 'json')
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout, demo.stdout)
            self.assertEqual(path.read_bytes(), before)

    def test_malformed_json_has_stderr_and_no_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.json'
            path.write_text('{"a":1,"a":2}', encoding='utf-8')
            run = self.run_cli('compare', str(path))
            self.assertEqual(run.returncode, 2)
            self.assertEqual(run.stdout, '')
            self.assertIn('duplicate JSON key', run.stderr)

    def test_missing_file_has_nonzero_status_and_no_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.run_cli('compare', str(Path(tmp) / 'missing.json'))
            self.assertEqual(run.returncode, 2)
            self.assertEqual(run.stdout, '')


if __name__ == '__main__':
    unittest.main()
