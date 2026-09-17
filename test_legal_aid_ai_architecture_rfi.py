from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from commercial.legal_aid_ai_architecture_rfi.core import (
    AUTHORITY,
    INPUT_SCHEMA,
    QUESTION_BY_ID,
    QUESTION_SPECS,
    REQUIREMENT_MANIFEST_SHA256,
    RFIError,
    canonical_json,
    compile_rfi,
    empty_template,
    render_markdown,
    source_binding,
    strict_json_loads,
    verify_rfi,
)


def evidence(kind: str, ref: str):
    return {"kind": kind, "ref": ref}


def pricing(option: str, low: int, high: int, *, currency="USD", decimals=2, model="FIXED_FEE"):
    return {
        "option": option,
        "currency": currency,
        "decimals": decimals,
        "low_minor": low,
        "high_minor": high,
        "model": model,
        "assumptions": ["Non-binding market-research estimate; final scope and price require owner review."],
        "evidence_refs": [evidence("OWNER", f"owner:pricing:{option}")],
    }


def complete_input():
    rows = []
    for qid, _section, _key, _allow_na, kinds in QUESTION_SPECS:
        preferred = "OWNER" if "OWNER" in kinds else sorted(kinds)[0]
        rows.append({
            "question_id": qid,
            "status": "ANSWERED",
            "answer": f"Owner-reviewed draft response for {qid}.",
            "evidence_refs": [evidence(preferred, f"{preferred.lower()}:evidence:{qid}")],
        })
    return {
        "schema": INPUT_SCHEMA,
        "as_of": "2026-09-17T03:30:00-04:00",
        "source": source_binding(),
        "answers": rows,
        "pricing_options": [
            pricing("AI_READINESS_ONLY", 1_000_000, 2_000_000),
            pricing("GOVERNANCE_POLICY_ONLY", 1_000_000, 2_500_000),
            pricing("ARCHITECTURE_VENDOR_STRATEGY_ONLY", 1_500_000, 3_000_000),
            pricing("FULL_PLANNING_ENGAGEMENT", 3_000_000, 6_000_000),
        ],
        "assurances": {
            "sensitive_information_screened": True,
            "claim_evidence_reviewed": True,
            "pricing_non_binding_ack": True,
        },
    }


def row(data, qid):
    return next(item for item in data["answers"] if item["question_id"] == qid)


class LegalAidArchitectureRFITests(unittest.TestCase):
    def test_empty_template_holds_all_31(self):
        packet = compile_rfi(empty_template())
        self.assertEqual(packet["readiness"]["status"], "HOLD")
        self.assertEqual(packet["coverage"]["question_count_present"], 31)
        self.assertEqual(packet["coverage"]["question_count_resolved"], 0)
        self.assertEqual(len(packet["coverage"]["owner_input_required_ids"]), 31)

    def test_complete_packet_ready(self):
        packet = compile_rfi(complete_input())
        self.assertEqual(packet["readiness"]["status"], "READY_FOR_OWNER_RFI_REVIEW")
        self.assertEqual(packet["coverage"]["question_count_present"], 31)
        self.assertEqual(packet["coverage"]["question_count_resolved"], 31)
        self.assertEqual(packet["coverage"]["missing_question_ids"], [])
        self.assertEqual(packet["readiness"]["blockers"], [])
        self.assertEqual(len(packet["pricing_options"]), 4)
        self.assertTrue(verify_rfi(complete_input(), packet))

    def test_authority_is_all_false(self):
        packet = compile_rfi(complete_input())
        self.assertTrue(AUTHORITY)
        self.assertTrue(packet["authority"])
        self.assertTrue(all(value is False for value in packet["authority"].values()))

    def test_manifest_digest_is_bound(self):
        packet = compile_rfi(complete_input())
        self.assertEqual(packet["source"]["requirement_manifest_sha256"], REQUIREMENT_MANIFEST_SHA256)
        self.assertEqual(packet["source_manifest"]["question_count"], 31)
        self.assertEqual(len(packet["source_manifest"]["questions"]), 31)

    def test_source_tamper_rejected(self):
        data = complete_input(); data["source"]["response_email"] = "attacker@example.com"
        with self.assertRaisesRegex(RFIError, "retained buyer manifest"):
            compile_rfi(data)

    def test_duplicate_question_rejected(self):
        data = complete_input(); data["answers"][1]["question_id"] = data["answers"][0]["question_id"]
        with self.assertRaisesRegex(RFIError, "duplicate question answer"):
            compile_rfi(data)

    def test_unknown_question_rejected(self):
        data = complete_input(); data["answers"][0]["question_id"] = "Q99"
        with self.assertRaisesRegex(RFIError, "unknown"):
            compile_rfi(data)

    def test_missing_question_holds_without_fabricating_row(self):
        data = complete_input(); data["answers"] = [item for item in data["answers"] if item["question_id"] != "Q18"]
        packet = compile_rfi(data)
        self.assertEqual(packet["readiness"]["status"], "HOLD")
        self.assertEqual(packet["coverage"]["missing_question_ids"], ["Q18"])
        self.assertIn("missing_question_rows", packet["readiness"]["blockers"])

    def test_owner_input_required_holds(self):
        data = complete_input(); target = row(data, "Q20")
        target.update(status="OWNER_INPUT_REQUIRED", answer="", evidence_refs=[])
        packet = compile_rfi(data)
        self.assertEqual(packet["readiness"]["status"], "HOLD")
        self.assertEqual(packet["coverage"]["owner_input_required_ids"], ["Q20"])

    def test_profile_question_cannot_be_not_applicable(self):
        data = complete_input(); target = row(data, "Q01")
        target.update(status="NOT_APPLICABLE", answer="No company identity.")
        with self.assertRaisesRegex(RFIError, "may not be marked NOT_APPLICABLE"):
            compile_rfi(data)

    def test_optional_not_applicable_is_resolved(self):
        data = complete_input(); target = row(data, "Q31")
        target.update(status="NOT_APPLICABLE", answer="No verified similar-work references are available for this response.", evidence_refs=[evidence("OWNER", "owner:refs:none")])
        packet = compile_rfi(data)
        self.assertEqual(packet["readiness"]["status"], "READY_FOR_OWNER_RFI_REVIEW")
        self.assertEqual(packet["coverage"]["not_applicable_ids"], ["Q31"])

    def test_answer_requires_evidence(self):
        data = complete_input(); row(data, "Q09")["evidence_refs"] = []
        with self.assertRaisesRegex(RFIError, "requires at least one"):
            compile_rfi(data)

    def test_owner_input_must_not_carry_evidence(self):
        data = complete_input(); target = row(data, "Q20")
        target.update(status="OWNER_INPUT_REQUIRED", answer="", evidence_refs=[evidence("OWNER", "owner:lead")])
        with self.assertRaisesRegex(RFIError, "must be empty"):
            compile_rfi(data)

    def test_staffing_rejects_repo_evidence(self):
        data = complete_input(); row(data, "Q19")["evidence_refs"] = [evidence("REPO", "repo:staff")]
        with self.assertRaisesRegex(RFIError, "not admissible"):
            compile_rfi(data)

    def test_pricing_answer_rejects_public_evidence(self):
        data = complete_input(); row(data, "Q26")["evidence_refs"] = [evidence("PUBLIC", "public:rate-card")]
        with self.assertRaisesRegex(RFIError, "not admissible"):
            compile_rfi(data)

    def test_reference_rejects_repo_evidence(self):
        data = complete_input(); row(data, "Q31")["evidence_refs"] = [evidence("REPO", "repo:reference")]
        with self.assertRaisesRegex(RFIError, "not admissible"):
            compile_rfi(data)

    def test_methodology_accepts_repo_evidence(self):
        data = complete_input(); row(data, "Q09")["evidence_refs"] = [evidence("REPO", "repo:methodology")]
        packet = compile_rfi(data)
        self.assertEqual(packet["readiness"]["status"], "READY_FOR_OWNER_RFI_REVIEW")

    def test_pricing_bool_minor_rejected(self):
        data = complete_input(); data["pricing_options"][0]["low_minor"] = True
        with self.assertRaisesRegex(RFIError, "must be an integer"):
            compile_rfi(data)

    def test_pricing_low_above_high_rejected(self):
        data = complete_input(); data["pricing_options"][0]["low_minor"] = 9_000_000
        with self.assertRaisesRegex(RFIError, "cannot exceed"):
            compile_rfi(data)

    def test_pricing_mixed_currency_rejected(self):
        data = complete_input(); data["pricing_options"][1]["currency"] = "EUR"
        with self.assertRaisesRegex(RFIError, "one native currency"):
            compile_rfi(data)

    def test_duplicate_pricing_option_rejected(self):
        data = complete_input(); data["pricing_options"][1]["option"] = data["pricing_options"][0]["option"]
        with self.assertRaisesRegex(RFIError, "duplicate pricing option"):
            compile_rfi(data)

    def test_q25_answered_without_structured_pricing_holds(self):
        data = complete_input(); data["pricing_options"] = []
        packet = compile_rfi(data)
        self.assertEqual(packet["readiness"]["status"], "HOLD")
        self.assertIn("structured_pricing_ranges_missing", packet["readiness"]["blockers"])

    def test_false_assurances_hold(self):
        for key in list(complete_input()["assurances"]):
            data = complete_input(); data["assurances"][key] = False
            packet = compile_rfi(data)
            self.assertEqual(packet["readiness"]["status"], "HOLD")
            self.assertTrue(any(key in blocker for blocker in packet["readiness"]["blockers"]))

    def test_receipt_tamper_fails_verification(self):
        data = complete_input(); packet = compile_rfi(data)
        packet["receipt"]["sha256"] = "0" * 64
        self.assertFalse(verify_rfi(data, packet))

    def test_semantic_tamper_fails_verification(self):
        data = complete_input(); packet = compile_rfi(data)
        packet["answers"][0]["answer"] = "forged"
        self.assertFalse(verify_rfi(data, packet))

    def test_render_has_draft_banner_sections_and_authority_warning(self):
        text = render_markdown(compile_rfi(complete_input()))
        self.assertIn("DRAFT — OWNER REVIEW REQUIRED — NOT SUBMITTED", text)
        self.assertIn("## A. Vendor Profile and Qualifications", text)
        self.assertIn("## I. References", text)
        self.assertIn("does not authorize buyer contact", text)
        self.assertIn("FULL_PLANNING_ENGAGEMENT", text)

    def test_strict_json_rejects_duplicate_keys(self):
        with self.assertRaisesRegex(RFIError, "duplicate JSON key"):
            strict_json_loads('{"a":1,"a":2}')

    def test_strict_json_rejects_float_and_nan(self):
        with self.assertRaises(RFIError): strict_json_loads('{"a":1.5}')
        with self.assertRaises(RFIError): strict_json_loads('{"a":NaN}')

    def test_lone_surrogate_answer_rejected(self):
        data = complete_input(); row(data, "Q09")["answer"] = "bad\ud800"
        with self.assertRaisesRegex(RFIError, "Unicode scalar"):
            compile_rfi(data)

    def test_cli_template_compile_verify_render(self):
        root = Path(__file__).parent
        env = dict(os.environ); env["PYTHONPATH"] = str(root)
        with tempfile.TemporaryDirectory() as td:
            input_path = Path(td) / "input.json"
            packet_path = Path(td) / "packet.json"
            md_path = Path(td) / "draft.md"
            template_path = Path(td) / "template.json"
            input_path.write_text(canonical_json(complete_input()), encoding="utf-8")
            commands = [
                [sys.executable, "-m", "commercial.legal_aid_ai_architecture_rfi.core", "template", str(template_path)],
                [sys.executable, "-m", "commercial.legal_aid_ai_architecture_rfi.core", "compile", str(input_path), str(packet_path)],
                [sys.executable, "-m", "commercial.legal_aid_ai_architecture_rfi.core", "verify", str(input_path), str(packet_path)],
                [sys.executable, "-m", "commercial.legal_aid_ai_architecture_rfi.core", "render", str(input_path), str(md_path)],
            ]
            for command in commands:
                cp = subprocess.run(command, env=env, capture_output=True, text=True)
                self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertEqual(strict_json_loads(template_path.read_text())["schema"], INPUT_SCHEMA)
            self.assertIn("DRAFT — OWNER REVIEW REQUIRED", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
