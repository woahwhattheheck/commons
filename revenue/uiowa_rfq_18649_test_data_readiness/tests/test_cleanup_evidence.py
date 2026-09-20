"""Cleanup evidence must distinguish an explicit false flag from no declaration."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "uiowa047_cleanup_assessor", ROOT / "test_data_assessor.py"
)
if SPEC is None or SPEC.loader is None:
    raise ImportError("Cannot load the retained UIOWA-047 assessor")
assessor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assessor)


class CleanupEvidenceTests(unittest.TestCase):
    def payload(self, **fields):
        return {
            "as_of": "2026-09-19",
            "datasets": [{
                "dataset_id": "SYN-CLEANUP-DECLARATION",
                "service": "ESS",
                "purpose": "Fictional cleanup evidence boundary",
                **fields,
            }],
        }

    def cleanup(self, **fields):
        report = assessor.evaluate_catalog(self.payload(**fields))
        return next(check for check in report["datasets"][0]["checks"]
                    if check["check_id"] == "cleanup")

    def assert_unknown(self, **fields):
        check = self.cleanup(**fields)
        self.assertEqual(check["state"], assessor.UNKNOWN)
        self.assertNotEqual(check["state"], assessor.OBSERVED_GAP)
        self.assertTrue(check["follow_up"].strip())
        self.assertNotIn("marks cleanup as not required", check["detail"])

    def test_absent_declaration_is_unknown(self):
        self.assert_unknown()

    def test_verification_does_not_supply_absent_declaration(self):
        self.assert_unknown(cleanup_last_verified="2026-09-18")

    def test_null_declaration_is_unknown(self):
        self.assert_unknown(cleanup_required=None)

    def test_verification_does_not_supply_null_declaration(self):
        self.assert_unknown(cleanup_required=None,
                            cleanup_last_verified="2026-09-18")

    def test_non_boolean_declarations_are_unknown(self):
        for value in (0, 1, 0.0, 1.0, "", "false", "true", [], {}, [True], {"value": False}):
            with self.subTest(value=value):
                self.assert_unknown(cleanup_required=value)

    def test_verification_does_not_coerce_non_boolean_declaration(self):
        for value in (0, 1, "false", "true", [], {"value": True}):
            with self.subTest(value=value):
                self.assert_unknown(cleanup_required=value,
                                    cleanup_last_verified="2026-09-18")

    def test_explicit_false_retains_not_required_evidence(self):
        check = self.cleanup(cleanup_required=False)
        self.assertEqual(check["state"], assessor.EVIDENCED)
        self.assertEqual(check["detail"],
                         "Catalog marks cleanup as not required for this fixture.")
        self.assertEqual(check["follow_up"], "")

    def test_explicit_false_needs_no_verification_date(self):
        check = self.cleanup(cleanup_required=False,
                             cleanup_last_verified="not-a-date")
        self.assertEqual(check["state"], assessor.EVIDENCED)

    def test_explicit_true_without_verification_stays_unknown(self):
        self.assert_unknown(cleanup_required=True)

    def test_explicit_true_with_invalid_verification_stays_unknown(self):
        self.assert_unknown(cleanup_required=True,
                            cleanup_last_verified="not-a-date")

    def test_explicit_true_with_recorded_verification_stays_evidenced(self):
        check = self.cleanup(cleanup_required=True,
                             cleanup_last_verified="2026-09-18")
        self.assertEqual(check["state"], assessor.EVIDENCED)
        self.assertIn("2026-09-18", check["detail"])

    def test_omitted_evidence_is_not_counted_as_a_pass_or_a_defect(self):
        report = assessor.evaluate_catalog(self.payload())
        self.assertEqual(report["summary"], {
            assessor.EVIDENCED: 0, assessor.OBSERVED_GAP: 0, assessor.UNKNOWN: 7,
        })
        self.assertEqual(sum(report["summary"].values()), 7)

    def test_evaluation_preserves_supplied_record(self):
        payload = self.payload(cleanup_last_verified="2026-09-18")
        original = deepcopy(payload)
        assessor.evaluate_catalog(payload)
        self.assertEqual(payload, original)
        self.assertNotIn("cleanup_required", payload["datasets"][0])

    def test_json_and_markdown_cli_preserve_the_unknown(self):
        with tempfile.TemporaryDirectory(prefix="uiowa047-cleanup-cli-") as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text(json.dumps(self.payload()), encoding="utf-8")
            original = path.read_bytes()
            for output_format in ("json", "markdown"):
                with self.subTest(output_format=output_format):
                    command = [sys.executable]
                    if sys.flags.optimize:
                        command.append("-O")
                    command.extend(["-B", str(ROOT / "test_data_assessor.py"),
                                    str(path), "--format", output_format])
                    result = subprocess.run(command, capture_output=True,
                                            text=True, timeout=20, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    if output_format == "json":
                        report = json.loads(result.stdout)
                        cleanup = next(c for c in report["datasets"][0]["checks"]
                                       if c["check_id"] == "cleanup")
                        self.assertEqual(cleanup["state"], assessor.UNKNOWN)
                        self.assertEqual(report["summary"][assessor.EVIDENCED], 0)
                    else:
                        self.assertIn("| cleanup | UNKNOWN |", result.stdout)
                        self.assertNotIn("marks cleanup as not required", result.stdout)
                    self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
