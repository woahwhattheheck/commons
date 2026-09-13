from __future__ import annotations

import copy
import unittest

from .acceptance import run_acceptance
from .fixtures import frozen_packets, frozen_reference_set, frozen_reference_sha256
from .gate import (
    AUTHORITY,
    CODES,
    EvidenceError,
    STATUS_HOLD,
    STATUS_READY,
    evaluate_batch,
    evaluate_packet,
    output_manifest,
    render_csv,
    render_json,
    sha256_value,
    verify_batch,
)


class IqviaSiteLabGateTests(unittest.TestCase):
    def setUp(self):
        self.reference = frozen_reference_set()
        self.reference_sha256 = frozen_reference_sha256()

    def eval(self, packet):
        return evaluate_packet(packet, self.reference, self.reference_sha256)

    def batch(self, packets):
        return evaluate_batch(packets, self.reference, self.reference_sha256)

    def test_full_frozen_acceptance_contract(self):
        receipt = run_acceptance()
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual((receipt["packets"], receipt["ready"], receipt["hold"]), (180, 150, 30))
        self.assertEqual(receipt["reason_counts"], {code: 5 for code in CODES})
        self.assertEqual(receipt["reference_sha256"], self.reference_sha256)

    def test_pure_evaluation_does_not_mutate_inputs(self):
        packets = frozen_packets()
        reference = frozen_reference_set()
        before_packets = copy.deepcopy(packets)
        before_reference = copy.deepcopy(reference)
        report = evaluate_batch(packets, reference, self.reference_sha256)
        self.assertEqual(packets, before_packets)
        self.assertEqual(reference, before_reference)
        self.assertEqual(report["authority"], AUTHORITY)

    def test_byte_identical_json_csv_manifest_replay(self):
        a = self.batch(frozen_packets())
        b = self.batch(frozen_packets())
        self.assertEqual(render_json(a), render_json(b))
        self.assertEqual(render_csv(a), render_csv(b))
        self.assertEqual(output_manifest(a), output_manifest(b))

    def test_unknown_candidate_fields_fail_closed(self):
        packet = frozen_packets()[0]
        packet["clinical_decision"] = "release"
        with self.assertRaises(EvidenceError):
            self.eval(packet)

    def test_candidate_cannot_supply_protocol_authority(self):
        packet = frozen_packets()[0]
        packet["protocol_id"] = "PROTO-BETA"
        row = self.eval(packet)
        self.assertEqual(row["status"], STATUS_HOLD)
        packet["expected_protocol_id"] = "PROTO-BETA"
        with self.assertRaises(EvidenceError):
            self.eval(packet)

    def test_candidate_cannot_supply_sample_or_method_authority(self):
        packet = frozen_packets()[0]
        packet["sample_type"] = "WHOLE_BLOOD"
        row = self.eval(packet)
        self.assertEqual(row["status"], STATUS_HOLD)
        packet["required_sample_type"] = "WHOLE_BLOOD"
        packet["method_allowed_sample_types"] = ["WHOLE_BLOOD"]
        with self.assertRaises(EvidenceError):
            self.eval(packet)

    def test_candidate_cannot_widen_courier_policy(self):
        packet = frozen_packets()[0]
        packet["courier_temperature_c"] = 12.0
        row = self.eval(packet)
        self.assertEqual(row["status"], STATUS_HOLD)
        packet["courier_max_c"] = 20.0
        with self.assertRaises(EvidenceError):
            self.eval(packet)

    def test_candidate_cannot_widen_collection_window(self):
        packet = frozen_packets()[0]
        packet["collection_at"] = "2026-09-13T17:00:00Z"
        row = self.eval(packet)
        self.assertEqual(row["status"], STATUS_HOLD)
        packet["collection_window_end"] = "2026-09-13T18:00:00Z"
        with self.assertRaises(EvidenceError):
            self.eval(packet)

    def test_wrong_or_missing_trusted_reference_digest_fails_closed(self):
        packet = frozen_packets()[0]
        with self.assertRaises(EvidenceError):
            evaluate_packet(packet, self.reference, "0" * 64)
        with self.assertRaises(EvidenceError):
            evaluate_packet(packet, self.reference, "")

    def test_changed_reference_bytes_under_same_generation_fail_old_host_pin(self):
        changed = frozen_reference_set()
        changed["courier_max_c"] = 20.0
        with self.assertRaises(EvidenceError):
            evaluate_packet(frozen_packets()[0], changed, self.reference_sha256)

    def test_reference_unknown_field_fails_closed_even_with_recomputed_digest(self):
        changed = frozen_reference_set()
        changed["candidate_override"] = True
        with self.assertRaises(EvidenceError):
            evaluate_packet(frozen_packets()[0], changed, sha256_value(changed))

    def test_malformed_reference_lot_fails_closed(self):
        changed = frozen_reference_set()
        changed["kit_expiry_by_lot"]["BAD LOT"] = "2026-10-01T00:00:00Z"
        with self.assertRaises(EvidenceError):
            evaluate_packet(frozen_packets()[0], changed, sha256_value(changed))

    def test_unapproved_kit_lot_holds(self):
        packet = frozen_packets()[0]
        packet["kit_lot"] = "KIT-UNLISTED"
        row = self.eval(packet)
        self.assertEqual(row["status"], STATUS_HOLD)
        self.assertIn("KIT_EXPIRED", row["reason_codes"])

    def test_duplicate_packet_identity_fails_closed(self):
        packet = frozen_packets()[0]
        with self.assertRaises(EvidenceError):
            self.batch([packet, copy.deepcopy(packet)])

    def test_nonfinite_temperature_fails_closed(self):
        packet = frozen_packets()[0]
        packet["courier_temperature_c"] = float("nan")
        with self.assertRaises(EvidenceError):
            self.eval(packet)

    def test_protocol_mismatch_holds_with_both_lineages(self):
        packet = frozen_packets()[0]
        packet["requisition_protocol_id"] = "PROTO-BETA"
        row = self.eval(packet)
        self.assertEqual(row["status"], STATUS_HOLD)
        reason = row["reasons"][0]
        self.assertEqual(reason["code"], "PROTOCOL_VISIT_MISMATCH")
        self.assertIn("protocol", reason["observation_source_refs"])
        self.assertIn("protocol", reason["reference_source_refs"])

    def test_multiple_faults_are_all_reported_in_stable_order(self):
        packet = frozen_packets()[0]
        packet["requisition_visit_id"] = "VISIT-99"
        packet["kit_lot"] = "KIT-EXPIRED"
        packet["queries"][0]["status"] = "OPEN"
        packet["queries"][0]["resolution_evidence_hash"] = None
        row = self.eval(packet)
        self.assertEqual(row["status"], STATUS_HOLD)
        self.assertEqual(
            row["reason_codes"],
            ["KIT_EXPIRED", "PROTOCOL_VISIT_MISMATCH", "UNRESOLVED_QUERY"],
        )

    def test_ready_packet_retains_observation_and_reference_lineage(self):
        packet = frozen_packets()[0]
        row = self.eval(packet)
        self.assertEqual(row["status"], STATUS_READY)
        self.assertEqual(row["reason_codes"], [])
        self.assertEqual(row["source_refs"], packet["source_refs"])
        self.assertEqual(row["reference_sha256"], self.reference_sha256)
        self.assertEqual(row["reference_generation_id"], self.reference["generation_id"])
        self.assertEqual(len(row["source_digest"]), 64)
        self.assertEqual(len(row["evidence_digest"]), 64)

    def test_invalid_source_hash_fails_closed(self):
        packet = frozen_packets()[0]
        packet["source_refs"]["kit"] = "not-a-hash"
        with self.assertRaises(EvidenceError):
            self.eval(packet)

    def test_open_query_cannot_self_assert_resolution_evidence(self):
        packet = frozen_packets()[0]
        packet["queries"][0]["status"] = "OPEN"
        with self.assertRaises(EvidenceError):
            self.eval(packet)

    def test_report_and_manifest_bind_reference_generation(self):
        report = self.batch(frozen_packets())
        manifest = output_manifest(report)
        self.assertEqual(report["reference_sha256"], self.reference_sha256)
        self.assertEqual(manifest["reference_sha256"], self.reference_sha256)
        self.assertEqual(
            manifest["reference_generation_id"], self.reference["generation_id"]
        )

    def test_verifier_rejects_substituted_reference_authority(self):
        packets = frozen_packets()
        report = self.batch(packets)
        changed = frozen_reference_set()
        changed["courier_max_c"] = 20.0
        self.assertFalse(
            verify_batch(report, packets, changed, self.reference_sha256)
        )

    def test_verifier_rejects_tampered_report(self):
        packets = frozen_packets()
        report = self.batch(packets)
        report["results"][0]["status"] = STATUS_HOLD
        self.assertFalse(
            verify_batch(report, packets, self.reference, self.reference_sha256)
        )

    def test_report_contains_only_nonauthoritative_statuses(self):
        report = self.batch(frozen_packets())
        payload = render_json(report).decode("utf-8").lower()
        self.assertEqual(set(report["status_counts"]), {STATUS_READY, STATUS_HOLD})
        self.assertNotIn('"clinical_decision"', payload)
        self.assertNotIn('"specimen_disposition"', payload)
        self.assertNotIn('"eligible"', payload)


if __name__ == "__main__":
    unittest.main()
