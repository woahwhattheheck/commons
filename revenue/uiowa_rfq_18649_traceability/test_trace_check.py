#!/usr/bin/env python3
"""Behaviour tests for the traceability checker.

Every hostile case here is a way a real engagement loses provenance: a source
file that moved, a section that got renamed, a finding edited after the report
shipped, a number invented where the record says UNKNOWN. Each test asserts the
specific rule fires -- not merely that "something failed" -- because a checker
that fails for the wrong reason teaches an operator to ignore it.
"""
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout

import trace_check
import schema as S

HERE = os.path.dirname(os.path.abspath(__file__))
GOOD = os.path.join(HERE, "bundle")
DRIFTED = os.path.join(HERE, "bundle_drifted")


def rules(rep, level=None):
    return sorted({i["rule"] for i in rep.items if level is None or i["level"] == level})


class BundleCase(unittest.TestCase):
    """Each test gets a private copy so a hostile edit cannot leak sideways."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="uiowa093-")
        self.b = os.path.join(self.tmp, "bundle")
        shutil.copytree(GOOD, self.b)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path(self, name):
        return os.path.join(self.b, name)

    def edit(self, name, old, new, required=True):
        p = self.path(name)
        with open(p, encoding="utf-8") as fh:
            t = fh.read()
        if required:
            self.assertIn(old, t, "fixture anchor %r vanished from %s" % (old[:40], name))
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(t.replace(old, new))

    def check(self):
        return trace_check.check(self.b)[0]


class TestGoodBundle(BundleCase):
    def test_clean_bundle_passes(self):
        rep = self.check()
        self.assertEqual(rep.errors, [], "clean bundle reported: %s" % rep.sorted_items())
        self.assertEqual(rep.warnings, [])

    def test_trace_map_reaches_source_records(self):
        rep, data, findings, evidence, sources, _ = trace_check.check(self.b)
        rows = trace_check.trace_map(data, findings, evidence, sources)
        self.assertEqual(len(rows), 15)
        for r in rows:
            self.assertTrue(r["source_path"], "row %s has no source file" % r["statement_id"])
            self.assertTrue(os.path.isfile(os.path.join(self.b, r["source_path"])))
            self.assertEqual(len(r["source_sha256"]), 16)

    def test_every_statement_reaches_a_finding_and_a_source(self):
        _rep, data, findings, evidence, sources, _ = trace_check.check(self.b)
        for st in data["trace-map.csv"]:
            fids = S.split_ids(st["finding_ids"])
            self.assertTrue(fids, "%s cites no finding" % st["statement_id"])
            for fid in fids:
                for eid in S.split_ids(findings[fid]["evidence_ids"]):
                    self.assertIn(evidence[eid]["source_id"], sources)

    def test_json_output_is_valid_and_deterministic(self):
        outs = []
        for _ in range(2):
            buf = io.StringIO()
            with redirect_stdout(buf):
                trace_check.main([self.b, "--format", "json"])
            outs.append(buf.getvalue())
        self.assertEqual(outs[0], outs[1], "output is not reproducible")
        doc = json.loads(outs[0])
        self.assertEqual(doc["result"], "PASS")
        self.assertEqual(doc["counts"]["trace_rows"], 15)

    def test_exit_code_zero_on_pass(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(trace_check.main([self.b]), 0)


class TestDriftFixture(unittest.TestCase):
    """The order's real risk: the report drifts away from its evidence."""

    def test_drift_is_confined_to_the_record(self):
        # If the report had also been edited this would be a rewrite, not
        # drift, and the fixture would prove nothing.
        for name in ("executive-summary.md", "final-report.md", "trace-map.csv",
                     "evidence.csv", "recommendations.csv", "sources.csv"):
            with open(os.path.join(GOOD, name), "rb") as fh:
                a = fh.read()
            with open(os.path.join(DRIFTED, name), "rb") as fh:
                b = fh.read()
            self.assertEqual(a, b, "%s differs; the drift must touch findings.csv only" % name)
        with open(os.path.join(GOOD, "findings.csv"), "rb") as fh:
            good = fh.read()
        with open(os.path.join(DRIFTED, "findings.csv"), "rb") as fh:
            drifted = fh.read()
        self.assertNotEqual(good, drifted)

    def test_drifted_bundle_fails_on_three_independent_rules(self):
        rep = trace_check.check(DRIFTED)[0]
        self.assertEqual(rules(rep, "error"), ["T301", "T306", "T307"])
        self.assertEqual(len(rep.errors), 5)

    def test_drift_names_the_finding_that_moved(self):
        rep = trace_check.check(DRIFTED)[0]
        t306 = [i for i in rep.items if i["rule"] == "T306"]
        self.assertTrue(t306)
        for item in t306:
            self.assertIn("finding F-002 changed", item["detail"])

    def test_link_integrity_alone_would_not_catch_it(self):
        # Every id in the drifted bundle still resolves. That is exactly why a
        # link checker passes it and why the agreement layer has to exist.
        rep = trace_check.check(DRIFTED)[0]
        for code in ("T101", "T102", "T103", "T104", "T105", "T106"):
            self.assertNotIn(code, rules(rep))


class TestOrphans(BundleCase):
    def test_unregistered_paragraph_in_the_summary_is_an_error(self):
        with open(self.path("executive-summary.md"), "a", encoding="utf-8") as f:
            f.write("\n\nAll three groups demonstrate adequate release discipline "
                    "and no further remediation is required this cycle.\n")
        rep = self.check()
        self.assertIn("T202", rules(rep, "error"))

    def test_narrative_marker_does_not_buy_silence(self):
        with open(self.path("final-report.md"), "a", encoding="utf-8") as f:
            f.write("\n\n{narrative} All seven consumers are adequate and no further "
                    "work is required.\n")
        rep = self.check()
        self.assertIn("T201", rules(rep, "warning"))

    def test_statement_id_in_prose_but_not_in_the_map(self):
        with open(self.path("final-report.md"), "a", encoding="utf-8") as f:
            f.write("\n\n**S-099.** An unregistered conclusion. [F:F-001] [E:E-001]\n")
        rep = self.check()
        self.assertIn("T202", rules(rep, "error"))
        self.assertTrue(any("S-099" in i["detail"] for i in rep.items))

    def test_finding_that_reaches_no_statement_is_a_warning(self):
        with open(self.path("findings.csv"), "a", encoding="utf-8") as f:
            f.write('F-009,ESS,gap,Orphan finding,"Nothing in the report rests on this",'
                    'E-001,low,"none"\n')
        rep = self.check()
        self.assertIn("T203", rules(rep, "warning"))

    def test_source_cited_by_no_evidence_is_a_warning(self):
        extra = self.path("sources/SRC-009-unused.txt")
        with open(extra, "w", encoding="utf-8") as fh:
            fh.write("SOURCE-ID: SRC-009\nSYNTHETIC: yes\n---\n"
                     "[anchor: unused]\nnothing cites this\n")
        with open(self.path("sources.csv"), "a", encoding="utf-8") as f:
            f.write("SRC-009,Unused fictional record,sources/SRC-009-unused.txt,,2026-08-01,yes\n")
        rep = self.check()
        self.assertIn("T205", rules(rep, "warning"))


class TestCitationToSource(BundleCase):
    def test_missing_source_file(self):
        os.remove(self.path("sources/SRC-005-ris-test-inventory.txt"))
        rep = self.check()
        self.assertIn("T106", rules(rep, "error"))

    def test_source_edited_after_sealing(self):
        p = self.path("sources/SRC-008-iam-dependent-application-inventory.txt")
        with open(p, "a", encoding="utf-8") as fh:
            fh.write("\nAppended after the citation was sealed.\n")
        rep = self.check()
        self.assertIn("T107", rules(rep, "error"))

    def test_renamed_anchor_breaks_the_citation(self):
        self.edit("sources/SRC-005-ris-test-inventory.txt",
                  "[anchor: row reporting-contract-04]", "[anchor: row reporting-contract-99]")
        rep = self.check()
        # The bytes changed too, so the seal breaks as well -- both are true.
        self.assertIn("T108", rules(rep, "error"))

    def test_evidence_quantity_must_match_the_source_bytes(self):
        self.edit("evidence.csv", "end_to_end_propagation_scenarios=0 count",
                  "end_to_end_propagation_scenarios=4 count")
        rep = self.check()
        self.assertIn("T109", rules(rep, "error"))

    def test_evidence_citing_an_unregistered_source(self):
        self.edit("evidence.csv", "E-004,RIS,design_record,SRC-004",
                  "E-004,RIS,design_record,SRC-404")
        rep = self.check()
        self.assertIn("T105", rules(rep, "error"))

    def test_source_path_escaping_the_bundle_is_refused(self):
        self.edit("sources.csv", "sources/SRC-001-ess-change-request-2287.txt",
                  "../../../../etc/passwd")
        rep = self.check()
        self.assertIn("T005", rules(rep, "error"))


class TestAgreement(BundleCase):
    def test_unknown_must_not_become_a_number(self):
        self.edit("trace-map.csv",
                  "E-008.propagation_outcome_for_remaining_consumers=UNKNOWN",
                  "E-008.propagation_outcome_for_remaining_consumers=6")
        rep = self.check()
        self.assertIn("T304", rules(rep, "error"))
        self.assertTrue(any("must not become a number" in i["detail"] for i in rep.items))

    def test_statement_quantity_must_match_the_evidence(self):
        self.edit("trace-map.csv", "E-008.dependent_applications=7",
                  "E-008.dependent_applications=9")
        rep = self.check()
        self.assertIn("T302", rules(rep, "error"))

    def test_report_wording_changed_after_registration(self):
        self.edit("executive-summary.md",
                  "covering 1 acceptance criterion.", "covering all acceptance criteria.")
        rep = self.check()
        self.assertIn("T305", rules(rep, "error"))

    def test_summary_and_body_may_not_word_a_statement_differently(self):
        # Only the body copy is changed, so the exec summary and the report
        # body now say different things under one statement id.
        self.edit("final-report.md",
                  "propagation evidence for one of them. [F:F-003] [R:R-002] "
                  "[E:E-007,E-008]\n[LIMIT:F-003]",
                  "propagation evidence for most of them. [F:F-003] [R:R-002] "
                  "[E:E-007,E-008]\n[LIMIT:F-003]")
        rep = self.check()
        self.assertIn("T112", rules(rep, "error"))

    def test_dropping_a_limitation_is_caught(self):
        self.edit("trace-map.csv",
                  "E-008.dependent_applications=7,yes", "E-008.dependent_applications=7,no")
        rep = self.check()
        self.assertIn("T303", rules(rep, "error"))

    def test_prose_tags_must_match_the_map(self):
        self.edit("executive-summary.md", "[E:E-001,E-002,E-003]", "[E:E-001,E-002]")
        rep = self.check()
        self.assertIn("T110", rules(rep, "error"))

    def test_dangling_finding_reference_in_the_map(self):
        self.edit("trace-map.csv", ",F-001,E-001;E-002;E-003", ",F-404,E-001;E-002;E-003")
        rep = self.check()
        self.assertIn("T101", rules(rep, "error"))

    def test_registering_is_deliberate_and_running_the_check_never_heals_drift(self):
        self.edit("findings.csv", "F-002,RIS,gap,", "F-002,RIS,strength,")
        first = rules(self.check(), "error")
        self.assertIn("T306", first)
        for _ in range(3):
            with redirect_stdout(io.StringIO()):
                trace_check.main([self.b])
        self.assertIn("T306", rules(self.check(), "error"),
                      "running the checker silently re-registered the drift")


class TestStructural(BundleCase):
    def test_missing_required_column(self):
        self.edit("findings.csv", "finding_id,service,type,title,statement,"
                  "evidence_ids,confidence,limitation",
                  "finding_id,service,type,title,statement,evidence_ids,confidence")
        rep = self.check()
        self.assertIn("T002", rules(rep, "error"))

    def test_duplicate_id(self):
        with open(self.path("findings.csv"), "a", encoding="utf-8") as f:
            f.write('F-001,ESS,gap,Duplicate,"A second row claiming the same id",'
                    'E-001,low,"none"\n')
        rep = self.check()
        self.assertIn("T003", rules(rep, "error"))

    def test_missing_file_is_reported_not_raised(self):
        os.remove(self.path("recommendations.csv"))
        rep = self.check()
        self.assertIn("T001", rules(rep, "error"))

    def test_empty_directory_reports_every_missing_file_without_crashing(self):
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty)
        rep = trace_check.check(empty)[0]
        self.assertIn("T001", rules(rep, "error"))
        self.assertGreaterEqual(len([i for i in rep.items if i["rule"] == "T001"]), 5)

    def test_every_emitted_rule_has_catalogue_text(self):
        # A rule id with no description is an error message nobody can action.
        for bundle in (GOOD, DRIFTED):
            for item in trace_check.check(bundle)[0].items:
                self.assertIn(item["rule"], S.RULES)
                self.assertTrue(item["rule_text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestGeneratedArtifact(unittest.TestCase):
    """The committed trace map is generated; it must not drift from the bundle.

    A checked-in report that nobody regenerates becomes wrong the first time
    the bundle moves, which is the same failure this whole lane is about.
    """

    def test_committed_trace_map_matches_a_fresh_render(self):
        rep, data, findings, evidence, sources, _ = trace_check.check(GOOD)
        fresh = trace_check.render_markdown(
            rep, data, trace_check.trace_map(data, findings, evidence, sources))
        with open(os.path.join(HERE, "TRACE_MAP.md"), encoding="utf-8") as fh:
            committed = fh.read()
        self.assertEqual(fresh.strip(), committed.strip(),
                         "TRACE_MAP.md is stale: re-run "
                         "`python3 trace_check.py bundle --format markdown > TRACE_MAP.md`")
