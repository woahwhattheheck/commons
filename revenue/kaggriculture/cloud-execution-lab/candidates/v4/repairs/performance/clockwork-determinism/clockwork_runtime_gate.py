#!/usr/bin/env python3
"""Fail-closed quiet-vs-loaded runtime decision equivalence gate for TITAN V4.

This module does not run games and does not change policy.  It authenticates
per-callback receipts emitted by a current-entrypoint runner and rejects any
contention-dependent action/state/fallback behavior.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

HEX64 = set("0123456789abcdef")
VALID_STATUS = {"completed", "deadline_fallback"}


class GateError(ValueError):
    pass


def _sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX64 for c in value):
        raise GateError(f"{field} must be a lowercase 64-hex SHA256")
    return value


def _integer(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise GateError(f"{field} must be an integer >= {minimum}")
    return value


def _finite_optional(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GateError(f"{field} must be a finite number or null")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise GateError(f"{field} must be finite and nonnegative")
    return result


def normalize_row(raw: Any, *, source: str, line: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise GateError(f"{source}:{line}: row must be an object")
    allowed = {
        "candidate_sha256", "runtime_sha256", "engine_sha256", "opponent_id",
        "seed", "seat", "step", "status", "fallback_stage", "observation_sha256",
        "input_state_sha256", "action_sha256", "state_sha256", "elapsed_seconds", "act_cpu_seconds",
    }
    extra = sorted(set(raw) - allowed)
    missing = sorted({
        "candidate_sha256", "runtime_sha256", "engine_sha256", "opponent_id",
        "seed", "seat", "step", "status", "fallback_stage", "observation_sha256",
        "input_state_sha256", "action_sha256", "state_sha256",
    } - set(raw))
    if missing:
        raise GateError(f"{source}:{line}: missing fields: {', '.join(missing)}")
    if extra:
        raise GateError(f"{source}:{line}: unexpected fields: {', '.join(extra)}")
    opponent = raw["opponent_id"]
    if not isinstance(opponent, str) or not opponent or opponent.strip() != opponent:
        raise GateError(f"{source}:{line}: opponent_id must be a nonempty trimmed string")
    status = raw["status"]
    if status not in VALID_STATUS:
        raise GateError(f"{source}:{line}: unsupported status {status!r}")
    stage = raw["fallback_stage"]
    if status == "completed":
        if stage is not None:
            raise GateError(f"{source}:{line}: completed row must have fallback_stage=null")
    else:
        if not isinstance(stage, str) or not stage or stage.strip() != stage:
            raise GateError(f"{source}:{line}: deadline_fallback requires a stage string")
    row = {
        "candidate_sha256": _sha256(raw["candidate_sha256"], "candidate_sha256"),
        "runtime_sha256": _sha256(raw["runtime_sha256"], "runtime_sha256"),
        "engine_sha256": _sha256(raw["engine_sha256"], "engine_sha256"),
        "opponent_id": opponent,
        "seed": _integer(raw["seed"], "seed"),
        "seat": _integer(raw["seat"], "seat"),
        "step": _integer(raw["step"], "step"),
        "status": status,
        "fallback_stage": stage,
        "observation_sha256": _sha256(raw["observation_sha256"], "observation_sha256"),
        "input_state_sha256": _sha256(raw["input_state_sha256"], "input_state_sha256"),
        "action_sha256": _sha256(raw["action_sha256"], "action_sha256"),
        "state_sha256": _sha256(raw["state_sha256"], "state_sha256"),
        "elapsed_seconds": _finite_optional(raw.get("elapsed_seconds"), "elapsed_seconds"),
        "act_cpu_seconds": _finite_optional(raw.get("act_cpu_seconds"), "act_cpu_seconds"),
    }
    if row["seat"] not in (0, 1):
        raise GateError(f"{source}:{line}: seat must be 0 or 1")
    return row


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, text in enumerate(handle, 1):
            if not text.strip():
                continue
            try:
                raw = json.loads(text, parse_constant=lambda token: (_ for _ in ()).throw(
                    GateError(f"nonfinite JSON constant {token}")))
            except (json.JSONDecodeError, GateError) as exc:
                raise GateError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            rows.append(normalize_row(raw, source=str(path), line=line_no))
    if not rows:
        raise GateError(f"{path}: panel is empty")
    return rows


def coordinate(row: dict[str, Any]) -> tuple[str, int, int, int]:
    return row["opponent_id"], row["seed"], row["seat"], row["step"]


def _index(rows: Iterable[dict[str, Any]], label: str) -> dict[tuple[str, int, int, int], dict[str, Any]]:
    out: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    identity = None
    for row in rows:
        key = coordinate(row)
        if key in out:
            raise GateError(f"{label}: duplicate coordinate {key!r}")
        current_identity = (row["candidate_sha256"], row["runtime_sha256"], row["engine_sha256"])
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise GateError(f"{label}: mixed candidate/runtime/engine identities")
        out[key] = row
    if not out:
        raise GateError(f"{label}: panel is empty")
    return out


def compare_panels(
    quiet_rows: Iterable[dict[str, Any]],
    loaded_rows: Iterable[dict[str, Any]],
    *,
    require_completed: bool = True,
) -> dict[str, Any]:
    quiet = _index(quiet_rows, "quiet")
    loaded = _index(loaded_rows, "loaded")
    q_keys, l_keys = set(quiet), set(loaded)
    missing_loaded = sorted(q_keys - l_keys)
    missing_quiet = sorted(l_keys - q_keys)
    if missing_loaded or missing_quiet:
        raise GateError(
            f"coordinate mismatch: missing_loaded={missing_loaded[:5]!r} "
            f"missing_quiet={missing_quiet[:5]!r}"
        )
    keys = sorted(q_keys)
    q_identity = tuple(quiet[keys[0]][name] for name in (
        "candidate_sha256", "runtime_sha256", "engine_sha256"))
    l_identity = tuple(loaded[keys[0]][name] for name in (
        "candidate_sha256", "runtime_sha256", "engine_sha256"))
    if q_identity != l_identity:
        raise GateError("quiet/loaded candidate/runtime/engine identity mismatch")

    observation_mismatch = []
    input_state_mismatch = []
    action_mismatch = []
    state_mismatch = []
    status_mismatch = []
    stage_mismatch = []
    quiet_fallbacks = Counter()
    loaded_fallbacks = Counter()
    for key in keys:
        q, l = quiet[key], loaded[key]
        if q["observation_sha256"] != l["observation_sha256"]:
            observation_mismatch.append(key)
        if q["input_state_sha256"] != l["input_state_sha256"]:
            input_state_mismatch.append(key)
        if q["action_sha256"] != l["action_sha256"]:
            action_mismatch.append(key)
        if q["state_sha256"] != l["state_sha256"]:
            state_mismatch.append(key)
        if q["status"] != l["status"]:
            status_mismatch.append(key)
        if q["fallback_stage"] != l["fallback_stage"]:
            stage_mismatch.append(key)
        if q["status"] == "deadline_fallback":
            quiet_fallbacks[q["fallback_stage"]] += 1
        if l["status"] == "deadline_fallback":
            loaded_fallbacks[l["fallback_stage"]] += 1

    reasons = []
    if observation_mismatch:
        reasons.append(f"observation_mismatch={len(observation_mismatch)}")
    if input_state_mismatch:
        reasons.append(f"input_state_mismatch={len(input_state_mismatch)}")
    if action_mismatch:
        reasons.append(f"action_mismatch={len(action_mismatch)}")
    if state_mismatch:
        reasons.append(f"state_mismatch={len(state_mismatch)}")
    if status_mismatch:
        reasons.append(f"status_mismatch={len(status_mismatch)}")
    if stage_mismatch:
        reasons.append(f"fallback_stage_mismatch={len(stage_mismatch)}")
    if require_completed and (quiet_fallbacks or loaded_fallbacks):
        reasons.append(
            f"fallbacks_present=quiet:{sum(quiet_fallbacks.values())},loaded:{sum(loaded_fallbacks.values())}"
        )

    return {
        "schema": "titan-v4-clockwork-runtime-gate-v1",
        "authoritative": bool(require_completed),
        "passed": not reasons,
        "rows": len(keys),
        "identity": {
            "candidate_sha256": q_identity[0],
            "runtime_sha256": q_identity[1],
            "engine_sha256": q_identity[2],
        },
        "quiet_fallbacks_by_stage": dict(sorted(quiet_fallbacks.items())),
        "loaded_fallbacks_by_stage": dict(sorted(loaded_fallbacks.items())),
        "observation_mismatch_count": len(observation_mismatch),
        "input_state_mismatch_count": len(input_state_mismatch),
        "action_mismatch_count": len(action_mismatch),
        "state_mismatch_count": len(state_mismatch),
        "status_mismatch_count": len(status_mismatch),
        "fallback_stage_mismatch_count": len(stage_mismatch),
        "first_observation_mismatches": [list(x) for x in observation_mismatch[:5]],
        "first_input_state_mismatches": [list(x) for x in input_state_mismatch[:5]],
        "first_action_mismatches": [list(x) for x in action_mismatch[:5]],
        "first_state_mismatches": [list(x) for x in state_mismatch[:5]],
        "first_status_mismatches": [list(x) for x in status_mismatch[:5]],
        "first_stage_mismatches": [list(x) for x in stage_mismatch[:5]],
        "reasons": reasons,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", type=Path, required=True)
    parser.add_argument("--loaded", type=Path, required=True)
    parser.add_argument("--json", type=Path)
    parser.add_argument(
        "--diagnostic-allow-symmetric-fallback",
        action="store_true",
        help="non-authoritative diagnostics only; authoritative mode requires zero fallbacks",
    )
    args = parser.parse_args(argv)
    try:
        receipt = compare_panels(
            load_jsonl(args.quiet), load_jsonl(args.loaded),
            require_completed=not args.diagnostic_allow_symmetric_fallback,
        )
    except (OSError, GateError) as exc:
        receipt = {
            "schema": "titan-v4-clockwork-runtime-gate-v1",
            "authoritative": not args.diagnostic_allow_symmetric_fallback,
            "passed": False,
            "error": str(exc),
        }
    text = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    if args.json:
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if receipt.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
