#!/usr/bin/env python3
"""Keep the public $29 Agent Failure Autopsy bounded, purchasable, and safely attributable."""
import html
import json
import re
import subprocess
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "agent-rescue.html"
OLD_CHECKOUT_URL = "https://buy.stripe.com/8x25kC3Ot9fj5ep1Oy43S0a"
CHECKOUT_URL = "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g"
ALLOWED_UTM = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
}


class AgentFailureDiagnosticPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.lower = cls.page.lower()

    def _checkout_hrefs(self):
        values = re.findall(
            r'href="(https://buy\.stripe\.com/[A-Za-z0-9]+(?:\?[^"]*)?)"',
            self.page,
        )
        return [html.unescape(value) for value in values]

    def test_offer_is_the_29_diagnostic_not_a_proof_product(self):
        self.assertIn("<title>Agent Failure Autopsy — $29, one business day</title>", self.page)
        self.assertIn("Your coding agent failed. Find out why for $29.", self.page)
        self.assertIn("$29 · one business day", self.page)
        self.assertIn("for indie developers, automation builders, and small AI teams paying to run coding agents", self.page)
        self.assertNotIn("Same-Day Agent Survival Proof", self.page)
        self.assertNotIn("working recovery proof", self.lower)
        self.assertNotIn("Authorize one proof", self.page)

    def test_intake_and_one_clarification_round_are_explicit(self):
        for marker in (
            "One failed execution of one agent workflow.",
            "One sentence: what the agent should do, and what failed.",
            "The stack, framework, or harness name.",
            "One redacted log, transcript, or screenshot",
            "One clarification round is included",
            "delivery clock starts once usable redacted evidence is within the intake cap",
        ):
            self.assertIn(marker, self.page)

    def test_intake_cap_is_deterministic_and_quality_neutral(self):
        for marker in (
            "2,000,000 extracted Unicode characters (roughly 500,000 text tokens)",
            "10 files",
            "25,000,000 raw bytes total",
            "whichever limit is reached first",
            "No archives, executables, repository dumps, or unrelated incidents.",
            "we help you select the relevant slice",
            "This limits intake, not the quality of the diagnosis.",
            "legitimate case cannot be brought within the cap",
        ):
            self.assertIn(marker, self.page)

    def test_delivery_is_evidence_bounded_and_diagnostic_only(self):
        for marker in (
            "failure chain tied to the evidence",
            "Primary and contributing causes, with uncertainty stated.",
            "Concrete fix steps for prompt, configuration, or code only where the evidence supports them.",
            "A replay, regression, or prevention check with the expected result.",
            "cannot deliver a defensible diagnosis within one business day after the clock starts, the $29 is refunded",
            "cannot support a defensible diagnosis after that clarification, the $29 is refunded",
            "does not include repository access, production access, code implementation",
            "No diagnosis is presented as certain beyond the supplied evidence.",
        ):
            self.assertIn(marker, self.page)

    def test_verified_checkout_is_exposed_with_safe_static_attribution(self):
        self.assertNotIn(OLD_CHECKOUT_URL, self.page)
        hrefs = self._checkout_hrefs()
        self.assertEqual(len(hrefs), 2)
        seen_content = set()
        for href in hrefs:
            parsed = urlsplit(href)
            self.assertEqual(
                f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                CHECKOUT_URL,
            )
            params = parse_qs(parsed.query, strict_parsing=True)
            self.assertEqual(
                set(params),
                {"utm_source", "utm_medium", "utm_campaign", "utm_content"},
            )
            self.assertEqual(params["utm_source"], ["commons"])
            self.assertEqual(params["utm_medium"], ["website"])
            self.assertEqual(params["utm_campaign"], ["agent_failure_autopsy_29"])
            seen_content.add(params["utm_content"][0])
            for values in params.values():
                for value in values:
                    self.assertRegex(value, r"^[A-Za-z0-9_-]{1,60}$")
        self.assertEqual(seen_content, {"hero", "boundary"})
        self.assertNotIn("checkout button will appear only after", self.lower)
        self.assertIn("secure one-time stripe checkout", self.lower)

    def _runtime_checkout_hrefs(self, incoming):
        script_match = re.search(r"<script>([\s\S]*?)</script>", self.page)
        self.assertIsNotNone(script_match)
        script = script_match.group(1)
        hrefs = self._checkout_hrefs()
        harness = (
            "const vm=require('vm');"
            f"const code={json.dumps(script)};"
            f"const hrefs={json.dumps(hrefs)};"
            f"const search={json.dumps(incoming)};"
            "const links=hrefs.map(href=>({href,"
            "getAttribute(){return this.href},"
            "setAttribute(_key,value){this.href=value}}));"
            "const context={location:{search},"
            "document:{querySelectorAll(selector){"
            "if(selector!=='a[data-checkout]')throw new Error(selector);"
            "return links;}},URL,URLSearchParams,String};"
            "vm.runInNewContext(code,context);"
            "process.stdout.write(JSON.stringify(links.map(link=>link.href)));"
        )
        completed = subprocess.run(
            ["node", "-e", harness],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(completed.stdout)

    def test_runtime_attribution_is_allowlisted_and_ignores_failure_text(self):
        runtime_hrefs = self._runtime_checkout_hrefs(
            "?utm_source=x&utm_medium=paid_social&utm_campaign=agent_failure"
            "&utm_term=retry-bomb&utm_content=creative_1"
            "&failure_sentence=SHOULD_NOT_LEAK"
        )
        self.assertEqual(len(runtime_hrefs), 2)
        for href in runtime_hrefs:
            self.assertNotIn("SHOULD_NOT_LEAK", href)
            params = parse_qs(urlsplit(href).query, strict_parsing=True)
            self.assertEqual(set(params), ALLOWED_UTM)
            self.assertEqual(params["utm_source"], ["x"])
            self.assertEqual(params["utm_medium"], ["paid_social"])
            self.assertEqual(params["utm_campaign"], ["agent_failure"])
            self.assertEqual(params["utm_term"], ["retry-bomb"])
            self.assertEqual(params["utm_content"], ["creative_1"])
        self.assertIn('replace(/[^A-Za-z0-9_-]/g,"").slice(0,60)', self.page)

    def test_exact_x_campaign_gets_fixed_checkout_reference(self):
        hrefs = self._runtime_checkout_hrefs(
            "?utm_source=x&utm_medium=paid_social&utm_campaign=agent_failure_autopsy_29"
            "&utm_term=retry-bomb&utm_content=creative_1"
            "&client_reference_id=SHOULD_NOT_LEAK&email=SHOULD_NOT_LEAK"
            "&evidence_url=SHOULD_NOT_LEAK&failure_sentence=SHOULD_NOT_LEAK"
        )
        self.assertEqual(len(hrefs), 2)
        for href in hrefs:
            self.assertNotIn("SHOULD_NOT_LEAK", href)
            parsed = urlsplit(href)
            self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", CHECKOUT_URL)
            params = parse_qs(parsed.query, strict_parsing=True)
            self.assertEqual(set(params), ALLOWED_UTM | {"client_reference_id"})
            self.assertEqual(params["client_reference_id"], ["afa29_x_a_v1"])
            self.assertEqual(params["utm_source"], ["x"])
            self.assertEqual(params["utm_medium"], ["paid_social"])
            self.assertEqual(params["utm_campaign"], ["agent_failure_autopsy_29"])
            self.assertEqual(params["utm_term"], ["retry-bomb"])
            self.assertEqual(params["utm_content"], ["creative_1"])

    def test_other_and_ambiguous_traffic_never_inherits_x_reference(self):
        exact = "utm_source=x&utm_medium=paid_social&utm_campaign=agent_failure_autopsy_29"
        for incoming in (
            "",
            "?client_reference_id=afa29_x_a_v1",
            "?" + exact.replace("utm_source=x", "utm_source=commons"),
            "?" + exact.replace("paid_social", "referral"),
            "?" + exact.replace("agent_failure_autopsy_29", "another_campaign"),
            "?utm_source=x&utm_medium=paid_social",
            "?" + exact.replace("utm_source=x", "utm_source=x%21"),
            "?" + exact + "&utm_source=another_source",
        ):
            with self.subTest(incoming=incoming):
                for href in self._runtime_checkout_hrefs(incoming + "&client_reference_id=UNTRUSTED"):
                    params = parse_qs(urlsplit(href).query, strict_parsing=True)
                    self.assertLessEqual(set(params), ALLOWED_UTM)
                    self.assertNotIn("client_reference_id", params)
                    self.assertNotIn("UNTRUSTED", href)

    def test_page_does_not_solicit_or_expose_secret_material(self):
        for marker in ("API keys", "tokens", "passwords", "customer records", "production secrets"):
            self.assertIn(marker, self.page)
        self.assertIsNone(re.search(r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{12,}", self.page))


if __name__ == "__main__":
    unittest.main()
