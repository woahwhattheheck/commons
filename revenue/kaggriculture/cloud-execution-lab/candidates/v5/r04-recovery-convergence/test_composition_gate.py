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


class FakeSourceReader:
    def __init__(self):
        self.commits: dict[str, dict[str, bytes]] = {}

    def add(self, head: str, path: str, raw: bytes) -> None:
        self.commits.setdefault(head, {})[path] = raw

    def commit_exists(self, head_sha: str) -> bool:
        return head_sha in self.commits

    def read_file(self, head_sha: str, path: str) -> bytes:
        try:
            return self.commits[head_sha][path]
        except KeyError as exc:
            raise mod.GateError(f"Git object path missing: {head_sha}:{path}") from exc


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def cells(delta_by_opponent: dict[str, float] | None = None) -> list[dict]:
    delta_by_opponent = delta_by_opponent or {}
    out = []
    for opponent in ("apex_v7", "arlene_v14"):
        delta = delta_by_opponent.get(opponent, 1.0)
        for seed in (101, 102, 103, 104):
            for seat in (0, 1):
                out.append({
                    "opponent": opponent,
                    "seed": seed,
                    "seat": seat,
                    "control_own": 100.0,
                    "control_rival": 50.0,
                    "candidate_own": 100.0 + delta,
                    "candidate_rival": 50.0,
                })
    return out


def write_report(
    root: Path,
    name: str,
    label: str,
    *,
    candidate_digit: str,
    delta_by_opponent: dict[str, float] | None = None,
    component_source_sha256: str | None = None,
) -> dict:
    report = {
        "schema": mod.ECONOMICS_REPORT_SCHEMA,
        "label": label,
        "control_id": "v5c:" + "0" * 64,
        "candidate_id": "v5c:" + candidate_digit * 64,
        "engine_id": "official-engine:3c202c7e",
        "harness_id": "current-v5-paired:v1",
        "opponent_pack_id": "apex-v7+arlene-v14",
        "cells": cells(delta_by_opponent),
    }
    if component_source_sha256 is not None:
        report["component_source_sha256"] = component_source_sha256
    raw = (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path = root / name
    path.write_bytes(raw)
    return {
        "status": mod.ECONOMICS_PASS,
        "report_path": name,
        "report_sha256": sha(raw),
    }


def base_manifest() -> dict:
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
        "current_runtime_stages": copy.deepcopy(mod.CURRENT_RUNTIME_STAGES),
        "components": [],
        "composition_economics": {"status": "PENDING"},
    }


def make_fixture(root: Path, *, pending_slot: str | None = None):
    reader = FakeSourceReader()
    manifest = base_manifest()
    digits = "123456789a"

    # First establish exact Git source custody with economics deliberately PENDING.
    for index, slot in enumerate(mod.REQUIRED_SLOTS):
        head = digits[index] * 40
        path = f"revenue/kaggriculture/cloud-execution-lab/candidates/v5/fake/{slot}/adapter.py"
        reader.add(head, path, f"# {slot}\nVALUE={index}\n".encode())
        manifest["components"].append({
            "slot": slot,
            "current_abi": True,
            "producer_ownership": (
                "single_parent_delegate" if slot == "fert_hand_boundary" else "none"
            ),
            "source_paths": [path],
            "carrier": {"pr": 14000 + index, "head_sha": head},
            "economics": {"status": "PENDING"},
        })

    normalized = {}
    for index, component in enumerate(manifest["components"]):
        slot, value = mod._validate_component(
            component,
            index,
            source_reader=reader,
            evidence_root=root,
        )
        normalized[slot] = value

    # PASS evidence is permitted only after it binds that exact component source.
    for index, component in enumerate(manifest["components"]):
        slot = component["slot"]
        if slot == pending_slot:
            continue
        component["economics"] = write_report(
            root,
            f"{slot}.json",
            slot,
            candidate_digit=digits[index],
            component_source_sha256=normalized[slot]["component_source_sha256"],
        )

    # Revalidate source+leaf economics and derive the whole-composition fingerprint.
    normalized = {}
    for index, component in enumerate(manifest["components"]):
        slot, value = mod._validate_component(
            component,
            index,
            source_reader=reader,
            evidence_root=root,
        )
        normalized[slot] = value
    component_source_sha256 = mod._canonical_sha256({
        "submitted_v31_source": mod.SUBMITTED_V31_SOURCE,
        "submitted_v31_archive_sha256": mod.SUBMITTED_V31_ARCHIVE_SHA256,
        "submitted_topology": mod.SUBMITTED_TOPOLOGY,
        "current_runtime_stages": mod.CURRENT_RUNTIME_STAGES,
        "components": mod._component_source_view(normalized),
    })
    manifest["composition_economics"] = write_report(
        root,
        "combined.json",
        "combined_composition",
        candidate_digit="b",
        component_source_sha256=component_source_sha256,
    )
    return manifest, reader


class CompositionGateV2Tests(unittest.TestCase):
    def test_complete_raw_evidence_is_ready_but_never_release_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            receipt = mod.evaluate_manifest(
                manifest, evidence_root=root, source_reader=reader
            )
            self.assertEqual(receipt["status"], "CURRENT_V5_COMPOSITION_READY_DEFAULT_OFF")
            self.assertEqual(receipt["component_count"], len(mod.REQUIRED_SLOTS))
            self.assertIn("v231_late_cow", receipt["component_heads"])
            self.assertFalse(receipt["default_flip_authority"])
            self.assertFalse(receipt["release_authority"])
            self.assertFalse(receipt["kaggle_submission_authority"])

    def test_old_forged_positive_summary_is_rejected_not_hashed_as_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            eco = manifest["components"][0]["economics"]
            eco.clear()
            eco.update({
                "status": mod.ECONOMICS_PASS,
                "report_sha256": "1" * 64,
                "panel_digest": "2" * 64,
                "control_id": "v5c:" + "0" * 64,
                "candidate_id": "v5c:" + "1" * 64,
                "opponents": ["apex_v7", "arlene_v14"],
                "seeds_per_opponent": 4,
                "both_seats": True,
                "paired_cells": 16,
                "mean_margin_delta": 999999.0,
                "per_opponent_margin_delta": {"apex_v7": 999999.0, "arlene_v14": 999999.0},
            })
            with self.assertRaisesRegex(mod.GateError, "keys mismatch"):
                mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)

    def test_nonexistent_carrier_head_is_hard_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            manifest["components"][0]["carrier"]["head_sha"] = "f" * 40
            with self.assertRaisesRegex(mod.GateError, "does not resolve to a Git commit"):
                mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)

    def test_missing_source_path_is_hard_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            manifest["components"][0]["source_paths"] = ["missing.py"]
            with self.assertRaisesRegex(mod.GateError, "Git object path missing"):
                mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)

    def test_report_byte_tamper_is_hard_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            first = manifest["components"][0]["economics"]
            (root / first["report_path"]).write_text('{"tampered":true}\n')
            with self.assertRaisesRegex(mod.GateError, "report SHA256 mismatch"):
                mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)

    def test_raw_negative_opponent_cells_block_even_if_other_opponent_gains(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            target = manifest["components"][0]
            old_report = json.loads(
                (root / target["economics"]["report_path"]).read_text()
            )
            target["economics"] = write_report(
                root,
                "negative.json",
                target["slot"],
                candidate_digit="1",
                delta_by_opponent={"apex_v7": 10.0, "arlene_v14": -1.0},
                component_source_sha256=old_report["component_source_sha256"],
            )
            receipt = mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)
            self.assertEqual(receipt["status"], "BLOCKED")
            self.assertIn(
                f"negative_opponent_margin:{target['slot']}:arlene_v14",
                receipt["blockers"],
            )

    def test_duplicate_raw_cell_is_hard_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            component = manifest["components"][0]
            path = root / component["economics"]["report_path"]
            report = json.loads(path.read_text())
            report["cells"].append(copy.deepcopy(report["cells"][0]))
            raw = (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode()
            path.write_bytes(raw)
            component["economics"]["report_sha256"] = sha(raw)
            with self.assertRaisesRegex(mod.GateError, "duplicate paired cell"):
                mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)

    def test_missing_v231_is_explicit_blocker(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            manifest["components"] = [
                component for component in manifest["components"]
                if component["slot"] != "v231_late_cow"
            ]
            manifest["composition_economics"] = {"status": "PENDING"}
            receipt = mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)
            self.assertEqual(receipt["status"], "BLOCKED")
            self.assertIn("missing_component:v231_late_cow", receipt["blockers"])

    def test_current_runtime_stage_contract_is_separate_and_exact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            self.assertEqual(mod.CURRENT_RUNTIME_STAGES["h3c_goose_rescue"], "pre_capacity")
            self.assertEqual(mod.CURRENT_RUNTIME_STAGES["b9_terminal_fertilizer"], "post_market")
            manifest["current_runtime_stages"]["h3c_goose_rescue"] = "post_market"
            with self.assertRaisesRegex(mod.GateError, "current_runtime_stages"):
                mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)

    def test_combined_report_must_bind_exact_authenticated_source_set(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            combined = manifest["composition_economics"]
            path = root / combined["report_path"]
            report = json.loads(path.read_text())
            report["component_source_sha256"] = "0" * 64
            raw = (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode()
            path.write_bytes(raw)
            combined["report_sha256"] = sha(raw)
            with self.assertRaisesRegex(mod.GateError, "does not match exact source set"):
                mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)

    def test_component_order_does_not_change_evidence_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            first = mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)
            shuffled = copy.deepcopy(manifest)
            shuffled["components"].reverse()
            second = mod.evaluate_manifest(shuffled, evidence_root=root, source_reader=reader)
            self.assertEqual(first["evidence_sha256"], second["evidence_sha256"])
            self.assertEqual(first["component_source_sha256"], second["component_source_sha256"])

    def test_forbidden_whole_router_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            manifest["components"][0]["source_paths"] = [
                "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/r04_full_router.py"
            ]
            with self.assertRaisesRegex(mod.GateError, "whole-router"):
                mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)

    def test_pending_leaf_is_valid_but_blocks_readiness(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root, pending_slot="row_order")
            receipt = mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)
            self.assertEqual(receipt["status"], "BLOCKED")
            self.assertIn("economics_not_pass:row_order", receipt["blockers"])

    def test_source_bytes_change_source_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            first = mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)
            component = manifest["components"][0]
            head = component["carrier"]["head_sha"]
            path = component["source_paths"][0]
            reader.add(head, path, b"# changed source bytes\n")
            with self.assertRaisesRegex(mod.GateError, "component_source_sha256 does not match"):
                mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)
            self.assertTrue(first["component_source_sha256"])

    def test_report_path_cannot_escape_evidence_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, reader = make_fixture(root)
            manifest["components"][0]["economics"]["report_path"] = "../outside.json"
            with self.assertRaisesRegex(mod.GateError, "relative path inside evidence root"):
                mod.evaluate_manifest(manifest, evidence_root=root, source_reader=reader)

    def test_strict_json_rejects_duplicate_keys_and_nonfinite(self):
        with self.assertRaisesRegex(mod.GateError, "duplicate JSON object key"):
            mod.load_manifest_bytes(b'{"schema":"a","schema":"b"}')
        with self.assertRaisesRegex(mod.GateError, "non-finite JSON"):
            mod.load_manifest_bytes(b'{"x":NaN}')


if __name__ == "__main__":
    unittest.main(verbosity=2)
