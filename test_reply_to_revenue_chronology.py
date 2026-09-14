from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "reply_to_revenue_chronology",
    ROOT / "host" / "reply_to_revenue.py",
)
assert SPEC and SPEC.loader
r2r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r2r)


class ReplyToRevenueChronologyTests(unittest.TestCase):
    def receipt(self) -> dict[str, object]:
        return {
            "prospect_key": "example-buyer",
            "organization": "Example Buyer",
            "hard_dnr": True,
            "receipt_id": "receipt-example-1",
            "path": "fixture.json",
            "cash_usd": 0,
        }

    def event(
        self,
        classification: str,
        received_at: str,
        event_ref: str,
    ) -> dict[str, object]:
        return {
            "event_ref": event_ref,
            "received_at": received_at,
            "prospect_key": "example-buyer",
            "matched_receipt_id": "receipt-example-1",
            "classification": classification,
        }

    def contact(self, *events: dict[str, object]) -> dict[str, object]:
        contacts = r2r._contact_rows([self.receipt()], list(events))
        self.assertEqual(len(contacts), 1)
        return contacts[0]

    def test_later_negative_closes_stale_positive(self) -> None:
        contact = self.contact(
            self.event("POSITIVE_SCOPE", "2026-09-13T12:00:00Z", "opaque:positive-old"),
            self.event("NEGATIVE", "2026-09-13T12:10:00Z", "opaque:negative-new"),
        )
        self.assertEqual(contact["lane"], "CLOSED")
        self.assertEqual(contact["next_action"], "CLOSE")

    def test_later_opt_out_closes_stale_positive(self) -> None:
        contact = self.contact(
            self.event("POSITIVE_SCOPE", "2026-09-13T12:00:00Z", "opaque:positive-old"),
            self.event("OPT_OUT", "2026-09-13T12:10:00Z", "opaque:optout-new"),
        )
        self.assertEqual(contact["lane"], "CLOSED")
        self.assertEqual(contact["next_action"], "DNC/CLOSE")

    def test_later_needs_human_blocks_stale_positive(self) -> None:
        contact = self.contact(
            self.event("POSITIVE_SCOPE", "2026-09-13T12:00:00Z", "opaque:positive-old"),
            self.event("NEEDS_HUMAN", "2026-09-13T12:10:00Z", "opaque:review-new"),
        )
        self.assertEqual(contact["lane"], "NEEDS_HUMAN")
        self.assertEqual(
            contact["next_action"],
            "ESCALATE_ONLY_IF_BUYER_REQUESTS_BRYCE",
        )

    def test_later_positive_can_supersede_older_negative(self) -> None:
        contact = self.contact(
            self.event("NEGATIVE", "2026-09-13T12:00:00Z", "opaque:negative-old"),
            self.event("POSITIVE_SCOPE", "2026-09-13T12:10:00Z", "opaque:positive-new"),
        )
        self.assertEqual(contact["lane"], "HUMAN_POSITIVE")
        self.assertEqual(contact["next_action"], "NEEDS_ACCEPTANCE")

    def test_later_negative_closes_old_question(self) -> None:
        contact = self.contact(
            self.event("QUESTION", "2026-09-13T12:00:00Z", "opaque:question-old"),
            self.event("NEGATIVE", "2026-09-13T12:10:00Z", "opaque:negative-new"),
        )
        self.assertEqual(contact["lane"], "CLOSED")
        self.assertEqual(contact["next_action"], "CLOSE")

    def test_later_human_positive_supersedes_older_failure(self) -> None:
        contact = self.contact(
            self.event("DELIVERY_FAILURE", "2026-09-13T12:00:00Z", "opaque:failure-old"),
            self.event("POSITIVE_SCOPE", "2026-09-13T12:10:00Z", "opaque:positive-new"),
        )
        self.assertEqual(contact["lane"], "HUMAN_POSITIVE")

    def test_later_machine_failure_does_not_revoke_human_positive(self) -> None:
        positive = self.event(
            "POSITIVE_SCOPE", "2026-09-13T12:00:00Z", "opaque:positive-authority"
        )
        failure = self.event(
            "DELIVERY_FAILURE", "2026-09-13T12:10:00Z", "opaque:failure-later"
        )
        contact = self.contact(positive, failure)
        self.assertEqual(contact["lane"], "HUMAN_POSITIVE")
        surfaces = r2r.surface_positives([contact], [positive, failure])
        self.assertEqual(len(surfaces), 1)
        self.assertEqual(surfaces[0]["event_ref"], "opaque:positive-authority")
        self.assertEqual(surfaces[0]["received_at"], "2026-09-13T12:00:00Z")

    def test_later_auto_ack_does_not_poison_positive_surface_provenance(self) -> None:
        positive = self.event(
            "POSITIVE_SCOPE", "2026-09-13T12:00:00Z", "opaque:positive-authority"
        )
        auto = self.event(
            "AUTO_RESPONSE", "2026-09-13T12:10:00Z", "opaque:auto-later"
        )
        contact = self.contact(positive, auto)
        surfaces = r2r.surface_positives([contact], [positive, auto])
        self.assertEqual(surfaces[0]["event_ref"], "opaque:positive-authority")

    def test_equal_time_conflicting_human_states_fail_closed(self) -> None:
        positive = self.event(
            "POSITIVE_SCOPE", "2026-09-13T12:00:00Z", "opaque:positive-tie"
        )
        negative = self.event(
            "NEGATIVE", "2026-09-13T08:00:00-04:00", "opaque:negative-tie"
        )
        contact = self.contact(positive, negative)
        self.assertEqual(contact["lane"], "NEEDS_HUMAN")
        self.assertEqual(r2r.surface_positives([contact], [positive, negative]), [])

    def test_equal_time_identical_positive_state_is_deterministic(self) -> None:
        second = self.event(
            "POSITIVE_SCOPE", "2026-09-13T12:00:00Z", "opaque:positive-b"
        )
        first = self.event(
            "POSITIVE_SCOPE", "2026-09-13T08:00:00-04:00", "opaque:positive-a"
        )
        contact = self.contact(second, first)
        self.assertEqual(contact["lane"], "HUMAN_POSITIVE")
        surfaces = r2r.surface_positives([contact], [second, first])
        self.assertEqual(surfaces[0]["event_ref"], "opaque:positive-a")

    def test_utc_normalization_not_lexical_timestamp_ordering(self) -> None:
        contact = self.contact(
            self.event("POSITIVE_SCOPE", "2026-09-13T12:00:00Z", "opaque:positive-old"),
            self.event("NEGATIVE", "2026-09-13T08:05:00-04:00", "opaque:negative-new"),
        )
        self.assertEqual(contact["lane"], "CLOSED")
        self.assertEqual(contact["next_action"], "CLOSE")

    def test_checked_in_historical_funnel_remains_valid(self) -> None:
        funnel = r2r.validate_funnel()
        self.assertEqual(funnel["truth"]["human_positive"], 0)
        self.assertEqual(funnel["truth"]["delivery_failures"], 0)
        self.assertEqual(funnel["truth"]["cash_usd"], 0)
        self.assertEqual(funnel["truth"]["resends"], 0)
        self.assertEqual(funnel["truth"]["transport_actions"], 0)


if __name__ == "__main__":
    unittest.main()
