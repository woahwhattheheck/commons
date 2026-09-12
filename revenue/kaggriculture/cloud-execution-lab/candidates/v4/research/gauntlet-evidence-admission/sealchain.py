#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compose existing TITAN V4 gauntlet trust oracles into one admission receipt.

SEALCHAIN is intentionally not a runner, evaluator, scheduler, or promotion rule.
It verifies exact current authority source bytes, invokes those authorities, then
checks that their identities and coverage agree before emitting one deterministic
machine-readable certificate.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from typing import Any, Iterable, Mapping

SCHEMA = "titan.gauntlet.sealchain.v1"

# Git blob ids of the reviewed current-main authority implementations. A source
# edit is a contract change: SEALCHAIN fails closed until these pins are reviewed.
AUTHORITY_PINS = {
    "chainlock": {
        "path": "research/agent-index-predictability/bind_result_provenance.py",
        "git_blob": "1d5211e39af26f06f49e050ae127fde9fc8a7873",
    },
    "quietbox": {
        "path": "research/gauntlet-contention/quietbox_gate.py",
        "git_blob": "f69cba703a97d892d447995b61f5f6c9e3937c91",
    },
    "spectrum": {
        "path": "research/gauntlet-panel-diversity/panel_diversity.py",
        "git_blob": "68bac86adf100e3e1941a71a2185c50ae059591a",
    },
    "cohort": {
        "path": "research/replay-loss-autopsy/gauntlet_audit.py",
        "git_blob": "73e3fc9d2da365159f7f1b2be6fa6240142cb493",
    },
}

QUIETBOX_AUTHORITY_DEFAULTS = {
    "exact_coverage": True,
    "max_abs_drift": 100.0,
    "max_mean_abs_drift": 50.0,
    "max_mean_bias": 50.0,
    "claimed_edge": None,
    "max_noise_fraction": 0.25,
    "min_pairs": 2,
    "require_both_seats": True,
    "seat_index": 2,
}


class SealError(ValueError):
    """Input or authority mismatch that makes admission non-certifiable."""


def _git_blob_id(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise SealError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value: str) -> None:
    raise SealError(f"non-finite JSON constant: {value}")


def loads_strict(text: str, label: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except SealError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise SealError(f"{label}: invalid JSON: {exc}") from exc


def load_strict(path: str | Path, label: str) -> Any:
    try:
        return loads_strict(Path(path).read_text(encoding="utf-8"), label)
    except OSError as exc:
        raise SealError(f"{label}: cannot read {path}: {exc}") from exc


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SealError(f"{label} must be a finite number")
    try:
        out = float(value)
    except (OverflowError, ValueError) as exc:
        raise SealError(f"{label} must be finite") from exc
    if not math.isfinite(out):
        raise SealError(f"{label} must be finite")
    return out


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"sealchain_authority_{name}", path)
    if spec is None or spec.loader is None:
        raise SealError(f"cannot import authority {name}: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise SealError(f"authority {name} import failed: {exc}") from exc
    return module


def load_authorities(v4_root: str | Path) -> tuple[dict[str, ModuleType], dict[str, Any]]:
    root = Path(v4_root)
    try:
        root_resolved = root.resolve(strict=True)
    except OSError as exc:
        raise SealError(f"V4 root unavailable: {root}: {exc}") from exc
    if root.is_symlink() or not root_resolved.is_dir():
        raise SealError("V4 root must be a real directory, not a symlink")

    modules: dict[str, ModuleType] = {}
    receipt: dict[str, Any] = {}
    for name, pin in AUTHORITY_PINS.items():
        path = root / pin["path"]
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root_resolved)
        except (OSError, ValueError) as exc:
            raise SealError(f"authority {name} escapes/misses V4 root: {path}") from exc
        if path.is_symlink() or not resolved.is_file():
            raise SealError(f"authority {name} must be a regular non-symlink file")
        data = resolved.read_bytes()
        blob = _git_blob_id(data)
        if blob != pin["git_blob"]:
            raise SealError(
                f"authority {name} source drift: expected Git blob {pin['git_blob']}, got {blob}"
            )
        receipt[name] = {
            "path": pin["path"],
            "git_blob": blob,
            "sha256": _sha256(data),
            "bytes": len(data),
        }
        modules[name] = _load_module(name, resolved)
    return modules, receipt


def _opponent_map(receipt: Mapping[str, Any], label: str) -> dict[str, str]:
    rows = receipt.get("opponents")
    if not isinstance(rows, list) or not rows:
        raise SealError(f"{label}: CHAINLOCK receipt has no opponents")
    out: dict[str, str] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SealError(f"{label}.opponents[{i}] must be an object")
        name = row.get("artifact")
        sha = row.get("sha256")
        if not isinstance(name, str) or not name or name in out:
            raise SealError(f"{label}: invalid/duplicate opponent artifact {name!r}")
        if not isinstance(sha, str) or len(sha) != 64:
            raise SealError(f"{label}: invalid opponent sha256 for {name!r}")
        out[name] = sha
    return out


def _bind_one(
    chainlock: ModuleType,
    *,
    candidate: Path,
    engine: Path,
    opponent_root: Path,
    raw_results: Path,
    label: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    try:
        raw_rows = chainlock._read_jsonl(raw_results)
        ledger, analyzer, receipt = chainlock.bind_results(
            candidate_path=candidate,
            engine_path=engine,
            opponent_root=opponent_root,
            rows=raw_rows,
        )
    except Exception as exc:
        raise SealError(f"{label}: CHAINLOCK rejected results: {exc}") from exc
    if receipt.get("verdict") != "PASS":
        raise SealError(f"{label}: CHAINLOCK did not return PASS")
    if receipt.get("score_ceiling_applied") is not False:
        raise SealError(f"{label}: unexpected score ceiling semantics")
    return raw_rows, ledger, analyzer, receipt


def _quietbox_rows(chainlock: ModuleType, rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        try:
            seat, _candidate, _opponent, margin = chainlock._derived_outcome(row, index)
            seed = chainlock._seed(row.get("environment_seed"), f"row {index} environment_seed")
            replicate = chainlock._strict_int(
                row.get("replicate", 0), f"row {index} replicate", minimum=0
            )
        except Exception as exc:
            raise SealError(f"cannot adapt CHAINLOCK row {index} to QUIETBOX: {exc}") from exc
        artifact = row.get("opponent_artifact")
        if not isinstance(artifact, str) or not artifact:
            raise SealError(f"row {index}: missing opponent_artifact")
        out.append(
            {
                "opponent": artifact,
                "seed": seed,
                "seat": seat,
                "replicate": replicate,
                "margin": margin,
                "status": "complete",
            }
        )
    return out


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(dict(row), sort_keys=True, allow_nan=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def run_quietbox(
    quietbox: ModuleType,
    chainlock: ModuleType,
    quiet_rows: list[dict[str, Any]],
    loaded_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, str]]:
    qrows = _quietbox_rows(chainlock, quiet_rows)
    lrows = _quietbox_rows(chainlock, loaded_rows)
    with tempfile.TemporaryDirectory(prefix="titan-sealchain-") as td:
        qpath = Path(td) / "quiet.jsonl"
        lpath = Path(td) / "loaded.jsonl"
        _write_jsonl(qpath, qrows)
        _write_jsonl(lpath, lrows)
        try:
            quiet = quietbox.load_jsonl(qpath, None, None)
            loaded = quietbox.load_jsonl(lpath, None, None)
            report = quietbox.evaluate(quiet, loaded, **QUIETBOX_AUTHORITY_DEFAULTS)
        except Exception as exc:
            raise SealError(f"QUIETBOX rejected bound panels: {exc}") from exc
        hashes = {"quiet_sha256": quietbox.sha256_file(qpath), "loaded_sha256": quietbox.sha256_file(lpath)}
    if report.get("certified") is not True or report.get("failures"):
        raise SealError(f"QUIETBOX contention certificate failed: {report.get('failures')}")
    return report, hashes


def _aggregate_spectrum_results(
    chainlock: ModuleType,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        artifact = row.get("opponent_artifact")
        if not isinstance(artifact, str) or not artifact:
            raise SealError(f"row {index}: invalid opponent_artifact")
        try:
            _seat, _candidate, _opponent, margin = chainlock._derived_outcome(row, index)
        except Exception as exc:
            raise SealError(f"row {index}: invalid outcome for SPECTRUM: {exc}") from exc
        bucket = grouped.setdefault(
            artifact,
            {"opponent_id": artifact, "wins": 0, "losses": 0, "draws": 0, "margin_sum": 0.0},
        )
        if margin > 0:
            bucket["wins"] += 1
        elif margin < 0:
            bucket["losses"] += 1
        else:
            bucket["draws"] += 1
        bucket["margin_sum"] = _finite(bucket["margin_sum"] + margin, f"{artifact}.margin_sum")
    return {"schema": "titan.gauntlet.results.v1", "rows": [grouped[k] for k in sorted(grouped)]}


def _enforce_panel_source_binding(
    spectrum: ModuleType,
    panel_raw: Any,
    opponent_artifacts: Mapping[str, str],
) -> dict[str, Any]:
    try:
        panel = spectrum.validate_panel(panel_raw)
    except Exception as exc:
        raise SealError(f"SPECTRUM panel rejected: {exc}") from exc
    panel_rows = panel["opponents"]
    ids = {row["id"] for row in panel_rows}
    if ids != set(opponent_artifacts):
        missing = sorted(set(opponent_artifacts) - ids)
        extra = sorted(ids - set(opponent_artifacts))
        raise SealError(f"panel/opponent artifact mismatch: missing={missing}, extra={extra}")
    digest_identity: dict[str, tuple[str, str]] = {}
    source_digest: dict[str, str] = {}
    for row in panel_rows:
        if row["status"] != "resolved":
            raise SealError(f"authoritative admission forbids unresolved panel id {row['id']!r}")
        digest = opponent_artifacts[row["id"]]
        identity = (row["family"], row["source_id"])
        prior = digest_identity.get(digest)
        if prior is not None and prior != identity:
            raise SealError(
                f"identical opponent bytes {digest} claim conflicting family/source identities: {prior} vs {identity}"
            )
        digest_identity[digest] = identity
        prior_digest = source_digest.get(row["source_id"])
        if prior_digest is not None and prior_digest != digest:
            raise SealError(
                f"source_id {row['source_id']!r} maps to multiple exact opponent digests"
            )
        source_digest[row["source_id"]] = digest
    return panel


def run_spectrum(
    spectrum: ModuleType,
    chainlock: ModuleType,
    panel_raw: Any,
    quiet_rows: list[dict[str, Any]],
    opponent_artifacts: Mapping[str, str],
) -> dict[str, Any]:
    panel = _enforce_panel_source_binding(spectrum, panel_raw, opponent_artifacts)
    results = _aggregate_spectrum_results(chainlock, quiet_rows)
    try:
        report = spectrum.analyze(panel, results)
    except Exception as exc:
        raise SealError(f"SPECTRUM analysis failed: {exc}") from exc
    if report.get("authoritative_family_weighting") is not True:
        raise SealError(f"SPECTRUM not authoritative: {report.get('blocking_reasons')}")
    return report


def run_cohort_if_supplied(
    cohort: ModuleType,
    cohort_input: Path | None,
    *,
    candidate_sha256: str,
    engine_sha256: str,
    opponent_sha256s: set[str],
) -> dict[str, Any] | None:
    if cohort_input is None:
        return None
    raw = load_strict(cohort_input, "COHORT input")
    if not isinstance(raw, dict) or raw.get("schema") != "titan.gauntlet.paired.v1":
        raise SealError("COHORT input must be titan.gauntlet.paired.v1 for authoritative composition")
    artifacts = raw.get("artifacts")
    if not isinstance(artifacts, dict) or artifacts.get("candidate") != candidate_sha256:
        raise SealError("COHORT candidate artifact does not match CHAINLOCK candidate")
    if raw.get("engine_sha256") != engine_sha256:
        raise SealError("COHORT engine does not match CHAINLOCK engine")
    cells = raw.get("cells")
    if not isinstance(cells, list) or not cells:
        raise SealError("COHORT paired input has no cells")
    for i, cell in enumerate(cells):
        if not isinstance(cell, dict) or cell.get("opponent_sha256") not in opponent_sha256s:
            raise SealError(f"COHORT cell {i} opponent is outside CHAINLOCK opponent set")
    try:
        report = cohort.audit(raw)
    except Exception as exc:
        raise SealError(f"COHORT rejected paired audit: {exc}") from exc
    if report.get("mode") != "planned_paired":
        raise SealError("COHORT did not produce planned_paired audit")
    if report.get("coverage_complete") is not True or report.get("runtime_clean") is not True:
        raise SealError("COHORT paired audit is incomplete, failed, or contains fallbacks")
    return report


def certify(
    *,
    v4_root: Path,
    candidate: Path,
    engine: Path,
    opponent_root: Path,
    quiet_results: Path,
    loaded_results: Path,
    panel_path: Path,
    cohort_input: Path | None,
) -> dict[str, Any]:
    modules, authority_sources = load_authorities(v4_root)
    q_raw, q_ledger, _q_analyzer, q_receipt = _bind_one(
        modules["chainlock"],
        candidate=candidate,
        engine=engine,
        opponent_root=opponent_root,
        raw_results=quiet_results,
        label="quiet",
    )
    l_raw, l_ledger, _l_analyzer, l_receipt = _bind_one(
        modules["chainlock"],
        candidate=candidate,
        engine=engine,
        opponent_root=opponent_root,
        raw_results=loaded_results,
        label="loaded",
    )

    q_candidate = q_receipt["candidate"]["sha256"]
    q_engine = q_receipt["engine"]["sha256"]
    if l_receipt["candidate"]["sha256"] != q_candidate:
        raise SealError("quiet/loaded candidate artifact mismatch")
    if l_receipt["engine"]["sha256"] != q_engine:
        raise SealError("quiet/loaded engine artifact mismatch")
    q_opponents = _opponent_map(q_receipt, "quiet")
    l_opponents = _opponent_map(l_receipt, "loaded")
    if q_opponents != l_opponents:
        raise SealError("quiet/loaded opponent artifact identities differ")

    quietbox_report, bound_jsonl_hashes = run_quietbox(
        modules["quietbox"], modules["chainlock"], q_raw, l_raw
    )
    panel_raw = load_strict(panel_path, "SPECTRUM panel")
    spectrum_report = run_spectrum(
        modules["spectrum"], modules["chainlock"], panel_raw, q_raw, q_opponents
    )
    cohort_report = run_cohort_if_supplied(
        modules["cohort"],
        cohort_input,
        candidate_sha256=q_candidate,
        engine_sha256=q_engine,
        opponent_sha256s=set(q_opponents.values()),
    )

    # Cross-check the independently produced CHAINLOCK panels are coordinate-equivalent.
    q_rows = q_ledger.get("rows", [])
    l_rows = l_ledger.get("rows", [])
    q_coords = {(r.get("environment_seed"), r.get("opponent_sha256"), r.get("seat")) for r in q_rows}
    l_coords = {(r.get("environment_seed"), r.get("opponent_sha256"), r.get("seat")) for r in l_rows}
    if q_coords != l_coords or len(q_coords) != len(q_rows) or len(l_coords) != len(l_rows):
        raise SealError("quiet/loaded CHAINLOCK coordinate sets differ or contain collisions")

    panel_section = spectrum_report.get("panel", {})
    certificate = {
        "schema": SCHEMA,
        "admitted": True,
        "authority_sources": authority_sources,
        "candidate_sha256": q_candidate,
        "engine_sha256": q_engine,
        "opponent_artifacts": [
            {"artifact": name, "sha256": sha} for name, sha in sorted(q_opponents.items())
        ],
        "chainlock": {
            "quiet_panel_sha256": q_receipt["panel_sha256"],
            "loaded_panel_sha256": l_receipt["panel_sha256"],
            "quiet_rows": q_receipt["rows"],
            "loaded_rows": l_receipt["rows"],
            "paired_cells": q_receipt["paired_cells"],
            "score_ceiling_applied": False,
        },
        "quietbox": {
            "certified": True,
            "aligned_pairs": quietbox_report.get("aligned_pairs"),
            "max_abs_drift": quietbox_report.get("max_abs_drift"),
            "mean_abs_drift": quietbox_report.get("mean_abs_drift"),
            "mean_signed_bias": quietbox_report.get("mean_signed_bias"),
            "authority_defaults": dict(QUIETBOX_AUTHORITY_DEFAULTS),
            **bound_jsonl_hashes,
        },
        "spectrum": {
            "authoritative_family_weighting": True,
            "observed_labels": panel_section.get("observed_labels"),
            "unique_families": panel_section.get("unique_families"),
            "unique_sources": panel_section.get("unique_sources"),
            "unresolved_labels": panel_section.get("unresolved_labels"),
            "family_balanced": (spectrum_report.get("results") or {}).get("family_balanced"),
        },
        "cohort": (
            {
                "applicable": True,
                "runtime_clean": True,
                "complete_pairs": cohort_report.get("complete_pairs"),
                "expected_games": cohort_report.get("expected_games"),
                "observed_games": cohort_report.get("observed_games"),
            }
            if cohort_report is not None
            else {
                "applicable": False,
                "reason": "no titan.gauntlet.paired.v1 baseline/candidate packet supplied",
            }
        ),
        "limits": [
            "SEALCHAIN composes trust/admission evidence only; it is not a gameplay or promotion rule.",
            "QUIETBOX thresholds are the pinned authority defaults, not new SEALCHAIN thresholds.",
            "COHORT is mandatory only when a paired baseline/candidate packet is supplied.",
            "Execution/host attestation beyond the invoked authority contracts is out of scope.",
        ],
    }
    return certificate


def build_parser() -> argparse.ArgumentParser:
    script = Path(__file__).resolve()
    default_root = script.parents[2]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--v4-root", type=Path, default=default_root)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--engine", type=Path, required=True)
    p.add_argument("--opponent-root", type=Path, required=True)
    p.add_argument("--quiet-results", type=Path, required=True)
    p.add_argument("--loaded-results", type=Path, required=True)
    p.add_argument("--panel", type=Path, required=True)
    p.add_argument("--cohort-input", type=Path)
    p.add_argument("--out", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        certificate = certify(
            v4_root=args.v4_root,
            candidate=args.candidate,
            engine=args.engine,
            opponent_root=args.opponent_root,
            quiet_results=args.quiet_results,
            loaded_results=args.loaded_results,
            panel_path=args.panel,
            cohort_input=args.cohort_input,
        )
        rendered = json.dumps(certificate, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 0
    except (OSError, SealError) as exc:
        print(f"SEALCHAIN BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
