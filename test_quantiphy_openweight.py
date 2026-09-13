from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from revenue.quantiphy_openweight.toolkit import (
    QuantiPhyError,
    apply_recipe,
    build_recipe,
    ensemble_prediction_sets,
    item_mra,
    score_prediction_rows,
    write_submission,
)


def row(i: int, category: str, truth: float, prediction: float) -> dict[str, object]:
    # Mirror organizer-style tokens such as video_type=S2SC/S3MC and inference_type=SS/DS.
    inference = category[0] + "S"
    video_type = "S" + category[1] + "SC"
    return {
        "id": i,
        "video_id": f"v{i // 2}",
        "question": f"q{i}",
        "inference_type": inference,
        "video_type": video_type,
        "ground_truth_posterior": truth,
        "parsed_value": prediction,
    }


class TestQuantiPhyOpenWeight(unittest.TestCase):
    def test_official_threshold_semantics(self) -> None:
        self.assertEqual(item_mra(100.0, 100.0), 1.0)
        self.assertEqual(item_mra(-100.0, 100.0), 1.0)  # organizer applies abs(parsed_value)
        self.assertAlmostEqual(item_mra(50.0, 100.0), 0.4)

    def test_macro_average_is_category_balanced(self) -> None:
        truth = [
            row(1, "S2", 100, 100), row(2, "S2", 100, 100), row(3, "S2", 100, 100),
            row(4, "D2", 100, 100), row(5, "S3", 100, 100), row(6, "D3", 100, 100),
        ]
        pred = [dict(item) for item in truth]
        # Make all three S2 rows completely wrong. Macro score is 3/4, not 3/6.
        for item in pred[:3]:
            item["parsed_value"] = 10000
        scored = score_prediction_rows(truth, pred)
        self.assertAlmostEqual(scored["mra_by_category"]["S2"], 0.0)
        self.assertAlmostEqual(scored["mra_average"], 0.75)

    def test_geometric_ensemble(self) -> None:
        a = [row(i, category, 100, 50) for i, category in enumerate(("S2", "D2", "S3", "D3"), 1)]
        b = [row(i, category, 100, 200) for i, category in enumerate(("S2", "D2", "S3", "D3"), 1)]
        combined = ensemble_prediction_sets([a, b], "geometric_mean")
        for item in combined:
            self.assertAlmostEqual(float(item["parsed_value"]), 100.0)

    def test_recipe_uses_held_out_selection(self) -> None:
        truth = []
        exact = []
        noisy = []
        i = 0
        for category in ("S2", "D2", "S3", "D3"):
            for j in range(10):
                i += 1
                target = 10.0 + j
                truth.append(row(i, category, target, target))
                exact.append(row(i, category, target, target))
                factor = 0.3 if j % 2 else 3.0
                noisy.append(row(i, category, target, target * factor))
        recipe = build_recipe(truth, [exact, noisy], prediction_names=["exact", "noisy"], fold_count=5)
        self.assertEqual(recipe["method"], "model:0")
        self.assertAlmostEqual(recipe["cv"]["selection_mra"], 1.0)

    def test_apply_recipe_requires_model_order(self) -> None:
        truth = []
        model = []
        i = 0
        for category in ("S2", "D2", "S3", "D3"):
            for j in range(5):
                i += 1
                truth.append(row(i, category, 100, 100))
                model.append(row(i, category, 100, 100))
        recipe = build_recipe(truth, [model], prediction_names=["m"], fold_count=5)
        with self.assertRaises(QuantiPhyError):
            apply_recipe(recipe, [model], prediction_names=["wrong"])

    def test_submission_drops_ground_truth_and_is_deterministic(self) -> None:
        rows = [row(i, category, 100, 100 + i) for i, category in enumerate(("S2", "D2", "S3", "D3"), 1)]
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a.csv"
            second = Path(tmp) / "b.csv"
            receipt_a = write_submission(rows, first)
            receipt_b = write_submission(list(reversed(rows)), second)
            self.assertEqual(receipt_a["sha256"], receipt_b["sha256"])
            text = first.read_text(encoding="utf-8")
            self.assertNotIn("ground_truth_posterior", text.splitlines()[0])

    def test_duplicate_key_rejected(self) -> None:
        duplicate = row(1, "S2", 1, 1)
        with self.assertRaises(QuantiPhyError):
            score_prediction_rows([duplicate] * 2, [duplicate] * 2, require_all_categories=False)


if __name__ == "__main__":
    unittest.main()
