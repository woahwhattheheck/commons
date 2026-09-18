import copy
import datetime as dt
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("wrfcheck", HERE.parent / "validate_readiness.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
BASE = json.loads((HERE.parent / "submission_manifest.json").read_text())
NOW = dt.datetime(2026, 9, 13, 13, 30, tzinfo=dt.timezone.utc)
LATE = dt.datetime(2026, 9, 15, 0, 0, tzinfo=dt.timezone.utc)
SOURCE_ID = "synthetic-authority-generation"
SOURCE_SHA = "a" * 64


def record(eid, kind, gate, subject, fact, verified_at="2026-09-13T13:00:00Z"):
    return {
        "evidence_id": eid,
        "kind": kind,
        "gate": gate,
        "subject": subject,
        "opportunity_id": v.OPPORTUNITY_ID,
        "source_generation": SOURCE_ID,
        "source_sha256": SOURCE_SHA,
        "verified_at": verified_at,
        "fact_sha256": v.digest(fact),
    }


def ready_fixture():
    m = copy.deepcopy(BASE)
    m["intended_submission_state"] = v.READY
    for name, entry in m["hard_gates"].items():
        entry["status"] = "PROVEN"
        entry["subject"] = f"subject:{name}"
    m["budget"] = {
        "wrf_request_usd_cents": 30_000_000,
        "documented_eligible_contribution_usd_cents": 9_900_000,
        "direct_cost_base_usd_cents": 20_000_000,
        "reimbursed_indirect_usd_cents": 3_000_000,
    }
    for name, entry in m["budget_artifacts"].items():
        entry["status"] = "PROVEN"
        entry["subject"] = f"subject:{name}"
    m["utility_participants"] = [
        {"utility_id":"utility-a", "site_id":"site-a", "role":"field-demo", "sector":"drinking_water", "status":"PROVEN"},
        {"utility_id":"utility-b", "site_id":"site-b", "role":"field-demo", "sector":"wastewater", "status":"PROVEN"},
    ]

    records = []
    for i, name in enumerate(v.REQUIRED_GATES):
        fact = v.gate_fact(name, m["hard_gates"][name])
        records.append(record(f"gate-{i}", "GATE", name, fact["subject"], fact))
    for i, name in enumerate(v.REQUIRED_BUDGET_ARTIFACTS):
        fact = v.artifact_fact(name, m["budget_artifacts"][name])
        records.append(record(f"artifact-{i}", "BUDGET_ARTIFACT", name, fact["subject"], fact))
    bfact = v.budget_fact(m["budget"])
    records.append(record("budget", "BUDGET", "budget", v.OPPORTUNITY_ID, bfact))
    for i, item in enumerate(m["utility_participants"]):
        fact = v.utility_fact(item)
        subject = f"{fact['utility_id']}|{fact['site_id']}|{fact['role']}"
        records.append(record(f"utility-{i}", "UTILITY_CONSENT", "utility_consent", subject, fact))

    authority = {
        "schema_version": 1,
        "opportunity_id": v.OPPORTUNITY_ID,
        "authority_generation": "synthetic-ready/1",
        "source_generation": {"id": SOURCE_ID, "sha256": SOURCE_SHA, "observed_at":"2026-09-13T12:59:00Z"},
        "records": records,
    }
    return m, authority


class Tests(unittest.TestCase):
    def test_default_candidate_holds_even_with_self_claimed_pi_rule(self):
        authority = json.loads((HERE.parent / "authority_evidence.example.json").read_text())
        receipt = v.compile_readiness(copy.deepcopy(BASE), authority, NOW)
        self.assertEqual(receipt["state"], v.HOLD)
        self.assertIn("pi_owner_eligibility: missing exact retained authority", receipt["reasons"])

    def test_full_synthetic_fixture_reaches_review_ready_not_submission(self):
        m, a = ready_fixture()
        receipt = v.compile_readiness(m, a, NOW)
        self.assertEqual(receipt["state"], v.READY)
        self.assertEqual(receipt["reasons"], [])
        self.assertFalse(receipt["authority"]["carrier_may_submit"])
        self.assertFalse(receipt["authority"]["portal_mutation"])

    def test_candidate_cannot_choose_gate_set(self):
        m, a = ready_fixture()
        m["hard_gates"].pop("legal_ip_pfa_review")
        with self.assertRaisesRegex(v.ReadinessError, "immutable required gate set"):
            v.compile_readiness(m, a, NOW)

    def test_candidate_cannot_choose_deadline(self):
        m, a = ready_fixture()
        m["deadline"] = {"local":"2099-01-01T00:00:00"}
        with self.assertRaisesRegex(v.ReadinessError, "keys mismatch"):
            v.compile_readiness(m, a, NOW)

    def test_deadline_is_verifier_owned_and_expired(self):
        m, a = ready_fixture()
        receipt = v.compile_readiness(m, a, LATE)
        self.assertEqual(receipt["state"], v.HOLD)
        self.assertIn("deadline expired", receipt["reasons"])

    def test_one_sector_both_site_cannot_satisfy_multisite(self):
        m, a = ready_fixture()
        m["utility_participants"] = [{"utility_id":"utility-a", "site_id":"site-a", "role":"field-demo", "sector":"both", "status":"PROVEN"}]
        fact = v.utility_fact(m["utility_participants"][0])
        subject = f"{fact['utility_id']}|{fact['site_id']}|{fact['role']}"
        a["records"] = [r for r in a["records"] if r["kind"] != "UTILITY_CONSENT"]
        a["records"].append(record("utility-only", "UTILITY_CONSENT", "utility_consent", subject, fact))
        receipt = v.compile_readiness(m, a, NOW)
        self.assertIn("fewer than two distinct consenting utility sites", receipt["reasons"])

    def test_cross_site_consent_transplant_fails(self):
        m, a = ready_fixture()
        m["utility_participants"][0]["site_id"] = "site-x"
        receipt = v.compile_readiness(m, a, NOW)
        self.assertIn("utility 0: missing exact retained consent authority", receipt["reasons"])

    def test_cross_gate_evidence_transplant_fails(self):
        m, a = ready_fixture()
        target = next(r for r in a["records"] if r["gate"] == "computer_vision_lead")
        target["gate"] = "water_wastewater_domain_lead"
        receipt = v.compile_readiness(m, a, NOW)
        self.assertIn("computer_vision_lead: missing exact retained authority", receipt["reasons"])

    def test_cross_opportunity_authority_rejected(self):
        m, a = ready_fixture()
        a["records"][0]["opportunity_id"] = "OTHER"
        with self.assertRaisesRegex(v.ReadinessError, "cross-opportunity"):
            v.compile_readiness(m, a, NOW)

    def test_source_generation_transplant_rejected(self):
        m, a = ready_fixture()
        a["records"][0]["source_sha256"] = "b" * 64
        with self.assertRaisesRegex(v.ReadinessError, "source generation mismatch"):
            v.compile_readiness(m, a, NOW)

    def test_future_authority_rejected(self):
        m, a = ready_fixture()
        a["records"][0]["verified_at"] = "2026-09-13T14:00:01Z"
        with self.assertRaisesRegex(v.ReadinessError, "future"):
            v.compile_readiness(m, a, NOW)

    def test_contribution_floor_is_exact_integer_arithmetic(self):
        m, a = ready_fixture()
        m["budget"]["documented_eligible_contribution_usd_cents"] = 9_899_999
        receipt = v.compile_readiness(m, a, NOW)
        self.assertTrue(any("below immutable 33% floor" in x for x in receipt["reasons"]))

    def test_indirect_ceiling_is_enforced(self):
        m, a = ready_fixture()
        m["budget"]["reimbursed_indirect_usd_cents"] = 3_000_001
        receipt = v.compile_readiness(m, a, NOW)
        self.assertTrue(any("exceeds immutable 15%" in x for x in receipt["reasons"]))

    def test_budget_bool_is_not_integer(self):
        m, a = ready_fixture()
        m["budget"]["wrf_request_usd_cents"] = True
        with self.assertRaisesRegex(v.ReadinessError, "nonnegative integer"):
            v.compile_readiness(m, a, NOW)

    def test_budget_workbook_requires_retained_authority(self):
        m, a = ready_fixture()
        a["records"] = [r for r in a["records"] if r["gate"] != "budget_workbook"]
        receipt = v.compile_readiness(m, a, NOW)
        self.assertIn("budget_workbook: missing exact retained authority", receipt["reasons"])

    def test_candidate_cannot_enable_submission_authority(self):
        m, a = ready_fixture()
        m["submission_authority"]["carrier_may_submit"] = True
        with self.assertRaisesRegex(v.ReadinessError, "hard false"):
            v.compile_readiness(m, a, NOW)

    def test_duplicate_evidence_id_rejected(self):
        m, a = ready_fixture()
        a["records"][1]["evidence_id"] = a["records"][0]["evidence_id"]
        with self.assertRaisesRegex(v.ReadinessError, "duplicate evidence_id"):
            v.compile_readiness(m, a, NOW)

    def test_receipt_tamper_and_current_drift_fail(self):
        m, a = ready_fixture()
        receipt = v.compile_readiness(m, a, NOW)
        ok, reasons = v.verify_receipt(receipt, m, a, NOW)
        self.assertTrue(ok, reasons)
        bad = copy.deepcopy(receipt); bad["state"] = v.HOLD
        self.assertFalse(v.verify_receipt(bad, m, a, NOW)[0])
        self.assertFalse(v.verify_receipt(receipt, m, a, LATE)[0])

    def test_strict_json_rejects_duplicate_keys_float_and_nonfinite(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":1.5}', b'{"a":NaN}'):
            with self.subTest(raw=raw):
                with self.assertRaises(v.ReadinessError):
                    v.strict_json_bytes(raw)

    def test_strict_json_rejects_oversized_integer(self):
        with self.assertRaisesRegex(v.ReadinessError, "integer token too large"):
            v.strict_json_bytes(b'{"a":1234567890123456789}')

    def test_regular_file_ingress_rejects_symlink(self):
        if not hasattr(os, "O_NOFOLLOW"):
            self.skipTest("platform lacks O_NOFOLLOW")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "target.json"
            link = Path(td) / "link.json"
            target.write_text("{}")
            link.symlink_to(target)
            with self.assertRaises(v.ReadinessError):
                v.load_strict_file(link)


if __name__ == "__main__":
    unittest.main()
