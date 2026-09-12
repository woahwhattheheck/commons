# SPDX-License-Identifier: Apache-2.0
"""Materialize selective-carrot arms from an exact current V5 package."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
LAB_ROOT = HERE.parents[2]
SELECTIVE_SOURCE = HERE / "selective_carrot.py"
ENTRY_SOURCE = HERE / "current_entry.py"

# These are source identities, not a commit pin. The builder may remain valid
# across main commits that leave these exact implementation bytes unchanged.
EXPECTED_PARENT_MAIN_BLOB = "9cf8feaa9a755ffdf85d8878baa07b1fc7940192"
EXPECTED_SELECTIVE_BLOB = "6af9a832dec058b7824fd7dd080f00ee50bb1d2f"
EXPECTED_ENTRY_BLOB = "02c50e8eb6eecb5c06d610d421e0ff3bf007fb0e"


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def package_digest(root: Path) -> str:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink not allowed in package: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append(
            [relative.as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()]
        )
    raw = json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(raw).hexdigest()


def _at_or_below(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _capacity(value: int) -> int:
    if type(value) is not int or value not in (4, 12):
        raise ValueError("max_active must be plain int 4 or 12")
    return value


def _require_source_identity() -> None:
    if git_blob(SELECTIVE_SOURCE) != EXPECTED_SELECTIVE_BLOB:
        raise ValueError("canonical selective-carrot source drift")
    if git_blob(ENTRY_SOURCE) != EXPECTED_ENTRY_BLOB:
        raise ValueError("canonical selective-carrot current entry drift")
    if git_blob(LAB_ROOT / "main.py") != EXPECTED_PARENT_MAIN_BLOB:
        raise ValueError("canonical current-V5 parent main.py drift")


def build_candidate(
    baseline_root: Path, out: Path, max_active: int
) -> dict[str, object]:
    max_active = _capacity(max_active)
    baseline_root = baseline_root.resolve()
    out = out.resolve()
    if out.exists():
        raise ValueError("output directory must be new")
    if not baseline_root.is_dir():
        raise ValueError("baseline root must be a directory")
    if _at_or_below(out, baseline_root):
        raise ValueError("output directory must be outside baseline root")

    parent_main = baseline_root / "main.py"
    if not parent_main.is_file() or parent_main.is_symlink():
        raise ValueError("baseline main.py must be a regular file")
    if git_blob(parent_main) != EXPECTED_PARENT_MAIN_BLOB:
        raise ValueError("expected exact current-V5 parent main.py")
    for collision in (
        "baseline_main.py",
        "selective_carrot.py",
        "CARROT-CAPACITY.json",
    ):
        if (baseline_root / collision).exists():
            raise ValueError(f"baseline already contains {collision}")

    _require_source_identity()
    control_before = package_digest(baseline_root)
    try:
        shutil.copytree(
            baseline_root,
            out,
            symlinks=False,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
        copied_control = package_digest(out)
        control_after = package_digest(baseline_root)
        if not control_before == copied_control == control_after:
            raise ValueError("baseline package moved during materialization")

        (out / "main.py").rename(out / "baseline_main.py")
        shutil.copyfile(ENTRY_SOURCE, out / "main.py")
        shutil.copyfile(SELECTIVE_SOURCE, out / "selective_carrot.py")
        profile = {
            "schema": "titan-v5-selective-carrot-current/v1",
            "max_active": max_active,
            "control_package_sha256": control_before,
            "parent_main_git_blob": EXPECTED_PARENT_MAIN_BLOB,
            "selective_carrot_git_blob": EXPECTED_SELECTIVE_BLOB,
            "entry_git_blob": EXPECTED_ENTRY_BLOB,
        }
        (out / "CARROT-CAPACITY.json").write_text(
            json.dumps(profile, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        candidate_digest = package_digest(out)
    except Exception:
        if out.exists():
            shutil.rmtree(out)
        raise

    return {
        "schema": "titan-v5-selective-carrot-current-build/v1",
        "max_active": max_active,
        "control_package_sha256": control_before,
        "candidate_package_sha256": candidate_digest,
        "parent_main_git_blob": EXPECTED_PARENT_MAIN_BLOB,
        "selective_carrot_git_blob": EXPECTED_SELECTIVE_BLOB,
        "entry_git_blob": EXPECTED_ENTRY_BLOB,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--max-active", required=True, type=int, choices=[4, 12])
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)

    baseline_root = args.baseline_root.resolve()
    out = args.out.resolve()
    receipt_path = args.receipt.resolve() if args.receipt else None
    if receipt_path is not None:
        if receipt_path.exists():
            raise ValueError("receipt path must be new")
        if _at_or_below(receipt_path, baseline_root) or _at_or_below(
            receipt_path, out
        ):
            raise ValueError("receipt path must be outside package roots")

    receipt = build_candidate(baseline_root, out, args.max_active)
    raw = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if receipt_path is not None:
        receipt_path.write_text(raw, encoding="utf-8")
    print(raw, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
