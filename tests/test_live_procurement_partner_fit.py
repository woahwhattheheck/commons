from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from revenue.live_procurement_partner_fit import QualificationError, canonical_json, compile_partner_fit, verify_receipt

NOW = datetime(2026, 9, 16, 22, 30, 0, tzinfo=timezone.utc)


def valid_payload():
    return {
        "opportunity": {
            "opportunity_id": "PROC-2026-001",
            "buyer": "Example Public Buyer",
            "source_url": "https://buyer.example/proc/001",
            "observed_at": "2026-09-16T21:00:00Z",
            "submission_deadline_at": "2026-09-30T21:00:00Z",
            "delivery_start_at": "2026-11-15T14:00:00Z",
        },
        "workshare": {
            "source_repository": "woahwhattheheck/commons",
            "source_path": "revenue/example/TEAMING_WORKSHARE.md",
            "source_commit": "a" * 40,
            "landed": True,
            "commercial_state": "PROPOSED_NOT_ACCEPTED",
            "role_statement": "Paid fixed-fee specialist subcontract/workshare; not staffing; not recruiting; not platform replacement.",
            "deliverables": ["Migration reconciliation", "UAT evidence"],
            "acceptance_criteria": ["Deterministic receipt", "Exception ledger"],
        },
        "partner_fit": {
            "organization": "Example Integrator",
            "evidence_url": "https://partner.example/public-sector",
            "observed_at": "2026-09-16T20:00:00Z",
            "fit_statement": "First-party page shows public-sector integration services.",
        },
        "delivery_runway": {
            "minimum_lead_days": 42,
            "evidence_url": "https://partner.example/delivery",
            "observed_at": "2026-09-16T20:00:00Z",
        },
        "route": {
            "organization": "Example Integrator",
            "route": "Teaming@Partner.Example",
            "kind": "email",
            "evidence_url": "https://partner.example/contact",
            "observed_at": "2026-09-16T20:00:00Z",
            "provenance": "FIRST_PARTY_CURRENT",
            "state": "CLEAR",
        },
        "collision": {
            "buyer": "Example Public Buyer",
            "opportunity_id": "PROC-2026-001",
            "organization": "Example Integrator",
            "route": "Teaming@Partner.Example",
            "purpose": "paid procurement workshare qualification",
            "state": "CLEAR",
            "observed_at": "2026-09-16T22:00:00Z",
            "evidence_refs": ["slack:census:1", "gmail:census:1"],
        },
    }


class PartnerFitTests(unittest.TestCase):
    def test_ready_receipt_is_authority_negative(self):
        receipt = compile_partner_fit(valid_payload(), now=NOW)
        self.assertEqual(receipt["status"], "READY_FOR_MUSE")
        self.assertEqual(receipt["reasons"], [])
        self.assertEqual(receipt["muse_handoff"]["state"], "PREPARED_NOT_REQUESTED")
        self.assertTrue(receipt["muse_handoff"]["publication_key"].startswith("lp-partner-fit:"))
        self.assertTrue(all(value is False for value in receipt["authority"].values()))
        self.assertEqual(receipt["muse_handoff"]["candidate"]["route"], "teaming@partner.example")
        self.assertTrue(verify_receipt(valid_payload(), receipt, now=NOW))

    def test_deterministic_across_mapping_order(self):
        first = valid_payload()
        second = {key: first[key] for key in reversed(list(first))}
        self.assertEqual(compile_partner_fit(first, now=NOW), compile_partner_fit(second, now=NOW))

    def test_tampered_receipt_fails_verify(self):
        receipt = compile_partner_fit(valid_payload(), now=NOW)
        receipt["status"] = "HOLD"
        self.assertFalse(verify_receipt(valid_payload(), receipt, now=NOW))

    def test_stale_route_holds(self):
        payload = valid_payload(); payload["route"]["observed_at"] = "2026-08-01T00:00:00Z"
        receipt = compile_partner_fit(payload, now=NOW)
        self.assertEqual(receipt["status"], "HOLD")
        self.assertIn("ROUTE_EVIDENCE_STALE", receipt["reasons"])

    def test_future_observation_holds(self):
        payload = valid_payload(); payload["partner_fit"]["observed_at"] = "2026-09-17T00:00:00Z"
        self.assertIn("PARTNER_FIT_FUTURE_OBSERVATION", compile_partner_fit(payload, now=NOW)["reasons"])

    def test_expired_deadline_holds(self):
        payload = valid_payload(); payload["opportunity"]["submission_deadline_at"] = "2026-09-15T00:00:00Z"
        self.assertIn("OPPORTUNITY_DEADLINE_CLOSED", compile_partner_fit(payload, now=NOW)["reasons"])

    def test_past_delivery_start_holds(self):
        payload = valid_payload(); payload["opportunity"]["delivery_start_at"] = "2026-09-15T00:00:00Z"
        self.assertIn("DELIVERY_START_CLOSED", compile_partner_fit(payload, now=NOW)["reasons"])

    def test_insufficient_runway_holds(self):
        payload = valid_payload(); payload["delivery_runway"]["minimum_lead_days"] = 61
        self.assertIn("INSUFFICIENT_DELIVERY_RUNWAY", compile_partner_fit(payload, now=NOW)["reasons"])

    def test_zero_lead_allowed(self):
        payload = valid_payload(); payload["delivery_runway"]["minimum_lead_days"] = 0
        self.assertEqual(compile_partner_fit(payload, now=NOW)["status"], "READY_FOR_MUSE")

    def test_bool_lead_time_rejected(self):
        payload = valid_payload(); payload["delivery_runway"]["minimum_lead_days"] = True
        with self.assertRaises(QualificationError): compile_partner_fit(payload, now=NOW)

    def test_workshare_must_be_landed(self):
        payload = valid_payload(); payload["workshare"]["landed"] = False
        self.assertIn("WORKSHARE_NOT_LANDED", compile_partner_fit(payload, now=NOW)["reasons"])

    def test_commercial_state_exact(self):
        payload = valid_payload(); payload["workshare"]["commercial_state"] = "ACCEPTED"
        self.assertIn("WORKSHARE_COMMERCIAL_STATE_UNSUPPORTED", compile_partner_fit(payload, now=NOW)["reasons"])

    def test_every_required_role_clause(self):
        cases = [
            ("Paid ", "ROLE_CLARITY_PAID_MISSING"),
            ("fixed-fee ", "ROLE_CLARITY_FIXED_FEE_MISSING"),
            ("subcontract/workshare; ", "ROLE_CLARITY_WORKSHARE_MISSING"),
            ("not staffing; ", "ROLE_CLARITY_NOT_STAFFING_MISSING"),
            ("not recruiting; ", "ROLE_CLARITY_NOT_RECRUITING_MISSING"),
            ("not platform replacement.", "ROLE_CLARITY_NOT_PLATFORM_REPLACEMENT_MISSING"),
        ]
        original = valid_payload()["workshare"]["role_statement"]
        for removed, expected in cases:
            with self.subTest(expected=expected):
                payload = valid_payload(); payload["workshare"]["role_statement"] = original.replace(removed, "")
                self.assertIn(expected, compile_partner_fit(payload, now=NOW)["reasons"])

    def test_route_organization_binding_holds(self):
        payload = valid_payload(); payload["route"]["organization"] = "Other Integrator"
        self.assertIn("ROUTE_ORGANIZATION_MISMATCH", compile_partner_fit(payload, now=NOW)["reasons"])

    def test_collision_identity_bindings_hold(self):
        cases = [
            ("buyer", "Other Buyer", "COLLISION_BUYER_MISMATCH"),
            ("opportunity_id", "OTHER-001", "COLLISION_OPPORTUNITY_MISMATCH"),
            ("organization", "Other Integrator", "COLLISION_ORGANIZATION_MISMATCH"),
            ("route", "other@partner.example", "COLLISION_ROUTE_MISMATCH"),
        ]
        for field, value, reason in cases:
            with self.subTest(field=field):
                payload = valid_payload(); payload["collision"][field] = value
                self.assertIn(reason, compile_partner_fit(payload, now=NOW)["reasons"])

    def test_contact_form_and_phone_routes_are_validated(self):
        payload = valid_payload()
        payload["route"].update({"kind": "contact_form", "route": "https://partner.example/contact/form"})
        payload["collision"]["route"] = "https://partner.example/contact/form"
        self.assertEqual(compile_partner_fit(payload, now=NOW)["status"], "READY_FOR_MUSE")
        payload = valid_payload(); payload["route"].update({"kind": "phone", "route": "+1 (555) 010-2200"}); payload["collision"]["route"] = "+1 (555) 010-2200"
        self.assertEqual(compile_partner_fit(payload, now=NOW)["status"], "READY_FOR_MUSE")
        payload["route"]["route"] = "call-me-maybe"
        with self.assertRaises(QualificationError): compile_partner_fit(payload, now=NOW)

    def test_route_provenance_fail_closed(self):
        payload = valid_payload(); payload["route"]["provenance"] = "HISTORICAL_PUBLIC_DOC"
        self.assertIn("ROUTE_PROVENANCE_NOT_CURRENT_FIRST_PARTY", compile_partner_fit(payload, now=NOW)["reasons"])

    def test_route_states_fail_closed(self):
        for state in ("DEAD_ROUTE", "TEMP_DELAY", "UNKNOWN", "PROVIDER_RETRY"):
            with self.subTest(state=state):
                payload = valid_payload(); payload["route"]["state"] = state
                receipt = compile_partner_fit(payload, now=NOW)
                self.assertEqual(receipt["status"], "HOLD")
                self.assertIn(f"ROUTE_STATE_{state}", receipt["reasons"])

    def test_collision_states_fail_closed(self):
        for state in ("DNR", "SENT", "AWAITING_REPLY", "UNKNOWN", "HOLD"):
            with self.subTest(state=state):
                payload = valid_payload(); payload["collision"]["state"] = state
                receipt = compile_partner_fit(payload, now=NOW)
                self.assertEqual(receipt["status"], "HOLD")
                self.assertIn(f"COLLISION_STATE_{state}", receipt["reasons"])

    def test_collision_census_staleness_holds(self):
        payload = valid_payload(); payload["collision"]["observed_at"] = "2026-09-16T17:00:00Z"
        self.assertIn("COLLISION_EVIDENCE_STALE", compile_partner_fit(payload, now=NOW)["reasons"])

    def test_unknown_fields_rejected(self):
        payload = valid_payload(); payload["route"]["send_now"] = True
        with self.assertRaises(QualificationError): compile_partner_fit(payload, now=NOW)

    def test_missing_fields_rejected(self):
        payload = valid_payload(); del payload["collision"]["evidence_refs"]
        with self.assertRaises(QualificationError): compile_partner_fit(payload, now=NOW)

    def test_duplicate_evidence_rejected(self):
        payload = valid_payload(); payload["collision"]["evidence_refs"] = ["same", "SAME"]
        with self.assertRaises(QualificationError): compile_partner_fit(payload, now=NOW)

    def test_float_and_nonfinite_rejected(self):
        payload = valid_payload(); payload["delivery_runway"]["minimum_lead_days"] = 1.0
        with self.assertRaises(QualificationError): compile_partner_fit(payload, now=NOW)
        with self.assertRaises(QualificationError): canonical_json({"x": float("nan")})

    def test_bad_commit_rejected(self):
        payload = valid_payload(); payload["workshare"]["source_commit"] = "main"
        with self.assertRaises(QualificationError): compile_partner_fit(payload, now=NOW)

    def test_bad_url_rejected(self):
        payload = valid_payload(); payload["route"]["evidence_url"] = "http://partner.example/contact"
        with self.assertRaises(QualificationError): compile_partner_fit(payload, now=NOW)

    def test_url_credentials_rejected(self):
        payload = valid_payload(); payload["partner_fit"]["evidence_url"] = "https://u:p@partner.example/a"
        with self.assertRaises(QualificationError): compile_partner_fit(payload, now=NOW)

    def test_naive_timestamps_rejected(self):
        payload = valid_payload(); payload["route"]["observed_at"] = "2026-09-16T20:00:00"
        with self.assertRaises(QualificationError): compile_partner_fit(payload, now=NOW)

    def test_empty_deliverables_rejected(self):
        payload = valid_payload(); payload["workshare"]["deliverables"] = []
        with self.assertRaises(QualificationError): compile_partner_fit(payload, now=NOW)

    def test_cli_compile_verify_and_nonfinite_rejection(self):
        payload = valid_payload()
        with tempfile.TemporaryDirectory() as td_raw:
            td = Path(td_raw); inp = td / "candidate.json"; rec = td / "receipt.json"
            inp.write_text(json.dumps(payload), encoding="utf-8")
            env = dict(os.environ); repo_root = str(Path(__file__).resolve().parents[1]); env["PYTHONPATH"] = repo_root + os.pathsep + env.get("PYTHONPATH", "")
            compile_run = subprocess.run([sys.executable, "-m", "revenue.live_procurement_partner_fit", "compile", "--input", str(inp), "--now", "2026-09-16T22:30:00Z"], cwd=repo_root, env=env, check=True, capture_output=True, text=True)
            rec.write_text(compile_run.stdout, encoding="utf-8")
            verify_run = subprocess.run([sys.executable, "-m", "revenue.live_procurement_partner_fit", "verify", "--input", str(inp), "--receipt", str(rec), "--now", "2026-09-16T22:30:00Z"], cwd=repo_root, env=env, capture_output=True, text=True)
            self.assertEqual(verify_run.returncode, 0, verify_run.stderr)
            self.assertEqual(json.loads(verify_run.stdout), {"verified": True})
            bad = td / "bad.json"; bad.write_text('{"x":NaN}', encoding="utf-8")
            bad_run = subprocess.run([sys.executable, "-m", "revenue.live_procurement_partner_fit", "compile", "--input", str(bad), "--now", "2026-09-16T22:30:00Z"], cwd=repo_root, env=env, capture_output=True, text=True)
            self.assertEqual(bad_run.returncode, 2)


if __name__ == "__main__":
    unittest.main()
