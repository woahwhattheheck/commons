from __future__ import annotations

import copy
import hashlib
import unittest

from revenue.trafficflowbench_2026.benchmark import synthetic_evidence
from revenue.trafficflowbench_2026.contract import UPSTREAM, authority_ceiling, canonical_json_bytes, contract_receipt, validate_authority_claims
from revenue.trafficflowbench_2026.methods import projected_ridge_odme, queue_wave_forecast, reconstruct_state, triangular_fd_flow_cap
from revenue.trafficflowbench_2026.scoring import odme_score, physics_score, queue_iou, state_regime_score, total_score
from revenue.trafficflowbench_2026.submission import compile_submission, verify_compiled_submission


class TrafficFlowBenchContractTests(unittest.TestCase):
    def test_upstream_generation_and_leakage_fix_are_pinned(self):
        self.assertEqual(UPSTREAM["commit"], "c88cddf533bbf0afa4ff1fc6c031d760a08e7a31")
        self.assertIn("split-local", UPSTREAM["task4_prior_rule"])
        self.assertEqual(UPSTREAM["files"]["src/task4/score_task4.py"], "9cfe8df0ac0764d6599057610a625f86b742bb3d")

    def test_authority_ceiling_is_all_false(self):
        ceiling = authority_ceiling()
        for key, value in ceiling.items():
            if key != "evidenceClass":
                self.assertIs(value, False)
        validate_authority_claims(ceiling)
        bad = dict(ceiling)
        bad["submissionSent"] = True
        with self.assertRaises(ValueError):
            validate_authority_claims(bad)

    def test_contract_receipt_deterministic(self):
        self.assertEqual(contract_receipt(), contract_receipt())
        self.assertEqual(len(contract_receipt()["receiptSha256"]), 64)


class ScoringTests(unittest.TestCase):
    def test_state_score_matches_published_formula(self):
        result = state_regime_score([80.0], [1800.0], [55.0], [600.0], [2])
        self.assertAlmostEqual(result["S_speed"], 0.0)
        self.assertAlmostEqual(result["rmse_flow_per_lane"], 600.0)
        self.assertAlmostEqual(result["S_flow"], 0.0)
        self.assertAlmostEqual(result["S_state"], 0.0)

    def test_queue_iou_and_empty_empty_rule(self):
        self.assertEqual(queue_iou([0, 0, 0], [0, 0, 0]), 1.0)
        self.assertAlmostEqual(queue_iou([1, 1, 0, 0], [1, 0, 1, 0]), 1 / 3)

    def test_published_aggregations(self):
        self.assertAlmostEqual(physics_score(0.9, 0.6), 0.7)
        self.assertAlmostEqual(total_score(1.0, 1.0, 1.0, 1.0), 1.0)
        self.assertAlmostEqual(total_score(0.0, 0.0, 0.0, 0.0), 0.0)

    def test_odme_local_mirror_perfect_is_one(self):
        truth = [30.0, 20.0, 10.0]
        A = [[1.0, 1.0, 0.0], [0.0, 1.0, 1.0]]
        counts = [50.0, 30.0]
        prior = [25.0, 20.0, 15.0]
        score = odme_score(truth, truth, A, counts, prior, ["A", "B", "B"])
        self.assertAlmostEqual(score["S_ODME"], 1.0)


class MethodTests(unittest.TestCase):
    def test_fd_projection_caps_implausible_flow(self):
        cap = triangular_fd_flow_cap(40.0, lanes=2, free_speed_kmh=100.0, capacity_per_lane_vph=1800.0)
        self.assertGreater(cap, 0.0)
        self.assertLessEqual(cap, 3600.0)
        speed, flow = reconstruct_state(
            historical_speed_kmh=90,
            historical_flow_vph=1000,
            observed_neighbors=[(40, 9000), (42, 8500)],
            lanes=2,
            free_speed_kmh=100,
            capacity_per_lane_vph=1800,
        )
        self.assertLessEqual(flow, triangular_fd_flow_cap(speed, lanes=2, free_speed_kmh=100, capacity_per_lane_vph=1800))

    def test_visible_neighbor_reconstruction_beats_historical_mean_on_synthetic_gap(self):
        truth_speed = [42.0]
        truth_flow = [2500.0]
        historical = state_regime_score(truth_speed, truth_flow, [88.0], [1000.0], [2])["S_state"]
        pred = reconstruct_state(
            historical_speed_kmh=88,
            historical_flow_vph=1000,
            observed_neighbors=[(40, 2450), (44, 2550)],
            lanes=2,
            free_speed_kmh=100,
            capacity_per_lane_vph=1800,
        )
        improved = state_regime_score(truth_speed, truth_flow, [pred[0]], [pred[1]], [2])["S_state"]
        self.assertGreater(improved, historical + 0.25)

    def test_queue_wave_forecast_beats_origin_persistence_on_onset_fixture(self):
        # Link order upstream->downstream. Downstream queue is forming and propagates upstream.
        history = [
            [95, 92, 90],
            [92, 86, 82],
            [88, 76, 69],
            [82, 67, 55],
        ]
        forecast = queue_wave_forecast(history, [100, 100, 100], horizons=3)
        truth = [[0, 1, 1], [1, 1, 1], [1, 1, 1]]
        wave = sum(queue_iou(t, p) for t, p in zip(truth, forecast)) / 3
        persistence = [0, 0, 1]
        base = sum(queue_iou(t, persistence) for t in truth) / 3
        self.assertGreater(wave, base)

    def test_projected_ridge_reduces_link_error_and_stays_nonnegative(self):
        A = [[1.0, 1.0, 0.0], [0.0, 1.0, 1.0], [1.0, 0.0, 1.0]]
        counts = [50.0, 30.0, 40.0]
        prior = [10.0, 10.0, 10.0]
        solved = projected_ridge_odme(A, counts, prior, iterations=2500)
        def err(f):
            return sum(abs(sum(a * x for a, x in zip(row, f)) - c) for row, c in zip(A, counts))
        self.assertTrue(all(x >= 0 for x in solved))
        self.assertLess(err(solved), err(prior) * 0.20)


class EvidenceLedgerTests(unittest.TestCase):
    def test_synthetic_evidence_records_material_lifts_without_authority_claims(self):
        report = synthetic_evidence()
        self.assertGreater(report["task1"]["absoluteLift"], 0.25)
        self.assertGreater(report["task2"]["absoluteLift"], 0.25)
        self.assertLess(report["task4"]["relativeError"], 0.20)
        self.assertEqual(report["evidenceClass"], "LOCAL_SYNTHETIC")
        self.assertIs(report["authority"]["officialScoreEstablished"], False)
        self.assertIs(report["authority"]["prizeAwarded"], False)


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.keys = [
            {"submission_id": "1", "task": "state", "panel": "P", "timestamp": "2026-01-01T00:00:00Z", "station_id": "S", "link_id": "L", "mask_regime": "R1"},
            {"submission_id": "2", "task": "queue", "window_id": "W", "timestamp": "2026-01-01T00:05:00Z", "link_id": "L"},
            {"submission_id": "3", "task": "odme", "panel": "P", "departure_time": "AM", "path_id": "PATH"},
        ]
        self.state = [{"panel": "P", "timestamp": "2026-01-01T00:00:00Z", "station_id": "S", "link_id": "L", "mask_regime": "R1", "speed_kmh": 70, "flow_vph": 2100}]
        self.queue = [{"window_id": "W", "timestamp": "2026-01-01T00:05:00Z", "link_id": "L", "queue_pred": 1}]
        self.odme = [{"panel": "P", "departure_time": "AM", "path_id": "PATH", "origin_zone": "O", "destination_zone": "D", "path_flow": 12.5}]

    def test_compile_and_verify_is_deterministic_and_zero_fills_other_task_columns(self):
        payload, receipt = compile_submission(self.keys, state_rows=self.state, queue_rows=self.queue, odme_rows=self.odme)
        payload2, receipt2 = compile_submission(self.keys, state_rows=self.state, queue_rows=self.queue, odme_rows=self.odme)
        self.assertEqual((payload, receipt), (payload2, receipt2))
        self.assertTrue(verify_compiled_submission(payload, receipt, self.keys))
        self.assertIn("1,state,70.0,2100.0,0.0,0.0", payload)
        self.assertIn("2,queue,0.0,0.0,1.0,0.0", payload)

    def test_missing_row_fails_closed_by_default(self):
        with self.assertRaises(ValueError):
            compile_submission(self.keys, state_rows=self.state, queue_rows=[], odme_rows=self.odme)

    def test_duplicate_task_key_and_bad_queue_rejected(self):
        with self.assertRaises(ValueError):
            compile_submission(self.keys, state_rows=self.state + copy.deepcopy(self.state), queue_rows=self.queue, odme_rows=self.odme)
        bad_queue = [dict(self.queue[0], queue_pred=2)]
        with self.assertRaises(ValueError):
            compile_submission(self.keys, state_rows=self.state, queue_rows=bad_queue, odme_rows=self.odme)

    def test_receipt_tamper_fails(self):
        payload, receipt = compile_submission(self.keys, state_rows=self.state, queue_rows=self.queue, odme_rows=self.odme)
        self.assertFalse(verify_compiled_submission(payload + "x", receipt, self.keys))
        authority_tamper = copy.deepcopy(receipt)
        authority_tamper["authority"]["submissionSent"] = True
        self.assertFalse(verify_compiled_submission(payload, authority_tamper, self.keys))
        source_tamper = dict(receipt, upstreamCommit="deadbeef")
        self.assertFalse(verify_compiled_submission(payload, source_tamper, self.keys))

    def test_receipt_exact_keys_and_submission_key_generation_are_bound(self):
        payload, receipt = compile_submission(self.keys, state_rows=self.state, queue_rows=self.queue, odme_rows=self.odme)
        missing = dict(receipt)
        del missing["gaps"]
        self.assertFalse(verify_compiled_submission(payload, missing, self.keys))
        extra = dict(receipt, surprise="field")
        self.assertFalse(verify_compiled_submission(payload, extra, self.keys))
        wrong_keys = copy.deepcopy(self.keys)
        wrong_keys[0]["link_id"] = "OTHER"
        self.assertFalse(verify_compiled_submission(payload, receipt, wrong_keys))
        self.assertFalse(verify_compiled_submission(payload, receipt, list(reversed(self.keys))))

    def test_rehashed_task_column_forgery_still_fails(self):
        payload, receipt = compile_submission(self.keys, state_rows=self.state, queue_rows=self.queue, odme_rows=self.odme)
        forged_payload = payload.replace("1,state,70.0,2100.0,0.0,0.0", "1,state,70.0,2100.0,0.0,9.0")
        forged = copy.deepcopy(receipt)
        forged["csvSha256"] = hashlib.sha256(forged_payload.encode("utf-8")).hexdigest()
        body = dict(forged)
        body.pop("receiptSha256")
        forged["receiptSha256"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
        self.assertFalse(verify_compiled_submission(forged_payload, forged, self.keys))

    def test_task_specific_schema_edges_fail_closed(self):
        bad_regime = [dict(self.state[0], mask_regime="R4")]
        with self.assertRaises(ValueError):
            compile_submission(self.keys, state_rows=bad_regime, queue_rows=self.queue, odme_rows=self.odme)
        no_zone = [dict(self.odme[0])]
        del no_zone[0]["origin_zone"]
        with self.assertRaises(ValueError):
            compile_submission(self.keys, state_rows=self.state, queue_rows=self.queue, odme_rows=no_zone)

    def test_null_keys_and_malformed_receipt_fail_closed(self):
        bad_keys = [dict(self.keys[0], link_id=None), *self.keys[1:]]
        with self.assertRaises(ValueError):
            compile_submission(bad_keys, state_rows=self.state, queue_rows=self.queue, odme_rows=self.odme)
        payload, _ = compile_submission(self.keys, state_rows=self.state, queue_rows=self.queue, odme_rows=self.odme)
        self.assertFalse(verify_compiled_submission(payload, [], self.keys))


if __name__ == "__main__":
    unittest.main()
