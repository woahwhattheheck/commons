import copy
import subprocess
import sys
import unittest

from coordination import outbound_delivery_truth as m


def sha(ch):
    return ch * 64


def packet(events=None):
    return {
        "schema": m.INPUT_SCHEMA,
        "submission": {
            "operation_key": "SYNTH-LEAD-001",
            "counterparty": "Synthetic Counterparty",
            "purpose": "synthetic workshare",
            "provider": "synthetic-mail",
            "provider_message_id": "msg-001",
            "provider_thread_id": "thr-001",
            "sender": "sender-token",
            "recipient": "recipient-token",
            "submitted_at": "2026-09-17T23:09:00Z",
            "source_ref": "synthetic:submission:msg-001",
            "source_sha256": sha("a"),
        },
        "events": list(events or []),
    }


def legacy_packet(events=None):
    p = packet(events)
    p["legacy_local_sent"] = p["submission"]
    p["submission"] = None
    return p


def event(
    *,
    eid="e1",
    source="b",
    observed="2026-09-17T23:10:00Z",
    kind="DSN",
    message="msg-001",
    thread="thr-001",
    sender="sender-token",
    recipient="recipient-token",
    action="failed",
    status="5.4.1",
    diagnostic="synthetic permanent route failure",
):
    return {
        "id": eid,
        "kind": kind,
        "observed_at": observed,
        "provider": "synthetic-mail",
        "original_message_id": message,
        "original_thread_id": thread,
        "sender": sender,
        "recipient": recipient,
        "action": action,
        "status": status,
        "diagnostic_code": diagnostic,
        "source_ref": f"synthetic:evidence:{eid}",
        "source_sha256": sha(source),
    }


class DeliveryTruthTests(unittest.TestCase):
    def test_hard_dsn_downgrades_submission_and_kills_route_without_contact_claim(self):
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
        self.assertEqual(art["delivery_state"], "PROVIDER_SUBMITTED_PENDING_DELIVERY")
        self.assertEqual(art["state_transition"], ["UNSENT", "PROVIDER_SUBMITTED_PENDING_DELIVERY"])
        self.assertFalse(art["collision_projection"]["counts_as_contacted"])
        self.assertFalse(art["evidence_claims"]["absence_of_dsn_is_delivery"])

    def test_bound_positive_delivery_evidence_can_confirm_contact(self):
        ev = event(
            kind="PROVIDER_DELIVERY_CONFIRMATION",
            action="delivered",
            status="2.0.0",
            diagnostic="synthetic retained delivery confirmation",
        )
        art = m.compile_delivery_truth(packet([ev]))
        self.assertEqual(art["delivery_state"], "DELIVERED_EVIDENCE")
        self.assertTrue(art["collision_projection"]["organization_contact_confirmed"])
        self.assertTrue(art["collision_projection"]["counts_as_contacted"])
        self.assertFalse(art["collision_projection"]["counts_as_revenue"])

    def test_wrong_message_dsn_is_unbound_not_failure(self):
        art = m.compile_delivery_truth(packet([event(message="msg-other")]))
        self.assertEqual(art["delivery_state"], "DELIVERY_UNKNOWN")
        self.assertIn("message", art["evaluated_evidence"][0]["binding_mismatches"])

    def test_wrong_recipient_dsn_is_unbound(self):
        art = m.compile_delivery_truth(packet([event(recipient="other-recipient")]))
        self.assertEqual(art["delivery_state"], "DELIVERY_UNKNOWN")
        self.assertIn("recipient", art["evaluated_evidence"][0]["binding_mismatches"])

    def test_thread_alias_collision_does_not_bind(self):
        art = m.compile_delivery_truth(packet([event(thread="thr-other")]))
        self.assertEqual(art["delivery_state"], "DELIVERY_UNKNOWN")
        self.assertIn("thread", art["evaluated_evidence"][0]["binding_mismatches"])

    def test_duplicate_retained_source_rejected(self):
        ev1 = event(eid="e1", source="b")
        ev2 = event(eid="e2", source="b", diagnostic="different synthetic fact")
        with self.assertRaises(m.DeliveryTruthError):
            m.compile_delivery_truth(packet([ev1, ev2]))

    def test_semantic_remint_under_new_id_ref_and_blob_is_rejected(self):
        ev1 = event(eid="e1", source="b")
        ev2 = event(eid="e2", source="c", observed="2026-09-17T23:11:00Z")
        with self.assertRaisesRegex(m.DeliveryTruthError, "reminted duplicate"):
            m.compile_delivery_truth(packet([ev1, ev2]))

    def test_delayed_soft_failure_stays_unknown(self):
        ev = event(action="delayed", status="4.4.1", diagnostic="synthetic temporary route issue")
        art = m.compile_delivery_truth(packet([ev]))
        self.assertEqual(art["delivery_state"], "DELIVERY_UNKNOWN")
        self.assertEqual(art["evaluated_evidence"][0]["classification"], "SOFT_FAILURE")

    def test_free_text_cannot_override_structured_status(self):
        ev = event(action="delayed", status="4.2.0", diagnostic="synthetic text claims permanent failure")
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
            diagnostic="synthetic final delivery",
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

    def test_retained_three_way_replay_matrix(self):
        hard_packet = packet([event()])
        unknown_packet = legacy_packet()
        delivered_event = event(
            kind="PROVIDER_DELIVERY_CONFIRMATION",
            action="delivered",
            status="2.0.0",
            diagnostic="synthetic retained delivery confirmation",
        )
        delivered_packet = packet([delivered_event])
        hard = m.compile_delivery_truth(hard_packet)
        unknown = m.compile_delivery_truth(unknown_packet)
        delivered = m.compile_delivery_truth(delivered_packet)
        self.assertEqual(
            [hard["delivery_state"], unknown["delivery_state"], delivered["delivery_state"]],
            ["DELIVERY_FAILED", "DELIVERY_UNKNOWN", "DELIVERED_EVIDENCE"],
        )
        self.assertTrue(m.verify_delivery_truth(hard_packet, hard)["valid"])
        self.assertTrue(m.verify_delivery_truth(unknown_packet, unknown)["valid"])
        self.assertTrue(m.verify_delivery_truth(delivered_packet, delivered)["valid"])


    def test_unsent_packet_is_representable(self):
        p = {
            "schema": m.INPUT_SCHEMA,
            "submission": None,
            "legacy_local_sent": None,
            "events": [],
        }
        art = m.compile_delivery_truth(p)
        self.assertEqual(art["delivery_state"], "UNSENT")
        self.assertEqual(art["state_transition"], ["UNSENT"])
        proj = art["collision_projection"]
        self.assertFalse(proj["provider_submission_observed"])
        self.assertFalse(proj["same_route_dedupe_hold"])
        self.assertEqual(proj["route_viability"], "UNTRIED_ROUTE")

    def test_historical_local_sent_without_evidence_is_unknown(self):
        art = m.compile_delivery_truth(legacy_packet())
        self.assertEqual(art["delivery_state"], "DELIVERY_UNKNOWN")
        self.assertTrue(art["evidence_claims"]["legacy_local_sent_retained"])
        self.assertFalse(art["collision_projection"]["counts_as_contacted"])

    def test_historical_local_sent_late_hard_dsn_reconciles_failed(self):
        art = m.compile_delivery_truth(legacy_packet([event()]))
        self.assertEqual(art["delivery_state"], "DELIVERY_FAILED")
        self.assertEqual(art["state_transition"], ["UNSENT", "DELIVERY_UNKNOWN", "DELIVERY_FAILED"])
        self.assertFalse(art["collision_projection"]["organization_contact_confirmed"])

    def test_historical_local_sent_late_positive_evidence_reconciles_delivered(self):
        ev = event(
            kind="PROVIDER_DELIVERY_CONFIRMATION",
            action="delivered",
            status="2.0.0",
            diagnostic="synthetic retained delivery confirmation",
        )
        art = m.compile_delivery_truth(legacy_packet([ev]))
        self.assertEqual(art["delivery_state"], "DELIVERED_EVIDENCE")
        self.assertTrue(art["collision_projection"]["organization_contact_confirmed"])

    def test_delivery_event_without_any_submission_evidence_is_rejected(self):
        p = {
            "schema": m.INPUT_SCHEMA,
            "submission": None,
            "legacy_local_sent": None,
            "events": [event()],
        }
        with self.assertRaisesRegex(m.DeliveryTruthError, "requires submission or legacy_local_sent"):
            m.compile_delivery_truth(p)

    def test_old_three_key_packet_shape_remains_accepted(self):
        p = packet()
        self.assertEqual(set(p), {"schema", "submission", "events"})
        art = m.compile_delivery_truth(p)
        self.assertEqual(art["delivery_state"], "PROVIDER_SUBMITTED_PENDING_DELIVERY")
        self.assertIsNone(art["legacy_local_sent"])

    def test_real_python_O_legacy_hard_failure_path(self):
        script = r"""
from coordination import outbound_delivery_truth as m
def sha(ch): return ch * 64
sub={
    "operation_key":"SYNTH-O","counterparty":"Synthetic","purpose":"synthetic",
    "provider":"synthetic-mail","provider_message_id":"m","provider_thread_id":"t",
    "sender":"sender-token","recipient":"recipient-token",
    "submitted_at":"2026-09-17T23:09:00Z","source_ref":"synthetic:legacy","source_sha256":sha("a"),
}
ev={
    "id":"e","kind":"DSN","observed_at":"2026-09-17T23:10:00Z","provider":"synthetic-mail",
    "original_message_id":"m","original_thread_id":"t","sender":"sender-token","recipient":"recipient-token",
    "action":"failed","status":"5.4.1","diagnostic_code":"synthetic","source_ref":"synthetic:e","source_sha256":sha("b"),
}
p={"schema":m.INPUT_SCHEMA,"submission":None,"legacy_local_sent":sub,"events":[ev]}
art=m.compile_delivery_truth(p)
assert art["delivery_state"] == "DELIVERY_FAILED"
assert all(v is False for v in art["authority"].values())
"""
        cp = subprocess.run([sys.executable, "-O", "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(cp.returncode, 0, cp.stderr.decode())


if __name__ == "__main__":
    unittest.main()
