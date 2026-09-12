from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("composition_gate", HERE / "composition_gate.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)


def h(ch: str, n: int) -> str:
    return ch * n


def valid_component(slot: str, index: int) -> dict:
    ownership = "single_parent_delegate" if slot == "fert_hand_boundary" else "none"
    return {
        "slot": slot,
        "current_abi": True,
        "producer_ownership": ownership,
        "source_paths": [f"revenue/kaggriculture/cloud-execution-lab/candidates/v5/{slot}/adapter.py"],
        "carrier": {
            "pr": 14000 + index,
            "head_sha": f"{index + 1:x}" * 40,
            "source_receipt_sha256": f"{index + 1:x}" * 64,
        },
        "economics": {
            "status": mod.ECONOMICS_PASS,
            "report_sha256": f"{index + 9:x}"[-1] * 64,
            "control_id": "v5c:" + "a" * 64,
            "candidate_id": "v5c:" + f"{index + 1:x}"[-1] * 64,
            "opponents": ["apex_v7", "arlene_v14"],
            "seeds_per_opponent": 4,
            "both_seats": True,
            "paired_cells": 16,
            "mean_margin_delta": 1.0,
        },
    }


def valid_manifest() -> dict:
    return {
        "schema": mod.SCHEMA,
        "target_version": "v5",
        "source_architecture": "current_v5",
        "submitted_v31_authority": {
            "source_commit": mod.SUBMITTED_V31_SOURCE,
            "archive_sha256": mod.SUBMITTED_V31_ARCHIVE_SHA256,
        },
        "v4_thaw": False,
        "legacy_whole_router_transplant": False,
        "production_default_flip": False,
        "release_requested": False,
        "kaggle_submission_requested": False,
        "submitted_topology": copy.deepcopy(mod.SUBMITTED_TOPOLOGY),
        "components": [
            valid_component(slot, i) for i, slot in enumerate(mod.REQUIRED_SLOTS)
        ],
    }


class CompositionGateTests(unittest.TestCase):
    def test_complete_positive_manifest_is_composition_ready_but_not_release_authority(self):
        receipt = mod.evaluate_manifest(valid_manifest())
        self.assertEqual(receipt["status"], "CURRENT_V5_COMPOSITION_READY_DEFAULT_OFF")
        self.assertEqual(receipt["blockers"], [])
        self.assertEqual(receipt["component_count"], len(mod.REQUIRED_SLOTS))
        self.assertFalse(receipt["default_flip_authority"])
        self.assertFalse(receipt["release_authority"])
        self.assertFalse(receipt["kaggle_submission_authority"])

    def test_missing_component_blocks_without_inventing_authority(self):
        manifest = valid_manifest()
        manifest["components"] = manifest["components"][:-1]
        receipt = mod.evaluate_manifest(manifest)
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertIn("missing_component:h3c_goose_rescue", receipt["blockers"])

    def test_duplicate_semantic_slot_is_hard_error(self):
        manifest = valid_manifest()
        manifest["components"].append(copy.deepcopy(manifest["components"][0]))
        with self.assertRaisesRegex(mod.GateError, "duplicate semantic slot"):
            mod.evaluate_manifest(manifest)

    def test_source_ready_component_may_wait_on_economics(self):
        manifest = valid_manifest()
        manifest["components"][0]["economics"] = {"status": "PENDING"}
        receipt = mod.evaluate_manifest(manifest)
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertIn("economics_not_pass:sale_window_h8_l3", receipt["blockers"])

    def test_pending_economics_cannot_smuggle_unbound_fields(self):
        manifest = valid_manifest()
        manifest["components"][0]["economics"] = {
            "status": "PENDING",
            "candidate_id": "v5c:" + "a" * 64,
        }
        with self.assertRaisesRegex(mod.GateError, "may contain only status"):
            mod.evaluate_manifest(manifest)

    def test_negative_economics_blocks_even_when_source_is_green(self):
        manifest = valid_manifest()
        manifest["components"][2]["economics"]["mean_margin_delta"] = -0.5
        receipt = mod.evaluate_manifest(manifest)
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertIn("negative_mean_margin:row_shed", receipt["blockers"])

    def test_paired_economics_depth_is_required(self):
        manifest = valid_manifest()
        eco = manifest["components"][0]["economics"]
        eco["opponents"] = ["apex_v7"]
        eco["seeds_per_opponent"] = 3
        eco["paired_cells"] = 12
        receipt = mod.evaluate_manifest(manifest)
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertIn("opponent_diversity:sale_window_h8_l3", receipt["blockers"])
        self.assertIn("seed_depth:sale_window_h8_l3", receipt["blockers"])
        self.assertIn("paired_cell_floor:sale_window_h8_l3", receipt["blockers"])

    def test_exact_bool_alias_is_rejected(self):
        manifest = valid_manifest()
        manifest["components"][0]["economics"]["both_seats"] = 1
        with self.assertRaisesRegex(mod.GateError, "exact JSON boolean"):
            mod.evaluate_manifest(manifest)

    def test_submitted_topology_is_exact_not_set_equivalent(self):
        manifest = valid_manifest()
        manifest["submitted_topology"]["outer_return_pipeline"].reverse()
        with self.assertRaisesRegex(mod.GateError, "submitted_topology"):
            mod.evaluate_manifest(manifest)

    def test_historical_off_feature_cannot_be_smuggled_in(self):
        manifest = valid_manifest()
        manifest["components"][0]["slot"] = "kill_late_water"
        with self.assertRaisesRegex(mod.GateError, "OFF/identity"):
            mod.evaluate_manifest(manifest)

    def test_whole_router_or_tape_transplant_is_rejected(self):
        for forbidden in (
            "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/r04_full_router.py",
            "revenue/kaggriculture/cloud-execution-lab/candidates/v3/r01_tapes.py",
        ):
            manifest = valid_manifest()
            manifest["components"][0]["source_paths"] = [forbidden]
            with self.subTest(forbidden=forbidden):
                with self.assertRaisesRegex(mod.GateError, "forbidden whole-router"):
                    mod.evaluate_manifest(manifest)

    def test_only_fert_hand_may_own_single_parent_delegate(self):
        manifest = valid_manifest()
        manifest["components"][0]["producer_ownership"] = "single_parent_delegate"
        with self.assertRaisesRegex(mod.GateError, "second producers are forbidden"):
            mod.evaluate_manifest(manifest)

        manifest = valid_manifest()
        fert = next(c for c in manifest["components"] if c["slot"] == "fert_hand_boundary")
        fert["producer_ownership"] = "none"
        with self.assertRaisesRegex(mod.GateError, "single_parent_delegate"):
            mod.evaluate_manifest(manifest)

    def test_v31_authority_is_exact_and_v4_thaw_is_forbidden(self):
        manifest = valid_manifest()
        manifest["submitted_v31_authority"]["source_commit"] = "0" * 40
        with self.assertRaisesRegex(mod.GateError, "source commit mismatch"):
            mod.evaluate_manifest(manifest)

        manifest = valid_manifest()
        manifest["v4_thaw"] = True
        with self.assertRaisesRegex(mod.GateError, "must remain false"):
            mod.evaluate_manifest(manifest)

    def test_duplicate_json_key_and_nonfinite_json_fail_closed(self):
        dup = b'{"schema":"a","schema":"b"}'
        with self.assertRaisesRegex(mod.GateError, "duplicate JSON object key"):
            mod.load_manifest_bytes(dup)
        with self.assertRaisesRegex(mod.GateError, "non-finite JSON"):
            mod.load_manifest_bytes(b'{"x":NaN}')

    def test_receipt_digest_is_deterministic_and_ignores_input_component_order(self):
        first = valid_manifest()
        second = valid_manifest()
        second["components"].reverse()
        r1 = mod.evaluate_manifest(first)
        r2 = mod.evaluate_manifest(second)
        self.assertEqual(r1["evidence_sha256"], r2["evidence_sha256"])
        self.assertEqual(r1["component_heads"], r2["component_heads"])

    def test_output_receipt_is_write_once(self):
        manifest = valid_manifest()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_path = root / "manifest.json"
            output_path = root / "receipt.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(mod.main([str(manifest_path), "--output", str(output_path)]), 0)
            with self.assertRaises(SystemExit) as exc:
                mod.main([str(manifest_path), "--output", str(output_path)])
            self.assertEqual(exc.exception.code, 2)

    def test_blocked_cli_returns_three(self):
        manifest = valid_manifest()
        manifest["components"][0]["economics"] = {"status": "PENDING"}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(mod.main([str(path)]), 3)


if __name__ == "__main__":
    unittest.main()
