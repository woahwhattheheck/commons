from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
