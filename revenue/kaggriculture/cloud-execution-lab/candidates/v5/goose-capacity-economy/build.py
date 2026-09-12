# SPDX-License-Identifier: Apache-2.0
"""Materialize the P02 treatment from exact production-v3 bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ENTRY_SOURCE = HERE / "entry.py"
HELPER_SOURCE = HERE / "goose_capacity_economy.py"
EXPECTED_CONTROL_SHA256 = "20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239"


def package_digest(root: Path) -> str:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink not allowed: {path}")
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if "__pycache__" in rel.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append([rel.as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()])
    raw = json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(raw).hexdigest()


def _at_or_below(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def build_candidate(baseline_root: Path, out: Path):
    baseline_root = baseline_root.resolve()
    out = out.resolve()
    if not baseline_root.is_dir():
        raise ValueError("baseline root must be a directory")
    if out.exists():
        raise ValueError("output directory must be new")
    if _at_or_below(out, baseline_root):
        raise ValueError("output must be outside baseline root")
    if package_digest(baseline_root) != EXPECTED_CONTROL_SHA256:
        raise ValueError("production-v3 baseline digest drift")
    parent = baseline_root / "main.py"
    if not parent.is_file() or parent.is_symlink():
        raise ValueError("baseline main.py must be a regular file")
    if (baseline_root / "baseline_main.py").exists():
        raise ValueError("baseline already contains baseline_main.py")
    if (baseline_root / "goose_capacity_economy.py").exists():
        raise ValueError("baseline already contains P02 helper")

    control_before = package_digest(baseline_root)
    try:
        shutil.copytree(
            baseline_root,
            out,
            symlinks=False,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
        if package_digest(out) != control_before:
            raise ValueError("copied baseline drift")
        (out / "main.py").rename(out / "baseline_main.py")
        shutil.copyfile(ENTRY_SOURCE, out / "main.py")
        shutil.copyfile(HELPER_SOURCE, out / "goose_capacity_economy.py")
        candidate = package_digest(out)
    except Exception:
        if out.exists():
            shutil.rmtree(out)
        raise
    if package_digest(baseline_root) != control_before:
        shutil.rmtree(out)
        raise ValueError("baseline moved during materialization")
    return {
        "schema": "titan-v5-p02-goose-capacity-economy/v1",
        "control_package_sha256": control_before,
        "candidate_package_sha256": candidate,
        "treatment": "one-extra-goose-empty-coop",
        "default_activation": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    receipt = build_candidate(args.baseline_root, args.out)
    raw = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        receipt_path = args.receipt.resolve()
        if receipt_path.exists() or _at_or_below(receipt_path, args.baseline_root.resolve()) or _at_or_below(receipt_path, args.out.resolve()):
            raise ValueError("receipt must be new and outside package roots")
        receipt_path.write_text(raw)
    print(raw, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
