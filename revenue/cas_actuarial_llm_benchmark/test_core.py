from __future__ import annotations

import copy
import unittest

from revenue.cas_actuarial_llm_benchmark.core import (
    BenchmarkInputError,
    evaluate_benchmark,
    verify_snapshot,
)
from revenue.cas_actuarial_llm_benchmark.fixture import synthetic_evidence


class CasActuarialBenchmarkTests(unittest.TestCase):
    def test_acceptance_fixture_is_ready_and_deterministic(self):
        evidence = synthetic_evidence()
        first = evaluate_benchmark(evidence)
        second = evaluate_benchmark(copy.deepcopy(evidence))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PROPOSAL_TECHNICAL_EVIDENCE_READY")
        self.assertTrue(first["signals"]["matrix_complete"])
        self.assertEqual(first["signals"]["task_count"], 2)
        self.assertEqual(first["signals"]["model_count"], 6)
        self.assertEqual(first["signals"]["run_count"], 12)
        self.assertTrue(verify_snapshot(first))

    def test_authority_remains_noncommercial_and_nonactuarial(self):
        result = evaluate_benchmark(synthetic_evidence())
        self.assertEqual(
            result["authority"],
            {
                "actuarial_task_validity": False,
                "cas_submission": False,
                "model_provider_action": False,
                "contract": False,
                "payment": False,
                "recognized_revenue": False,
            },
        )

    def test_tampered_snapshot_fails_integrity(self):
        result = evaluate_benchmark(synthetic_evidence())
        result["runs"][0]["metrics"]["accuracy"] = "1.000000000000"
        self.assertFalse(verify_snapshot(result))

    def test_missing_commercial_provider_fails_closed(self):
        evidence = synthetic_evidence()
        evidence["models"] = [m for m in evidence["models"] if m["provider"] != "google"]
        evidence["runs"] = [r for r in evidence["runs"] if r["model_id"] != "commercial-google"]
        with self.assertRaisesRegex(BenchmarkInputError, "commercial roster"):
            evaluate_benchmark(evidence)

    def test_fewer_than_three_open_models_fails_closed(self):
        evidence = synthetic_evidence()
        dropped = {"open-model-b", "open-model-c"}
        evidence["models"] = [m for m in evidence["models"] if m["model_id"] not in dropped]
        evidence["runs"] = [r for r in evidence["runs"] if r["model_id"] not in dropped]
        with self.assertRaisesRegex(BenchmarkInputError, "at least three distinct open models"):
            evaluate_benchmark(evidence)

    def test_unpublishable_dataset_fails_closed(self):
        evidence = synthetic_evidence()
        evidence["tasks"][0]["dataset"]["license_status"] = "unknown"
        with self.assertRaisesRegex(BenchmarkInputError, "confirmed_publishable"):
            evaluate_benchmark(evidence)

    def test_non_https_dataset_source_fails_closed(self):
        evidence = synthetic_evidence()
        evidence["tasks"][0]["dataset"]["source_uri"] = "file:///private/data.csv"
        with self.assertRaisesRegex(BenchmarkInputError, "must use https"):
            evaluate_benchmark(evidence)

    def test_dataset_digest_mismatch_fails_closed(self):
        evidence = synthetic_evidence()
        evidence["runs"][0]["dataset_sha256"] = "0" * 64
        with self.assertRaisesRegex(BenchmarkInputError, "dataset digest"):
            evaluate_benchmark(evidence)

    def test_split_digest_mismatch_fails_closed(self):
        evidence = synthetic_evidence()
        evidence["runs"][0]["split_sha256"] = "0" * 64
        with self.assertRaisesRegex(BenchmarkInputError, "split digest"):
            evaluate_benchmark(evidence)

    def test_model_artifact_digest_mismatch_fails_closed(self):
        evidence = synthetic_evidence()
        evidence["runs"][0]["model_artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(BenchmarkInputError, "model artifact digest"):
            evaluate_benchmark(evidence)

    def test_duplicate_run_pair_fails_closed(self):
        evidence = synthetic_evidence()
        duplicate = copy.deepcopy(evidence["runs"][0])
        duplicate["run_id"] = "duplicate-run"
        evidence["runs"].append(duplicate)
        with self.assertRaisesRegex(BenchmarkInputError, "model/task pair"):
            evaluate_benchmark(evidence)

    def test_missing_matrix_cell_fails_closed(self):
        evidence = synthetic_evidence()
        evidence["runs"].pop()
        with self.assertRaisesRegex(BenchmarkInputError, "matrix incomplete"):
            evaluate_benchmark(evidence)

    def test_duplicate_item_id_fails_closed(self):
        evidence = synthetic_evidence()
        evidence["runs"][0]["records"][1]["item_id"] = evidence["runs"][0]["records"][0]["item_id"]
        with self.assertRaisesRegex(BenchmarkInputError, "item_id values must be unique"):
            evaluate_benchmark(evidence)

    def test_unknown_label_fails_closed(self):
        evidence = synthetic_evidence()
        evidence["runs"][0]["records"][0]["prediction"] = "not-a-label"
        with self.assertRaisesRegex(BenchmarkInputError, "declared task labels"):
            evaluate_benchmark(evidence)

    def test_probabilities_must_cover_every_label(self):
        evidence = synthetic_evidence()
        evidence["runs"][0]["records"][0]["probabilities"] = {"routine": "1"}
        with self.assertRaisesRegex(BenchmarkInputError, "exactly every task label"):
            evaluate_benchmark(evidence)

    def test_probabilities_must_sum_exactly_to_one(self):
        evidence = synthetic_evidence()
        evidence["runs"][0]["records"][0]["probabilities"] = {
            "routine": "0.7",
            "escalate": "0.2",
        }
        with self.assertRaisesRegex(BenchmarkInputError, "sum exactly to 1"):
            evaluate_benchmark(evidence)

    def test_nonfinite_probability_is_rejected(self):
        evidence = synthetic_evidence()
        evidence["runs"][0]["records"][0]["probabilities"] = {
            "routine": "NaN",
            "escalate": "NaN",
        }
        with self.assertRaisesRegex(BenchmarkInputError, "finite"):
            evaluate_benchmark(evidence)

    def test_silent_mutation_governance_is_rejected(self):
        evidence = synthetic_evidence()
        evidence["governance"]["update_policy"] = "latest-wins"
        with self.assertRaisesRegex(BenchmarkInputError, "versioned_no_silent_mutation"):
            evaluate_benchmark(evidence)

    def test_actuarial_authority_cannot_be_self_assigned(self):
        evidence = synthetic_evidence()
        evidence["governance"]["task_authority"] = "tjlabs"
        with self.assertRaisesRegex(BenchmarkInputError, "qualified_actuarial_reviewer"):
            evaluate_benchmark(evidence)

    def test_license_contract_is_mpl2(self):
        evidence = synthetic_evidence()
        evidence["governance"]["benchmark_license"] = "MIT"
        with self.assertRaisesRegex(BenchmarkInputError, "MPL-2.0"):
            evaluate_benchmark(evidence)

    def test_schema_bool_is_not_integer_one(self):
        evidence = synthetic_evidence()
        evidence["schema_version"] = True
        # Python True == 1; explicitly prove schema version uses a real int.
        # Current implementation should fail this hostile case.
        with self.assertRaises(BenchmarkInputError):
            evaluate_benchmark(evidence)

    def test_binary_metric_values_are_objective_strings(self):
        result = evaluate_benchmark(synthetic_evidence())
        binary = next(r for r in result["runs"] if r["task_id"] == "claim-triage")
        self.assertRegex(binary["metrics"]["accuracy"], r"^\d\.\d{12}$")
        self.assertRegex(binary["metrics"]["macro_f1"], r"^\d\.\d{12}$")
        self.assertRegex(binary["metrics"]["brier_score"], r"^\d\.\d{12}$")
        self.assertRegex(binary["metrics"]["log_loss"], r"^\d\.\d{12}$")


if __name__ == "__main__":
    unittest.main()
