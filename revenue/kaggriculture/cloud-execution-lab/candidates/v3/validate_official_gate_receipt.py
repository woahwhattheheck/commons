#!/usr/bin/env python3
"""Validate whether a TITAN V3.1 simulation receipt qualifies as an official gate.

This is evidence/tooling only. It does not execute Kaggriculture, mutate a candidate,
or decide whether an economically valid result should be promoted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


class ReceiptError(ValueError):
    """Raised when a claimed gate receipt is incomplete, ambiguous, or inconsistent."""


RECEIPT_SCHEMA = "titan-v31-gate-receipt/v1"
OFFICIAL_INTERPRETER_COMMIT = "28b6d8af3"
LIVE_RELEASE_VERSION = "3.1"
SEED_LIST_ENCODING = "ASCII decimal seed per line, LF after every seed including the final seed"
HERE = Path(__file__).resolve().parent
AUTHORITATIVE_MANIFEST = HERE / "V3-MANIFEST.json"
AUTHORITATIVE_PANEL = HERE / "OFFICIAL-GATE-PANEL.json"

CANONICAL_V31_CONFIG_KEYS = frozenset(
    {
        "consumer", "frozen", "seed", "funding", "terminal_route", "committed",
        "budget_seconds", "reserve_seconds", "terminal_history", "redundant_hire",
        "fourth_quadrant", "market_pressure", "committed_seed_retry", "operating_stock",
        "idle_fertilizer", "crop_release", "early_capital",
    }
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReceiptError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ReceiptError(f"{label} must be a list")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ReceiptError(f"{label} must be a lowercase 64-hex SHA-256")
    return value


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReceiptError(f"{label} must be a JSON number")
    out = float(value)
    if not math.isfinite(out):
        raise ReceiptError(f"{label} must be finite")
    return out


def _seat(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
        raise ReceiptError(f"{label} must be 0 or 1")
    return value


def _score_pair(value: Any, label: str) -> tuple[float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        raise ReceiptError(f"{label} must contain [seat0, seat1]")
    return _number(value[0], f"{label}[0]"), _number(value[1], f"{label}[1]")


def _json_equal(left: Any, right: Any) -> bool:
    """JSON structural equality without Python's bool/int equivalence."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_json_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_json_equal(a, b) for a, b in zip(left, right))
    return left == right


def _latest_release(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    releases = manifest.get("releases")
    if not isinstance(releases, list) or not releases:
        raise ReceiptError("manifest.releases must be a non-empty list")
    return _mapping(releases[-1], "manifest.releases[-1]")


def _live_v31_release(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    release = _latest_release(manifest)
    if release.get("version") != LIVE_RELEASE_VERSION:
        raise ReceiptError(
            "manifest latest release must be authoritative V3.1; "
            f"found version {release.get('version')!r}. Official V3.1 receipts fail closed until "
            "the live-submission release/config is durably recorded."
        )
    return release


def _required_v31_config_keys(manifest: Mapping[str, Any]) -> set[str]:
    required = set(CANONICAL_V31_CONFIG_KEYS)
    keys = _mapping(manifest.get("keys"), "manifest.keys")
    params = _mapping(keys.get("params"), "manifest.keys.params")
    required.update(params.keys())
    for key, spec_any in keys.items():
        if key == "params":
            continue
        spec = _mapping(spec_any, f"manifest.keys[{key!r}]")
        if "default" in spec:
            required.add(key)
    return required


def _expected_cells(panel: Mapping[str, Any]) -> set[tuple[int, int]]:
    seeds = _list(panel.get("seeds"), "panel.seeds")
    seats = _list(panel.get("seats"), "panel.seats")
    if not seeds:
        raise ReceiptError("panel.seeds must be non-empty")
    normalized_seeds: list[int] = []
    for idx, seed in enumerate(seeds):
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ReceiptError(f"panel.seeds[{idx}] must be an integer")
        normalized_seeds.append(seed)
    if len(set(normalized_seeds)) != len(normalized_seeds):
        raise ReceiptError("panel.seeds must not contain duplicates")
    normalized_seats = [_seat(seat, f"panel.seats[{idx}]") for idx, seat in enumerate(seats)]
    if sorted(normalized_seats) != [0, 1]:
        raise ReceiptError("panel.seats must contain both seats exactly once")

    encoding = panel.get("seed_list_sha256_encoding")
    if encoding != SEED_LIST_ENCODING:
        raise ReceiptError(f"panel.seed_list_sha256_encoding must be exactly {SEED_LIST_ENCODING!r}")
    seed_bytes = "".join(f"{seed}\n" for seed in normalized_seeds).encode("ascii")
    recomputed_digest = hashlib.sha256(seed_bytes).hexdigest()
    declared_digest = _sha256(panel.get("seed_list_sha256"), "panel.seed_list_sha256")
    if declared_digest != recomputed_digest:
        raise ReceiptError(
            "panel.seed_list_sha256 disagrees with the authoritative seeds/encoding: "
            f"declared {declared_digest}, recomputed {recomputed_digest}"
        )
    return {(seed, seat) for seed in normalized_seeds for seat in normalized_seats}


def _validate_config(receipt: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
    release = _live_v31_release(manifest)
    expected_live = _mapping(release.get("config"), "manifest V3.1 release.config")
    missing_required = sorted(_required_v31_config_keys(manifest) - set(expected_live))
    if missing_required:
        raise ReceiptError(
            "manifest V3.1 release.config is not a complete live TITAN-CONFIG; "
            f"missing required keys: {missing_required}"
        )
    submission = _mapping(release.get("submission_archive"), "manifest V3.1 release.submission_archive")
    expected_submission_sha = _sha256(
        submission.get("sha256"), "manifest V3.1 release.submission_archive.sha256"
    )

    baseline = _mapping(receipt.get("baseline"), "baseline")
    if baseline.get("submission_archive_sha256") != expected_submission_sha:
        raise ReceiptError("baseline.submission_archive_sha256 does not match the authoritative V3.1 release")
    baseline_config = _mapping(baseline.get("config"), "baseline.config")
    if not _json_equal(dict(baseline_config), dict(expected_live)):
        raise ReceiptError(
            "baseline.config must exactly equal the complete authoritative V3.1 release.config "
            "with JSON type+value strictness"
        )

    candidate = _mapping(receipt.get("candidate"), "candidate")
    candidate_config = _mapping(candidate.get("config"), "candidate.config")
    overrides = _mapping(candidate.get("config_overrides"), "candidate.config_overrides")
    if set(candidate_config) != set(baseline_config):
        raise ReceiptError("candidate.config key set must exactly match baseline.config")
    unknown = sorted(set(overrides) - set(baseline_config))
    if unknown:
        raise ReceiptError(f"candidate.config_overrides contains unknown keys: {unknown}")

    expected_candidate = dict(baseline_config)
    for key, value in overrides.items():
        if type(value) is not type(baseline_config[key]):
            raise ReceiptError(
                f"candidate.config_overrides[{key!r}] changes JSON type "
                f"from {type(baseline_config[key]).__name__} to {type(value).__name__}"
            )
        expected_candidate[key] = value
    if not _json_equal(dict(candidate_config), expected_candidate):
        raise ReceiptError(
            "candidate.config differs from baseline by more than the declared, JSON-type-strict config_overrides"
        )


def _validate_provenance(receipt: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
    interpreter = _mapping(receipt.get("interpreter"), "interpreter")
    if interpreter.get("commit") != OFFICIAL_INTERPRETER_COMMIT:
        raise ReceiptError(f"interpreter.commit must be pinned official {OFFICIAL_INTERPRETER_COMMIT}")
    _sha256(interpreter.get("blob_sha256"), "interpreter.blob_sha256")
    if interpreter.get("verified_clean") is not True:
        raise ReceiptError("interpreter.verified_clean must be true")

    base = _mapping(manifest.get("base"), "manifest.base")
    expected_base_sha = _sha256(base.get("sha256"), "manifest.base.sha256")
    candidate = _mapping(receipt.get("candidate"), "candidate")
    if candidate.get("builder") != "build_v3.py":
        raise ReceiptError("candidate.builder must be build_v3.py")
    if candidate.get("built_from_pinned_archive") is not True:
        raise ReceiptError("candidate.built_from_pinned_archive must be true")
    if candidate.get("base_archive_sha256") != expected_base_sha:
        raise ReceiptError("candidate.base_archive_sha256 does not match manifest.base.sha256")
    _sha256(candidate.get("package_sha256"), "candidate.package_sha256")


def _validate_panel_and_results(
    receipt: Mapping[str, Any], panel: Mapping[str, Any]
) -> dict[str, float | int]:
    expected = _expected_cells(panel)
    games_per_opponent = panel.get("games_per_opponent")
    if (
        isinstance(games_per_opponent, bool)
        or not isinstance(games_per_opponent, int)
        or games_per_opponent != len(expected)
    ):
        raise ReceiptError("panel.games_per_opponent must be an exact integer equal to the frozen seed x seat cell count")
    gate = _mapping(receipt.get("panel"), "receipt.panel")
    if not _json_equal(gate.get("seeds"), panel.get("seeds")):
        raise ReceiptError("receipt.panel.seeds must exactly match OFFICIAL-GATE-PANEL.json with JSON type strictness")
    if not _json_equal(gate.get("seats"), panel.get("seats")):
        raise ReceiptError("receipt.panel.seats must exactly match OFFICIAL-GATE-PANEL.json with JSON type strictness")
    if gate.get("seed_list_sha256") != panel.get("seed_list_sha256"):
        raise ReceiptError("receipt.panel.seed_list_sha256 mismatch")
    if not _json_equal(gate.get("games_per_opponent"), games_per_opponent):
        raise ReceiptError("receipt.panel.games_per_opponent must exactly match with JSON type strictness")

    opponent = _mapping(receipt.get("opponent"), "opponent")
    if not isinstance(opponent.get("name"), str) or not opponent["name"].strip():
        raise ReceiptError("opponent.name must be a non-empty string")
    _sha256(opponent.get("sha256"), "opponent.sha256")
    if opponent.get("same_bytes_between_arms") is not True:
        raise ReceiptError("opponent.same_bytes_between_arms must be true")

    rows = _list(receipt.get("per_cell_results"), "per_cell_results")
    seen: set[tuple[int, int]] = set()
    deltas: list[float] = []
    for idx, row_any in enumerate(rows):
        row = _mapping(row_any, f"per_cell_results[{idx}]")
        seed = row.get("seed")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ReceiptError(f"per_cell_results[{idx}].seed must be an integer")
        seat = _seat(row.get("candidate_seat"), f"per_cell_results[{idx}].candidate_seat")
        key = (seed, seat)
        if key not in expected:
            raise ReceiptError(f"per_cell_results[{idx}] is outside the frozen panel: {key}")
        if key in seen:
            raise ReceiptError(f"duplicate frozen panel cell: {key}")
        seen.add(key)
        baseline = _score_pair(row.get("baseline_scores"), f"per_cell_results[{idx}].baseline_scores")
        candidate = _score_pair(row.get("candidate_scores"), f"per_cell_results[{idx}].candidate_scores")
        b_own, b_rival = (baseline[0], baseline[1]) if seat == 0 else (baseline[1], baseline[0])
        c_own, c_rival = (candidate[0], candidate[1]) if seat == 0 else (candidate[1], candidate[0])
        delta = (c_own - c_rival) - (b_own - b_rival)
        supplied = _number(row.get("delta_m"), f"per_cell_results[{idx}].delta_m")
        if not math.isclose(supplied, delta, rel_tol=0.0, abs_tol=1e-9):
            raise ReceiptError(
                f"per_cell_results[{idx}].delta_m={supplied} "
                f"disagrees with seat-aware recomputation {delta}"
            )
        deltas.append(delta)

    missing = sorted(expected - seen)
    if missing:
        raise ReceiptError(f"partial frozen panel; missing cells: {missing[:5]}")
    if len(rows) != len(expected):
        raise ReceiptError(f"per_cell_results must contain exactly {len(expected)} frozen cells")

    aggregate = _mapping(receipt.get("aggregate"), "aggregate")
    mean = sum(deltas) / len(deltas)
    supplied_mean = _number(aggregate.get("mean_delta_m"), "aggregate.mean_delta_m")
    if not math.isclose(supplied_mean, mean, rel_tol=0.0, abs_tol=1e-9):
        raise ReceiptError(f"aggregate.mean_delta_m={supplied_mean} disagrees with recomputed {mean}")
    return {"cells": len(rows), "mean_delta_m": mean}


def _validate_receipt_against_inputs(
    receipt: Mapping[str, Any], manifest: Mapping[str, Any], panel: Mapping[str, Any]
) -> dict[str, Any]:
    """Pure consistency validator; it never grants official eligibility."""
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise ReceiptError(f"schema must be {RECEIPT_SCHEMA}")

    mode = receipt.get("mode")
    if mode == "practice":
        if receipt.get("official_gate_pass") is not False:
            raise ReceiptError("practice receipts must set official_gate_pass=false")
        reason = receipt.get("practice_reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ReceiptError("practice receipts must state a non-empty practice_reason")
        return {"valid": True, "mode": "practice", "official_gate_eligible": False, "reason": reason.strip()}
    if mode != "official":
        raise ReceiptError("mode must be exactly 'official' or 'practice'")

    _validate_provenance(receipt, manifest)
    _validate_config(receipt, manifest)
    result = _validate_panel_and_results(receipt, panel)
    return {"valid": True, "mode": "official", "input_contract_valid": True, **result}


def validate_receipt(
    receipt: Mapping[str, Any], manifest: Mapping[str, Any], panel: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate caller-supplied mappings without granting official provenance."""
    if receipt.get("mode") == "official":
        raise ReceiptError(
            "caller-supplied manifest/panel mappings cannot mint official eligibility; "
            "use validate_authoritative_receipt()"
        )
    return _validate_receipt_against_inputs(receipt, manifest, panel)


def _read_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"cannot read {label} JSON {path}: {exc}") from exc
    return _mapping(value, label)


def _read_authoritative_json(path: Path, label: str) -> tuple[Mapping[str, Any], str]:
    if path.is_symlink():
        raise ReceiptError(f"authoritative {label} must not be a symlink: {path}")
    if not path.is_file():
        raise ReceiptError(f"authoritative {label} is not a regular file: {path}")
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"cannot read authoritative {label} JSON {path}: {exc}") from exc
    return _mapping(value, label), hashlib.sha256(raw).hexdigest()


def validate_authoritative_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Validate official evidence against only this checkout's sibling authority files."""
    if receipt.get("mode") != "official":
        raise ReceiptError("validate_authoritative_receipt() requires mode='official'")
    manifest, manifest_sha256 = _read_authoritative_json(AUTHORITATIVE_MANIFEST, "manifest")
    panel, panel_sha256 = _read_authoritative_json(AUTHORITATIVE_PANEL, "panel")
    result = _validate_receipt_against_inputs(receipt, manifest, panel)
    if result.get("input_contract_valid") is not True:
        raise ReceiptError("authoritative input contract did not validate")
    result["official_gate_eligible"] = True
    result["authoritative_inputs"] = {
        "manifest": AUTHORITATIVE_MANIFEST.name,
        "manifest_sha256": manifest_sha256,
        "panel": AUTHORITATIVE_PANEL.name,
        "panel_sha256": panel_sha256,
    }
    return result


def _same_path(left: Path, right: Path) -> bool:
    return left.expanduser().resolve(strict=False) == right.expanduser().resolve(strict=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--manifest", type=Path, default=AUTHORITATIVE_MANIFEST, help="custom manifest for practice-mode validation only")
    parser.add_argument("--panel", type=Path, default=AUTHORITATIVE_PANEL, help="custom panel for practice-mode validation only")
    args = parser.parse_args(argv)
    try:
        receipt = _read_json(args.receipt, "receipt")
        if receipt.get("mode") == "official":
            if not _same_path(args.manifest, AUTHORITATIVE_MANIFEST) or not _same_path(args.panel, AUTHORITATIVE_PANEL):
                raise ReceiptError(
                    "official mode rejects --manifest/--panel overrides; authoritative sibling files are mandatory"
                )
            result = validate_authoritative_receipt(receipt)
        else:
            result = validate_receipt(receipt, _read_json(args.manifest, "manifest"), _read_json(args.panel, "panel"))
    except ReceiptError as exc:
        print(f"FIDELITY ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
