#!/usr/bin/env python3
"""Tests for the assertion auditor.

Four of these are regression tests for false positives the auditor produced
against the live tree before it was corrected. That is deliberate: this tool
passes judgement on other people's tests, so every accusation it once made
wrongly is pinned down by a test that fails if it starts making it again.

Its first run reported 35 findings. Twelve accused a well-written hostile-case
suite of having no assertions; four called a determinism check a tautology; one
called a recorded rejection a swallowed failure. After correction: 18 findings,
all verified by hand against the source.
"""
import os
import shutil
import tempfile
import unittest

import audit_assertions as A


def write(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


class ScanCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="assert-audit-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def scan_test(self, body, name="test_thing.py"):
        p = os.path.join(self.root, name)
        write(p, body)
        return A.scan_test_file(p, name)

    def scan_source(self, body, name="thing.py"):
        p = os.path.join(self.root, name)
        write(p, body)
        return A.scan_source_file(p, name)

    def rules(self, findings):
        return sorted({f["rule"] for f in findings})


class TestNoAssertion(ScanCase):
    def test_a_test_with_no_assertion_is_caught(self):
        f = self.scan_test("""import unittest
class T(unittest.TestCase):
    def test_does_nothing(self):
        value = 1 + 1
""")
        self.assertEqual(self.rules(f), ["NO_ASSERTION"])
        self.assertEqual(f[0]["test"], "test_does_nothing")

    def test_a_normal_assertion_is_clean(self):
        self.assertEqual(self.scan_test("""import unittest
class T(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(1, 2)
"""), [])

    def test_assertraises_context_manager_counts(self):
        self.assertEqual(self.scan_test("""import unittest
class T(unittest.TestCase):
    def test_raises(self):
        with self.assertRaises(ValueError):
            int("x")
"""), [])


class TestFalsePositivesItOnceProduced(ScanCase):
    def test_a_test_that_delegates_to_an_asserting_helper_is_clean(self):
        # Twelve tests in uiowa_rfq_18649_report_visuals were accused of having
        # no assertion. Every one delegates to a helper that does
        # assertRaises + assertIn. The tests were correct; the analyzer was
        # only looking inside the test body.
        self.assertEqual(self.scan_test("""import unittest
class T(unittest.TestCase):
    def _expect_error(self, mutate, fragment):
        with self.assertRaises(ValueError) as ctx:
            mutate()
        self.assertIn(fragment, str(ctx.exception))

    def test_blank_is_refused(self):
        self._expect_error(lambda: int(""), "invalid literal")
"""), [])

    def test_a_helper_chain_two_deep_is_followed(self):
        self.assertEqual(self.scan_test("""import unittest
class T(unittest.TestCase):
    def _inner(self, v):
        self.assertTrue(v)

    def _outer(self, v):
        self._inner(v)

    def test_delegates_twice(self):
        self._outer(True)
"""), [])

    def test_a_helper_that_asserts_nothing_is_still_caught(self):
        f = self.scan_test("""import unittest
class T(unittest.TestCase):
    def _record(self, v):
        self.seen = v

    def test_delegates_to_nothing(self):
        self._record(1)
""")
        self.assertEqual(self.rules(f), ["NO_ASSERTION"])

    def test_recursive_helpers_do_not_hang(self):
        f = self.scan_test("""import unittest
class T(unittest.TestCase):
    def _a(self):
        self._b()

    def _b(self):
        self._a()

    def test_mutual(self):
        self._a()
""")
        self.assertEqual(self.rules(f), ["NO_ASSERTION"])

    def test_comparing_two_calls_is_a_determinism_check_not_a_tautology(self):
        # assertEqual(f(x), f(x)) EVALUATES f twice. That is exactly how you
        # test determinism, and flagging it was the auditor's own error.
        self.assertEqual(self.scan_test("""import unittest
def digest(x):
    return x

class T(unittest.TestCase):
    def test_is_deterministic(self):
        self.assertEqual(digest("a"), digest("a"))
"""), [])

    def test_a_handler_that_records_the_failure_is_not_swallowing(self):
        # uiowa_rfq_18649_ai_integration catches ValueError, records
        # "REJECTED", and asserts on that record afterwards.
        self.assertEqual(self.scan_test("""import unittest
class T(unittest.TestCase):
    def test_rejection_path(self):
        scores = {}
        for w in ("good", "bad"):
            try:
                scores[w] = score(w)
            except ValueError:
                scores[w] = "REJECTED"
                continue
        self.assertEqual(scores["bad"], "REJECTED")
"""), [])

    def test_a_lone_raise_does_not_excuse_a_module_of_bare_asserts(self):
        # The first cut used "has any raise" and let a smoke script whose 15 of
        # 16 checks are bare asserts fall into the advisory bucket. Its only
        # raise was `raise SystemExit(main())` -- an entrypoint, not a check.
        f = self.scan_source("""import sys
def main():
    assert 1 == 1
    assert 2 == 2
    assert 3 == 3
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
""")
        self.assertEqual(self.rules(f), ["ASSERT_IS_THE_CHECK"])


class TestTautology(ScanCase):
    def test_constant_assertions_are_caught(self):
        f = self.scan_test("""import unittest
class T(unittest.TestCase):
    def test_vacuous(self):
        self.assertTrue(True)
        self.assertEqual(1, 1)
        self.assertIsNotNone("x")
""")
        self.assertEqual(self.rules(f), ["TAUTOLOGY"])
        self.assertEqual(len(f), 3)

    def test_call_free_self_comparison_is_caught(self):
        f = self.scan_test("""import unittest
class T(unittest.TestCase):
    def test_self_compare(self):
        value = compute()
        self.assertEqual(value, value)
""")
        self.assertEqual(self.rules(f), ["TAUTOLOGY"])

    def test_a_real_comparison_is_clean(self):
        self.assertEqual(self.scan_test("""import unittest
class T(unittest.TestCase):
    def test_real(self):
        self.assertEqual(compute(), 4)
"""), [])


class TestSwallowed(ScanCase):
    def test_except_pass_is_caught(self):
        f = self.scan_test("""import unittest
class T(unittest.TestCase):
    def test_swallows(self):
        try:
            self.assertEqual(1, 2)
        except AssertionError:
            pass
""")
        self.assertIn("SWALLOWED", self.rules(f))

    def test_a_reraising_handler_is_clean(self):
        self.assertEqual(self.scan_test("""import unittest
class T(unittest.TestCase):
    def test_reraises(self):
        try:
            self.assertEqual(1, 2)
        except AssertionError:
            raise
"""), [])


class TestSourceAsserts(ScanCase):
    def test_a_module_verifying_with_bare_asserts(self):
        f = self.scan_source("""def check(page):
    assert page.a == 1
    assert page.b == 2
    assert page.c == 3
""")
        self.assertEqual(self.rules(f), ["ASSERT_IS_THE_CHECK"])
        self.assertEqual(len(f), 3)

    def test_a_single_internal_invariant_is_advisory(self):
        f = self.scan_source("""CODES = ("A", "B")
class Issue:
    def __init__(self, code):
        assert code in CODES, code
        self.code = code
""")
        self.assertEqual(self.rules(f), ["ASSERT_INTERNAL_INVARIANT"])

    def test_a_module_with_no_asserts_is_clean(self):
        self.assertEqual(self.scan_source("def f():\n    return 1\n"), [])

    def test_a_unittest_module_is_not_judged_as_source(self):
        f = self.scan_source("""import unittest
assert 1 == 1
assert 2 == 2
assert 3 == 3
""", name="helper.py")
        self.assertEqual(self.rules(f), ["ASSERT_INTERNAL_INVARIANT"])


class TestRobustness(ScanCase):
    def test_a_syntactically_broken_test_file_is_reported_not_raised(self):
        f = self.scan_test("def test_oops(:\n")
        self.assertEqual(self.rules(f), ["UNPARSEABLE"])

    def test_a_broken_source_file_is_skipped_quietly(self):
        self.assertEqual(self.scan_source("def f(:\n"), [])

    def test_lane_audit_counts_test_files(self):
        lane = os.path.join(self.root, "uiowa_rfq_18649_demo")
        write(os.path.join(lane, "test_a.py"), "import unittest\n")
        write(os.path.join(lane, "mod.py"), "def f():\n    return 1\n")
        r = A.audit_lane(lane)
        self.assertEqual(r["test_files"], 1)
        self.assertEqual(r["findings"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
