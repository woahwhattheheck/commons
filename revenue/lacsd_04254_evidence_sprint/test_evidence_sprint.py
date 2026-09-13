from __future__ import annotations

import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import evidence_sprint
from evidence_sprint import (
    EVENT_SCHEMA,
    MAX_JSON_BYTES,
    ValidationError,
    build_portfolio,
    canonical_json,
    compile_receipt,
    evaluate_candidate,
    reference_candidate,
    verify_receipt,
    _load_strict_json,
)


class EvidenceSprintTests(unittest.TestCase):
    def setUp(self):
        self.portfolio = build_portfolio()
        self.candidate = reference_candidate()

    def test_portfolio_is_deterministic_and_has_required_fault_classes(self):
        self.assertEqual(self.portfolio, build_portfolio())
        self.assertEqual(len(self.portfolio["scenarios"]), 10)
        classes = {row["fault_class"] for row in self.portfolio["scenarios"]}
        self.assertEqual(classes, {"normal_diurnal", "blockage_drift", "storm_inflow_infiltration", "sensor_dropout", "duplicate_packet_replay", "transport_interruption_recovery"})
        self.assertEqual(len(self.portfolio["portfolio_sha256"]), 64)

    def test_reference_candidate_meets_every_binary_gate(self):
        result = evaluate_candidate(self.candidate)
        self.assertEqual(result["status"], "READY_FOR_BUYER_REVIEW")
        self.assertTrue(all(result["gates"].values()))
        self.assertEqual(result["alert_detection_rate"], 1.0)
        self.assertEqual(result["false_urgent_alert_rate"], 0.0)
        self.assertEqual(result["duplicate_effect_count"], 0)
        self.assertEqual(result["candidate_build_sha256"], self.candidate["candidate_build_sha256"])
        self.assertFalse(result["authority"]["field_performance_claimed"])
        self.assertFalse(result["authority"]["production_control_authorized"])
        self.assertFalse(result["authority"]["payment_or_revenue_claimed"])

    def test_duplicate_effect_on_replayed_packet_holds(self):
        candidate = copy.deepcopy(self.candidate)
        base = next(event for event in candidate["events"] if event["scenario_id"] == "duplicate-replay-01")
        extra = dict(base)
        extra["event_id"] = "event-duplicate-replay-extra"
        extra["effect_id"] = "effect-duplicate-replay-extra"
        extra["observed_at_s"] += 1
        candidate["events"].append(extra)
        result = evaluate_candidate(candidate)
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["duplicate_effect_count"], 1)
        self.assertFalse(result["gates"]["duplicate_effect_count_0"])

    def test_false_urgent_alert_holds(self):
        candidate = copy.deepcopy(self.candidate)
        event = next(event for event in candidate["events"] if event["scenario_id"] == "normal-diurnal-01")
        event["disposition"] = "ALERT"
        event["effect_id"] = "effect-false-alert"
        result = evaluate_candidate(candidate)
        self.assertEqual(result["status"], "HOLD")
        self.assertGreater(result["false_urgent_alert_rate"], 0.0)

    def test_late_alert_holds(self):
        candidate = copy.deepcopy(self.candidate)
        event = next(event for event in candidate["events"] if event["scenario_id"] == "blockage-drift-01")
        event["source_packet_id"] = "b1-4"
        event["observed_at_s"] = 720
        result = evaluate_candidate(candidate)
        self.assertEqual(result["status"], "HOLD")
        self.assertLess(result["timeliness_pass_rate"], 1.0)

    def test_fabricated_latency_timestamp_fails_closed(self):
        candidate = copy.deepcopy(self.candidate)
        event = next(event for event in candidate["events"] if event["scenario_id"] == "blockage-drift-01")
        event["observed_at_s"] = 481
        with self.assertRaises(ValidationError):
            evaluate_candidate(candidate)

    def test_alert_cannot_bind_transport_unavailable_occurrence(self):
        candidate = copy.deepcopy(self.candidate)
        event = next(event for event in candidate["events"] if event["scenario_id"] == "recovery-after-interruption-01")
        event["observed_at_s"] = 420
        event["source_packet_id"] = "x1-1"
        with self.assertRaises(ValidationError):
            evaluate_candidate(candidate)

    def test_no_data_must_bind_transport_unavailable_occurrence(self):
        candidate = copy.deepcopy(self.candidate)
        event = next(event for event in candidate["events"] if event["scenario_id"] == "sensor-dropout-01")
        event["source_packet_id"] = "d1-1"
        event["observed_at_s"] = 300
        with self.assertRaises(ValidationError):
            evaluate_candidate(candidate)

    def test_missing_scenario_holds(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["events"] = [event for event in candidate["events"] if event["scenario_id"] != "sensor-dropout-02"]
        result = evaluate_candidate(candidate)
        self.assertEqual(result["status"], "HOLD")
        self.assertFalse(result["gates"]["all_scenarios_covered"])

    def test_lineage_transplant_holds_not_silently_passes(self):
        candidate = copy.deepcopy(self.candidate)
        a = candidate["events"][0]
        b = candidate["events"][1]
        a["input_sha256"] = b["input_sha256"]
        result = evaluate_candidate(candidate)
        self.assertEqual(result["status"], "HOLD")
        self.assertLess(result["lineage_pass_rate"], 1.0)

    def test_wrong_portfolio_hash_fails_closed(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["portfolio_sha256"] = "0" * 64
        with self.assertRaises(ValidationError):
            evaluate_candidate(candidate)

    def test_unknown_candidate_field_fails_closed(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["buyer_accepted"] = True
        with self.assertRaises(ValidationError):
            evaluate_candidate(candidate)

    def test_unknown_event_field_fails_closed(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["events"][0]["dispatch_authorized"] = True
        with self.assertRaises(ValidationError):
            evaluate_candidate(candidate)

    def test_non_alert_cannot_carry_effect_id(self):
        candidate = copy.deepcopy(self.candidate)
        event = next(event for event in candidate["events"] if event["disposition"] == "CLEAR")
        event["effect_id"] = "work-order-pretend"
        with self.assertRaises(ValidationError):
            evaluate_candidate(candidate)

    def test_alert_requires_effect_id(self):
        candidate = copy.deepcopy(self.candidate)
        event = next(event for event in candidate["events"] if event["disposition"] == "ALERT")
        event["effect_id"] = None
        with self.assertRaises(ValidationError):
            evaluate_candidate(candidate)

    def test_unknown_packet_id_fails_closed(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["events"][0]["source_packet_id"] = "not-in-stream"
        with self.assertRaises(ValidationError):
            evaluate_candidate(candidate)

    def test_duplicate_event_id_fails_closed(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["events"].append(copy.deepcopy(candidate["events"][0]))
        with self.assertRaises(ValidationError):
            evaluate_candidate(candidate)

    def test_recovery_alert_before_transport_recovery_fails_closed(self):
        candidate = copy.deepcopy(self.candidate)
        event = next(event for event in candidate["events"] if event["scenario_id"] == "recovery-after-interruption-01")
        event["observed_at_s"] = 500
        with self.assertRaises(ValidationError):
            evaluate_candidate(candidate)

    def test_receipt_exactly_recomputes_and_detects_tamper(self):
        receipt = compile_receipt(self.candidate)
        self.assertEqual(verify_receipt(receipt, self.candidate), receipt)
        tampered = copy.deepcopy(receipt)
        tampered["evaluation"]["status"] = "HOLD"
        with self.assertRaises(ValidationError):
            verify_receipt(tampered, self.candidate)

    def test_receipt_cannot_be_transplanted_to_changed_candidate(self):
        receipt = compile_receipt(self.candidate)
        changed = copy.deepcopy(self.candidate)
        changed["model_version"] = "v2"
        with self.assertRaises(ValidationError):
            verify_receipt(receipt, changed)

    def test_fresh_recompile_rejects_changed_envelope_build_identity(self):
        changed = copy.deepcopy(self.candidate)
        changed["model_version"] = "v2"
        changed["candidate_build_sha256"] = "a" * 64
        with self.assertRaises(ValidationError):
            compile_receipt(changed)

    def test_single_event_build_binding_mismatch_fails_closed(self):
        changed = copy.deepcopy(self.candidate)
        changed["events"][0]["candidate_build_sha256"] = "b" * 64
        with self.assertRaises(ValidationError):
            evaluate_candidate(changed)

    def test_single_event_model_identity_mismatch_fails_closed(self):
        changed = copy.deepcopy(self.candidate)
        changed["events"][0]["model_version"] = "pretend-v9"
        with self.assertRaises(ValidationError):
            evaluate_candidate(changed)

    def test_cross_scenario_effect_id_transplant_fails_closed(self):
        changed = copy.deepcopy(self.candidate)
        alerts = [e for e in changed["events"] if e["disposition"] == "ALERT"]
        alerts[1]["effect_id"] = alerts[0]["effect_id"]
        with self.assertRaises(ValidationError):
            evaluate_candidate(changed)

    def test_strict_json_loader_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dupe.json"
            path.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            with self.assertRaises(ValidationError):
                _load_strict_json(path)

    def test_strict_json_loader_rejects_nonfinite_constant(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nan.json"
            path.write_text('{"x":NaN}', encoding="utf-8")
            with self.assertRaises(ValidationError):
                _load_strict_json(path)

    def test_loader_rejects_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValidationError):
                _load_strict_json(Path(tmp))

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW") and hasattr(os, "symlink"), "requires no-follow symlink support")
    def test_loader_rejects_final_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target.json"
            link = Path(tmp) / "link.json"
            target.write_text('{"x":1}', encoding="utf-8")
            os.symlink(target, link)
            with self.assertRaises(ValidationError):
                _load_strict_json(link)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires FIFO support")
    def test_loader_rejects_fifo_without_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            fifo = Path(tmp) / "input.fifo"
            os.mkfifo(fifo)
            with self.assertRaises(ValidationError):
                _load_strict_json(fifo)

    def test_loader_rejects_oversize_regular_file_before_materializing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "too-big.json"
            with path.open("wb") as handle:
                handle.seek(MAX_JSON_BYTES)
                handle.write(b"x")
            with self.assertRaises(ValidationError):
                _load_strict_json(path)

    def test_loader_rejects_generation_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ok.json"
            path.write_text('{"x":1}', encoding="utf-8")
            with mock.patch.object(evidence_sprint, "_file_generation", side_effect=[(1, 1, 1, 7, 1, 1), (1, 1, 1, 7, 2, 2)]):
                with self.assertRaises(ValidationError):
                    _load_strict_json(path)

    def test_canonical_json_is_order_independent_for_objects(self):
        self.assertEqual(canonical_json({"b": 2, "a": 1}), canonical_json({"a": 1, "b": 2}))

    def test_claim_test_result_rows_are_machine_readable_and_all_pass_reference(self):
        result = evaluate_candidate(self.candidate)
        claims = result["claims"]
        self.assertEqual(len(claims), 8)
        self.assertEqual(len({row["claim_id"] for row in claims}), 8)
        self.assertTrue(all(set(row) == {"claim_id", "test", "passed", "evidence"} for row in claims))
        self.assertTrue(all(row["passed"] for row in claims))
        exactly_once = next(row for row in claims if row["claim_id"] == "synthetic.exactly-once-work-intent")
        self.assertEqual(exactly_once["evidence"]["duplicate_effect_count"], 0)

    def test_replayed_alert_with_same_work_intent_id_remains_exactly_once(self):
        candidate = copy.deepcopy(self.candidate)
        base = next(event for event in candidate["events"] if event["scenario_id"] == "duplicate-replay-01")
        retry = dict(base)
        retry["event_id"] = "event-duplicate-replay-same-intent-retry"
        retry["observed_at_s"] = 481
        candidate["events"].append(retry)
        result = evaluate_candidate(candidate)
        self.assertEqual(result["status"], "READY_FOR_BUYER_REVIEW")
        row = next(row for row in result["scenario_results"] if row["scenario_id"] == "duplicate-replay-01")
        self.assertEqual(row["event_count"], 2)
        self.assertEqual(row["distinct_effect_count"], 1)

    def test_conflicting_retransmission_disposition_holds(self):
        candidate = copy.deepcopy(self.candidate)
        base = next(event for event in candidate["events"] if event["scenario_id"] == "duplicate-replay-01")
        conflict = dict(base)
        conflict["event_id"] = "event-duplicate-replay-conflict"
        conflict["observed_at_s"] = 481
        conflict["disposition"] = "CLEAR"
        conflict["effect_id"] = None
        candidate["events"].append(conflict)
        result = evaluate_candidate(candidate)
        self.assertEqual(result["status"], "HOLD")
        self.assertFalse(result["gates"]["exact_expected_dispositions"])

    def test_out_of_order_event_input_canonicalizes_to_same_receipt(self):
        receipt = compile_receipt(self.candidate)
        reversed_candidate = copy.deepcopy(self.candidate)
        reversed_candidate["events"] = list(reversed(reversed_candidate["events"]))
        self.assertEqual(receipt, compile_receipt(reversed_candidate))

    def test_candidate_events_use_expected_schema(self):
        self.assertTrue(self.candidate["events"])
        self.assertTrue(all(event["schema"] == EVENT_SCHEMA for event in self.candidate["events"]))


if __name__ == "__main__":
    unittest.main()
