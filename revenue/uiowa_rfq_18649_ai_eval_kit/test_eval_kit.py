#!/usr/bin/env python3
"""Regression tests for the UIOWA-075 AI usefulness evaluation kit.

Run:  python3 -m unittest -v   (from this directory)

These assert the behaviours that are easy to get wrong and expensive to get
wrong quietly: a fabrication outranking an abstention, an unrun task being
counted as a zero, a measured figure being averaged with a modeled one, and a
value that does not survive the trip out to a reader's spreadsheet.
"""

import copy
import os
import shutil
import tempfile
import unittest

import eval_kit as ek
import interchange as ix

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, "data", "tasks.json")
ASSISTED = os.path.join(HERE, "data", "runs_assisted.json")
MANUAL = os.path.join(HERE, "data", "runs_manual.json")


def task_by_id(dataset, task_id):
    return next(t for t in dataset["tasks"] if t["task_id"] == task_id)


def result_by_id(workflow, task_id):
    return next(r for r in workflow["results"] if r["task_id"] == task_id)


class ScoringBehaviour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = ix.read_json(TASKS)
        cls.assisted = ek.score_workflow(cls.dataset, ix.read_json(ASSISTED))
        cls.manual = ek.score_workflow(cls.dataset, ix.read_json(MANUAL))

    def test_dataset_validates(self):
        self.assertEqual(ek.validate_dataset(self.dataset), [])

    def test_fabrication_scores_worse_than_abstention(self):
        """THE guardrail. A confident invented answer must lose to an honest 'not in
        the sources' on every measure -- otherwise the kit recommends the workflow
        that fabricates most fluently."""
        fabricated = result_by_id(self.assisted, "DOC-MIS-04")   # "retained for 90 days"
        abstained = result_by_id(self.manual, "DOC-MIS-04")      # "not stated in the supplied sources"

        self.assertLess(fabricated["completeness"], abstained["completeness"])
        self.assertLess(fabricated["correctness"], abstained["correctness"])
        self.assertGreater(fabricated["modeled_repair_minutes"],
                           abstained["modeled_repair_minutes"])
        # And the fabrication is net time-NEGATIVE: producing it cost time.
        self.assertLess(fabricated["net_minutes_saved"], 0)
        self.assertGreater(abstained["net_minutes_saved"], 0)
        self.assertIn("F-INVENT-RET", fabricated["forbidden_ids"])
        self.assertEqual(abstained["forbidden_ids"], [])

    def test_missing_information_abstention_failure_is_named(self):
        self.assertIn("DOC-MIS-04", self.assisted["summary"]["abstention_failures"])
        self.assertIn("TST-MIS-08", self.assisted["summary"]["abstention_failures"])
        self.assertEqual(self.manual["summary"]["abstention_failures"], [])

    def test_ambiguous_case_accepts_either_defensible_answer(self):
        """Two different correct answers both score correct, and the report records
        WHICH one matched -- the ambiguity is preserved, not silently resolved."""
        exclusive = result_by_id(self.assisted, "TST-AMB-06")   # day 91
        inclusive = result_by_id(self.manual, "TST-AMB-06")     # day 90
        self.assertEqual(exclusive["completeness"], 1.0)
        self.assertEqual(inclusive["completeness"], 1.0)
        self.assertEqual(exclusive["matched_variant"], "V2")
        self.assertEqual(inclusive["matched_variant"], "V1")
        self.assertEqual(exclusive["tied_variants"], [])
        self.assertEqual(inclusive["tied_variants"], [])
        self.assertNotEqual(exclusive["variant_label"], inclusive["variant_label"])

    def test_ambiguous_answer_without_naming_its_reading_is_incomplete(self):
        """Picking a reading is fine. Not saying which one you picked is not."""
        unnamed = result_by_id(self.manual, "DOC-AMB-02")
        named = result_by_id(self.assisted, "DOC-AMB-02")
        self.assertEqual(named["completeness"], 1.0)
        self.assertLess(unnamed["completeness"], 1.0)
        self.assertIn("E-STATES-ASSUMPTION", unnamed["missed_ids"])

    def test_fluent_stale_context_output_is_penalized(self):
        """DOC-STA-03's assisted output is well written and entirely wrong: it uses a
        retired endpoint from a 2025 source as if it were current."""
        stale = result_by_id(self.assisted, "DOC-STA-03")
        self.assertEqual(stale["correctness"], 0.0)
        self.assertEqual(stale["completeness"], 0.0)
        self.assertIn("F-RETIRED-EP", stale["forbidden_ids"])
        clean = result_by_id(self.manual, "DOC-STA-03")
        self.assertEqual(clean["completeness"], 1.0)

    def test_not_run_task_is_unknown_and_leaves_every_denominator(self):
        """Hostile/missing-data case. manual-draft-v1 never attempted REQ-STA-11."""
        missing = result_by_id(self.manual, "REQ-STA-11")
        self.assertEqual(missing["status"], "NOT_RUN")
        for field in ("completeness", "correctness", "modeled_repair_minutes",
                      "net_minutes_saved", "generation_minutes"):
            self.assertIsNone(missing[field], f"{field} should be UNKNOWN, not a number")
        summary = self.manual["summary"]
        self.assertEqual(summary["tasks_total"], 12)
        self.assertEqual(summary["tasks_scored"], 11)
        self.assertIn("REQ-STA-11", summary["tasks_not_run"])
        # The mean is over the 11 scored tasks only. A zero-filled 12th would drag
        # completeness down to 0.847; that would be a fabricated finding.
        scored = [r["completeness"] for r in self.manual["results"] if r["status"] == "SCORED"]
        self.assertEqual(summary["completeness_mean"], round(sum(scored) / 11, 4))
        self.assertNotEqual(summary["completeness_mean"], round(sum(scored) / 12, 4))

    def test_unknown_time_assumption_propagates_and_does_not_become_zero(self):
        """REQ-MIS-12 has from_scratch_minutes = null. Usefulness is UNKNOWN, and the
        task is excluded from the net-saved total rather than contributing 0."""
        for workflow in (self.assisted, self.manual):
            result = result_by_id(workflow, "REQ-MIS-12")
            self.assertEqual(result["status"], "SCORED")
            self.assertIsNone(result["net_minutes_saved"])
            self.assertEqual(result["time_basis"], ek.UNKNOWN)
            self.assertIn("REQ-MIS-12", workflow["summary"]["time_unknown_tasks"])
            self.assertNotIn("REQ-MIS-12", workflow["summary"]["timed_tasks"])
            # ...but it IS still scored for correctness/completeness. An unknown time
            # assumption does not erase a known quality result.
            self.assertIsNotNone(result["completeness"])

    def test_measured_and_modeled_repair_are_never_averaged(self):
        summary = self.assisted["summary"]
        unmeasured = result_by_id(self.assisted, "DOC-MIS-04")
        self.assertIsNone(unmeasured["measured_repair_minutes"])
        self.assertEqual(unmeasured["repair_basis"], "MODELED")
        self.assertIn("DOC-MIS-04", summary["repair_not_measured_tasks"])
        self.assertNotIn("DOC-MIS-04", summary["repair_measured_tasks"])
        # The measured subtotal is the sum of measurements only.
        measured_only = sum(r["measured_repair_minutes"] for r in self.assisted["results"]
                            if r["measured_repair_minutes"] is not None)
        self.assertEqual(summary["repair_measured_total"], measured_only)
        self.assertNotEqual(summary["repair_measured_total"],
                            summary["repair_modeled_total_all_scored"])

    def test_empty_output_is_scored_zero_not_unknown(self):
        """'Produced nothing' is evidence about the workflow. 'Never ran' is not.
        The two must not collapse into each other."""
        task = task_by_id(self.dataset, "DOC-ORD-01")
        blank = ek.score_task(task, {"task_id": "DOC-ORD-01", "output": "",
                                     "generation_minutes": 1, "recorded_repair_minutes": None})
        self.assertEqual(blank["status"], "SCORED")
        self.assertEqual(blank["completeness"], 0.0)
        self.assertEqual(blank["correctness"], 0.0)
        self.assertIsNotNone(blank["modeled_repair_minutes"])
        notrun = ek.score_task(task, None)
        self.assertEqual(notrun["status"], "NOT_RUN")
        self.assertIsNone(notrun["completeness"])

    def test_paired_comparison_excludes_unpaired_tasks(self):
        comparison = ek.compare(self.assisted, self.manual)
        self.assertEqual(len(comparison["paired_tasks"]), 11)
        self.assertEqual(comparison["unpaired_tasks_excluded"], ["REQ-STA-11"])
        self.assertNotIn("REQ-STA-11", comparison["paired_tasks"])

    def test_ambiguous_reading_is_attributed_to_the_right_variant(self):
        """Regression for a bug these tests caught: both REQ-AMB-10 outputs name both
        senses of 'priority' ("uses queue priority, NOT the business priority column").
        With plain substring keys each output matched both variants and the variant_id
        tie-break silently credited the manual run with the reading it explicitly did
        not use. The keys now discriminate on what the summary says it USES."""
        self.assertEqual(result_by_id(self.assisted, "REQ-AMB-10")["matched_variant"], "V1")
        self.assertEqual(result_by_id(self.manual, "REQ-AMB-10")["matched_variant"], "V2")
        self.assertEqual(result_by_id(self.assisted, "TST-AMB-06")["matched_variant"], "V2")
        self.assertEqual(result_by_id(self.manual, "TST-AMB-06")["matched_variant"], "V1")
        for workflow in (self.assisted, self.manual):
            self.assertEqual(workflow["summary"]["undiscriminated_ambiguous_tasks"], [])

    def test_indistinguishable_variants_are_reported_as_a_tie(self):
        """When an output genuinely does not pick a side, the kit says so instead of
        letting the variant_id sort order decide."""
        task = {
            "task_id": "SYN-TIE", "family": "documentation", "case_class": "ambiguous",
            "from_scratch_minutes": 10,
            "answer_variants": [
                {"variant_id": "V1", "label": "reading A",
                 "required": [{"element_id": "E", "any_of": ["escalation"], "repair_minutes": 5}]},
                {"variant_id": "V2", "label": "reading B",
                 "required": [{"element_id": "E", "any_of": ["escalation"], "repair_minutes": 5}]},
            ],
        }
        result = ek.score_task(task, {"task_id": "SYN-TIE", "output": "the escalation path",
                                      "generation_minutes": 1, "recorded_repair_minutes": 0})
        self.assertEqual(result["tied_variants"], ["V1", "V2"])

    def test_no_composite_usefulness_score_is_emitted(self):
        """Static tripwire, labelled as one: it guards intent, not behaviour. The kit
        reports four measures separately; a blended score would hide the speed/repair
        trade the reader has to make."""
        keys = set(self.assisted["summary"])
        blended = [k for k in keys
                   if k == "score" or k.endswith("_score") or "composite" in k
                   or "usefulness_index" in k or k.endswith("_rating")]
        self.assertFalse(blended, blended)
        # ...and all four measures really are present, separately.
        for key in ("completeness_mean", "correctness_mean", "repair_measured_total",
                    "repair_modeled_total_all_scored", "net_minutes_saved_timed"):
            self.assertIn(key, keys)


class DatasetValidation(unittest.TestCase):
    def setUp(self):
        self.dataset = ix.read_json(TASKS)

    def test_missing_information_task_must_require_abstention(self):
        broken = copy.deepcopy(self.dataset)
        task = task_by_id(broken, "DOC-MIS-04")
        task["answer_variants"][0]["required"] = [
            {"element_id": "E-OTHER", "description": "x", "any_of": ["nightly"], "repair_minutes": 2}
        ]
        problems = ek.validate_dataset(broken)
        self.assertTrue(any("abstention element" in p for p in problems), problems)

    def test_inverted_repair_cost_asymmetry_is_caught(self):
        """If catching a fabrication is priced cheaper than noticing an omission, every
        ranking downstream is wrong and nothing else would notice."""
        broken = copy.deepcopy(self.dataset)
        task = task_by_id(broken, "DOC-MIS-04")
        task["answer_variants"][0]["forbidden"][0]["repair_minutes"] = 1
        problems = ek.validate_dataset(broken)
        self.assertTrue(any("not greater than" in p for p in problems), problems)

    def test_element_with_only_negative_terms_is_caught(self):
        """none_of alone cannot establish that an output said the right thing."""
        broken = copy.deepcopy(self.dataset)
        task = task_by_id(broken, "REQ-AMB-10")
        task["answer_variants"][0]["required"][0] = {
            "element_id": "E-NEG", "description": "x", "none_of": ["queue priority"]}
        self.assertTrue(any("no match terms" in p for p in ek.validate_dataset(broken)))

    def test_element_with_no_match_terms_is_caught(self):
        broken = copy.deepcopy(self.dataset)
        task = task_by_id(broken, "DOC-ORD-01")
        task["answer_variants"][0]["required"][0] = {"element_id": "E-EMPTY", "description": "x"}
        self.assertTrue(any("no match terms" in p for p in ek.validate_dataset(broken)))


class Interchange(unittest.TestCase):
    """The results have to survive the trip out to a reader who does not have this
    environment. These are the values that break that trip in practice."""

    HOSTILE = [
        "=SUM(A1:A9)", "+1-2", "@cmd|'/c calc'", "-5",
        "ordinary text", "", "NA", "\\N", "'already quoted",
        "José Álvarez — em dash", "田中 さくら",
        'comma, and "quotes" inside', "line one\r\nline two", "x" * 400,
    ]

    def test_hostile_values_round_trip_exactly(self):
        columns = [("id", "int"), ("value", "text"), ("maybe", "text")]
        rows = [{"id": i, "value": v, "maybe": None} for i, v in enumerate(self.HOSTILE)]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "hostile.csv")
            ix.write_csv(path, columns, rows)
            back = ix.read_csv(path, columns)
        self.assertEqual([ix.record_hash(r) for r in rows],
                         [ix.record_hash(r) for r in back])

    def test_formula_injection_neutralized_flagged_and_reversible(self):
        columns = [("value", "text")]
        rows = [{"value": "=SUM(A1:A9)"}, {"value": "harmless"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "f.csv")
            warnings = ix.write_csv(path, columns, rows)
            with open(path, encoding="utf-8") as fh:
                raw = fh.read()
            back = ix.read_csv(path, columns)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["field"], "value")
        self.assertIn("'=SUM(A1:A9)", raw)
        # No cell begins a formula: neutralized, not merely warned about.
        for line in raw.splitlines()[1:]:
            self.assertFalse(line.startswith(("=", "+", "@")), line)
        # ...and the value is not mangled: it comes back exactly.
        self.assertEqual(back[0]["value"], "=SUM(A1:A9)")

    def test_null_empty_and_literal_na_stay_three_distinct_states(self):
        columns = [("v", "text")]
        rows = [{"v": None}, {"v": ""}, {"v": "NA"}, {"v": "\\N"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "n.csv")
            ix.write_csv(path, columns, rows)
            back = ix.read_csv(path, columns)
        self.assertIsNone(back[0]["v"])
        self.assertEqual(back[1]["v"], "")
        self.assertEqual(back[2]["v"], "NA")
        self.assertEqual(back[3]["v"], "\\N")
        self.assertEqual(len({repr(r["v"]) for r in back}), 4)

    def test_ambiguous_date_is_rejected_not_guessed(self):
        with self.assertRaises(ix.AmbiguousDateError) as ctx:
            ix.decode_cell("03/04/2026", "date")
        message = str(ctx.exception)
        self.assertIn("2026-03-04", message)
        self.assertIn("2026-04-03", message)
        self.assertEqual(ix.decode_cell("2026-03-04", "date"), "2026-03-04")
        with self.assertRaises(ix.InterchangeError):
            ix.decode_cell("March 4 2026", "date")

    def test_unicode_normalization_makes_the_same_name_the_same_name(self):
        composed = "José"
        decomposed = "José"
        self.assertNotEqual(composed, decomposed)
        self.assertEqual(ix.record_hash({"n": composed}), ix.record_hash({"n": decomposed}))

    def test_empty_numeric_cell_is_refused_rather_than_guessed(self):
        with self.assertRaises(ix.InterchangeError):
            ix.decode_cell("", "int")

    def test_markdown_table_cell_cannot_break_the_table(self):
        cell = ix.md_escape("a | b\nsecond line")
        self.assertNotIn("\n", cell)
        self.assertIn("\\|", cell)
        self.assertEqual(ix.md_escape(None), "_not recorded_")


class GeneratedArtifacts(unittest.TestCase):
    def test_full_build_is_byte_reproducible(self):
        """Two operators, two directories, identical bytes -- or a loud failure."""
        first = tempfile.mkdtemp(prefix="evalkit-a-")
        second = tempfile.mkdtemp(prefix="evalkit-b-")
        try:
            _, _, _, digests_a = ek.build(TASKS, [ASSISTED, MANUAL], first)
            _, _, _, digests_b = ek.build(TASKS, [ASSISTED, MANUAL], second)
            self.assertEqual(digests_a, digests_b)
            self.assertEqual(len(digests_a), 4)
        finally:
            shutil.rmtree(first, ignore_errors=True)
            shutil.rmtree(second, ignore_errors=True)

    def test_results_csv_round_trips_every_generated_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflows, _, warnings, _ = ek.build(TASKS, [ASSISTED, MANUAL], tmp)
            rows = ek._csv_rows(workflows)
            back = ix.read_csv(os.path.join(tmp, "results.csv"), ek.RESULT_COLUMNS)
        expected = [{k: v for k, v in r.items()} for r in rows]
        self.assertEqual([ix.record_hash(r) for r in expected],
                         [ix.record_hash(r) for r in back])
        self.assertEqual(len(back), 24)
        self.assertIsNone(rows[0]["tied_variants"])
        self.assertTrue(warnings, "the pasted-formula fixture should raise a warning")

    def test_generated_csv_preserves_the_long_locator_and_crlf_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            ek.build(TASKS, [ASSISTED, MANUAL], tmp)
            back = ix.read_csv(os.path.join(tmp, "results.csv"), ek.RESULT_COLUMNS)
        rows = {(r["workflow_id"], r["task_id"]): r for r in back}
        locator = rows[("assisted-draft-v1", "REQ-STA-11")]["review_locator"]
        self.assertGreaterEqual(len(locator), 400)
        note = rows[("assisted-draft-v1", "DOC-AMB-02")]["reviewer_note"]
        self.assertIn("\r\n", note)
        self.assertEqual(rows[("assisted-draft-v1", "TST-ORD-05")]["reviewer_note"],
                         "=SUM(B2:B13)")
        # Tri-state survives the real generated file, not just the unit fixture.
        self.assertEqual(rows[("assisted-draft-v1", "DOC-ORD-01")]["analyst_followup"], "NA")
        self.assertEqual(rows[("assisted-draft-v1", "DOC-AMB-02")]["analyst_followup"], "")
        self.assertIsNone(rows[("assisted-draft-v1", "DOC-STA-03")]["analyst_followup"])

    def test_report_names_unknowns_instead_of_hiding_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            ek.build(TASKS, [ASSISTED, MANUAL], tmp)
            with open(os.path.join(tmp, "report.md"), encoding="utf-8") as fh:
                report = fh.read()
        self.assertIn("REQ-STA-11", report)          # the NOT_RUN task is named
        self.assertIn("REQ-MIS-12", report)          # the UNKNOWN-time task is named
        self.assertIn("UNKNOWN", report)
        self.assertIn("FICTION", report)
        self.assertIn("does not rate any individual", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
