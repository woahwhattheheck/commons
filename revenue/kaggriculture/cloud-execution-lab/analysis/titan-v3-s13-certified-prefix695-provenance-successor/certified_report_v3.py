#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Provenance-bound successor for the S13 certified-prefix report.

This layer deliberately leaves certified_report_v2.py byte-identical. It pins
that reviewed builder by Git blob, reuses its gameplay/result math, and adds the
raw evaluator/provenance bindings that v2 did not retain.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping

SCHEMA = "titan-v3-s13-certified-prefix-report/v3"
V2_BLOB = "df35cf41cfa664c2832f54082ce80eb1c2b2bee6"
HERE = Path(__file__).resolve().parent
V2_PATH = (
    HERE.parent
    / "titan-v3-s13-certified-prefix695-custody-closure"
    / "certified_report_v2.py"
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
COMMON_KEYS = (
    "engine_ref",
    "engine_sha256",
    "loader_sha256",
    "opponents",
    "seeds",
    "agent_rng_seed",
    "limits",
    "method",
)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_v2():
    data = V2_PATH.read_bytes()
    actual = git_blob_sha(data)
    if actual != V2_BLOB:
        raise RuntimeError(f"v2 report blob drift: expected={V2_BLOB} actual={actual}")
    name = "titan_s13_certified_report_v2"
    spec = importlib.util.spec_from_file_location(name, V2_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {V2_PATH}")
    module = importlib.util.module_from_spec(spec)
    prior = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if prior is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
    return module


v2 = load_v2()
CertifiedReportError = v2.CertifiedReportError


def _hex64(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise CertifiedReportError(f"{label} is not a lowercase SHA-256")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CertifiedReportError(f"{label} is not an object")
    return value


def _strict_load_bytes(data: bytes, label: str) -> Any:
    """Parse exactly the bytes already captured for custody; never reopen a path."""
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise CertifiedReportError(f"{label}: duplicate JSON key {key!r}")
            out[key] = value
        return out

    def reject(value: str) -> Any:
        raise CertifiedReportError(f"{label}: non-finite JSON constant {value}")

    try:
        text = data.decode("utf-8")
        return json.loads(
            text,
            object_pairs_hook=pairs,
            parse_constant=reject,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CertifiedReportError(f"{label}: invalid evaluator JSON: {exc}") from exc


def _provenance(report: Mapping[str, Any], label: str) -> dict[str, Any]:
    if report.get("schema_version") != 1:
        raise CertifiedReportError(f"{label} evaluator schema_version drift")
    engine_ref = report.get("engine_ref")
    if not isinstance(engine_ref, str) or not engine_ref:
        raise CertifiedReportError(f"{label} engine_ref is absent")
    engine_sha = dict(_mapping(report.get("engine_sha256"), f"{label} engine_sha256"))
    if not engine_sha:
        raise CertifiedReportError(f"{label} engine_sha256 is empty")
    for name, digest in engine_sha.items():
        if not isinstance(name, str) or not name:
            raise CertifiedReportError(f"{label} engine source name is malformed")
        _hex64(digest, f"{label} engine_sha256[{name!r}]")
    loader_sha = _hex64(report.get("loader_sha256"), f"{label} loader_sha256")
    evaluator_sha = _hex64(report.get("evaluator_sha256"), f"{label} evaluator_sha256")
    candidate = dict(_mapping(report.get("candidate"), f"{label} candidate"))
    opponents = dict(_mapping(report.get("opponents"), f"{label} opponents"))
    if not opponents:
        raise CertifiedReportError(f"{label} opponents are empty")
    seeds = report.get("seeds")
    if (
        not isinstance(seeds, list)
        or not seeds
        or any(type(seed) is not int for seed in seeds)
        or len(seeds) != len(set(seeds))
    ):
        raise CertifiedReportError(f"{label} seeds are malformed")
    rng_seed = report.get("agent_rng_seed")
    if type(rng_seed) is not int:
        raise CertifiedReportError(f"{label} agent_rng_seed is malformed")
    limits = dict(_mapping(report.get("limits"), f"{label} limits"))
    if not limits:
        raise CertifiedReportError(f"{label} limits are empty")
    for key, value in limits.items():
        if not isinstance(key, str) or not key:
            raise CertifiedReportError(f"{label} limit key is malformed")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise CertifiedReportError(f"{label} limit {key!r} is malformed")
    method = report.get("method")
    if not isinstance(method, str) or not method:
        raise CertifiedReportError(f"{label} method is absent")
    return {
        "engine_ref": engine_ref,
        "engine_sha256": engine_sha,
        "loader_sha256": loader_sha,
        "evaluator_sha256": evaluator_sha,
        "candidate": candidate,
        "opponents": opponents,
        "seeds": list(seeds),
        "agent_rng_seed": rng_seed,
        "limits": limits,
        "method": method,
        "python": report.get("python"),
        "platform": report.get("platform"),
    }


def _same(left: Any, right: Any) -> bool:
    return v2.canonical(left) == v2.canonical(right)


def _bind_inputs(paths: Mapping[str, Path]) -> tuple[dict[str, Any], dict[str, Mapping[str, Any]]]:
    """Read each evaluator path once, then bind digest and parsed object to those bytes."""
    inputs: dict[str, Any] = {}
    loaded: dict[str, Mapping[str, Any]] = {}
    for label, path in paths.items():
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise CertifiedReportError(f"{path}: cannot read evaluator JSON: {exc}") from exc
        value = _strict_load_bytes(data, str(path))
        if not isinstance(value, Mapping):
            raise CertifiedReportError(f"{label} evaluator report is not an object")
        inputs[label] = {
            "path": str(path),
            "bytes": len(data),
            "sha256": sha256_bytes(data),
        }
        loaded[label] = value
    return inputs, loaded


def _validate_cross_arm(prov: Mapping[str, Mapping[str, Any]]) -> None:
    control = prov["control"]
    for label in ("unsafe_prefix", "certified_prefix"):
        for key in COMMON_KEYS:
            if not _same(control[key], prov[label][key]):
                raise CertifiedReportError(
                    f"{label} provenance drift for {key}: does not match control"
                )
    if control["evaluator_sha256"] != prov["unsafe_prefix"]["evaluator_sha256"]:
        raise CertifiedReportError(
            "unsafe_prefix evaluator identity differs from control evaluator"
        )


def _validate_activation_bounds(certified: Mapping[str, Any], source_seat: int) -> None:
    games = certified.get("games")
    if not isinstance(games, list):
        raise CertifiedReportError("certified evaluator report has no games")
    for game in games:
        if not isinstance(game, Mapping):
            raise CertifiedReportError("certified evaluator game is malformed")
        steps = game.get("steps")
        episode_steps = game.get("episode_steps")
        if type(steps) is not int or steps < 1:
            raise CertifiedReportError("certified evaluator executed steps are malformed")
        if type(episode_steps) is not int or episode_steps < steps:
            raise CertifiedReportError("certified evaluator episode_steps are malformed")
        seat = game.get("candidate_seat")
        if seat not in (0, 1):
            raise CertifiedReportError("certified evaluator candidate_seat is malformed")
        actors = game.get("actors")
        if not isinstance(actors, list) or len(actors) != 2:
            raise CertifiedReportError("certified evaluator actors are malformed")
        actor = actors[seat]
        if not isinstance(actor, Mapping):
            raise CertifiedReportError("certified evaluator candidate actor is malformed")
        diag = actor.get("agent_diagnostics")
        if not isinstance(diag, Mapping):
            raise CertifiedReportError("certified candidate runtime diagnostics are absent")
        if diag.get("source_seat") != source_seat:
            raise CertifiedReportError("runtime source-seat binding drift")
        activation_steps = diag.get("activation_steps")
        if not isinstance(activation_steps, list):
            raise CertifiedReportError("runtime activation_steps are malformed")
        for step in activation_steps:
            if type(step) is not int or step < 0 or step >= steps or step >= episode_steps:
                raise CertifiedReportError(
                    f"runtime activation step {step!r} is outside executed game bounds"
                )


def _build_v2_from_loaded(
    loaded: Mapping[str, Mapping[str, Any]],
    *,
    source_seat: int,
    control_label: str,
) -> dict[str, Any]:
    """Run the pinned v2 scientific math over already-captured parsed objects."""
    if source_seat not in (0, 1):
        raise CertifiedReportError("source_seat must be 0 or 1")

    control = v2.cells(loaded["control"])
    unsafe = v2.cells(loaded["unsafe_prefix"])
    certified = v2.cells(
        loaded["certified_prefix"],
        require_runtime_diagnostics=True,
    )
    if set(control) != set(unsafe) or set(control) != set(certified):
        raise CertifiedReportError("the three evaluator banks differ")
    for key, row in certified.items():
        if row["runtime_diagnostics"]["source_seat"] != source_seat:
            raise CertifiedReportError(f"runtime source-seat binding drift at {key!r}")

    unsafe_summary = v2.paired(unsafe, control)
    certified_summary = v2.paired(certified, control)
    retention_rows = []
    for key in sorted(control):
        raw, guarded = unsafe[key], certified[key]
        retention_rows.append(
            {
                "opponent": guarded["opponent"],
                "seed": guarded["seed"],
                "seat": guarded["seat"],
                "own_cash_delta_certified_minus_unsafe": guarded["own_cash"] - raw["own_cash"],
                "margin_delta_certified_minus_unsafe": guarded["margin"] - raw["margin"],
            }
        )

    source_rows = [row for row in certified_summary["rows"] if row["seat"] == source_seat]
    off_rows = [row for row in certified_summary["rows"] if row["seat"] != source_seat]
    if not source_rows or not off_rows:
        raise CertifiedReportError("both candidate seats are required")

    off_seat_exact_fallback = all(
        row["activation_count"] == 0
        and not row["trace_changed"]
        and row["own_cash_delta"] == 0
        and row["margin_delta"] == 0
        for row in off_rows
    )
    source_strata = [
        row for row in certified_summary["strata"] if row["seat"] == source_seat
    ]
    source_safe = bool(
        sum(row["new_loss"] for row in source_rows) == 0
        and v2.mean(row["own_cash_delta"] for row in source_rows) >= 0
        and v2.mean(row["margin_delta"] for row in source_rows) >= 0
        and all(row["mean_margin_delta"] >= 0 for row in source_strata)
    )
    source_activated = any(row["activation_count"] > 0 for row in source_rows)

    if off_seat_exact_fallback and source_safe and source_activated:
        verdict = "CERTIFIED_SURVIVOR"
    elif off_seat_exact_fallback and not source_activated:
        verdict = "CERTIFICATE_REJECTS_TRANSPLANT"
    else:
        verdict = "CERTIFIED_HOLD"

    diagnostic_rows = [
        {
            "opponent": row["opponent"],
            "seed": row["seed"],
            "seat": row["seat"],
            "runtime_diagnostics": row["runtime_diagnostics"],
        }
        for row in certified_summary["rows"]
    ]
    diagnostic_sha = hashlib.sha256(v2.canonical(diagnostic_rows)).hexdigest()
    return {
        "schema": v2.SCHEMA,
        "source_seat": source_seat,
        "control": control_label,
        "unsafe_prefix": unsafe_summary,
        "certified_prefix": certified_summary,
        "certified_vs_unsafe": {
            "rows": retention_rows,
            "mean_own_cash_delta": v2.mean(
                row["own_cash_delta_certified_minus_unsafe"] for row in retention_rows
            ),
            "mean_margin_delta": v2.mean(
                row["margin_delta_certified_minus_unsafe"] for row in retention_rows
            ),
        },
        "runtime_diagnostics_sha256": diagnostic_sha,
        "off_seat_exact_fallback": off_seat_exact_fallback,
        "source_seat_activated": source_activated,
        "source_seat_activation_cells": sum(
            row["activation_count"] > 0 for row in source_rows
        ),
        "source_seat_activation_events": sum(
            row["activation_count"] for row in source_rows
        ),
        "source_seat_safe": source_safe,
        "verdict": verdict,
        "scope": (
            "reused frozen seeds only; activation derives only from retained runtime "
            "emissions; no promotion, provider, Kaggle, or submission mutation"
        ),
    }


def _identities(values: Mapping[str, str]) -> dict[str, str]:
    git_head = values.get("git_head")
    archive_sha256 = values.get("archive_sha256")
    source_manifest_sha256 = values.get("source_manifest_sha256")
    if not isinstance(git_head, str) or HEX40.fullmatch(git_head) is None:
        raise CertifiedReportError("git_head is not a lowercase Git SHA-1")
    _hex64(archive_sha256, "archive_sha256")
    _hex64(source_manifest_sha256, "source_manifest_sha256")
    return {
        "git_head": git_head,
        "archive_sha256": archive_sha256,
        "source_manifest_sha256": source_manifest_sha256,
    }


def _bindings(values: Mapping[str, Path]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, path in sorted(values.items()):
        if re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,63}", name) is None:
            raise CertifiedReportError(f"binding name is malformed: {name!r}")
        data = path.read_bytes()
        out[name] = {"path": str(path), "bytes": len(data), "sha256": sha256_bytes(data)}
    return out


def build_report(
    control_path: Path,
    unsafe_path: Path,
    certified_path: Path,
    *,
    source_seat: int,
    identities: Mapping[str, str],
    bindings: Mapping[str, Path],
) -> dict[str, Any]:
    paths = {
        "control": control_path,
        "unsafe_prefix": unsafe_path,
        "certified_prefix": certified_path,
    }
    input_receipts, loaded = _bind_inputs(paths)
    provenance = {
        label: _provenance(loaded[label], label)
        for label in ("control", "unsafe_prefix", "certified_prefix")
    }
    _validate_cross_arm(provenance)
    _validate_activation_bounds(loaded["certified_prefix"], source_seat)
    base = _build_v2_from_loaded(
        loaded,
        source_seat=source_seat,
        control_label=str(control_path),
    )
    result = dict(base)
    result["schema"] = SCHEMA
    result["v2_report_sha256"] = sha256_bytes(v2.canonical(base))
    result["input_reports"] = input_receipts
    result["evaluator_provenance"] = provenance
    result["identities"] = _identities(identities)
    result["companion_bindings"] = _bindings(bindings)
    result["scope"] = (
        "reused frozen seeds only; v3 binds raw evaluator provenance and companion "
        "artifact identities; activation derives only from bounded retained runtime "
        "emissions; no promotion, provider, Kaggle, or submission mutation"
    )
    return result


def markdown(report: Mapping[str, Any]) -> str:
    base = v2.markdown(report).rstrip()
    ids = report["identities"]
    return "\n".join(
        [
            base,
            "",
            "## Provenance bindings",
            "",
            f"- Git head: `{ids['git_head']}`",
            f"- Archive SHA-256: `{ids['archive_sha256']}`",
            f"- Source-manifest SHA-256: `{ids['source_manifest_sha256']}`",
            f"- v2 report SHA-256: `{report['v2_report_sha256']}`",
            "",
            "Raw control/unsafe/certified report SHA-256 values and evaluator provenance are embedded in the JSON report.",
            "",
        ]
    )


def _parse_bindings(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for item in values:
        name, sep, raw = item.partition("=")
        if not sep or not name or not raw or name in result:
            raise CertifiedReportError("--binding requires unique NAME=PATH")
        result[name] = Path(raw)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--unsafe-prefix", type=Path, required=True)
    parser.add_argument("--certified-prefix", type=Path, required=True)
    parser.add_argument("--source-seat", type=int, required=True)
    parser.add_argument("--git-head", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    parser.add_argument("--binding", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(
        args.control,
        args.unsafe_prefix,
        args.certified_prefix,
        source_seat=args.source_seat,
        identities={
            "git_head": args.git_head,
            "archive_sha256": args.archive_sha256,
            "source_manifest_sha256": args.source_manifest_sha256,
        },
        bindings=_parse_bindings(args.binding),
    )
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
