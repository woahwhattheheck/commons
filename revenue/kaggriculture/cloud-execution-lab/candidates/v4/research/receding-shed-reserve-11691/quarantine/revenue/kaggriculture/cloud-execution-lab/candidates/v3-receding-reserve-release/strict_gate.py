# SPDX-License-Identifier: Apache-2.0
"""Own-cash admission gate layered after the paired margin comparator.

The existing paired comparator rejects incomplete evidence and margin
regressions.  This second, independent gate prevents an apparent margin gain
caused by reducing the rival's cash while the candidate's own cash falls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import tempfile
from typing import Any, Mapping

OPERATION = "titan-v3-receding-reserve-release-20260909-01"


class StrictGateError(ValueError):
    pass


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StrictGateError(f"{label} is not numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise StrictGateError(f"{label} is not finite")
    return parsed


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_report(path: Path) -> dict[str, Any]:
    try:
        report = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(
                StrictGateError(f"non-finite JSON token: {token}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StrictGateError(
            f"cannot read paired report: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(report, dict):
        raise StrictGateError("paired report must be one JSON object")
    return report


def evaluate(report: Mapping[str, Any]) -> dict[str, Any]:
    if report.get("schema_version") != 1:
        raise StrictGateError("schema_version mismatch")
    if report.get("operation") != OPERATION:
        raise StrictGateError("operation mismatch")
    upstream = report.get("verdict")
    if upstream not in ("ADVANCE", "NO_SIGNAL", "HOLD", "INVALID"):
        raise StrictGateError("unknown upstream verdict")

    rows = report.get("rows")
    if not isinstance(rows, list) or not rows:
        raise StrictGateError("paired rows must be a non-empty list")
    if report.get("cells") != len(rows):
        raise StrictGateError("paired cell count mismatch")

    seen: set[tuple[str, int, int]] = set()
    own: list[float] = []
    margin: list[float] = []
    changed = 0
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise StrictGateError(f"row {index} is not an object")
        opponent = row.get("opponent")
        seed = row.get("seed")
        seat = row.get("seat")
        if (
            not isinstance(opponent, str)
            or not opponent
            or isinstance(seed, bool)
            or not isinstance(seed, int)
            or seat not in (0, 1)
        ):
            raise StrictGateError(f"row {index} has an invalid identity")
        key = (opponent, seed, int(seat))
        if key in seen:
            raise StrictGateError(f"duplicate paired row {key}")
        seen.add(key)
        own.append(_number(row.get("own_delta"), f"row {index} own_delta"))
        margin.append(
            _number(row.get("margin_delta"), f"row {index} margin_delta")
        )
        trace_changed = row.get("trace_changed")
        if not isinstance(trace_changed, bool):
            raise StrictGateError(f"row {index} trace_changed is not boolean")
        changed += int(trace_changed)

    summary = {
        "cells": len(rows),
        "changed_cells": changed,
        "positive_own_cells": sum(value > 0 for value in own),
        "zero_own_cells": sum(value == 0 for value in own),
        "negative_own_cells": sum(value < 0 for value in own),
        "mean_own_delta": statistics.mean(own),
        "minimum_own_delta": min(own),
        "maximum_own_delta": max(own),
        "negative_margin_cells": sum(value < 0 for value in margin),
        "mean_margin_delta": statistics.mean(margin),
    }

    if upstream == "INVALID":
        verdict = "INVALID"
        reason = "upstream comparator marked evidence invalid"
    elif upstream == "HOLD":
        verdict = "HOLD"
        reason = "upstream comparator held the candidate"
    elif upstream == "NO_SIGNAL":
        if changed != 0:
            raise StrictGateError("NO_SIGNAL report contains changed traces")
        verdict = "NO_SIGNAL"
        reason = "upstream comparator found no candidate trace signal"
    elif changed == 0:
        verdict = "HOLD"
        reason = "ADVANCE report contains no changed trace"
    elif summary["negative_own_cells"]:
        verdict = "HOLD"
        reason = "at least one complete development cell lost own cash"
    elif summary["mean_own_delta"] <= 0:
        verdict = "HOLD"
        reason = "mean paired own cash did not improve"
    elif summary["negative_margin_cells"]:
        verdict = "HOLD"
        reason = "at least one complete development cell lost paired margin"
    elif summary["mean_margin_delta"] <= 0:
        verdict = "HOLD"
        reason = "mean paired margin did not improve"
    else:
        verdict = "ADVANCE"
        reason = "positive own cash and margin with no negative complete cell"

    return {
        "schema_version": 1,
        "operation": OPERATION,
        "upstream_verdict": upstream,
        "verdict": verdict,
        "reason": reason,
        "summary": summary,
    }


def markdown(result: Mapping[str, Any]) -> str:
    summary = result["summary"]
    return "\n".join(
        [
            "# TITAN V3 strict own-cash gate",
            "",
            f"**Verdict:** `{result['verdict']}` — {result['reason']}",
            "",
            f"- Upstream paired verdict: `{result['upstream_verdict']}`",
            f"- Complete cells: {summary['cells']}",
            f"- Trace-changed cells: {summary['changed_cells']}",
            f"- Own-cash cells (+ / 0 / -): "
            f"{summary['positive_own_cells']} / {summary['zero_own_cells']} / "
            f"{summary['negative_own_cells']}",
            f"- Mean own-cash delta: {summary['mean_own_delta']:+.3f}",
            f"- Minimum own-cash delta: {summary['minimum_own_delta']:+.3f}",
            f"- Mean paired-margin delta: {summary['mean_margin_delta']:+.3f}",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = evaluate(load_report(args.report))
        result["paired_report_sha256"] = _sha256(args.report)
        result["strict_gate_sha256"] = _sha256(Path(__file__))
    except StrictGateError as exc:
        result = {
            "schema_version": 1,
            "operation": OPERATION,
            "verdict": "INVALID",
            "reason": str(exc),
        }
        _atomic_write(
            args.output,
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        )
        _atomic_write(
            args.markdown,
            "# TITAN V3 strict own-cash gate\n\n"
            f"**Verdict:** `INVALID` — {exc}\n",
        )
        print(json.dumps(result, sort_keys=True))
        return 2

    _atomic_write(
        args.output,
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    _atomic_write(args.markdown, markdown(result))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["verdict"] in ("ADVANCE", "NO_SIGNAL") else 1


if __name__ == "__main__":
    raise SystemExit(main())
