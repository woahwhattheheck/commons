#!/usr/bin/env python3
"""Tests for the OPS-RUN-SWEEP delivery-kit sweep.

Built on synthetic lane trees, not on the real repository, so the suite is
hermetic and does not change meaning as other seats land work.

The ones that matter:

  * a suite that runs zero tests must never be counted as a pass
  * a module that errors before reaching the runner must be distinguished
    from a test that ran and failed
  * a lane with no suite must be UNKNOWN, never a failure
  * the sweep must not write into a lane it did not create

Run:  python3 -m unittest -v test_run_sweep
"""

import hashlib
import json
import os
import shutil
import tempfile
import unittest

import run_sweep as rs


PASSING = """import unittest
class T(unittest.TestCase):
    def test_a(self):
        self.assertTrue(True)
    def test_b(self):
        self.assertEqual(1, 1)
"""

FAILING = """import unittest
class T(unittest.TestCase):
    def test_a(self):
        self.assertEqual(1, 2)
"""

NO_TESTCASE = """# A file named like a test that contains no test case.
HELPER = 1
"""

IMPORT_ERROR = """import a_module_that_does_not_exist
import unittest
class T(unittest.TestCase):
    def test_a(self):
        self.assertTrue(True)
"""

SLOW = """import time, unittest
class T(unittest.TestCase):
    def test_slow(self):
        time.sleep(30)
"""


class SweepHarness(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.revenue = os.path.join(self.root, "revenue")
        os.makedirs(self.revenue)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def lane(self, name, files):
        path = os.path.join(self.revenue, "uiowa_rfq_18649_" + name)
        for rel, content in files.items():
            full = os.path.join(path, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as handle:
                handle.write(content)
        os.makedirs(path, exist_ok=True)
        return path

    def sweep(self, timeout=60):
        return rs.sweep(self.root, "uiowa_rfq_18649_", timeout, "2026-09-19")

    def lanes_by_name(self, report):
        return {l["lane"]: l for l in report["lanes"]}


class Outcomes(SweepHarness):

    def test_a_passing_lane_passes(self):
        self.lane("good", {"test_good.py": PASSING})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_good"]
        self.assertEqual(lane["lane_outcome"], rs.PASS)
        self.assertEqual(lane["tests_run_total"], 2)
        self.assertEqual(report["summary"]["lanes_passing"], 1)

    def test_a_failing_lane_fails_and_keeps_its_output(self):
        self.lane("bad", {"test_bad.py": FAILING})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_bad"]
        self.assertEqual(lane["lane_outcome"], rs.FAIL)
        self.assertEqual(lane["suites"][0]["outcome"], rs.FAIL)
        self.assertIn("FAILED", lane["suites"][0]["status_line"])
        self.assertTrue(lane["suites"][0]["tail"],
                        "a failing suite must keep its output")

    def test_zero_tests_is_never_a_pass(self):
        # This is the headline guard. The module imports fine and unittest
        # exits zero, so a sweep that trusts the exit code records it green.
        self.lane("hollow", {"test_hollow.py": NO_TESTCASE})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_hollow"]
        self.assertEqual(lane["suites"][0]["outcome"], rs.EMPTY)
        self.assertEqual(lane["suites"][0]["exit_code"], 0)
        self.assertEqual(lane["suites"][0]["tests_run"], 0)
        self.assertEqual(lane["lane_outcome"], rs.EMPTY)
        self.assertEqual(report["summary"]["lanes_passing"], 0)
        self.assertEqual(report["summary"]["lanes_asserting_nothing"], 1)
        self.assertIn("uiowa_rfq_18649_hollow::test_hollow.py",
                      report["summary"]["empty_suites"])

    def test_import_error_is_an_error_not_a_failure(self):
        # unittest wraps an unimportable module in a synthetic failing test,
        # so it reports "Ran 1 test ... FAILED". That is a different finding
        # from a test that executed and failed an assertion.
        self.lane("broken", {"test_broken.py": IMPORT_ERROR})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_broken"]
        self.assertEqual(lane["suites"][0]["outcome"], rs.ERROR)
        self.assertEqual(lane["lane_outcome"], rs.FAIL)
        self.assertIn("did not load", lane["suites"][0]["note"])

    def test_a_placeholder_test_does_not_inflate_the_executed_count(self):
        # The module's own tests never ran, so the total must not claim one did.
        self.lane("broken", {"test_broken.py": IMPORT_ERROR})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_broken"]
        self.assertEqual(lane["suites"][0]["tests_run"], 0)
        self.assertEqual(lane["tests_run_total"], 0)
        self.assertEqual(report["summary"]["tests_executed"], 0)

    def test_timeout_is_recorded_as_timeout(self):
        self.lane("slow", {"test_slow.py": SLOW})
        report = self.sweep(timeout=1)
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_slow"]
        self.assertEqual(lane["suites"][0]["outcome"], rs.TIMEOUT)
        self.assertEqual(lane["lane_outcome"], rs.FAIL)

    def test_a_real_suite_alongside_an_empty_module_still_passes(self):
        # The lane works; the hollow file is still reported so it can be
        # removed or filled.
        self.lane("mixed", {"test_hollow.py": NO_TESTCASE,
                            "tests/test_real.py": PASSING})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_mixed"]
        self.assertEqual(lane["lane_outcome"], rs.PASS)
        self.assertIn("uiowa_rfq_18649_mixed::test_hollow.py",
                      report["summary"]["empty_suites"])

    def test_tests_subdirectory_is_discovered(self):
        self.lane("subdir", {"tests/test_real.py": PASSING})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_subdir"]
        self.assertEqual(lane["lane_outcome"], rs.PASS)
        self.assertEqual(lane["tests_run_total"], 2)


class Categories(SweepHarness):

    def test_a_lane_with_code_but_no_suite_is_not_a_failure(self):
        self.lane("tool", {"validate.py": "print('ok')\n"})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_tool"]
        self.assertEqual(lane["category"], rs.EXECUTABLE_NO_SUITE)
        self.assertEqual(lane["lane_outcome"], "NO_SUITE")
        self.assertEqual(report["summary"]["lanes_failing"], 0)
        self.assertEqual(report["summary"]["lanes_with_a_suite"], 0)

    def test_a_documents_only_lane_is_not_a_failure(self):
        self.lane("docs", {"README.md": "# notes\n", "guide.md": "text\n"})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_docs"]
        self.assertEqual(lane["category"], rs.DOCUMENTS_ONLY)
        self.assertEqual(lane["lane_outcome"], "NO_SUITE")
        self.assertEqual(report["summary"]["lanes_failing"], 0)

    def test_lanes_without_a_suite_stay_out_of_the_pass_denominator(self):
        self.lane("good", {"test_good.py": PASSING})
        self.lane("docs", {"README.md": "# notes\n"})
        report = self.sweep()
        s = report["summary"]
        self.assertEqual(s["lanes_seen"], 2)
        self.assertEqual(s["lanes_with_a_suite"], 1)
        self.assertEqual(s["lanes_passing"], 1)
        self.assertEqual(s["lanes_documents_only"], 1)


class CollisionSignal(SweepHarness):

    def test_two_root_readmes_are_the_strong_signal(self):
        self.lane("shared", {
            "README.md": "Built by OP5-ALPHA\n",
            "README-second-implementation.md": "Also here: ZZ-Bravo\n",
            "test_x.py": PASSING})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_shared"]
        self.assertTrue(lane["shared_directory_signal"])
        self.assertIn("uiowa_rfq_18649_shared",
                      report["summary"]["shared_directory_lanes"])

    def test_nested_readmes_in_fixtures_are_not_a_collision(self):
        # A kit shipping a sample tree would otherwise look like a collision.
        self.lane("kit", {
            "README.md": "Built by OP5-ALPHA\n",
            "fixtures/minikit/README.md": "sample\n",
            "fixtures/minikit/inner/README.md": "sample\n",
            "test_x.py": PASSING})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_kit"]
        self.assertEqual(len(lane["readme_files"]), 3)
        self.assertEqual(len(lane["root_readme_files"]), 1)
        self.assertFalse(lane["shared_directory_signal"])
        self.assertEqual(report["summary"]["shared_directory_lanes"], [])

    def test_naming_another_seat_is_reported_but_not_a_collision(self):
        self.lane("cites", {
            "README.md": "Built by OP5-ALPHA. Consumes ZZ-Bravo's contract.\n",
            "test_x.py": PASSING})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_cites"]
        self.assertTrue(lane["multi_seat"])
        self.assertFalse(lane["shared_directory_signal"])
        self.assertIn("uiowa_rfq_18649_cites", report["summary"]["multi_seat_lanes"])

    def test_a_single_seat_lane_is_not_flagged(self):
        self.lane("solo", {"README.md": "Built by OP5-ALPHA\n",
                           "test_x.py": PASSING})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_solo"]
        self.assertEqual(lane["seats_named"], ["OP5-ALPHA"])
        self.assertFalse(lane["multi_seat"])

    def test_prerequisites_file_is_detected(self):
        self.lane("deps", {"requirements.txt": "pypdf>=6,<7\n",
                           "test_x.py": PASSING})
        report = self.sweep()
        lane = self.lanes_by_name(report)["uiowa_rfq_18649_deps"]
        self.assertEqual(lane["prerequisites_file"], "requirements.txt")
        self.assertIn("uiowa_rfq_18649_deps",
                      report["summary"]["lanes_with_prerequisites"])


class Parsing(unittest.TestCase):

    def test_reads_the_test_count(self):
        count, status = rs.parse_unittest_output(
            "..\n---\nRan 2 tests in 0.001s\n\nOK\n")
        self.assertEqual(count, 2)
        self.assertEqual(status, "OK")

    def test_singular_test_is_parsed(self):
        count, _status = rs.parse_unittest_output("Ran 1 test in 0.000s\n\nOK\n")
        self.assertEqual(count, 1)

    def test_last_run_line_wins_when_several_are_present(self):
        text = "Ran 3 tests in 0.1s\nOK\nRan 9 tests in 0.2s\nOK\n"
        count, _status = rs.parse_unittest_output(text)
        self.assertEqual(count, 9)

    def test_no_run_line_means_nothing_executed(self):
        count, _status = rs.parse_unittest_output("Traceback...\nImportError\n")
        self.assertIsNone(count)

    def test_empty_output_does_not_crash(self):
        self.assertEqual(rs.parse_unittest_output(""), (None, ""))
        self.assertEqual(rs.parse_unittest_output(None), (None, ""))

    def test_classification_truth_table(self):
        self.assertEqual(rs.classify(0, 5, "OK", False), rs.PASS)
        self.assertEqual(rs.classify(0, 0, "OK", False), rs.EMPTY)
        self.assertEqual(rs.classify(1, 5, "FAILED (failures=1)", False), rs.FAIL)
        self.assertEqual(rs.classify(0, 5, "FAILED (failures=1)", False), rs.FAIL)
        self.assertEqual(rs.classify(None, None, "", False), rs.ERROR)
        self.assertEqual(rs.classify(0, 5, "OK", True), rs.TIMEOUT)

    def test_a_module_that_would_not_load_is_an_error_not_a_failure(self):
        # unittest reports this as "Ran 1 test ... FAILED (errors=1)", which
        # is indistinguishable from a broken assertion unless the loader
        # marker is read.
        output = ("ERROR: test_x (unittest.loader._FailedTest.test_x)\n"
                  "ImportError: Failed to import test module: test_x\n"
                  "Ran 1 test in 0.000s\n\nFAILED (errors=1)\n")
        self.assertEqual(
            rs.classify(1, 1, "FAILED (errors=1)", False, output), rs.ERROR)

    def test_a_genuine_assertion_error_stays_a_failure(self):
        output = ("F\nAssertionError: 1 != 2\n"
                  "Ran 6 tests in 0.077s\n\nFAILED (errors=2)\n")
        self.assertEqual(
            rs.classify(1, 6, "FAILED (errors=2)", False, output), rs.FAIL)


class Outputs(SweepHarness):

    def test_cli_writes_all_three_artifacts_and_exits_nonzero_on_a_failure(self):
        self.lane("good", {"test_good.py": PASSING})
        self.lane("bad", {"test_bad.py": FAILING})
        outdir = os.path.join(self.root, "out")
        code = rs.main(["--root", self.root, "--outdir", outdir,
                        "--observed-on", "2026-09-19", "--quiet"])
        self.assertEqual(code, 1, "a failing lane must be visible in the exit code")
        for name in ("run_sweep.json", "run_sweep.csv", "run_sweep_report.md"):
            self.assertTrue(os.path.exists(os.path.join(outdir, name)), name)

    def test_cli_exits_zero_when_every_lane_runs_clean(self):
        self.lane("good", {"test_good.py": PASSING})
        code = rs.main(["--root", self.root,
                        "--outdir", os.path.join(self.root, "out"),
                        "--observed-on", "2026-09-19", "--quiet"])
        self.assertEqual(code, 0)

    def test_missing_root_is_refused(self):
        code = rs.main(["--root", os.path.join(self.root, "nope"),
                        "--outdir", os.path.join(self.root, "out"),
                        "--observed-on", "2026-09-19", "--quiet"])
        self.assertEqual(code, 2)

    def test_observed_on_is_required(self):
        with self.assertRaises(SystemExit):
            rs.main(["--root", self.root])

    def test_csv_never_leaves_a_cell_blank(self):
        self.lane("good", {"test_good.py": PASSING})
        self.lane("docs", {"README.md": "# notes\n"})
        outdir = os.path.join(self.root, "out")
        rs.main(["--root", self.root, "--outdir", outdir,
                 "--observed-on", "2026-09-19", "--quiet"])
        import csv as csv_mod
        with open(os.path.join(outdir, "run_sweep.csv"), encoding="utf-8",
                  newline="") as handle:
            rows = list(csv_mod.DictReader(handle))
        self.assertEqual(len(rows), 2)
        for row in rows:
            for column, value in row.items():
                self.assertNotEqual(str(value).strip(), "",
                                    "blank %s for %s" % (column, row["lane"]))

    def test_report_names_the_failing_lane_and_its_output(self):
        self.lane("bad", {"test_bad.py": FAILING})
        report = self.sweep()
        text = rs.render_report(report)
        self.assertIn("uiowa_rfq_18649_bad", text)
        self.assertIn("FAILED", text)

    def test_report_states_what_a_pass_does_not_mean(self):
        self.lane("good", {"test_good.py": PASSING})
        text = rs.render_report(self.sweep())
        self.assertIn("not a statement", text)
        self.assertIn("maturity", text)


class ReadOnly(SweepHarness):
    """The sweep executes other seats' code. It must not modify it."""

    def _hash_tree(self, path):
        digests = {}
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in sorted(files):
                full = os.path.join(root, name)
                with open(full, "rb") as handle:
                    digests[os.path.relpath(full, path)] = hashlib.sha256(
                        handle.read()).hexdigest()
        return digests

    def test_no_lane_file_is_modified(self):
        # Running a Python module creates __pycache__; that is a side effect of
        # executing Python, not of this tool, and is excluded. Nothing else in
        # a lane may change.
        self.lane("good", {"test_good.py": PASSING, "README.md": "# x\n"})
        self.lane("bad", {"test_bad.py": FAILING})
        before = self._hash_tree(self.revenue)
        self.sweep()
        after = self._hash_tree(self.revenue)
        self.assertEqual(before, after)

    def test_sweep_creates_no_files_in_the_lane_root(self):
        self.lane("good", {"test_good.py": PASSING})
        lane_dir = os.path.join(self.revenue, "uiowa_rfq_18649_good")
        before = {n for n in os.listdir(lane_dir) if n != "__pycache__"}
        self.sweep()
        after = {n for n in os.listdir(lane_dir) if n != "__pycache__"}
        self.assertEqual(before, after)


class Determinism(SweepHarness):

    def test_classification_is_stable_across_runs(self):
        self.lane("good", {"test_good.py": PASSING})
        self.lane("hollow", {"test_hollow.py": NO_TESTCASE})
        self.lane("bad", {"test_bad.py": FAILING})

        def shape(report):
            return [(l["lane"], l["category"], l["lane_outcome"],
                     l["tests_run_total"],
                     [s["outcome"] for s in l["suites"]])
                    for l in report["lanes"]]

        self.assertEqual(shape(self.sweep()), shape(self.sweep()))

    def test_source_reads_no_clock(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "run_sweep.py"), encoding="utf-8") as handle:
            source = handle.read()
        for banned in ("datetime.now", "date.today", "random."):
            self.assertNotIn(banned, source,
                             "%s would make the report irreproducible" % banned)

    def test_json_is_serialisable(self):
        self.lane("good", {"test_good.py": PASSING})
        json.dumps(self.sweep())


if __name__ == "__main__":
    unittest.main(verbosity=2)
