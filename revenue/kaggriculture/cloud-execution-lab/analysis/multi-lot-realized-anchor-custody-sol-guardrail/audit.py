#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Emit a deterministic predecessor-killer and repaired custody receipt."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
PREDECESSOR_SOURCE = LAB / "candidates" / "multi-lot-portfolio-sol-pro" / "multi_lot_portfolio.py"
EXPECTED_PREDECESSOR_GIT_BLOB = "b7478242f19ef8554bb4e5b102fe1f9b61811a26"
EXPECTED_PREDECESSOR_SHA256 = "87e9e14981a4c9ecf6b98bd1eb0b76d5599ff41a2c80bf320e84b3b90d503d89"
SOURCE_HEAD = "74a77b154af1783a1c3767e484ff3d801966b73e"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from realized_anchor_custody import render_suffix, select_with_realized_anchor_custody


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    payload = path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def load_predecessor() -> Any:
    if git_blob(PREDECESSOR_SOURCE) != EXPECTED_PREDECESSOR_GIT_BLOB:
        raise RuntimeError("predecessor Git blob drift")
    if sha256(PREDECESSOR_SOURCE) != EXPECTED_PREDECESSOR_SHA256:
        raise RuntimeError("predecessor SHA-256 drift")
    spec = importlib.util.spec_from_file_location("bound_rejected_multi_lot", PREDECESSOR_SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load predecessor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def candidate(item: str, quantity: int, gain: float) -> dict[str, Any]:
    return {
        "item": item,
        "plan": ((10, quantity),),
        "info": {"witness": item},
        "rank": (False, gain),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    predecessor = load_predecessor()
    market = [["PASS"] for _ in range(8)]
    current = {"EGG": 1, "MILK": 0, "WOOL": 0}
    available = {"EGG": 1, "MILK": 1, "WOOL": 1}
    rows = [candidate("MILK", 1, 10), candidate("WOOL", 1, 20)]

    old = predecessor.select_portfolio(
        candidates=rows,
        anchor_item="WOOL",
        current=current,
        market=market,
        now=10,
        max_orders=10,
    )
    old_quantities = dict(current)
    for row in old.selected:
        old_quantities[row["item"]] = dict(row["plan"])[10]
    predecessor_suffix = render_suffix(
        quantities=old_quantities, offered={}, available=available, free_slots=2
    )
    scalar_suffix = render_suffix(
        quantities={**current, "WOOL": 1}, offered={}, available=available, free_slots=2
    )

    repaired = select_with_realized_anchor_custody(
        candidates=rows,
        anchor_item="WOOL",
        current=current,
        available=available,
        market=market,
        now=10,
        max_orders=10,
    )

    predecessor_selected = [row["item"] for row in old.selected]
    repaired_selected = [row["item"] for row in repaired.selected]
    checks = {
        "predecessor_reports_anchor_selected": "WOOL" in predecessor_selected,
        "predecessor_reports_all_slots_used": old.suffix_slots_used == 2,
        "predecessor_renderer_drops_anchor": ("WOOL", 1) not in predecessor_suffix,
        "scalar_renderer_realizes_anchor": ("WOOL", 1) in scalar_suffix,
        "repair_keeps_only_scalar_anchor": repaired_selected == ["WOOL"],
        "repair_preserves_scalar_suffix_exactly": (
            repaired.portfolio_suffix == repaired.scalar_suffix == scalar_suffix
        ),
        "repair_rejects_unrealizable_extra": repaired.rejected_unrealized == ("MILK",),
    }
    if not all(checks.values()):
        raise RuntimeError(f"custody audit failed: {checks}")

    receipt = {
        "schema_version": 1,
        "operation": "TITAN-V3-MULTI-LOT-REALIZED-ANCHOR-CUSTODY-20260910-01",
        "source_head": SOURCE_HEAD,
        "source_binding": {
            "path": str(PREDECESSOR_SOURCE.relative_to(LAB)),
            "git_blob": git_blob(PREDECESSOR_SOURCE),
            "sha256": sha256(PREDECESSOR_SOURCE),
        },
        "witness": {
            "max_orders": 10,
            "inherited_rows": 8,
            "current": current,
            "available": available,
            "candidate_order": [row["item"] for row in rows],
            "anchor_item": "WOOL",
            "predecessor_selected": predecessor_selected,
            "predecessor_reported_suffix_slots_used": old.suffix_slots_used,
            "scalar_suffix": [list(row) for row in scalar_suffix],
            "predecessor_realized_suffix": [list(row) for row in predecessor_suffix],
            "repaired_selected": repaired_selected,
            "repaired_realized_suffix": [list(row) for row in repaired.portfolio_suffix],
            "repaired_unrealized": list(repaired.rejected_unrealized),
            "repaired_scalar_displacements": list(repaired.rejected_scalar_displacement),
        },
        "checks": checks,
        "result": "PASS_STRUCTURAL_REPAIR_ONLY",
        "score_claim": False,
        "canonical_mutated": False,
        "provider_mutated": False,
        "kaggle_mutated": False,
        "files": {
            "repair_sha256": sha256(HERE / "realized_anchor_custody.py"),
            "test_sha256": sha256(HERE / "test_realized_anchor_custody.py"),
        },
    }
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
