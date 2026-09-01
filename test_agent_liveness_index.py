#!/usr/bin/env python3
"""Focused tests for receipt-derived agent freshness."""

from __future__ import annotations

import copy
import json
import unittest

from host.agent_liveness_index import (
    AgentLivenessError,
    build_index,
    canonical_text,
    git_blob_sha,
)


BLOBS = {
    "presence.json": "1" * 40,
    "lastseen.json": "2" * 40,
    "claims.json": "3" * 40,
}
OBSERVED = "2026-09-01T16:00:00Z"


def fixture() -> dict[str, object]:
    return {
        "presence": [
            {"from": "FRESH", "presence": "PRESENT", "id": "r1", "ts": "2026-09-01T15:00:00Z"},
            {"from": "RECENT", "presence": "PRESENT", "id": "r2", "ts": "2026-09-01T08:00:00Z"},
            {"from": "STALE", "presence": "PRESENT", "id": "r3", "ts": "2026-08-30T12:00:00Z"},
            {"from": "UNKNOWN", "presence": "PRESENT", "id": "r4", "ts": ""},
        ],
        "lastseen": [
            {"from": "FRESH", "id": "r1", "ts": "2026-09-01T15:00:00Z", "to": "TABLE"},
            {"from": "RECENT", "id": "r2", "ts": "2026-09-01T08:00:00Z", "to": "TABLE"},
            {"from": "STALE", "id": "r3", "ts": "2026-08-30T12:00:00Z", "to": "TABLE"},
            {"from": "UNKNOWN", "id": "r4", "ts": "", "to": "TABLE"},
        ],
        "claims": {
            "claims": [
                {"id": "r1", "from": "FRESH", "status": "OPEN", "ts": "2026-09-01T15:00:00Z", "href": "./p/r1.html"},
                {"id": "other", "from": "OTHER", "status": "CLOSED", "ts": "", "href": ""},
            ]
        },
    }


def build(data: dict[str, object] | None = None) -> dict[str, object]:
    data = fixture() if data is None else data
    return build_index(
        presence=data["presence"],
        lastseen=data["lastseen"],
        claims=data["claims"],
        observed_at=OBSERVED,
        source_commit="a" * 40,
        source_blobs=BLOBS,
    )


class AgentLivenessIndexTests(unittest.TestCase):
    def test_exact_freshness_summary(self) -> None:
        self.assertEqual(
            build()["summary"],
            {
                "identities": 4,
                "fresh_6h": 1,
                "recent_6_to_24h": 1,
                "stale_over_24h": 1,
                "unknown_timestamp": 1,
                "claims": 2,
                "claim_ids_matching_lastseen": 1,
                "claim_statuses": {"CLOSED": 1, "OPEN": 1},
            },
        )

    def test_fresh_receipt_never_claims_session_reachability(self) -> None:
        fresh = next(row for row in build()["identities"] if row["actor"] == "FRESH")
        self.assertEqual(fresh["routing_evidence"], "FRESH_RECEIPT_ONLY")
        self.assertEqual(fresh["session_reachability"], "NOT_VERIFIED")

    def test_nonfresh_receipts_fail_closed_for_routing(self) -> None:
        rows = {row["actor"]: row for row in build()["identities"]}
        for actor in ("RECENT", "STALE", "UNKNOWN"):
            self.assertEqual(rows[actor]["routing_evidence"], "NOT_CURRENT")

    def test_exact_claim_match_does_not_turn_open_into_capacity(self) -> None:
        row = next(row for row in build()["identities"] if row["actor"] == "FRESH")
        self.assertEqual(row["exact_claims"][0]["status"], "OPEN")
        self.assertEqual(row["session_reachability"], "NOT_VERIFIED")
        self.assertTrue(build()["truth"]["open_claim_is_not_active_capacity"])

    def test_source_order_does_not_change_bytes(self) -> None:
        data = fixture()
        reverse = copy.deepcopy(data)
        reverse["presence"].reverse()
        reverse["lastseen"].reverse()
        reverse["claims"]["claims"].reverse()
        self.assertEqual(canonical_text(build(data)), canonical_text(build(reverse)))
        json.loads(canonical_text(build(data)))

    def test_presence_and_lastseen_sets_must_match(self) -> None:
        data = fixture()
        data["lastseen"].pop()
        with self.assertRaisesRegex(AgentLivenessError, "actor sets differ"):
            build(data)

    def test_receipt_id_and_timestamp_must_match(self) -> None:
        data = fixture()
        data["lastseen"][0]["id"] = "different"
        with self.assertRaisesRegex(AgentLivenessError, "receipt id mismatch"):
            build(data)
        data = fixture()
        data["lastseen"][0]["ts"] = "2026-09-01T14:00:00Z"
        with self.assertRaisesRegex(AgentLivenessError, "timestamp mismatch"):
            build(data)

    def test_duplicate_actor_and_claim_fail_closed(self) -> None:
        data = fixture()
        data["presence"].append(dict(data["presence"][0]))
        with self.assertRaisesRegex(AgentLivenessError, "duplicate actor"):
            build(data)
        data = fixture()
        data["claims"]["claims"].append(dict(data["claims"]["claims"][0]))
        with self.assertRaisesRegex(AgentLivenessError, "duplicate id"):
            build(data)

    def test_invalid_or_future_timestamp_fails_closed(self) -> None:
        data = fixture()
        data["presence"][0]["ts"] = data["lastseen"][0]["ts"] = "not-a-time"
        with self.assertRaisesRegex(AgentLivenessError, "must be RFC3339"):
            build(data)
        data = fixture()
        data["presence"][0]["ts"] = data["lastseen"][0]["ts"] = "2026-09-01T17:00:00Z"
        with self.assertRaisesRegex(AgentLivenessError, "in the future"):
            build(data)

    def test_exact_source_boundary(self) -> None:
        self.assertEqual(build()["source_blobs"], BLOBS)
        with self.assertRaisesRegex(AgentLivenessError, "three source files"):
            data = fixture()
            build_index(
                presence=data["presence"], lastseen=data["lastseen"], claims=data["claims"],
                observed_at=OBSERVED, source_commit="a" * 40,
                source_blobs={"presence.json": "1" * 40},
            )

    def test_git_blob_sha_matches_empty_blob(self) -> None:
        self.assertEqual(git_blob_sha(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")

    def test_truth_records_zero_mutations(self) -> None:
        truth = build()["truth"]
        self.assertTrue(truth["board_presence_is_not_runtime_liveness"])
        self.assertTrue(truth["fresh_receipt_is_not_session_reachability"])
        self.assertEqual(truth["sessions_woken"], 0)
        self.assertEqual(truth["claims_mutated"], 0)
        self.assertEqual(truth["messages_sent"], 0)


if __name__ == "__main__":
    unittest.main()
