from __future__ import annotations

from copy import deepcopy
import unittest

from .acceptance import make_clean_bundle, run_acceptance
from .core import (
    ConsolidationEvidenceError,
    batch_content_sha256,
    evaluate,
    load_strict_json,
    verify_receipt,
)


def codes(receipt):
    return {row["code"] for row in receipt["failures"]}


def refresh_batch(bundle, batch_id):
    rows = []
    seen = set()
    for row in bundle["records"]:
        if row["batch_id"] == batch_id and row["event_id"] not in seen:
            rows.append(row); seen.add(row["event_id"])
    batch = next(row for row in bundle["batches"] if row["batch_id"] == batch_id)
    batch["declared_records"] = len(rows)
    batch["content_sha256"] = batch_content_sha256(rows)


class ConsolidationQATests(unittest.TestCase):
    def setUp(self):
        self.bundle = make_clean_bundle(18)

    def test_clean_bundle_passes_without_migration_authority(self):
        receipt = evaluate(self.bundle).receipt
        self.assertEqual("PASS", receipt["status"])
        self.assertEqual(18, receipt["migration_candidate_count"])
        self.assertEqual(0, receipt["quarantined_entity_count"])
        self.assertEqual(0, receipt["invalid_batch_count"])
        self.assertEqual(receipt["batch_count"], receipt["trusted_batch_count"])
        self.assertEqual(receipt["effective_record_count"], receipt["trusted_record_count"])
        self.assertEqual(1_000_000, receipt["reconciliation"]["source_entity_completeness_ppm"])
        self.assertEqual(54, receipt["reconciliation"]["expected_source_entity_links"])
        self.assertEqual(54, receipt["reconciliation"]["matched_source_entity_links"])
        self.assertEqual({}, receipt["reconciliation"]["exception_counts"])
        self.assertFalse(receipt["migration_authorized"])
        self.assertFalse(receipt["external_effects_performed"])
        self.assertTrue(verify_receipt(receipt))

    def test_input_order_is_not_authority(self):
        a = evaluate(self.bundle).receipt_sha256
        other = deepcopy(self.bundle)
        other["sources"].reverse(); other["batches"].reverse(); other["records"].reverse()
        b = evaluate(other).receipt_sha256
        self.assertEqual(a, b)

    def test_exact_event_replays_collapse(self):
        receipt = evaluate(self.bundle).receipt
        self.assertGreater(receipt["exact_replay_count"], 0)
        self.assertEqual(54, receipt["effective_record_count"])

    def test_changed_event_replay_holds(self):
        bundle = deepcopy(self.bundle)
        row = deepcopy(bundle["records"][0])
        key = next(iter(row["payload"]))
        row["payload"][key] = "DRIFT"
        bundle["records"].append(row)
        receipt = evaluate(bundle).receipt
        self.assertEqual("HOLD", receipt["status"])
        self.assertIn("EVENT_REPLAY_CONFLICT", codes(receipt))

    def test_batch_digest_drift_quarantines_batch_entities(self):
        bundle = deepcopy(self.bundle)
        victim = bundle["batches"][0]
        victim_keys = {
            row["entity_key"] for row in bundle["records"]
            if row["batch_id"] == victim["batch_id"]
        }
        victim["content_sha256"] = "0" * 64
        receipt = evaluate(bundle).receipt
        self.assertIn("BATCH_CONTENT_MISMATCH", codes(receipt))
        self.assertEqual(1, receipt["invalid_batch_count"])
        self.assertLess(receipt["trusted_record_count"], receipt["effective_record_count"])
        self.assertLess(receipt["migration_candidate_count"], 18)
        self.assertLess(receipt["reconciliation"]["source_entity_completeness_ppm"], 1_000_000)
        self.assertGreater(receipt["reconciliation"]["missing_source_entity_links"], 0)
        for entity in receipt["entities"]:
            if entity["entity_key"] in victim_keys:
                self.assertEqual("HOLD", entity["status"])
                self.assertIn("SOURCE_ENTITY_MISSING", entity["reason_codes"])

    def test_batch_count_drift_quarantines_batch(self):
        bundle = deepcopy(self.bundle)
        bundle["batches"][0]["declared_records"] += 1
        receipt = evaluate(bundle).receipt
        self.assertIn("BATCH_RECORD_COUNT_MISMATCH", codes(receipt))
        self.assertEqual(1, receipt["invalid_batch_count"])
        self.assertLess(receipt["migration_candidate_count"], 18)

    def test_batch_schema_drift_quarantines_batch(self):
        bundle = deepcopy(self.bundle)
        bundle["batches"][0]["schema_version"] = "wrong-v1"
        receipt = evaluate(bundle).receipt
        self.assertIn("BATCH_SCHEMA_MISMATCH", codes(receipt))
        self.assertEqual(1, receipt["invalid_batch_count"])
        self.assertLess(receipt["migration_candidate_count"], 18)

    def test_duplicate_batch_sequence_holds(self):
        bundle = deepcopy(self.bundle)
        same_source = [b for b in bundle["batches"] if b["source_id"] == bundle["batches"][0]["source_id"]]
        if len(same_source) < 2:
            self.skipTest("fixture unexpectedly lacks two batches")
        same_source[1]["sequence"] = same_source[0]["sequence"]
        receipt = evaluate(bundle).receipt
        self.assertIn("DUPLICATE_BATCH_SEQUENCE", codes(receipt))
        self.assertEqual(2, receipt["invalid_batch_count"])
        self.assertEqual(0, receipt["migration_candidate_count"])

    def test_source_missing_entity_holds(self):
        bundle = deepcopy(self.bundle)
        source = bundle["sources"][0]
        key = source["expected_entity_keys"][0]
        touched = set()
        kept = []
        for row in bundle["records"]:
            if row["source_id"] == source["source_id"] and row["entity_key"] == key:
                touched.add(row["batch_id"])
            else:
                kept.append(row)
        bundle["records"] = kept
        for batch_id in touched:
            refresh_batch(bundle, batch_id)
        receipt = evaluate(bundle).receipt
        self.assertIn("SOURCE_ENTITY_MISSING", codes(receipt))
        entity = next(e for e in receipt["entities"] if e["entity_key"] == key)
        self.assertEqual("HOLD", entity["status"])
        self.assertIn("SOURCE_ENTITY_MISSING", entity["reason_codes"])
        self.assertEqual(1, receipt["reconciliation"]["missing_source_entity_links"])

    def test_source_unexpected_entity_holds(self):
        bundle = deepcopy(self.bundle)
        row = deepcopy(next(r for r in bundle["records"] if r["source_id"] == "EDI-TERMINAL"))
        row["event_id"] = "EV-EXTRA"
        row["external_id"] = "EXT-EXTRA"
        row["entity_key"] = "ENTITY-EXTRA"
        bundle["records"].append(row)
        refresh_batch(bundle, row["batch_id"])
        receipt = evaluate(bundle).receipt
        self.assertIn("SOURCE_ENTITY_UNEXPECTED", codes(receipt))
        entity = next(e for e in receipt["entities"] if e["entity_key"] == "ENTITY-EXTRA")
        self.assertEqual("HOLD", entity["status"])
        self.assertIn("SOURCE_ENTITY_UNEXPECTED", entity["reason_codes"])

    def test_missing_required_source_field_holds(self):
        bundle = deepcopy(self.bundle)
        row = next(r for r in bundle["records"] if r["event_id"] == "EV-1-00001")
        row["payload"].pop("asset")
        refresh_batch(bundle, row["batch_id"])
        self.assertIn("MISSING_REQUIRED_SOURCE_FIELD", codes(evaluate(bundle).receipt))

    def test_unmapped_source_field_holds(self):
        bundle = deepcopy(self.bundle)
        row = next(r for r in bundle["records"] if r["event_id"] == "EV-1-00001")
        row["payload"]["legacy_code"] = "X"
        refresh_batch(bundle, row["batch_id"])
        self.assertIn("UNMAPPED_SOURCE_FIELD", codes(evaluate(bundle).receipt))

    def test_canonical_field_conflict_quarantines_entity(self):
        bundle = deepcopy(self.bundle)
        row = next(r for r in bundle["records"] if r["event_id"] == "EV-2-00001")
        row["payload"]["statusCode"] = "CONFLICTING"
        refresh_batch(bundle, row["batch_id"])
        receipt = evaluate(bundle).receipt
        self.assertIn("CANONICAL_FIELD_CONFLICT", codes(receipt))
        entity = next(e for e in receipt["entities"] if e["entity_key"] == "ENTITY-0001")
        self.assertEqual("HOLD", entity["status"])
        self.assertIsNone(entity["canonical_record"])

    def test_same_source_latest_version_conflict_holds(self):
        bundle = deepcopy(self.bundle)
        base = next(r for r in bundle["records"] if r["event_id"] == "EV-1-00001")
        a = deepcopy(base); a["event_id"] = "EV-V2-A"; a["version"] = 2
        b = deepcopy(base); b["event_id"] = "EV-V2-B"; b["version"] = 2; b["external_id"] = "EXT-OTHER"
        bundle["records"].extend([a, b])
        refresh_batch(bundle, base["batch_id"])
        self.assertIn("ENTITY_VERSION_CONFLICT", codes(evaluate(bundle).receipt))

    def test_newer_source_version_wins_deterministically(self):
        bundle = deepcopy(self.bundle)
        base = next(r for r in bundle["records"] if r["event_id"] == "EV-1-00001")
        newer = deepcopy(base); newer["event_id"] = "EV-V2"; newer["version"] = 2
        bundle["records"].append(newer)
        refresh_batch(bundle, base["batch_id"])
        receipt = evaluate(bundle).receipt
        self.assertEqual("PASS", receipt["status"])
        entity = next(e for e in receipt["entities"] if e["entity_key"] == "ENTITY-0001")
        line = next(x for x in entity["source_lineage"] if x["source_id"] == "EDI-TERMINAL")
        self.assertEqual(2, line["version"])

    def test_record_batch_source_mismatch_holds(self):
        bundle = deepcopy(self.bundle)
        row = next(r for r in bundle["records"] if r["event_id"] == "EV-1-00001")
        row["source_id"] = "API-OPS"
        self.assertIn("RECORD_BATCH_SOURCE_MISMATCH", codes(evaluate(bundle).receipt))

    def test_unknown_record_batch_holds(self):
        bundle = deepcopy(self.bundle)
        row = next(r for r in bundle["records"] if r["event_id"] == "EV-1-00001")
        row["batch_id"] = "BATCH-MISSING"
        self.assertIn("UNKNOWN_RECORD_BATCH", codes(evaluate(bundle).receipt))

    def test_duplicate_source_id_rejected(self):
        bundle = deepcopy(self.bundle)
        bundle["sources"].append(deepcopy(bundle["sources"][0]))
        with self.assertRaisesRegex(ConsolidationEvidenceError, "DUPLICATE_SOURCE_ID"):
            evaluate(bundle)

    def test_duplicate_batch_id_rejected(self):
        bundle = deepcopy(self.bundle)
        bundle["batches"].append(deepcopy(bundle["batches"][0]))
        with self.assertRaisesRegex(ConsolidationEvidenceError, "DUPLICATE_BATCH_ID"):
            evaluate(bundle)

    def test_ambiguous_field_map_rejected(self):
        bundle = deepcopy(self.bundle)
        source = bundle["sources"][0]
        keys = list(source["field_map"])
        source["field_map"][keys[1]] = source["field_map"][keys[0]]
        with self.assertRaisesRegex(ConsolidationEvidenceError, "AMBIGUOUS_FIELD_MAP"):
            evaluate(bundle)

    def test_unknown_canonical_mapping_rejected(self):
        bundle = deepcopy(self.bundle)
        source = bundle["sources"][0]
        source["field_map"][next(iter(source["field_map"]))] = "not_canonical"
        with self.assertRaisesRegex(ConsolidationEvidenceError, "UNKNOWN_CANONICAL_FIELD"):
            evaluate(bundle)

    def test_nested_payload_rejected(self):
        bundle = deepcopy(self.bundle)
        bundle["records"][0]["payload"][next(iter(bundle["records"][0]["payload"]))] = {"nested": True}
        with self.assertRaisesRegex(ConsolidationEvidenceError, "NON_SCALAR_VALUE"):
            evaluate(bundle)

    def test_float_payload_rejected(self):
        bundle = deepcopy(self.bundle)
        bundle["records"][0]["payload"][next(iter(bundle["records"][0]["payload"]))] = 1.25
        with self.assertRaisesRegex(ConsolidationEvidenceError, "NON_SCALAR_VALUE"):
            evaluate(bundle)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(ConsolidationEvidenceError, "DUPLICATE_JSON_KEY"):
            load_strict_json('{"x":1,"x":2}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaisesRegex(ConsolidationEvidenceError, "NONFINITE_JSON_NUMBER"):
            load_strict_json('{"x":NaN}')

    def test_receipt_tamper_detected(self):
        receipt = deepcopy(evaluate(self.bundle).receipt)
        receipt["migration_candidate_count"] += 1
        self.assertFalse(verify_receipt(receipt))

    def test_non_object_receipt_invalid(self):
        self.assertFalse(verify_receipt(["bad"]))

    def test_batch_digest_helper_rejects_duplicate_event(self):
        row = deepcopy(self.bundle["records"][0])
        with self.assertRaisesRegex(ConsolidationEvidenceError, "DUPLICATE_EVENT_FOR_BATCH_DIGEST"):
            batch_content_sha256([row, deepcopy(row)])

    def test_acceptance_matrix(self):
        summary = run_acceptance()
        self.assertEqual(3, summary["synthetic_sources"])
        self.assertEqual(6, summary["synthetic_batches"])
        self.assertEqual(200, summary["synthetic_entities"])
        self.assertEqual(200, summary["migration_candidates"])
        self.assertEqual(0, summary["quarantined_entities"])
        self.assertTrue(summary["order_invariant_receipt"])
        self.assertTrue(summary["receipt_verified"])
        self.assertEqual(
            {
                "batch_content_drift": "BATCH_CONTENT_MISMATCH",
                "batch_count_drift": "BATCH_RECORD_COUNT_MISMATCH",
                "canonical_conflict": "CANONICAL_FIELD_CONFLICT",
                "changed_event_replay": "EVENT_REPLAY_CONFLICT",
                "source_missing_entity": "SOURCE_ENTITY_MISSING",
            },
            summary["hostile_classes"],
        )


if __name__ == "__main__":
    unittest.main()
