from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INTAKE = ROOT / "agent-autopsy-intake.html"
PRODUCT = ROOT / "agent-rescue.html"
CHECKOUT = "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g"
RECEIPT = ROOT / "p" / "sol-profit-agent-autopsy-intake-builder-20260909-01.md"


class AgentAutopsyIntakeContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.intake = INTAKE.read_text(encoding="utf-8")
        cls.product = PRODUCT.read_text(encoding="utf-8")

    def test_product_links_to_local_intake_builder_once(self) -> None:
        self.assertEqual(self.product.count('href="./agent-autopsy-intake.html"'), 1)
        self.assertIn("Build a sanitized case brief locally", self.product)

    def test_intake_keeps_existing_product_and_checkout_truth(self) -> None:
        self.assertIn("Agent Failure Autopsy", self.intake)
        self.assertIn("$29 once · one business day", self.intake)
        self.assertEqual(self.intake.count(CHECKOUT), 1)
        self.assertIn('href="./agent-rescue.html"', self.intake)
        self.assertIn("utm_medium=intake_tool", self.intake)
        self.assertIn("utm_campaign=agent_failure_autopsy_29", self.intake)

    def test_local_only_boundary_is_structural(self) -> None:
        lower = self.intake.lower()
        self.assertIn("connect-src 'none'", lower)
        self.assertIn("form-action 'none'", lower)
        self.assertNotIn("<form", lower)
        self.assertNotIn("fetch(", lower)
        self.assertNotIn("xmlhttprequest", lower)
        self.assertNotIn("sendbeacon", lower)
        self.assertNotIn("localstorage", lower)
        self.assertNotIn("sessionstorage", lower)
        self.assertNotIn("document.cookie", lower)
        self.assertNotRegex(lower, r"<script\s+[^>]*src=")

    def test_redaction_gate_and_single_run_scope_are_explicit(self) -> None:
        for phrase in (
            "API keys, tokens, passwords",
            "customer data, PII, and PHI",
            "private URLs, hostnames, IDs",
            "one failed execution of one agent workflow",
        ):
            self.assertIn(phrase, self.intake)
        self.assertEqual(self.intake.count("data-redaction"), 5)  # four inputs + selector
        self.assertIn("build.disabled=!ready()", self.intake)

    def test_case_brief_captures_failure_chain_inputs(self) -> None:
        for field_id in (
            "intended",
            "observed",
            "stack",
            "error",
            "last-good",
            "effects",
            "state",
            "changed",
            "evidence",
        ):
            self.assertRegex(self.intake, rf'id="{re.escape(field_id)}"')
        for heading in (
            "INTENDED OUTCOME",
            "OBSERVED FAILURE",
            "FIRST VISIBLE ERROR OR DIVERGENCE",
            "RETRIES AND SIDE EFFECTS",
            "STATE AND RESUME BEHAVIOR",
            "REDACTION CONFIRMATION",
        ):
            self.assertIn(heading, self.intake)

    def test_copy_is_user_initiated_with_nonclipboard_fallback(self) -> None:
        self.assertIn('id="copy" type="button" disabled', self.intake)
        self.assertIn("navigator.clipboard.writeText", self.intake)
        self.assertIn("brief.select()", self.intake)
        self.assertIn('aria-live="polite"', self.intake)

    def test_receipt_pins_preimage_and_scope(self) -> None:
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("d33aa5dace32ad554b6d065750d5c183c29a844d", receipt)
        self.assertIn("no new Stripe product, price, or Payment Link", receipt)
        self.assertIn("connect-src 'none'", receipt)
        self.assertIn("#8802", receipt)


if __name__ == "__main__":
    unittest.main()
