#!/usr/bin/env python3
"""Regression tests for the cross-lane CSV export-safety auditor.

Run:  python3 -m unittest -v   (from this directory)

Half of these exist because the auditor's first run against the real delivery
kit produced 195 false positives out of 199 findings. An auditor that cries wolf
against other people's work is worse than no auditor, so every false-positive
class it ever produced is pinned by a named test.
"""

import json
import os
import shutil
import tempfile
import unittest

import export_safety as es

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")


def scan_one(name):
    path = os.path.join(FIXTURES, name)
    findings, _ = es.scan_csv(path, "fixtures", name)
    return findings


def codes(findings):
    return sorted(f["code"] for f in findings)


class FalsePositivesThisAuditorOnceProduced(unittest.TestCase):
    def test_a_leading_comment_line_is_one_finding_not_one_per_row(self):
        """The 185-false-positive bug. Several lanes put a provenance notice on
        line 1 as a `#` comment. Treating it as the header made every data row
        look ragged. The notice is real and worth reporting once, as a
        portability issue -- not 185 times as a data defect."""
        findings = scan_one("comment_header.csv")
        self.assertEqual(codes(findings), ["LEADING_COMMENT_LINE"])
        self.assertNotIn("RAGGED_ROW", codes(findings))

    def test_negative_numbers_and_placeholder_dashes_are_not_injection(self):
        """Ten of the first eleven injection findings were a lone '-' used as a
        not-applicable placeholder. Excel renders that as text."""
        for safe in ("-5", "+3.2", "-", "--", "-1e6", "-1,200", "", "ordinary"):
            self.assertFalse(es.looks_like_formula(safe), repr(safe))
        for risky in ("=SUM(A1)", "@cmd", "-A1*2", "+A1", "\tSUM", "\r=1"):
            self.assertTrue(es.looks_like_formula(risky), repr(risky))

    def test_injection_fixture_flags_exactly_the_three_real_ones(self):
        findings = scan_one("injection.csv")
        self.assertEqual(codes(findings), ["FORMULA_INJECTION"] * 3)
        flagged = {f["sample"] for f in findings}
        self.assertEqual(flagged, {"=SUM(A1:A9)", "@cmd|'/c calc'", "-A1*2"})

    def test_an_already_neutralized_cell_is_correct_not_a_finding(self):
        path = os.path.join(FIXTURES, "neutralized.csv")
        findings, stats = es.scan_csv(path, "fixtures", "neutralized.csv")
        self.assertEqual(findings, [])
        self.assertEqual(stats["neutralized"], 1)

    def test_a_declared_null_sentinel_downgrades_the_null_finding(self):
        """Empty vs 'NA' is genuinely ambiguous -- unless the file also uses an
        explicit sentinel, in which case it is a documentation question. Judging
        both the same way would flag a correct convention as a defect."""
        self.assertEqual(codes(scan_one("nulls_ambiguous.csv")),
                         ["NULL_SEMANTICS_AMBIGUOUS"])
        self.assertEqual(codes(scan_one("nulls_declared.csv")),
                         ["NULL_SEMANTICS_DECLARED"])
        ambiguous = scan_one("nulls_ambiguous.csv")[0]
        declared = scan_one("nulls_declared.csv")[0]
        self.assertEqual(ambiguous["severity"], es.MEDIUM)
        self.assertEqual(declared["severity"], es.INFO)


class Checks(unittest.TestCase):
    def test_duplicate_header_and_ragged_row(self):
        findings = scan_one("ragged_and_dupes.csv")
        self.assertEqual(codes(findings), ["DUPLICATE_HEADER", "RAGGED_ROW"])
        for item in findings:
            self.assertEqual(item["severity"], es.HIGH)

    def test_ambiguous_date_names_both_readings_and_iso_is_clean(self):
        findings = scan_one("dates.csv")
        self.assertEqual(codes(findings), ["AMBIGUOUS_DATE", "NON_ISO_DATE"])
        ambiguous = [f for f in findings if f["code"] == "AMBIGUOUS_DATE"][0]
        self.assertIn("2026-03-04", ambiguous["detail"])
        self.assertIn("2026-04-03", ambiguous["detail"])

    def test_unicode_checks(self):
        findings = scan_one("unicode.csv")
        self.assertEqual(codes(findings), ["OVERLONG_CELL", "UNNORMALIZED_UNICODE"])
        # A precomposed name and a CJK name are fine; only the decomposed one trips.
        decomposed = [f for f in findings if f["code"] == "UNNORMALIZED_UNICODE"][0]
        self.assertEqual(decomposed["row"], 1)

    def test_unreadable_file_is_UNKNOWN_never_a_pass(self):
        """Hostile case. The one thing an auditor must never do is count a file
        it could not read as clean."""
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "broken.csv")
            with open(bad, "wb") as fh:
                fh.write(b"id,name\n1,\xff\xfe\xfa not utf-8\n")
            findings, _ = es.scan_csv(bad, "tmp", "broken.csv")
        self.assertEqual(codes(findings), ["ENCODING_RISK"])
        self.assertNotEqual(findings, [])

    def test_bom_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bom.csv")
            with open(path, "wb") as fh:
                fh.write(b"\xef\xbb\xbfid,name\n1,alpha\n")
            findings, _ = es.scan_csv(path, "tmp", "bom.csv")
        self.assertIn("ENCODING_RISK", codes(findings))

    def test_empty_and_header_only_files_do_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, body in (("empty.csv", ""), ("header_only.csv", "a,b\n"),
                               ("comments_only.csv", "# just a notice\n")):
                path = os.path.join(tmp, name)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(body)
                findings, _ = es.scan_csv(path, "tmp", name)
                self.assertIsInstance(findings, list, name)


class AuditorDiscipline(unittest.TestCase):
    def test_the_auditor_passes_its_own_check(self):
        """Its findings quote offending cells, several of which begin with '='.
        Writing those bare would make the report itself an injection vector. An
        auditor that fails its own check has no standing."""
        with tempfile.TemporaryDirectory() as out:
            es.run(FIXTURES, out)
            findings, _ = es.scan_csv(os.path.join(out, "findings.csv"),
                                      "self", "findings.csv")
        self.assertNotIn("FORMULA_INJECTION", codes(findings))
        self.assertNotIn("RAGGED_ROW", codes(findings))

    def test_it_modifies_nothing_outside_its_own_output_directory(self):
        """It reports; it never edits another seat's lane. Proven by mtime, not
        promised in a README."""
        with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as out:
            copied = os.path.join(workspace, "lanes")
            shutil.copytree(FIXTURES, copied)
            before = {p: os.stat(os.path.join(copied, p)) for p in os.listdir(copied)}
            es.run(copied, out)
            for name, stat in before.items():
                after = os.stat(os.path.join(copied, name))
                self.assertEqual(stat.st_mtime_ns, after.st_mtime_ns, name)
                self.assertEqual(stat.st_size, after.st_size, name)

    def test_lane_filter_limits_the_scan(self):
        with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as out:
            shutil.copytree(FIXTURES, os.path.join(workspace, "lane_a"))
            shutil.copytree(FIXTURES, os.path.join(workspace, "lane_b"))
            _, files, _ = es.run(workspace, out, lane_filter="lane_a")
        self.assertTrue(files)
        self.assertEqual({f.split(os.sep)[0] for f in files}, {"lane_a"})

    def test_findings_json_records_what_was_scanned_not_just_what_failed(self):
        """A file list is how a reader tells 'clean' from 'never looked at'."""
        with tempfile.TemporaryDirectory() as out:
            es.run(FIXTURES, out)
            with open(os.path.join(out, "findings.json"), encoding="utf-8") as fh:
                payload = json.load(fh)
        self.assertEqual(len(payload["files_scanned"]), 8)
        self.assertGreater(payload["stats"]["cells"], 0)

    def test_report_states_that_clean_is_not_a_certification(self):
        with tempfile.TemporaryDirectory() as out:
            es.run(FIXTURES, out)
            with open(os.path.join(out, "export_safety_report.md"), encoding="utf-8") as fh:
                text = fh.read()
        self.assertIn("never \"certified\"", text)
        self.assertIn("UNREADABLE", text)
        self.assertIn("edits nothing", text)

    def test_fail_on_severity_gate(self):
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(es.main(["scan", "--root", FIXTURES, "--out", out,
                                      "--fail-on", es.HIGH]), 1)
        with tempfile.TemporaryDirectory() as out:
            clean = os.path.join(out, "clean")
            os.makedirs(clean)
            shutil.copy(os.path.join(FIXTURES, "neutralized.csv"), clean)
            self.assertEqual(es.main(["scan", "--root", clean, "--out",
                                      os.path.join(out, "o"), "--fail-on", es.LOW]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
