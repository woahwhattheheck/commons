"""Fail-closed promotion authority for the legacy TITAN V5 lean-feed carrier.

The legacy Corn/Pasture/Straw oracle remains useful as a synthetic research
instrument, but retained source evidence proves it is not the official D2 model.
This module fences the promotion path without mutating gameplay artifacts.
"""
from __future__ import annotations

import copy
import math
from collections import defaultdict
from typing import Any, Mapping

from lean_feed_core import (
    D2_ARCHIVE_SHA256,
    D2_MEMBER_COUNT,
    EvidenceError,
    _require,
    sha256_json,
)

SOURCE_MODEL_STATE = "SOURCE_MODEL_BLOCKED"
SOURCE_PROMOTION_AUTHORIZED = False
SOURCE_AUTHORITY_RECEIPT_SHA256 = (
    "297f7cf6e38f8e4be7fd00387e228194e366648570b781cd7abe05be41f2d4d8"
)
D2_MAIN_SHA256 = "ae7032281ba680cc70fdfc333bb55cbd4aab7127c277c5150f18746c12f549d3"
OFFICIAL_ENGINE_SHA256 = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
SOURCE_BLOCK_REASON = (
    "retained official source is WHEAT-only and exact D2 archive member bytes "
    "are not retained; legacy fixed-feed economics cannot authorize promotion"
)


def _positive_finite(value: Any, label: str) -> float:
    _require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"{label} must be numeric",
    )
    numeric = float(value)
    _require(math.isfinite(numeric) and numeric > 0, f"{label} must be positive finite")
    return numeric


def validate_promotion_evidence(document: Mapping[str, Any]) -> None:
    """Reject evidence shapes that can manufacture a false promotion."""
    _require(isinstance(document, Mapping), "evidence root must be an object")
    authority = document.get("authority")
    _require(isinstance(authority, Mapping), "authority required")
    _require(
        authority.get("archive_sha256") == D2_ARCHIVE_SHA256,
        "wrong D2 archive SHA-256",
    )
    if "authority_verified" in authority:
        _require(
            authority.get("authority_verified") is False,
            "caller evidence cannot self-mint promotion authority",
        )

    runs = document.get("runs")
    _require(isinstance(runs, list) and runs, "runs must be a non-empty list")

    seen_arm_rows: set[tuple[Any, ...]] = set()
    first_snapshot_by_cell: dict[tuple[Any, ...], dict[str, str]] = defaultdict(dict)

    for run in runs:
        _require(isinstance(run, Mapping), "run must be an object")
        cell = (
            run.get("split"),
            run.get("opponent"),
            run.get("seed"),
            run.get("seat"),
            run.get("pair_id"),
        )
        arm = run.get("arm")
        arm_row = (*cell, arm)
        _require(arm_row not in seen_arm_rows, f"duplicate arm row: {arm_row}")
        seen_arm_rows.add(arm_row)

        windows = run.get("decision_windows")
        _require(isinstance(windows, list) and windows, "decision_windows required")
        first = windows[0]
        _require(isinstance(first, Mapping), "decision window invalid")
        first_snapshot = first.get("snapshot")
        _require(isinstance(first_snapshot, Mapping), "snapshot must be an object")
        first_snapshot_by_cell[cell][str(arm)] = sha256_json(first_snapshot)

        seen_liberation_ids: set[str] = set()
        for window in windows:
            _require(isinstance(window, Mapping), "decision window invalid")
            snapshot = window.get("snapshot")
            _require(isinstance(snapshot, Mapping), "snapshot must be an object")
            decision = window.get("decision")
            _require(isinstance(decision, Mapping), "decision required")

            if decision.get("candidate_active") is True:
                obligations = snapshot.get("obligations")
                _require(isinstance(obligations, list), "obligations must be a list")
                proven = [
                    row
                    for row in obligations
                    if isinstance(row, Mapping)
                    and row.get("source_proven") is True
                    and row.get("executable") is True
                ]
                _require(
                    bool(proven),
                    "active lean window requires a non-empty proven obligation census",
                )
                _require(
                    all(
                        isinstance(row.get("boundary_step"), int)
                        and not isinstance(row.get("boundary_step"), bool)
                        for row in proven
                    ),
                    "active lean window has invalid obligation boundary",
                )

                liberation_id = decision.get("liberation_id")
                _require(
                    isinstance(liberation_id, str) and liberation_id,
                    "active lean window requires liberation_id",
                )
                _require(
                    liberation_id not in seen_liberation_ids,
                    f"reused liberation_id in run: {liberation_id}",
                )
                seen_liberation_ids.add(liberation_id)
                _positive_finite(decision.get("cash_liberated"), "cash_liberated")

                uses = window.get("cash_uses", [])
                _require(isinstance(uses, list), "cash_uses must be a list")
                seen_uses: set[tuple[Any, ...]] = set()
                for use in uses:
                    _require(isinstance(use, Mapping), "cash use invalid")
                    amount = _positive_finite(use.get("amount"), "cash use amount")
                    fingerprint = (
                        use.get("liberation_id"),
                        use.get("step"),
                        use.get("category"),
                        amount,
                    )
                    _require(
                        fingerprint not in seen_uses,
                        "duplicate liberated-cash telemetry event",
                    )
                    seen_uses.add(fingerprint)
            else:
                _require(
                    decision.get("liberation_id") in (None, ""),
                    "inactive decision cannot carry a liberation_id",
                )

    for cell, arm_snapshots in first_snapshot_by_cell.items():
        if len(arm_snapshots) > 1:
            _require(
                len(set(arm_snapshots.values())) == 1,
                f"cross-arm starting snapshot mismatch: {cell}",
            )


def _terminal_evidence_digests(document: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in document.get("runs", []):
        _require(isinstance(raw, Mapping), "run must be an object")
        run_id = raw.get("run_id")
        _require(isinstance(run_id, str) and run_id, "run_id invalid")
        _require(run_id not in result, "duplicate run_id")
        result[run_id] = sha256_json(
            {
                "decision_windows": raw.get("decision_windows"),
                "result": raw.get("result"),
            }
        )
    return result


def apply_source_authority(
    report: Mapping[str, Any], document: Mapping[str, Any]
) -> dict[str, Any]:
    """Bind terminal evidence and enforce the retained non-authorizing source root."""
    hardened = copy.deepcopy(dict(report))
    terminal_digests = _terminal_evidence_digests(document)
    terminal_root = sha256_json(terminal_digests)

    for row in hardened.get("runs", []):
        digest = terminal_digests.get(row.get("run_id"))
        _require(isinstance(digest, str), "report run missing source evidence")
        row["evidence_sha256"] = digest

    promotion = dict(hardened.get("promotion", {}))
    if promotion.get("conclusion") == "PROMOTE_RESEARCH_CANDIDATE":
        legacy_report_sha = hardened.get("report_sha256")
        hardened["authority"] = {
            "archive_sha256": D2_ARCHIVE_SHA256,
            "archive_member_count": D2_MEMBER_COUNT,
            "main_sha256": D2_MAIN_SHA256,
            "official_engine_sha256": OFFICIAL_ENGINE_SHA256,
            "authority_verified": False,
            "source_model_state": SOURCE_MODEL_STATE,
            "source_promotion_authorized": SOURCE_PROMOTION_AUTHORIZED,
            "source_authority_receipt_sha256": SOURCE_AUTHORITY_RECEIPT_SHA256,
            "terminal_evidence_root_sha256": terminal_root,
            "legacy_candidate_report_sha256": legacy_report_sha,
        }
        hardened["design"] = {
            "cells": 0,
            "dev_opponents": [],
            "holdout_opponents": [],
        }
        hardened["promotion"] = {
            "conclusion": SOURCE_MODEL_STATE,
            "selected_arm": None,
            "legacy_candidate_conclusion": "PROMOTE_RESEARCH_CANDIDATE",
            "dev_mean_delta_m": 0.0,
            "holdout_mean_delta_m": 0.0,
            "active_dev_windows": 0,
            "active_holdout_windows": 0,
            "dev_downstream_cash_used": 0.0,
            "holdout_downstream_cash_used": 0.0,
            "obligation_failures": 0,
            "productivity_loss": 0.0,
            "survival_loss": 0.0,
            "strata": [],
            "falsifiers": [SOURCE_BLOCK_REASON],
        }
        hardened["census"] = []
        hardened["paired_deltas"] = []
        hardened["runs"] = []
    else:
        authority = dict(hardened.get("authority", {}))
        authority.update(
            {
                "authority_verified": False,
                "source_model_state": SOURCE_MODEL_STATE,
                "source_promotion_authorized": SOURCE_PROMOTION_AUTHORIZED,
                "source_authority_receipt_sha256": SOURCE_AUTHORITY_RECEIPT_SHA256,
                "terminal_evidence_root_sha256": terminal_root,
            }
        )
        hardened["authority"] = authority

    hardened.pop("report_sha256", None)
    hardened["report_sha256"] = sha256_json(hardened)
    return hardened
