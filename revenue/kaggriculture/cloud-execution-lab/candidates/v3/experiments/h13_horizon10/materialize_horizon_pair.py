# SPDX-License-Identifier: Apache-2.0
"""Materialize an exact V3.1 H8/H10 R04 comparison pair.

This is experiment/custody tooling only.  It adds no runtime policy and does not
change V3 defaults or package inputs.  Both arms are built from the same
``build_v3.package_files()`` result.  The H8 control enables the shipped R04
submission mode; the H10 candidate differs from H8 only in
``r04_sale_horizon: 8 -> 10``.

The caller must provide the exact frozen canonical archive.  We verify its SHA
before entering the current ``build_v3`` helper so this tool remains fail-closed
even if Python assertions are disabled.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

V3 = Path(__file__).resolve().parents[2]
if str(V3) not in sys.path:
    sys.path.insert(0, str(V3))

import build_v3  # noqa: E402

EXPECTED_CANONICAL_SHA256 = "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
CONFIG_NAME = "TITAN-CONFIG.json"
CONTROL_NAME = "titan-v3.1-h8-control.tar.gz"
CANDIDATE_NAME = "titan-v3.1-h10-candidate.tar.gz"
RECEIPT_NAME = "H13-HORIZON10-CARRIER-RECEIPT.json"

# Exact live V3.1 R04 tuple at the experiment's source boundary.  JSON scalar
# type is part of the contract: True must never satisfy integer 1, or vice versa.
BASELINE_R04 = {
    "r04_sale_window": False,
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
}


class CarrierError(RuntimeError):
    """Fail-closed custody/config error."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CarrierError(message)


def _json_equal(left: Any, right: Any) -> bool:
    return type(left) is type(right) and left == right


def validate_base_config(config: Mapping[str, Any]) -> None:
    _require(isinstance(config, Mapping), "TITAN-CONFIG.json must contain an object")
    for key, expected in BASELINE_R04.items():
        _require(key in config, f"missing live V3.1 config key: {key}")
        actual = config[key]
        _require(
            _json_equal(actual, expected),
            f"live V3.1 config drift: {key}={actual!r} ({type(actual).__name__}), "
            f"expected {expected!r} ({type(expected).__name__})",
        )


def config_delta(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    _require(set(left) == set(right), "config key set drift between arms")
    out: dict[str, dict[str, Any]] = {}
    for key in sorted(left):
        if not _json_equal(left[key], right[key]):
            out[key] = {"left": left[key], "right": right[key]}
    return out


def build_arm_configs(base_config: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return exact H8 control and H10 candidate config dictionaries."""
    validate_base_config(base_config)
    base = copy.deepcopy(dict(base_config))
    h8 = copy.deepcopy(base)
    h10 = copy.deepcopy(base)

    h8["r04_sale_window"] = True
    h10["r04_sale_window"] = True
    h10["r04_sale_horizon"] = 10

    _require(
        config_delta(base, h8)
        == {"r04_sale_window": {"left": False, "right": True}},
        "H8 control changed something other than submission-mode R04 enablement",
    )
    _require(
        config_delta(h8, h10)
        == {"r04_sale_horizon": {"left": 8, "right": 10}},
        "H10 candidate must differ from H8 only by sale horizon 8 -> 10",
    )
    _require(
        config_delta(base, h10)
        == {
            "r04_sale_horizon": {"left": 8, "right": 10},
            "r04_sale_window": {"left": False, "right": True},
        },
        "source-to-H10 delta is not exactly R04 enablement plus horizon 10",
    )
    return h8, h10


def _config_bytes(config: Mapping[str, Any]) -> bytes:
    return (json.dumps(dict(config), indent=2) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_set_digest(files: Mapping[str, bytes], *, exclude_config: bool = False) -> str:
    rows = []
    for name in sorted(files):
        if exclude_config and name == CONFIG_NAME:
            continue
        rows.append([name, _sha256(files[name])])
    payload = json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return _sha256(payload)


def materialize(canonical: Path, out_dir: Path) -> dict[str, Any]:
    _require(canonical.is_file() and not canonical.is_symlink(), "canonical must be a regular non-symlink file")
    canonical_bytes = canonical.read_bytes()
    canonical_sha = _sha256(canonical_bytes)
    _require(
        canonical_sha == EXPECTED_CANONICAL_SHA256,
        f"canonical SHA mismatch: got {canonical_sha}, expected {EXPECTED_CANONICAL_SHA256}",
    )

    manifest = build_v3.manifest()
    _require(isinstance(manifest, dict), "V3 manifest must be an object")
    pinned = (manifest.get("base") or {}).get("sha256") if isinstance(manifest.get("base"), dict) else None
    _require(
        isinstance(pinned, str) and pinned == EXPECTED_CANONICAL_SHA256,
        "current V3 manifest no longer pins the frozen H13 canonical",
    )

    files = build_v3.package_files(canonical)
    _require(CONFIG_NAME in files, "built V3 package has no TITAN-CONFIG.json")
    try:
        source_config = json.loads(files[CONFIG_NAME].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CarrierError("built TITAN-CONFIG.json is not valid UTF-8 JSON") from exc

    h8_config, h10_config = build_arm_configs(source_config)
    source_files = dict(files)
    h8_files = dict(files)
    h10_files = dict(files)
    h8_files[CONFIG_NAME] = _config_bytes(h8_config)
    h10_files[CONFIG_NAME] = _config_bytes(h10_config)

    _require(set(source_files) == set(h8_files) == set(h10_files), "package file set drift between arms")
    non_config_digest = _file_set_digest(source_files, exclude_config=True)
    _require(_file_set_digest(h8_files, exclude_config=True) == non_config_digest, "H8 changed non-config package bytes")
    _require(_file_set_digest(h10_files, exclude_config=True) == non_config_digest, "H10 changed non-config package bytes")

    source_blob = build_v3.build_bytes(source_files)
    h8_blob = build_v3.build_bytes(h8_files)
    h10_blob = build_v3.build_bytes(h10_files)

    _require(not out_dir.exists(), f"output directory already exists: {out_dir}")
    out_dir.mkdir(parents=True)
    (out_dir / CONTROL_NAME).write_bytes(h8_blob)
    (out_dir / CANDIDATE_NAME).write_bytes(h10_blob)

    receipt = {
        "schema": "titan.v31.h13-horizon10-pair.v1",
        "truth_boundary": "experiment/custody pair only; not an official promotion or leaderboard receipt",
        "canonical_sha256": canonical_sha,
        "source_package": {
            "sha256": _sha256(source_blob),
            "bytes": len(source_blob),
            "files": len(source_files),
            "file_set_sha256": _file_set_digest(source_files),
            "non_config_file_set_sha256": non_config_digest,
        },
        "control_h8": {
            "archive": CONTROL_NAME,
            "sha256": _sha256(h8_blob),
            "bytes": len(h8_blob),
            "files": len(h8_files),
            "config": {key: h8_config[key] for key in BASELINE_R04},
        },
        "candidate_h10": {
            "archive": CANDIDATE_NAME,
            "sha256": _sha256(h10_blob),
            "bytes": len(h10_blob),
            "files": len(h10_files),
            "config": {key: h10_config[key] for key in BASELINE_R04},
        },
        "arm_config_delta": config_delta(h8_config, h10_config),
        "source_to_control_delta": config_delta(source_config, h8_config),
        "build_v3_sha256": _sha256((V3 / "build_v3.py").read_bytes()),
        "make_submission_sha256": _sha256((V3 / "make_submission.py").read_bytes()),
    }
    _require(
        receipt["arm_config_delta"]
        == {"r04_sale_horizon": {"left": 8, "right": 10}},
        "receipt arm delta drift",
    )
    (out_dir / RECEIPT_NAME).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = materialize(args.canonical, args.out_dir)
    print(
        "H13 HORIZON10 PAIR",
        receipt["control_h8"]["sha256"],
        receipt["candidate_h10"]["sha256"],
        receipt["arm_config_delta"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
