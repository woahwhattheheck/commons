from __future__ import annotations

import copy
import unittest

from .acceptance import run_acceptance
from .fixtures import frozen_packets
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
)


class IqviaSiteLabGateTests(unittest.TestCase):
    def test_full_frozen_acceptance_contract(self):
        receipt = run_acceptance()
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual((receipt["packets"], receipt["ready"], receipt["hold"]), (180, 150, 30))
        self.assertEqual(receipt["reason_counts"], {code: 5 for code in CODES})

    def test_pure_evaluation_does_not_mutate_source_packets(self):
        packets = frozen_packets()
        before = copy.deepcopy(packets)
        report = evaluate_batch(packets)
        self.assertEqual(packets, before)
        self.assertEqual(report["authority"], AUTHORITY)

    def test_byte_identical_json_csv_manifest_replay(self):
        a = evaluate_batch(frozen_packets())
        b = evaluate_batch(frozen_packets())
        self.assertEqual(render_json(a), render_json(b))
        self.assertEqual(render_csv(a), render_csv(b))
        self.assertEqual(output_manifest(a), output_manifest(b))

    def test_unknown_fields_fail_closed(self):
        packet = frozen_packets()[0]
        packet["clinical_decision"] = "release"
        with self.assertRaises(EvidenceError):
            evaluate_packet(packet)

    def test_duplicate_packet_identity_fails_closed(self):
        packet = frozen_packets()[0]
        with self.assertRaises(EvidenceError):
            evaluate_batch([packet, copy.deepcopy(packet)])

    def test_nonfinite_temperature_fails_closed(self):
        packet = frozen_packets()[0]
        packet["courier_temperature_c"] = float("nan")
        with self.assertRaises(EvidenceError):
            evaluate_packet(packet)

    def test_out_of_range_temperature_holds_with_courier_source(self):
        packet = frozen_packets()[0]
        packet["courier_temperature_c"] = 12.0
        row = evaluate_packet(packet)
        self.assertEqual(row["status"], STATUS_HOLD)
        self.assertEqual(row["reason_codes"], ["MISSING_COURIER_TEMPERATURE"])
        self.assertEqual(set(row["reasons"][0]["source_refs"]), {"courier"})

    def test_protocol_mismatch_holds_and_never_ready(self):
        packet = frozen_packets()[0]
        packet["requisition_protocol_id"] = "PROTO-BETA"
        row = evaluate_packet(packet)
        self.assertEqual(row["status"], STATUS_HOLD)
        self.assertIn("PROTOCOL_VISIT_MISMATCH", row["reason_codes"])

    def test_multiple_faults_are_all_reported_in_stable_order(self):
        packet = frozen_packets()[0]
        packet["requisition_visit_id"] = "VISIT-99"
        packet["kit_expires_at"] = "2026-09-01T00:00:00Z"
        packet["queries"][0]["status"] = "OPEN"
        packet["queries"][0]["resolution_evidence_hash"] = None
        row = evaluate_packet(packet)
        self.assertEqual(row["status"], STATUS_HOLD)
        self.assertEqual(
            row["reason_codes"],
            ["KIT_EXPIRED", "PROTOCOL_VISIT_MISMATCH", "UNRESOLVED_QUERY"],
        )

    def test_ready_packet_retains_full_source_lineage(self):
        packet = frozen_packets()[0]
        row = evaluate_packet(packet)
        self.assertEqual(row["status"], STATUS_READY)
        self.assertEqual(row["reason_codes"], [])
        self.assertEqual(row["source_refs"], packet["source_refs"])
        self.assertEqual(len(row["source_digest"]), 64)
        self.assertEqual(len(row["evidence_digest"]), 64)

    def test_invalid_source_hash_fails_closed(self):
        packet = frozen_packets()[0]
        packet["source_refs"]["kit"] = "not-a-hash"
        with self.assertRaises(EvidenceError):
            evaluate_packet(packet)

    def test_inverted_collection_window_fails_closed(self):
        packet = frozen_packets()[0]
        packet["collection_window_start"] = "2026-09-13T18:00:00Z"
        with self.assertRaises(EvidenceError):
            evaluate_packet(packet)

    def test_open_query_cannot_self_assert_resolution_evidence(self):
        packet = frozen_packets()[0]
        packet["queries"][0]["status"] = "OPEN"
        with self.assertRaises(EvidenceError):
            evaluate_packet(packet)

    def test_report_contains_only_nonauthoritative_statuses(self):
        report = evaluate_batch(frozen_packets())
        payload = render_json(report).decode("utf-8").lower()
        self.assertEqual(set(report["status_counts"]), {STATUS_READY, STATUS_HOLD})
        self.assertNotIn('"clinical_decision"', payload)
        self.assertNotIn('"specimen_disposition"', payload)
        self.assertNotIn('"eligible"', payload)


if __name__ == "__main__":
    unittest.main()
