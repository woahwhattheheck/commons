#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed active-seam companion to :mod:`titan_regression_gate`.

This command binds canonical packaged bytes to exact paired execution evidence.
It does not estimate leaderboard score or modify canonical state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from titan_regression_gate import GateError, audit_current
from titan_active_evidence import compare_active_ledgers
from titan_runtime_closure import audit_runtime_archive


def _issue(code: str, message: str, **details: Any) -> dict[str, Any]:
    row: dict[str, Any] = {"code": code, "message": message}
    if details:
        row["details"] = details
    return row

def _write_report(report: Mapping[str, Any], target: str | None) -> None:
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if target:
        Path(target).write_text(encoded, encoding="utf-8")
    print(encoded, end="")

def _load_object(path: str | Path, label: str) -> Mapping[str, Any]:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GateError(f"missing {label}: {source}") from exc
    except json.JSONDecodeError as exc:
        raise GateError(f"invalid JSON in {label} {source}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise GateError(f"{label} must be a JSON object")
    return value

def audit_active_current(
    root: str | Path,
    *,
    require_games: bool = False,
    import_entrypoint: bool = True,
    import_timeout: float = 8.0,
) -> dict[str, Any]:
    """Run canonical provenance audit and packaged runtime closure together."""
    root_path = Path(root).resolve()
    base = audit_current(root_path, require_games=require_games)
    runtime: dict[str, Any] | None = None
    blockers = list(base.get("blockers", []))
    receipt = base.get("canonical_archive")
    if isinstance(receipt, Mapping):
        archive_rel = receipt.get("path")
        entrypoint = receipt.get("entrypoint", "main.py::agent")
        if isinstance(archive_rel, str) and isinstance(entrypoint, str):
            archive_path = (root_path / archive_rel).resolve()
            try:
                archive_path.relative_to(root_path)
            except ValueError:
                blockers.append(_issue(
                    "CANONICAL_ARCHIVE_ESCAPES_ROOT",
                    "canonical archive receipt resolves outside the audited root",
                    path=str(archive_path),
                ))
            else:
                runtime = audit_runtime_archive(
                    archive_path,
                    entrypoint=entrypoint,
                    import_entrypoint=import_entrypoint,
                    import_timeout=import_timeout,
                )
                blockers.extend(runtime.get("blockers", []))
        else:
            blockers.append(_issue(
                "RUNTIME_RECEIPT_INCOMPLETE",
                "canonical receipt cannot identify runtime archive and entrypoint",
            ))
    else:
        blockers.append(_issue(
            "RUNTIME_RECEIPT_UNAVAILABLE",
            "canonical provenance audit did not expose an archive receipt",
        ))

    runtime_ready = runtime is not None and runtime.get("verdict") == "PASS"
    integrity_ready = bool(base.get("integrity_ready")) and runtime_ready and not blockers
    promotion_ready = bool(base.get("promotion_ready")) and runtime_ready and not blockers
    return {
        "schema_version": 2,
        "verdict": "PASS" if not blockers and base.get("verdict") == "PASS" else "BLOCKED",
        "integrity_ready": integrity_ready,
        "promotion_ready": promotion_ready,
        "require_games": require_games,
        "base_audit": base,
        "runtime_closure": runtime,
        "blockers": blockers,
        "notes": list(base.get("notes", [])) + (list(runtime.get("notes", [])) if runtime else []),
    }

def admit_current(
    root: str | Path,
    baseline_ledger: Mapping[str, Any],
    candidate_ledger: Mapping[str, Any],
    *,
    require_games: bool = True,
    import_entrypoint: bool = True,
    import_timeout: float = 8.0,
    require_identical_panel: bool = True,
    require_action_change: bool = True,
    require_causal_activation: bool = True,
    require_execution_provenance: bool = True,
    reject_outcome_regressions: bool = True,
    require_cash: bool = False,
    min_mean_margin_delta: float | None = 0.0,
    min_median_margin_delta: float | None = 0.0,
    min_opponent_seat_mean_margin_delta: float | None = 0.0,
    min_seed_mean_margin_delta: float | None = None,
    min_mean_cash_delta: float | None = None,
    min_opponent_seat_mean_cash_delta: float | None = None,
) -> dict[str, Any]:
    """Bind canonical bytes, runtime closure, and active paired evidence."""
    audit = audit_active_current(
        root,
        require_games=require_games,
        import_entrypoint=import_entrypoint,
        import_timeout=import_timeout,
    )
    comparison = compare_active_ledgers(
        baseline_ledger,
        candidate_ledger,
        require_identical_panel=require_identical_panel,
        require_action_change=require_action_change,
        require_causal_activation=require_causal_activation,
        require_execution_provenance=require_execution_provenance,
        reject_outcome_regressions=reject_outcome_regressions,
        require_cash=require_cash,
        min_mean_margin_delta=min_mean_margin_delta,
        min_median_margin_delta=min_median_margin_delta,
        min_opponent_seat_mean_margin_delta=min_opponent_seat_mean_margin_delta,
        min_seed_mean_margin_delta=min_seed_mean_margin_delta,
        min_mean_cash_delta=min_mean_cash_delta,
        min_opponent_seat_mean_cash_delta=min_opponent_seat_mean_cash_delta,
    )
    blockers = list(audit.get("blockers", [])) + list(comparison.get("blockers", []))

    canonical_sha: str | None = None
    base_audit = audit.get("base_audit")
    if isinstance(base_audit, Mapping):
        receipt = base_audit.get("canonical_archive")
        if isinstance(receipt, Mapping) and isinstance(receipt.get("sha256"), str):
            canonical_sha = receipt["sha256"]
    candidate_sha = comparison.get("right_archive_sha256")
    if canonical_sha is None or candidate_sha != canonical_sha:
        blockers.append(_issue(
            "CANDIDATE_LEDGER_NOT_CANONICAL",
            "paired candidate evidence is not bound to the canonical archive",
            canonical_archive_sha256=canonical_sha,
            candidate_ledger_sha256=candidate_sha,
        ))

    return {
        "schema_version": 2,
        "verdict": "PASS" if not blockers else "BLOCKED",
        "canonical_archive_sha256": canonical_sha,
        "active_audit": audit,
        "active_comparison": comparison,
        "blockers": blockers,
    }

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit", help="audit canonical evidence and packaged runtime closure")
    audit.add_argument("--root", default=".")
    audit.add_argument("--require-games", action="store_true")
    audit.add_argument("--compile-only", action="store_true")
    audit.add_argument("--import-timeout", type=float, default=8.0)
    audit.add_argument("--report-json")

    compare = sub.add_parser("compare", help="compare paired margin, action, and cash evidence")
    compare.add_argument("--left", required=True)
    compare.add_argument("--right", required=True)
    compare.add_argument("--allow-partial-panel", action="store_true")
    compare.add_argument("--allow-dormant", action="store_true")
    compare.add_argument("--allow-action-only", action="store_true")
    compare.add_argument("--allow-unbound-execution", action="store_true")
    compare.add_argument("--allow-outcome-regression", action="store_true")
    compare.add_argument("--require-cash", action="store_true")
    compare.add_argument("--min-mean-margin-delta", type=float, default=0.0)
    compare.add_argument("--min-median-margin-delta", type=float, default=0.0)
    compare.add_argument("--min-opponent-seat-mean-margin-delta", type=float, default=0.0)
    compare.add_argument("--min-seed-mean-margin-delta", type=float)
    compare.add_argument("--min-mean-cash-delta", type=float)
    compare.add_argument("--min-opponent-seat-mean-cash-delta", type=float)
    compare.add_argument("--report-json")

    admit = sub.add_parser("admit", help="bind canonical bytes to active paired evidence")
    admit.add_argument("--root", default=".")
    admit.add_argument("--baseline-ledger", required=True)
    admit.add_argument("--candidate-ledger", required=True)
    admit.add_argument("--allow-no-games", action="store_true")
    admit.add_argument("--compile-only", action="store_true")
    admit.add_argument("--import-timeout", type=float, default=8.0)
    admit.add_argument("--allow-partial-panel", action="store_true")
    admit.add_argument("--allow-dormant", action="store_true")
    admit.add_argument("--allow-action-only", action="store_true")
    admit.add_argument("--allow-unbound-execution", action="store_true")
    admit.add_argument("--allow-outcome-regression", action="store_true")
    admit.add_argument("--require-cash", action="store_true")
    admit.add_argument("--min-mean-margin-delta", type=float, default=0.0)
    admit.add_argument("--min-median-margin-delta", type=float, default=0.0)
    admit.add_argument("--min-opponent-seat-mean-margin-delta", type=float, default=0.0)
    admit.add_argument("--min-seed-mean-margin-delta", type=float)
    admit.add_argument("--min-mean-cash-delta", type=float)
    admit.add_argument("--min-opponent-seat-mean-cash-delta", type=float)
    admit.add_argument("--report-json")
    return parser

def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "audit":
            report = audit_active_current(
                args.root,
                require_games=args.require_games,
                import_entrypoint=not args.compile_only,
                import_timeout=args.import_timeout,
            )
        elif args.command == "compare":
            report = compare_active_ledgers(
                _load_object(args.left, "left ledger"),
                _load_object(args.right, "right ledger"),
                require_identical_panel=not args.allow_partial_panel,
                require_action_change=not args.allow_dormant,
                require_causal_activation=not args.allow_action_only,
                require_execution_provenance=not args.allow_unbound_execution,
                reject_outcome_regressions=not args.allow_outcome_regression,
                require_cash=args.require_cash,
                min_mean_margin_delta=args.min_mean_margin_delta,
                min_median_margin_delta=args.min_median_margin_delta,
                min_opponent_seat_mean_margin_delta=(
                    args.min_opponent_seat_mean_margin_delta
                ),
                min_seed_mean_margin_delta=args.min_seed_mean_margin_delta,
                min_mean_cash_delta=args.min_mean_cash_delta,
                min_opponent_seat_mean_cash_delta=(
                    args.min_opponent_seat_mean_cash_delta
                ),
            )
        else:
            report = admit_current(
                args.root,
                _load_object(args.baseline_ledger, "baseline ledger"),
                _load_object(args.candidate_ledger, "candidate ledger"),
                require_games=not args.allow_no_games,
                import_entrypoint=not args.compile_only,
                import_timeout=args.import_timeout,
                require_identical_panel=not args.allow_partial_panel,
                require_action_change=not args.allow_dormant,
                require_causal_activation=not args.allow_action_only,
                require_execution_provenance=not args.allow_unbound_execution,
                reject_outcome_regressions=not args.allow_outcome_regression,
                require_cash=args.require_cash,
                min_mean_margin_delta=args.min_mean_margin_delta,
                min_median_margin_delta=args.min_median_margin_delta,
                min_opponent_seat_mean_margin_delta=(
                    args.min_opponent_seat_mean_margin_delta
                ),
                min_seed_mean_margin_delta=args.min_seed_mean_margin_delta,
                min_mean_cash_delta=args.min_mean_cash_delta,
                min_opponent_seat_mean_cash_delta=(
                    args.min_opponent_seat_mean_cash_delta
                ),
            )
        _write_report(report, args.report_json)
        return 0 if report.get("verdict") in {"PASS", "ACTIVE_COMPARABLE"} else 2
    except GateError as exc:
        report = {"schema_version": 2, "verdict": "REFUSED", "error": str(exc)}
        _write_report(report, getattr(args, "report_json", None))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
