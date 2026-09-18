from __future__ import annotations

import re
import unittest
from datetime import datetime, timedelta, timezone

from tools.relationship_contact_guard import guard
from tools.relationship_contact_guard.guard import GuardError, compile_guard, verify_guard


def candidate(**overrides):
    row = {
        "counterparty_id": "example.com",
        "opportunity_id": "example-rfp-1",
        "route": "sales@example.com",
        "purpose": "paid-qa-workshare",
    }
    row.update(overrides)
    return row


class RelationshipGuardDirectBoundaryTests(unittest.TestCase):
    def test_direct_compile_huge_integer_is_guarderror(self):
        packet = {
            "candidate": candidate(relationship_cooldown_seconds=10**5000),
            "events": [],
        }
        with self.assertRaisesRegex(GuardError, "integer outside supported"):
            compile_guard(packet)

    def test_direct_verify_huge_integer_artifact_is_guarderror(self):
        packet = {"candidate": candidate(), "events": []}
        artifact = compile_guard(packet)
        artifact["decision"]["retained_event_count"] = 10**5000
        with self.assertRaisesRegex(GuardError, "integer outside supported"):
            verify_guard(packet, artifact)

    def test_direct_deep_object_is_guarderror_not_recursionerror(self):
        deep: object = "leaf"
        for _ in range(guard.MAX_JSON_DEPTH + 2):
            deep = [deep]
        packet = {"candidate": candidate(), "events": [], "deep": deep}
        with self.assertRaisesRegex(GuardError, "depth limit"):
            compile_guard(packet)

    def test_direct_oversize_canonical_packet_is_guarderror(self):
        packet = {
            "candidate": candidate(purpose="p"),
            "events": [],
            "padding": "x" * (guard.MAX_JSON_BYTES + 1),
        }
        with self.assertRaisesRegex(GuardError, "canonical bytes"):
            compile_guard(packet)

    def test_direct_oversized_list_hits_node_fence_before_child_inspection(self):
        hostile_events = [object()] + [None] * guard.MAX_JSON_NODES
        packet = {"candidate": candidate(), "events": hostile_events}
        with self.assertRaisesRegex(GuardError, "node limit exceeded before child traversal"):
            compile_guard(packet)

    def test_direct_oversized_dict_hits_key_value_node_fence_before_child_inspection(self):
        hostile = {"trap": object()}
        hostile.update({f"k{i:05d}": None for i in range((guard.MAX_JSON_NODES // 2) + 1)})
        packet = {"candidate": candidate(), "events": [], "hostile": hostile}
        with self.assertRaisesRegex(GuardError, "node limit exceeded before child traversal"):
            compile_guard(packet)

    def test_direct_oversize_string_rejects_before_serializer_entry(self):
        packet = {
            "candidate": candidate(purpose="p"),
            "events": [],
            "padding": "x" * (guard.MAX_JSON_BYTES + 1),
        }
        original = guard.json.dumps
        calls = 0

        def bomb(*args, **kwargs):
            nonlocal calls
            calls += 1
            raise AssertionError("full canonical serializer entered")

        guard.json.dumps = bomb
        try:
            with self.assertRaisesRegex(GuardError, "canonical bytes"):
                compile_guard(packet)
            self.assertEqual(calls, 0)
        finally:
            guard.json.dumps = original

    def test_direct_ensure_ascii_del_escape_rejects_before_serializer_entry(self):
        packet = {
            "candidate": candidate(purpose="p"),
            "events": [],
            "padding": "\x7f" * ((guard.MAX_JSON_BYTES // 6) + 1),
        }
        original = guard.json.dumps
        calls = 0

        def bomb(*args, **kwargs):
            nonlocal calls
            calls += 1
            raise AssertionError("full canonical serializer entered")

        guard.json.dumps = bomb
        try:
            with self.assertRaisesRegex(GuardError, "canonical bytes"):
                compile_guard(packet)
            self.assertEqual(calls, 0)
        finally:
            guard.json.dumps = original

    def test_exported_policy_rebinding_cannot_weaken_loaded_generation(self):
        occurred_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).replace(microsecond=0)
        sent = {
            "event_id": "sent-policy-root-1",
            "kind": "PROVIDER_SENT",
            "occurred_at": occurred_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "counterparty_id": "example.com",
            "opportunity_id": "other-rfp",
            "route": "other@example.com",
            "purpose": "other-purpose",
            "provider_message_id": "msg-policy-root-1",
        }
        packet = {"candidate": candidate(), "events": [sent]}
        artifact = compile_guard(packet)
        self.assertEqual(artifact["decision"]["status"], "HOLD_RECENT_COUNTERPARTY_CONTACT")

        names = (
            "MIN_RELATIONSHIP_COOLDOWN_SECONDS",
            "MIN_PURSUIT_COOLDOWN_SECONDS",
            "MAX_JSON_BYTES",
            "MAX_EVENTS",
            "MAX_SAFE_INTEGER",
            "MAX_JSON_DEPTH",
            "MAX_JSON_NODES",
            "IDENT_RE",
            "OPAQUE_RE",
            "HEX64_RE",
            "KINDS",
            "SCOPES",
            "SCHEMA",
            "ARTIFACT_SCHEMA",
            "VERIFICATION_SCHEMA",
            "AUTHORITY",
        )
        original = {name: getattr(guard, name) for name in names}
        try:
            guard.MIN_RELATIONSHIP_COOLDOWN_SECONDS = 0
            guard.MIN_PURSUIT_COOLDOWN_SECONDS = 0
            guard.MAX_JSON_BYTES = 10**9
            guard.MAX_EVENTS = 10**9
            guard.MAX_SAFE_INTEGER = 10**100
            guard.MAX_JSON_DEPTH = 10**6
            guard.MAX_JSON_NODES = 10**9
            guard.IDENT_RE = re.compile(r".*")
            guard.OPAQUE_RE = re.compile(r".*")
            guard.HEX64_RE = re.compile(r".*")
            guard.KINDS = {"EVIL"}
            guard.SCOPES = {"EVIL"}
            guard.SCHEMA = "evil-schema"
            guard.ARTIFACT_SCHEMA = "evil-artifact"
            guard.VERIFICATION_SCHEMA = "evil-verification"
            guard.AUTHORITY = {"send_authorized": True}

            zero_packet = {
                "candidate": candidate(
                    relationship_cooldown_seconds=0,
                    pursuit_cooldown_seconds=0,
                ),
                "events": [sent],
            }
            with self.assertRaisesRegex(GuardError, "integer must be >= 21600"):
                compile_guard(zero_packet)

            fresh = compile_guard(packet)
            self.assertEqual(fresh["artifact_schema"], "relationship-contact-guard-artifact/v3")
            self.assertEqual(fresh["decision"]["schema"], "relationship-contact-guard/v3")
            self.assertEqual(fresh["decision"]["status"], "HOLD_RECENT_COUNTERPARTY_CONTACT")
            self.assertFalse(any(fresh["decision"]["authority"].values()))

            verified = verify_guard(packet, artifact)
            self.assertEqual(verified["verification_schema"], "relationship-contact-guard-verification/v1")
            self.assertEqual(verified["fresh_status"], "HOLD_RECENT_COUNTERPARTY_CONTACT")
            self.assertFalse(any(verified["authority"].values()))

            bad_kind = dict(sent)
            bad_kind["event_id"] = "bad-kind-1"
            bad_kind["provider_message_id"] = "bad-kind-msg-1"
            bad_kind["kind"] = "EVIL"
            with self.assertRaisesRegex(GuardError, "unsupported event kind"):
                compile_guard({"candidate": candidate(), "events": [bad_kind]})

            bad_ident = {"candidate": candidate(counterparty_id="UPPER"), "events": []}
            with self.assertRaisesRegex(GuardError, "canonical lowercase ASCII identifier"):
                compile_guard(bad_ident)

            scoped_send = dict(sent)
            scoped_send.update({
                "event_id": "scope-send-1",
                "provider_message_id": "scope-msg-1",
                "opportunity_id": "example-rfp-1",
                "route": "sales@example.com",
                "purpose": "paid-qa-workshare",
            })
            negative = {
                "event_id": "scope-negative-1",
                "kind": "HUMAN_NEGATIVE",
                "occurred_at": occurred_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "counterparty_id": "example.com",
                "opportunity_id": "example-rfp-1",
                "route": "sales@example.com",
                "purpose": "paid-qa-workshare",
                "in_reply_to_message_id": "scope-msg-1",
                "scope": "EVIL",
            }
            with self.assertRaisesRegex(GuardError, "requires valid scope"):
                compile_guard({"candidate": candidate(), "events": [scoped_send, negative]})

            deep = "leaf"
            for _ in range(guard.MAX_JSON_DEPTH if guard.MAX_JSON_DEPTH < 1000 else 66):
                deep = [deep]
            with self.assertRaisesRegex(GuardError, "depth limit"):
                compile_guard({"candidate": candidate(), "events": [], "deep": deep})
        finally:
            for name, value in original.items():
                setattr(guard, name, value)

    def test_public_entrypoints_reject_dependency_injection(self):
        packet = {"candidate": candidate(), "events": []}
        forged = {"artifact_schema": "forged", "decision": {"status": "NO_CONFLICT_FOUND"}}

        with self.assertRaises(TypeError):
            compile_guard(packet, _compile_at_fn=lambda frozen, now, mode: forged)

        artifact = compile_guard(packet)
        with self.assertRaises(TypeError):
            verify_guard(packet, artifact, _digest_fn=lambda value: "0" * 64)

        with self.assertRaises(TypeError):
            verify_guard(packet, artifact, _canonical_bytes_fn=lambda value: b"forged")

    def test_bounded_file_prefix_requests_only_limit_plus_one(self):
        calls = []

        class Reader:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self, size=-1):
                calls.append(size)
                if size < 0:
                    raise AssertionError("unbounded file read attempted")
                return b"x" * size

        reader = Reader()

        def fake_open(path, mode):
            self.assertEqual(mode, "rb")
            return reader

        raw = guard._bounded_file_prefix(
            guard.Path("ignored.json"),
            guard.MAX_JSON_BYTES,
            _path_open=fake_open,
        )
        self.assertEqual(calls, [guard.MAX_JSON_BYTES + 1])
        self.assertEqual(len(raw), guard.MAX_JSON_BYTES + 1)

    def test_remaining_helper_rebinding_cannot_weaken_loaded_public_generation(self):
        original_size = guard._json_string_size
        original_decode_error = guard.json.JSONDecodeError
        try:
            guard._json_string_size = lambda value, path, remaining: 0
            guard.json.JSONDecodeError = RuntimeError

            packet = {
                "candidate": candidate(purpose="p"),
                "events": [],
                "padding": "x" * (guard.MAX_JSON_BYTES + 1),
            }
            with self.assertRaisesRegex(GuardError, "canonical bytes"):
                compile_guard(packet)

            with self.assertRaises(GuardError):
                guard._decode_json_bytes(b"{", "broken.json")
        finally:
            guard._json_string_size = original_size
            guard.json.JSONDecodeError = original_decode_error


if __name__ == "__main__":
    unittest.main()
