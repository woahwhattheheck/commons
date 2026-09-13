from __future__ import annotations

import unittest

from funded_work_freshness import Candidate, preflight
from test_support import NOW, FakeTransport, candidate, evidence_routes, open_issue


def authority_comment(
    body: str,
    stamp: str,
    *,
    association: str = "OWNER",
    login: str = "maintainer",
):
    return {
        "body": body,
        "user": {"login": login},
        "author_association": association,
        "created_at": stamp,
        "updated_at": stamp,
    }


class AmountPrecedenceTests(unittest.TestCase):
    def test_newer_trusted_amount_supersedes_older_amount(self):
        gh = "https://github.com/acme/widget/issues/12"
        issue = open_issue(gh, body="## Acceptance Criteria\n- [ ] pass\nReward: $500 via Algora")
        comments = [
            authority_comment(
                "Reward: $200 via Algora. Effective immediately.",
                "2026-09-13T05:00:00Z",
            )
        ]
        routes = evidence_routes("acme", "widget", 12, issue, comments)

        # 1. Stale $500 candidate row is rejected / ambiguous
        cand_500 = candidate(gh, amount="500", canonical_url=gh)
        receipt_500 = preflight(cand_500, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt_500["freshness_status"], "ambiguous")
        self.assertEqual(receipt_500["route"], "reject")
        self.assertIn("advertised_amount_not_supported_by_canonical_evidence", receipt_500["reasons"])
        self.assertFalse(receipt_500["checks"]["advertised_amount_supported_by_canonical_evidence"])
        self.assertEqual(receipt_500["checks"]["resolved_amount_status"], "resolved")
        self.assertEqual(receipt_500["checks"]["current_canonical_amount"], "200")
        self.assertEqual(receipt_500["checks"]["current_canonical_currency"], "USD")

        # 2. Fresh $200 candidate row is actionable
        cand_200 = candidate(gh, amount="200", canonical_url=gh)
        receipt_200 = preflight(cand_200, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt_200["freshness_status"], "actionable")
        self.assertEqual(receipt_200["route"], "qualified_for_human_claim_decision")
        self.assertTrue(receipt_200["checks"]["advertised_amount_supported_by_canonical_evidence"])
        self.assertEqual(receipt_200["checks"]["current_canonical_amount"], "200")

    def test_outsider_amount_comment_cannot_supersede_canonical_amount(self):
        gh = "https://github.com/acme/widget/issues/12"
        issue = open_issue(gh, body="## Acceptance Criteria\n- [ ] pass\nReward: $500 via Algora")
        comments = [
            authority_comment(
                "Reward: $200 via Algora. Effective immediately.",
                "2026-09-13T05:00:00Z",
                association="NONE",
                login="random-outsider",
            )
        ]
        routes = evidence_routes("acme", "widget", 12, issue, comments)

        # Canonical amount remains $500
        cand_500 = candidate(gh, amount="500", canonical_url=gh)
        receipt_500 = preflight(cand_500, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt_500["freshness_status"], "actionable")
        self.assertEqual(receipt_500["checks"]["current_canonical_amount"], "500")

        # Candidate $200 is rejected
        cand_200 = candidate(gh, amount="200", canonical_url=gh)
        receipt_200 = preflight(cand_200, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt_200["freshness_status"], "ambiguous")
        self.assertFalse(receipt_200["checks"]["advertised_amount_supported_by_canonical_evidence"])

    def test_sponsor_bot_amount_change_counts(self):
        gh = "https://github.com/acme/widget/issues/12"
        issue = open_issue(gh, body="## Acceptance Criteria\n- [ ] pass\nReward: $500 via Algora")
        comments = [
            authority_comment(
                "Bounty increased to $750",
                "2026-09-13T05:00:00Z",
                association="NONE",
                login="algora-pbc[bot]",
            )
        ]
        routes = evidence_routes("acme", "widget", 12, issue, comments)

        cand_750 = candidate(gh, amount="750", canonical_url=gh)
        receipt = preflight(cand_750, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt["freshness_status"], "actionable")
        self.assertEqual(receipt["checks"]["current_canonical_amount"], "750")

    def test_unrelated_budget_prose_does_not_alter_reward_amount(self):
        gh = "https://github.com/acme/widget/issues/12"
        issue = open_issue(gh, body="## Acceptance Criteria\n- [ ] pass\nReward: $500 via Algora")
        comments = [
            authority_comment(
                "test budget is $200; bounty remains available",
                "2026-09-13T05:00:00Z",
            )
        ]
        routes = evidence_routes("acme", "widget", 12, issue, comments)

        cand = candidate(gh, amount="500", canonical_url=gh)
        receipt = preflight(cand, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt["freshness_status"], "actionable")
        self.assertEqual(receipt["checks"]["current_canonical_amount"], "500")

    def test_reversed_comments_processed_in_chronological_order(self):
        gh = "https://github.com/acme/widget/issues/12"
        issue = open_issue(gh, body="## Acceptance Criteria\n- [ ] pass\nReward: $500 via Algora")
        c1 = authority_comment("Reward: $300 via Algora", "2026-09-13T04:00:00Z")
        c2 = authority_comment("Reward: $200 via Algora", "2026-09-13T05:00:00Z")

        # Input comments in reversed chronological order
        routes = evidence_routes("acme", "widget", 12, issue, [c2, c1])

        cand_200 = candidate(gh, amount="200", canonical_url=gh)
        receipt_200 = preflight(cand_200, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt_200["freshness_status"], "actionable")
        self.assertEqual(receipt_200["checks"]["current_canonical_amount"], "200")

        cand_300 = candidate(gh, amount="300", canonical_url=gh)
        receipt_300 = preflight(cand_300, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt_300["freshness_status"], "ambiguous")

    def test_currency_change_supersedes_older_currency_without_fx(self):
        gh = "https://github.com/acme/widget/issues/12"
        issue = open_issue(gh, body="## Acceptance Criteria\n- [ ] pass\nReward: $500 via Algora")
        comments = [
            authority_comment(
                "Reward: 400 EUR via Algora",
                "2026-09-13T05:00:00Z",
            )
        ]
        routes = evidence_routes("acme", "widget", 12, issue, comments)

        # Old USD candidate fails
        cand_usd = candidate(gh, amount="400", canonical_url=gh)  # currency is USD
        receipt_usd = preflight(cand_usd, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt_usd["freshness_status"], "ambiguous")
        self.assertFalse(receipt_usd["checks"]["advertised_amount_supported_by_canonical_evidence"])

        # Matching EUR candidate succeeds
        cand_eur = Candidate.validated(
            candidate_url=gh,
            platform="fixture-board",
            advertised_amount="400",
            currency="EUR",
            canonical_url=gh,
            max_age_days=30,
        )
        receipt_eur = preflight(cand_eur, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt_eur["freshness_status"], "actionable")
        self.assertEqual(receipt_eur["checks"]["current_canonical_amount"], "400")
        self.assertEqual(receipt_eur["checks"]["current_canonical_currency"], "EUR")

    def test_ambiguous_multiple_current_amounts_fails_closed(self):
        gh = "https://github.com/acme/widget/issues/12"
        issue = open_issue(gh, body="## Acceptance Criteria\n- [ ] pass\nReward: $500 via Algora")
        comments = [
            authority_comment(
                "Bounty is either $200 or $300",
                "2026-09-13T05:00:00Z",
            )
        ]
        routes = evidence_routes("acme", "widget", 12, issue, comments)

        cand = candidate(gh, amount="200", canonical_url=gh)
        receipt = preflight(cand, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt["freshness_status"], "ambiguous")
        self.assertEqual(receipt["route"], "reject")
        self.assertIn("canonical_amount_ambiguous", receipt["reasons"])
        self.assertEqual(receipt["checks"]["resolved_amount_status"], "ambiguous")
        self.assertIsNone(receipt["checks"]["current_canonical_amount"])

    def test_explicit_transition_from_to_resolves_destination(self):
        gh = "https://github.com/acme/widget/issues/12"
        issue = open_issue(gh, body="## Acceptance Criteria\n- [ ] pass\nReward: $500 via Algora")
        comments = [
            authority_comment(
                "Reward changed from $500 to $200 via Algora",
                "2026-09-13T05:00:00Z",
            )
        ]
        routes = evidence_routes("acme", "widget", 12, issue, comments)

        cand = candidate(gh, amount="200", canonical_url=gh)
        receipt = preflight(cand, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt["freshness_status"], "actionable")
        self.assertEqual(receipt["checks"]["current_canonical_amount"], "200")

    def test_untrusted_issue_author_cannot_establish_initial_amount(self):
        gh = "https://github.com/acme/widget/issues/12"
        issue = open_issue(
            gh,
            body="## Acceptance Criteria\n- [ ] pass\nReward: $500 via Algora",
            author_association="NONE",
            author_login="untrusted-opener",
        )
        comments = [
            authority_comment(
                "## Acceptance Criteria\n- [ ] pass\nReward: $200 via Algora",
                "2026-09-13T05:00:00Z",
            )
        ]
        routes = evidence_routes("acme", "widget", 12, issue, comments)

        # Candidate $500 is rejected
        cand_500 = candidate(gh, amount="500", canonical_url=gh)
        receipt_500 = preflight(cand_500, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt_500["freshness_status"], "ambiguous")

        # Candidate $200 is actionable
        cand_200 = candidate(gh, amount="200", canonical_url=gh)
        receipt_200 = preflight(cand_200, FakeTransport(routes), observed_at=NOW)
        self.assertEqual(receipt_200["freshness_status"], "actionable")
        self.assertEqual(receipt_200["checks"]["current_canonical_amount"], "200")


if __name__ == "__main__":
    unittest.main()
