from __future__ import annotations

import unittest

from validator import (
    Candidate,
    FreshnessStatus,
    Observation,
    validate_candidate,
    verify_receipt,
)


CHECKED = "2026-09-13T06:30:00Z"
SOURCE = "2026-09-13T06:20:00Z"


class StubReader:
    def __init__(self, observation: Observation):
        self.observation = observation
        self.calls = []

    def inspect(self, candidate: Candidate) -> Observation:
        self.calls.append(candidate)
        return self.observation


def candidate(url: str = "https://example.test/bounty/omi-2316") -> Candidate:
    return Candidate(
        candidate_url=url,
        advertised_amount="1000.00",
        currency="usd",
        platform="Algora",
        source_timestamp=SOURCE,
    )


class FreshnessFenceTests(unittest.TestCase):
    def test_board_open_but_canonical_closed_is_stale(self):
        reader = StubReader(
            Observation(
                canonical_url="https://github.com/BasedHardware/omi/issues/2316",
                canonical_state="closed",
                last_substantive_activity="2026-09-12T20:00:00Z",
                sponsor_payment_present=True,
                acceptance_criteria_reachable=False,
                notes=("board still advertised candidate as open",),
            )
        )
        receipt = validate_candidate(candidate(), reader, checked_at=CHECKED)
        self.assertEqual(receipt.freshness_status, FreshnessStatus.STALE)
        self.assertEqual(receipt.route, "reject")
        self.assertTrue(verify_receipt(receipt))
        self.assertEqual(len(reader.calls), 1)

    def test_second_closed_omi_fixture_is_also_stale(self):
        reader = StubReader(
            Observation(
                canonical_url="https://github.com/BasedHardware/omi/issues/1812",
                canonical_state="CLOSED",
                sponsor_payment_present=True,
                acceptance_criteria_reachable=False,
                last_substantive_activity="2026-09-11T12:00:00+00:00",
            )
        )
        receipt = validate_candidate(candidate("https://example.test/bounty/omi-1812"), reader, checked_at=CHECKED)
        self.assertEqual(receipt.freshness_status, FreshnessStatus.STALE)

    def test_genuinely_open_unoccupied_candidate_is_actionable(self):
        reader = StubReader(
            Observation(
                canonical_url="https://github.com/example/project/issues/42",
                canonical_state="open",
                assignees=(),
                visible_claim_count=0,
                active_competing_prs=(),
                last_substantive_activity="2026-09-13T05:00:00Z",
                sponsor_payment_present=True,
                acceptance_criteria_reachable=True,
            )
        )
        receipt = validate_candidate(candidate("https://example.test/bounty/42"), reader, checked_at=CHECKED)
        self.assertEqual(receipt.freshness_status, FreshnessStatus.ACTIONABLE)
        self.assertEqual(receipt.route, "work_feed")
        self.assertTrue(verify_receipt(receipt))

    def test_assignee_claim_or_competing_pr_marks_occupied(self):
        variants = (
            Observation(
                canonical_url="https://github.com/example/project/issues/42",
                canonical_state="open",
                assignees=("alice",),
                visible_claim_count=0,
                last_substantive_activity="2026-09-13T05:00:00Z",
                sponsor_payment_present=True,
                acceptance_criteria_reachable=True,
            ),
            Observation(
                canonical_url="https://github.com/example/project/issues/42",
                canonical_state="open",
                visible_claim_count=2,
                last_substantive_activity="2026-09-13T05:00:00Z",
                sponsor_payment_present=True,
                acceptance_criteria_reachable=True,
            ),
            Observation(
                canonical_url="https://github.com/example/project/issues/42",
                canonical_state="open",
                visible_claim_count=0,
                active_competing_prs=("https://github.com/example/project/pull/99",),
                last_substantive_activity="2026-09-13T05:00:00Z",
                sponsor_payment_present=True,
                acceptance_criteria_reachable=True,
            ),
        )
        for observation in variants:
            with self.subTest(observation=observation):
                receipt = validate_candidate(candidate(), StubReader(observation), checked_at=CHECKED)
                self.assertEqual(receipt.freshness_status, FreshnessStatus.OCCUPIED)
                self.assertEqual(receipt.route, "hold")

    def test_unknown_payment_or_acceptance_fails_closed_as_ambiguous(self):
        reader = StubReader(
            Observation(
                canonical_url="https://github.com/example/project/issues/42",
                canonical_state="open",
                visible_claim_count=0,
                last_substantive_activity="2026-09-13T05:00:00Z",
                sponsor_payment_present=None,
                acceptance_criteria_reachable=True,
            )
        )
        receipt = validate_candidate(candidate(), reader, checked_at=CHECKED)
        self.assertEqual(receipt.freshness_status, FreshnessStatus.AMBIGUOUS)
        self.assertEqual(receipt.route, "hold")

    def test_security_bounty_routes_research_only(self):
        reader = StubReader(
            Observation(
                canonical_url="https://github.com/example/project/issues/42",
                canonical_state="open",
                last_substantive_activity="2026-09-13T05:00:00Z",
                sponsor_payment_present=True,
                acceptance_criteria_reachable=True,
                security_bounty=True,
            )
        )
        receipt = validate_candidate(candidate(), reader, checked_at=CHECKED)
        self.assertEqual(receipt.freshness_status, FreshnessStatus.AMBIGUOUS)
        self.assertEqual(receipt.route, "research_only")

    def test_old_activity_is_ambiguous_not_actionable(self):
        reader = StubReader(
            Observation(
                canonical_url="https://github.com/example/project/issues/42",
                canonical_state="open",
                last_substantive_activity="2025-01-01T00:00:00Z",
                sponsor_payment_present=True,
                acceptance_criteria_reachable=True,
            )
        )
        receipt = validate_candidate(candidate(), reader, checked_at=CHECKED, max_idle_days=90)
        self.assertEqual(receipt.freshness_status, FreshnessStatus.AMBIGUOUS)

    def test_receipt_hash_detects_tampering(self):
        reader = StubReader(
            Observation(
                canonical_url="https://github.com/example/project/issues/42",
                canonical_state="open",
                last_substantive_activity="2026-09-13T05:00:00Z",
                sponsor_payment_present=True,
                acceptance_criteria_reachable=True,
            )
        )
        receipt = validate_candidate(candidate(), reader, checked_at=CHECKED)
        self.assertTrue(verify_receipt(receipt))
        object.__setattr__(receipt, "route", "reject")
        self.assertFalse(verify_receipt(receipt))

    def test_invalid_candidate_fails_before_reader(self):
        reader = StubReader(Observation(None, "unknown"))
        invalid = Candidate("not-a-url", "NaN", "", "", SOURCE)
        with self.assertRaises(ValueError):
            validate_candidate(invalid, reader, checked_at=CHECKED)
        self.assertEqual(reader.calls, [])

    def test_source_timestamp_cannot_be_future(self):
        reader = StubReader(Observation(None, "unknown"))
        future = Candidate(
            "https://example.test/bounty/1",
            "10",
            "USD",
            "Example",
            "2026-09-14T00:00:00Z",
        )
        with self.assertRaisesRegex(ValueError, "must not be in the future"):
            validate_candidate(future, reader, checked_at=CHECKED)
        self.assertEqual(reader.calls, [])


if __name__ == "__main__":
    unittest.main()
