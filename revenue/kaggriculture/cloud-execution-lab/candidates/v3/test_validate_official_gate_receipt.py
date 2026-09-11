from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
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
    "r04_sale_window": True,
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "lane_x": False,
}


def manifest():
    return {
        "base": {"sha256": SHA},
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
    candidate_config["lane_x"] = True
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
            "config_overrides": {"lane_x": True},
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


class SimFidelityGuardTests(unittest.TestCase):
    def test_valid_official_receipt_passes_with_authoritative_v31_release(self):
        result = guard.validate_receipt(valid_receipt(), manifest(), panel())
        self.assertTrue(result["official_gate_eligible"])
        self.assertEqual(result["cells"], 4)

    def test_current_repo_manifest_cannot_false_green_without_v31_release(self):
        repo_manifest = json.loads((HERE / "V3-MANIFEST.json").read_text(encoding="utf-8"))
        latest = repo_manifest["releases"][-1]
        if latest.get("version") == guard.LIVE_RELEASE_VERSION:
            self.skipTest("repo now records an authoritative V3.1 release")
        with self.assertRaisesRegex(guard.ReceiptError, "authoritative V3.1"):
            guard.validate_receipt(valid_receipt(), repo_manifest, panel())

    def test_wrong_interpreter_commit_fails(self):
        receipt = valid_receipt()
        receipt["interpreter"]["commit"] = "deadbeef"
        with self.assertRaisesRegex(guard.ReceiptError, "interpreter.commit"):
            guard.validate_receipt(receipt, manifest(), panel())

    def test_interpreter_must_be_blob_verified_clean(self):
        receipt = valid_receipt()
        receipt["interpreter"]["verified_clean"] = False
        with self.assertRaisesRegex(guard.ReceiptError, "verified_clean"):
            guard.validate_receipt(receipt, manifest(), panel())

    def test_wrong_canonical_archive_fails(self):
        receipt = valid_receipt()
        receipt["candidate"]["base_archive_sha256"] = "9" * 64
        with self.assertRaisesRegex(guard.ReceiptError, "manifest.base.sha256"):
            guard.validate_receipt(receipt, manifest(), panel())

    def test_live_submission_config_mismatch_fails(self):
        receipt = valid_receipt()
        receipt["baseline"]["config"]["r04_sale_horizon"] = 99
        with self.assertRaisesRegex(guard.ReceiptError, "exactly equal"):
            guard.validate_receipt(receipt, manifest(), panel())

    def test_baseline_bool_int_type_confusion_fails(self):
        receipt = valid_receipt()
        receipt["baseline"]["config"]["r04_sale_window"] = 1
        with self.assertRaisesRegex(guard.ReceiptError, "type\+value strictness"):
            guard.validate_receipt(receipt, manifest(), panel())
        receipt = valid_receipt()
        receipt["baseline"]["config"]["lane_x"] = 0
        with self.assertRaisesRegex(guard.ReceiptError, "type\+value strictness"):
            guard.validate_receipt(receipt, manifest(), panel())

    def test_undeclared_candidate_config_drift_fails(self):
        receipt = valid_receipt()
        receipt["candidate"]["config"]["r04_sale_horizon"] = 7
        with self.assertRaisesRegex(guard.ReceiptError, "declared"):
            guard.validate_receipt(receipt, manifest(), panel())

    def test_candidate_override_bool_int_type_confusion_fails(self):
        receipt = valid_receipt()
        receipt["candidate"]["config_overrides"]["lane_x"] = 1
        receipt["candidate"]["config"]["lane_x"] = 1
        with self.assertRaisesRegex(guard.ReceiptError, "changes JSON type"):
            guard.validate_receipt(receipt, manifest(), panel())

    def test_seed_or_seat_substitution_fails(self):
        receipt = valid_receipt()
        receipt["panel"]["seeds"] = [101, 999]
        with self.assertRaisesRegex(guard.ReceiptError, "seeds"):
            guard.validate_receipt(receipt, manifest(), panel())

    def test_frozen_panel_metadata_must_be_self_consistent(self):
        broken = panel()
        broken["seeds"] = [101, 101]
        with self.assertRaisesRegex(guard.ReceiptError, "duplicates"):
            guard.validate_receipt(valid_receipt(), manifest(), broken)
        broken = panel()
        broken["games_per_opponent"] = 99
        with self.assertRaisesRegex(guard.ReceiptError, "seed x seat"):
            guard.validate_receipt(valid_receipt(), manifest(), broken)
        broken = panel()
        broken["seed_list_sha256"] = "c" * 64
        with self.assertRaisesRegex(guard.ReceiptError, "recomputed"):
            guard.validate_receipt(valid_receipt(), manifest(), broken)

    def test_opponent_bytes_must_match_between_arms(self):
        receipt = valid_receipt()
        receipt["opponent"]["same_bytes_between_arms"] = False
        with self.assertRaisesRegex(guard.ReceiptError, "same_bytes_between_arms"):
            guard.validate_receipt(receipt, manifest(), panel())

    def test_partial_panel_fails(self):
        receipt = valid_receipt()
        receipt["per_cell_results"].pop()
        with self.assertRaisesRegex(guard.ReceiptError, "partial frozen panel"):
            guard.validate_receipt(receipt, manifest(), panel())

    def test_seat_one_delta_is_recomputed_from_seat_ordered_scores(self):
        receipt = valid_receipt()
        seat_one = next(row for row in receipt["per_cell_results"] if row["candidate_seat"] == 1)
        seat_one["delta_m"] *= -1
        with self.assertRaisesRegex(guard.ReceiptError, "seat-aware recomputation"):
            guard.validate_receipt(receipt, manifest(), panel())

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
