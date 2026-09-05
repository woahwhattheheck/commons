#!/usr/bin/env python3
"""Keep the public $29 agent-failure diagnostic focused, bounded, and unchargeable until checkout exists."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "agent-rescue.html"
OLD_CHECKOUT_URL = "https://buy.stripe.com/8x25kC3Ot9fj5ep1Oy43S0a"


class AgentFailureDiagnosticPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.lower = cls.page.lower()

    def test_offer_is_the_29_diagnostic_not_a_proof_product(self):
        self.assertIn("One failed agent run. Find out what broke.", self.page)
        self.assertIn("$29 · one business day", self.page)
        self.assertIn("for indie developers, automation builders, and small AI teams", self.page)
        self.assertNotIn("Same-Day Agent Survival Proof", self.page)
        self.assertNotIn("working recovery proof", self.lower)
        self.assertNotIn("Authorize one proof", self.page)

    def test_intake_and_one_clarification_round_are_explicit(self):
        for marker in (
            "One sentence: what the agent should do, and what failed.",
            "The stack, framework, or harness name.",
            "One redacted log, transcript, or screenshot",
            "One clarification round is included",
            "delivery clock starts when usable redacted evidence arrives",
        ):
            self.assertIn(marker, self.page)

    def test_delivery_is_evidence_bounded_and_diagnostic_only(self):
        for marker in (
            "failure chain tied to the evidence",
            "Primary and contributing causes, with uncertainty stated.",
            "Concrete fix steps for prompt, configuration, or code only where the evidence supports them.",
            "A replay, regression, or prevention check with the expected result.",
            "cannot support a defensible diagnosis after that clarification, the $29 is refunded",
            "does not include repository access, production access, code implementation",
            "No diagnosis is presented as certain beyond the supplied evidence.",
        ):
            self.assertIn(marker, self.page)

    def test_unverified_checkout_is_not_exposed(self):
        self.assertNotIn(OLD_CHECKOUT_URL, self.page)
        self.assertIsNone(re.search(r"https://(?:buy|donate)\.stripe\.com/[A-Za-z0-9]+", self.page))
        self.assertIn("checkout button will appear only after a live $29 payment link is created and verified", self.lower)
        self.assertIn("this page requests no payment", self.lower)

    def test_email_intake_keeps_campaign_attribution(self):
        subject = "subject=AI%20Agent%20Failure%20Diagnostic"
        self.assertEqual(self.page.count('href="mailto:tokenjunkielabs@gmail.com?' + subject), 2)
        for marker in ('p.get("utm_source")', 'p.get("utm_campaign")', 'p.get("utm_content")', "%5Bvia%20"):
            self.assertIn(marker, self.page)

    def test_page_does_not_solicit_or_expose_secret_material(self):
        for marker in ("API keys", "tokens", "passwords", "customer records", "production secrets"):
            self.assertIn(marker, self.page)
        self.assertIsNone(re.search(r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{12,}", self.page))


if __name__ == "__main__":
    unittest.main()
