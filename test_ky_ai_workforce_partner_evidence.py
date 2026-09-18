from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from revenue.ky_ai_workforce_partner_evidence.cli import main
from revenue.ky_ai_workforce_partner_evidence.io import load_json_object
from revenue.ky_ai_workforce_partner_evidence.model import EvidenceError
from revenue.ky_ai_workforce_partner_evidence.validate import evaluate_bundle


def receipt(source: str, kind: str) -> dict[str, str]:
    return {
        "source_id": source,
        "sha256": hashlib.sha256(source.encode()).hexdigest(),
        "captured_at": "2026-09-13T09:00:00Z",
        "kind": kind,
    }


def ready_bundle() -> dict:
    legal = "Experienced Workforce Partner"
    refs = [
        {
            "client_label": f"Client {idx}",
            "work_summary": "Comparable adult workforce training",
            "completed_on": f"202{idx + 2}-06-15",
            "attributable_party": legal,
            "permission_status": "confirmed",
            "contact_id": f"ref-contact-{idx}",
            "evidence": receipt(f"ref-{idx}", "reference_confirmation"),
        }
        for idx in range(3)
    ]
    instructors = [
        {
            "name": "Instructor A",
            "scopes": ["manufacturing", "construction", "logistics"],
            "modes": ["live_remote", "in_person"],
            "availability_status": "confirmed",
            "evidence": receipt("instructor-a", "resume"),
        },
        {
            "name": "Instructor B",
            "scopes": ["healthcare", "business_operations", "career_readiness"],
            "modes": ["live_remote", "in_person"],
            "availability_status": "confirmed",
            "evidence": receipt("instructor-b", "resume"),
        },
    ]
    op_kinds = {
        "kentucky_in_person_dispatch": "travel_plan",
        "live_remote_delivery": "capability_statement",
        "curriculum_rights": "curriculum",
        "accessibility_plan": "accessibility_plan",
        "records_reporting_plan": "records_plan",
        "data_security_plan": "data_security_plan",
        "insurance_registration": "insurance",
        "pricing_model": "pricing",
        "travel_model": "travel_plan",
    }
    return {
        "opportunity_id": "R-C08-KY-AI-WORKFORCE-2026",
        "evaluated_on": "2026-09-13",
        "partner": {
            "legal_name": legal,
            "role": "prime",
            "commitment_status": "confirmed",
            "commitment_evidence": receipt("commitment", "signed_letter"),
            "relevant_experience_years": 15,
            "experience_evidence": receipt("experience", "capability_statement"),
        },
        "references": refs,
        "instructors": instructors,
        "operations": {
            name: {"status": "confirmed", "evidence": receipt(name, kind)}
            for name, kind in op_kinds.items()
        },
    }


class PartnerEvidenceTests(unittest.TestCase):
    def test_ready_bundle_qualifies_without_granting_external_authority(self):
        report = evaluate_bundle(ready_bundle())
        self.assertEqual(report["decision"], "QUALIFIED_TEAMING")
        self.assertTrue(all(gate["status"] == "PASS" for gate in report["gates"]))
        self.assertFalse(report["authority"]["proposal_authorized"])
        self.assertFalse(report["authority"]["proposal_submitted"])
        self.assertFalse(report["authority"]["contract_awarded"])
        self.assertFalse(report["authority"]["recognized_revenue"])
        self.assertEqual(report["evidence_receipt_count"], 16)

    def test_pending_partner_commitment_holds(self):
        bundle = ready_bundle()
        bundle["partner"]["commitment_status"] = "pending"
        report = evaluate_bundle(bundle)
        self.assertEqual(report["decision"], "HOLD_PARTNER_EVIDENCE")
        gate = next(item for item in report["gates"] if item["gate"] == "partner_commitment")
        self.assertEqual(gate["status"], "HOLD")

    def test_reference_must_be_recent_confirmed_and_attributable(self):
        bundle = ready_bundle()
        bundle["references"][0]["completed_on"] = "2019-01-01"
        bundle["references"][1]["permission_status"] = "pending"
        bundle["references"][2]["attributable_party"] = "Someone Else"
        report = evaluate_bundle(bundle)
        gate = next(item for item in report["gates"] if item["gate"] == "comparable_references")
        self.assertEqual(gate["status"], "HOLD")
        self.assertIn("0 attributable", gate["detail"])

    def test_modality_gap_holds_even_when_scopes_exist(self):
        bundle = ready_bundle()
        bundle["instructors"][1]["modes"] = ["live_remote"]
        report = evaluate_bundle(bundle)
        gate = next(item for item in report["gates"] if item["gate"] == "instructor_scope_and_modality")
        self.assertEqual(gate["status"], "HOLD")
        self.assertIn("healthcare", gate["detail"])

    def test_unavailable_operation_holds(self):
        bundle = ready_bundle()
        bundle["operations"]["kentucky_in_person_dispatch"]["status"] = "unavailable"
        report = evaluate_bundle(bundle)
        self.assertEqual(report["decision"], "HOLD_PARTNER_EVIDENCE")
        gate = next(item for item in report["gates"] if item["gate"] == "kentucky_in_person_dispatch")
        self.assertEqual(gate["status"], "HOLD")

    def test_boolean_years_rejected(self):
        bundle = ready_bundle()
        bundle["partner"]["relevant_experience_years"] = True
        with self.assertRaises(EvidenceError):
            evaluate_bundle(bundle)

    def test_receipt_digest_must_be_exact_sha256(self):
        bundle = ready_bundle()
        bundle["partner"]["experience_evidence"]["sha256"] = "abc"
        with self.assertRaises(EvidenceError):
            evaluate_bundle(bundle)

    def test_receipt_timestamp_requires_timezone(self):
        bundle = ready_bundle()
        bundle["partner"]["experience_evidence"]["captured_at"] = "2026-09-13T09:00:00"
        with self.assertRaises(EvidenceError):
            evaluate_bundle(bundle)

    def test_unknown_fields_fail_closed(self):
        bundle = ready_bundle()
        bundle["partner"]["invented"] = "claim"
        with self.assertRaises(EvidenceError):
            evaluate_bundle(bundle)

    def test_report_is_deterministic(self):
        bundle = ready_bundle()
        first = evaluate_bundle(bundle, input_sha256="1" * 64)
        second = evaluate_bundle(json.loads(json.dumps(bundle)), input_sha256="1" * 64)
        self.assertEqual(first, second)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bundle.json"
            path.write_text('{"opportunity_id":"a","opportunity_id":"b"}', encoding="utf-8")
            with self.assertRaises(EvidenceError):
                load_json_object(path)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unsupported")
    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target.json"
            target.write_text(json.dumps(ready_bundle()), encoding="utf-8")
            alias = root / "alias.json"
            try:
                alias.symlink_to(target)
            except OSError:
                self.skipTest("symlink unavailable")
            with self.assertRaises(EvidenceError):
                load_json_object(alias)

    def test_cli_holds_with_exit_2_and_atomic_output(self):
        bundle = ready_bundle()
        bundle["operations"]["pricing_model"]["status"] = "pending"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_path = root / "in.json"
            output_path = root / "out.json"
            input_path.write_text(json.dumps(bundle), encoding="utf-8")
            self.assertEqual(main([str(input_path), "--output", str(output_path)]), 2)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["decision"], "HOLD_PARTNER_EVIDENCE")
            self.assertEqual(report["input_sha256"], hashlib.sha256(input_path.read_bytes()).hexdigest())

    def test_cli_rejects_hardlink_alias(self):
        if not hasattr(os, "link"):
            self.skipTest("hardlinks unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_path = root / "in.json"
            input_path.write_text(json.dumps(ready_bundle()), encoding="utf-8")
            output_path = root / "same.json"
            try:
                os.link(input_path, output_path)
            except OSError:
                self.skipTest("hardlinks unavailable")
            self.assertEqual(main([str(input_path), "--output", str(output_path)]), 3)

    def test_evidence_kind_is_bound_to_gate(self):
        bundle = ready_bundle()
        bundle["operations"]["pricing_model"]["evidence"]["kind"] = "insurance"
        with self.assertRaises(EvidenceError):
            evaluate_bundle(bundle)

    def test_hold_report_lists_missing_gates(self):
        bundle = ready_bundle()
        bundle["partner"]["commitment_status"] = "pending"
        bundle["operations"]["pricing_model"]["status"] = "pending"
        report = evaluate_bundle(bundle)
        self.assertEqual(
            report["missing_gates"],
            ["partner_commitment", "pricing_model"],
        )

    def test_five_year_window_is_leap_day_safe(self):
        bundle = ready_bundle()
        bundle["evaluated_on"] = "2024-02-29"
        bundle["references"][0]["completed_on"] = "2019-02-28"
        bundle["references"][1]["completed_on"] = "2020-01-01"
        bundle["references"][2]["completed_on"] = "2021-01-01"
        report = evaluate_bundle(bundle)
        gate = next(item for item in report["gates"] if item["gate"] == "comparable_references")
        self.assertEqual(gate["status"], "PASS")

    def test_nonfinite_experience_rejected(self):
        bundle = ready_bundle()
        bundle["partner"]["relevant_experience_years"] = float("inf")
        with self.assertRaises(EvidenceError):
            evaluate_bundle(bundle)

    def test_future_reference_rejected(self):
        bundle = ready_bundle()
        bundle["references"][0]["completed_on"] = "2027-01-01"
        with self.assertRaises(EvidenceError):
            evaluate_bundle(bundle)

    def test_duplicate_reference_contact_rejected(self):
        bundle = ready_bundle()
        bundle["references"][1]["contact_id"] = bundle["references"][0]["contact_id"]
        with self.assertRaises(EvidenceError):
            evaluate_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
