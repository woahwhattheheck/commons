#!/usr/bin/env python3
"""Fail-closed authenticated front door for the merged CARESAT current-route report.

This is not a second CARE oracle. It authenticates the exact merged CARESAT
oracle and the sibling current-Arlene route loader before importing either,
then delegates to ``care_bank_oracle.build_current_report()`` unchanged.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve()
FAMILY = HERE.parent
ORACLE_NAME = "care_bank_oracle.py"
CURRENT_CENSUS_NAME = "current_arlene_census.py"
EXPECTED_ORACLE_BLOB = "efb612c7edebd920dd1f5b70da6c7f4a97e784d2"
EXPECTED_CURRENT_CENSUS_BLOB = "d521dfcafd7d91287ec4cb18d6a29bfecc3627cd"


class CareSatTrustError(RuntimeError):
    pass


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _safe_rel(name: str) -> PurePosixPath:
    if not isinstance(name, str) or not name or "\\" in name:
        raise CareSatTrustError(f"unsafe path {name!r}")
    rel = PurePosixPath(name)
    if rel.is_absolute() or any(part in ("", ".", "..") for part in rel.parts):
        raise CareSatTrustError(f"unsafe path {name!r}")
    return rel


def verify_pinned_file(root: Path, name: str, expected_blob: str) -> Path:
    root = root.resolve(strict=True)
    rel = _safe_rel(name)
    if len(expected_blob) != 40 or any(c not in "0123456789abcdef" for c in expected_blob):
        raise CareSatTrustError(f"invalid expected Git blob for {name}")
    cur = root
    for part in rel.parts:
        cur = cur / part
        if cur.is_symlink():
            raise CareSatTrustError(f"symlink ancestry forbidden for {name}: {cur}")
    try:
        resolved = cur.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, RuntimeError, OSError, ValueError) as exc:
        raise CareSatTrustError(f"missing/escaping source {name}") from exc
    if not resolved.is_file():
        raise CareSatTrustError(f"regular file required for {name}")
    actual = git_blob_sha(resolved)
    if actual != expected_blob:
        raise CareSatTrustError(
            f"source drift for {name}: expected {expected_blob}, got {actual}"
        )
    return resolved


def _import_verified(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise CareSatTrustError(f"cannot import authenticated source {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_authenticated_oracle(root: Path = FAMILY) -> tuple[ModuleType, dict[str, str]]:
    oracle_path = verify_pinned_file(root, ORACLE_NAME, EXPECTED_ORACLE_BLOB)
    census_path = verify_pinned_file(
        root, CURRENT_CENSUS_NAME, EXPECTED_CURRENT_CENSUS_BLOB
    )
    # Authenticate the sibling dependency before importing the oracle. The
    # oracle later imports this exact path when build_current_report() runs.
    oracle = _import_verified(oracle_path, "_titan_v4_authenticated_caresat")
    return oracle, {
        "care_bank_oracle_blob": EXPECTED_ORACLE_BLOB,
        "current_arlene_census_blob": EXPECTED_CURRENT_CENSUS_BLOB,
    }


def build_authenticated_report(root: Path = FAMILY) -> dict[str, Any]:
    oracle, trust = load_authenticated_oracle(root)
    build = getattr(oracle, "build_current_report", None)
    if not callable(build):
        raise CareSatTrustError("authenticated CARESAT oracle lacks build_current_report")
    result = build()
    if not isinstance(result, dict):
        raise CareSatTrustError("authenticated CARESAT report must be a JSON object")
    out = dict(result)
    out["report_trust"] = trust
    return out


def main() -> int:
    try:
        report = build_authenticated_report()
    except (CareSatTrustError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
