from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import coordination.outbound_delivery_truth as odt


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def outbound() -> dict:
    return {
        "operation_key": "SYNTH-DELIVERY-001",
        "organization_id": "org:example-labs",
        "counterparty": "Example Labs",
        "route": "sales@example.invalid",
        "purpose": "paid diagnostic qualification",
        "provider": "Gmail",
        "subject_sha256": h("subject"),
        "body_sha256": h("body"),
    }


def receipt(label: str = "submission", *, when: str = "2026-09-17T23:00:00Z") -> dict:
    return {
        "provider": "gmail",
        "provider_message_id": "msg-001",
        "provider_thread_id": "thread-001",
        "recipient": "sales@example.invalid",
        "submitted_at": when,
        "source": {"source_ref": f"synthetic:{label}", "source_sha256": h(label)},
    }


def dsn(
    label: str,
    *,
    action: str = "failed",
    smtp_status: str = "550",
    enhanced_status: str = "5.4.1",
    when: str = "2026-09-17T23:01:00Z",
) -> dict:
    return {
        "event_id": f"evt-{label}",
        "kind": "DSN",
        "provider": "gmail",
        "provider_message_id": "msg-001",
        "provider_thread_id": "thread-001",
        "recipient": "sales@example.invalid",
        "observed_at": when,
        "source": {"source_ref": f"synthetic:{label}", "source_sha256": h(label)},
        "dsn": {
            "action": action,
            "smtp_status": smtp_status,
            "enhanced_status": enhanced_status,
            "final_recipient": "sales@example.invalid",
            "original_message_id": "msg-001",
            "diagnostic_code": f"smtp; {smtp_status} synthetic diagnostic",
        },
    }


def packet(*, submission=True, legacy=False, events=None) -> dict:
    out = outbound()
    return {
        "schema": "commons.outbound-delivery-evidence/v1",
        "outbound": out,
        "outbound_descriptor_sha256": odt.sha256_json({**out, "provider": "gmail"}),
        "submission": receipt() if submission else None,
        "legacy_local_sent": receipt("legacy") if legacy else None,
        "delivery_events": list(events or []),
    }


class DeliveryTruthTests(unittest.TestCase):
    def test_unsent(self):
        got = odt.compile_packet(packet(submission=False))
        self.assertEqual(got["state"], "UNSENT")
        self.assertFalse(got["collision_projection"]["provider_submission_seen"])

    def test_submission_is_pending_not_delivered(self):
        got = odt.compile_packet(packet())
        self.assertEqual(got["state"], "PROVIDER_SUBMITTED_PENDING_DELIVERY")
        self.assertFalse(got["evidence_claims"]["provider_submission_is_delivery_proof"])
        self.assertFalse(got["collision_projection"]["organization_contacted_from_this_generation"])

    def test_legacy_local_sent_migrates_to_unknown(self):
        got = odt.compile_packet(packet(submission=False, legacy=True))
        self.assertEqual(got["state"], "DELIVERY_UNKNOWN")
        self.assertFalse(got["collision_projection"]["treat_as_delivered_for_collision_history"])

    def test_legacy_local_sent_reconciles_when_late_bound_dsn_arrives(self):
        got = odt.compile_packet(packet(submission=False, legacy=True, events=[dsn("legacy-hard")]))
        self.assertEqual(got["state"], "DELIVERY_FAILED")
        self.assertEqual(got["collision_projection"]["route_viability"], "DEAD_ROUTE")
        self.assertFalse(got["collision_projection"]["organization_contacted_from_this_generation"])

    def test_hard_dsn_downgrades_exact_submission(self):
        got = odt.compile_packet(packet(events=[dsn("hard")]))
        self.assertEqual(got["state"], "DELIVERY_FAILED")
        self.assertEqual(got["collision_projection"]["route_viability"], "DEAD_ROUTE")
        self.assertEqual(got["collision_projection"]["organization_contact_state"], "DEAD_ROUTE_NOT_CONTACTED")
        self.assertFalse(got["collision_projection"]["organization_contacted_from_this_generation"])
        self.assertTrue(got["collision_projection"]["same_route_delivery_failed"])

    def test_soft_dsn_is_unknown(self):
        got = odt.compile_packet(packet(events=[dsn("soft", action="delayed", smtp_status="450", enhanced_status="4.2.0")]))
        self.assertEqual(got["state"], "DELIVERY_UNKNOWN")
        self.assertEqual(got["collision_projection"]["successful_contact_count_delta"], 0)

    def test_explicit_delivered_dsn(self):
        got = odt.compile_packet(packet(events=[dsn("ok", action="delivered", smtp_status="250", enhanced_status="2.0.0")]))
        self.assertEqual(got["state"], "DELIVERED_EVIDENCE")
        self.assertEqual(got["collision_projection"]["successful_contact_count_delta"], 1)
        self.assertEqual(got["collision_projection"]["revenue_activity_count_delta"], 0)

    def test_wrong_message_dsn_rejected(self):
        e = dsn("wrong-message")
        e["provider_message_id"] = "msg-other"
        with self.assertRaisesRegex(odt.DeliveryTruthError, "message binding mismatch"):
            odt.compile_packet(packet(events=[e]))

    def test_wrong_thread_dsn_rejected(self):
        e = dsn("wrong-thread")
        e["provider_thread_id"] = "thread-other"
        with self.assertRaisesRegex(odt.DeliveryTruthError, "thread binding mismatch"):
            odt.compile_packet(packet(events=[e]))

    def test_wrong_recipient_dsn_rejected(self):
        e = dsn("wrong-recipient")
        e["recipient"] = "other@example.invalid"
        with self.assertRaisesRegex(odt.DeliveryTruthError, "recipient binding mismatch"):
            odt.compile_packet(packet(events=[e]))

    def test_dsn_final_recipient_transplant_rejected(self):
        e = dsn("wrong-final")
        e["dsn"]["final_recipient"] = "other@example.invalid"
        with self.assertRaisesRegex(odt.DeliveryTruthError, "final recipient"):
            odt.compile_packet(packet(events=[e]))

    def test_dsn_original_message_transplant_rejected(self):
        e = dsn("wrong-original")
        e["dsn"]["original_message_id"] = "msg-other"
        with self.assertRaisesRegex(odt.DeliveryTruthError, "original message"):
            odt.compile_packet(packet(events=[e]))

    def test_duplicate_event_id_rejected(self):
        a = dsn("a", action="delayed", smtp_status="450", enhanced_status="4.2.0")
        b = dsn("b", action="failed", smtp_status="550", enhanced_status="5.4.1", when="2026-09-17T23:02:00Z")
        b["event_id"] = a["event_id"]
        with self.assertRaisesRegex(odt.DeliveryTruthError, "duplicate delivery event id"):
            odt.compile_packet(packet(events=[a, b]))

    def test_reminted_source_generation_rejected(self):
        a = dsn("a", action="delayed", smtp_status="450", enhanced_status="4.2.0")
        b = dsn("b", action="failed", smtp_status="550", enhanced_status="5.4.1", when="2026-09-17T23:02:00Z")
        b["source"]["source_sha256"] = a["source"]["source_sha256"]
        with self.assertRaisesRegex(odt.DeliveryTruthError, "duplicate/reminted delivery source"):
            odt.compile_packet(packet(events=[a, b]))

    def test_reminted_semantics_rejected_even_with_new_source(self):
        a = dsn("same")
        b = copy.deepcopy(a)
        b["event_id"] = "evt-remint"
        b["source"] = {"source_ref": "synthetic:remint", "source_sha256": h("remint")}
        b["observed_at"] = "2026-09-17T23:02:00Z"
        with self.assertRaisesRegex(odt.DeliveryTruthError, "duplicate/reminted delivery semantics"):
            odt.compile_packet(packet(events=[a, b]))

    def test_forged_free_text_bounce_is_not_admitted(self):
        e = dsn("free-text")
        e["kind"] = "FREE_TEXT_BOUNCE"
        with self.assertRaisesRegex(odt.DeliveryTruthError, "kind must be DSN"):
            odt.compile_packet(packet(events=[e]))

    def test_action_status_class_mismatch_rejected(self):
        e = dsn("bad-class", action="failed", smtp_status="450", enhanced_status="4.2.0")
        with self.assertRaisesRegex(odt.DeliveryTruthError, "action/status class conflict"):
            odt.compile_packet(packet(events=[e]))

    def test_smtp_and_enhanced_class_mismatch_rejected(self):
        e = dsn("bad-enhanced", action="failed", smtp_status="550", enhanced_status="4.2.0")
        with self.assertRaisesRegex(odt.DeliveryTruthError, "SMTP/enhanced status classes conflict"):
            odt.compile_packet(packet(events=[e]))

    def test_conflicting_terminal_evidence_fails_closed_unknown(self):
        delivered = dsn("delivered", action="delivered", smtp_status="250", enhanced_status="2.0.0")
        failed = dsn("failed", when="2026-09-17T23:02:00Z")
        got = odt.compile_packet(packet(events=[delivered, failed]))
        self.assertEqual(got["state"], "DELIVERY_UNKNOWN")
        self.assertFalse(got["collision_projection"]["organization_contacted_from_this_generation"])

    def test_out_of_order_events_rejected(self):
        later = dsn("later", action="delayed", smtp_status="450", enhanced_status="4.2.0", when="2026-09-17T23:03:00Z")
        earlier = dsn("earlier", when="2026-09-17T23:02:00Z")
        with self.assertRaisesRegex(odt.DeliveryTruthError, "nondecreasing"):
            odt.compile_packet(packet(events=[later, earlier]))

    def test_pre_submission_event_rejected(self):
        e = dsn("early", when="2026-09-17T22:59:59Z")
        with self.assertRaisesRegex(odt.DeliveryTruthError, "predates provider submission"):
            odt.compile_packet(packet(events=[e]))

    def test_descriptor_mutation_breaks_digest_binding(self):
        p = packet()
        p["outbound"]["purpose"] = "different purpose"
        with self.assertRaisesRegex(odt.DeliveryTruthError, "descriptor digest mismatch"):
            odt.compile_packet(p)

    def test_submission_route_and_provider_are_bound(self):
        p = packet()
        p["submission"]["recipient"] = "other@example.invalid"
        with self.assertRaisesRegex(odt.DeliveryTruthError, "recipient does not bind"):
            odt.compile_packet(p)
        p = packet()
        p["submission"]["provider"] = "other-provider"
        with self.assertRaisesRegex(odt.DeliveryTruthError, "provider does not bind"):
            odt.compile_packet(p)

    def test_legacy_and_submission_are_mutually_exclusive(self):
        p = packet()
        p["legacy_local_sent"] = receipt("legacy")
        with self.assertRaisesRegex(odt.DeliveryTruthError, "mutually exclusive"):
            odt.compile_packet(p)

    def test_delivery_event_without_submission_rejected(self):
        p = packet(submission=False, events=[dsn("orphan")])
        with self.assertRaisesRegex(odt.DeliveryTruthError, "requires a provider submission"):
            odt.compile_packet(p)

    def test_all_authority_is_hard_false_in_compile_and_verify(self):
        p = packet(events=[dsn("hard")])
        report = odt.compile_packet(p)
        self.assertTrue(report["authority"])
        self.assertTrue(all(value is False for value in report["authority"].values()))
        verify = odt.verify_report(p, report)
        self.assertTrue(verify["valid"])
        self.assertTrue(all(value is False for value in verify["authority"].values()))

    def test_report_semantic_tamper_fails_verification(self):
        p = packet(events=[dsn("hard")])
        report = odt.compile_packet(p)
        tampered = copy.deepcopy(report)
        tampered["state"] = "DELIVERED_EVIDENCE"
        self.assertFalse(odt.verify_report(p, tampered)["valid"])

    def test_report_receipt_remint_cannot_hide_semantic_tamper(self):
        p = packet(events=[dsn("hard")])
        report = odt.compile_packet(p)
        tampered = copy.deepcopy(report)
        tampered["state"] = "DELIVERED_EVIDENCE"
        no_receipt = dict(tampered)
        no_receipt.pop("receipt_sha256")
        tampered["receipt_sha256"] = odt.sha256_json(no_receipt)
        self.assertEqual(odt.verify_report(p, tampered)["reason"], "semantic_recompile_mismatch")

    def test_strict_json_rejects_duplicate_float_nonfinite_and_lone_surrogate(self):
        with self.assertRaises(odt.DeliveryTruthError):
            odt.loads_strict('{"x":1,"x":2}')
        with self.assertRaises(odt.DeliveryTruthError):
            odt.loads_strict('{"x":1.5}')
        with self.assertRaises(odt.DeliveryTruthError):
            odt.loads_strict('{"x":NaN}')
        with self.assertRaises(odt.DeliveryTruthError):
            odt.loads_strict('"\\ud800"')

    def test_post_import_public_global_rebinding_does_not_steer_generation(self):
        p = packet(events=[dsn("hard")])
        expected = odt.compile_packet(p)
        saved_json, saved_hashlib, saved_authority, saved_states = odt._json, odt._hashlib, odt._AUTHORITY, odt._STATES
        try:
            odt._json = object()
            odt._hashlib = object()
            odt._AUTHORITY = {"send_authorized": True}
            odt._STATES = frozenset({"DELIVERED_EVIDENCE"})
            self.assertEqual(odt.compile_packet(p), expected)
        finally:
            odt._json, odt._hashlib, odt._AUTHORITY, odt._STATES = saved_json, saved_hashlib, saved_authority, saved_states

    def test_cli_compile_verify_roundtrip(self):
        p = packet(events=[dsn("hard")])
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inp, rep = td / "input.json", td / "report.json"
            inp.write_bytes(odt.canonical_json(p))
            cp = subprocess.run(
                [sys.executable, "coordination/outbound_delivery_truth.py", "compile", "--input", str(inp)],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            report = odt.loads_strict(cp.stdout)
            rep.write_bytes(odt.canonical_json(report))
            vp = subprocess.run(
                [sys.executable, "coordination/outbound_delivery_truth.py", "verify", "--input", str(inp), "--report", str(rep)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            self.assertEqual(vp.returncode, 0, vp.stderr.decode())
            self.assertTrue(odt.loads_strict(vp.stdout)["valid"])

    def test_real_python_O_hard_bounce_path(self):
        script = r'''
import hashlib
from coordination.outbound_delivery_truth import compile_packet, sha256_json
h=lambda s: hashlib.sha256(s.encode()).hexdigest()
out={"operation_key":"o","organization_id":"org","counterparty":"c","route":"r@example.invalid","purpose":"p","provider":"gmail","subject_sha256":h("s"),"body_sha256":h("b")}
sub={"provider":"gmail","provider_message_id":"m","provider_thread_id":"t","recipient":"r@example.invalid","submitted_at":"2026-09-17T23:00:00Z","source":{"source_ref":"x","source_sha256":h("x")}}
e={"event_id":"e","kind":"DSN","provider":"gmail","provider_message_id":"m","provider_thread_id":"t","recipient":"r@example.invalid","observed_at":"2026-09-17T23:01:00Z","source":{"source_ref":"d","source_sha256":h("d")},"dsn":{"action":"failed","smtp_status":"550","enhanced_status":"5.4.1","final_recipient":"r@example.invalid","original_message_id":"m","diagnostic_code":"smtp; 550"}}
p={"schema":"commons.outbound-delivery-evidence/v1","outbound":out,"outbound_descriptor_sha256":sha256_json(out),"submission":sub,"legacy_local_sent":None,"delivery_events":[e]}
r=compile_packet(p)
assert r["state"]=="DELIVERY_FAILED"
assert all(v is False for v in r["authority"].values())
'''
        cp = subprocess.run([sys.executable, "-O", "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(cp.returncode, 0, cp.stderr.decode())


    def test_retained_demo_three_case_replay(self):
        demo = odt.loads_strict(Path("coordination/outbound_delivery_truth_demo.json").read_bytes())
        self.assertEqual(demo["schema"], "commons.outbound-delivery-demo/v1")
        self.assertEqual([row["name"] for row in demo["cases"]], ["delivered", "legacy-local-sent", "hard-bounce"])
        for row in demo["cases"]:
            report = odt.compile_packet(row["packet"])
            self.assertEqual(report["state"], row["expected_state"], row["name"])
            self.assertTrue(odt.verify_report(row["packet"], report)["valid"], row["name"])


if __name__ == "__main__":
    unittest.main()
