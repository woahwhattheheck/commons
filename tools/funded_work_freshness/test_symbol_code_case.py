from __future__ import annotations

import unittest

from funded_work_freshness import Candidate, preflight
from test_support import NOW, FakeTransport, evidence_routes, open_issue


GH = "https://github.com/acme/widget/issues/12"
STAMP = "2026-09-13T04:00:00Z"


def authority_comment(body: str):
    return {
        "body": body,
        "user": {"login": "maintainer"},
        "author_association": "OWNER",
        "created_at": STAMP,
        "updated_at": STAMP,
    }


class SymbolCodeCaseTests(unittest.TestCase):
    def _receipt(self, body: str, *, currency: str = "USD"):
        candidate = Candidate.validated(
            candidate_url=GH,
            platform="fixture-board",
            advertised_amount="200",
            currency=currency,
            canonical_url=GH,
            max_age_days=30,
        )
        transport = FakeTransport(
            evidence_routes(
                "acme",
                "widget",
                12,
                open_issue(GH),
                [authority_comment(body)],
            )
        )
        return preflight(candidate, transport, observed_at=NOW)

    def test_conflicting_symbol_code_is_case_insensitive_and_fails_closed(self):
        hostiles = (
            "Reward: $200 cad via Algora.",
            "Reward: $200 CaD via Algora.",
            "Reward: cad $200 via Algora.",
            "Reward: cAd $200 via Algora.",
            "Reward: €200 usd via Algora.",
            "Reward: uSd €200 via Algora.",
        )
        for body in hostiles:
            with self.subTest(body=body):
                receipt = self._receipt(body)
                self.assertEqual(receipt["freshness_status"], "ambiguous")
                self.assertEqual(receipt["route"], "reject")
                self.assertEqual(
                    receipt["checks"]["authoritative_amount_state"], "ambiguous"
                )
                self.assertIsNone(
                    receipt["checks"]["canonical_current_reward_currency"]
                )
                self.assertIsNone(
                    receipt["checks"]["canonical_current_reward_amount"]
                )
                self.assertEqual(
                    receipt["reasons"], ["canonical_reward_amount_ambiguous"]
                )

    def test_consistent_usd_symbol_code_remains_resolvable_across_case(self):
        forms = (
            "Reward: $200 usd via Algora.",
            "Reward: $200 UsD via Algora.",
            "Reward: usd $200 via Algora.",
            "Reward: uSd $200 via Algora.",
        )
        for body in forms:
            with self.subTest(body=body):
                receipt = self._receipt(body)
                self.assertEqual(receipt["freshness_status"], "actionable")
                self.assertEqual(
                    receipt["route"], "qualified_for_human_claim_decision"
                )
                self.assertEqual(
                    receipt["checks"]["authoritative_amount_state"], "resolved"
                )
                self.assertEqual(
                    receipt["checks"]["canonical_current_reward_currency"], "USD"
                )
                self.assertEqual(
                    receipt["checks"]["canonical_current_reward_amount"], "200"
                )

    def test_standalone_currency_codes_keep_existing_case_insensitive_grammar(self):
        forms = (
            "Reward: cad 200 via Algora.",
            "Reward: 200 cAd via Algora.",
        )
        for body in forms:
            with self.subTest(body=body):
                receipt = self._receipt(body, currency="CAD")
                self.assertEqual(receipt["freshness_status"], "actionable")
                self.assertEqual(
                    receipt["checks"]["authoritative_amount_state"], "resolved"
                )
                self.assertEqual(
                    receipt["checks"]["canonical_current_reward_currency"], "CAD"
                )
                self.assertEqual(
                    receipt["checks"]["canonical_current_reward_amount"], "200"
                )

    def test_identifier_like_suffixes_are_not_currency_codes(self):
        forms = (
            "Reward: $200 cadet via Algora.",
            "Reward: $200 usd_label via Algora.",
        )
        for body in forms:
            with self.subTest(body=body):
                receipt = self._receipt(body)
                self.assertEqual(receipt["freshness_status"], "actionable")
                self.assertEqual(
                    receipt["checks"]["authoritative_amount_state"], "resolved"
                )
                self.assertEqual(
                    receipt["checks"]["canonical_current_reward_currency"], "USD"
                )
                self.assertEqual(
                    receipt["checks"]["canonical_current_reward_amount"], "200"
                )


if __name__ == "__main__":
    unittest.main()
