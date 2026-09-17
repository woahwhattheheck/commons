from __future__ import annotations

import copy
import hashlib
import subprocess
import sys
import unittest

from revenue.trafficflowbench_2026.benchmark import synthetic_evidence
from revenue.trafficflowbench_2026.contract import (
    UPSTREAM,
    authority_ceiling,
    canonical_json_bytes,
    contract_receipt,
    validate_authority_claims,
)
from revenue.trafficflowbench_2026.methods import (
    projected_ridge_odme,
    queue_wave_forecast,
    reconstruct_state,
    triangular_fd_flow_cap,
)
from revenue.trafficflowbench_2026.scoring import (
    odme_score,
    physics_score,
    queue_iou,
    state_regime_score,
    total_score,
)
from revenue.trafficflowbench_2026.submission import (
    compile_submission,
    verify_compiled_submission,
)


def _rehash_receipt(receipt):
    body = copy.deepcopy(receipt)
    body.pop("receiptSha256", None)
    receipt["receiptSha256"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()


class TrafficFlowBenchContractTests(unittest.TestCase):
    def test_upstream_generation_and_leakage_fix_are_pinned(self):
        self.assertEqual(
            UPSTREAM["commit"], "c88cddf533bbf0afa4ff1fc6c031d760a08e7a31"
        )
        self.assertIn("split-local", UPSTREAM["task4_prior_rule"])
        self.assertEqual(
            UPSTREAM["files"]["src/task4/score_task4.py"],
            "9cfe8df0ac0764d6599057610a625f86b742bb3d",
        )

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
        incidence = [[1.0, 1.0, 0.0], [0.0, 1.0, 1.0]]
        counts = [50.0, 30.0]
        prior = [25.0, 20.0, 15.0]
        score = odme_score(
            truth, truth, incidence, counts, prior, ["A", "B", "B"]
        )
        self.assertAlmostEqual(score["S_ODME"], 1.0)


class MethodTests(unittest.TestCase):
    def test_fd_projection_caps_implausible_flow(self):
        cap = triangular_fd_flow_cap(
            40.0,
            lanes=2,
            free_speed_kmh=100.0,
            capacity_per_lane_vph=1800.0,
        )
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
        self.assertLessEqual(
            flow,
            triangular_fd_flow_cap(
                speed,
                lanes=2,
                free_speed_kmh=100,
                capacity_per_lane_vph=1800,
            ),
        )

    def test_visible_neighbor_reconstruction_beats_historical_mean_on_synthetic_gap(self):
        truth_speed = [42.0]
        truth_flow = [2500.0]
        historical = state_regime_score(
            truth_speed, truth_flow, [88.0], [1000.0], [2]
        )["S_state"]
        pred = reconstruct_state(
            historical_speed_kmh=88,
            historical_flow_vph=1000,
            observed_neighbors=[(40, 2450), (44, 2550)],
            lanes=2,
            free_speed_kmh=100,
            capacity_per_lane_vph=1800,
        )
        improved = state_regime_score(
            truth_speed, truth_flow, [pred[0]], [pred[1]], [2]
        )["S_state"]
        self.assertGreater(improved, historical + 0.25)

    def test_queue_wave_forecast_beats_origin_persistence_on_onset_fixture(self):
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
        incidence = [
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 1.0],
            [1.0, 0.0, 1.0],
        ]
        counts = [50.0, 30.0, 40.0]
        prior = [10.0, 10.0, 10.0]
        solved = projected_ridge_odme(incidence, counts, prior, iterations=2500)

        def error(flow):
            return sum(
                abs(sum(a * x for a, x in zip(row, flow)) - count)
                for row, count in zip(incidence, counts)
            )

        self.assertTrue(all(x >= 0 for x in solved))
        self.assertLess(error(solved), error(prior) * 0.20)


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
            {
                "submission_id": "1",
                "task": "state",
                "panel": "P",
                "timestamp": "2026-01-01T00:00:00Z",
                "station_id": "S",
                "link_id": "L",
                "mask_regime": "R1",
            },
            {
                "submission_id": "2",
                "task": "queue",
                "window_id": "W",
                "timestamp": "2026-01-01T00:05:00Z",
                "link_id": "L",
            },
            {
                "submission_id": "3",
                "task": "odme",
                "panel": "P",
                "departure_time": "AM",
                "path_id": "PATH",
            },
        ]
        self.state = [
            {
                "panel": "P",
                "timestamp": "2026-01-01T00:00:00Z",
                "station_id": "S",
                "link_id": "L",
                "mask_regime": "R1",
                "speed_kmh": 70,
                "flow_vph": 2100,
            }
        ]
        self.queue = [
            {
                "window_id": "W",
                "timestamp": "2026-01-01T00:05:00Z",
                "link_id": "L",
                "queue_pred": 1,
            }
        ]
        self.odme = [
            {
                "panel": "P",
                "departure_time": "AM",
                "path_id": "PATH",
                "origin_zone": "O",
                "destination_zone": "D",
                "path_flow": 12.5,
            }
        ]

    def compile(self, **kwargs):
        return compile_submission(
            kwargs.pop("keys", self.keys),
            state_rows=kwargs.pop("state", self.state),
            queue_rows=kwargs.pop("queue", self.queue),
            odme_rows=kwargs.pop("odme", self.odme),
            **kwargs,
        )

    def verify(self, payload, receipt, **kwargs):
        return verify_compiled_submission(
            payload,
            receipt,
            submission_key_rows=kwargs.pop("keys", self.keys),
            state_rows=kwargs.pop("state", self.state),
            queue_rows=kwargs.pop("queue", self.queue),
            odme_rows=kwargs.pop("odme", self.odme),
        )

    def test_compile_and_verify_is_deterministic_and_zero_fills_other_task_columns(self):
        payload, receipt = self.compile()
        payload2, receipt2 = self.compile()
        self.assertEqual((payload, receipt), (payload2, receipt2))
        self.assertTrue(self.verify(payload, receipt))
        self.assertIn("1,state,70.0,2100.0,0.0,0.0", payload)
        self.assertIn("2,queue,0.0,0.0,1.0,0.0", payload)
        self.assertEqual(receipt["schema"], "trafficflowbench-local-submission/v2")
        self.assertEqual(len(receipt["compileInputSha256"]), 64)
        self.assertEqual(len(receipt["compilerContractSha256"]), 64)

    def test_missing_row_fails_closed_by_default(self):
        with self.assertRaises(ValueError):
            self.compile(queue=[])

    def test_incomplete_mode_binds_gaps_and_recompiles(self):
        payload, receipt = self.compile(queue=[], require_complete=False)
        self.assertEqual(receipt["gaps"]["queue"], 1)
        self.assertTrue(self.verify(payload, receipt, queue=[]))

    def test_duplicate_task_key_and_bad_queue_rejected(self):
        with self.assertRaises(ValueError):
            self.compile(state=self.state + copy.deepcopy(self.state))
        bad_queue = [dict(self.queue[0], queue_pred=2)]
        with self.assertRaises(ValueError):
            self.compile(queue=bad_queue)

    def test_payload_tamper_fails(self):
        payload, receipt = self.compile()
        self.assertFalse(self.verify(payload + "x", receipt))

    def test_self_authored_receipt_without_compile_inputs_has_no_provenance_standing(self):
        payload, receipt = self.compile()
        self.assertFalse(verify_compiled_submission(payload, receipt))

    def test_authority_forgery_fails_even_after_receipt_rehash(self):
        payload, receipt = self.compile()
        forged = copy.deepcopy(receipt)
        forged["authority"]["submissionSent"] = True
        _rehash_receipt(forged)
        self.assertFalse(self.verify(payload, forged))

    def test_receipt_field_deletion_fails_even_after_rehash(self):
        payload, receipt = self.compile()
        forged = copy.deepcopy(receipt)
        del forged["upstreamCommit"]
        _rehash_receipt(forged)
        self.assertFalse(self.verify(payload, forged))

    def test_task_irrelevant_column_mutation_fails_even_after_payload_and_receipt_rehash(self):
        payload, receipt = self.compile()
        lines = payload.splitlines()
        fields = lines[1].split(",")
        fields[-1] = "9.0"
        lines[1] = ",".join(fields)
        forged_payload = "\n".join(lines) + "\n"
        forged_receipt = copy.deepcopy(receipt)
        forged_receipt["csvSha256"] = hashlib.sha256(
            forged_payload.encode("utf-8")
        ).hexdigest()
        _rehash_receipt(forged_receipt)
        self.assertFalse(self.verify(forged_payload, forged_receipt))

    def test_meaningful_payload_plus_receipt_remint_fails_exact_recompile(self):
        payload, receipt = self.compile()
        lines = payload.splitlines()
        fields = lines[1].split(",")
        fields[3] = "2200.0"
        lines[1] = ",".join(fields)
        forged_payload = "\n".join(lines) + "\n"
        forged_receipt = copy.deepcopy(receipt)
        forged_receipt["csvSha256"] = hashlib.sha256(
            forged_payload.encode("utf-8")
        ).hexdigest()
        _rehash_receipt(forged_receipt)
        self.assertFalse(self.verify(forged_payload, forged_receipt))

    def test_compile_input_transplant_fails(self):
        payload, receipt = self.compile()
        changed_state = [dict(self.state[0], flow_vph=2200)]
        self.assertFalse(self.verify(payload, receipt, state=changed_state))

    def test_hostile_receipt_suite_runs_under_optimized_python(self):
        if sys.flags.optimize:
            return
        proc = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "tests.test_trafficflowbench_2026.SubmissionTests",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)


if __name__ == "__main__":
    unittest.main()
