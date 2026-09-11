#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize exact 8e3 cattle ON/OFF score-facing package pair.

The OFF arm is produced by the exact reviewed #12505 submission transform donor.
The ON control is derived from that OFF file mapping by changing exactly one config
boolean back to the canonical score-facing value: r04_cattle_early=True.
Both arms must retain the shipped #12537 B5 CARROT + JIT factors.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
if str(V3) not in sys.path:
    sys.path.insert(0, str(V3))

import build_v3  # noqa: E402

DONOR = HERE / "make_submission_12505.py"
DONOR_BLOB = "9c5e46428f0a2357d7db6e46c4aa5f1f4748717d"
EXPECTED_8E3_PACKAGE = "4d920b2d8948488dc4f491a3a2b3d038c830d723baaaaba1e4470799b66f7d13"
CANONICAL_COMMIT = "8e3d92a286806f9f9525973ee7d359b629a11487"


def _load_donor():
    spec = importlib.util.spec_from_file_location("make_submission_12505", DONOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load #12505 donor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_tree(files, root: Path):
    for name, blob in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)


def _config(files):
    value = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
    if not isinstance(value, dict):
        raise AssertionError("TITAN-CONFIG.json must decode to object")
    return value


def _set_config(files, config):
    out = dict(files)
    out["TITAN-CONFIG.json"] = (json.dumps(config, indent=2) + "\n").encode("utf-8")
    return out


def _package_digest(files):
    return hashlib.sha256(build_v3.build_bytes(files)).hexdigest()


def _require_shipped_stack(config, label):
    required_true = (
        "r04_sale_fertilizer",
        "r04_strawberry_topup",
        "r04_no_late_sale_advance",
        "r04_b5_carrot_fertilizer",
        "r04_b5_jit_fertilize",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise AssertionError(f"{label} must retain shipped factor {key}=true")
    if config.get("r04_no_late_sale_advance_step") != 648 or type(config.get("r04_no_late_sale_advance_step")) is not int:
        raise AssertionError(f"{label} must retain literal gated-L3 threshold 648")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--on-tree", type=Path, required=True)
    p.add_argument("--off-tree", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    args = p.parse_args()

    base = build_v3.package_files()
    base_digest = _package_digest(base)
    if base_digest != EXPECTED_8E3_PACKAGE:
        raise SystemExit(f"wrong canonical package: {base_digest}")

    base_cfg = _config(base)
    _require_shipped_stack(base_cfg, "base")
    if base_cfg.get("r04_cattle_early") is not True:
        raise AssertionError("8e3 base must still ship cattle-early ON before A/B")

    donor = _load_donor()
    off, off_cfg = donor.apply_submission_config(base, 8)
    if off_cfg["r04_sale_window"] is not True:
        raise AssertionError("OFF arm must be score-facing sale-window ON")
    if off_cfg["r04_sale_horizon"] != 8 or type(off_cfg["r04_sale_horizon"]) is not int:
        raise AssertionError("OFF arm horizon must be literal int 8")
    if off_cfg["r04_cattle_early"] is not False:
        raise AssertionError("OFF arm cattle must be OFF")
    _require_shipped_stack(off_cfg, "OFF arm")

    on_cfg = dict(off_cfg)
    on_cfg["r04_cattle_early"] = True
    _require_shipped_stack(on_cfg, "ON arm")
    on = _set_config(off, on_cfg)

    if set(on) != set(off) or set(off) != set(base):
        raise AssertionError("package membership changed")
    off_vs_base = sorted(name for name in base if base[name] != off[name])
    if off_vs_base != ["TITAN-CONFIG.json"]:
        raise AssertionError(f"#12505 transform changed unexpected members: {off_vs_base}")
    on_vs_off = sorted(name for name in on if on[name] != off[name])
    if on_vs_off != ["TITAN-CONFIG.json"]:
        raise AssertionError(f"cattle A/B changed unexpected members: {on_vs_off}")

    differing_keys = sorted(key for key in set(on_cfg) | set(off_cfg) if on_cfg.get(key) != off_cfg.get(key))
    if differing_keys != ["r04_cattle_early"]:
        raise AssertionError(f"cattle A/B config drift: {differing_keys}")

    args.on_tree.mkdir(parents=True, exist_ok=True)
    args.off_tree.mkdir(parents=True, exist_ok=True)
    _write_tree(on, args.on_tree)
    _write_tree(off, args.off_tree)

    held_keys = (
        "r04_sale_window",
        "r04_sale_horizon",
        "r04_sale_fertilizer",
        "r04_cattle_early",
        "r04_strawberry_topup",
        "r04_no_late_sale_advance",
        "r04_no_late_sale_advance_step",
        "r04_b5_carrot_fertilizer",
        "r04_b5_jit_fertilize",
    )
    receipt = {
        "schema": "titan-v31-8e3-cattle-ab-materialization/v1",
        "canonical_commit": CANONICAL_COMMIT,
        "canonical_package_sha256": base_digest,
        "submission_transform_donor_blob": DONOR_BLOB,
        "on_package_sha256": _package_digest(on),
        "off_package_sha256": _package_digest(off),
        "package_members": len(base),
        "base_to_off_changed_members": off_vs_base,
        "on_to_off_changed_members": on_vs_off,
        "on_to_off_changed_config_keys": differing_keys,
        "control_config": {key: on_cfg[key] for key in held_keys},
        "candidate_config": {key: off_cfg[key] for key in held_keys},
    }
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
