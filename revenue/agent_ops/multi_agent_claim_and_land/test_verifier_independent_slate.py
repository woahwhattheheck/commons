"""Independent regression controls for lane-verifier observations.

All generated lanes are fictional and run only in disposable directories.
Default target: sibling verify_lanes.py. Override VERIFIER_PATH to test an
explicit published revision without copying or changing that source.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import textwrap
import unittest

TARGET = Path(os.environ.get("VERIFIER_PATH", Path(__file__).with_name("verify_lanes.py"))).resolve()
SPEC = importlib.util.spec_from_file_location("slate_observed_verifier", TARGET)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load verifier: {TARGET}")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class IndependentObservationTests(unittest.TestCase):
    def observe(self, source: str, runner: str = "auto") -> dict:
        with tempfile.TemporaryDirectory(prefix="slate-observation-") as directory:
            root = Path(directory)
            (root / "test_fixture.py").write_text(textwrap.dedent(source), encoding="utf-8")
            return VERIFIER.run_tests(root, 10, runner)

    def repeated(self, count: int, method: str) -> dict:
        source = (
            "import unittest\n"
            "class Case(unittest.TestCase):\n"
            "    def test_case(self):\n"
            + textwrap.indent(textwrap.dedent(method).strip(), "        ")
            + "\ndef load_tests(loader, tests, pattern):\n"
            "    same = Case('test_case')\n"
            f"    return unittest.TestSuite([same] * {count})\n"
        )
        return self.observe(source)

    def test_reused_case_all_skipped_twice_is_never_pass(self):
        row = self.repeated(2, "self.skipTest('synthetic skip')")
        self.assertEqual((row["status"], row["tests"], row["tests_executed"], row["tests_skipped"]),
                         ("SKIPPED", 2, 0, 2))
        self.assertEqual(row["files"][0]["other_skip_events"], 0)

    def test_reused_case_all_skipped_five_times_counts_invocations(self):
        row = self.repeated(5, "self.skipTest('synthetic skip')")
        self.assertEqual((row["status"], row["tests_executed"], row["tests_skipped"], row["skip_events"]),
                         ("SKIPPED", 0, 5, 5))

    def test_reused_case_skip_pass_skip_counts_one_execution(self):
        row = self.repeated(3, """
            self.calls = getattr(self, 'calls', 0) + 1
            if self.calls != 2:
                self.skipTest('synthetic skip')
            self.assertEqual(self.calls, 2)
        """)
        self.assertEqual((row["status"], row["tests"], row["tests_executed"], row["tests_skipped"]),
                         ("PASS", 3, 1, 2))

    def test_reused_case_two_real_executions_still_pass(self):
        row = self.repeated(2, "self.assertEqual(2 + 2, 4)")
        self.assertEqual((row["status"], row["tests_executed"], row["tests_skipped"]), ("PASS", 2, 0))

    def test_reused_case_subtest_skips_do_not_erase_real_invocations(self):
        row = self.repeated(2, """
            with self.subTest(sample='synthetic'):
                self.skipTest('subtest only')
            self.assertEqual(2 + 2, 4)
        """)
        self.assertEqual((row["status"], row["tests_executed"], row["tests_skipped"], row["skip_events"]),
                         ("PASS", 2, 0, 2))

    def test_class_setup_skip_starts_no_test_cases(self):
        row = self.observe("""
            import unittest
            class Case(unittest.TestCase):
                @classmethod
                def setUpClass(cls):
                    raise unittest.SkipTest('synthetic class skip')
                def test_one(self): self.fail('must not run')
                def test_two(self): self.fail('must not run')
        """)
        self.assertEqual((row["status"], row["tests"], row["tests_executed"], row["skip_events"]),
                         ("SKIPPED", 0, 0, 1))

    def test_module_setup_skip_starts_no_test_cases(self):
        row = self.observe("""
            import unittest
            def setUpModule():
                raise unittest.SkipTest('synthetic module skip')
            class Case(unittest.TestCase):
                def test_one(self): self.fail('must not run')
        """)
        self.assertEqual((row["status"], row["tests"], row["tests_executed"], row["skip_events"]),
                         ("SKIPPED", 0, 0, 1))

    def test_module_setup_error_is_failure_even_with_zero_cases_started(self):
        row = self.observe("""
            import unittest
            def setUpModule():
                raise RuntimeError('intentional synthetic setup failure')
            class Case(unittest.TestCase):
                def test_one(self): self.assertTrue(True)
        """)
        self.assertEqual((row["status"], row["tests_executed"]), ("FAIL", 0))
        self.assertEqual(row["files"][0]["errors"], 1)

    def test_script_skip_summary_with_ordinary_ok_print_is_unverified(self):
        row = self.observe("""
            import unittest
            print('OK')
            class Case(unittest.TestCase):
                @unittest.skip('synthetic skip')
                def test_one(self): self.fail('must not run')
            if __name__ == '__main__': unittest.main()
        """, runner="script")
        self.assertEqual((row["status"], row["tests_executed"]), ("UNVERIFIED", 0))

    def test_script_clean_real_summary_still_passes(self):
        row = self.observe("""
            import unittest
            class Case(unittest.TestCase):
                def test_one(self): self.assertEqual(2 + 2, 4)
            if __name__ == '__main__': unittest.main()
        """, runner="script")
        self.assertEqual((row["status"], row["tests_executed"]), ("PASS", 1))

    def test_script_failure_with_ordinary_ok_print_remains_failure(self):
        row = self.observe("""
            import unittest
            print('OK')
            class Case(unittest.TestCase):
                def test_one(self): self.fail('intentional synthetic failure')
            if __name__ == '__main__': unittest.main()
        """, runner="script")
        self.assertEqual(row["status"], "FAIL")

    def test_script_conflicting_summaries_are_not_disambiguated_by_ok(self):
        row = VERIFIER._script_observation("Ran 2 tests in 0.01s\nOK (skipped=2)\nOK\n", 0)
        self.assertEqual((row["status"], row["tests_executed"]), ("UNVERIFIED", 0))

    def test_script_two_run_summaries_are_unverified(self):
        row = VERIFIER._script_observation("Ran 1 test in 0.01s\nOK\nRan 2 tests in 0.01s\nOK\n", 0)
        self.assertEqual((row["status"], row["tests_executed"]), ("UNVERIFIED", 0))

    def test_alias_testcase_without_main_guard_really_runs(self):
        row = self.observe("""
            from unittest import TestCase as Alias
            class Base(Alias): pass
            class Case(Base):
                def test_one(self): self.assertEqual(2 + 2, 4)
        """)
        self.assertEqual((row["status"], row["tests_executed"]), ("PASS", 1))


if __name__ == "__main__":
    unittest.main()
