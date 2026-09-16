from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import hashlib
import tempfile
import unittest

from revenue.hyperagent_slack_transcript.adapter import (
    ConflictError,
    TranscriptProjector,
    ValidationError,
    canonical_bytes,
    load_strict_json,
    project_fixture,
)
from revenue.hyperagent_slack_transcript.cli import main as cli_main

ROOT = Path(__file__).resolve().parent


def fixture():
    return load_strict_json((ROOT / "fixture.json").read_bytes())


def mutation_event(event_id="m1", run_id="mut-run", action="send", generation=2):
    return {
        "backend": "stream",
        "run_id": run_id,
        "event_id": event_id,
        "seq": 1,
        "kind": "MUTATING_ACTION",
        "payload": {
            "thread": "mut",
            "text": "would mutate provider",
            "action_id": action,
            "generation": generation,
        },
    }


def approval_for(event, *, generation=2, issued="2026-09-16T11:00:00Z", expires="2026-09-16T13:00:00Z"):
    raw = f"run\x1fstream\x1f{event['run_id']}".encode()
    run_id = "run_" + hashlib.sha256(raw).hexdigest()[:24]
    return {
        "approval_id": "ap-1",
        "run_id": run_id,
        "action_id": event["payload"]["action_id"],
        "generation": generation,
        "decision": "APPROVE",
        "issued_at": issued,
        "expires_at": expires,
        "evidence_sha256": "a" * 64,
    }


class HyperagentTranscriptTests(unittest.TestCase):
    def test_fixture_30_events_to_exactly_six_artifacts(self):
        result = project_fixture(fixture())
        self.assertEqual(result["artifact_count"], 6)
        self.assertEqual(result["message_count"], 30)
        self.assertEqual(len(result["new_message_ids"]), 30)
        self.assertEqual({a["thread_ref"] for a in result["artifacts"]}, {"alpha", "beta", "gamma", "delta", "epsilon", "zeta"})
        self.assertTrue(all(a["external_send_authorized"] is False for a in result["artifacts"]))

    def test_full_fixture_replay_emits_zero_duplicate_messages(self):
        f = fixture()
        projector = TranscriptProjector()
        first = projector.ingest(f["events"], f["approvals"], as_of=f["as_of"])
        second = projector.ingest(f["events"], f["approvals"], as_of=f["as_of"])
        self.assertEqual(len(first["new_message_ids"]), 30)
        self.assertEqual(second["new_message_ids"], [])
        self.assertEqual(second["message_count"], 30)
        ids = [m["message_id"] for a in second["artifacts"] for m in a["messages"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_changed_semantics_under_same_source_event_id_conflicts(self):
        f = fixture()
        projector = TranscriptProjector()
        projector.ingest([f["events"][0]], [], as_of=f["as_of"])
        changed = deepcopy(f["events"][0])
        changed["payload"]["text"] = "changed bytes"
        with self.assertRaises(ConflictError):
            projector.ingest([changed], [], as_of=f["as_of"])

    def test_mutation_without_approval_emits_no_artifact(self):
        event = mutation_event()
        result = TranscriptProjector().ingest([event], [], as_of="2026-09-16T12:00:00Z")
        self.assertEqual(result["artifact_count"], 0)
        self.assertEqual(result["message_count"], 0)
        self.assertEqual(len(result["held"]), 1)

    def test_mutation_exact_current_approval_emits(self):
        event = mutation_event()
        result = TranscriptProjector().ingest([event], [approval_for(event)], as_of="2026-09-16T12:00:00Z")
        self.assertEqual(result["artifact_count"], 1)
        self.assertEqual(result["message_count"], 1)
        self.assertEqual(result["artifacts"][0]["messages"][0]["approval_id"], "ap-1")
        self.assertFalse(result["artifacts"][0]["external_send_authorized"])

    def test_held_mutation_can_emit_when_exact_approval_arrives_later(self):
        event = mutation_event()
        projector = TranscriptProjector()
        first = projector.ingest([event], [], as_of="2026-09-16T12:00:00Z")
        self.assertEqual(first["message_count"], 0)
        second = projector.ingest([event], [approval_for(event)], as_of="2026-09-16T12:00:00Z")
        self.assertEqual(second["message_count"], 1)
        self.assertEqual(len(second["new_message_ids"]), 1)

    def test_foreign_generation_approval_holds(self):
        event = mutation_event()
        approval = approval_for(event, generation=3)
        result = TranscriptProjector().ingest([event], [approval], as_of="2026-09-16T12:00:00Z")
        self.assertEqual(result["artifact_count"], 0)

    def test_stale_approval_holds(self):
        event = mutation_event()
        approval = approval_for(event, issued="2026-09-16T09:00:00Z", expires="2026-09-16T10:00:00Z")
        result = TranscriptProjector().ingest([event], [approval], as_of="2026-09-16T12:00:00Z")
        self.assertEqual(result["artifact_count"], 0)

    def test_foreign_run_approval_holds(self):
        event = mutation_event()
        approval = approval_for(event)
        approval["run_id"] = "run_deadbeefdeadbeefdeadbeef"
        result = TranscriptProjector().ingest([event], [approval], as_of="2026-09-16T12:00:00Z")
        self.assertEqual(result["artifact_count"], 0)

    def test_denied_approval_holds(self):
        event = mutation_event()
        approval = approval_for(event)
        approval["decision"] = "DENY"
        result = TranscriptProjector().ingest([event], [approval], as_of="2026-09-16T12:00:00Z")
        self.assertEqual(result["artifact_count"], 0)

    def test_duplicate_approval_id_changed_semantics_conflicts(self):
        event = mutation_event()
        a = approval_for(event)
        b = deepcopy(a)
        b["generation"] = 9
        with self.assertRaises(ConflictError):
            TranscriptProjector().ingest([event], [a, b], as_of="2026-09-16T12:00:00Z")

    def test_approval_id_changed_across_ingests_conflicts(self):
        event = mutation_event()
        a = approval_for(event)
        b = deepcopy(a)
        b["evidence_sha256"] = "b" * 64
        projector = TranscriptProjector()
        projector.ingest([], [a], as_of="2026-09-16T12:00:00Z")
        with self.assertRaises(ConflictError):
            projector.ingest([], [b], as_of="2026-09-16T12:00:00Z")

    def test_input_order_does_not_change_artifact_bytes(self):
        f = fixture()
        a = project_fixture(f)
        g = deepcopy(f)
        g["events"].reverse()
        b = project_fixture(g)
        self.assertEqual(canonical_bytes(a["artifacts"]), canonical_bytes(b["artifacts"]))
        self.assertEqual(a["state_sha256"], b["state_sha256"])

    def test_clean_projection_is_byte_identical(self):
        f = fixture()
        self.assertEqual(canonical_bytes(project_fixture(f)), canonical_bytes(project_fixture(f)))

    def test_three_backend_shapes_are_required_strictly(self):
        f = fixture()
        for index in (0, 10, 20):
            bad = deepcopy(f["events"][index])
            bad["unexpected"] = True
            with self.assertRaises(ValidationError):
                TranscriptProjector().ingest([bad], [], as_of=f["as_of"])

    def test_bool_does_not_alias_sequence_int(self):
        f = fixture()
        bad = deepcopy(f["events"][0])
        bad["seq"] = True
        with self.assertRaises(ValidationError):
            TranscriptProjector().ingest([bad], [], as_of=f["as_of"])

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ValidationError):
            load_strict_json('{"a":1,"a":2}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValidationError):
            load_strict_json('{"a":Infinity}')

    def test_cli_create_exclusive_and_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "fixture.json"
            src.write_bytes((ROOT / "fixture.json").read_bytes())
            out1 = td / "out1.json"
            out2 = td / "out2.json"
            self.assertEqual(cli_main([str(src), str(out1)]), 0)
            self.assertEqual(cli_main([str(src), str(out2)]), 0)
            self.assertEqual(out1.read_bytes(), out2.read_bytes())
            before = out1.read_bytes()
            self.assertEqual(cli_main([str(src), str(out1)]), 2)
            self.assertEqual(out1.read_bytes(), before)

    def test_same_backend_event_id_may_repeat_in_distinct_runs(self):
        f = fixture()
        first = deepcopy(f["events"][0])
        second = deepcopy(first)
        second["run_id"] = "s-run-2"
        result = TranscriptProjector().ingest([first, second], [], as_of=f["as_of"])
        self.assertEqual(result["artifact_count"], 2)
        self.assertEqual(result["message_count"], 2)
        ids = [m["message_id"] for a in result["artifacts"] for m in a["messages"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_non_scalar_unicode_is_controlled_validation_error(self):
        f = fixture()
        bad = deepcopy(f["events"][0])
        bad["payload"]["text"] = "\ud800"
        with self.assertRaises(ValidationError):
            TranscriptProjector().ingest([bad], [], as_of=f["as_of"])
        with self.assertRaises(ValidationError):
            canonical_bytes({"bad": "\ud800"})

    def test_cli_lone_surrogate_returns_two_without_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "bad.json"
            out = td / "out.json"
            raw = (ROOT / "fixture.json").read_text(encoding="utf-8")
            raw = raw.replace("alpha one", r"\ud800", 1)
            src.write_text(raw, encoding="utf-8")
            self.assertEqual(cli_main([str(src), str(out)]), 2)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
