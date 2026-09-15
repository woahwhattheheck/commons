from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "reply_to_revenue_chronology_hostiles",
    ROOT / "host" / "reply_to_revenue.py",
)
assert SPEC and SPEC.loader
r2r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r2r)


class ReplyToRevenueChronologyHostileTests(unittest.TestCase):
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
        *,
        prospect_key: str = "example-buyer",
        matched_receipt_id: str = "receipt-example-1",
    ) -> dict[str, object]:
        return {
            "event_ref": event_ref,
            "received_at": received_at,
            "prospect_key": prospect_key,
            "matched_receipt_id": matched_receipt_id,
            "classification": classification,
        }

    def contact(self, *events: dict[str, object]) -> dict[str, object]:
        contacts = r2r._contact_rows([self.receipt()], list(events))
        self.assertEqual(len(contacts), 1)
        return contacts[0]

    def test_equal_time_opt_out_dominates_positive_across_offsets(self) -> None:
        positive = self.event(
            "POSITIVE_SCOPE",
            "2026-09-13T12:00:00Z",
            "opaque:positive-equal-time",
        )
        opt_out = self.event(
            "OPT_OUT",
            "2026-09-13T08:00:00-04:00",
            "opaque:opt-out-equal-time",
        )
        contact = self.contact(positive, opt_out)
        self.assertEqual(contact["lane"], "CLOSED")
        self.assertEqual(contact["next_action"], "DNC/CLOSE")
        self.assertEqual(r2r.surface_positives([contact], [positive, opt_out]), [])

    def test_equal_time_opt_out_dominates_question_and_needs_human(self) -> None:
        for conflicting in ("QUESTION", "NEEDS_HUMAN"):
            with self.subTest(conflicting=conflicting):
                other = self.event(
                    conflicting,
                    "2026-09-13T12:00:00Z",
                    f"opaque:{conflicting.casefold()}-equal-time",
                )
                opt_out = self.event(
                    "OPT_OUT",
                    "2026-09-13T08:00:00-04:00",
                    "opaque:opt-out-equal-time",
                )
                contact = self.contact(other, opt_out)
                self.assertEqual(contact["lane"], "CLOSED")
                self.assertEqual(contact["next_action"], "DNC/CLOSE")

    def test_opt_out_does_not_bypass_unknown_classification_validation(self) -> None:
        opt_out = self.event(
            "OPT_OUT",
            "2026-09-13T12:00:00Z",
            "opaque:opt-out-known",
        )
        unknown = self.event(
            "UNRECOGNIZED_STATE",
            "2026-09-13T12:00:00Z",
            "opaque:unknown-state",
        )
        with self.assertRaises(r2r.ReplyRevenueError):
            r2r._reduce_contact_state([opt_out, unknown])

    def test_unmatched_opt_out_row_remains_hard_dnr(self) -> None:
        opt_out = self.event(
            "OPT_OUT",
            "2026-09-13T12:00:00Z",
            "opaque:unmatched-opt-out",
            prospect_key="raw-unmatched-buyer",
            matched_receipt_id="missing-receipt",
        )
        contacts = r2r._contact_rows([], [opt_out])
        self.assertEqual(len(contacts), 1)
        self.assertIs(contacts[0]["hard_dnr"], True)
        self.assertEqual(contacts[0]["lane"], "CLOSED")
        self.assertEqual(contacts[0]["next_action"], "DNC/CLOSE")

    def test_later_failure_is_disclosed_without_revoking_positive(self) -> None:
        positive = self.event(
            "POSITIVE_SCOPE",
            "2026-09-13T12:00:00Z",
            "opaque:positive-authority",
        )
        failure = self.event(
            "DELIVERY_FAILURE",
            "2026-09-13T12:10:00Z",
            "opaque:failure-later",
        )
        contact = self.contact(positive, failure)
        surface = r2r.surface_positives([contact], [positive, failure])[0]
        self.assertEqual(surface["event_ref"], "opaque:positive-authority")
        self.assertIn("DELIVERY_FAILURE", surface["context"])
        self.assertIn("do not override human semantics", surface["context"])
        self.assertNotIn("were absent", surface["context"])

    def test_later_auto_response_is_disclosed_without_revoking_positive(self) -> None:
        positive = self.event(
            "POSITIVE_SCOPE",
            "2026-09-13T12:00:00Z",
            "opaque:positive-authority",
        )
        auto = self.event(
            "AUTO_RESPONSE",
            "2026-09-13T12:10:00Z",
            "opaque:auto-later",
        )
        contact = self.contact(positive, auto)
        surface = r2r.surface_positives([contact], [positive, auto])[0]
        self.assertEqual(surface["event_ref"], "opaque:positive-authority")
        self.assertIn("AUTO_RESPONSE", surface["context"])
        self.assertIn("do not override human semantics", surface["context"])
        self.assertNotIn("were absent", surface["context"])

    def test_machine_free_positive_context_is_explicit(self) -> None:
        positive = self.event(
            "POSITIVE_SCOPE",
            "2026-09-13T12:00:00Z",
            "opaque:positive-only",
        )
        contact = self.contact(positive)
        surface = r2r.surface_positives([contact], [positive])[0]
        self.assertIn("no machine delivery-failure", surface["context"])
        self.assertNotIn("were absent", surface["context"])


if __name__ == "__main__":
    unittest.main()
