import copy
import datetime as dt
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("wrfcheck", HERE.parent / "validate_readiness.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
BASE = json.loads((HERE.parent / "submission_manifest.json").read_text())
NOW = dt.datetime(2026, 9, 13, 13, 30, tzinfo=dt.timezone.utc)
EXP = "2026-09-14T20:59:59Z"


def _record(gate, subject, claim, n):
    r = {
        "opportunity_id": v.OPPORTUNITY_ID,
        "gate": gate,
        "subject": subject,
        "evidence_type": "synthetic_review_fixture",
        "source_id": f"fixture-source-{n:03d}",
        "source_generation": f"fixture-generation-{n:03d}",
        "source_sha256": f"{n:064x}"[-64:],
        "claim_sha256": claim,
        "verified_at": "2026-09-13T12:00:00Z",
        "expires_at": EXP,
    }
    r["record_id"] = v.record_id_for(r)
    return r


def ready_fixture():
    m = copy.deepcopy(BASE)
    m["intended_submission_state"] = v.READY
    m["budget"]["wrf_request_usd"] = 300000
    m["budget"]["documented_eligible_contribution_usd"] = 99000
    m["budget"]["reimbursed_indirect_cost_usd"] = 45000
    m["utility_participants"] = [
        {
            "utility_ref": "utility-a",
            "site_ref": "site-drinking-a",
            "sector": "drinking_water",
            "consent_status": "PROVEN",
            "consent_evidence": [],
        },
        {
            "utility_ref": "utility-b",
            "site_ref": "site-wastewater-b",
            "sector": "wastewater",
            "consent_status": "PROVEN",
            "consent_evidence": [],
        },
    ]
    records = []
    n = 1

    def add(entry, gate, subject, claim):
        nonlocal n
        entry["status"] = "PROVEN"
        rec = _record(gate, subject, claim, n)
        n += 1
        entry["evidence"] = [rec["record_id"]]
        records.append(rec)

    add(
        m["deadline"]["deadline_offset_recheck"],
        "deadline_offset_recheck", v.OPPORTUNITY_ID,
        v._gate_claim("deadline_offset_recheck", v.OPPORTUNITY_ID),
    )
    for gate in sorted(v.REQUIRED_HARD_GATES):
        add(m["hard_gates"][gate], gate, "applicant", v._gate_claim(gate))
    add(m["budget"]["budget_terms"], "budget_terms", "applicant", v._budget_claim(m["budget"]))
    add(m["budget"]["budget_workbook"], "budget_workbook", "applicant", v._gate_claim("budget_workbook"))
    add(m["budget"]["budget_narrative"], "budget_narrative", "applicant", v._gate_claim("budget_narrative"))
    for p in m["utility_participants"]:
        rec = _record("utility_consent", f"{p['utility_ref']}:{p['site_ref']}", v._utility_claim(p), n)
        n += 1
        p["consent_evidence"] = [rec["record_id"]]
        records.append(rec)

    bundle = {
        "schema_version": 1,
        "opportunity_id": v.OPPORTUNITY_ID,
        "generation": "synthetic-reviewed-authority-v1",
        "captured_at": "2026-09-13T12:00:00Z",
        "records": records,
    }
    return m, bundle


def evaluate_pinned(m, bundle, now=NOW):
    digest = v.authority_bundle_digest(bundle)
    with mock.patch.object(v, "PINNED_AUTHORITY_ROOTS", frozenset({digest})):
        return v.evaluate(m, bundle, now)


class Tests(unittest.TestCase):
    def test_default_holds_without_authority(self):
        result = v.evaluate(copy.deepcopy(BASE), None, NOW)
        self.assertEqual(result["state"], v.HOLD)
        self.assertIn("trusted authority bundle missing", result["reasons"])
        self.assertTrue(any("organization_my_portal_account" in x for x in result["reasons"]))

    def test_candidate_self_minted_proven_strings_cannot_ready(self):
        m = copy.deepcopy(BASE)
        m["intended_submission_state"] = v.READY
        m["deadline"]["deadline_offset_recheck"] = {"status": "PROVEN", "evidence": ["synthetic:test"]}
        m["budget"]["wrf_request_usd"] = 300000
        m["budget"]["documented_eligible_contribution_usd"] = 99000
        m["budget"]["reimbursed_indirect_cost_usd"] = 0
        for key in ("budget_terms", "budget_workbook", "budget_narrative"):
            m["budget"][key] = {"status": "PROVEN", "evidence": ["synthetic:test"]}
        for gate in m["hard_gates"]:
            m["hard_gates"][gate] = {"status": "PROVEN", "evidence": ["synthetic:test"]}
        m["utility_participants"] = [
            {"utility_ref":"a","site_ref":"a1","sector":"drinking_water","consent_status":"PROVEN","consent_evidence":["synthetic:a"]},
            {"utility_ref":"b","site_ref":"b1","sector":"wastewater","consent_status":"PROVEN","consent_evidence":["synthetic:b"]},
        ]
        result = v.evaluate(m, None, NOW)
        self.assertEqual(result["state"], v.HOLD)
        self.assertIn("READY spoofed while blockers remain", result["reasons"])
        self.assertIn("trusted authority bundle missing", result["reasons"])

    def test_reviewed_pinned_authority_can_reach_review_ready_only(self):
        m, bundle = ready_fixture()
        result = evaluate_pinned(m, bundle)
        self.assertEqual(result["state"], v.READY)
        self.assertEqual(result["reasons"], [])
        self.assertFalse(result["receipt"]["carrier_may_submit"])
        self.assertEqual(result["receipt"]["contract_sha256"], v.CONTRACT_DIGEST)

    def test_authority_bundle_not_pinned_holds(self):
        m, bundle = ready_fixture()
        result = v.evaluate(m, bundle, NOW)
        self.assertEqual(result["state"], v.HOLD)
        self.assertTrue(any("root not pinned" in x for x in result["reasons"]))

    def test_missing_required_gate_holds(self):
        m, bundle = ready_fixture()
        del m["hard_gates"]["financial_statements_packet"]
        result = evaluate_pinned(m, bundle)
        self.assertEqual(result["state"], v.HOLD)
        self.assertTrue(any("missing required gates" in x for x in result["reasons"]))

    def test_extra_gate_holds(self):
        m, bundle = ready_fixture()
        m["hard_gates"]["anything"] = {"status": "PROVEN", "evidence": []}
        result = evaluate_pinned(m, bundle)
        self.assertEqual(result["state"], v.HOLD)
        self.assertTrue(any("unknown gates" in x for x in result["reasons"]))

    def test_forged_future_deadline_holds_and_fixed_deadline_expires(self):
        m, bundle = ready_fixture()
        m["deadline"]["local"] = "2099-09-14T15:00:00"
        result = evaluate_pinned(m, bundle)
        self.assertEqual(result["state"], v.HOLD)
        self.assertTrue(any("cannot override" in x for x in result["reasons"]))
        m, bundle = ready_fixture()
        result = evaluate_pinned(m, bundle, dt.datetime(2026, 9, 14, 21, 0, tzinfo=dt.timezone.utc))
        self.assertEqual(result["state"], v.HOLD)
        self.assertIn("deadline expired", result["reasons"])

    def test_one_sector_both_is_rejected(self):
        m, bundle = ready_fixture()
        m["utility_participants"][0]["sector"] = "both"
        result = evaluate_pinned(m, bundle)
        self.assertEqual(result["state"], v.HOLD)
        self.assertTrue(any("sector must" in x for x in result["reasons"]))

    def test_same_site_twice_holds(self):
        m, bundle = ready_fixture()
        m["utility_participants"][1]["site_ref"] = m["utility_participants"][0]["site_ref"]
        result = evaluate_pinned(m, bundle)
        self.assertEqual(result["state"], v.HOLD)
        self.assertIn("multi-site utility requirement not proven", result["reasons"])

    def test_indirect_cost_above_15_percent_holds(self):
        m, bundle = ready_fixture()
        m["budget"]["reimbursed_indirect_cost_usd"] = 45000.01
        result = evaluate_pinned(m, bundle)
        self.assertEqual(result["state"], v.HOLD)
        self.assertTrue(any("exceeds 15% ceiling" in x for x in result["reasons"]))

    def test_one_cent_short_contribution_holds(self):
        m, bundle = ready_fixture()
        m["budget"]["documented_eligible_contribution_usd"] = 98999.99
        result = evaluate_pinned(m, bundle)
        self.assertEqual(result["state"], v.HOLD)
        self.assertTrue(any("contribution below required 99000.00" in x for x in result["reasons"]))

    def test_budget_claim_change_breaks_authority_binding(self):
        m, bundle = ready_fixture()
        m["budget"]["wrf_request_usd"] = 299999
        result = evaluate_pinned(m, bundle)
        self.assertEqual(result["state"], v.HOLD)
        self.assertTrue(any("budget.budget_terms: authority claim digest mismatch" in x for x in result["reasons"]))

    def test_cross_gate_record_reuse_holds(self):
        m, bundle = ready_fixture()
        source = m["hard_gates"]["applying_entity_identity"]["evidence"][0]
        m["hard_gates"]["financial_statements_packet"]["evidence"] = [source]
        result = evaluate_pinned(m, bundle)
        self.assertEqual(result["state"], v.HOLD)
        self.assertTrue(any("authority record reused across claims" in x for x in result["reasons"]))

    def test_cross_opportunity_bundle_holds(self):
        m, bundle = ready_fixture()
        bundle["opportunity_id"] = "OTHER"
        digest = v.authority_bundle_digest(bundle)
        with mock.patch.object(v, "PINNED_AUTHORITY_ROOTS", frozenset({digest})):
            result = v.evaluate(m, bundle, NOW)
        self.assertEqual(result["state"], v.HOLD)
        self.assertTrue(any("wrong opportunity_id" in x for x in result["reasons"]))

    def test_expired_authority_record_holds(self):
        m, bundle = ready_fixture()
        bundle["records"][0]["expires_at"] = "2026-09-13T13:00:00Z"
        bundle["records"][0]["record_id"] = v.record_id_for(bundle["records"][0])
        m["deadline"]["deadline_offset_recheck"]["evidence"] = [bundle["records"][0]["record_id"]]
        result = evaluate_pinned(m, bundle)
        self.assertEqual(result["state"], v.HOLD)
        self.assertTrue(any("authority expired" in x for x in result["reasons"]))

    def test_cross_utility_consent_transplant_holds(self):
        m, bundle = ready_fixture()
        m["utility_participants"][1]["consent_evidence"] = list(m["utility_participants"][0]["consent_evidence"])
        result = evaluate_pinned(m, bundle)
        self.assertEqual(result["state"], v.HOLD)
        self.assertTrue(any("authority record reused across claims" in x for x in result["reasons"]))

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            v.parse_strict_json_bytes(b'{"a":1,"a":2}')

    def test_oversize_input_rejected(self):
        with self.assertRaisesRegex(ValueError, "hard byte cap"):
            v.parse_strict_json_bytes(b" " * (v.MAX_JSON_BYTES + 1))

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink unavailable")
    def test_final_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "target.json"
            link = Path(td) / "link.json"
            target.write_text("{}")
            os.symlink(target, link)
            with self.assertRaises(OSError):
                v.read_bounded_regular_file(link)

    def test_receipt_is_deterministic_for_fixed_time(self):
        m, bundle = ready_fixture()
        a = evaluate_pinned(m, bundle)
        b = evaluate_pinned(copy.deepcopy(m), copy.deepcopy(bundle))
        self.assertEqual(a, b)
        self.assertEqual(a["receipt"]["receipt_sha256"], b["receipt"]["receipt_sha256"])


if __name__ == "__main__":
    unittest.main()
