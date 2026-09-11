#!/usr/bin/env python3
"""Materialize an exact score-facing cattle ON/OFF package pair for evaluator A/B.

Both trees come from the current reviewed build_v3 package. The score-facing submission
transform is applied first so sale-window, horizon and sale-fertilizer are identical.
The control then changes only r04_cattle_early from false back to true. A receipt proves
that TITAN-CONFIG.json is the sole byte difference between the two materialized trees.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_v3  # noqa: E402
import make_submission  # noqa: E402

CONFIG = "TITAN-CONFIG.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_digest(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in sorted(files):
        blob = files[name]
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(str(len(blob)).encode("ascii") + b"\0")
        digest.update(blob)
    return digest.hexdigest()


def safe_write_tree(root: Path, files: dict[str, bytes]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, blob in files.items():
        pure = PurePosixPath(name)
        if pure.is_absolute() or not pure.parts or any(part in ("", ".", "..") for part in pure.parts):
            raise ValueError(f"unsafe package member: {name!r}")
        if not isinstance(blob, bytes):
            raise TypeError(f"package member {name!r} is not bytes")
        target = root.joinpath(*pure.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)


def strict_config(files: dict[str, bytes]) -> dict[str, object]:
    value = json.loads(files[CONFIG].decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("TITAN-CONFIG.json must decode to an object")
    return value


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--on-dir", type=Path, required=True)
    parser.add_argument("--off-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)

    base = build_v3.package_files()
    off_files, off_config = make_submission.apply_submission_config(base, 8)
    expected_off = {
        "r04_sale_window": True,
        "r04_sale_horizon": 8,
        "r04_sale_fertilizer": True,
        "r04_cattle_early": False,
    }
    for key, expected in expected_off.items():
        if type(off_config.get(key)) is not type(expected) or off_config.get(key) != expected:
            raise ValueError(f"OFF config mismatch for {key}: {off_config.get(key)!r}")

    on_files = dict(off_files)
    on_config = strict_config(on_files)
    if on_config.get("r04_cattle_early") is not False:
        raise ValueError("field-gated package must enter A/B with cattle OFF")
    on_config["r04_cattle_early"] = True
    on_files[CONFIG] = (json.dumps(on_config, indent=2) + "\n").encode("utf-8")

    if set(base) != set(off_files) or set(off_files) != set(on_files):
        raise ValueError("package member set changed during cattle A/B materialization")
    base_to_off = sorted(name for name in base if base[name] != off_files[name])
    if base_to_off != [CONFIG]:
        raise ValueError(f"submission transform changed unexpected members: {base_to_off!r}")
    on_to_off = sorted(name for name in on_files if on_files[name] != off_files[name])
    if on_to_off != [CONFIG]:
        raise ValueError(f"cattle A/B differs outside config: {on_to_off!r}")

    on_roundtrip = strict_config(on_files)
    off_roundtrip = strict_config(off_files)
    if on_roundtrip.get("r04_cattle_early") is not True or off_roundtrip.get("r04_cattle_early") is not False:
        raise ValueError("cattle A/B boolean split is not exact")
    for key in ("r04_sale_window", "r04_sale_horizon", "r04_sale_fertilizer"):
        if type(on_roundtrip.get(key)) is not type(off_roundtrip.get(key)) or on_roundtrip.get(key) != off_roundtrip.get(key):
            raise ValueError(f"non-cattle score-facing config drift: {key}")

    safe_write_tree(args.on_dir, on_files)
    safe_write_tree(args.off_dir, off_files)

    receipt = {
        "schema": "titan-v31-cattle-conditional-ab-materialization/v1",
        "member_count": len(on_files),
        "base_to_off_changed_members": base_to_off,
        "on_to_off_changed_members": on_to_off,
        "control_cattle_on_config": on_roundtrip,
        "candidate_cattle_off_config": off_roundtrip,
        "control_tree_sha256": tree_digest(on_files),
        "candidate_tree_sha256": tree_digest(off_files),
        "control_archive_sha256": sha256_bytes(build_v3.build_bytes(on_files)),
        "candidate_archive_sha256": sha256_bytes(build_v3.build_bytes(off_files)),
        "member_sha256": {
            "control": {name: sha256_bytes(on_files[name]) for name in sorted(on_files)},
            "candidate": {name: sha256_bytes(off_files[name]) for name in sorted(off_files)},
        },
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "member_count": receipt["member_count"],
        "control_tree_sha256": receipt["control_tree_sha256"],
        "candidate_tree_sha256": receipt["candidate_tree_sha256"],
        "only_difference": on_to_off,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
