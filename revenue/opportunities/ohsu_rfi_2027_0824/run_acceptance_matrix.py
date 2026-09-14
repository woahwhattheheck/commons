#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from ap_acceptance import evaluate
from ohsu_ap_rfi import ContractError, strict_load

MATRIX_SCHEMA = "tjlabs.ap-acceptance-matrix/v1"
RESULT_SCHEMA = "tjlabs.ap-acceptance-matrix-result/v1"
DECISIONS = {
    "ACCEPT_STP",
    "REJECT_DUPLICATE",
    "HOLD_MISSING_PO",
    "HOLD_VENDOR_MISMATCH",
    "HOLD_AMOUNT_VARIANCE",
    "HOLD_APPROVAL",
    "HOLD_RECONCILIATION",
}


def _canonical(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def evaluate_matrix(doc: Any) -> dict[str, Any]:
    if type(doc) is not dict or set(doc) != {"schema", "cases"}:
        raise ContractError("matrix: exact schema required")
    if doc["schema"] != MATRIX_SCHEMA:
        raise ContractError("matrix.schema: unsupported")
    rows = doc["cases"]
    if type(rows) is not list or len(rows) < 20 or len(rows) > 200:
        raise ContractError("matrix.cases: 20..200 cases required")

    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    counts = {d: 0 for d in sorted(DECISIONS)}
    for idx, row in enumerate(rows):
        if type(row) is not dict or set(row) != {"case", "expected_decision"}:
            raise ContractError(f"matrix.cases[{idx}]: exact wrapper required")
        expected = row["expected_decision"]
        if type(expected) is not str or expected not in DECISIONS:
            raise ContractError(f"matrix.cases[{idx}].expected_decision: unsupported")
        result = evaluate(row["case"])
        cid = result["case_id"]
        if cid in seen:
            raise ContractError(f"matrix.cases[{idx}].case_id: duplicate")
        seen.add(cid)
        if result["decision"] != expected:
            raise ContractError(
                f"matrix.cases[{idx}]: expected {expected}, got {result['decision']}"
            )
        counts[expected] += 1
        results.append(result)

    # A useful acceptance corpus must exercise every terminal disposition, not merely repeat STP.
    missing = [d for d, n in counts.items() if n == 0]
    if missing:
        raise ContractError(f"matrix: missing decision coverage {missing}")

    core = {
        "schema": RESULT_SCHEMA,
        "case_count": len(results),
        "decision_counts": counts,
        "results": results,
        "oracle_write_authorized": False,
        "payment_authorized": False,
    }
    core["receipt_sha256"] = hashlib.sha256(_canonical(core)).hexdigest()
    return core


def exclusive_write(path: Path, data: bytes) -> None:
    if path.is_symlink():
        raise RuntimeError(f"refusing symlink output: {path}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    finally:
        os.close(fd)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("matrix")
    p.add_argument("--json-out", required=True)
    args = p.parse_args()
    result = evaluate_matrix(strict_load(args.matrix))
    exclusive_write(Path(args.json_out), _canonical(result))
    print(result["receipt_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
