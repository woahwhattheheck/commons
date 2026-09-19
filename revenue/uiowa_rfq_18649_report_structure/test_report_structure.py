#!/usr/bin/env python3
"""Tests for the UIOWA-082 report structure, content map and scope guard.

Run:  python3 -m unittest -v test_report_structure.py

The tests that matter most are the hostile ones: a content map with an RFQ
element nobody covers, a section that cites nothing, a field name somebody
invented, and prose that has drifted into an audit verdict, an individual
performance evaluation, or a product purchase. A checker that only passes on
good input has not been tested.
"""

from __future__ import annotations

import copy
import csv
import json
import os
import tempfile
import unittest

import report_structure as rs
import scope_guard as sg

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def codes(issues):
    return {i.code for i in issues}


class ContentMapCoverageTests(unittest.TestCase):
    """The shipped map must be complete, and the checker must reject broken ones."""

    def setUp(self):
        self.cmap = rs.load_map()
        self.schemas = rs.load_schemas()

    def test_shipped_map_has_no_errors(self):
        issues = rs.check_coverage(self.cmap, self.schemas)
        self.assertEqual([], rs.errors(issues), "\n".join(str(i) for i in issues))

    def test_every_rfq_element_reaches_a_section(self):
        for e in self.cmap.elements:
            with self.subTest(element=e["element_id"]):
                self.assertTrue(self.cmap.sections_for(e["element_id"]),
                                f"{e['element_id']} is not covered by any section")

    def test_the_six_named_rfq_deliverables_are_all_covered(self):
        """The work order names six report areas by name. All six must map."""
        required = ["executive summary", "methodology", "peer", "cross-cutting",
                    "recommendation", "supporting evidence"]
        names = " ".join(e["name"].lower() for e in self.cmap.elements)
        for token in required:
            with self.subTest(deliverable=token):
                self.assertIn(token, names, f"no RFQ element covers '{token}'")

    def test_unmapped_element_is_an_error(self):
        broken = copy.deepcopy(self.cmap)
        broken.elements.append({"element_id": "RFQ-E99", "name": "Orphaned element",
                                "rfq_basis": "x", "must_not": "y"})
        issues = rs.check_coverage(broken, self.schemas)
        self.assertIn("UNMAPPED_ELEMENT", codes(issues))
        self.assertTrue(rs.errors(issues))

    def test_section_with_no_source_is_an_error(self):
        """A prose section citing nothing is how an unsupported assertion gets in."""
        broken = copy.deepcopy(self.cmap)
        broken.sections[0]["required_inputs"] = []
        issues = rs.check_coverage(broken, self.schemas)
        self.assertIn("SECTION_WITHOUT_SOURCE", codes(issues))
        self.assertTrue(rs.errors(issues))

    def test_unknown_dataset_is_an_error(self):
        broken = copy.deepcopy(self.cmap)
        broken.sections[0]["required_inputs"][0]["dataset"] = "some_register_nobody_built"
        issues = rs.check_coverage(broken, self.schemas)
        self.assertIn("UNKNOWN_DATASET", codes(issues))

    def test_invented_field_name_is_an_error(self):
        """The completion condition: the structure must accept the REAL field names."""
        broken = copy.deepcopy(self.cmap)
        broken.sections[0]["required_inputs"][0]["fields"] = ["maturity_score"]
        issues = rs.check_coverage(broken, self.schemas)
        self.assertIn("FIELD_NOT_IN_SCHEMA", codes(issues))
        self.assertTrue(any("maturity_score" in i.detail for i in issues))

    def test_orphan_section_and_dangling_element_ref_are_errors(self):
        broken = copy.deepcopy(self.cmap)
        broken.sections.append({"section_id": "SEC-99", "number": "99", "title": "Orphan",
                                "covers": [], "required_inputs": [], "purpose": "",
                                "traceability_rule": "r", "unknown_rule": "u", "prompts": ["p"]})
        broken.sections.append({"section_id": "SEC-98", "number": "98", "title": "Dangling",
                                "covers": ["RFQ-E77"], "purpose": "",
                                "required_inputs": [{"dataset": "finding_matrix",
                                                     "fields": ["finding_id"], "why": "w"}],
                                "traceability_rule": "r", "unknown_rule": "u", "prompts": ["p"]})
        issues = rs.check_coverage(broken, self.schemas)
        self.assertIn("ORPHAN_SECTION", codes(issues))
        self.assertIn("DANGLING_ELEMENT_REF", codes(issues))

    def test_missing_unknown_rule_is_an_error(self):
        """Every section must say what it does with missing evidence."""
        broken = copy.deepcopy(self.cmap)
        broken.sections[0].pop("unknown_rule")
        issues = rs.check_coverage(broken, self.schemas)
        self.assertIn("MISSING_UNKNOWN_RULE", codes(issues))

    def test_duplicate_section_id_is_an_error(self):
        broken = copy.deepcopy(self.cmap)
        broken.sections.append(copy.deepcopy(broken.sections[0]))
        issues = rs.check_coverage(broken, self.schemas)
        self.assertIn("DUPLICATE_SECTION_ID", codes(issues))

    def test_removing_an_exclusion_is_an_error(self):
        """The three out-of-scope deliverables must stay declared."""
        for guard in ("audit_verdict", "individual_evaluation", "product_procurement"):
            with self.subTest(guard=guard):
                broken = copy.deepcopy(self.cmap)
                broken.excluded = [x for x in broken.excluded if x["guard_class"] != guard]
                issues = rs.check_coverage(broken, self.schemas)
                self.assertIn("MISSING_EXCLUSION", codes(issues))

    def test_empty_map_fails_loudly_rather_than_passing_vacuously(self):
        """Hostile: an empty map must not read as 'nothing wrong'."""
        empty = rs.ContentMap(raw={}, elements=[], sections=[], excluded=[])
        issues = rs.check_coverage(empty, self.schemas)
        self.assertTrue(rs.errors(issues))
        self.assertIn("MISSING_EXCLUSION", codes(issues))


class WorkbenchSchemaTests(unittest.TestCase):
    """The pinned field names must still match what other seats landed."""

    def setUp(self):
        self.schemas = rs.load_schemas()

    def test_pinned_fields_match_the_real_registers(self):
        issues = rs.verify_workbench(self.schemas, REPO_ROOT)
        drift = [i for i in issues if i.code == "SCHEMA_DRIFT"]
        missing = [i for i in issues if i.code == "WORKBENCH_FILE_MISSING"]
        if missing:
            self.skipTest(f"not running inside the Commons checkout: {missing[0].detail}")
        self.assertEqual([], drift, "\n".join(str(i) for i in drift))

    def test_drift_is_detected_when_a_pinned_field_disappears(self):
        """Hostile: simulate the upstream register losing a column."""
        with tempfile.TemporaryDirectory() as td:
            rel = "revenue/fake/register.csv"
            path = os.path.join(td, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["evidence_id", "finding_id"])  # scope_limit gone
            schemas = {"fake": {"provenance": "workbench_pinned", "source_path": rel,
                                "fields": ["evidence_id", "finding_id", "scope_limit"]}}
            issues = rs.verify_workbench(schemas, td)
            self.assertIn("SCHEMA_DRIFT", codes(issues))
            self.assertTrue(rs.errors(issues))

    def test_missing_upstream_file_warns_and_does_not_silently_pass(self):
        schemas = {"fake": {"provenance": "workbench_pinned",
                            "source_path": "revenue/does/not/exist.csv",
                            "fields": ["a"]}}
        issues = rs.verify_workbench(schemas, "/nonexistent-root")
        self.assertIn("WORKBENCH_FILE_MISSING", codes(issues))

    def test_lane_local_datasets_are_not_asserted_against_the_workbench(self):
        schemas = {"local": {"provenance": "lane_local", "source_path": "nope.csv",
                             "fields": ["a"]}}
        self.assertEqual([], rs.verify_workbench(schemas, "/nonexistent-root"))

    def test_every_declared_dataset_has_fields(self):
        for name, spec in self.schemas.items():
            with self.subTest(dataset=name):
                self.assertTrue(spec.get("fields"), f"{name} declares no fields")


class FixtureConsistencyTests(unittest.TestCase):
    """The synthetic corpus must hold together, and it must be labeled fiction."""

    def setUp(self):
        self.schemas = rs.load_schemas()
        self.data = rs.load_all_fixtures(self.schemas)
        self.matrix = self.data["finding_matrix"]
        self.evidence = self.data["evidence_register"]
        self.recs = self.data["recommendation_register"]
        self.themes = self.data["theme_register"]

    def test_fixtures_use_only_declared_field_names(self):
        for ds in ("finding_matrix", "evidence_register", "recommendation_register",
                   "theme_register", "peer_context_table"):
            with self.subTest(dataset=ds):
                allowed = set(self.schemas[ds]["fields"])
                for row in self.data[ds]:
                    self.assertEqual(set(), set(row) - allowed,
                                     f"{ds} fixture carries a field not in the schema")

    def test_every_evidence_item_points_at_a_real_finding(self):
        known = {r["finding_id"] for r in self.matrix}
        for e in self.evidence:
            with self.subTest(evidence=e["evidence_id"]):
                self.assertIn(e["finding_id"], known)

    def test_every_recommendation_cites_a_real_finding(self):
        known = {r["finding_id"] for r in self.matrix}
        for r in self.recs:
            refs = [x for x in r["finding_refs"].split(";") if x]
            self.assertTrue(refs, f"{r['recommendation_id']} cites no finding")
            for ref in refs:
                with self.subTest(rec=r["recommendation_id"], ref=ref):
                    self.assertIn(ref, known)

    def test_every_theme_spans_at_least_two_findings(self):
        """A theme that rests on one finding is that finding, renamed."""
        known = {r["finding_id"] for r in self.matrix}
        for t in self.themes:
            refs = [x for x in t["finding_refs"].split(";") if x]
            with self.subTest(theme=t["theme_id"]):
                self.assertGreaterEqual(len(refs), 2)
                for ref in refs:
                    self.assertIn(ref, known)

    def test_controlled_values_are_respected(self):
        cv = self.schemas["finding_matrix"]["controlled_values"]
        for r in self.matrix:
            with self.subTest(finding=r["finding_id"]):
                self.assertIn(r["group"], cv["group"])
                self.assertIn(r["area"], cv["area"])
                self.assertIn(r["status"], cv["status"])
                self.assertIn(r["confidence"], cv["confidence"])

    def test_corpus_shows_both_a_strength_and_a_real_gap(self):
        statuses = {r["status"] for r in self.matrix}
        self.assertIn("SUPPORTED", statuses, "no strength in the corpus")
        self.assertTrue({"PARTIAL", "CONFLICT", "UNKNOWN"} & statuses, "no gap in the corpus")
        self.assertTrue(any(r["confidence"] == "HIGH" for r in self.matrix))
        self.assertTrue(any(r["confidence"] == "UNRESOLVED" for r in self.matrix))

    def test_unassessed_cell_carries_no_evidence_and_is_not_a_zero(self):
        """The completion condition for missing data, asserted."""
        unknown = [r for r in self.matrix if r["status"] == "UNKNOWN"]
        self.assertTrue(unknown, "corpus must contain an unassessed cell")
        for r in unknown:
            with self.subTest(finding=r["finding_id"]):
                self.assertEqual("NOT_EVIDENCED", r["confidence"])
                self.assertEqual("", r["evidence_refs"])
                self.assertTrue(r["follow_up_question"],
                                "an unassessed cell must carry the question that would resolve it")
                supporting = [e for e in self.evidence if e["finding_id"] == r["finding_id"]]
                self.assertEqual([], supporting)

    def test_conflicting_finding_keeps_both_sides(self):
        conflicts = [r for r in self.matrix if r["status"] == "CONFLICT"]
        self.assertTrue(conflicts)
        for r in conflicts:
            supporting = [e for e in self.evidence if e["finding_id"] == r["finding_id"]]
            with self.subTest(finding=r["finding_id"]):
                self.assertGreaterEqual(len(supporting), 2,
                                        "a conflict must retain the evidence on both sides")
                self.assertTrue(any(e["evidence_state"] == "CONFLICTING" for e in supporting))

    def test_matrix_is_not_silently_padded_to_twelve(self):
        """A cell nobody reached is absent or UNKNOWN - never invented."""
        self.assertLess(len(self.matrix), 12,
                        "fixture should leave at least one cell entirely unreached")
        pairs = {(r["group"], r["area"]) for r in self.matrix}
        self.assertNotIn(("RIS", "AI"), pairs)

    def test_recommendation_with_no_estimate_stays_unknown(self):
        unknown_horizon = [r for r in self.recs if r["horizon"] == "UNKNOWN"]
        self.assertTrue(unknown_horizon, "corpus must exercise the unsequenced bucket")
        for r in unknown_horizon:
            with self.subTest(rec=r["recommendation_id"]):
                self.assertNotIn(r["horizon"], ("0-90", "90-180", "180+"))

    def test_peer_rows_never_claim_a_comparison(self):
        allowed = {"context_only", "not_comparable_without_normalization",
                   "historical_not_current_benchmark"}
        for p in self.data["peer_context_table"]:
            with self.subTest(peer=p["peer"]):
                self.assertIn(p["comparison_status"], allowed)
                self.assertTrue(p["comparability_notes"])


class RenderingTests(unittest.TestCase):
    def setUp(self):
        self.cmap = rs.load_map()
        self.schemas = rs.load_schemas()
        self.data = rs.load_all_fixtures(self.schemas)
        self.template = rs.render_template(self.cmap, self.schemas)
        self.sample = rs.render_sample(self.cmap, self.schemas, self.data)

    def test_template_contains_every_section(self):
        for s in self.cmap.sections:
            with self.subTest(section=s["section_id"]):
                self.assertIn(s["title"], self.template)

    def test_sample_contains_every_section(self):
        for s in self.cmap.sections:
            with self.subTest(section=s["section_id"]):
                self.assertIn(s["title"], self.sample)

    def test_sample_is_labeled_fiction(self):
        self.assertIn("SYNTHETIC", self.sample)
        self.assertIn("NOT A UNIVERSITY FINDING", self.sample)

    def test_unassessed_cell_renders_as_unassessed_not_as_zero(self):
        self.assertIn("UNKNOWN - not assessed", self.sample)
        self.assertNotIn("| 0 |", self.sample)

    def test_matrix_counts_only_assessed_cells(self):
        assessed = len([r for r in self.data["finding_matrix"] if r["status"] != "UNKNOWN"])
        self.assertIn(f"{assessed} of 12 cells", self.sample)

    def test_unsequenced_bucket_is_rendered(self):
        self.assertIn("Unsequenced - estimate missing", self.sample)

    def test_findings_without_evidence_are_named_in_the_appendix(self):
        self.assertIn("Findings with no registered evidence item", self.sample)
        self.assertIn("FND-SYN-IAM-AI-001", self.sample)

    def test_blank_value_becomes_unknown_never_empty(self):
        self.assertEqual("UNKNOWN", rs._blank(""))
        self.assertEqual("UNKNOWN", rs._blank(None))
        self.assertEqual("UNKNOWN", rs._blank("   "))
        self.assertEqual("0", rs._blank("0"), "a real zero must survive as a zero")

    def test_content_map_csv_has_a_row_for_every_element(self):
        rows = rs.content_map_rows(self.cmap)
        seen = {r[0] for r in rows}
        self.assertEqual(set(self.cmap.element_ids), seen)

    def test_renderers_survive_a_completely_empty_dataset(self):
        """Hostile: no data at all must render a report that says so, not crash."""
        empty = {ds: [] for ds in self.schemas}
        out = rs.render_sample(self.cmap, self.schemas, empty)
        self.assertIn("0 of 12 cells", out)
        self.assertIn("UNKNOWN - not assessed", out)

    def test_renderer_tolerates_rows_missing_fields(self):
        """Hostile: a half-populated matrix row must not take the renderer down."""
        broken = {ds: [] for ds in self.schemas}
        broken["finding_matrix"] = [{"finding_id": "FND-X", "group": "ESS", "area": "SD"}]
        out = rs.render_sample(self.cmap, self.schemas, broken)
        self.assertIn("FND-X", out)
        self.assertIn("UNKNOWN", out)


class ScopeGuardTests(unittest.TestCase):
    """The three drifts the work order forbids, each caught - without over-firing."""

    def _classes(self, text):
        return {h.guard_class for h in sg.flagged(sg.scan_text(text))}

    def test_catches_audit_compliance_verdict(self):
        text = ("Finding 3: the RIS group is non-compliant with the access-review standard. "
                "This is a material weakness and the control failed the audit.")
        hits = sg.flagged(sg.scan_text(text))
        self.assertTrue(hits)
        self.assertIn(sg.AUDIT_VERDICT, {h.guard_class for h in hits})
        self.assertTrue(all(h.suggested_rewrite for h in hits))

    def test_catches_individual_performance_evaluation(self):
        text = ("The ESS database administrator is underperforming and lacks the experience "
                "for this platform. Her performance rating should reflect that, and she "
                "should be reassigned.")
        self.assertIn(sg.INDIVIDUAL_EVALUATION, self._classes(text))

    def test_catches_named_person_evaluation(self):
        text = "Dana Whitfield is underperforming, and Dana Whitfield's productivity is the issue."
        hits = sg.flagged(sg.scan_text(text))
        self.assertIn(sg.INDIVIDUAL_EVALUATION, {h.guard_class for h in hits})
        self.assertTrue({"IE-05", "IE-06"} & {h.rule_id for h in hits})

    def test_catches_product_procurement(self):
        text = ("We recommend purchasing an enterprise secrets-management platform. "
                "The preferred vendor should be selected this quarter and the per-seat "
                "price is within budget.")
        self.assertIn(sg.PRODUCT_PROCUREMENT, self._classes(text))

    def test_all_three_drift_classes_are_caught_in_one_pass(self):
        text = ("The group is non-compliant with IT-18. "
                "The lead engineer lacks the skills to close this. "
                "We recommend purchasing a replacement platform.")
        self.assertEqual({sg.AUDIT_VERDICT, sg.INDIVIDUAL_EVALUATION, sg.PRODUCT_PROCUREMENT},
                         self._classes(text))

    def test_scope_boundary_language_is_not_flagged(self):
        """The report's own disclaimer must pass. A guard that flags it gets turned off."""
        text = ("This assessment is not a formal audit and issues no compliance determination, "
                "certification or attestation. It assesses organizational practice; no statement "
                "rates, ranks or evaluates a named individual. It describes capabilities the "
                "University may need; no vendor selection or product purchase is recommended.")
        self.assertEqual([], sg.flagged(sg.scan_text(text)))

    def test_legitimate_report_prose_is_not_flagged(self):
        """Ordinary findings language mentions these topics without performing them."""
        text = ("Policy IT-18 requires documented revision controls; no current review record "
                "was observed for two of the in-scope services, so the cell is PARTIAL with LOW "
                "confidence. A lead-time policy is a published process target, not observed "
                "deployment performance. The group depends on a vendor-hosted identity platform, "
                "and the licence renewal window was noted as a scheduling constraint.")
        hits = sg.flagged(sg.scan_text(text))
        self.assertEqual([], hits, "\n".join(f"{h.rule_id}: {h.matched}" for h in hits))

    def test_shipped_template_and_sample_are_clean(self):
        cmap = rs.load_map()
        schemas = rs.load_schemas()
        data = rs.load_all_fixtures(schemas)
        for name, text in (("template", rs.render_template(cmap, schemas)),
                           ("sample", rs.render_sample(cmap, schemas, data))):
            with self.subTest(doc=name):
                hits = sg.flagged(sg.scan_text(text, name))
                self.assertEqual([], hits,
                                 "\n".join(f"{h.rule_id} line {h.line}: {h.matched}" for h in hits))

    def test_neutralized_matches_are_reported_not_discarded(self):
        """A neutralized match is still visible to a reviewer."""
        text = "No vendor selection is recommended by this assessment."
        hits = sg.scan_text(text)
        self.assertTrue(hits, "the guard should still see the phrase")
        self.assertTrue(all(h.status == sg.NEUTRALIZED for h in hits))
        self.assertTrue(all(h.neutralized_by for h in hits))

    def test_personal_name_rules_are_case_sensitive(self):
        """Regression: IE-05 compiled IGNORECASE matched 'deployment performance'."""
        for rule in sg.RULES:
            if rule.rule_id in ("IE-05", "IE-06"):
                with self.subTest(rule=rule.rule_id):
                    self.assertEqual(0, rule.flags)
        self.assertEqual([], sg.flagged(sg.scan_text("observed deployment performance")))
        self.assertEqual([], sg.flagged(sg.scan_text("not attained performance")))

    def test_guard_handles_empty_and_whitespace_input(self):
        self.assertEqual([], sg.scan_text(""))
        self.assertEqual([], sg.scan_text("   \n\n  "))

    def test_every_rule_declares_a_class_a_reason_and_a_rewrite(self):
        for rule in sg.RULES:
            with self.subTest(rule=rule.rule_id):
                self.assertIn(rule.guard_class, sg.GUARD_CLASSES)
                self.assertTrue(rule.why)
                self.assertTrue(rule.suggested_rewrite)

    def test_all_three_guard_classes_have_rules(self):
        covered = {r.guard_class for r in sg.RULES}
        self.assertEqual(set(sg.GUARD_CLASSES), covered)

    def test_cli_exit_code_is_nonzero_on_drift(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "drifted.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write("The service is non-compliant and we recommend purchasing a new tool.")
            self.assertEqual(1, sg.main([p]))
            clean = os.path.join(td, "clean.md")
            with open(clean, "w", encoding="utf-8") as f:
                f.write("The cell is PARTIAL with LOW confidence; no review record was observed.")
            self.assertEqual(0, sg.main([clean]))


class JsonIntegrityTests(unittest.TestCase):
    def test_shipped_json_files_parse(self):
        for name in ("content_map.json", "input_schemas.json"):
            with self.subTest(file=name):
                with open(os.path.join(HERE, name), encoding="utf-8") as f:
                    self.assertIsInstance(json.load(f), dict)

    def test_map_declares_it_is_not_a_university_finding(self):
        cmap = rs.load_map()
        self.assertIn("NOT A UNIVERSITY FINDING", cmap.raw.get("status", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
