from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "revenue" / "usac_ai_consulting" / "qualification.py"
SPEC = importlib.util.spec_from_file_location("usac_q", MOD_PATH)
assert SPEC is not None and SPEC.loader is not None
q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(q)

MANIFEST = json.loads((ROOT / "revenue" / "usac_ai_consulting" / "source_manifest.json").read_text())
SAMPLE = json.loads((ROOT / "revenue" / "usac_ai_consulting" / "sample_facts.json").read_text())
AS_OF = "2026-09-13T14:45:00Z"


def contract(holder: str, suffix: str) -> dict:
    return {
        "holder": holder,
        "client": f"Client {suffix}",
        "contract_ref": f"REF-{suffix}",
        "relevant_date": "2025-06-01",
        "similar_scope": True,
        "regulated_or_federal_oversight": True,
        "reference_reachable": True,
        "reference_permission_confirmed": True,
    }


def baseline() -> dict:
    facts = copy.deepcopy(SAMPLE)
    facts["organization"] = {
        "legal_name": "Example Offeror LLC",
        "us_performance_capable": True,
    }
    facts["key_personnel"] = [{
        "name": "Named SME",
        "role": "AI Subject Matter Expert",
        "affiliation": "prime",
        "committed": True,
    }]
    return facts


class QualificationTests(unittest.TestCase):
    def test_default_packet_holds(self):
        receipt = q.evaluate(copy.deepcopy(MANIFEST), copy.deepcopy(SAMPLE), as_of=AS_OF)
        self.assertEqual(receipt["decision"], "HOLD")
        self.assertFalse(receipt["submission_ready"])
        self.assertFalse(receipt["submission_authority"])
        self.assertIn("US_PERFORMANCE_CAPABILITY_UNPROVEN", receipt["blockers"])
        self.assertIn("QUALIFYING_CORPORATE_PAST_PERFORMANCE_LT_2", receipt["blockers"])

    def test_two_prime_contracts_make_prime_path(self):
        facts = baseline()
        facts["past_performance"] = [contract("prime", "A"), contract("prime", "B")]
        receipt = q.evaluate(copy.deepcopy(MANIFEST), facts, as_of=AS_OF)
        self.assertEqual(receipt["decision"], "PRIME_READY")
        self.assertEqual(receipt["prime_count"], 2)
        self.assertFalse(receipt["submission_ready"])
        self.assertFalse(receipt["submission_authority"])

    def test_partner_contracts_require_teaming(self):
        facts = baseline()
        facts["past_performance"] = [
            contract("prime", "A"),
            contract("teaming_partner", "B"),
        ]
        receipt = q.evaluate(copy.deepcopy(MANIFEST), facts, as_of=AS_OF)
        self.assertEqual(receipt["decision"], "TEAMING_REQUIRED")
        self.assertEqual(receipt["prime_count"], 1)
        self.assertEqual(receipt["team_count"], 1)

    def test_personal_resume_cannot_masquerade_as_corporate_contract(self):
        facts = baseline()
        bad = contract("prime", "A")
        bad["holder"] = "prior_employer_personal_experience"
        facts["past_performance"] = [bad, contract("prime", "B")]
        receipt = q.evaluate(copy.deepcopy(MANIFEST), facts, as_of=AS_OF)
        self.assertEqual(receipt["decision"], "HOLD")
        self.assertTrue(any("holder must be prime or teaming_partner" in b for b in receipt["blockers"]))

    def test_stale_contract_rejected(self):
        facts = baseline()
        a = contract("prime", "A")
        a["relevant_date"] = "2022-01-01"
        facts["past_performance"] = [a, contract("prime", "B")]
        receipt = q.evaluate(copy.deepcopy(MANIFEST), facts, as_of=AS_OF)
        self.assertEqual(receipt["decision"], "HOLD")
        self.assertTrue(any("older than three-year" in b for b in receipt["blockers"]))

    def test_reference_permission_is_fail_closed(self):
        facts = baseline()
        a = contract("prime", "A")
        a["reference_permission_confirmed"] = False
        facts["past_performance"] = [a, contract("prime", "B")]
        receipt = q.evaluate(copy.deepcopy(MANIFEST), facts, as_of=AS_OF)
        self.assertEqual(receipt["decision"], "HOLD")
        self.assertTrue(any("reference_permission_confirmed not proven" in b for b in receipt["blockers"]))

    def test_key_personnel_limit_enforced(self):
        facts = baseline()
        facts["past_performance"] = [contract("prime", "A"), contract("prime", "B")]
        facts["key_personnel"].extend([
            {"name": f"P{i}", "role": "Support", "affiliation": "prime", "committed": True}
            for i in range(4)
        ])
        receipt = q.evaluate(copy.deepcopy(MANIFEST), facts, as_of=AS_OF)
        self.assertEqual(receipt["decision"], "HOLD")
        self.assertIn("KEY_PERSONNEL_LIMIT_EXCEEDED", receipt["blockers"])

    def test_source_currentness_is_fail_closed(self):
        manifest = copy.deepcopy(MANIFEST)
        manifest["current_page_verified"] = False
        facts = baseline()
        facts["past_performance"] = [contract("prime", "A"), contract("prime", "B")]
        receipt = q.evaluate(manifest, facts, as_of=AS_OF)
        self.assertEqual(receipt["decision"], "HOLD")
        self.assertIn("SOURCE_CURRENTNESS_UNVERIFIED", receipt["blockers"])

    def test_deadline_passed_is_fail_closed(self):
        facts = baseline()
        facts["past_performance"] = [contract("prime", "A"), contract("prime", "B")]
        receipt = q.evaluate(copy.deepcopy(MANIFEST), facts, as_of="2026-09-30T15:00:00Z")
        self.assertEqual(receipt["decision"], "HOLD")
        self.assertIn("DEADLINE_PASSED", receipt["blockers"])

    def test_ai_use_never_self_authorizes_performance(self):
        facts = baseline()
        facts["past_performance"] = [contract("prime", "A"), contract("prime", "B")]
        facts["ai_delivery"]["ai_use_requested"] = True
        facts["ai_delivery"]["ai_use_described_in_technical_volume"] = True
        facts["proposal"]["bid_sheet_with_ai_complete"] = True
        receipt = q.evaluate(copy.deepcopy(MANIFEST), facts, as_of=AS_OF)
        self.assertEqual(receipt["decision"], "PRIME_READY")
        self.assertFalse(receipt["performance_ai_authorized"])
        self.assertTrue(any("AI_PERFORMANCE_NOT_AUTHORIZED" in w for w in receipt["warnings"]))

    def test_url_bound_source_truth_is_visible(self):
        facts = baseline()
        facts["past_performance"] = [contract("prime", "A"), contract("prime", "B")]
        receipt = q.evaluate(copy.deepcopy(MANIFEST), facts, as_of=AS_OF)
        self.assertEqual(receipt["source_binding"], "URL_BOUND_OFFICIAL_PAGE_ONLY")
        self.assertTrue(any("NOT_BYTE_BOUND" in w for w in receipt["warnings"]))

    def test_cli_strict_mode_fails_on_sample(self):
        cmd = [
            sys.executable,
            str(MOD_PATH),
            "--manifest", str(ROOT / "revenue/usac_ai_consulting/source_manifest.json"),
            "--facts", str(ROOT / "revenue/usac_ai_consulting/sample_facts.json"),
            "--as-of", AS_OF,
            "--require-submission-ready",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 2)
        parsed = json.loads(proc.stdout)
        self.assertEqual(parsed["decision"], "HOLD")


if __name__ == "__main__":
    unittest.main()
