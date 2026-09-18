from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from revenue.commerce_conversion_loop.engine import (
    EvidenceError,
    compile_packet,
    evidence_sha256,
    parse_json_bytes,
    read_regular_file,
    render_bundle,
    retained_root,
    verify_bundle,
    write_bundle_exclusive,
)


def event(event_id, typ, at, parent, facts, *, opp="OPP-1", evidence=None, source_ref=None):
    evidence = evidence or f"retained evidence for {event_id}"
    return {
        "eventId": event_id,
        "opportunityId": opp,
        "eventType": typ,
        "occurredAt": at,
        "sourceRef": source_ref or f"urn:evidence:{event_id}",
        "evidenceText": evidence,
        "sourceSha256": evidence_sha256(evidence),
        "parentEventId": parent,
        "facts": facts,
    }


def base_offer():
    return event("E1", "OFFER_SHIPPED", "2026-09-01T00:00:00Z", None,
                 {"offerId": "OFF-1", "artifactRef": "github:example/repo#1", "artifactCommit": "a" * 40})


def full_doc():
    return {"schemaVersion": 1, "opportunityId": "OPP-1", "events": [
        base_offer(),
        event("E2", "TARGET_QUALIFIED", "2026-09-02T00:00:00Z", "E1",
              {"targetId": "T-1", "qualificationCode": "OWNER_REVIEWED"}),
        event("E3", "OUTBOUND_SUBMITTED", "2026-09-03T00:00:00Z", "E2",
              {"providerCode": "MAIL", "submissionId": "SUB-1"}),
        event("E4", "DELIVERY_CONFIRMED", "2026-09-03T00:01:00Z", "E3",
              {"deliveryId": "DEL-1"}),
        event("E5", "REPLY_OBSERVED", "2026-09-04T00:00:00Z", "E4", {"replyId": "REP-1"}),
        event("E6", "PROPOSAL_OBSERVED", "2026-09-05T00:00:00Z", "E5", {"proposalId": "PROP-1"}),
        event("E7", "PAYMENT_OBSERVED", "2026-09-06T00:00:00Z", "E6",
              {"paymentId": "PAY-1", "amountMinor": 12500, "currency": "USD"}),
    ]}


class ConversionLoopTests(unittest.TestCase):
    def compile(self, doc):
        return compile_packet(doc, retained_root(doc))

    def test_offer_only_is_not_conversion(self):
        doc = {"schemaVersion": 1, "opportunityId": "OPP-1", "events": [base_offer()]}
        packet = self.compile(doc)
        self.assertEqual(packet["observedState"], "OFFER_ONLY")
        self.assertEqual(packet["nextExperiment"]["code"], "QUALIFY_ONE_TARGET")
        self.assertFalse(any(packet["authority"].values()))

    def test_full_chain_payment_is_observed_not_revenue(self):
        packet = self.compile(full_doc())
        self.assertEqual(packet["observedState"], "PAYMENT_OBSERVED")
        self.assertFalse(packet["authority"]["revenueRecognitionAuthorized"])
        self.assertIn("not revenue recognition", packet["truthBoundary"])

    def test_submission_is_not_delivery(self):
        doc = full_doc(); doc["events"] = doc["events"][:3]
        packet = self.compile(doc)
        self.assertEqual(packet["observedState"], "OUTBOUND_PENDING_DELIVERY")
        self.assertEqual(packet["nextExperiment"]["code"], "RECONCILE_PROVIDER_DELIVERY")

    def test_delivery_failure_is_distinct(self):
        doc = full_doc(); doc["events"] = doc["events"][:3] + [
            event("E4F", "DELIVERY_FAILED", "2026-09-03T00:01:00Z", "E3", {"failureId": "FAIL-1", "reasonCode": "REMOTE_REJECTED"})]
        packet = self.compile(doc)
        self.assertEqual(packet["observedState"], "OUTBOUND_DELIVERY_FAILED")
        self.assertEqual(packet["findings"], [])

    def test_positive_event_after_failed_delivery_holds(self):
        doc = full_doc()
        doc["events"][3] = event("E4F", "DELIVERY_FAILED", "2026-09-03T00:01:00Z", "E3", {"failureId": "FAIL-1", "reasonCode": "REMOTE_REJECTED"})
        doc["events"][4]["parentEventId"] = "E4F"
        packet = self.compile(doc)
        self.assertEqual(packet["observedState"], "HOLD")
        self.assertTrue(any("POSITIVE_STAGE_AFTER_FAILED_DELIVERY" in x for x in packet["findings"]))

    def test_wrong_parent_type_holds(self):
        doc = full_doc(); doc["events"][5]["parentEventId"] = "E3"
        packet = self.compile(doc)
        self.assertEqual(packet["observedState"], "HOLD")
        self.assertIn("WRONG_PARENT_TYPE_PROPOSAL_OBSERVED", packet["findings"])

    def test_scope_transplant_holds(self):
        doc = full_doc(); doc["events"][2]["opportunityId"] = "OPP-OTHER"
        packet = self.compile(doc)
        self.assertEqual(packet["observedState"], "HOLD")
        self.assertIn("OPPORTUNITY_SCOPE_DRIFT", packet["findings"])

    def test_chronology_regression_holds(self):
        doc = full_doc(); doc["events"][4]["occurredAt"] = "2026-09-02T00:00:00Z"
        packet = self.compile(doc)
        self.assertEqual(packet["observedState"], "HOLD")
        self.assertIn("CHRONOLOGY_REGRESSION_REPLY_OBSERVED", packet["findings"])

    def test_conflicting_delivery_terminals_hold(self):
        doc = full_doc(); doc["events"].insert(4, event("E4F", "DELIVERY_FAILED", "2026-09-03T00:02:00Z", "E3", {"failureId": "FAIL-1", "reasonCode": "REMOTE_REJECTED"}))
        packet = self.compile(doc)
        self.assertEqual(packet["observedState"], "HOLD")
        self.assertIn("CONFLICTING_DELIVERY_TERMINALS", packet["findings"])

    def test_duplicate_stage_holds(self):
        doc = full_doc(); doc["events"].append(event("E8", "TARGET_QUALIFIED", "2026-09-02T00:01:00Z", "E1", {"targetId": "T-2", "qualificationCode": "OWNER_REVIEWED"}))
        packet = self.compile(doc)
        self.assertEqual(packet["observedState"], "HOLD")
        self.assertIn("DUPLICATE_STAGE_TARGET_QUALIFIED", packet["findings"])

    def test_evidence_identity_reuse_holds(self):
        doc = full_doc()
        for k in ("sourceRef", "sourceSha256", "evidenceText"):
            doc["events"][1][k] = doc["events"][0][k]
        packet = self.compile(doc)
        self.assertEqual(packet["observedState"], "HOLD")
        self.assertIn("EVIDENCE_IDENTITY_REUSED_ACROSS_EVENTS", packet["findings"])

    def test_retained_root_mismatch_holds(self):
        packet = compile_packet(full_doc(), "0" * 64)
        self.assertEqual(packet["observedState"], "HOLD")
        self.assertIn("RETAINED_ROOT_MISMATCH", packet["findings"])

    def test_input_order_invariance(self):
        doc = full_doc(); rev = {"schemaVersion": 1, "opportunityId": "OPP-1", "events": list(reversed(doc["events"]))}
        self.assertEqual(retained_root(doc), retained_root(rev))
        self.assertEqual(render_bundle(doc, retained_root(doc)), render_bundle(rev, retained_root(rev)))

    def test_bundle_tamper_detected(self):
        doc = full_doc(); root = retained_root(doc); b = render_bundle(doc, root)
        self.assertTrue(verify_bundle(doc, root, packet_json=b.packet_json, summary_md=b.summary_md, events_csv=b.events_csv, receipt_txt=b.receipt_txt))
        self.assertFalse(verify_bundle(doc, root, packet_json=b.packet_json+b" ", summary_md=b.summary_md, events_csv=b.events_csv, receipt_txt=b.receipt_txt))

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(EvidenceError): parse_json_bytes(b'{"schemaVersion":1,"schemaVersion":1}')

    def test_float_rejected(self):
        with self.assertRaises(EvidenceError): parse_json_bytes(b'{"x":1.0}')

    def test_bool_not_int(self):
        doc = full_doc(); doc["events"][-1]["facts"]["amountMinor"] = True
        with self.assertRaises(EvidenceError): retained_root(doc)

    def test_unknown_field_rejected(self):
        doc = full_doc(); doc["events"][0]["surprise"] = "x"
        with self.assertRaises(EvidenceError): retained_root(doc)

    def test_bad_evidence_digest_rejected(self):
        doc = full_doc(); doc["events"][0]["sourceSha256"] = "0" * 64
        with self.assertRaises(EvidenceError): retained_root(doc)

    def test_contact_or_secret_shaped_evidence_rejected(self):
        doc = full_doc(); text = "contact me at someone@example.com"
        doc["events"][0]["evidenceText"] = text; doc["events"][0]["sourceSha256"] = evidence_sha256(text)
        with self.assertRaises(EvidenceError): retained_root(doc)

    def test_file_boundary_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"source.json"; p.write_text("{}", encoding="utf-8")
            link = Path(td)/"link.json"
            try: os.symlink(p, link)
            except (OSError, NotImplementedError): self.skipTest("symlink unavailable")
            with self.assertRaises(EvidenceError): read_regular_file(link)

    def test_output_is_create_exclusive(self):
        doc=full_doc(); b=render_bundle(doc, retained_root(doc))
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"out"; write_bundle_exclusive(out,b)
            with self.assertRaises(EvidenceError): write_bundle_exclusive(out,b)

    def test_real_public_fixture_is_offer_only(self):
        sample = Path(__file__).parents[1]/"revenue"/"commerce_conversion_loop"/"real_public.sample.json"
        doc=parse_json_bytes(sample.read_bytes()); packet=compile_packet(doc, retained_root(doc))
        self.assertEqual(packet["observedState"], "OFFER_ONLY")
        self.assertEqual(packet["findings"], [])
        self.assertFalse(any(packet["authority"].values()))


if __name__ == "__main__":
    unittest.main()
