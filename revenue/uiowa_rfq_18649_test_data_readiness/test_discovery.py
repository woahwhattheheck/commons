"""Regression checks for collecting the retained UIOWA-047 behavioral suite.

This file stays at the component root so a missing tests package marker cannot
silently hide both the behavioral tests and the test that checks discovery.
Discovery happens in a fresh interpreter; collected suites are not executed
there, so discovering this module cannot recursively execute these checks.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
BEHAVIORAL_CASES = frozenset({
    "test_catalog_has_three_service_examples",
    "test_clean_ess_fixture_is_fully_evidenced",
    "test_iam_missing_evidence_stays_unknown",
    "test_interface_alignment_can_be_evidenced_despite_other_unknowns",
    "test_invalid_as_of_fails_closed",
    "test_markdown_explains_unknown_boundary",
    "test_ris_exposes_staleness_interface_drift_and_missing_cases",
})
DISCOVER = """
import json
import sys
import unittest

def case_ids(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from case_ids(item)
        else:
            yield item.id()

loader = unittest.TestLoader()
suite = loader.discover(sys.argv[1], pattern='test*.py')
print(json.dumps({'ids': list(case_ids(suite)), 'errors': loader.errors}))
"""


class DiscoveryTests(unittest.TestCase):
    def discover(self, root: Path, start: str = ".", optimized: bool = False) -> list[str]:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-B", "-c", DISCOVER, start])
        result = subprocess.run(
            command, cwd=root, capture_output=True, text=True, timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["errors"], [], report["errors"])
        return report["ids"]

    def assert_behavioral_cases(self, ids: list[str]) -> None:
        prefix = ".TestDataReadinessTests."
        found = [case.split(prefix, 1)[1] for case in ids if prefix in case]
        self.assertTrue(BEHAVIORAL_CASES.issubset(set(found)),
                        f"Behavioral suite missing cases: {sorted(BEHAVIORAL_CASES - set(found))}")
        self.assertEqual(len(found), len(set(found)),
                         "Behavioral cases must be collected exactly once")

    def test_root_discovery_collects_behavioral_cases(self):
        self.assert_behavioral_cases(self.discover(ROOT))

    def test_optimized_root_discovery_collects_behavioral_cases(self):
        self.assert_behavioral_cases(self.discover(ROOT, optimized=True))

    def test_explicit_tests_directory_collects_behavioral_cases(self):
        self.assert_behavioral_cases(self.discover(ROOT, start="tests"))

    def test_missing_behavioral_suite_is_detected(self):
        # Delete only from an isolated copy; never mutate the inspected source.
        with tempfile.TemporaryDirectory(prefix="uiowa047-discovery-") as tmp:
            copy = Path(tmp) / "lane"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__"))
            (copy / "tests" / "test_assessor.py").unlink()
            with self.assertRaisesRegex(AssertionError, "Behavioral suite missing"):
                self.assert_behavioral_cases(self.discover(copy))


if __name__ == "__main__":
    unittest.main()
