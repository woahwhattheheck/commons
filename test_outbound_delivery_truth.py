import copy
import json
import pathlib
import unittest

from coordination import outbound_delivery_truth as m


def sha(ch):
    return ch * 64


def packet(events=None):
    return {
        "schema": m.INPUT_SCHEMA,
        "submission": {
            "operation_key": "LEAD-ACME-001",
            "counterparty": "Acme Corp",
            "purpose": "paid controls workshare",
            "provider": "gmail",
            "provider_message_id": "msg-001",
            "provider_thread_id": "thr-001",
            "sender": "sales@example.com",
            "recipient": "ops@acme.example",
            "submitted_at": "2026-09-17T23:09:00Z",
            "source_ref": "gmail:sent:msg-001",
            "source_sha256": sha("a"),
        },
        "events": list(events or []),
    }


def event(
    *,
    eid="e1",
    source="b",
    observed="2026-09-17T23:10:00Z",
    kind="DSN",
    message="msg-001",
    thread="thr-001",
    sender="sales@example.com",
    recipient="ops@acme.example",
    action="failed",
    status="5.4.1",
    diagnostic="smtp; 550 5.4.1 Recipient address rejected",
):
    return {
        "id": eid,
        "kind": kind,
        "observed_at": observed,
        "provider": "gmail",
        "original_message_id": message,
        "original_thread_id": thread,
        "sender": sender,
        "recipient": recipient,
        "action": action,
        "status": status,
        "diagnostic_code": diagnostic,
        "source_ref": f"gmail:dsn:{eid}",
        "source_sha256": sha(source),
    }


class DeliveryTruthTests(unittest.TestCase):
    def test_hard_dsn_downgrades_sent_and_kills_route_without_contact_claim(self):
        art = m.compile_delivery_truth(packet([event()]))
        self.assertEqual(art["delivery_state"], "DELIVERY_FAILED")
        self.assertEqual(art["state_transition"][1], "PROVIDER_SUBMITTED_PENDING_DELIVERY")
        p = art["collision_projection"]
        self.assertFalse(p["organization_contact_confirmed"])
        self.assertEqual(p["route_viability"], "DEAD_ROUTE_EVIDENCE")
        self.assertTrue(p["same_route_dedupe_hold"])
        self.assertFalse(p["same_route_resend_authorized"])
        self.assertFalse(p["alternate_route_send_authorized"])
        self.assertFalse(p["counts_as_revenue"])

    def test_no_dsn_never_becomes_delivery_confirmation(self):
        art = m.compile_delivery_truth(packet())
        self.assertEqual(art["delivery_state"], "DELIVERY_UNKNOWN")
        self.assertFalse(art["collision_projection"]["counts_as_contacted"])
        self.assertFalse(art["evidence_claims"]["absence_of_dsn_is_delivery"])

    def test_bound_positive_delivery_evidence_can_confirm_contact(self):
        ev = event(
            kind="PROVIDER_DELIVERY_CONFIRMATION",
            action="delivered",
            status="2.0.0",
            diagnostic="provider retained final delivery confirmation",
        )
        art = m.compile_delivery_truth(packet([ev]))
        self.assertEqual(art["delivery_state"], "DELIVERED_EVIDENCE")
        self.assertTrue(art["collision_projection"]["organization_contact_confirmed"])
        self.assertTrue(art["collision_projection"]["counts_as_contacted"])
        self.assertFalse(art["collision_projection"]["counts_as_revenue"])

    def test_wrong_message_dsn_is_unbound_not_failure(self):
        ev = event(message="msg-other")
        art = m.compile_delivery_truth(packet([ev]))
        self.assertEqual(art["delivery_state"], "DELIVERY_UNKNOWN")
        self.assertIn("message", art["evaluated_evidence"][0]["binding_mismatches"])

    def test_wrong_recipient_dsn_is_unbound(self):
        ev = event(recipient="other@acme.example")
        art = m.compile_delivery_truth(packet([ev]))
        self.assertEqual(art["delivery_state"], "DELIVERY_UNKNOWN")
        self.assertIn("recipient", art["evaluated_evidence"][0]["binding_mismatches"])

    def test_thread_alias_collision_does_not_bind(self):
        ev = event(thread="thr-other")
        art = m.compile_delivery_truth(packet([ev]))
        self.assertEqual(art["delivery_state"], "DELIVERY_UNKNOWN")
        self.assertIn("thread", art["evaluated_evidence"][0]["binding_mismatches"])

    def test_duplicate_retained_source_rejected(self):
        ev1 = event(eid="e1", source="b")
        ev2 = event(eid="e2", source="b", diagnostic="a different provider fact")
        with self.assertRaises(m.DeliveryTruthError):
            m.compile_delivery_truth(packet([ev1, ev2]))

    def test_semantic_remint_under_new_id_ref_and_blob_is_rejected(self):
        ev1 = event(eid="e1", source="b")
        ev2 = event(eid="e2", source="c", observed="2026-09-17T23:11:00Z")
        with self.assertRaisesRegex(m.DeliveryTruthError, "reminted duplicate"):
            m.compile_delivery_truth(packet([ev1, ev2]))

    def test_delayed_soft_failure_stays_unknown(self):
        ev = event(action="delayed", status="4.4.1", diagnostic="smtp; 451 temporary route issue")
        art = m.compile_delivery_truth(packet([ev]))
        self.assertEqual(art["delivery_state"], "DELIVERY_UNKNOWN")
        self.assertEqual(art["evaluated_evidence"][0]["classification"], "SOFT_FAILURE")

    def test_forged_free_text_bounce_cannot_override_structured_status(self):
        ev = event(
            action="delayed",
            status="4.2.0",
            diagnostic="550 5.1.1 HARD BOUNCE recipient does not exist",
        )
        art = m.compile_delivery_truth(packet([ev]))
        self.assertEqual(art["delivery_state"], "DELIVERY_UNKNOWN")
        self.assertEqual(art["evaluated_evidence"][0]["classification"], "SOFT_FAILURE")

    def test_conflicting_terminal_evidence_fails_to_unknown(self):
        fail = event(eid="fail", source="b")
        ok = event(
            eid="ok",
            source="c",
            kind="PROVIDER_DELIVERY_CONFIRMATION",
            action="delivered",
            status="2.0.0",
            diagnostic="final delivery",
        )
        art = m.compile_delivery_truth(packet([fail, ok]))
        self.assertEqual(art["delivery_state"], "DELIVERY_UNKNOWN")
        self.assertEqual(art["reason"], "conflicting_terminal_evidence")

    def test_evidence_before_submission_is_rejected(self):
        with self.assertRaisesRegex(m.DeliveryTruthError, "predates provider submission"):
            m.compile_delivery_truth(packet([event(observed="2026-09-17T23:08:59Z")]))

    def test_timestamp_must_be_canonical_whole_second_utc(self):
        p = packet()
        p["submission"]["submitted_at"] = "2026-09-17T23:09:00+00:00"
        with self.assertRaises(m.DeliveryTruthError):
            m.compile_delivery_truth(p)
        with self.assertRaises(m.DeliveryTruthError):
            m.compile_delivery_truth(packet([event(observed="2026-09-17T23:10:00.123Z")]))

    def test_verify_detects_artifact_tamper(self):
        p = packet([event()])
        art = m.compile_delivery_truth(p)
        self.assertTrue(m.verify_delivery_truth(p, art)["valid"])
        bad = copy.deepcopy(art)
        bad["delivery_state"] = "DELIVERED_EVIDENCE"
        self.assertFalse(m.verify_delivery_truth(p, bad)["valid"])

    def test_verify_detects_source_change_even_if_artifact_untouched(self):
        p = packet([event()])
        art = m.compile_delivery_truth(p)
        p2 = copy.deepcopy(p)
        p2["submission"]["purpose"] = "different purpose"
        self.assertFalse(m.verify_delivery_truth(p2, art)["valid"])

    def test_bool_or_float_not_smuggled_into_packet(self):
        p = packet()
        p["submission"]["provider_message_id"] = True
        with self.assertRaises(m.DeliveryTruthError):
            m.compile_delivery_truth(p)
        p = packet([event()])
        p["events"][0]["status"] = 5.1
        with self.assertRaises(m.DeliveryTruthError):
            m.compile_delivery_truth(p)

    def test_authority_is_hard_false(self):
        art = m.compile_delivery_truth(packet([event()]))
        self.assertTrue(all(value is False for value in art["authority"].values()))
        proj = m.collision_projection(art)
        self.assertFalse(proj["same_route_resend_authorized"])
        self.assertFalse(proj["alternate_route_send_authorized"])

    def test_retained_examples_replay_to_declared_states(self):
        path = pathlib.Path(__file__).parent / "coordination" / "outbound_delivery_truth.examples.json"
        examples = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(examples["schema"], "commons.outbound-delivery-examples/v1")
        self.assertEqual(len(examples["cases"]), 3)
        for case in examples["cases"]:
            artifact = m.compile_delivery_truth(case["packet"])
            self.assertEqual(artifact["delivery_state"], case["expected_state"])
            self.assertTrue(m.verify_delivery_truth(case["packet"], artifact)["valid"])


if __name__ == "__main__":
    unittest.main()
