import copy
import json
import unittest
from pathlib import Path

from benchmark import BenchmarkError, score, sha256_json, validate_benchmark, validate_predictions
from render_report import render

ROOT = Path(__file__).resolve().parent
BENCHMARK = json.loads((ROOT / "fixtures" / "synthetic_tasks.json").read_text(encoding="utf-8"))
PREDICTIONS = json.loads((ROOT / "fixtures" / "example_predictions.json").read_text(encoding="utf-8"))


class BenchmarkContractTests(unittest.TestCase):
    def test_fixture_is_publishable_synthetic_classification_only(self):
        validated = validate_benchmark(BENCHMARK)
        self.assertEqual(validated["license"], "CC0-1.0")
        self.assertFalse(validated["provenance"]["contains_real_claims"])
        self.assertTrue(all(task["task_type"] == "classification" for task in validated["tasks"]))

    def test_score_is_deterministic_and_bound_to_exact_benchmark(self):
        first = score(BENCHMARK, PREDICTIONS, model_id="fixture-model")
        second = score(copy.deepcopy(BENCHMARK), copy.deepcopy(PREDICTIONS), model_id="fixture-model")
        self.assertEqual(first, second)
        self.assertEqual(first["benchmark_sha256"], sha256_json(validate_benchmark(BENCHMARK)))
        self.assertEqual(first["metrics"]["accuracy"], 1.0)
        self.assertEqual(first["metrics"]["macro_f1"], 1.0)
        self.assertGreater(first["metrics"]["log_loss"], 0.0)
        self.assertGreater(first["metrics"]["brier"], 0.0)

    def test_gold_change_rotates_benchmark_digest(self):
        changed = copy.deepcopy(BENCHMARK)
        changed["tasks"][0]["gold_label"] = "SPECIAL_INVESTIGATION"
        original = score(BENCHMARK, PREDICTIONS, model_id="fixture-model")
        mutated = score(changed, PREDICTIONS, model_id="fixture-model")
        self.assertNotEqual(original["benchmark_sha256"], mutated["benchmark_sha256"])
        self.assertLess(mutated["metrics"]["accuracy"], 1.0)

    def test_missing_prediction_fails_closed(self):
        with self.assertRaisesRegex(BenchmarkError, "exactly one row per task"):
            validate_predictions(PREDICTIONS[:-1], validate_benchmark(BENCHMARK))

    def test_duplicate_task_fails_closed(self):
        changed = copy.deepcopy(BENCHMARK)
        changed["tasks"][1]["id"] = changed["tasks"][0]["id"]
        with self.assertRaisesRegex(BenchmarkError, "duplicate task id"):
            validate_benchmark(changed)

    def test_non_classification_task_is_rejected(self):
        changed = copy.deepcopy(BENCHMARK)
        changed["tasks"][0]["task_type"] = "generative"
        with self.assertRaisesRegex(BenchmarkError, "objective classification"):
            validate_benchmark(changed)

    def test_unpublishable_license_is_rejected(self):
        changed = copy.deepcopy(BENCHMARK)
        changed["license"] = "proprietary"
        with self.assertRaisesRegex(BenchmarkError, "CC0"):
            validate_benchmark(changed)

    def test_probability_contract_is_exact(self):
        changed = copy.deepcopy(PREDICTIONS)
        changed[0]["probabilities"]["EXPRESS_GLASS"] = 0.5
        with self.assertRaisesRegex(BenchmarkError, "sum to 1"):
            validate_predictions(changed, validate_benchmark(BENCHMARK))

    def test_report_requires_same_benchmark_digest(self):
        one = score(BENCHMARK, PREDICTIONS, model_id="model-a")
        two = copy.deepcopy(one)
        two["model_id"] = "model-b"
        two["benchmark_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "same benchmark"):
            render([one, two])

    def test_report_escapes_model_identifier(self):
        result = score(BENCHMARK, PREDICTIONS, model_id="<script>alert(1)</script>")
        output = render([result])
        self.assertNotIn("<script>", output)
        self.assertIn("&lt;script&gt;", output)
        self.assertIn(result["benchmark_sha256"], output)


if __name__ == "__main__":
    unittest.main()
