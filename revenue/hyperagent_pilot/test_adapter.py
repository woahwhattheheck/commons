from __future__ import annotations

import copy
import hashlib
import hmac
import json
import unittest
from pathlib import Path

from revenue.hyperagent_pilot.adapter import (
    AdapterError,
    canonical_bytes,
    normalize_event,
    normalize_events,
    prepare_candidate_payloads,
    project_transcripts,
    projection_bytes,
)


FIXTURE = Path(__file__).with_name("fixture_30_events.json")
TEST_APPROVAL_KEY = b"hyperagent-test-approval-key-32-bytes"
OTHER_APPROVAL_KEY = b"hyperagent-other-authority-key-32bytes"


def fixture() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def approval_for(raw: dict, *, signing_key: bytes = TEST_APPROVAL_KEY, **overrides) -> dict:
    event = normalize_event(raw)
    value = {
        "schema": "hyperagent-pilot/approval/v1",
        "run_id": event["run_id"],
        "event_id": event["event_id"],
        "action_generation": event["action_generation"],
        "approved_at": "2026-09-16T18:00:00Z",
        "expires_at": "2026-09-16T19:00:00Z",
    }
    value.update(overrides)
    value["auth_tag"] = hmac.new(
        signing_key,
        canonical_bytes(value),
        hashlib.sha256,
    ).hexdigest()
    return value


def prepare(rows, approvals, *, now="2026-09-16T18:30:00Z"):
    return prepare_candidate_payloads(
        rows,
        approvals,
        now=now,
        approval_auth_key=TEST_APPROVAL_KEY,
    )


class HyperagentPilotAdapterTests(unittest.TestCase):
    def test_fixture_is_exactly_30_events_across_three_schemas(self):
        rows = fixture()
        self.assertEqual(len(rows), 30)
        self.assertEqual({row["backend"] for row in rows}, {"atlas", "beacon", "cipher"})
        self.assertEqual(
            {
                row["backend"]: sum(1 for x in rows if x["backend"] == row["backend"])
                for row in rows
            },
            {"atlas": 10, "beacon": 10, "cipher": 10},
        )

    def test_fixture_projects_to_six_transcripts_and_30_unique_messages(self):
        result = project_transcripts(fixture())
        self.assertEqual(result["artifact_count"], 6)
        self.assertEqual(result["logical_message_count"], 30)
        self.assertEqual(result["duplicate_source_event_count"], 0)
        message_ids = [m["event_id"] for a in result["artifacts"] for m in a["messages"]]
        self.assertEqual(len(message_ids), 30)
        self.assertEqual(len(set(message_ids)), 30)
        self.assertTrue(all(a["outbound_authorized"] is False for a in result["artifacts"]))
        self.assertFalse(result["authority"]["slack_send_performed"])

    def test_full_fixture_replay_emits_zero_duplicate_logical_messages(self):
        rows = fixture()
        result = project_transcripts(rows + copy.deepcopy(rows))
        self.assertEqual(result["artifact_count"], 6)
        self.assertEqual(result["logical_message_count"], 30)
        self.assertEqual(result["duplicate_source_event_count"], 30)
        message_ids = [m["event_id"] for a in result["artifacts"] for m in a["messages"]]
        self.assertEqual(len(message_ids), len(set(message_ids)))

    def test_two_clean_projections_are_byte_identical(self):
        rows = fixture()
        self.assertEqual(projection_bytes(rows), projection_bytes(copy.deepcopy(rows)))

    def test_source_order_does_not_change_projection_bytes(self):
        rows = fixture()
        self.assertEqual(projection_bytes(rows), projection_bytes(list(reversed(rows))))

    def test_stable_identity_is_schema_specific_and_repeatable(self):
        rows = fixture()
        first = normalize_event(rows[0])
        again = normalize_event(copy.deepcopy(rows[0]))
        self.assertEqual(first, again)
        self.assertEqual(len(first["run_id"]), 64)
        self.assertEqual(len(first["thread_id"]), 64)
        self.assertEqual(len(first["event_id"]), 64)

    def test_same_source_event_id_with_changed_semantics_fails_closed(self):
        rows = fixture()
        changed = copy.deepcopy(rows[0])
        changed["event"]["text"] = "different semantics"
        with self.assertRaisesRegex(AdapterError, "same source event ID changed semantics"):
            normalize_events([rows[0], changed])

    def test_same_source_run_sequence_with_different_event_id_is_ambiguous(self):
        rows = fixture()
        changed = copy.deepcopy(rows[0])
        changed["event"]["id"] = "different-id"
        with self.assertRaisesRegex(AdapterError, "ambiguous sequence"):
            normalize_events([rows[0], changed])

    def test_valid_exact_generation_authenticated_approval_emits_one_offline_candidate(self):
        rows = fixture()
        action = next(row for row in rows if normalize_event(row)["kind"] == "ACTION_REQUEST")
        approval = approval_for(action)
        payloads = prepare(rows, [approval])
        self.assertEqual(len(payloads), 1)
        self.assertTrue(payloads[0]["approval_validated"])
        self.assertEqual(payloads[0]["approval_receipt_sha256"], hashlib.sha256(canonical_bytes(approval)).hexdigest())
        self.assertFalse(payloads[0]["outbound_authorized"])
        self.assertFalse(payloads[0]["provider_action_performed"])
        self.assertEqual(len(payloads[0]["candidate_sha256"]), 64)

    def test_caller_fabricated_approval_under_untrusted_key_fails_closed(self):
        rows = fixture()
        action = next(row for row in rows if normalize_event(row)["kind"] == "ACTION_REQUEST")
        forged = approval_for(action, signing_key=OTHER_APPROVAL_KEY)
        self.assertEqual(prepare(rows, [forged]), [])

    def test_tampered_signed_approval_field_without_resigning_fails_closed(self):
        rows = fixture()
        action = next(row for row in rows if normalize_event(row)["kind"] == "ACTION_REQUEST")
        approval = approval_for(action)
        approval["expires_at"] = "2026-09-16T20:00:00Z"
        self.assertEqual(prepare(rows, [approval]), [])

    def test_missing_retained_approval_authority_key_fails_closed(self):
        rows = fixture()
        action = next(row for row in rows if normalize_event(row)["kind"] == "ACTION_REQUEST")
        self.assertEqual(
            prepare_candidate_payloads(
                rows,
                [approval_for(action)],
                now="2026-09-16T18:30:00Z",
            ),
            [],
        )

    def test_missing_approval_emits_no_candidate_for_actions(self):
        self.assertEqual(prepare(fixture(), []), [])

    def test_wrong_run_authenticated_approval_fails_closed_to_zero(self):
        rows = fixture()
        action = next(row for row in rows if normalize_event(row)["kind"] == "ACTION_REQUEST")
        self.assertEqual(prepare(rows, [approval_for(action, run_id="f" * 64)]), [])

    def test_wrong_action_generation_authenticated_approval_fails_closed_to_zero(self):
        rows = fixture()
        action = next(row for row in rows if normalize_event(row)["kind"] == "ACTION_REQUEST")
        self.assertEqual(
            prepare(rows, [approval_for(action, action_generation="f" * 64)]),
            [],
        )

    def test_stale_authenticated_approval_fails_closed_to_zero(self):
        rows = fixture()
        action = next(row for row in rows if normalize_event(row)["kind"] == "ACTION_REQUEST")
        self.assertEqual(
            prepare(rows, [approval_for(action)], now="2026-09-16T19:00:01Z"),
            [],
        )

    def test_foreign_authenticated_approval_fails_entire_set_closed(self):
        rows = fixture()
        action = next(row for row in rows if normalize_event(row)["kind"] == "ACTION_REQUEST")
        foreign = approval_for(action, event_id="e" * 64)
        self.assertEqual(prepare(rows, [foreign]), [])

    def test_malformed_approval_fails_closed_to_zero(self):
        rows = fixture()
        action = next(row for row in rows if normalize_event(row)["kind"] == "ACTION_REQUEST")
        malformed = approval_for(action)
        malformed["unexpected"] = True
        self.assertEqual(prepare(rows, [malformed]), [])

    def test_duplicate_approval_for_same_event_fails_closed(self):
        rows = fixture()
        action = next(row for row in rows if normalize_event(row)["kind"] == "ACTION_REQUEST")
        approval = approval_for(action)
        self.assertEqual(prepare(rows, [approval, copy.deepcopy(approval)]), [])

    def test_noncanonical_utc_approval_fails_closed(self):
        rows = fixture()
        action = next(row for row in rows if normalize_event(row)["kind"] == "ACTION_REQUEST")
        approval = approval_for(action, approved_at="2026-09-16T14:00:00-04:00")
        self.assertEqual(prepare(rows, [approval]), [])

    def test_short_approval_authority_key_fails_closed(self):
        rows = fixture()
        action = next(row for row in rows if normalize_event(row)["kind"] == "ACTION_REQUEST")
        approval = approval_for(action)
        self.assertEqual(
            prepare_candidate_payloads(
                rows,
                [approval],
                now="2026-09-16T18:30:00Z",
                approval_auth_key=b"too-short",
            ),
            [],
        )

    def test_unknown_backend_is_rejected(self):
        with self.assertRaisesRegex(AdapterError, "unsupported backend"):
            normalize_event({"backend": "unknown"})

    def test_bool_is_not_a_sequence_number(self):
        row = copy.deepcopy(fixture()[0])
        row["event"]["sequence"] = True
        with self.assertRaisesRegex(AdapterError, "must be an integer"):
            normalize_event(row)

    def test_control_text_is_rejected(self):
        row = copy.deepcopy(fixture()[0])
        row["event"]["text"] = "bad\u0000text"
        with self.assertRaisesRegex(AdapterError, "control characters"):
            normalize_event(row)


if __name__ == "__main__":
    unittest.main()
