from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "revenue" / "uark_rfp09112026_cmmc" / "qualifier.py"
FIXTURE_PATH = ROOT / "revenue" / "uark_rfp09112026_cmmc" / "synthetic_candidate.json"
SOURCE_PATH = ROOT / "revenue" / "uark_rfp09112026_cmmc" / "source_ledger.json"
MATRIX_PATH = ROOT / "revenue" / "uark_rfp09112026_cmmc" / "requirement_matrix.json"
WORKSHEET_PATH = ROOT / "revenue" / "uark_rfp09112026_cmmc" / "owner_evidence_worksheet.json"

SPEC = importlib.util.spec_from_file_location("uark_rfp09112026_qualifier", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

def fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

def prime_candidate() -> dict:
    value = fixture()
    c = value["candidate"]
    c["route_requested"] = "PRIME"
    for field in (
        "legal_entity_ready", "authorized_signer_ready", "portal_submission_ready",
        "insurance_evidence_ready", "similar_cmmc_engagements_evidence_ready",
        "personnel_qualification_evidence_ready", "pricing_authority_ready",
        "statutory_certifications_reviewed",
    ):
        c[field] = True
    c["current_us_reference_count"] = 3
    c["higher_ed_reference_count"] = 3
    return value

class UarkRfp09112026Tests(unittest.TestCase):
    def test_synthetic_teaming_route_is_ready_but_not_outbound_authority(self) -> None:
        packet = mod.compile_qualification(fixture())
        self.assertEqual(packet["decision"]["status"], "TEAMING_READY")
        self.assertFalse(packet["decision"]["submission_ready"])
        self.assertFalse(packet["decision"]["partner_outreach_authorized"])
        self.assertFalse(packet["decision"]["authority"]["partner_contact_authorized"])

    def test_teaming_can_be_ready_while_direct_prime_gates_are_not(self) -> None:
        packet = mod.compile_qualification(fixture())
        self.assertIn("OUR_DIRECT_PRIME_REFERENCE_GATE_NOT_MET_PARTNER_MUST_CARRY", packet["decision"]["risks"])
        self.assertIn("OUR_DIRECT_PRIME_INSURANCE_GATE_NOT_MET_PARTNER_MUST_CARRY_OR_ALLOCATE", packet["decision"]["risks"])

    def test_prime_fails_closed_until_standard_terms_acquired(self) -> None:
        packet = mod.compile_qualification(prime_candidate())
        self.assertEqual(packet["decision"]["status"], "HOLD")
        self.assertIn("STANDARD_TERMS_NOT_ACQUIRED_FOR_SUBMISSION", packet["decision"]["blockers"])

    def test_minimum_three_references_is_mandatory_for_prime(self) -> None:
        value = prime_candidate()
        value["candidate"]["current_us_reference_count"] = 2
        value["candidate"]["higher_ed_reference_count"] = 2
        packet = mod.compile_qualification(value)
        self.assertIn("MINIMUM_THREE_CURRENT_US_REFERENCES_NOT_MET", packet["decision"]["blockers"])

    def test_higher_ed_references_are_score_risk_not_false_mandatory_gate(self) -> None:
        value = prime_candidate()
        value["candidate"]["higher_ed_reference_count"] = 0
        packet = mod.compile_qualification(value)
        self.assertIn("QUALIFICATION_SCORE_RISK_NO_HIGHER_ED_REFERENCE", packet["decision"]["risks"])
        self.assertNotIn("HIGHER_ED_REFERENCE_MANDATORY", packet["decision"]["blockers"])

    def test_missing_insurance_blocks_prime(self) -> None:
        value = prime_candidate()
        value["candidate"]["insurance_evidence_ready"] = False
        packet = mod.compile_qualification(value)
        self.assertIn("INSURANCE_EVIDENCE_NOT_READY", packet["decision"]["blockers"])

    def test_missing_personnel_evidence_blocks_teaming(self) -> None:
        value = fixture()
        value["candidate"]["personnel_qualification_evidence_ready"] = False
        packet = mod.compile_qualification(value)
        self.assertEqual(packet["decision"]["status"], "HOLD")
        self.assertIn("WORKSHARE_PERSONNEL_EVIDENCE_NOT_READY", packet["decision"]["blockers"])

    def test_each_teaming_gate_fails_closed(self) -> None:
        fields = {
            "partner_prime_identified":"PARTNER_PRIME_NOT_IDENTIFIED",
            "partner_prime_responsibility_confirmed":"PARTNER_PRIME_RESPONSIBILITY_NOT_CONFIRMED",
            "partner_due_diligence_ready":"PARTNER_DUE_DILIGENCE_NOT_READY",
            "specific_service_scope_agreed":"SPECIFIC_SERVICE_SCOPE_NOT_AGREED",
            "technical_workshare_owner_ready":"TECHNICAL_WORKSHARE_OWNER_NOT_READY",
            "workshare_price_boundary_ready":"WORKSHARE_PRICE_BOUNDARY_NOT_READY",
        }
        for field, reason in fields.items():
            value = fixture()
            value["candidate"][field] = False
            packet = mod.compile_qualification(value)
            self.assertEqual(packet["decision"]["status"], "HOLD")
            self.assertIn(reason, packet["decision"]["blockers"])

    def test_certification_claim_forces_hold(self) -> None:
        value = fixture()
        value["candidate"]["cmmc_certification_claimed"] = True
        packet = mod.compile_qualification(value)
        self.assertIn("UNAUTHORIZED_CMMC_CERTIFICATION_CLAIM", packet["decision"]["blockers"])

    def test_external_assessor_claim_forces_hold(self) -> None:
        value = fixture()
        value["candidate"]["external_assessor_authority_claimed"] = True
        packet = mod.compile_qualification(value)
        self.assertIn("UNAUTHORIZED_EXTERNAL_ASSESSOR_CLAIM", packet["decision"]["blockers"])

    def test_buyer_interest_award_revenue_claims_force_hold(self) -> None:
        cases = {
            "buyer_interest_claimed":"BUYER_INTEREST_CLAIM_PRESENT",
            "award_claimed":"AWARD_CLAIM_PRESENT",
            "revenue_claimed":"REVENUE_CLAIM_PRESENT",
        }
        for field, reason in cases.items():
            value = fixture()
            value["candidate"][field] = True
            packet = mod.compile_qualification(value)
            self.assertIn(reason, packet["decision"]["blockers"])

    def test_deadline_expiry_is_no_bid(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = "2026-10-16T19:30:00Z"
        packet = mod.compile_qualification(value)
        self.assertEqual(packet["decision"]["status"], "NO_BID")
        self.assertIn("PROPOSAL_DEADLINE_PASSED", packet["decision"]["blockers"])

    def test_withdrawn_is_no_bid(self) -> None:
        value = fixture()
        value["candidate"]["opportunity_withdrawn"] = True
        self.assertEqual(mod.compile_qualification(value)["decision"]["status"], "NO_BID")

    def test_question_deadline_pass_is_risk_not_bid_expiry(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = "2026-09-25T22:00:00Z"
        packet = mod.compile_qualification(value)
        self.assertEqual(packet["decision"]["status"], "TEAMING_READY")
        self.assertIn("QUESTION_DEADLINE_PASSED", packet["decision"]["risks"])

    def test_source_generation_drift_rejected(self) -> None:
        value = fixture()
        value["source_generation"]["hogbid_checked_at_utc"] = "2026-09-15T01:01:00Z"
        with self.assertRaisesRegex(mod.InputError, "source generation drift"):
            mod.compile_qualification(value)

    def test_contact_route_field_injection_rejected(self) -> None:
        value = fixture()
        value["candidate"]["partner_email"] = "nobody@example.com"
        with self.assertRaisesRegex(mod.InputError, "forbidden contact-route"):
            mod.compile_qualification(value)

    def test_unknown_field_rejected(self) -> None:
        value = fixture()
        value["candidate"]["confidence"] = 0.9
        with self.assertRaisesRegex(mod.InputError, "schema mismatch"):
            mod.compile_qualification(value)

    def test_duplicate_json_keys_rejected(self) -> None:
        with self.assertRaisesRegex(mod.InputError, "duplicate JSON key"):
            mod.parse_json_strict('{"schema":"a","schema":"b"}')

    def test_nonfinite_json_rejected(self) -> None:
        with self.assertRaisesRegex(mod.InputError, "non-finite"):
            mod.parse_json_strict('{"x":NaN}')

    def test_bool_not_accepted_as_reference_count(self) -> None:
        value = fixture()
        value["candidate"]["current_us_reference_count"] = True
        with self.assertRaisesRegex(mod.InputError, "nonnegative integer"):
            mod.compile_qualification(value)

    def test_reference_counts_are_consistent(self) -> None:
        value = fixture()
        value["candidate"]["current_us_reference_count"] = 1
        value["candidate"]["higher_ed_reference_count"] = 2
        with self.assertRaisesRegex(mod.InputError, "cannot exceed"):
            mod.compile_qualification(value)

    def test_packet_receipt_tamper_rejected(self) -> None:
        packet = mod.compile_qualification(fixture())
        packet["internal_workshare_target_usd"] = 1
        with self.assertRaisesRegex(mod.InputError, "receipt mismatch"):
            mod.verify_packet(packet)

    def test_semantic_tamper_rejected_with_recomputed_outer_digest(self) -> None:
        packet = mod.compile_qualification(fixture())
        packet["decision"]["status"] = "PRIME_READY"
        unsigned = copy.deepcopy(packet)
        unsigned.pop("packet_receipt_sha256")
        packet["packet_receipt_sha256"] = mod.sha256_obj(unsigned)
        with self.assertRaisesRegex(mod.InputError, "semantic verification"):
            mod.verify_packet(packet)

    def test_rfp_facts_do_not_overstate_higher_ed_reference_gate(self) -> None:
        ledger = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        ref = next(row for row in ledger["controlling_facts"] if row["id"] == "references")
        self.assertIn("preferred", ref["fact"])
        matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
        r04 = next(row for row in matrix["requirements"] if row["id"] == "R04")
        self.assertIn("continental-US", r04["requirement"])
        r05 = next(row for row in matrix["requirements"] if row["id"] == "R05")
        self.assertEqual(r05["type"], "preferred_scored")

    def test_owner_worksheet_keeps_external_prime_gates_unknown(self) -> None:
        worksheet = json.loads(WORKSHEET_PATH.read_text(encoding="utf-8"))
        statuses = {row["field"]: row["status"] for row in worksheet["prime_gates"]}
        self.assertEqual(statuses["insurance_evidence_ready"], "UNKNOWN")
        self.assertEqual(statuses["current_us_reference_count"], "UNKNOWN")

    def test_authority_ceiling_is_false_for_mutating_actions(self) -> None:
        packet = mod.compile_qualification(fixture())
        authority = packet["decision"]["authority"]
        self.assertTrue(authority["internal_qualification_only"])
        for key, value in authority.items():
            if key != "internal_qualification_only":
                self.assertFalse(value, key)

    def test_markdown_preserves_not_offered_boundary(self) -> None:
        packet = mod.compile_qualification(fixture())
        md = mod.render_markdown(packet)
        self.assertIn("HISTORICAL / INTEGRITY ONLY", md)
        self.assertIn("NOT CURRENT", md)
        self.assertIn("INTERNAL_HYPOTHESIS_NOT_OFFERED", md)
        self.assertIn("authorizes no buyer or partner contact", md)

    def test_cli_compile_verify_and_exclusive_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "packet.json"
            md = Path(td) / "packet.md"

            refused = subprocess.run(
                [sys.executable, str(MODULE_PATH), "compile", str(FIXTURE_PATH),
                 "--json-out", str(out), "--markdown-out", str(md)],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
            self.assertIn("refuses persisted Markdown", refused.stderr)
            self.assertFalse(out.exists(), "historical Markdown refusal must precede JSON publication")
            self.assertFalse(md.exists(), "historical Markdown must not be persisted")

            subprocess.run(
                [sys.executable, str(MODULE_PATH), "compile", str(FIXTURE_PATH),
                 "--json-out", str(out)],
                check=True, cwd=ROOT,
            )
            verified = subprocess.run([sys.executable, str(MODULE_PATH), "verify", str(out)],
                                      check=True, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(verified.stdout.strip(), "VERIFIED")
            again = subprocess.run([sys.executable, str(MODULE_PATH), "compile", str(FIXTURE_PATH),
                                    "--json-out", str(out)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(again.returncode, 2)
            self.assertIn("exclusive create", again.stderr)

    def test_symlink_input_rejected(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            link = Path(td) / "input.json"
            try:
                os.symlink(FIXTURE_PATH, link)
            except OSError as exc:
                self.skipTest(str(exc))
            proc = subprocess.run([sys.executable, str(MODULE_PATH), "compile", str(link)],
                                  cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("non-symlink", proc.stderr)

if __name__ == "__main__":
    unittest.main()
