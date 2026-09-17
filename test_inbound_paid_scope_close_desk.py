from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from revenue.inbound_paid_scope_close_desk.engine import (
    CloseDeskError,
    INPUT_SCHEMA,
    TRUTH_BOUNDARY,
    _cli,
    authority_flags,
    canonical_json,
    compile_bundle,
    load_json,
    verify_bundle,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64
SHA_F = "f" * 64
SHA_1 = "1" * 64
SHA_2 = "2" * 64


def ready_value():
    return {
        "schema": INPUT_SCHEMA,
        "truth_boundary": TRUTH_BOUNDARY,
        "case_id": "case-001",
        "evaluation_time": "2026-09-16T20:30:00Z",
        "max_event_age_seconds": 86400,
        "max_evidence_age_seconds": 2592000,
        "fixture": False,
        "event": {
            "event_id": "evt-001",
            "provider": "gmail",
            "conversation_id": "thread-42",
            "message_id": "msg-99",
            "observed_at": "2026-09-16T20:20:00Z",
            "sender_role": "EXTERNAL_HUMAN",
            "event_class": "HUMAN_SCOPE_REQUEST",
            "source_authority": "PROVIDER_RECEIPT",
            "source_uri": "provider:gmail/thread-42/msg-99",
            "source_sha256": SHA_A,
            "text_sha256": SHA_B,
        },
        "offer": {
            "offer_id": "fixed-pilot-v1",
            "observed_at": "2026-09-16T19:00:00Z",
            "source_uri": "repo:offer/fixed-pilot-v1",
            "source_sha256": SHA_C,
            "commercial_state": "PROPOSED_NOT_ACCEPTED",
            "currency": "USD",
            "fixed_amount_minor": 2500000,
            "deliverables": ["bounded evidence review", "deterministic owner packet"],
            "acceptance_questions": ["Who owns source access?", "What is the acceptance date?"],
            "exclusions": ["no production mutation", "no buyer acceptance implied"],
        },
        "capability_evidence": [
            {
                "evidence_id": "merge-384",
                "observed_at": "2026-09-10T12:00:00Z",
                "source_uri": "https://github.com/example/repo/pull/384",
                "source_sha256": SHA_D,
                "status": "VERIFIED",
                "claim": "Public merged delivery receipt exists for the bounded technical change.",
                "public": True,
            },
            {
                "evidence_id": "private-ops-note",
                "observed_at": "2026-09-15T12:00:00Z",
                "source_uri": "private:ops-note",
                "source_sha256": SHA_E,
                "status": "VERIFIED",
                "claim": "Private owner-only delivery planning evidence.",
                "public": False,
            },
        ],
        "qualification": {
            "status": "PRIME_SUPPORTED",
            "source_uri": "repo:qualification/latest",
            "source_sha256": SHA_F,
            "observed_at": "2026-09-16T18:00:00Z",
            "gaps": [],
        },
        "route": {
            "status": "REPLY_ONLY",
            "provider": "gmail",
            "canonical_opportunity_key": "orgx-paid-pilot",
            "recipient_key": "route-opaque-1",
            "action_key": "reply-scope-questions-v1",
            "collision_state": "CLEAR",
            "source_uri": "slack:route-census/123",
            "source_sha256": SHA_1,
            "observed_at": "2026-09-16T20:25:00Z",
        },
        "muse": {
            "status": "SELECTED",
            "election_id": "muse-election-7",
            "canonical_opportunity_key": "orgx-paid-pilot",
            "action_key": "reply-scope-questions-v1",
            "selected_sender_id": "swarm-z",
            "observed_at": "2026-09-16T20:26:00Z",
            "expires_at": "2026-09-16T20:45:00Z",
            "source_uri": "slack:muse-dm/456",
            "source_sha256": SHA_2,
        },
        "prior_touch": {
            "state": "CLEAR",
            "contact_count": 1,
            "last_contact_at": "2026-09-15T12:00:00Z",
            "last_action_key": "initial-intro-v1",
            "source_uri": "ledger:prior-touch/1",
            "source_sha256": SHA_A,
        },
    }


def raw(value=None):
    return canonical_json(ready_value() if value is None else value)


def packet_for(value=None):
    p, m, r = compile_bundle(raw(value))
    return load_json(p, "packet"), p, m, r


class CloseDeskTests(unittest.TestCase):
    def test_ready_human_scope_request(self):
        packet, pb, mb, rb = packet_for()
        self.assertEqual(packet["decision"], "READY_FOR_OWNER_CLOSE")
        self.assertEqual(verify_bundle(raw(), pb, mb, rb), "EXACT_OWNER_CLOSE_MATCH")
        self.assertEqual(packet["authority"], authority_flags())
        self.assertTrue(all(v is False for v in packet["authority"].values()))

    def test_human_positive_also_eligible(self):
        v = ready_value()
        v["event"]["event_class"] = "HUMAN_POSITIVE"
        self.assertEqual(packet_for(v)[0]["decision"], "READY_FOR_OWNER_CLOSE")

    def test_auto_ack_never_counts_as_interest(self):
        v = ready_value()
        v["event"]["event_class"] = "AUTO_ACK"
        v["event"]["sender_role"] = "AUTOMATION"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_SCOPE")

    def test_support_ticket_never_counts_as_interest(self):
        v = ready_value()
        v["event"]["event_class"] = "SUPPORT_TICKET"
        v["event"]["sender_role"] = "SYSTEM"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_SCOPE")

    def test_silence_never_counts_as_interest(self):
        v = ready_value()
        v["event"]["event_class"] = "SILENCE"
        v["event"]["sender_role"] = "UNKNOWN"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_SCOPE")

    def test_curated_export_human_label_does_not_mint_human_interest(self):
        v = ready_value()
        v["event"]["source_authority"] = "CURATED_EXPORT"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_SCOPE")

    def test_stale_event_holds_scope(self):
        v = ready_value()
        v["max_event_age_seconds"] = 60
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_SCOPE")

    def test_future_event_rejected(self):
        v = ready_value()
        v["event"]["observed_at"] = "2026-09-16T20:31:00Z"
        with self.assertRaises(CloseDeskError):
            compile_bundle(raw(v))

    def test_fixture_never_becomes_live_ready(self):
        v = ready_value()
        v["fixture"] = True
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_SYNTHETIC")

    def test_dnr_dominates(self):
        v = ready_value()
        v["route"]["status"] = "DNR"
        self.assertEqual(packet_for(v)[0]["decision"], "DNR")

    def test_collision_other_owner_holds_route(self):
        v = ready_value()
        v["route"]["collision_state"] = "ACTIVE_OTHER_OWNER"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_ROUTE")

    def test_prior_touch_unknown_holds_route(self):
        v = ready_value()
        v["prior_touch"]["state"] = "UNKNOWN"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_ROUTE")

    def test_provider_mismatch_holds_route(self):
        v = ready_value()
        v["route"]["provider"] = "slack"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_ROUTE")

    def test_route_stale_holds(self):
        v = ready_value()
        v["max_event_age_seconds"] = 60
        v["event"]["observed_at"] = "2026-09-16T20:29:30Z"
        v["route"]["observed_at"] = "2026-09-16T20:20:00Z"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_ROUTE")

    def test_missing_capability_evidence_holds(self):
        v = ready_value()
        v["capability_evidence"][0]["status"] = "MISSING"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_EVIDENCE")

    def test_expired_verified_evidence_is_truth_narrowed(self):
        v = ready_value()
        v["max_evidence_age_seconds"] = 60
        v["offer"]["observed_at"] = "2026-09-16T20:29:30Z"
        v["qualification"]["observed_at"] = "2026-09-16T20:29:30Z"
        v["capability_evidence"][0]["observed_at"] = "2026-09-16T20:00:00Z"
        v["capability_evidence"][1]["observed_at"] = "2026-09-16T20:29:30Z"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_EVIDENCE")

    def test_qualification_hold_blocks(self):
        v = ready_value()
        v["qualification"]["status"] = "HOLD_MISSING_EVIDENCE"
        v["qualification"]["gaps"] = ["insurance evidence"]
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_EVIDENCE")

    def test_partner_only_can_reach_owner_close(self):
        v = ready_value()
        v["qualification"]["status"] = "PARTNER_ONLY"
        v["qualification"]["gaps"] = ["prime must supply reference"]
        self.assertEqual(packet_for(v)[0]["decision"], "READY_FOR_OWNER_CLOSE")

    def test_muse_unrequested_holds(self):
        v = ready_value()
        v["muse"]["status"] = "UNREQUESTED"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_MUSE")

    def test_muse_mismatched_opportunity_holds(self):
        v = ready_value()
        v["muse"]["canonical_opportunity_key"] = "different-opportunity"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_MUSE")

    def test_muse_mismatched_action_holds(self):
        v = ready_value()
        v["muse"]["action_key"] = "different-action"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_MUSE")

    def test_expired_muse_holds(self):
        v = ready_value()
        v["muse"]["expires_at"] = "2026-09-16T20:27:00Z"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_MUSE")

    def test_muse_selected_never_authorizes_send(self):
        packet = packet_for()[0]
        self.assertEqual(packet["muse"]["status"], "SELECTED")
        self.assertFalse(packet["authority"]["external_send_authorized"])
        self.assertIn("single-writer coordination", packet["muse"]["meaning"])

    def test_private_evidence_claim_not_in_markdown(self):
        packet, pb, mb, rb = packet_for()
        text = mb.decode()
        self.assertNotIn("Private owner-only delivery planning evidence", text)
        self.assertNotIn("private:ops-note", text)
        self.assertIn("private evidence item", text)

    def test_source_uri_not_leaked_into_public_evidence_packet(self):
        packet = packet_for()[0]
        self.assertNotIn("source_uri", packet["public_capability_evidence"][0])

    def test_duplicate_json_keys_rejected(self):
        bad = b'{"schema":"x","schema":"y"}'
        with self.assertRaisesRegex(CloseDeskError, "duplicate JSON key"):
            load_json(bad)

    def test_float_nonfinite_and_bool_int_rejected(self):
        for text in [b'{"x":1.5}', b'{"x":NaN}', b'{"x":Infinity}']:
            with self.subTest(text=text):
                with self.assertRaises(CloseDeskError):
                    load_json(text)
        v = ready_value()
        v["offer"]["fixed_amount_minor"] = True
        with self.assertRaisesRegex(CloseDeskError, "integer required"):
            compile_bundle(raw(v))

    def test_unknown_keys_rejected(self):
        v = ready_value()
        v["unexpected"] = "nope"
        with self.assertRaisesRegex(CloseDeskError, "keys mismatch"):
            compile_bundle(raw(v))

    def test_tampered_packet_rejected(self):
        pb, mb, rb = compile_bundle(raw())
        p = load_json(pb, "packet")
        p["decision"] = "DNR"
        with self.assertRaisesRegex(CloseDeskError, "bundle mismatch"):
            verify_bundle(raw(), canonical_json(p), mb, rb)

    def test_tampered_markdown_rejected(self):
        pb, mb, rb = compile_bundle(raw())
        with self.assertRaisesRegex(CloseDeskError, "bundle mismatch"):
            verify_bundle(raw(), pb, mb + b"x", rb)

    def test_tampered_receipt_rejected(self):
        pb, mb, rb = compile_bundle(raw())
        receipt = load_json(rb, "receipt")
        receipt["input_sha256"] = "0" * 64
        with self.assertRaisesRegex(CloseDeskError, "bundle mismatch"):
            verify_bundle(raw(), pb, mb, canonical_json(receipt))

    def test_input_one_byte_change_breaks_old_bundle(self):
        pb, mb, rb = compile_bundle(raw())
        v = ready_value()
        v["offer"]["deliverables"][0] += " changed"
        with self.assertRaisesRegex(CloseDeskError, "bundle mismatch"):
            verify_bundle(raw(v), pb, mb, rb)

    def test_deterministic_compile(self):
        self.assertEqual(compile_bundle(raw()), compile_bundle(raw()))

    def test_cli_compile_verify_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "input.json"
            packet = root / "packet.json"
            markdown = root / "packet.md"
            receipt = root / "receipt.json"
            inp.write_bytes(raw())
            self.assertEqual(
                _cli(["compile", str(inp), "--packet", str(packet), "--markdown", str(markdown), "--receipt", str(receipt)]),
                0,
            )
            self.assertEqual(_cli(["verify", str(inp), str(packet), str(markdown), str(receipt)]), 0)
            self.assertEqual(
                _cli(["compile", str(inp), "--packet", str(packet), "--markdown", str(markdown), "--receipt", str(receipt)]),
                2,
            )

    def test_cli_preflight_prevents_partial_publication(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "input.json"
            packet = root / "packet.json"
            markdown = root / "packet.md"
            receipt = root / "receipt.json"
            inp.write_bytes(raw())
            markdown.write_text("foreign")
            self.assertEqual(
                _cli(["compile", str(inp), "--packet", str(packet), "--markdown", str(markdown), "--receipt", str(receipt)]),
                2,
            )
            self.assertFalse(packet.exists())
            self.assertFalse(receipt.exists())
            self.assertEqual(markdown.read_text(), "foreign")

    def test_output_paths_must_be_distinct(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "input.json"
            out = root / "out"
            receipt = root / "receipt"
            inp.write_bytes(raw())
            self.assertEqual(
                _cli(["compile", str(inp), "--packet", str(out), "--markdown", str(out), "--receipt", str(receipt)]),
                2,
            )
            self.assertFalse(out.exists())
            self.assertFalse(receipt.exists())

    def test_muse_status_denied_is_not_dnr_without_route_dnr(self):
        v = ready_value()
        v["muse"]["status"] = "DENIED"
        self.assertEqual(packet_for(v)[0]["decision"], "HOLD_MUSE")

    def test_payment_link_or_merge_cannot_be_event_class(self):
        v = ready_value()
        v["event"]["event_class"] = "MERGED_PR"
        with self.assertRaisesRegex(CloseDeskError, "unsupported value"):
            compile_bundle(raw(v))

    def test_receipt_contains_no_positive_authority(self):
        _, _, rb = compile_bundle(raw())
        receipt = load_json(rb, "receipt")
        self.assertTrue(all(v is False for v in receipt["authority"].values()))


if __name__ == "__main__":
    unittest.main()
