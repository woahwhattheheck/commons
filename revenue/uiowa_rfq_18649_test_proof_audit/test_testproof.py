#!/usr/bin/env python3
"""Tests for the test-proof auditor.

A tool that judges other suites has to survive its own standard, so this file
does two things beyond the usual: it checks the auditor against fixtures with
known ground truth in BOTH directions (it must fire on the hollow lane and
must NOT fire on the solid one), and it proves the auditor never executes the
code it reads.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

import testproof

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")


def audit_fixtures():
    return testproof.audit_tree(FIXTURES, include_fixtures=True)


def kinds_for(findings, lane=None, path=None):
    out = []
    for f in findings:
        if lane and f.lane != lane:
            continue
        if path and f.path != path:
            continue
        out.append(f.kind)
    return sorted(out)


def write_lane(root, name, files):
    lane = os.path.join(root, name)
    os.makedirs(lane, exist_ok=True)
    for fn, body in files.items():
        with open(os.path.join(lane, fn), "w", encoding="utf-8") as fh:
            fh.write(body)
    return lane


class TestGroundTruthHollowLane(unittest.TestCase):
    """It must fire on each thing it claims to detect."""

    def setUp(self):
        self.findings, self.metrics = audit_fixtures()

    def test_a_file_with_no_test_methods_is_a_defect(self):
        self.assertIn("NO_TESTS_COLLECTED", kinds_for(self.findings, "hollow_lane", "test_empty.py"))

    def test_a_test_with_no_assertion_and_no_call_is_a_defect(self):
        found = [f for f in self.findings if f.kind == "TEST_WITHOUT_ASSERTION"]
        self.assertEqual([f.name for f in found], ["test_expected_value"])
        self.assertEqual(found[0].severity, "DEFECT")

    def test_a_tautological_assertion_is_a_defect(self):
        found = [f for f in self.findings if f.kind == "TAUTOLOGICAL_ASSERTION"]
        self.assertEqual([f.name for f in found], ["test_always_true"])

    def test_a_test_file_naming_nothing_in_its_lane_is_flagged(self):
        paths = sorted(f.path for f in self.findings if f.kind == "NO_REFERENCE_TO_LANE")
        self.assertEqual(paths, ["test_empty.py", "test_unrelated.py"])

    def test_a_guard_with_no_negative_case_is_flagged(self):
        found = [f for f in self.findings if f.kind == "GUARD_WITHOUT_NEGATIVE_CASE"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].lane, "hollow_lane")
        self.assertEqual(found[0].severity, "REVIEW")


class TestItDoesNotOverFire(unittest.TestCase):
    """The failure mode of a linter like this is a false accusation. Each of
    these is a real pattern that a naive implementation flags wrongly."""

    def setUp(self):
        self.findings, self.metrics = audit_fixtures()

    def test_the_solid_lane_produces_nothing_at_all(self):
        self.assertEqual(kinds_for(self.findings, "solid_lane"), [])

    def test_a_test_asserting_through_a_helper_is_not_flagged(self):
        names = [f.name for f in self.findings]
        self.assertNotIn("test_via_a_helper_still_counts", names)

    def test_a_suite_aggregator_is_recognised_not_reported(self):
        """A file that imports TestCase classes from siblings so one entry
        point runs them all has no test methods of its own and is entirely
        legitimate. The auditor over-fired on exactly this on its first live
        run against the repository."""
        with tempfile.TemporaryDirectory() as tmp:
            write_lane(tmp, "agg_lane", {
                "engine.py": "def go():\n    return 1\n",
                "parts_tests.py": (
                    "import unittest\nimport engine\n\n"
                    "class PartTests(unittest.TestCase):\n"
                    "    def test_go(self):\n        self.assertEqual(engine.go(), 1)\n"
                ),
                "test_all.py": "from parts_tests import PartTests  # noqa: F401\n",
            })
            findings, metrics = testproof.audit_tree(tmp, include_fixtures=True)
            self.assertNotIn("NO_TESTS_COLLECTED", kinds_for(findings, "agg_lane"))
            aggregators = metrics[0]["suite_aggregators"]
            self.assertEqual(aggregators[0]["path"], "test_all.py")
            self.assertEqual(aggregators[0]["runs"], ["parts_tests"])

    def test_a_lane_exercised_through_its_cli_is_not_called_unrelated(self):
        """A suite that runs the lane in a subprocess names the module by
        filename, not by import. Counting only imports flags it falsely."""
        with tempfile.TemporaryDirectory() as tmp:
            write_lane(tmp, "cli_lane", {
                "tool.py": "def main():\n    return 0\n",
                "test_tool.py": (
                    "import os\nimport subprocess\nimport sys\nimport unittest\n\n"
                    "class T(unittest.TestCase):\n"
                    "    def test_cli(self):\n"
                    "        proc = subprocess.run([sys.executable, 'tool.py'],\n"
                    "                              capture_output=True)\n"
                    "        self.assertEqual(proc.returncode, 0)\n"
                ),
            })
            findings, _ = testproof.audit_tree(tmp, include_fixtures=True)
            self.assertNotIn("NO_REFERENCE_TO_LANE", kinds_for(findings, "cli_lane"))

    def test_a_no_assertion_test_that_calls_code_is_review_not_defect(self):
        """It can still fail if the call raises. Calling that a defect
        overstates what the syntax shows."""
        found = [f for f in self.findings if f.kind == "SMOKE_TEST_NO_ASSERTION"]
        self.assertEqual([f.name for f in found], ["test_rate_is_accepted"])
        self.assertEqual(found[0].severity, "REVIEW")

    def test_an_assertion_against_a_variable_is_not_a_tautology(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_lane(tmp, "ok_lane", {
                "m.py": "def add(a, b):\n    return a + b\n",
                "test_m.py": (
                    "import unittest\nimport m\n\n"
                    "class T(unittest.TestCase):\n"
                    "    def test_add(self):\n"
                    "        self.assertEqual(m.add(2, 3), 5)\n"
                    "    def test_flag(self):\n"
                    "        self.assertTrue(m.add(1, 1) == 2)\n"
                ),
            })
            findings, _ = testproof.audit_tree(tmp, include_fixtures=True)
            self.assertNotIn("TAUTOLOGICAL_ASSERTION", kinds_for(findings, "ok_lane"))


class TestItReadsButNeverRuns(unittest.TestCase):
    def test_auditing_a_module_does_not_execute_it(self):
        """The whole safety case for pointing this at other people's lanes is
        that it parses and never imports. Proven, not asserted in prose."""
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "SIDE_EFFECT_HAPPENED")
            write_lane(tmp, "sneaky_lane", {
                "sneaky.py": (
                    "import os\n"
                    "with open(%r, 'w') as fh:\n"
                    "    fh.write('the auditor imported this module')\n\n"
                    "def validate(x):\n"
                    "    if x < 0:\n        raise ValueError('no')\n    return x\n" % marker
                ),
                "test_sneaky.py": (
                    "import unittest\nimport sneaky\n\n"
                    "class T(unittest.TestCase):\n"
                    "    def test_ok(self):\n        self.assertEqual(sneaky.validate(1), 1)\n"
                ),
            })
            testproof.audit_tree(tmp, include_fixtures=True)
            self.assertFalse(os.path.exists(marker),
                             "the auditor executed code it was only supposed to read")

    def test_auditing_writes_nothing_into_the_audited_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_lane(tmp, "quiet_lane", {
                "m.py": "def f():\n    return 1\n",
                "test_m.py": ("import unittest\nimport m\n\n"
                              "class T(unittest.TestCase):\n"
                              "    def test_f(self):\n        self.assertEqual(m.f(), 1)\n"),
            })
            before = sorted(os.listdir(os.path.join(tmp, "quiet_lane")))
            testproof.audit_tree(tmp, include_fixtures=True)
            self.assertEqual(sorted(os.listdir(os.path.join(tmp, "quiet_lane"))), before)


class TestItProvesItCanFail(unittest.TestCase):
    def test_injecting_a_hollow_test_into_a_clean_lane_turns_it_red(self):
        """A checker that has never gone red is worth nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            files = {
                "m.py": "def f():\n    return 1\n",
                "test_m.py": ("import unittest\nimport m\n\n"
                              "class T(unittest.TestCase):\n"
                              "    def test_f(self):\n        self.assertEqual(m.f(), 1)\n"
                              "    def test_raises(self):\n"
                              "        with self.assertRaises(TypeError):\n"
                              "            m.f(1)\n"),
            }
            write_lane(tmp, "clean_lane", files)
            findings, _ = testproof.audit_tree(tmp, include_fixtures=True)
            self.assertEqual(kinds_for(findings, "clean_lane"), [])

            files["test_m.py"] += "    def test_nothing(self):\n        placeholder = 1\n"
            write_lane(tmp, "clean_lane", files)
            findings, _ = testproof.audit_tree(tmp, include_fixtures=True)
            self.assertIn("TEST_WITHOUT_ASSERTION", kinds_for(findings, "clean_lane"))


class TestSeverityAndOutput(unittest.TestCase):
    def test_defect_kinds_are_the_mechanically_certain_ones(self):
        defects = sorted(k for k, (sev, _m) in testproof.FINDING_KINDS.items() if sev == "DEFECT")
        self.assertEqual(defects, ["NO_TESTS_COLLECTED", "TAUTOLOGICAL_ASSERTION",
                                   "TEST_WITHOUT_ASSERTION"])

    def test_heuristic_kinds_are_never_reported_as_defects(self):
        for kind in ("NO_REFERENCE_TO_LANE", "GUARD_WITHOUT_NEGATIVE_CASE",
                     "SMOKE_TEST_NO_ASSERTION", "UNPARSEABLE"):
            self.assertEqual(testproof.FINDING_KINDS[kind][0], "REVIEW", kind)

    def test_an_unparseable_file_is_reported_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_lane(tmp, "broken_lane", {"test_broken.py": "def (:\n"})
            findings, _ = testproof.audit_tree(tmp, include_fixtures=True)
            self.assertIn("UNPARSEABLE", kinds_for(findings, "broken_lane"))

    def test_the_data_payload_carries_no_ranking_or_score(self):
        """Checked against the payload, not the prose -- the report's own
        disclaimer says it does not rank lanes, and grepping the words would
        match that sentence."""
        findings, metrics = audit_fixtures()
        payload = json.dumps({
            "summary": testproof.summarise(findings, metrics),
            "findings": [f.as_dict() for f in findings],
            "metrics": metrics,
        }).lower()
        for banned in ("rank", "leaderboard", "worst", "grade", "percentile", "score"):
            self.assertNotIn(banned, payload, "found %r in the audit payload" % banned)

    def test_no_metric_orders_lanes_against_each_other(self):
        _findings, metrics = audit_fixtures()
        for m in metrics:
            self.assertNotIn("position", m)
            self.assertNotIn("percentile", m)
            self.assertIsInstance(m["test_methods"], int)

    def test_the_report_says_a_clean_lane_is_not_certified_correct(self):
        findings, metrics = audit_fixtures()
        text = testproof.render_markdown(findings, metrics, "fixtures")
        self.assertIn("not evidence of correctness", text)

    def test_summary_counts_agree_with_the_finding_list(self):
        findings, metrics = audit_fixtures()
        s = testproof.summarise(findings, metrics)
        self.assertEqual(s["findings_total"], len(findings))
        self.assertEqual(s["defects"] + s["review_items"], len(findings))
        self.assertEqual(sum(s["by_kind"].values()), len(findings))


class TestCli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "testproof.py")] + list(args),
            cwd=HERE, capture_output=True, text=True,
        )

    def test_defects_exit_one_and_three_files_are_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.run_cli("--root", FIXTURES, "--include-fixtures", "--outdir", tmp)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            for name in ("findings.csv", "audit.json", "audit.md"):
                self.assertTrue(os.path.exists(os.path.join(tmp, name)), name)
            with open(os.path.join(tmp, "audit.json"), encoding="utf-8") as fh:
                payload = json.load(fh)
            self.assertEqual(payload["summary"]["defects"], 3)

    def test_a_clean_lane_exits_zero(self):
        proc = self.run_cli("--root", FIXTURES, "--include-fixtures", "--lane", "solid_lane")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_a_missing_root_exits_two_without_a_traceback(self):
        proc = self.run_cli("--root", os.path.join(HERE, "no-such-dir"))
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn("Traceback", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
