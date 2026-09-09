# SPDX-License-Identifier: Apache-2.0
"""Compose HELIX's exact factorial materializer with root-owned entry guards.

This module changes no seller policy. It delegates every source copy and literal
seam edit to the reviewed SOL-HELIX materializer, replacing only the generated
entry wrapper so a preloaded or escaped ``candidate``/``scheduler`` cannot
impersonate the retained closure.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import strict_factorial

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "v1v2-seller-factorial-sol-helix" / "materialize.py"
REPAIR = "sol-vernier-factorial-import-ownership-v1"
IMPORT_OWNERSHIP = "candidate+scheduler-under-bound-root-v1"


class MaterializeCompositionError(RuntimeError):
    """The exact parent materializer or composed receipt is invalid."""


def _load_parent(path: Path = PARENT):
    path = Path(path).resolve(strict=True)
    spec = importlib.util.spec_from_file_location("_sol_vernier_helix_materialize", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load HELIX materializer: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if getattr(module, "OPERATION", None) != strict_factorial.OPERATION:
        raise MaterializeCompositionError("HELIX operation identity drift")
    return module


def materialize_arm(
    arm: str,
    *,
    source: Path,
    output: Path,
    receipt_path: Path,
    parent_path: Path = PARENT,
) -> dict[str, Any]:
    """Materialize one arm and add executable import-root custody."""
    parent = _load_parent(parent_path)
    original_factory = parent._bound_entry_source
    parent._bound_entry_source = strict_factorial.bound_entry_source
    try:
        receipt = parent.materialize_arm(
            arm,
            source=Path(source),
            output=Path(output),
            receipt_path=Path(receipt_path),
        )
    finally:
        parent._bound_entry_source = original_factory

    if not isinstance(receipt, dict):
        raise MaterializeCompositionError("HELIX materializer returned a non-object receipt")
    entry = receipt.get("entrypoint")
    if not isinstance(entry, dict):
        raise MaterializeCompositionError("HELIX receipt lacks entrypoint object")
    entry["import_ownership"] = IMPORT_OWNERSHIP
    entry["runtime_origins"] = strict_factorial.verify_entry_runtime(
        Path(output).resolve(strict=True) / "bound_entry.py"
    )
    receipt["evidence_repair"] = {
        "schema_version": 1,
        "repair": REPAIR,
        "parent_materializer_sha256": strict_factorial.sha256_file(Path(parent_path)),
        "strict_admission_sha256": strict_factorial.sha256_file(Path(strict_factorial.__file__)),
        "policy_bytes_changed": False,
    }
    parent.atomic_json(Path(receipt_path), receipt)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=sorted(strict_factorial.ARMS), required=True)
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)

    parent = _load_parent()
    source = args.source if args.source is not None else parent.SOURCE
    receipt = materialize_arm(
        args.arm,
        source=source,
        output=args.output,
        receipt_path=args.receipt,
    )
    print(
        json.dumps(
            {
                "arm": args.arm,
                "entry_sha256": receipt["entrypoint"]["sha256"],
                "closure_sha256": receipt["closure_bound_at_entry"]["sha256"],
                "import_ownership": receipt["entrypoint"]["import_ownership"],
                "repair": receipt["evidence_repair"]["repair"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
