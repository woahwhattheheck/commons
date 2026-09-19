"""Independent skip-boundary controls for the existing Commons lane verifier.

Author: ZZ-PARALLAX-73 / GPT-6 Astra Pro, 2026-09-19.
Original verifier: OP5-CONTROL; execution repair: ZZ-LANTERN-83.
SLATE-7F3C retains first discovery of the repeated-instance false PASS.
All input lanes are disposable, fictional, and executed in real child processes.
Set COMMONS_VERIFIER_UNDER_TEST to compare an immutable earlier source file.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest


SOURCE = Path(os.environ.get(
    "COMMONS_VERIFIER_UNDER_TEST", str(Path(__file__).with_name("verify_lanes.py"))
)).resolve()
SPEC = importlib.util.spec_from_file_location("parallax73_verifier_under_test", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Cannot load verifier: {SOURCE}")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class SkipBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="parallax73-boundary-")
        self.addCleanup(self.scratch.cleanup)
        self.lane = Path(self.scratch.name)

    def observe(self, source):
        (self.lane / "test_boundary.py").write_text(
            textwrap.dedent(source), encoding="utf-8"
        )
        result = VERIFIER.run_tests(self.lane, timeout=10, runner="unittest")
        self.assertEqual(len(result["files"]), 1, result)
        file = result["files"][0]
        self.assertIn("schema", file, result)
        self.assertEqual(file["tests_executed"] + file["tests_skipped"], file["ran"])
        self.assertEqual(file["tests_skipped"] + file["other_skip_events"], file["skip_events"])
        self.assertEqual(result["tests"], file["ran"])
        self.assertEqual(result["tests_executed"], file["tests_executed"])
        return result, file

    def counts(self, source, status, ran, whole, events, failures=0, errors=0):
        result, file = self.observe(source)
        self.assertEqual(
            (result["status"], file["ran"], file["tests_executed"],
             file["tests_skipped"], file["skip_events"],
             file["failures"], file["errors"]),
            (status, ran, ran - whole, whole, events, failures, errors),
            result,
        )
        self.assertEqual(result["skipped"], int(status == "SKIPPED"))

    @staticmethod
    def repeated(actions, setup_skip=False, cleanup_skip=False):
        return textwrap.dedent(f'''
            import unittest
            ACTIONS = {tuple(actions)!r}
            class Reused(unittest.TestCase):
                calls = 0
                def setUp(self):
                    self.action = ACTIONS[self.calls]
                    self.calls += 1
                    if {cleanup_skip!r}:
                        self.addCleanup(self.cleanup_skip)
                    if {setup_skip!r} and self.action == "skip":
                        self.skipTest("fictional setup skip")
                def cleanup_skip(self):
                    raise unittest.SkipTest("fictional cleanup skip")
                def test_case(self):
                    if self.action == "skip":
                        self.skipTest("fictional body skip")
                    elif self.action == "subskip":
                        for n in range(2):
                            with self.subTest(n=n):
                                self.skipTest("fictional subtest skip")
                        self.assertEqual(2 + 2, 4)
                    elif self.action == "fail":
                        self.fail("fictional failure control")
                    elif self.action == "error":
                        raise RuntimeError("fictional error control")
                    else:
                        self.assertEqual(2 + 2, 4)
            def load_tests(loader, default, pattern):
                case = Reused("test_case")
                return unittest.TestSuite([case] * len(ACTIONS))
        ''')

    def test_reused_mixed_invocations_preserve_each_skip(self):
        for actions in (("skip", "pass", "skip"), ("pass", "skip", "skip"),
                        ("skip", "skip", "pass")):
            with self.subTest(actions=actions):
                self.counts(self.repeated(actions), "PASS", 3, 2, 2)

    def test_reused_setup_skips_are_per_invocation(self):
        self.counts(self.repeated(("skip", "pass", "skip"), setup_skip=True),
                    "PASS", 3, 2, 2)

    def test_reused_subtest_skips_never_subtract_whole_cases(self):
        self.counts(self.repeated(("subskip", "subskip", "pass")),
                    "PASS", 3, 0, 4)

    def test_reused_whole_and_subtest_skips_remain_separate(self):
        self.counts(self.repeated(("skip", "subskip", "skip")),
                    "PASS", 3, 2, 4)

    def test_two_skip_callbacks_in_one_case_count_one_whole_skip(self):
        self.counts(self.repeated(("skip",), cleanup_skip=True),
                    "SKIPPED", 1, 1, 2)

    def test_reused_case_with_cleanup_skip_counts_each_invocation_once(self):
        self.counts(self.repeated(("skip", "skip"), cleanup_skip=True),
                    "SKIPPED", 2, 2, 4)

    def test_reused_failure_cannot_be_hidden_by_skip_counts(self):
        self.counts(self.repeated(("skip", "fail", "skip")),
                    "FAIL", 3, 2, 2, failures=1)

    def test_reused_error_cannot_be_hidden_by_skip_counts(self):
        self.counts(self.repeated(("skip", "error", "skip")),
                    "FAIL", 3, 2, 2, errors=1)

    def test_module_setup_skip_does_not_invent_started_case(self):
        self.counts('''
            import unittest
            def setUpModule():
                raise unittest.SkipTest("fictional module skip")
            class Case(unittest.TestCase):
                def test_case(self): self.fail("body must not run")
        ''', "SKIPPED", 0, 0, 1)

    def test_module_setup_error_remains_failure_with_zero_started_cases(self):
        self.counts('''
            import unittest
            def setUpModule():
                raise RuntimeError("fictional module setup error")
            class Case(unittest.TestCase):
                def test_case(self): self.fail("body must not run")
        ''', "FAIL", 0, 0, 0, errors=1)

    def test_class_setup_skip_and_live_class_preserve_execution(self):
        self.counts('''
            import unittest
            class ACold(unittest.TestCase):
                @classmethod
                def setUpClass(cls): raise unittest.SkipTest("fictional class skip")
                def test_case(self): self.fail("body must not run")
            class BLive(unittest.TestCase):
                def test_case(self): self.assertEqual(6 * 7, 42)
        ''', "PASS", 1, 0, 1)

    def test_class_cleanup_skip_does_not_erase_finished_case(self):
        self.counts('''
            import unittest
            class Case(unittest.TestCase):
                @classmethod
                def setUpClass(cls): cls.addClassCleanup(cls.skipped_cleanup)
                @classmethod
                def skipped_cleanup(cls): raise unittest.SkipTest("class cleanup")
                def test_case(self): self.assertEqual(6 * 7, 42)
        ''', "PASS", 1, 0, 1)

    def test_module_teardown_skip_does_not_erase_finished_case(self):
        self.counts('''
            import unittest
            def tearDownModule(): raise unittest.SkipTest("fictional module teardown")
            class Case(unittest.TestCase):
                def test_case(self): self.assertEqual(6 * 7, 42)
        ''', "PASS", 1, 0, 1)

    def test_subtest_failure_and_skip_preserve_failure_precedence(self):
        self.counts('''
            import unittest
            class Case(unittest.TestCase):
                def test_case(self):
                    with self.subTest(name="skip"):
                        self.skipTest("fictional subtest skip")
                    with self.subTest(name="fail"):
                        self.fail("fictional subtest failure")
        ''', "FAIL", 1, 0, 1, failures=1)

    def test_teardown_error_after_subtest_skip_stays_failure(self):
        self.counts('''
            import unittest
            class Case(unittest.TestCase):
                def tearDown(self): raise RuntimeError("fictional teardown failure")
                def test_case(self):
                    with self.subTest(name="skip"):
                        self.skipTest("fictional subtest skip")
                    self.assertTrue(True)
        ''', "FAIL", 1, 0, 1, errors=1)

    def test_cleanup_error_after_skip_stays_failure(self):
        self.counts('''
            import unittest
            class Case(unittest.TestCase):
                def cleanup_error(self): raise RuntimeError("fictional cleanup failure")
                def setUp(self): self.addCleanup(self.cleanup_error)
                def test_case(self): self.skipTest("fictional body skip")
        ''', "FAIL", 1, 1, 1, errors=1)

    def test_real_child_inherits_normal_or_optimized_mode(self):
        self.counts(f'''
            import sys, unittest
            class Case(unittest.TestCase):
                def test_case(self):
                    self.assertEqual(sys.flags.optimize, {sys.flags.optimize})
        ''', "PASS", 1, 0, 0)


if __name__ == "__main__":
    unittest.main()
