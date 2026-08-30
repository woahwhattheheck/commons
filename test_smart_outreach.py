from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("smart_outreach", ROOT / "host" / "smart_outreach.py")
assert SPEC and SPEC.loader
smart = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smart)


def qualified_prospect() -> dict:
    return {
        "prospect_id": "qualified-example",
        "organization": "Qualified Example",
        "recipient_email": "owner@example.test",
        "evidence": {
            "source_url": "https://example.test/production",
            "observed_at": "2026-08-27T00:00:00Z",
            "exact_quote": "A production timeout needs idempotent recovery, replay, and an exact audit trace.",
        },
        "owner_role": "agent platform owner",
        "route": {"kind": "EMAIL", "value": "owner@example.test", "state": "VERIFIED"},
        "proof_hypothesis": "Can one timeout recover idempotently and leave an exact replay receipt?",
        "occupied_by": None,
        "do_not_contact": False,
        "disqualifiers": [],
    }


def input_with(*prospects: dict) -> dict:
    base = smart.read_object(smart.DEFAULT_INPUT)
    base["prospects"] = list(prospects)
    return base


class SmartOutreachTests(unittest.TestCase):
    def test_checked_in_cohort_holds_collisions_and_requires_research(self) -> None:
        plan = smart.build_plan(smart.read_object(smart.DEFAULT_INPUT))
        decisions = {item["prospect_id"]: item["decision"] for item in plan["items"]}
        self.assertEqual(decisions["anythingllm-mintplex"], "HOLD_DO_NOT_RESEND")
        self.assertEqual(decisions["metaforms"], "HOLD_DO_NOT_RESEND")
        self.assertEqual(decisions["signoz"], "RESEARCH_REQUIRED")
        self.assertEqual(decisions["composio"], "READY_TO_DRAFT")
        composio = next(item for item in plan["items"] if item["prospect_id"] == "composio")
        self.assertEqual(composio["recipient_email"], "support@composio.dev")
        self.assertEqual(composio["score"], 85)
        self.assertIn("sending the same email twice", composio["draft"]["body"])
        self.assertEqual(plan["truth"]["drafts_created"], 1)
        self.assertEqual(plan["truth"]["transport_actions"], 0)
        self.assertEqual(plan["truth"]["cash_usd"], 0)

    def test_recipient_or_organization_receipt_collision_holds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = {
                "organization": "Qualified Example",
                "recipient_email": "different@example.test",
                "dedupe": {"do_not_resend": True},
            }
            Path(directory, "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
            plan = smart.build_plan(input_with(qualified_prospect()), Path(directory))
        self.assertEqual(plan["items"][0]["decision"], "HOLD_DO_NOT_RESEND")
        self.assertEqual(plan["items"][0]["collision_receipts"], ["receipt.json"])
        self.assertIsNone(plan["items"][0]["draft"])

    def test_qualified_prospect_gets_one_evidence_bound_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plan = smart.build_plan(input_with(qualified_prospect()), Path(directory))
        item = plan["items"][0]
        self.assertEqual(item["decision"], "READY_TO_DRAFT")
        self.assertEqual(item["score"], 100)
        body = item["draft"]["body"]
        self.assertIn(qualified_prospect()["evidence"]["exact_quote"], body)
        self.assertIn("$2,500", body)
        self.assertIn("opt out", body)
        self.assertNotIn("$15,000", body)
        self.assertEqual(plan["truth"]["transport_actions"], 0)

    def test_missing_route_or_owner_never_drafts(self) -> None:
        prospect = qualified_prospect()
        prospect["owner_role"] = None
        prospect["route"] = {"kind": "FIRST_PARTY_ROUTE", "value": None, "state": "UNVERIFIED"}
        with tempfile.TemporaryDirectory() as directory:
            item = smart.build_plan(input_with(prospect), Path(directory))["items"][0]
        self.assertEqual(item["decision"], "RESEARCH_REQUIRED")
        self.assertIn("a relevant owner role", item["missing"])
        self.assertIn("a verified first-party route", item["missing"])
        self.assertIsNone(item["draft"])

    def test_duplicate_ids_and_unknown_fields_fail_closed(self) -> None:
        prospect = qualified_prospect()
        with self.assertRaises(smart.OutreachError):
            smart.validate_input(input_with(prospect, copy.deepcopy(prospect)))
        invalid = input_with(prospect)
        invalid["prospects"][0]["send_now"] = True
        with self.assertRaises(smart.OutreachError):
            smart.validate_input(invalid)

    def test_cli_is_deterministic_and_reports_zero_transport(self) -> None:
        command = [sys.executable, str(ROOT / "host" / "smart_outreach.py"), "plan"]
        first = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout
        second = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout
        self.assertEqual(first, second)
        parsed = json.loads(first)
        self.assertEqual(parsed["truth"]["transport_actions"], 0)
        validate = subprocess.run(
            [sys.executable, str(ROOT / "host" / "smart_outreach.py"), "validate"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertEqual(validate.strip(), "VALID 4 prospects 1 drafts 0 transport actions")


if __name__ == "__main__":
    unittest.main()
