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


def source_raw() -> bytes:
    return fixture.source_packet_bytes()


def scope_raw(source: bytes | None = None) -> bytes:
    return fixture.scope_bytes(source)


class SecurityRemediationScopeTests(unittest.TestCase):
    def test_golden_scope_verifies_exact_source_bytes(self):
        source = source_raw()
        report, markdown = scope.compile_bytes(scope_raw(source), source)
        self.assertEqual(report["scope_status"], "OWNER_REVIEW_READY")
        self.assertEqual(report["commercial"]["proposed_total_cents"], 1_750_000)
        self.assertTrue(report["source_packet"]["exact_bytes_verified"])
        self.assertEqual([item["id"] for item in report["work_items"]], ["F.ACCESS", "F.BACKUP"])
        self.assertEqual(report["excluded_findings"], [{"finding_id": "F.LOGGING", "reason": "SUPPORTED"}])
        self.assertIn("$17,500.00", markdown)

    def test_source_byte_tamper_fails_even_when_semantics_parse(self):
        source = source_raw()
        manifest = scope_raw(source)
        with self.assertRaises(scope.ScopeError):
            scope.compile_bytes(manifest, source + b"\n")

    def test_scope_cannot_override_source_finding_fields(self):
        obj = scope.loads_strict(scope_raw())
        obj["remediations"][0]["source_status"] = "SUPPORTED"
        with self.assertRaises(scope.ScopeError):
            scope.compile_bytes(scope.canonical_bytes(obj), source_raw())

    def test_supported_finding_cannot_be_monetized(self):
        obj = scope.loads_strict(scope_raw())
        extra = copy.deepcopy(obj["remediations"][0])
        extra["finding_id"] = "F.LOGGING"
        obj["remediations"].append(extra)
        with self.assertRaises(scope.ScopeError):
            scope.compile_bytes(scope.canonical_bytes(obj), source_raw())

    def test_unscoped_actionable_finding_holds_entire_scope(self):
        obj = scope.loads_strict(scope_raw())
        obj["remediations"] = [row for row in obj["remediations"] if row["finding_id"] != "F.BACKUP"]
        report, _ = scope.compile_bytes(scope.canonical_bytes(obj), source_raw())
        self.assertEqual(report["scope_status"], "HOLD_UNSCOPED_FINDINGS")
        self.assertEqual(report["unscoped_findings"][0]["finding_id"], "F.BACKUP")

    def test_prohibited_certification_and_compliance_outcomes_fail(self):
        for phrase in ["Certify the environment.", "Make it SOC 2 compliant.", "Guarantee compliance.", "Pass an audit."]:
            with self.subTest(phrase=phrase):
                obj = scope.loads_strict(scope_raw())
                obj["remediations"][0]["acceptance_test"] = phrase
                with self.assertRaises(scope.ScopeError):
                    scope.compile_bytes(scope.canonical_bytes(obj), source_raw())

    def test_strict_json_rejects_duplicates_floats_and_nonfinite(self):
        with self.assertRaises(scope.ScopeError):
            scope.loads_strict(b'{"x":1,"x":2}')
        with self.assertRaises(scope.ScopeError):
            scope.loads_strict(b'{"x":1.2}')
        with self.assertRaises(scope.ScopeError):
            scope.loads_strict(b'{"x":NaN}')

    def test_bool_price_is_not_integer_money(self):
        obj = scope.loads_strict(scope_raw())
        obj["remediations"][0]["owner_proposed_price_cents"] = True
        with self.assertRaises(scope.ScopeError):
            scope.compile_bytes(scope.canonical_bytes(obj), source_raw())

    def test_price_outside_fixed_scope_holds(self):
        obj = scope.loads_strict(scope_raw())
        for row in obj["remediations"]:
            row["owner_proposed_price_cents"] = 100_000
        report, _ = scope.compile_bytes(scope.canonical_bytes(obj), source_raw())
        self.assertEqual(report["scope_status"], "HOLD_PRICE_OUTSIDE_FIXED_SCOPE")
        self.assertEqual(report["commercial"]["commercial_state"], "PROPOSED_NOT_ACCEPTED")

    def test_scope_order_changes_raw_not_semantic_receipt(self):
        source = source_raw()
        raw_a = scope_raw(source)
        obj = scope.loads_strict(raw_a)
        obj["remediations"].reverse()
        raw_b = scope.canonical_bytes(obj)
        report_a, _ = scope.compile_bytes(raw_a, source)
        report_b, _ = scope.compile_bytes(raw_b, source)
        self.assertNotEqual(report_a["receipt"]["scope_raw_sha256"], report_b["receipt"]["scope_raw_sha256"])
        self.assertEqual(report_a["receipt"]["scope_semantic_sha256"], report_b["receipt"]["scope_semantic_sha256"])
        self.assertEqual(report_a["work_items"], report_b["work_items"])

    def test_report_tamper_breaks_verification(self):
        source = source_raw()
        raw = scope_raw(source)
        report, _ = scope.compile_bytes(raw, source)
        tampered = copy.deepcopy(report)
        tampered["commercial"]["proposed_total_cents"] += 1
        with self.assertRaises(scope.ScopeError):
            scope.verify_bytes(raw, source, scope.canonical_bytes(tampered))

    def test_future_source_packet_is_rejected(self):
        source_obj = scope.loads_strict(source_raw())
        source_obj["observed_at"] = "2026-09-17T00:00:00Z"
        source = fixture.canonical(source_obj)
        manifest_obj = fixture.build_scope_manifest(source)
        manifest_obj["source_packet"]["observed_at"] = source_obj["observed_at"]
        with self.assertRaises(scope.ScopeError):
            scope.compile_bytes(scope.canonical_bytes(manifest_obj), source)

    def test_source_status_requires_evidence_when_claiming_supported_partial_or_stale(self):
        source_obj = scope.loads_strict(source_raw())
        source_obj["findings"][0]["source_evidence_ids"] = []
        source = fixture.canonical(source_obj)
        manifest = fixture.build_scope_manifest(source)
        with self.assertRaises(scope.ScopeError):
            scope.compile_bytes(scope.canonical_bytes(manifest), source)

    def test_authority_is_hard_false_and_time_semantics_historical(self):
        source = source_raw()
        report, _ = scope.compile_bytes(scope_raw(source), source)
        self.assertTrue(all(value is False for value in report["authority"].values()))
        self.assertEqual(report["evidence_time_semantics"], "HISTORICAL_OWNER_REVIEW_ONLY")

    def test_cli_compile_verify_optimized_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            source_path = temp / "source.json"
            input_path = temp / "input.json"
            report_path = temp / "report.json"
            md_path = temp / "report.md"
            source = source_raw()
            source_path.write_bytes(source)
            input_path.write_bytes(scope_raw(source))
            common = ["--input", str(input_path), "--source-packet", str(source_path), "--report-json", str(report_path)]
            self.assertEqual(scope.cli(["compile", *common, "--report-md", str(md_path)]), 0)
            self.assertEqual(scope.cli(["verify", *common]), 0)
            proc = subprocess.run(
                [sys.executable, "-O", str(PRODUCT / "remediation_scope.py"), "verify", *common],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(scope.cli(["compile", *common, "--report-md", str(md_path)]), 2)


if __name__ == "__main__":
    unittest.main()
