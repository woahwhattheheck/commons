from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "revenue" / "security_remediation_scope"
if str(PRODUCT) not in sys.path:
    sys.path.insert(0, str(PRODUCT))

import remediation_scope as scope  # noqa: E402
import synthetic_fixture as fixture  # noqa: E402


def raw_fixture() -> bytes:
    return fixture.fixture_bytes()


class SecurityRemediationScopeTests(unittest.TestCase):
    def test_golden_scope_is_owner_review_ready(self):
        report, markdown = scope.compile_bytes(raw_fixture())
        self.assertEqual(report["scope_status"], "OWNER_REVIEW_READY")
        self.assertEqual(report["commercial"]["proposed_total_cents"], 1_750_000)
        self.assertEqual([item["finding_id"] for item in report["work_items"]], ["F.ACCESS", "F.BACKUP"])
        self.assertEqual(report["excluded_findings"], [{"finding_id": "F.LOGGING", "reason": "SUPPORTED"}])
        self.assertIn("$17,500.00", markdown)

    def test_supported_and_not_applicable_cannot_be_monetized(self):
        obj = scope.loads_strict(raw_fixture())
        supported = next(row for row in obj["findings"] if row["id"] == "F.LOGGING")
        supported["remediation"] = copy.deepcopy(obj["findings"][0]["remediation"])
        with self.assertRaises(scope.ScopeError):
            scope.compile_bytes(scope.canonical_bytes(obj))
        supported["source_status"] = "NOT_APPLICABLE"
        with self.assertRaises(scope.ScopeError):
            scope.compile_bytes(scope.canonical_bytes(obj))

    def test_actionable_finding_requires_remediation_object(self):
        obj = scope.loads_strict(raw_fixture())
        obj["findings"][0]["remediation"] = None
        with self.assertRaises(scope.ScopeError):
            scope.compile_bytes(scope.canonical_bytes(obj))

    def test_prohibited_certification_and_compliance_outcomes_fail(self):
        phrases = [
            "Certify the environment for the buyer.",
            "Make the service SOC 2 compliant.",
            "Guarantee compliance with the policy.",
            "Pass an audit for the reviewed system.",
        ]
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                obj = scope.loads_strict(raw_fixture())
                obj["findings"][0]["remediation"]["acceptance_test"] = phrase
                with self.assertRaises(scope.ScopeError):
                    scope.compile_bytes(scope.canonical_bytes(obj))

    def test_strict_json_rejects_duplicates_floats_and_nonfinite(self):
        with self.assertRaises(scope.ScopeError):
            scope.loads_strict(b'{"x":1,"x":2}')
        with self.assertRaises(scope.ScopeError):
            scope.loads_strict(b'{"x":1.2}')
        with self.assertRaises(scope.ScopeError):
            scope.loads_strict(b'{"x":NaN}')

    def test_bool_price_is_not_integer_money(self):
        obj = scope.loads_strict(raw_fixture())
        obj["findings"][0]["remediation"]["owner_proposed_price_cents"] = True
        with self.assertRaises(scope.ScopeError):
            scope.compile_bytes(scope.canonical_bytes(obj))

    def test_price_outside_fixed_scope_holds_without_inventing_acceptance(self):
        obj = scope.loads_strict(raw_fixture())
        obj["findings"][0]["remediation"]["owner_proposed_price_cents"] = 100_000
        obj["findings"][1]["remediation"]["owner_proposed_price_cents"] = 100_000
        report, _ = scope.compile_bytes(scope.canonical_bytes(obj))
        self.assertEqual(report["scope_status"], "HOLD_PRICE_OUTSIDE_FIXED_SCOPE")
        self.assertEqual(report["commercial"]["commercial_state"], "PROPOSED_NOT_ACCEPTED")

    def test_input_order_changes_raw_receipt_not_semantic_receipt(self):
        raw_a = raw_fixture()
        obj = scope.loads_strict(raw_a)
        obj["findings"].reverse()
        obj["findings"][0]["source_evidence_ids"].reverse()
        raw_b = scope.canonical_bytes(obj)
        report_a, _ = scope.compile_bytes(raw_a)
        report_b, _ = scope.compile_bytes(raw_b)
        self.assertNotEqual(report_a["receipt"]["raw_input_sha256"], report_b["receipt"]["raw_input_sha256"])
        self.assertEqual(report_a["receipt"]["semantic_manifest_sha256"], report_b["receipt"]["semantic_manifest_sha256"])
        self.assertEqual(report_a["work_items"], report_b["work_items"])

    def test_report_tamper_breaks_verification(self):
        raw = raw_fixture()
        report, _ = scope.compile_bytes(raw)
        tampered = copy.deepcopy(report)
        tampered["commercial"]["proposed_total_cents"] += 1
        with self.assertRaises(scope.ScopeError):
            scope.verify_bytes(raw, scope.canonical_bytes(tampered))

    def test_future_source_packet_is_rejected(self):
        obj = scope.loads_strict(raw_fixture())
        obj["source_packet"]["observed_at"] = "2026-09-17T00:00:00Z"
        with self.assertRaises(scope.ScopeError):
            scope.compile_bytes(scope.canonical_bytes(obj))

    def test_authority_is_hard_false_and_time_semantics_are_historical(self):
        report, _ = scope.compile_bytes(raw_fixture())
        self.assertTrue(report["authority"])
        self.assertTrue(all(value is False for value in report["authority"].values()))
        self.assertEqual(report["evidence_time_semantics"], "HISTORICAL_OWNER_REVIEW_ONLY")

    def test_no_actionable_findings_do_not_create_fake_work(self):
        obj = scope.loads_strict(raw_fixture())
        obj["findings"] = [row for row in obj["findings"] if row["source_status"] == "SUPPORTED"]
        report, _ = scope.compile_bytes(scope.canonical_bytes(obj))
        self.assertEqual(report["scope_status"], "NO_ACTIONABLE_FINDINGS")
        self.assertEqual(report["commercial"]["proposed_total_cents"], 0)
        self.assertEqual(report["work_items"], [])

    def test_cli_compile_verify_optimized_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            input_path = temp / "input.json"
            report_path = temp / "report.json"
            md_path = temp / "report.md"
            input_path.write_bytes(raw_fixture())
            self.assertEqual(scope.cli(["compile", "--input", str(input_path), "--report-json", str(report_path), "--report-md", str(md_path)]), 0)
            self.assertEqual(scope.cli(["verify", "--input", str(input_path), "--report-json", str(report_path)]), 0)
            proc = subprocess.run(
                [sys.executable, "-O", str(PRODUCT / "remediation_scope.py"), "verify", "--input", str(input_path), "--report-json", str(report_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(scope.cli(["compile", "--input", str(input_path), "--report-json", str(report_path), "--report-md", str(md_path)]), 2)


if __name__ == "__main__":
    unittest.main()
