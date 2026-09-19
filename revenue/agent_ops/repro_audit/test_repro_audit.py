#!/usr/bin/env python3
"""Tests for the cross-lane reproducibility audit.

The load-bearing ones: the audit must go RED on the deliberately broken fixture
lane, it must never write into a source lane, and UNKNOWN must never be
reported as a pass.

Run:  python3 -m unittest -v test_repro_audit
"""

import os
import shutil
import tempfile
import unittest

import repro_audit as R

HERE = os.path.dirname(os.path.abspath(__file__))
GOOD = os.path.join(HERE, "fixtures", "lane_deterministic")
BAD = os.path.join(HERE, "fixtures", "lane_nondeterministic")


def make_lane(tmp, name, readme, files=None):
    root = os.path.join(tmp, name)
    os.makedirs(root)
    if readme is not None:
        with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as handle:
            handle.write(readme)
    for filename, body in (files or {}).items():
        with open(os.path.join(root, filename), "w", encoding="utf-8") as handle:
            handle.write(body)
    return root


class CommandExtractionTests(unittest.TestCase):

    def test_commands_come_out_of_fenced_blocks_only(self):
        text = ("Do not run python3 nope.py here.\n\n"
                "```bash\npython3 gen.py\n```\n")
        self.assertEqual(["python3 gen.py"], R.documented_commands(text))

    def test_trailing_comments_are_stripped_and_duplicates_dropped(self):
        text = "```\npython3 gen.py   # writes out/\npython3 gen.py\n```\n"
        self.assertEqual(["python3 gen.py"], R.documented_commands(text))

    def test_line_continuations_are_joined(self):
        text = "```\npython3 gen.py \\\n    --flag value\n```\n"
        self.assertEqual(["python3 gen.py --flag value"], R.documented_commands(text))

    def test_no_fenced_block_means_no_commands(self):
        self.assertEqual([], R.documented_commands("Run python3 gen.py somehow."))


class CommandClassificationTests(unittest.TestCase):

    def test_test_suites_servers_and_shell_pipelines_are_refused(self):
        for command, fragment in (
                ("python3 -m unittest discover", "test suite"),
                ("python3 server.py", "server"),
                ("python3 gen.py > out.txt", "shell"),
                ("python3 gen.py && python3 other.py", "shell")):
            runnable, reason = R.classify_command(command, GOOD)
            self.assertFalse(runnable, command)
            self.assertIn(fragment, reason)

    def test_a_script_that_is_not_in_the_lane_is_refused_by_name(self):
        runnable, reason = R.classify_command("python3 missing.py", GOOD)
        self.assertFalse(runnable)
        self.assertIn("missing.py", reason)

    def test_a_real_command_is_runnable(self):
        self.assertEqual((True, ""), R.classify_command("python3 gen.py", GOOD))

    def test_reaching_above_the_lane_is_detected(self):
        self.assertTrue(R.references_outside_lane("python3 gen.py --root ../"))
        self.assertTrue(R.references_outside_lane("python3 gen.py ../sibling/x.md"))
        self.assertFalse(R.references_outside_lane("python3 gen.py fixtures/x.md"))


class RedirectTests(unittest.TestCase):

    def test_absolute_arguments_are_moved_inside_the_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts, notes = R.redirect_absolute_paths(
                ["python3", "gen.py", "/tmp/report.json", "fixtures/in.json"], tmp)
            self.assertTrue(parts[2].startswith(os.path.join(tmp, "_audit_redirect")))
            self.assertEqual("fixtures/in.json", parts[3])
            self.assertEqual([{"original": "/tmp/report.json",
                               "redirected_to": "_audit_redirect/report.json"}], notes)

    def test_flag_equals_absolute_form_is_handled(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts, notes = R.redirect_absolute_paths(
                ["python3", "gen.py", "--out=/tmp/o"], tmp)
            self.assertTrue(parts[2].startswith("--out="))
            self.assertIn("_audit_redirect", parts[2])
            self.assertEqual(1, len(notes))

    def test_a_command_with_no_absolute_paths_is_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts, notes = R.redirect_absolute_paths(["python3", "gen.py", "a", "b"], tmp)
            self.assertEqual(["python3", "gen.py", "a", "b"], parts)
            self.assertEqual([], notes)
            self.assertFalse(os.path.exists(os.path.join(tmp, "_audit_redirect")))


class DifferenceClassificationTests(unittest.TestCase):

    def test_same_lines_in_a_different_order_is_the_hash_seed_signature(self):
        self.assertEqual("ordering_like",
                         R.classify_difference("b\na\nc\n", "a\nc\nb\n", "/x", "/y"))

    def test_a_clock_in_the_output_is_recognised(self):
        self.assertEqual("timestamp_like",
                         R.classify_difference("run at 2026-09-19 10:00:01\n",
                                               "run at 2026-09-19 10:00:09\n",
                                               "/x", "/y"))

    def test_an_embedded_working_directory_is_recognised(self):
        self.assertEqual("absolute_path_like",
                         R.classify_difference("in /alpha/lane\n", "in /beta/lane\n",
                                               "/alpha", "/beta"))

    def test_unreadable_bytes_are_named_rather_than_guessed(self):
        self.assertEqual("binary_or_unreadable",
                         R.classify_difference(None, "x", "/a", "/b"))

    def test_different_line_counts_are_reported_as_such(self):
        self.assertEqual("length_differs",
                         R.classify_difference("a\n", "a\nb\n", "/a", "/b"))


class AuditVerdictTests(unittest.TestCase):

    def test_the_deterministic_fixture_is_reproducible(self):
        record = R.audit_lane(GOOD)
        self.assertEqual(R.REPRODUCIBLE, record["verdict"])

    def test_the_audit_can_go_red(self):
        # A checker that cannot fail is worth nothing.
        record = R.audit_lane(BAD)
        self.assertEqual(R.VARIES, record["verdict"])
        failing = [c for c in record["commands"] if c["verdict"] == R.VARIES][0]
        self.assertTrue(failing["differing_files"])
        causes = set(failing["causes"].values())
        self.assertIn("timestamp_like", causes)
        self.assertIn("absolute_path_like", causes)

    def test_the_audit_never_writes_into_the_source_lane(self):
        before = R.snapshot(BAD)
        R.audit_lane(BAD)
        self.assertEqual(before, R.snapshot(BAD))

    def test_a_lane_with_no_readme_is_unknown_and_says_it_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_lane(tmp, "no_readme", None)
            record = R.audit_lane(root)
            self.assertEqual(R.UNKNOWN, record["verdict"])
            self.assertIn("not assessed", record["note"])

    def test_a_readme_with_no_runnable_command_is_unknown_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_lane(tmp, "prose_only", "# Lane\n\nNo commands here.\n")
            record = R.audit_lane(root)
            self.assertEqual(R.UNKNOWN, record["verdict"])
            self.assertIn("This is not a pass", record["note"])

    def test_a_lane_documenting_only_its_test_suite_is_unknown_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_lane(tmp, "tests_only",
                             "# Lane\n\n```\npython3 -m unittest -v test_x\n```\n")
            record = R.audit_lane(root)
            self.assertEqual(R.UNKNOWN, record["verdict"])
            self.assertEqual([R.SKIPPED], [c["verdict"] for c in record["commands"]])
            self.assertIn("This is not a pass", record["note"])

    def test_a_command_that_genuinely_fails_is_reported_with_its_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_lane(tmp, "broken", "# Lane\n\n```\npython3 gen.py\n```\n",
                             {"gen.py": "import sys\n"
                                        "sys.stderr.write('boom\\n')\n"
                                        "raise SystemExit(3)\n"})
            record = R.audit_lane(root)
            self.assertEqual(R.FAILED, record["verdict"])
            command = record["commands"][0]
            self.assertIn("boom", command["detail"])
            self.assertEqual("lane", command["probable_owner"])

    def test_a_nonzero_exit_that_signals_findings_is_not_called_a_failure(self):
        # A checker exiting 1 because it found problems is behaving correctly.
        with tempfile.TemporaryDirectory() as tmp:
            root = make_lane(tmp, "checker", "# Lane\n\n```\npython3 gen.py\n```\n",
                             {"gen.py": "print('3 problems found')\n"
                                        "raise SystemExit(1)\n"})
            record = R.audit_lane(root)
            self.assertEqual(R.REPRODUCIBLE, record["verdict"])
            self.assertTrue(record["commands"][0]["exit_is_a_finding_signal"])

    def test_runs_disagreeing_on_their_exit_code_are_reported_as_varying(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_lane(tmp, "flappy", "# Lane\n\n```\npython3 gen.py\n```\n",
                             {"gen.py": "import os\n"
                                        "raise SystemExit(int(os.environ"
                                        "['PYTHONHASHSEED']))\n"})
            record = R.audit_lane(root)
            self.assertEqual(R.VARIES, record["verdict"])
            self.assertIn("exit code differed", record["commands"][0]["detail"])

    def test_the_worst_verdict_among_a_lanes_commands_wins(self):
        self.assertEqual(0, R.VERDICT_RANK[R.VARIES])
        self.assertEqual(max(R.VERDICT_RANK.values()), R.VERDICT_RANK[R.REPRODUCIBLE])
        self.assertLess(R.VERDICT_RANK[R.FAILED], R.VERDICT_RANK[R.UNKNOWN])

    def test_failure_ownership_separates_harness_limits_from_lane_defects(self):
        self.assertEqual("harness",
                         R.probable_owner("python3 gen.py ../sibling", "x", [])[0])
        self.assertEqual("environment",
                         R.probable_owner("python3 gen.py",
                                          "ModuleNotFoundError: no 'pypdf'", [])[0])
        self.assertEqual("lane", R.probable_owner("python3 gen.py", "KeyError", [])[0])


class SnapshotAndReportTests(unittest.TestCase):

    def test_snapshot_ignores_bytecode(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "__pycache__"))
            with open(os.path.join(tmp, "__pycache__", "x.pyc"), "wb") as handle:
                handle.write(b"\x00")
            with open(os.path.join(tmp, "real.txt"), "w", encoding="utf-8") as handle:
                handle.write("hello")
            self.assertEqual(["real.txt"], sorted(R.snapshot(tmp)))

    def test_tree_audit_counts_every_lane_and_states_the_unknown_rule(self):
        result = R.audit_tree(os.path.join(HERE, "fixtures"), "lane_*")
        self.assertEqual(2, result["lanes_audited"])
        self.assertEqual(1, result["counts"][R.REPRODUCIBLE])
        self.assertEqual(1, result["counts"][R.VARIES])
        self.assertIn("It is not a pass", result["unknown_notice"])

    def test_both_renderers_produce_the_verdicts(self):
        result = R.audit_tree(os.path.join(HERE, "fixtures"), "lane_*")
        for text in (R.render_text(result), R.render_markdown(result)):
            self.assertIn("lane_deterministic", text)
            self.assertIn(R.VARIES, text)

    def test_exit_code_is_one_when_something_varies(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(1, R.main(["--tree", os.path.join(HERE, "fixtures"),
                                        "--pattern", "lane_*", "--out", tmp]))
            self.assertTrue(os.path.exists(os.path.join(tmp, "audit.json")))
            self.assertTrue(os.path.exists(os.path.join(tmp, "audit.md")))

    def test_exit_code_is_zero_when_nothing_varies(self):
        with tempfile.TemporaryDirectory() as tmp:
            copied = os.path.join(tmp, "tree")
            os.makedirs(copied)
            shutil.copytree(GOOD, os.path.join(copied, "lane_deterministic"))
            self.assertEqual(0, R.main(["--tree", copied, "--pattern", "lane_*"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
