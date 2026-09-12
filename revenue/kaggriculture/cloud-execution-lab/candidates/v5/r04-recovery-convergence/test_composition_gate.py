from __future__ import annotations

import copy
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


def passing_economics(index: int = 0) -> dict:
    opponents = ["apex_v7", "arlene_v14"]
    return {
        "status": mod.ECONOMICS_PASS,
        "report_sha256": f"{index + 9:x}"[-1] * 64,
        "panel_digest": f"{index + 10:x}"[-1] * 64,
        "control_id": "v5c:" + "a" * 64,
        "candidate_id": "v5c:" + f"{index + 1:x}"[-1] * 64,
        "opponents": opponents,
        "seeds_per_opponent": 4,
        "both_seats": True,
        "paired_cells": 16,
        "mean_margin_delta": 1.0,
        "per_opponent_margin_delta": {
            "apex_v7": 1.0,
            "arlene_v14": 1.0,
        },
    }


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
        "economics": passing_economics(index),
    }


def component_source_sha256(manifest: dict) -> str:
    components = {component["slot"]: component for component in manifest["components"]}
    source_view = [
        {
            "slot": slot,
            "current_abi": components[slot]["current_abi"],
            "producer_ownership": components[slot]["producer_ownership"],
            "source_paths": components[slot]["source_paths"],
            "carrier": components[slot]["carrier"],
        }
        for slot in mod.REQUIRED_SLOTS
        if slot in components
    ]
    return mod._canonical_sha256(
        {
            "submitted_v31_source": mod.SUBMITTED_V31_SOURCE,
            "submitted_v31_archive_sha256": mod.SUBMITTED_V31_ARCHIVE_SHA256,
            "submitted_topology": mod.SUBMITTED_TOPOLOGY,
            "components": source_view,
        }
    )


def valid_manifest() -> dict:
    manifest = {
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
    combined = passing_economics(9)
    combined["component_source_sha256"] = component_source_sha256(manifest)
    manifest["composition_economics"] = combined
    return manifest


class CompositionGateTests(unittest.TestCase):
    def test_complete_positive_manifest_is_composition_ready_but_not_release_authority(self):
        receipt = mod.evaluate_manifest(valid_manifest())
        self.assertEqual(receipt["status"], "CURRENT_V5_COMPOSITION_READY_DEFAULT_OFF")
        self.assertEqual(receipt["blockers"], [])
        self.assertEqual(receipt["component_count"], len(mod.REQUIRED_SLOTS))
        self.assertEqual(receipt["combined_candidate_id"], "v5c:" + "a" * 64)
        self.assertFalse(receipt["default_flip_authority"])
        self.assertFalse(receipt["release_authority"])
        self.assertFalse(receipt["kaggle_submission_authority"])

    def test_missing_component_blocks_without_inventing_authority(self):
        manifest = valid_manifest()
        manifest["components"] = manifest["components"][:-1]
        manifest["composition_economics"] = {"status": "PENDING"}
        receipt = mod.evaluate_manifest(manifest)
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertIn("missing_component:h3c_goose_rescue", receipt["blockers"])

    def test_row_order_and_row_shed_are_distinct_required_slots(self):
        manifest = valid_manifest()
        manifest["components"] = [
            component for component in manifest["components"] if component["slot"] != "row_order"
        ]
        manifest["composition_economics"] = {"status": "PENDING"}
        receipt = mod.evaluate_manifest(manifest)
        self.assertIn("missing_component:row_order", receipt["blockers"])
        self.assertNotIn("missing_component:row_shed", receipt["blockers"])
        self.assertEqual(
            mod.SUBMITTED_TOPOLOGY["inner_return_pipeline"][2:4],
            ["row_order", "row_shed"],
        )

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

    def test_combined_economics_is_required_even_when_all_leaves_pass(self):
        manifest = valid_manifest()
        manifest["composition_economics"] = {"status": "PENDING"}
        receipt = mod.evaluate_manifest(manifest)
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertIn("economics_not_pass:combined_composition", receipt["blockers"])
        self.assertIsNone(receipt["combined_candidate_id"])

    def test_combined_economics_must_bind_exact_component_source_set(self):
        manifest = valid_manifest()
        manifest["composition_economics"]["component_source_sha256"] = "0" * 64
        with self.assertRaisesRegex(mod.GateError, "exact component source set"):
            mod.evaluate_manifest(manifest)

    def test_component_source_fingerprint_changes_when_one_head_changes(self):
        first = valid_manifest()
        second = valid_manifest()
        before = component_source_sha256(first)
        second["components"][0]["carrier"]["head_sha"] = "f" * 40
        after = component_source_sha256(second)
        self.assertNotEqual(before, after)
        with self.assertRaisesRegex(mod.GateError, "exact component source set"):
            mod.evaluate_manifest(second)

    def test_negative_leaf_economics_blocks_even_when_global_is_positive(self):
        manifest = valid_manifest()
        row_shed = next(c for c in manifest["components"] if c["slot"] == "row_shed")
        row_shed["economics"]["mean_margin_delta"] = 10.0
        row_shed["economics"]["per_opponent_margin_delta"]["apex_v7"] = -1.0
        receipt = mod.evaluate_manifest(manifest)
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertIn("negative_opponent_margin:row_shed:apex_v7", receipt["blockers"])

    def test_negative_combined_opponent_margin_blocks_offsetting_global_gain(self):
        manifest = valid_manifest()
        manifest["composition_economics"]["mean_margin_delta"] = 50.0
        manifest["composition_economics"]["per_opponent_margin_delta"]["arlene_v14"] = -5.0
        receipt = mod.evaluate_manifest(manifest)
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertIn(
            "negative_opponent_margin:combined_composition:arlene_v14",
            receipt["blockers"],
        )

    def test_per_opponent_keys_must_exactly_match_panel_opponents(self):
        manifest = valid_manifest()
        manifest["components"][0]["economics"]["per_opponent_margin_delta"] = {
            "apex_v7": 1.0,
            "fake": 1.0,
        }
        with self.assertRaisesRegex(mod.GateError, "keys must exactly match opponents"):
            mod.evaluate_manifest(manifest)

    def test_paired_economics_depth_is_required(self):
        manifest = valid_manifest()
        eco = manifest["components"][0]["economics"]
        eco["opponents"] = ["apex_v7"]
        eco["per_opponent_margin_delta"] = {"apex_v7": 1.0}
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
        manifest["composition_economics"] = {"status": "PENDING"}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(mod.main([str(path)]), 3)


if __name__ == "__main__":
    unittest.main()
