import copy
import unittest

from host.context_packet import (
    DIGEST_KEY,
    PacketError,
    canonical,
    compile_packet,
    markdown,
    verify_packet,
)


OP = "commons-context-dispatch-packets-20260913"


def pulse(head="abc123"):
    return {"seq": 42, "head": head, "ts": "2026-09-13T12:00:00Z"}


def ledger():
    return {
        "schema": "commons-resource-ledger/v2",
        "surfaces": [
            {
                "name": "Slack coordination",
                "kind": "AGENT_ROUTER",
                "stage": "PRODUCING",
                "consumer": OP,
                "next_action": "dispatch bounded context packet",
            },
            {
                "name": "Unrelated provider",
                "kind": "MODEL_FLEET",
                "stage": "AVAILABLE",
                "consumer": "other-work",
            },
        ],
    }


def events():
    return [
        {
            "id": "older-exact",
            "from": "Saito-Z",
            "durable_ts": "2026-09-13T12:01:00Z",
            "body": f"TAKE operation {OP}; build context packet compiler",
        },
        {
            "id": "newer-related",
            "from": "BRYCE",
            "durable_ts": "2026-09-13T12:03:00Z",
            "body": "Need context dispatch workers without rereading the whole project",
        },
        {
            "id": "newest-unrelated",
            "from": "peer",
            "durable_ts": "2026-09-13T12:04:00Z",
            "body": "totally unrelated fertilizer simulation",
        },
    ]


def claims():
    return [
        {
            "schema": "commons-change-holding/v1",
            "key": OP,
            "holder": "Saito-Z / GPT-5.6 Sol",
            "state": "ACTIVE",
            "taken_at": "2026-09-13T12:00:10Z",
            "heartbeat_at": "2026-09-13T12:02:10Z",
            "ttl_s": 1800,
            "note": "issue #13826 context dispatch",
        },
        {
            "schema": "commons-change-holding/v1",
            "key": "unrelated",
            "holder": "other",
            "state": "ACTIVE",
        },
    ]


class ContextDispatchTests(unittest.TestCase):
    def compile(self, **overrides):
        args = dict(
            operation=OP,
            objective="Compile a bounded deterministic worker context packet.",
            pulse=pulse(),
            recent=events(),
            ledger=ledger(),
            claims=claims(),
            explicit_terms=["context", "dispatch"],
            paths=["host/context_dispatch.py"],
            requested_main_head="abc123",
            provenance=[
                {"source": "pulse", "path": "pulse.json", "sha256": "1" * 64},
                {"source": "recent", "path": "recent.json", "sha256": "2" * 64},
            ],
            max_chars=12000,
            max_events=10,
            max_resources=10,
            max_claims=10,
            max_coordination=10,
        )
        args.update(overrides)
        return compile_packet(**args)

    def test_deterministic_under_input_reordering(self):
        first = self.compile()
        second = self.compile(
            recent=list(reversed(events())),
            claims=list(reversed(claims())),
            ledger={"schema": "commons-resource-ledger/v2", "surfaces": list(reversed(ledger()["surfaces"]))},
        )
        self.assertEqual(first, second)
        self.assertEqual(first[DIGEST_KEY], second[DIGEST_KEY])
        self.assertTrue(verify_packet(first)[0])

    def test_exact_operation_and_related_context_win_over_unrelated_newer_event(self):
        packet = self.compile(max_events=2)
        ids = [row["id"] for row in packet["recent"]]
        self.assertEqual(ids[0], "older-exact")
        self.assertIn("newer-related", ids)
        self.assertNotIn("newest-unrelated", ids)

    def test_budget_is_hard_and_omissions_are_explicit(self):
        many = [
            {
                "id": f"event-{index:03d}",
                "durable_ts": f"2026-09-13T12:{index % 60:02d}:00Z",
                "body": f"{OP} " + ("context " * 300),
            }
            for index in range(40)
        ]
        packet = self.compile(recent=many, max_chars=3600, max_events=40, max_resources=0, max_claims=1)
        self.assertLessEqual(len(canonical(packet)), 3600)
        self.assertGreater(packet["omitted"]["recent"], 0)
        self.assertTrue(verify_packet(packet)[0])

    def test_requested_main_mismatch_is_visible_not_relabelled(self):
        packet = self.compile(requested_main_head="different")
        fence = packet["source_fence"]
        self.assertEqual(fence["pulse_head"], "abc123")
        self.assertEqual(fence["requested_main_head"], "different")
        self.assertFalse(fence["pulse_matches_requested_main"])

    def test_unknown_event_fields_are_not_amplified(self):
        dirty = events()
        dirty[0]["unexpected_field"] = "must-not-amplify"
        dirty[0]["nested_metadata"] = {"internal_note": "also-must-not-amplify"}
        packet = self.compile(recent=dirty)
        rendered = canonical(packet)
        self.assertNotIn("must-not-amplify", rendered)
        self.assertNotIn("also-must-not-amplify", rendered)
        # Event fields are allowlisted before packetization.

    def test_digest_detects_tamper(self):
        packet = self.compile()
        tampered = copy.deepcopy(packet)
        tampered["objective"] += " tampered"
        self.assertEqual(verify_packet(tampered), (False, "digest-mismatch"))

    def test_markdown_is_derived_from_verified_packet(self):
        packet = self.compile()
        text = markdown(packet)
        self.assertIn(OP, text)
        self.assertIn(packet[DIGEST_KEY], text)
        self.assertIn("Ownership / claims", text)
        self.assertIn("Relevant durable events", text)

    def test_too_small_budget_is_rejected(self):
        with self.assertRaises(PacketError):
            self.compile(max_chars=1024)


if __name__ == "__main__":
    unittest.main()
