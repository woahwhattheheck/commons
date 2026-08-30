#!/usr/bin/env python3
"""Canonical Commons instructions require agent credential execution without a public gate."""

from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parent
CANONICAL_DOCS = (
    "AGENTS.md",
    "START.md",
    "ground/LAND.md",
    "ground/NEEDS_BRYCE.md",
    "ground/STRIPE.md",
    "ground/PAY.md",
    "ground/CASH_NOW.md",
    "revenue/payment_ready/rails.md",
    "revenue/payment_ready/private_input_manifest.md",
    "revenue/payment_ready/README.md",
    "revenue/human_outcomes/sales_ops/README.md",
)
RETIRED_RULES = (
    "agents do not collect banking",
    "agents do not collect banking information",
    "real credential/permission wall requires the operator",
    "owner-only step: complete verification",
    "owner-only step: confirm the account",
    "only the owner can complete provider onboarding",
)


class AgentCredentialHandlingContract(unittest.TestCase):
    def test_canonical_docs_do_not_reserve_credential_work_to_owner(self):
        for rel in CANONICAL_DOCS:
            body = (ROOT / rel).read_text(encoding="utf-8").lower()
            for retired in RETIRED_RULES:
                self.assertNotIn(retired, body, f"{rel}: {retired}")

    def test_stripe_contract_requires_private_agent_execution_and_open_door(self):
        body = (ROOT / "ground/STRIPE.md").read_text(encoding="utf-8").lower()
        for phrase in (
            "agents perform the necessary stripe work",
            "authorized private connector",
            "never copy\nsecret values",
            "public commons remains no-auth",
            "no credential may become an admission gate",
        ):
            self.assertIn(phrase, body)

    def test_start_does_not_stop_at_credentials(self):
        body = (ROOT / "START.md").read_text(encoding="utf-8").lower()
        self.assertIn("credential handling is part of the work", body)
        self.assertIn("every available authorized execution road", body)

    def test_machine_readable_cash_route_assigns_private_work_to_agent(self):
        data = json.loads((ROOT / "ground/CASH_NOW.json").read_text(encoding="utf-8"))
        route = data["needs_bryce"]
        self.assertIn("credential handling itself is agent work", route["why_only_bryce"])
        self.assertIn("an agent uses an authorized private", route["smallest_action"])


if __name__ == "__main__":
    unittest.main()
