from __future__ import annotations

from copy import deepcopy
import hashlib
import unittest

from revenue.hyperagent_slack_transcript import ConflictError, TranscriptProjector


def mutation_event():
    return {
        "backend": "stream",
        "run_id": "mut-run",
        "event_id": "m1",
        "seq": 1,
        "kind": "MUTATING_ACTION",
        "payload": {
            "thread": "mut",
            "text": "would mutate provider",
            "action_id": "send",
            "generation": 2,
        },
    }


def approval_for(event):
    raw = f"run\x1fstream\x1f{event['run_id']}".encode()
    run_id = "run_" + hashlib.sha256(raw).hexdigest()[:24]
    return {
        "approval_id": "ap-1",
        "run_id": run_id,
        "action_id": event["payload"]["action_id"],
        "generation": event["payload"]["generation"],
        "decision": "APPROVE",
        "issued_at": "2026-09-16T11:00:00Z",
        "expires_at": "2026-09-16T13:00:00Z",
        "evidence_sha256": "a" * 64,
    }


class IncrementalAuthorityTests(unittest.TestCase):
    def test_held_action_can_emit_after_exact_approval_arrives(self):
        event = mutation_event()
        projector = TranscriptProjector()
        first = projector.ingest([event], [], as_of="2026-09-16T12:00:00Z")
        self.assertEqual(first["message_count"], 0)
        second = projector.ingest([event], [approval_for(event)], as_of="2026-09-16T12:00:00Z")
        self.assertEqual(second["message_count"], 1)
        self.assertEqual(len(second["new_message_ids"]), 1)
        self.assertFalse(second["artifacts"][0]["external_send_authorized"])

    def test_changed_held_event_semantics_still_conflict(self):
        event = mutation_event()
        projector = TranscriptProjector()
        projector.ingest([event], [], as_of="2026-09-16T12:00:00Z")
        changed = deepcopy(event)
        changed["payload"]["text"] = "changed"
        with self.assertRaises(ConflictError):
            projector.ingest([changed], [approval_for(event)], as_of="2026-09-16T12:00:00Z")

    def test_approval_identity_is_immutable_across_ingests(self):
        event = mutation_event()
        approval = approval_for(event)
        projector = TranscriptProjector()
        projector.ingest([], [approval], as_of="2026-09-16T12:00:00Z")
        changed = deepcopy(approval)
        changed["evidence_sha256"] = "b" * 64
        with self.assertRaises(ConflictError):
            projector.ingest([], [changed], as_of="2026-09-16T12:00:00Z")

    def test_emitted_event_replay_remains_idempotent(self):
        event = mutation_event()
        approval = approval_for(event)
        projector = TranscriptProjector()
        first = projector.ingest([event], [approval], as_of="2026-09-16T12:00:00Z")
        second = projector.ingest([event], [approval], as_of="2026-09-16T12:00:00Z")
        self.assertEqual(len(first["new_message_ids"]), 1)
        self.assertEqual(second["new_message_ids"], [])
        self.assertEqual(second["message_count"], 1)


if __name__ == "__main__":
    unittest.main()
