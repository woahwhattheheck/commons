from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import unittest

from revenue.opportunity_portfolio_intake.cli import _pairs
from revenue.opportunity_portfolio_intake.intake import (
    IntakeError,
    compile_intake,
    normalize_intake,
    verify_receipt,
)


def h(text: str) -> str:
    return sha256(text.encode()).hexdigest()


def source(ref: str, at: str, token: str | None = None) -> dict[str, str]:
    return {"ref": ref, "digestSha256": h(token or ref), "observedAt": at}


def event(event_id: str, kind: str, at: str, **extra: object) -> dict[str, object]:
    return {"eventId": event_id, "kind": kind, "source": source(f"slack:{event_id}", at, event_id), **extra}


def facts() -> dict[str, object]:
    return {
        "source": source("issue:123", "2026-09-14T00:40:00Z", "facts"),
        "freshUntil": "2026-09-15T00:00:00Z",
        "deadline": "2026-09-16T00:00:00Z",
        "eligibility": {"status": "ELIGIBLE", "evidenceSha256": h("eligible")},
        "value": {
            "currency": "USD",
            "amountMinor": 250000,
            "probabilityBps": 5000,
            "probabilityEvidenceSha256": h("probability"),
        },
        "capacity": {"engineering": 1},
        "blockers": [],
        "dependsOn": [],
        "exclusiveGroup": None,
        "labels": ["revenue"],
    }


def packet(events: list[dict[str, object]] | None = None, *, custody: bool = True, status: bool = True) -> dict[str, object]:
    return {
        "schema": "commons-opportunity-portfolio-intake/v1",
        "actorSeat": "ZEP-B4N8",
        "capacities": {"engineering": 4},
        "currencyPriority": ["USD"],
        "snapshot": {
            "custodyComplete": custody,
            "statusComplete": status,
            "source": source("snapshot:1", "2026-09-14T01:00:00Z", "snapshot"),
        },
        "opportunities": [{"id": "opp-1", "title": "Paid lane", "facts": facts(), "events": events or []}],
    }


TRUSTED = "2026-09-14T01:01:00Z"


class IntakeTests(unittest.TestCase):
    def compile(self, events=None, **kwargs):
        return compile_intake(packet(events, **kwargs), trusted_as_of=TRUSTED)

    def item(self, receipt):
        return receipt["portfolioInput"]["opportunities"][0]

    def blockers(self, receipt):
        return {b["code"]: b["status"] for b in self.item(receipt)["blockers"]}

    def test_available_without_claim(self):
        self.assertEqual(self.item(self.compile())["owner"], {"status": "AVAILABLE", "seat": None})

    def test_this_seat_take(self):
        receipt = self.compile([event("e1", "TAKE", "2026-09-14T00:50:00Z", actorSeat="ZEP-B4N8")])
        self.assertEqual(self.item(receipt)["owner"], {"status": "OWNED_BY_THIS_SEAT", "seat": "ZEP-B4N8"})

    def test_other_seat_take(self):
        receipt = self.compile([event("e1", "TAKE", "2026-09-14T00:50:00Z", actorSeat="OTHER-1")])
        self.assertEqual(self.item(receipt)["owner"], {"status": "OWNED_BY_OTHER", "seat": "OTHER-1"})

    def test_active_owner_collision_fails_closed(self):
        receipt = self.compile([
            event("e1", "TAKE", "2026-09-14T00:50:00Z", actorSeat="A-1"),
            event("e2", "TAKE", "2026-09-14T00:50:00Z", actorSeat="B-1"),
        ])
        self.assertEqual(self.item(receipt)["owner"], {"status": "UNKNOWN", "seat": None})
        self.assertEqual(self.blockers(receipt)["OWNER-COLLISION"], "OPEN")

    def test_take_then_release_becomes_available(self):
        receipt = self.compile([
            event("e1", "TAKE", "2026-09-14T00:49:00Z", actorSeat="A-1"),
            event("e2", "RELEASE", "2026-09-14T00:51:00Z", actorSeat="A-1"),
        ])
        self.assertEqual(self.item(receipt)["owner"]["status"], "AVAILABLE")

    def test_same_timestamp_take_release_fails_closed(self):
        receipt = self.compile([
            event("a-release", "RELEASE", "2026-09-14T00:50:00Z", actorSeat="A-1"),
            event("z-take", "TAKE", "2026-09-14T00:50:00Z", actorSeat="A-1"),
        ])
        self.assertEqual(self.item(receipt)["owner"]["status"], "UNKNOWN")
        self.assertEqual(self.blockers(receipt)["CUSTODY-HISTORY-CONFLICT"], "OPEN")

    def test_unmatched_release_marks_history_conflict(self):
        receipt = self.compile([event("e1", "RELEASE", "2026-09-14T00:51:00Z", actorSeat="A-1")])
        self.assertEqual(self.item(receipt)["owner"]["status"], "UNKNOWN")
        self.assertEqual(self.blockers(receipt)["CUSTODY-HISTORY-CONFLICT"], "OPEN")

    def test_exact_replay_collapses(self):
        e = event("e1", "TAKE", "2026-09-14T00:50:00Z", actorSeat="A-1")
        receipt = self.compile([e, deepcopy(e)])
        self.assertEqual(receipt["folds"][0]["eventIds"], ["e1"])

    def test_changed_event_id_payload_is_rejected(self):
        a = event("e1", "TAKE", "2026-09-14T00:50:00Z", actorSeat="A-1")
        b = event("e1", "TAKE", "2026-09-14T00:50:00Z", actorSeat="B-1")
        with self.assertRaisesRegex(IntakeError, "changed payload reused eventId"):
            self.compile([a, b])

    def test_dnr_survives_internal_take(self):
        receipt = self.compile([
            event("e1", "DNR", "2026-09-14T00:45:00Z", origin="BUYER"),
            event("e2", "TAKE", "2026-09-14T00:50:00Z", actorSeat="ZEP-B4N8"),
        ])
        self.assertEqual(self.blockers(receipt)["DNR"], "OPEN")

    def test_only_buyer_reopen_clears_dnr(self):
        receipt = self.compile([
            event("e1", "DNR", "2026-09-14T00:45:00Z", origin="BUYER"),
            event("e2", "BUYER_REOPEN", "2026-09-14T00:55:00Z", origin="BUYER"),
        ])
        self.assertEqual(self.blockers(receipt)["DNR"], "RESOLVED")

    def test_buyer_reopen_without_dnr_marks_status_conflict(self):
        receipt = self.compile([event("e1", "BUYER_REOPEN", "2026-09-14T00:55:00Z", origin="BUYER")])
        self.assertEqual(self.blockers(receipt)["STATUS-HISTORY-CONFLICT"], "OPEN")

    def test_generic_event_cannot_resolve_reserved_dnr(self):
        with self.assertRaisesRegex(IntakeError, "reserved blocker DNR"):
            self.compile([event("e1", "BLOCKER_RESOLVED", "2026-09-14T00:55:00Z", code="DNR")])

    def test_closed_and_shipped_are_terminal_blockers(self):
        receipt = self.compile([
            event("e1", "CLOSED", "2026-09-14T00:45:00Z"),
            event("e2", "SHIPPED", "2026-09-14T00:46:00Z"),
        ])
        blockers = self.blockers(receipt)
        self.assertEqual(blockers["CLOSED"], "OPEN")
        self.assertEqual(blockers["ALREADY-SHIPPED"], "OPEN")

    def test_incomplete_snapshots_add_blockers(self):
        receipt = self.compile(custody=False, status=False)
        blockers = self.blockers(receipt)
        self.assertEqual(self.item(receipt)["owner"]["status"], "UNKNOWN")
        self.assertEqual(blockers["CUSTODY-INCOMPLETE"], "OPEN")
        self.assertEqual(blockers["STATUS-INCOMPLETE"], "OPEN")

    def test_duplicate_opportunity_id_is_rejected(self):
        p = packet()
        p["opportunities"].append(deepcopy(p["opportunities"][0]))
        with self.assertRaisesRegex(IntakeError, "duplicate id"):
            compile_intake(p, trusted_as_of=TRUSTED)

    def test_event_newer_than_snapshot_is_rejected_even_if_trusted_clock_is_later(self):
        with self.assertRaisesRegex(IntakeError, "newer than snapshot"):
            compile_intake(
                packet([event("e1", "TAKE", "2026-09-14T01:00:30Z", actorSeat="A-1")]),
                trusted_as_of="2026-09-14T01:10:00Z",
            )

    def test_snapshot_future_is_rejected(self):
        p = packet()
        p["snapshot"]["source"]["observedAt"] = "2026-09-14T01:02:00Z"
        with self.assertRaisesRegex(IntakeError, "snapshot.*future"):
            compile_intake(p, trusted_as_of=TRUSTED)

    def test_generic_blocker_open_then_resolved(self):
        receipt = self.compile([
            event("e1", "BLOCKER_OPEN", "2026-09-14T00:45:00Z", code="NEEDS-SCOPE"),
            event("e2", "BLOCKER_RESOLVED", "2026-09-14T00:55:00Z", code="NEEDS-SCOPE"),
        ])
        self.assertEqual(self.blockers(receipt)["NEEDS-SCOPE"], "RESOLVED")

    def test_same_timestamp_blocker_open_resolve_fails_closed(self):
        receipt = self.compile([
            event("a-resolve", "BLOCKER_RESOLVED", "2026-09-14T00:50:00Z", code="NEEDS-SCOPE"),
            event("z-open", "BLOCKER_OPEN", "2026-09-14T00:50:00Z", code="NEEDS-SCOPE"),
        ])
        self.assertEqual(self.blockers(receipt)["STATUS-HISTORY-CONFLICT"], "OPEN")

    def test_same_timestamp_dnr_reopen_fails_closed(self):
        receipt = self.compile([
            event("a-reopen", "BUYER_REOPEN", "2026-09-14T00:50:00Z", origin="BUYER"),
            event("z-dnr", "DNR", "2026-09-14T00:50:00Z", origin="BUYER"),
        ])
        self.assertEqual(self.blockers(receipt)["STATUS-HISTORY-CONFLICT"], "OPEN")

    def test_unknown_blocker_resolution_marks_history_conflict(self):
        receipt = self.compile([event("e1", "BLOCKER_RESOLVED", "2026-09-14T00:55:00Z", code="NEEDS-SCOPE")])
        self.assertEqual(self.blockers(receipt)["STATUS-HISTORY-CONFLICT"], "OPEN")

    def test_event_array_permutation_is_irrelevant(self):
        events = [
            event("e2", "RELEASE", "2026-09-14T00:55:00Z", actorSeat="A-1"),
            event("e1", "TAKE", "2026-09-14T00:45:00Z", actorSeat="A-1"),
        ]
        a = self.compile(events)
        b = self.compile(list(reversed(events)))
        self.assertEqual(a["receiptDigestSha256"], b["receiptDigestSha256"])

    def test_facts_are_not_rewritten_by_status_events(self):
        p = packet([event("e1", "DNR", "2026-09-14T00:55:00Z", origin="BUYER")])
        original = deepcopy(p["opportunities"][0]["facts"])
        receipt = compile_intake(p, trusted_as_of=TRUSTED)
        item = self.item(receipt)
        for key in ("source", "freshUntil", "deadline", "eligibility", "value", "capacity", "dependsOn"):
            self.assertEqual(item[key], original[key])

    def test_receipt_round_trip_and_tamper_detection(self):
        receipt = self.compile([event("e1", "TAKE", "2026-09-14T00:50:00Z", actorSeat="ZEP-B4N8")])
        self.assertEqual(verify_receipt(receipt)["receiptDigestSha256"], receipt["receiptDigestSha256"])
        tampered = deepcopy(receipt)
        tampered["authority"]["sendAuthorized"] = True
        with self.assertRaisesRegex(IntakeError, "digest mismatch"):
            verify_receipt(tampered)

    def test_authority_ceiling_is_all_false(self):
        receipt = self.compile()
        self.assertTrue(receipt["authority"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_normalized_intake_is_deterministic(self):
        p = packet()
        a = normalize_intake(p)
        b = normalize_intake(json.loads(json.dumps(p, sort_keys=False)))
        self.assertEqual(a, b)

    def test_duplicate_json_key_hook_rejects(self):
        with self.assertRaisesRegex(IntakeError, "duplicate JSON key"):
            _pairs([("a", 1), ("a", 2)])

    def test_secret_shaped_event_reference_is_rejected(self):
        p = packet([event("e1", "TAKE", "2026-09-14T00:50:00Z", actorSeat="A-1")])
        p["opportunities"][0]["events"][0]["source"]["ref"] = "xoxb-12345678901234567890-SECRET"
        with self.assertRaisesRegex(IntakeError, "secret-shaped material refused"):
            compile_intake(p, trusted_as_of=TRUSTED)

    def test_downstream_allocator_is_actually_invoked(self):
        receipt = self.compile()
        self.assertRegex(receipt["allocatorReceiptDigestSha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(receipt["portfolioInput"]["schema"], "commons-opportunity-portfolio/v1")


if __name__ == "__main__":
    unittest.main()
