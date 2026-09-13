from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from revenue.steerability_challenge.experiment_matrix import experiment_matrix
from revenue.steerability_challenge.scorecard import (
    COMPETITION_MODELS,
    EvaluationPoint,
    ScorecardError,
    rank_recipes,
)
from revenue.steerability_challenge.submission_plan import PlanError, validate_plan


def _points(recipe: str, target: float, regression: float, *, noise: float = 0.0):
    rows = []
    for model_index, model in enumerate(COMPETITION_MODELS):
        for seed in (1, 2):
            n = noise * (model_index - 1) * (1 if seed == 1 else -1)
            rows.extend(
                [
                    EvaluationPoint(
                        recipe_id=recipe,
                        model=model,
                        seed=seed,
                        metric="honesty",
                        kind="target",
                        baseline=0.40,
                        candidate=0.40 + target + n,
                    ),
                    EvaluationPoint(
                        recipe_id=recipe,
                        model=model,
                        seed=seed,
                        metric="knowledge",
                        kind="side_effect",
                        baseline=0.80,
                        candidate=0.80 - regression,
                    ),
                    EvaluationPoint(
                        recipe_id=recipe,
                        model=model,
                        seed=seed,
                        metric="reasoning_error",
                        kind="side_effect",
                        baseline=0.10,
                        candidate=0.10,
                        higher_is_better=False,
                    ),
                ]
            )
    return rows


class ScorecardTests(unittest.TestCase):
    def test_rank_prefers_net_improvement_and_marks_pareto(self):
        points = _points("steady", 0.20, 0.02) + _points("harmful", 0.27, 0.18)
        result = rank_recipes(points)
        self.assertEqual(result["winner"], "steady")
        by_id = {row["recipe_id"]: row for row in result["recipes"]}
        self.assertAlmostEqual(by_id["steady"]["mean_composite_proxy"], 0.19, places=9)
        self.assertTrue(by_id["steady"]["pareto"])
        self.assertTrue(by_id["harmful"]["pareto"])  # more target gain, more regression tradeoff
        self.assertFalse(result["authoritative"])

    def test_capability_gains_are_not_rewarded(self):
        points = _points("gain", 0.10, -0.50)
        row = rank_recipes(points)["recipes"][0]
        self.assertAlmostEqual(row["mean_side_effect_regression"], 0.0)
        self.assertAlmostEqual(row["mean_composite_proxy"], 0.10)

    def test_higher_is_better_false_orients_delta(self):
        point = EvaluationPoint(
            recipe_id="x",
            model=COMPETITION_MODELS[0],
            seed=1,
            metric="error",
            kind="target",
            baseline=0.4,
            candidate=0.2,
            higher_is_better=False,
        )
        self.assertAlmostEqual(point.oriented_delta, 0.2)

    def test_requires_all_models_same_seeds_and_metrics(self):
        points = _points("x", 0.1, 0.01)
        with self.assertRaisesRegex(ScorecardError, "model coverage mismatch"):
            rank_recipes([p for p in points if p.model != COMPETITION_MODELS[-1]])
        with self.assertRaisesRegex(ScorecardError, "metric coverage differs"):
            rank_recipes(
                [
                    p
                    for p in points
                    if not (
                        p.model == COMPETITION_MODELS[-1]
                        and p.seed == 2
                        and p.metric == "knowledge"
                    )
                ]
            )

    def test_duplicate_evidence_rejected(self):
        points = _points("x", 0.1, 0.01)
        with self.assertRaisesRegex(ScorecardError, "duplicate evaluation point"):
            rank_recipes(points + [points[0]])

    def test_instability_penalty_can_break_equal_mean(self):
        stable = _points("stable", 0.20, 0.02, noise=0.0)
        noisy = _points("noisy", 0.20, 0.02, noise=0.09)
        result = rank_recipes(stable + noisy)
        self.assertEqual(result["winner"], "stable")


class PlanTests(unittest.TestCase):
    def _plan(self):
        zero = "0" * 64
        return {
            "schema_version": 1,
            "guide_version": "v0.2",
            "toolkit_commit": "f1d8b5fd6d9ed15d506f9445a93d55cb5c5b07df",
            "recipe": [
                {
                    "id": "instruction",
                    "method": "user_prefix",
                    "access": "prompt",
                    "params": {"text": "Answer truthfully."},
                },
                {
                    "id": "direction",
                    "method": "activation_adapter",
                    "access": "activations",
                    "params": {"vector": "$artifact:honesty_vector", "multiplier": 0.5},
                },
            ],
            "models": {
                model: {
                    "spipe_path": f"submission/{i}.spipe",
                    "artifacts": {
                        "honesty_vector": {
                            "path": f"artifacts/{i}.safetensors",
                            "sha256": zero,
                            "source": "participant-created contrastive fit",
                            "license": "participant-owned",
                        }
                    },
                }
                for i, model in enumerate(COMPETITION_MODELS)
            },
            "custom_controls": [],
        }

    def test_valid_plan_derives_white_box_and_signature(self):
        result = validate_plan(self._plan())
        self.assertTrue(result["ok"])
        self.assertEqual(result["derived_track"], "white-box")
        self.assertEqual(result["artifact_placeholders"], ["honesty_vector"])
        self.assertEqual(len(result["recipe_structure_sha256"]), 64)
        self.assertTrue(result["starter_kit_checker_still_required"])

    def test_model_specific_recipe_override_rejected(self):
        plan = self._plan()
        plan["models"][COMPETITION_MODELS[0]]["recipe"] = []
        with self.assertRaisesRegex(PlanError, "model-specific recipe overrides"):
            validate_plan(plan)

    def test_artifact_binding_must_match_every_model(self):
        plan = self._plan()
        plan["models"][COMPETITION_MODELS[1]]["artifacts"] = {}
        with self.assertRaisesRegex(PlanError, "artifact bindings mismatch"):
            validate_plan(plan)

    def test_track_escalates_to_open_on_weights(self):
        plan = self._plan()
        plan["recipe"].append(
            {"id": "adapter", "method": "load_lora", "access": "weights", "params": {}}
        )
        self.assertEqual(validate_plan(plan)["derived_track"], "open")

    def test_require_files_verifies_hashes(self):
        plan = self._plan()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, model in enumerate(COMPETITION_MODELS):
                spipe = root / f"submission/{i}.spipe"
                spipe.parent.mkdir(parents=True, exist_ok=True)
                spipe.write_bytes(b"placeholder")
                artifact = root / f"artifacts/{i}.safetensors"
                artifact.parent.mkdir(parents=True, exist_ok=True)
                payload = f"artifact-{i}".encode()
                artifact.write_bytes(payload)
                plan["models"][model]["artifacts"]["honesty_vector"]["sha256"] = hashlib.sha256(payload).hexdigest()
            result = validate_plan(plan, require_files=True, base_dir=root)
            self.assertTrue(result["ok"])
            (root / "artifacts/1.safetensors").write_bytes(b"tampered")
            with self.assertRaisesRegex(PlanError, "artifact hash mismatch"):
                validate_plan(plan, require_files=True, base_dir=root)


class MatrixTests(unittest.TestCase):
    def test_matrix_is_deterministic_and_source_bound(self):
        first = experiment_matrix()
        second = experiment_matrix()
        self.assertEqual(first, second)
        self.assertEqual(first["guide_version"], "v0.2")
        self.assertEqual(
            first["toolkit_commit"],
            "f1d8b5fd6d9ed15d506f9445a93d55cb5c5b07df",
        )
        self.assertEqual(set(first["competition_models"]), set(COMPETITION_MODELS))
        self.assertGreaterEqual(len(first["families"]), 5)
        tracks = {family["track"] for family in first["families"]}
        self.assertEqual(tracks, {"black-box", "white-box", "open"})


if __name__ == "__main__":
    unittest.main()
