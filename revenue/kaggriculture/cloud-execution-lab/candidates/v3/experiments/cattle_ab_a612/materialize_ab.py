#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize exact a612 cattle ON/OFF score-facing package pair.

The OFF arm is produced by the exact reviewed #12505 submission transform donor.
The ON control is derived from that OFF file mapping by changing exactly one config
boolean back to the canonical score-facing value: r04_cattle_early=True.
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
EXPECTED_A612_PACKAGE = "400ae640f3258b6a6ff19f9da99c66ef9c433e315febb1d72c75296cddeb277c"


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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--on-tree", type=Path, required=True)
    p.add_argument("--off-tree", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    args = p.parse_args()

    base = build_v3.package_files()
    base_digest = _package_digest(base)
    if base_digest != EXPECTED_A612_PACKAGE:
        raise SystemExit(f"wrong canonical package: {base_digest}")

    donor = _load_donor()
    off, off_cfg = donor.apply_submission_config(base, 8)
    if off_cfg["r04_sale_window"] is not True:
        raise AssertionError("OFF arm must be score-facing sale-window ON")
    if off_cfg["r04_sale_horizon"] != 8:
        raise AssertionError("OFF arm horizon must be 8")
    if off_cfg["r04_sale_fertilizer"] is not True:
        raise AssertionError("OFF arm sale-fertilizer must be ON")
    if off_cfg["r04_cattle_early"] is not False:
        raise AssertionError("OFF arm cattle must be OFF")
    if off_cfg["r04_strawberry_topup"] is not True:
        raise AssertionError("OFF arm must retain shipped H4")
    if off_cfg["r04_no_late_sale_advance"] is not True:
        raise AssertionError("OFF arm must retain shipped rival-gated L3")
    if off_cfg["r04_no_late_sale_advance_step"] != 648:
        raise AssertionError("OFF arm must retain L3 threshold 648")

    on_cfg = dict(off_cfg)
    on_cfg["r04_cattle_early"] = True
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

    receipt = {
        "schema": "titan-v31-a612-cattle-ab-materialization/v1",
        "canonical_commit": "a6120d0ea1bdb75eb0da2239220efce551f624a6",
        "canonical_package_sha256": base_digest,
        "submission_transform_donor_blob": DONOR_BLOB,
        "on_package_sha256": _package_digest(on),
        "off_package_sha256": _package_digest(off),
        "package_members": len(base),
        "base_to_off_changed_members": off_vs_base,
        "on_to_off_changed_members": on_vs_off,
        "on_to_off_changed_config_keys": differing_keys,
        "control_config": {key: on_cfg[key] for key in (
            "r04_sale_window", "r04_sale_horizon", "r04_sale_fertilizer", "r04_cattle_early",
            "r04_strawberry_topup", "r04_no_late_sale_advance", "r04_no_late_sale_advance_step",
        )},
        "candidate_config": {key: off_cfg[key] for key in (
            "r04_sale_window", "r04_sale_horizon", "r04_sale_fertilizer", "r04_cattle_early",
            "r04_strawberry_topup", "r04_no_late_sale_advance", "r04_no_late_sale_advance_step",
        )},
    }
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
