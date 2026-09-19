#!/usr/bin/env python3
"""OPS-PERF-SCAN tests.

Two jobs here, and the second matters more than the first:

  RECALL   the scanner finds the shapes UIOWA-095 actually measured.
  PRECISION the scanner does NOT flag correct code.

Precision is the one that gets the weight. This scanner reads other seats'
lanes; a false positive is a false accusation about somebody else's work, and a
detector that cries wolf gets ignored and then finds nothing. The first version
of this scanner produced 131 matches against the delivered kit, nearly all of
them ordinary `if key in some_dict` lookups. Every regression test below marked
PRECISION exists because of a specific false positive that version produced.

Run:  python3 -m unittest discover -v
"""
from __future__ import annotations

import ast
import shutil
import tempfile
import textwrap
import unittest
from pathlib import Path

import scan_hotspots as sh
import scan_kit


def patterns_in(source: str) -> list:
    """Scan a source string, return the pattern ids found."""
    findings = sh.scan_source(Path("<test>"), textwrap.dedent(source))
    return [f.pattern for f in findings]


def findings_in(source: str) -> list:
    return sh.scan_source(Path("<test>"), textwrap.dedent(source))


class TestRecall(unittest.TestCase):
    """The shapes UIOWA-095 measured must be found."""

    def test_finds_substring_scan_of_file_text_in_a_loop(self):
        """The exact shape from validate_trace.py, measured at 22.55x."""
        src = """
            def check(root, ids):
                report = (root / "a.md").read_text(encoding="utf-8")
                report += (root / "b.md").read_text(encoding="utf-8")
                missing = []
                for sid in ids:
                    if sid not in report:
                        missing.append(sid)
                return missing
        """
        found = findings_in(src)
        self.assertEqual([f.pattern for f in found], ["P1_substring_scan_in_loop"])
        self.assertEqual(found[0].confidence, "CONFIRMED_SHAPE")

    def test_finds_read_all_then_slice(self):
        """The exact shape from validate_collection.py, measured at 4.15x."""
        src = """
            def label_ok(path):
                return "SYNTHETIC" in path.read_text(encoding="utf-8")[:500].upper()
        """
        found = findings_in(src)
        self.assertIn("P2_read_all_then_slice", [f.pattern for f in found])
        self.assertEqual(found[0].confidence, "CONFIRMED_SHAPE")

    def test_finds_order_preserving_dedup_against_a_list(self):
        """`seen = []` + `if x not in seen` is the classic accidental O(n^2)."""
        src = """
            def distinct(items):
                seen = []
                for x in items:
                    if x not in seen:
                        seen.append(x)
                return seen
        """
        self.assertEqual(patterns_in(src), ["P1_list_membership_in_loop"])

    def test_finds_a_file_read_inside_the_loop_body_then_searched(self):
        src = """
            def check(path, ids):
                for sid in ids:
                    if sid not in path.read_text(encoding="utf-8"):
                        print(sid)
        """
        self.assertIn("P1_substring_scan_in_loop", patterns_in(src))

    def test_str_parameter_is_reported_but_only_as_a_candidate(self):
        """Size arrives across a function boundary, so it cannot be confirmed."""
        src = """
            def absent(ids, report_text: str):
                out = []
                for sid in ids:
                    if sid not in report_text:
                        out.append(sid)
                return out
        """
        found = findings_in(src)
        self.assertEqual([f.pattern for f in found], ["P1_substring_scan_in_loop"])
        self.assertEqual(found[0].confidence, "CANDIDATE",
                         "a value whose size the scanner cannot see must not be CONFIRMED")


class TestPrecision(unittest.TestCase):
    """Correct code must produce nothing. Each of these is a real false positive
    the first version of this scanner emitted against the delivered kit."""

    def test_dict_membership_in_a_loop_is_not_flagged(self):
        """PRECISION: `if key in some_dict` is already O(1). This single shape
        accounted for most of the 131 matches the first version produced."""
        src = """
            def f(rows):
                index = {}
                for r in rows:
                    if r["id"] in index:
                        continue
                    index[r["id"]] = r
        """
        self.assertEqual(patterns_in(src), [])

    def test_set_membership_in_a_loop_is_not_flagged(self):
        src = """
            def f(rows):
                known = {"a", "b"}
                seen = set()
                for r in rows:
                    if r in known:
                        pass
                    if r not in seen:
                        seen.add(r)
        """
        self.assertEqual(patterns_in(src), [])

    def test_membership_against_a_short_derived_string_is_not_flagged(self):
        """PRECISION: `if "=" not in part` over CSV tokens. Structurally it is a
        substring test in a loop, but the string is a token, not a document.
        The measured defect needs a LARGE string, and the only ones a
        source-only scanner can be sure are large came off disk."""
        src = """
            def parse(value):
                out = {}
                for part in (value or "").split(";"):
                    part = part.strip()
                    if "=" not in part:
                        out[part] = None
                return out
        """
        self.assertEqual(patterns_in(src), [])

    def test_reading_a_different_file_each_iteration_is_not_flagged(self):
        """PRECISION: this is the normal, correct way to read many files.
        Missing it made the first version report 40 matches, 0 of them real."""
        src = """
            def digests(paths):
                out = {}
                for p in paths:
                    with open(p, "rb") as fh:
                        out[p] = fh.read()
                return out
        """
        self.assertEqual(patterns_in(src), [])

    def test_read_in_the_loop_header_is_evaluated_once(self):
        """PRECISION: `for line in Path(p).read_text().splitlines()` reads ONCE.
        The iterable is evaluated before the body, so it is not a per-iteration
        read. The first version flagged this."""
        src = """
            def cpu_model(p):
                for line in Path(p).read_text(encoding="utf-8").splitlines():
                    if line.startswith("model name"):
                        return line
                return "UNKNOWN"
        """
        self.assertEqual(patterns_in(src), [])

    def test_slicing_a_string_that_is_not_a_file_read_is_not_flagged(self):
        src = """
            def f(header):
                return header[:500]
        """
        self.assertEqual(patterns_in(src), [])

    def test_membership_outside_any_loop_is_not_flagged(self):
        src = """
            def f(path, sid):
                report = path.read_text(encoding="utf-8")
                return sid in report
        """
        self.assertEqual(patterns_in(src), [])

    def test_small_literal_membership_is_not_flagged(self):
        """A short literal is config, not a quadratic."""
        src = """
            def f(rows):
                for r in rows:
                    if r in ("a", "b", "c"):
                        pass
        """
        self.assertEqual(patterns_in(src), [])


class TestHostileAndMissingInput(unittest.TestCase):
    """An unreadable file is never a clean file."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="opsperf-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_syntax_error_is_reported_unscannable_not_clean(self):
        (self.tmp / "broken.py").write_text("def f(:\n    pass\n", encoding="utf-8")
        report = sh.scan_tree(self.tmp)
        self.assertEqual(report["files_scanned"], 0)
        self.assertEqual(report["files_unscannable"], 1)
        self.assertIn("SyntaxError", report["unscannable"][0]["reason"])

    def test_non_utf8_file_is_reported_unscannable_not_clean(self):
        (self.tmp / "binary.py").write_bytes(b"\xff\xfe\x00 print('x')")
        report = sh.scan_tree(self.tmp)
        self.assertEqual(report["files_scanned"], 0)
        self.assertEqual(report["files_unscannable"], 1)
        self.assertIn("UnicodeDecodeError", report["unscannable"][0]["reason"])

    def test_empty_file_scans_clean(self):
        (self.tmp / "empty.py").write_text("", encoding="utf-8")
        report = sh.scan_tree(self.tmp)
        self.assertEqual(report["files_scanned"], 1)
        self.assertEqual(report["finding_count"], 0)
        self.assertEqual(report["files_unscannable"], 0)

    def test_a_tree_with_one_good_and_one_broken_file_reports_both(self):
        (self.tmp / "ok.py").write_text("x = 1\n", encoding="utf-8")
        (self.tmp / "bad.py").write_text("def (\n", encoding="utf-8")
        report = sh.scan_tree(self.tmp)
        self.assertEqual(report["files_scanned"], 1)
        self.assertEqual(report["files_unscannable"], 1)

    def test_empty_directory_scans_to_zero_not_to_an_error(self):
        report = sh.scan_tree(self.tmp)
        self.assertEqual(report["finding_count"], 0)
        self.assertEqual(report["files_scanned"], 0)

    def test_kit_scan_of_a_directory_with_no_lanes_is_zero_not_a_crash(self):
        report = scan_kit.scan_kit(self.tmp)
        self.assertEqual(report["lanes_scanned"], 0)
        self.assertEqual(report["finding_count"], 0)
        self.assertIn("scanned_at_utc", report["environment"])


class TestHonestyOfTheReport(unittest.TestCase):
    def test_unmeasured_patterns_carry_UNKNOWN_cost(self):
        """A pattern match is not a measurement. Only the two shapes actually
        measured under UIOWA-095 may carry a number."""
        src = """
            def distinct(items):
                seen = []
                for x in items:
                    if x not in seen:
                        seen.append(x)
        """
        found = findings_in(src)[0].to_dict(Path("/"))
        self.assertIsInstance(found["measured_cost"], str)
        self.assertIn("UNKNOWN", found["measured_cost"])

    def test_measured_patterns_cite_where_they_were_measured(self):
        src = """
            def check(root, ids):
                report = (root / "a.md").read_text(encoding="utf-8")
                for sid in ids:
                    if sid not in report:
                        pass
        """
        found = findings_in(src)[0].to_dict(Path("/"))
        self.assertIsInstance(found["measured_cost"], dict)
        self.assertIn("BENCHMARK_REPORT.md", found["measured_cost"]["measured_in"])

    def test_rendered_report_states_it_is_not_a_score(self):
        report = scan_kit.scan_kit(Path(tempfile.mkdtemp(prefix="opsperf-empty-")))
        text = scan_kit.render(report)
        self.assertIn("not a score", text.lower())
        self.assertIn("not proven defects", text.lower())

    def test_scanner_never_writes_into_the_tree_it_scans(self):
        """Read-only is a promise about other seats' lanes, so it gets a test."""
        tmp = Path(tempfile.mkdtemp(prefix="opsperf-ro-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "a.py").write_text("x = 1\n", encoding="utf-8")
        before = {p: p.stat().st_mtime_ns for p in sorted(tmp.rglob("*"))}
        sh.scan_tree(tmp)
        scan_kit.scan_kit(tmp)
        after = {p: p.stat().st_mtime_ns for p in sorted(tmp.rglob("*"))}
        self.assertEqual(before, after, "the scan modified the tree it was reading")
        self.assertEqual(sorted(p.name for p in tmp.iterdir()), ["a.py"])


class TestScannerParsesItsOwnSource(unittest.TestCase):
    def test_the_scanner_can_scan_itself(self):
        """Cheap smoke test that the walker handles real code, not just snippets."""
        here = Path(__file__).resolve().parent
        report = sh.scan_tree(here)
        self.assertEqual(report["files_unscannable"], 0,
                         f"the scanner could not parse its own lane: {report['unscannable']}")
        self.assertGreaterEqual(report["files_scanned"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
