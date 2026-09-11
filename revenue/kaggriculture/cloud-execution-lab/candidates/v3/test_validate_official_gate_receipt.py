from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "validate_official_gate_receipt", HERE / "validate_official_gate_receipt.py"
)
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)

SHA = "a" * 64
OTHER_SHA = "b" * 64

BASE_CONFIG = {
    "consumer": "frozen",
    "frozen": True,
    "seed": True,
    "funding": True,
    "terminal_route": False,
    "committed": True,
    "budget_seconds": 1.0,
    "reserve_seconds": 0.01,
    "terminal_history": False,
    "redundant_hire": True,
    "fourth_quadrant": False,
    "market_pressure": True,
    "committed_seed_retry": False,
    "operating_stock": True,
    "idle_fertilizer": True,
    "crop_release": True,
    "early_capital": True,
    "e11_rival_sell": False,
    "rival_model": False,
    "e20_hire_guard": False,
    "l01_land": False,
    "l01_sheep": False,
    "l01_day0buy": False,
    "l01_tranche": False,
    "l01_leanplant": False,
    "r01_shop_router": False,
    "r02_route_bank": False,
    "r03_full_router": False,
    "r04_sale_window": True,
    "rival_dump_price_drop": 15.0,
    "rival_dump_lookback_steps": 8,
    "e11_min_future_absorption": 2,
    "e20_max_hires_per_day": 3,
    "e20_min_unwatered_crops": 3,
    "g01_early_expander_step": 144,
    "g01_land_cash_floor": 0,
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
}

V3_BOOL_KEYS = [
    "e11_rival_sell",
    "rival_model",
    "e20_hire_guard",
    "l01_land",
    "l01_sheep",
    "l01_day0buy",
    "l01_tranche",
    "l01_leanplant",
    "r01_shop_router",
    "r02_route_bank",
    "r03_full_router",
    "r04_sale_window",
]
V3_PARAM_KEYS = [
    "rival_dump_price_drop",
    "rival_dump_lookback_steps",
    "e11_min_future_absorption",
    "e20_max_hires_per_day",
    "e20_min_unwatered_crops",
    "g01_early_expander_step",
    "g01_land_cash_floor",
    "r04_sale_horizon",
    "r04_open_roundtrip",
    "r04_row_order",
    "r04_evening_flush",
    "r04_sale_fertilizer",
    "r04_cattle_early",
]


def manifest():
    keys = {key: {"default": False} for key in V3_BOOL_KEYS}
    keys["params"] = {key: BASE_CONFIG[key] for key in V3_PARAM_KEYS}
    return {
        "base": {"sha256": SHA},
        "keys": keys,
        "releases": [
            {
                "version": guard.LIVE_RELEASE_VERSION,
                "submission_archive": {"sha256": OTHER_SHA},
                "config": dict(BASE_CONFIG),
            }
        ],
    }


def panel():
    seeds = [101, 102]
    digest = hashlib.sha256("".join(f"{seed}\n" for seed in seeds).encode("ascii")).hexdigest()
    return {
        "seeds": seeds,
        "seats": [0, 1],
        "games_per_opponent": 4,
        "seed_list_sha256": digest,
        "seed_list_sha256_encoding": guard.SEED_LIST_ENCODING,
    }


def valid_receipt():
    base_config = dict(BASE_CONFIG)
    candidate_config = dict(base_config)
    candidate_config["e20_hire_guard"] = True
    rows = []
    scores = {
        (101, 0): ([10, 9], [12, 9]),
        (101, 1): ([10, 8], [9, 12]),
        (102, 0): ([7, 7], [8, 7]),
        (102, 1): ([4, 5], [3, 6]),
    }
    for (seed, seat), (baseline, candidate) in scores.items():
        b_own, b_rival = (baseline[0], baseline[1]) if seat == 0 else (baseline[1], baseline[0])
        c_own, c_rival = (candidate[0], candidate[1]) if seat == 0 else (candidate[1], candidate[0])
        rows.append(
            {
                "seed": seed,
                "candidate_seat": seat,
                "baseline_scores": baseline,
                "candidate_scores": candidate,
                "delta_m": (c_own - c_rival) - (b_own - b_rival),
            }
        )
    frozen = panel()
    return {
        "schema": guard.RECEIPT_SCHEMA,
        "mode": "official",
        "interpreter": {
            "commit": guard.OFFICIAL_INTERPRETER_COMMIT,
            "blob_sha256": "d" * 64,
            "verified_clean": True,
        },
        "baseline": {
            "submission_archive_sha256": OTHER_SHA,
            "config": base_config,
        },
        "candidate": {
            "builder": "build_v3.py",
            "built_from_pinned_archive": True,
            "base_archive_sha256": SHA,
            "package_sha256": "e" * 64,
            "config": candidate_config,
            "config_overrides": {"e20_hire_guard": True},
        },
        "panel": {
            "seeds": list(frozen["seeds"]),
            "seats": list(frozen["seats"]),
            "games_per_opponent": frozen["games_per_opponent"],
            "seed_list_sha256": frozen["seed_list_sha256"],
        },
        "opponent": {
            "name": "exact-opponent",
            "sha256": "f" * 64,
            "same_bytes_between_arms": True,
        },
        "per_cell_results": rows,
        "aggregate": {
            "mean_delta_m": sum(row["delta_m"] for row in rows) / len(rows),
        },
    }


def validate_synthetic(receipt=None, manifest_value=None, panel_value=None):
    return guard._validate_receipt_against_inputs(
        valid_receipt() if receipt is None else receipt,
        manifest() if manifest_value is None else manifest_value,
        panel() if panel_value is None else panel_value,
    )


class SimFidelityGuardTests(unittest.TestCase):
    def test_valid_synthetic_contract_never_mints_official_eligibility(self):
        result = validate_synthetic()
        self.assertTrue(result["input_contract_valid"])
        self.assertNotIn("official_gate_eligible", result)
        self.assertEqual(result["cells"], 4)

    def test_public_mapping_api_cannot_mint_official_eligibility(self):
        with self.assertRaisesRegex(guard.ReceiptError, "cannot mint official eligibility"):
            guard.validate_receipt(valid_receipt(), manifest(), panel())

    def test_authoritative_wrapper_uses_repo_inputs_and_current_repo_fails_closed(self):
        repo_manifest = json.loads((HERE / "V3-MANIFEST.json").read_text(encoding="utf-8"))
        latest = repo_manifest["releases"][-1]
        if latest.get("version") == guard.LIVE_RELEASE_VERSION:
            self.skipTest("repo now records an authoritative V3.1 release")
        with self.assertRaisesRegex(guard.ReceiptError, "authoritative V3.1"):
            guard.validate_authoritative_receipt(valid_receipt())

    def test_official_cli_rejects_custom_manifest_and_panel_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt_path = root / "receipt.json"
            manifest_path = root / "manifest.json"
            panel_path = root / "panel.json"
            receipt_path.write_text(json.dumps(valid_receipt()), encoding="utf-8")
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            panel_path.write_text(json.dumps(panel()), encoding="utf-8")
            rc = guard.main(
                [
                    str(receipt_path),
                    "--manifest",
                    str(manifest_path),
                    "--panel",
                    str(panel_path),
                ]
            )
        self.assertEqual(rc, 2)

    def test_incomplete_v31_release_config_fails_even_if_version_matches(self):
        broken_manifest = manifest()
        broken_manifest["releases"][-1]["config"].pop("r04_sale_fertilizer")
        broken_receipt = valid_receipt()
        broken_receipt["baseline"]["config"].pop("r04_sale_fertilizer")
        broken_receipt["candidate"]["config"].pop("r04_sale_fertilizer")
        with self.assertRaisesRegex(guard.ReceiptError, "not a complete live TITAN-CONFIG"):
            validate_synthetic(broken_receipt, broken_manifest)

    def test_new_manifest_lane_without_release_config_fails_dynamically(self):
        broken_manifest = manifest()
        broken_manifest["keys"]["future_lane"] = {"default": False}
        with self.assertRaisesRegex(guard.ReceiptError, "future_lane"):
            validate_synthetic(manifest_value=broken_manifest)

    def test_wrong_interpreter_commit_fails(self):
        receipt = valid_receipt()
        receipt["interpreter"]["commit"] = "deadbeef"
        with self.assertRaisesRegex(guard.ReceiptError, "interpreter.commit"):
            validate_synthetic(receipt)

    def test_interpreter_must_be_blob_verified_clean(self):
        receipt = valid_receipt()
        receipt["interpreter"]["verified_clean"] = False
        with self.assertRaisesRegex(guard.ReceiptError, "verified_clean"):
            validate_synthetic(receipt)

    def test_wrong_canonical_archive_fails(self):
        receipt = valid_receipt()
        receipt["candidate"]["base_archive_sha256"] = "9" * 64
        with self.assertRaisesRegex(guard.ReceiptError, "manifest.base.sha256"):
            validate_synthetic(receipt)

    def test_live_submission_config_mismatch_fails(self):
        receipt = valid_receipt()
        receipt["baseline"]["config"]["r04_sale_horizon"] = 99
        with self.assertRaisesRegex(guard.ReceiptError, "exactly equal"):
            validate_synthetic(receipt)

    def test_baseline_bool_int_type_confusion_fails(self):
        receipt = valid_receipt()
        receipt["baseline"]["config"]["r04_sale_window"] = 1
        with self.assertRaisesRegex(guard.ReceiptError, r"type\+value strictness"):
            validate_synthetic(receipt)
        receipt = valid_receipt()
        receipt["baseline"]["config"]["e20_hire_guard"] = 0
        with self.assertRaisesRegex(guard.ReceiptError, r"type\+value strictness"):
            validate_synthetic(receipt)

    def test_undeclared_candidate_config_drift_fails(self):
        receipt = valid_receipt()
        receipt["candidate"]["config"]["r04_sale_horizon"] = 7
        with self.assertRaisesRegex(guard.ReceiptError, "declared"):
            validate_synthetic(receipt)

    def test_candidate_override_bool_int_type_confusion_fails(self):
        receipt = valid_receipt()
        receipt["candidate"]["config_overrides"]["e20_hire_guard"] = 1
        receipt["candidate"]["config"]["e20_hire_guard"] = 1
        with self.assertRaisesRegex(guard.ReceiptError, "changes JSON type"):
            validate_synthetic(receipt)

    def test_seed_or_seat_substitution_fails(self):
        receipt = valid_receipt()
        receipt["panel"]["seeds"] = [101, 999]
        with self.assertRaisesRegex(guard.ReceiptError, "seeds"):
            validate_synthetic(receipt)

    def test_frozen_panel_metadata_must_be_self_consistent(self):
        broken = panel()
        broken["seeds"] = [101, 101]
        with self.assertRaisesRegex(guard.ReceiptError, "duplicates"):
            validate_synthetic(panel_value=broken)
        broken = panel()
        broken["games_per_opponent"] = 99
        with self.assertRaisesRegex(guard.ReceiptError, "seed x seat"):
            validate_synthetic(panel_value=broken)
        broken = panel()
        broken["seed_list_sha256"] = "c" * 64
        with self.assertRaisesRegex(guard.ReceiptError, "recomputed"):
            validate_synthetic(panel_value=broken)

    def test_opponent_bytes_must_match_between_arms(self):
        receipt = valid_receipt()
        receipt["opponent"]["same_bytes_between_arms"] = False
        with self.assertRaisesRegex(guard.ReceiptError, "same_bytes_between_arms"):
            validate_synthetic(receipt)

    def test_partial_panel_fails(self):
        receipt = valid_receipt()
        receipt["per_cell_results"].pop()
        with self.assertRaisesRegex(guard.ReceiptError, "partial frozen panel"):
            validate_synthetic(receipt)

    def test_seat_one_delta_is_recomputed_from_seat_ordered_scores(self):
        receipt = valid_receipt()
        seat_one = next(row for row in receipt["per_cell_results"] if row["candidate_seat"] == 1)
        seat_one["delta_m"] *= -1
        with self.assertRaisesRegex(guard.ReceiptError, "seat-aware recomputation"):
            validate_synthetic(receipt)

    def test_practice_receipt_must_be_explicitly_non_official(self):
        practice = {
            "schema": guard.RECEIPT_SCHEMA,
            "mode": "practice",
            "official_gate_pass": False,
            "practice_reason": "experiment file is outside build_v3.py package inputs",
        }
        result = guard.validate_receipt(practice, manifest(), panel())
        self.assertFalse(result["official_gate_eligible"])
        practice["official_gate_pass"] = True
        with self.assertRaisesRegex(guard.ReceiptError, "official_gate_pass=false"):
            guard.validate_receipt(practice, manifest(), panel())


if __name__ == "__main__":
    unittest.main()
