from __future__ import annotations

import copy
import hashlib
import json
import re
import unittest

from revenue.cas_actuarial_llm_benchmark.core import (
    BenchmarkInputError,
    evaluate_benchmark,
    verify_snapshot,
)
from revenue.cas_actuarial_llm_benchmark.fixture import synthetic_evidence


def _readdress(snapshot: dict) -> None:
    body = copy.deepcopy(snapshot)
    body.pop("snapshot_sha256", None)
    snapshot["snapshot_sha256"] = hashlib.sha256(
        json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


class CasActuarialBenchmarkTests(unittest.TestCase):
    def test_acceptance_fixture_is_ready_and_deterministic(self):
        evidence = synthetic_evidence()
        first = evaluate_benchmark(evidence)
        second = evaluate_benchmark(copy.deepcopy(evidence))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PROPOSAL_TECHNICAL_EVIDENCE_READY")
        self.assertTrue(first["signals"]["matrix_complete"])
        self.assertTrue(first["signals"]["shared_evaluation_universe_enforced"])
        self.assertTrue(first["signals"]["record_manifests_bound"])
        self.assertEqual(first["signals"]["task_count"], 2)
        self.assertEqual(first["signals"]["model_count"], 6)
        self.assertEqual(first["signals"]["run_count"], 12)
        self.assertEqual(first["signals"]["evaluation_item_count"], 24)
        self.assertTrue(verify_snapshot(first))

    def test_snapshot_binds_task_universe_and_run_record_manifests(self):
        result = evaluate_benchmark(synthetic_evidence())
        task_universes = {
            (task["task_id"], task["version"]): task["evaluation_universe"]
            for task in result["tasks"]
        }
        for universe in task_universes.values():
            self.assertEqual(universe["record_count"], 12)
            self.assertEqual(len(universe["records"]), 12)
            self.assertRegex(universe["sha256"], r"^[0-9a-f]{64}$")
        for run in result["runs"]:
            universe = task_universes[(run["task_id"], run["task_version"])]
            self.assertEqual(run["evaluation_universe_sha256"], universe["sha256"])
            self.assertEqual(run["record_count"], universe["record_count"])
            self.assertRegex(run["record_manifest_sha256"], r"^[0-9a-f]{64}$")

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

    def test_readdressed_tampered_task_universe_fails_structural_verification(self):
        result = evaluate_benchmark(synthetic_evidence())
        result["tasks"][0]["evaluation_universe"]["records"][0]["truth"] = "escalate"
        _readdress(result)
        self.assertFalse(verify_snapshot(result))

    def test_readdressed_run_universe_transplant_fails_structural_verification(self):
        result = evaluate_benchmark(synthetic_evidence())
        result["runs"][0]["evaluation_universe_sha256"] = "0" * 64
        _readdress(result)
        self.assertFalse(verify_snapshot(result))

    def test_readdressed_run_count_drift_fails_structural_verification(self):
        result = evaluate_benchmark(synthetic_evidence())
        result["runs"][0]["record_count"] = 11
        _readdress(result)
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

    def test_duplicate_run_item_id_fails_closed(self):
        evidence = synthetic_evidence()
        evidence["runs"][0]["records"][1]["item_id"] = evidence["runs"][0]["records"][0]["item_id"]
        with self.assertRaisesRegex(BenchmarkInputError, "run item_id values must be unique"):
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
        with self.assertRaises(BenchmarkInputError):
            evaluate_benchmark(evidence)

    def test_binary_metric_values_are_objective_strings(self):
        result = evaluate_benchmark(synthetic_evidence())
        binary = next(run for run in result["runs"] if run["task_id"] == "claim-triage")
        self.assertRegex(binary["metrics"]["accuracy"], r"^\d\.\d{12}$")
        self.assertRegex(binary["metrics"]["macro_f1"], r"^\d\.\d{12}$")
        self.assertRegex(binary["metrics"]["brier_score"], r"^\d\.\d{12}$")
        self.assertRegex(binary["metrics"]["log_loss"], r"^\d\.\d{12}$")

    def test_missing_evaluation_universe_fails_closed(self):
        evidence = synthetic_evidence()
        evidence["tasks"][0].pop("evaluation_universe")
        with self.assertRaisesRegex(BenchmarkInputError, "evaluation_universe"):
            evaluate_benchmark(evidence)

    def test_evaluation_universe_digest_tamper_fails_closed(self):
        evidence = synthetic_evidence()
        evidence["tasks"][0]["evaluation_universe"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(BenchmarkInputError, "universe digest"):
            evaluate_benchmark(evidence)

    def test_duplicate_evaluation_universe_item_fails_closed(self):
        evidence = synthetic_evidence()
        records = evidence["tasks"][0]["evaluation_universe"]["records"]
        records[1]["item_id"] = records[0]["item_id"]
        with self.assertRaisesRegex(BenchmarkInputError, "universe item_id values must be unique"):
            evaluate_benchmark(evidence)

    def test_evaluation_universe_truth_must_be_declared_label(self):
        evidence = synthetic_evidence()
        evidence["tasks"][0]["evaluation_universe"]["records"][0]["truth"] = "unknown"
        with self.assertRaisesRegex(BenchmarkInputError, "universe truth"):
            evaluate_benchmark(evidence)

    def test_run_cannot_drop_evaluation_item(self):
        evidence = synthetic_evidence()
        evidence["runs"][0]["records"].pop()
        with self.assertRaisesRegex(BenchmarkInputError, "missing evaluation universe"):
            evaluate_benchmark(evidence)

    def test_run_cannot_add_evaluation_item(self):
        evidence = synthetic_evidence()
        extra = copy.deepcopy(evidence["runs"][0]["records"][0])
        extra["item_id"] = "item-extra"
        evidence["runs"][0]["records"].append(extra)
        with self.assertRaisesRegex(BenchmarkInputError, "outside evaluation universe"):
            evaluate_benchmark(evidence)

    def test_run_cannot_substitute_evaluation_item(self):
        evidence = synthetic_evidence()
        evidence["runs"][0]["records"][0]["item_id"] = "item-substitute"
        with self.assertRaisesRegex(BenchmarkInputError, "missing evaluation universe"):
            evaluate_benchmark(evidence)

    def test_same_item_different_truth_across_models_fails_closed(self):
        evidence = synthetic_evidence()
        target_run = next(
            run
            for run in evidence["runs"]
            if run["task_id"] == "claim-triage" and run["model_id"] != "commercial-openai"
        )
        record = target_run["records"][0]
        record["truth"] = "escalate" if record["truth"] == "routine" else "routine"
        with self.assertRaisesRegex(BenchmarkInputError, "truth does not match evaluation universe"):
            evaluate_benchmark(evidence)

    def test_run_record_order_is_semantically_invariant(self):
        evidence = synthetic_evidence()
        first = evaluate_benchmark(evidence)
        permuted = copy.deepcopy(evidence)
        permuted["runs"][0]["records"].reverse()
        second = evaluate_benchmark(permuted)
        self.assertEqual(first, second)

    def test_task_universe_order_is_semantically_invariant(self):
        evidence = synthetic_evidence()
        first = evaluate_benchmark(evidence)
        permuted = copy.deepcopy(evidence)
        permuted["tasks"][0]["evaluation_universe"]["records"].reverse()
        second = evaluate_benchmark(permuted)
        self.assertEqual(first, second)

    def test_top_level_run_order_is_semantically_invariant(self):
        evidence = synthetic_evidence()
        first = evaluate_benchmark(evidence)
        permuted = copy.deepcopy(evidence)
        permuted["runs"].reverse()
        second = evaluate_benchmark(permuted)
        self.assertEqual(first, second)

    def test_prediction_change_changes_record_manifest(self):
        evidence = synthetic_evidence()
        first = evaluate_benchmark(evidence)
        changed = copy.deepcopy(evidence)
        record = changed["runs"][0]["records"][0]
        labels = changed["tasks"][0]["labels"]
        record["prediction"] = labels[(labels.index(record["prediction"]) + 1) % len(labels)]
        record["probabilities"] = {
            label: ("0.80" if label == record["prediction"] else "0.20")
            for label in labels
        }
        second = evaluate_benchmark(changed)
        first_run = next(run for run in first["runs"] if run["run_id"] == changed["runs"][0]["run_id"])
        second_run = next(run for run in second["runs"] if run["run_id"] == changed["runs"][0]["run_id"])
        self.assertNotEqual(
            first_run["record_manifest_sha256"],
            second_run["record_manifest_sha256"],
        )
        self.assertNotEqual(first["snapshot_sha256"], second["snapshot_sha256"])

    def test_equivalent_probability_spelling_has_one_manifest(self):
        evidence = synthetic_evidence()
        first = evaluate_benchmark(evidence)
        equivalent = copy.deepcopy(evidence)
        record = equivalent["runs"][0]["records"][0]
        record["probabilities"] = {
            label: str(float(value)) for label, value in record["probabilities"].items()
        }
        second = evaluate_benchmark(equivalent)
        self.assertEqual(first, second)

    def test_every_run_for_task_uses_identical_universe_digest_and_count(self):
        result = evaluate_benchmark(synthetic_evidence())
        for task in result["tasks"]:
            matching = [
                run
                for run in result["runs"]
                if (run["task_id"], run["task_version"])
                == (task["task_id"], task["version"])
            ]
            self.assertEqual(len(matching), 6)
            self.assertEqual(
                {run["evaluation_universe_sha256"] for run in matching},
                {task["evaluation_universe"]["sha256"]},
            )
            self.assertEqual(
                {run["record_count"] for run in matching},
                {task["evaluation_universe"]["record_count"]},
            )


if __name__ == "__main__":
    unittest.main()
