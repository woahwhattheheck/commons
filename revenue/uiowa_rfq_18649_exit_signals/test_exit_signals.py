"""Tests for the kit exit-signal contract, scanner and wrapper.

Run:  python3 -m unittest -v test_exit_signals

The load-bearing assertions are the ones about not guessing: an unresolvable exit is
not a gate and not a pass, an unwrapped tool with no declared rule is INDETERMINATE
rather than clean, and a crash is not a finding.
"""

import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import contract
import report
import scan
import wrap

FIXTURES = os.path.join(HERE, "fixtures")


def fixture(name):
    return os.path.join(FIXTURES, name)


# ------------------------------------------------------------------ contract

class TestContract(unittest.TestCase):

    def test_indeterminate_outranks_clean(self):
        """Could-not-tell must never be reported as checked-and-clean."""
        self.assertEqual(contract.decide(findings=0, indeterminate=3),
                         contract.INDETERMINATE)
        self.assertEqual(contract.decide(findings=0, indeterminate=0), contract.CLEAN)

    def test_findings_outrank_indeterminate(self):
        self.assertEqual(contract.decide(findings=1, indeterminate=9),
                         contract.FINDINGS)

    def test_input_error_outranks_everything(self):
        self.assertEqual(contract.decide(findings=5, indeterminate=5,
                                         input_error=True), contract.INPUT_ERROR)

    def test_status_line_roundtrips(self):
        line = contract.status_line(contract.FINDINGS, "t", findings=2,
                                    indeterminate=1, note="x")
        parsed = contract.parse_status_line("noise\n" + line + "\nmore noise")
        self.assertEqual(parsed["code"], contract.FINDINGS)
        self.assertEqual(parsed["tool"], "t")
        self.assertEqual(parsed["findings"], "2")

    def test_off_contract_code_is_refused(self):
        with self.assertRaises(ValueError):
            contract.status_line(99, "t")

    def test_malformed_status_line_is_not_trusted(self):
        """Hostile: a line that looks like a status line but is not parseable."""
        self.assertIsNone(contract.parse_status_line("KIT-STATUS: code=abc"))
        self.assertIsNone(contract.parse_status_line("KIT-STATUS: code=99 status=X"))
        self.assertIsNone(contract.parse_status_line("no status here at all"))

    def test_last_status_line_wins(self):
        text = (contract.status_line(contract.CLEAN, "a") + "\n" +
                contract.status_line(contract.FINDINGS, "b"))
        self.assertEqual(contract.parse_status_line(text)["code"], contract.FINDINGS)


# ------------------------------------------------------------------- scanner

class TestScanner(unittest.TestCase):

    def _scan(self, name):
        return scan.scan_file(fixture(name))

    def _codes(self, name):
        return {f["code"] for f in self._scan(name)["findings"]}

    def test_real_gate_is_a_gate(self):
        result = self._scan("t_gate.py")
        self.assertEqual(result["classification"], scan.GATE)
        self.assertNotIn("NO_SIGNAL_PATH", self._codes("t_gate.py"))

    def test_report_only_tool_is_flagged(self):
        result = self._scan("t_report_only.py")
        self.assertEqual(result["classification"], scan.REPORT_ONLY)
        self.assertIn("NO_SIGNAL_PATH", self._codes("t_report_only.py"))

    def test_tool_that_prints_failure_and_exits_zero_is_high_severity(self):
        result = self._scan("t_false_clean.py")
        self.assertEqual(result["classification"], scan.REPORT_ONLY)
        finding = next(f for f in result["findings"] if f["code"] == "FALSE_CLEAN")
        self.assertEqual(finding["severity"], "HIGH")
        self.assertIn("fail", result["failure_vocabulary_printed"])

    def test_dead_nonzero_exit_is_not_counted_as_a_gate(self):
        """Hostile: a grep for sys.exit(1) calls this gated. It is dead text."""
        result = self._scan("t_dead_gate.py")
        self.assertEqual(result["classification"], scan.REPORT_ONLY)
        self.assertEqual(result["dead_nonzero_exits"], 1)
        self.assertIn("DEAD_GATE", self._codes("t_dead_gate.py"))

    def test_unresolvable_exit_is_neither_gate_nor_report_only(self):
        result = self._scan("t_dynamic.py")
        self.assertEqual(result["classification"], scan.INDETERMINATE)
        self.assertIn("UNRESOLVED_EXIT", self._codes("t_dynamic.py"))

    def test_runtime_declared_status_is_not_reported_as_a_defect(self):
        result = self._scan("t_contract.py")
        self.assertTrue(result["emits_contract_status"])
        codes = self._codes("t_contract.py")
        self.assertIn("RUNTIME_DECLARED_STATUS", codes)
        self.assertNotIn("UNRESOLVED_EXIT", codes)
        self.assertNotIn("NO_CONTRACT_LINE", codes)

    def test_crash_only_tool_is_distinguished_from_a_gate(self):
        result = self._scan("t_crash_only.py")
        self.assertEqual(result["classification"], scan.REPORT_ONLY)
        self.assertTrue(result["raises_uncaught"])
        self.assertIn("CRASH_AS_SIGNAL", self._codes("t_crash_only.py"))

    def test_unparseable_source_is_indeterminate_not_clean(self):
        result = scan.scan_source("def broken(:\n  pass\n", "bad.py")
        self.assertEqual(result["classification"], scan.INDETERMINATE)
        self.assertEqual(result["findings"][0]["code"], "UNPARSEABLE")

    def test_scanner_does_not_execute_or_import_what_it_reads(self):
        """A source file with a module-level side effect must not run."""
        marker = os.path.join(HERE, "out", "_scanner_side_effect_marker")
        if os.path.exists(marker):
            os.remove(marker)
        source = (f"import pathlib\n"
                  f"pathlib.Path({marker!r}).write_text('ran')\n"
                  f"if __name__ == '__main__':\n    pass\n")
        scan.scan_source(source, "hostile.py")
        self.assertFalse(os.path.exists(marker))

    def test_tree_scan_skips_non_entrypoints_and_reports_the_count(self):
        result = scan.scan_tree(FIXTURES)
        self.assertEqual(len(result["entrypoints"]), 7)
        self.assertGreaterEqual(result["non_entrypoint_files_skipped"], 0)

    def test_lane_prefix_restricts_the_scan(self):
        parent = os.path.dirname(HERE)
        everything = scan.scan_tree(parent)
        restricted = scan.scan_tree(parent, lane_prefix="uiowa_rfq_18649_exit_sig")
        self.assertLessEqual(len(restricted["entrypoints"]),
                             len(everything["entrypoints"]))
        for entry in restricted["entrypoints"]:
            self.assertTrue(entry["tool"].startswith("uiowa_rfq_18649_exit_sig")
                            or os.sep not in entry["tool"])


# ------------------------------------------------------------------- wrapper

class TestWrapper(unittest.TestCase):

    def _run(self, name, **kwargs):
        return wrap.run_tool([sys.executable, fixture(name)], **kwargs)

    def test_default_for_a_silent_tool_is_indeterminate_not_clean(self):
        """The whole point of the wrapper's default."""
        result = self._run("t_report_only.py")
        self.assertEqual(result["code"], contract.INDETERMINATE)
        self.assertEqual(result["basis"], "no_status_no_rule")

    def test_contract_aware_tool_is_believed(self):
        result = self._run("t_contract.py")
        self.assertEqual(result["code"], contract.FINDINGS)
        self.assertEqual(result["basis"], "contract_status_line")

    def test_crash_is_input_error_not_findings(self):
        """t_crash_only exits 1 exactly like t_gate. Only the traceback tells them
        apart, so that is what is checked."""
        crash = self._run("t_crash_only.py")
        self.assertEqual(crash["returncode"], 1)
        self.assertEqual(crash["code"], contract.INPUT_ERROR)
        self.assertEqual(crash["basis"], "uncaught_exception")

    def test_declared_exit_code_rule_is_honored(self):
        result = self._run("t_gate.py", rule=wrap.RULE_EXIT_CODE)
        self.assertEqual(result["code"], contract.FINDINGS)
        clean = self._run("t_report_only.py", rule=wrap.RULE_EXIT_CODE)
        self.assertEqual(clean["code"], contract.CLEAN)

    def test_stdout_marker_rule_catches_the_false_clean_tool(self):
        result = self._run("t_false_clean.py", rule=wrap.RULE_STDOUT_MARKERS,
                           markers=("FAIL", "ERROR"))
        self.assertEqual(result["code"], contract.FINDINGS)
        self.assertIn("FAIL", result["markers_hit"])

    def test_marker_rule_without_markers_is_an_input_error(self):
        result = self._run("t_report_only.py", rule=wrap.RULE_STDOUT_MARKERS,
                           markers=())
        self.assertEqual(result["code"], contract.INPUT_ERROR)

    def test_missing_executable_is_input_error(self):
        result = wrap.run_tool(["no_such_executable_qqq", "--help"])
        self.assertEqual(result["code"], contract.INPUT_ERROR)
        self.assertEqual(result["basis"], "tool_not_found")

    def test_tool_that_could_not_run_is_never_clean_or_findings(self):
        """A missing SCRIPT is not a missing EXECUTABLE: the interpreter runs fine
        and reports the error itself, so this falls to the default. The invariant
        that matters is that it is not recorded as a result either way."""
        result = wrap.run_tool([sys.executable, fixture("does_not_exist.py")])
        self.assertNotIn(result["code"], (contract.CLEAN, contract.FINDINGS))

    def test_unknown_rule_is_refused(self):
        with self.assertRaises(ValueError):
            self._run("t_gate.py", rule="trust_me")


# ------------------------------------------------------ the auditor dogfoods

class TestAuditorObeysItsOwnContract(unittest.TestCase):

    def _audit(self, root, extra=()):
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "audit_kit.py"), root,
             "--out", os.path.join(HERE, "out"), "--quiet", *extra],
            capture_output=True, text=True, cwd=HERE, check=False)

    def test_auditing_the_fixtures_returns_findings(self):
        completed = self._audit(FIXTURES)
        self.assertEqual(completed.returncode, contract.FINDINGS)
        parsed = contract.parse_status_line(completed.stdout)
        self.assertIsNotNone(parsed, completed.stdout)
        self.assertEqual(parsed["code"], contract.FINDINGS)

    def test_missing_root_is_input_error_not_clean(self):
        completed = self._audit(os.path.join(HERE, "no_such_directory"))
        self.assertEqual(completed.returncode, contract.INPUT_ERROR)
        self.assertEqual(contract.parse_status_line(completed.stdout)["code"],
                         contract.INPUT_ERROR)

    def test_auditor_scan_of_itself_is_classified(self):
        result = scan.scan_file(os.path.join(HERE, "audit_kit.py"))
        self.assertIn(result["classification"], (scan.GATE, scan.INDETERMINATE))
        self.assertTrue(result["emits_contract_status"])


# ------------------------------------------------------------------ reporting

class TestReporting(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.result = scan.scan_tree(FIXTURES)

    def test_summary_counts_match_the_entrypoints(self):
        stats = report.summarize(self.result)
        self.assertEqual(stats["gate_count"] + stats["report_only_count"] +
                         stats["indeterminate_count"], stats["entrypoints"])

    def test_markdown_lists_every_entrypoint(self):
        markdown = report.render_markdown(self.result)
        for entry in self.result["entrypoints"]:
            self.assertIn(entry["tool"], markdown)

    def test_csv_has_a_row_for_every_finding(self):
        rows = report.render_csv(self.result).strip().splitlines()
        expected = sum(max(1, len(e["findings"])) for e in self.result["entrypoints"])
        self.assertEqual(len(rows) - 1, expected)

    def test_rendering_is_deterministic(self):
        self.assertEqual(report.render_markdown(self.result),
                         report.render_markdown(self.result))


# ------------------------------------------------------------------ evidence

class TestRecordedEvidence(unittest.TestCase):

    def test_evidence_file_carries_its_provenance_and_the_correction(self):
        path = os.path.join(HERE, "evidence", "kit_scan_20260919.json")
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
        provenance = payload["provenance"]
        for key in ("branch", "commit", "scanned_on", "method", "scope",
                    "corrections"):
            self.assertIn(key, provenance)
        self.assertEqual(len(provenance["commit"]), 40)
        self.assertTrue(provenance["corrections"])
        self.assertTrue(any("WRONG" in item for item in provenance["corrections"]),
                        "a published figure that was later corrected must say so")
        self.assertGreater(payload["summary"]["entrypoints"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
