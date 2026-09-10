# SPDX-License-Identifier: Apache-2.0
"""Exact-source carrier for TITAN same-turn funding Pareto ranking.

The production helper already minimizes the number of relocated SELL units before
any other tie break.  Its second key is positive remaining cash while the
candidate list is selected with ``min``.  Consequently, equal-minimum-movement
candidates are ordered from *least* to *most* certified cash.

This module verifies the exact current source and changes only the sign of that
one key.  It does not install the candidate into canonical TITAN.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

OPERATION = "TITAN-V3-SAME-TURN-FUNDING-PARETO-RANK-20260910-01"
CURRENT_BASE = "c51049d671b55d282e0fed5df37a0be7c513a838"
SOURCE_RELATIVE = "revenue/kaggriculture/cloud-execution-lab/frozen_selected.py"
SOURCE_GIT_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
CURRENT_ARCHIVE_SHA256 = "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"

PREIMAGE = b"                (moved,int(state['money']),source-target,target-destination,item),\n"
POSTIMAGE = b"                (moved,-int(state['money']),source-target,target-destination,item),\n"


class CustodyError(ValueError):
    """Raised when exact-source or one-hunk custody is not satisfied."""


def git_blob_id(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_source(data: bytes, *, expected_blob: str = SOURCE_GIT_BLOB) -> dict[str, object]:
    actual_blob = git_blob_id(data)
    if actual_blob != expected_blob:
        raise CustodyError(f"source Git blob mismatch: {actual_blob} != {expected_blob}")
    before = data.count(PREIMAGE)
    after = data.count(POSTIMAGE)
    if before != 1 or after != 0:
        raise CustodyError(
            f"ranking preimage custody failed: predecessor={before}, successor={after}"
        )
    return {
        "git_blob": actual_blob,
        "sha256": sha256(data),
        "bytes": len(data),
        "preimage_count": before,
        "postimage_count": after,
    }


def patch_source(data: bytes, *, expected_blob: str = SOURCE_GIT_BLOB) -> tuple[bytes, dict[str, object]]:
    source = verify_source(data, expected_blob=expected_blob)
    patched = data.replace(PREIMAGE, POSTIMAGE, 1)
    if patched == data:
        raise CustodyError("patch produced no byte change")
    if patched.count(PREIMAGE) != 0 or patched.count(POSTIMAGE) != 1:
        raise CustodyError("patched source does not contain exactly one successor key")

    # The one-factor carrier may change exactly one physical line.
    old_lines = data.splitlines(keepends=True)
    new_lines = patched.splitlines(keepends=True)
    if len(old_lines) != len(new_lines):
        raise CustodyError("patch changed source line cardinality")
    changed = [index + 1 for index, (old, new) in enumerate(zip(old_lines, new_lines)) if old != new]
    if len(changed) != 1:
        raise CustodyError(f"patch changed {len(changed)} lines, expected one")

    receipt = {
        "operation": OPERATION,
        "base_commit": CURRENT_BASE,
        "source_path": SOURCE_RELATIVE,
        "source": source,
        "candidate": {
            "git_blob": git_blob_id(patched),
            "sha256": sha256(patched),
            "bytes": len(patched),
            "preimage_count": patched.count(PREIMAGE),
            "postimage_count": patched.count(POSTIMAGE),
        },
        "changed_lines": changed,
        "semantic_delta": "minimize moved units, then maximize certified remaining cash",
    }
    return patched, receipt


@dataclass(frozen=True)
class FundingCandidate:
    moved: int
    remaining_cash: int
    source_distance: int
    destination_distance: int
    item: str

    def predecessor_key(self) -> tuple[int, int, int, int, str]:
        return (
            int(self.moved),
            int(self.remaining_cash),
            int(self.source_distance),
            int(self.destination_distance),
            str(self.item),
        )

    def candidate_key(self) -> tuple[int, int, int, int, str]:
        return (
            int(self.moved),
            -int(self.remaining_cash),
            int(self.source_distance),
            int(self.destination_distance),
            str(self.item),
        )


def choose(candidates: Sequence[FundingCandidate], *, repaired: bool) -> FundingCandidate:
    if not candidates:
        raise ValueError("at least one funding candidate is required")
    key = FundingCandidate.candidate_key if repaired else FundingCandidate.predecessor_key
    return min(candidates, key=key)


def model_witness() -> dict[str, object]:
    """Source-independent reduction matching the current concrete test case.

    A first HIRE costs 10.  Moving one CARROT sale ahead yields 35 and leaves 25;
    moving one WOOL sale ahead yields 200 and leaves 190.  Both relocate one
    already-planned unit and both complete the same HIRE.  All per-item sale
    quantities remain invariant.
    """
    candidates = (
        FundingCandidate(1, 25, 1, 1, "CARROT"),
        FundingCandidate(1, 190, 2, 1, "WOOL"),
    )
    predecessor = choose(candidates, repaired=False)
    repaired = choose(candidates, repaired=True)
    return {
        "operation": OPERATION,
        "orders": [[], ["HIRE"], ["SELL", "CARROT", 1], ["SELL", "WOOL", 1]],
        "hire_cost": 10,
        "market_inventory": {"CARROT": 10000, "WOOL": 10000},
        "candidates": [asdict(candidate) for candidate in candidates],
        "predecessor": asdict(predecessor),
        "candidate": asdict(repaired),
        "certified_remaining_cash_delta": repaired.remaining_cash - predecessor.remaining_cash,
        "invariants": {
            "minimum_moved_units_equal": predecessor.moved == repaired.moved == 1,
            "same_fixed_acquisition_completed": True,
            "sale_quantities_preserved_by_item": True,
        },
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _cmd_patch(args: argparse.Namespace) -> int:
    source_path = Path(args.source)
    output_path = Path(args.output)
    receipt_path = Path(args.receipt)
    data = source_path.read_bytes()
    patched, receipt = patch_source(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(patched)
    _write_json(receipt_path, receipt)
    return 0


def _cmd_model(args: argparse.Namespace) -> int:
    witness = model_witness()
    _write_json(Path(args.output), witness)
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    patch = sub.add_parser("patch", help="verify and patch exact frozen_selected.py")
    patch.add_argument("--source", required=True)
    patch.add_argument("--output", required=True)
    patch.add_argument("--receipt", required=True)
    patch.set_defaults(func=_cmd_patch)
    model = sub.add_parser("model-witness", help="write the deterministic reduced witness")
    model.add_argument("--output", required=True)
    model.set_defaults(func=_cmd_model)
    return result


def main(argv: Iterable[str] | None = None) -> int:
    args = parser().parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
