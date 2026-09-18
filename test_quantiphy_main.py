from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.quantiphy_main.maintrack import (
    QuantiPhyMainError,
    _grouped_folds,
    build_recipe,
    build_submission_bundle,
    canonical_bytes,
    parse_quantity,
    strict_json_loads,
    validate_dataset,
    validate_receipts,
    verify_submission_bundle,
    write_bundle_exclusive,
)

ROOT = Path(__file__).resolve().parent


def make_fixture():
    rows = []
    receipts = []
    cats = [
        ("S", "x2", "S2", 10),
        ("D", "x2", "D2", 20),
        ("S", "x3", "S3", 30),
        ("D", "x3", "D3", 40),
    ]
    for vi in range(8):
        for ci, (inf, video_type, cat, base) in enumerate(cats):
            truth = base + vi + 1
            q = f"q-{cat}-{vi}"
            row = {
                "video_id": f"video-{vi}",
                "question": q,
                "inference_type": inf,
                "video_type": video_type,
                "ground_truth_posterior": str(truth),
                "expected_unit": "m",
            }
            rows.append(row)
            # Model A is consistently precise on S categories and noisy on D; B is the inverse.
            # The noise is deliberately non-multiplicative so category scaling cannot erase specialization.
            if cat.startswith("S"):
                pa = truth * (1.0 + (0.01 if vi % 2 == 0 else -0.01))
                pb = truth * (1.0 + (0.38 if vi % 3 == 0 else (-0.26 if vi % 3 == 1 else 0.17)))
            else:
                pa = truth * (1.0 + (0.36 if vi % 3 == 0 else (-0.24 if vi % 3 == 1 else 0.18)))
                pb = truth * (1.0 + (0.008 if vi % 2 == 0 else -0.008))
            for provider, model, pred, cost in [
                ("provider-a", "model-a", pa, 11),
                ("provider-b", "model-b", pb, 7),
            ]:
                rid = f"R-{provider[-1]}-{vi}-{ci}"
                receipts.append({
                    "schema": "quantiphy-main-receipt/v1",
                    "request_id": rid,
                    "provider": provider,
                    "model": model,
                    "video_id": f"video-{vi}",
                    "question": q,
                    "status": "OK",
                    "output_sha256": ("a" if model == "model-a" else "b") * 64,
                    "parsed_value": format(pred, ".8f"),
                    "unit": "m",
                    "prompt_tokens": 100,
                    "completion_tokens": 10,
                    "latency_ms": 25,
                    "cost_microusd": cost,
                    "evidence_sha256": ("c" if model == "model-a" else "d") * 64,
                })
    return rows, receipts


def make_inference_fixture(rows, receipts):
    test_rows = [{k: v for k, v in row.items() if k != "ground_truth_posterior"} for row in copy.deepcopy(rows)]
    return test_rows, copy.deepcopy(receipts)


class QuantityTests(unittest.TestCase):
    def test_parse_quantity(self):
        self.assertEqual(parse_quantity("12.50 m", expected_unit="m"), ("12.5", "m"))

    def test_parse_scientific(self):
        self.assertEqual(parse_quantity("1.2e3"), ("1200", None))

    def test_ambiguous_two_numbers(self):
        with self.assertRaisesRegex(QuantiPhyMainError, "exactly one"):
            parse_quantity("12 or 13 m")

    def test_leading_prose_refused(self):
        with self.assertRaisesRegex(QuantiPhyMainError, "leading prose"):
            parse_quantity("about 12 m")

    def test_trailing_prose_refused(self):
        with self.assertRaisesRegex(QuantiPhyMainError, "ambiguous trailing"):
            parse_quantity("12 m approx")

    def test_unit_mismatch(self):
        with self.assertRaisesRegex(QuantiPhyMainError, "unit mismatch"):
            parse_quantity("12 cm", expected_unit="m")


class StrictDomainTests(unittest.TestCase):
    def test_duplicate_json_key(self):
        with self.assertRaisesRegex(QuantiPhyMainError, "duplicate JSON key"):
            strict_json_loads('{"a":1,"a":2}')

    def test_nonfinite_json(self):
        with self.assertRaises(QuantiPhyMainError):
            strict_json_loads('{"a":NaN}')

    def test_dataset_duplicate_key(self):
        rows, _ = make_fixture(); rows.append(copy.deepcopy(rows[0]))
        with self.assertRaisesRegex(QuantiPhyMainError, "duplicate dataset key"):
            validate_dataset(rows, require_truth=True)

    def test_dataset_bad_category(self):
        rows, _ = make_fixture(); rows[0]["video_type"] = "x9"
        with self.assertRaisesRegex(QuantiPhyMainError, "unsupported category"):
            validate_dataset(rows, require_truth=True)

    def test_truth_float_refused(self):
        rows, _ = make_fixture(); rows[0]["ground_truth_posterior"] = 1.5
        with self.assertRaisesRegex(QuantiPhyMainError, "not float"):
            validate_dataset(rows, require_truth=True)

    def test_dataset_unknown_key(self):
        rows, _ = make_fixture(); rows[0]["hidden_label"] = "x"
        with self.assertRaisesRegex(QuantiPhyMainError, "unknown keys"):
            validate_dataset(rows, require_truth=True)


class ReceiptTests(unittest.TestCase):
    def test_receipts_validate(self):
        rows, receipts = make_fixture()
        out = validate_receipts(receipts, validate_dataset(rows, require_truth=True))
        self.assertEqual(len(out), 64)

    def test_bool_cost_refused(self):
        rows, receipts = make_fixture(); receipts[0]["cost_microusd"] = True
        with self.assertRaisesRegex(QuantiPhyMainError, "integer"):
            validate_receipts(receipts, validate_dataset(rows, require_truth=True))

    def test_float_cost_refused(self):
        rows, receipts = make_fixture(); receipts[0]["cost_microusd"] = 1.2
        with self.assertRaisesRegex(QuantiPhyMainError, "integer"):
            validate_receipts(receipts, validate_dataset(rows, require_truth=True))

    def test_unknown_item_refused(self):
        rows, receipts = make_fixture(); receipts[0]["question"] = "not-a-real-item"
        with self.assertRaisesRegex(QuantiPhyMainError, "unknown dataset item"):
            validate_receipts(receipts, validate_dataset(rows, require_truth=True))

    def test_changed_request_reuse_refused(self):
        rows, receipts = make_fixture(); changed = copy.deepcopy(receipts[0]); changed["cost_microusd"] += 1; receipts.append(changed)
        with self.assertRaisesRegex(QuantiPhyMainError, "changed request_id reuse"):
            validate_receipts(receipts, validate_dataset(rows, require_truth=True))

    def test_exact_request_replay_collapses(self):
        rows, receipts = make_fixture(); receipts.append(copy.deepcopy(receipts[0]))
        out = validate_receipts(receipts, validate_dataset(rows, require_truth=True))
        self.assertEqual(len(out), 64)

    def test_duplicate_model_item_different_request_refused(self):
        rows, receipts = make_fixture(); extra = copy.deepcopy(receipts[0]); extra["request_id"] = "R-EXTRA"; receipts.append(extra)
        with self.assertRaisesRegex(QuantiPhyMainError, "duplicate provider/model"):
            validate_receipts(receipts, validate_dataset(rows, require_truth=True))

    def test_ok_requires_parsed(self):
        rows, receipts = make_fixture(); receipts[0].pop("parsed_value")
        with self.assertRaisesRegex(QuantiPhyMainError, "requires parsed_value"):
            validate_receipts(receipts, validate_dataset(rows, require_truth=True))

    def test_non_ok_cannot_carry_parsed(self):
        rows, receipts = make_fixture(); receipts[0]["status"] = "REFUSAL"
        with self.assertRaisesRegex(QuantiPhyMainError, "non-OK"):
            validate_receipts(receipts, validate_dataset(rows, require_truth=True))

    def test_unit_mismatch_refused(self):
        rows, receipts = make_fixture(); receipts[0]["unit"] = "cm"
        with self.assertRaisesRegex(QuantiPhyMainError, "unit mismatch"):
            validate_receipts(receipts, validate_dataset(rows, require_truth=True))

    def test_provider_identifier_cannot_embed_address(self):
        rows, receipts = make_fixture(); receipts[0]["provider"] = "user@example.com"
        with self.assertRaisesRegex(QuantiPhyMainError, "invalid identifier"):
            validate_receipts(receipts, validate_dataset(rows, require_truth=True))

    def test_unknown_receipt_key(self):
        rows, receipts = make_fixture(); receipts[0]["api_key"] = "nope"
        with self.assertRaisesRegex(QuantiPhyMainError, "unknown keys"):
            validate_receipts(receipts, validate_dataset(rows, require_truth=True))


class FoldAndRecipeTests(unittest.TestCase):
    def test_grouped_folds_keep_video_together(self):
        rows, _ = make_fixture(); clean = validate_dataset(rows, require_truth=True)
        folds = _grouped_folds(clean, 4)
        for vi in range(8):
            assigned = {folds[(f"video-{vi}", f"q-{cat}-{vi}")] for cat in ("S2", "D2", "S3", "D3")}
            self.assertEqual(len(assigned), 1)

    def test_recipe_builds_candidates_and_router(self):
        rows, receipts = make_fixture()
        recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        names = {c["name"] for c in recipe["candidates"]}
        self.assertIn("router:category", names)
        self.assertIn("ensemble:median", names)
        self.assertIn("model:provider-a::model-a", names)
        self.assertIn("model:provider-b::model-b", names)

    def test_router_is_selected_on_specialist_fixture(self):
        rows, receipts = make_fixture()
        recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        self.assertEqual(recipe["selected"]["name"], "router:category")
        self.assertEqual(recipe["selected"]["route"]["S2"], "provider-a::model-a")
        self.assertEqual(recipe["selected"]["route"]["D2"], "provider-b::model-b")

    def test_budget_blocks_all(self):
        rows, receipts = make_fixture()
        with self.assertRaisesRegex(QuantiPhyMainError, "no complete candidate"):
            build_recipe(rows, receipts, budget_microusd=1, fold_count=4)

    def test_budget_can_exclude_expensive_model(self):
        rows, receipts = make_fixture()
        # Model B costs 32*7 = 224; model A costs 352. Router ~288. Budget 230 leaves only B.
        recipe = build_recipe(rows, receipts, budget_microusd=230, fold_count=4)
        self.assertEqual(recipe["selected"]["name"], "model:provider-b::model-b")
        self.assertLessEqual(recipe["selected"]["cost_microusd"], 230)

    def test_refusal_excludes_incomplete_model(self):
        rows, receipts = make_fixture()
        target = next(r for r in receipts if r["provider"] == "provider-a")
        target["status"] = "REFUSAL"; target.pop("parsed_value"); target.pop("unit")
        recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        names = {c["name"] for c in recipe["candidates"]}
        self.assertNotIn("model:provider-a::model-a", names)
        self.assertEqual(recipe["selected"]["name"], "model:provider-b::model-b")

    def test_order_invariance(self):
        rows, receipts = make_fixture()
        a = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        rows.reverse(); receipts.reverse()
        b = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        self.assertEqual(canonical_bytes(a), canonical_bytes(b))

    def test_observed_total_cost_exact(self):
        rows, receipts = make_fixture()
        recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        self.assertEqual(recipe["observed_total_cost_microusd"], 32 * (11 + 7))

    def test_authority_is_false(self):
        rows, receipts = make_fixture(); recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        self.assertFalse(recipe["authority"]["provider_call_performed"])
        self.assertFalse(recipe["authority"]["competition_submission_authorized"])
        self.assertFalse(recipe["authority"]["prize_or_revenue_claimed"])


class BundleTests(unittest.TestCase):
    def test_recipe_tamper_rejected_before_inference(self):
        rows, receipts = make_fixture(); recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        recipe["category_scales"]["S2"] = "9"
        test_rows, test_receipts = make_inference_fixture(rows, receipts)
        with self.assertRaisesRegex(QuantiPhyMainError, "recipe self-digest mismatch"):
            build_submission_bundle(test_rows, test_receipts, recipe)

    def test_inference_budget_rechecked(self):
        rows, receipts = make_fixture(); recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        # Preserve fit recipe integrity while making the test inference more expensive.
        test_rows, test_receipts = make_inference_fixture(rows, receipts)
        for receipt in test_receipts:
            receipt["cost_microusd"] = 1000
        with self.assertRaisesRegex(QuantiPhyMainError, "exceeds recipe budget"):
            build_submission_bundle(test_rows, test_receipts, recipe)

    def test_submission_strips_truth(self):
        rows, receipts = make_fixture(); recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        test_rows, test_receipts = make_inference_fixture(rows, receipts)
        submission, manifest = build_submission_bundle(test_rows, test_receipts, recipe)
        text = submission.decode()
        self.assertNotIn("ground_truth", text)
        self.assertIn("video_id,question,parsed_value", text.splitlines()[0])
        self.assertEqual(manifest["readiness"], "BLOCKED_EXTERNAL_GATES")

    def test_bundle_verifies(self):
        rows, receipts = make_fixture(); recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        test_rows, test_receipts = make_inference_fixture(rows, receipts)
        submission, manifest = build_submission_bundle(test_rows, test_receipts, recipe)
        self.assertTrue(verify_submission_bundle(test_rows, test_receipts, manifest, submission))

    def test_submission_tamper_rejected(self):
        rows, receipts = make_fixture(); recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        test_rows, test_receipts = make_inference_fixture(rows, receipts)
        submission, manifest = build_submission_bundle(test_rows, test_receipts, recipe)
        with self.assertRaisesRegex(QuantiPhyMainError, "does not exactly recompile"):
            verify_submission_bundle(test_rows, test_receipts, manifest, submission + b"x")

    def test_manifest_tamper_rejected(self):
        rows, receipts = make_fixture(); recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        test_rows, test_receipts = make_inference_fixture(rows, receipts)
        submission, manifest = build_submission_bundle(test_rows, test_receipts, recipe)
        manifest["readiness"] = "READY"
        with self.assertRaisesRegex(QuantiPhyMainError, "self-digest mismatch"):
            verify_submission_bundle(test_rows, test_receipts, manifest, submission)

    def test_receipt_drift_rejected(self):
        rows, receipts = make_fixture(); recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        test_rows, test_receipts = make_inference_fixture(rows, receipts)
        submission, manifest = build_submission_bundle(test_rows, test_receipts, recipe)
        test_receipts[0]["cost_microusd"] += 1
        with self.assertRaises(QuantiPhyMainError):
            verify_submission_bundle(test_rows, test_receipts, manifest, submission)

    def test_bundle_deterministic(self):
        rows, receipts = make_fixture(); recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        test_rows, test_receipts = make_inference_fixture(rows, receipts)
        a = build_submission_bundle(test_rows, test_receipts, recipe)
        b = build_submission_bundle(copy.deepcopy(test_rows), copy.deepcopy(test_receipts), copy.deepcopy(recipe))
        self.assertEqual(a[0], b[0]); self.assertEqual(canonical_bytes(a[1]), canonical_bytes(b[1]))

    def test_write_bundle_exclusive(self):
        rows, receipts = make_fixture(); recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "bundle"
            test_rows, test_receipts = make_inference_fixture(rows, receipts)
            write_bundle_exclusive(dest, test_rows, test_receipts, recipe)
            self.assertTrue((dest / "submission.csv").is_file())
            with self.assertRaisesRegex(QuantiPhyMainError, "already exists"):
                write_bundle_exclusive(dest, test_rows, test_receipts, recipe)


    def test_submission_input_with_truth_refused(self):
        rows, receipts = make_fixture(); recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        with self.assertRaisesRegex(QuantiPhyMainError, "must not contain ground truth"):
            build_submission_bundle(rows, receipts, recipe)

    def test_recipe_applies_to_distinct_unlabeled_item_ids(self):
        rows, receipts = make_fixture(); recipe = build_recipe(rows, receipts, budget_microusd=10000, fold_count=4)
        test_rows, test_receipts = make_inference_fixture(rows, receipts)
        for row in test_rows:
            row["video_id"] = "test-" + row["video_id"]
        for receipt in test_receipts:
            receipt["video_id"] = "test-" + receipt["video_id"]
            receipt["request_id"] = "T-" + receipt["request_id"]
        submission, manifest = build_submission_bundle(test_rows, test_receipts, recipe)
        self.assertIn(b"test-video-0", submission)
        self.assertTrue(verify_submission_bundle(test_rows, test_receipts, manifest, submission))

    def test_cli_roundtrip(self):
        rows, receipts = make_fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dataset = root / "dataset.json"; dataset.write_text(json.dumps(rows))
            rec = root / "receipts.json"; rec.write_text(json.dumps(receipts))
            test_rows, test_receipts = make_inference_fixture(rows, receipts)
            test_dataset = root / "test.json"; test_dataset.write_text(json.dumps(test_rows))
            test_rec = root / "test_receipts.json"; test_rec.write_text(json.dumps(test_receipts))
            recipe = root / "recipe.json"
            cp = subprocess.run([sys.executable, "-m", "revenue.quantiphy_main.cli", "fit", str(dataset), str(rec), "--budget-microusd", "10000", "--folds", "4", "--recipe-out", str(recipe)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            dest = root / "bundle"
            cp = subprocess.run([sys.executable, "-m", "revenue.quantiphy_main.cli", "package", str(test_dataset), str(test_rec), str(recipe), "--dest", str(dest)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            cp = subprocess.run([sys.executable, "-m", "revenue.quantiphy_main.cli", "verify", str(test_dataset), str(test_rec), str(dest / "manifest.json"), str(dest / "submission.csv")], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertIn("VERIFIED", cp.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
