#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pinned, observation-only CURRENT-V5 boundary for atomic PLANT quorum relief.

This module never selects gameplay. It authenticates the already-landed #12954
theorem plus the official engine rule, then evaluates the theorem on a deep copy.
The caller receives the exact original action as control and a detached witness
for the hypothetical candidate. A preloaded authority API lets the current-V5
archive census authenticate once per cell instead of rereading mutable checkout
paths on every callback.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import types
from typing import Any, Mapping

HERE = Path(__file__).resolve()
LAB_ROOT = HERE.parents[3]
THEOREM_REL = Path("candidates/v4/research/unit-phase-chaining/plant_quorum_admission.py")
ENGINE_REL = Path("reference/engine/kaggriculture.py")
PINNED_THEOREM_BLOB = "15c24fbe305dfb7b4b1b2c39897af4af9b49f31f"
PINNED_ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
WITNESS_SCHEMA = "titan-v5-plantquorum-natural-census/v1"
_ENGINE_MARKERS = (
    "# Atomic PLANT validation: if total PLANT requests for a crop this turn",
    'plant_demand[a[1]] = plant_demand.get(a[1], 0) + 1',
    'blocked = {crop for crop, n in plant_demand.items() if n > seeds.get(crop, 0)}',
    'if isinstance(a, list) and len(a) >= 2 and a[0] == "PLANT" and a[1] in blocked:',
    'return ["PASS"]',
)


class CensusError(RuntimeError):
    """Pinned source/engine authority or theorem behavior is unsafe."""


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_snapshot(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise CensusError(f"cannot read {label}: {path}") from exc


def load_authority(
    root: Path = LAB_ROOT,
    *,
    theorem_path: Path | None = None,
    engine_path: Path | None = None,
) -> tuple[types.ModuleType, dict[str, str]]:
    """Authenticate exact theorem + engine bytes before executing theorem source.

    ``theorem_path``/``engine_path`` let an archive-bound census combine the
    canonical theorem checkout bytes with the exact engine bytes captured from
    the authenticated current runtime. Both are read exactly once before use.
    """
    if theorem_path is None or engine_path is None:
        root = Path(root).resolve(strict=True)
    theorem_path = (
        root / THEOREM_REL if theorem_path is None else Path(theorem_path).resolve(strict=True)
    )
    engine_path = (
        root / ENGINE_REL if engine_path is None else Path(engine_path).resolve(strict=True)
    )
    theorem_raw = _read_snapshot(theorem_path, "plant-quorum theorem")
    engine_raw = _read_snapshot(engine_path, "official engine")

    theorem_blob = _git_blob(theorem_raw)
    engine_blob = _git_blob(engine_raw)
    if theorem_blob != PINNED_THEOREM_BLOB:
        raise CensusError(
            f"plant-quorum theorem drift: expected {PINNED_THEOREM_BLOB}, got {theorem_blob}"
        )
    if engine_blob != PINNED_ENGINE_BLOB:
        raise CensusError(
            f"engine drift: expected {PINNED_ENGINE_BLOB}, got {engine_blob}"
        )
    try:
        engine_text = engine_raw.decode("utf-8")
        theorem_text = theorem_raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CensusError("pinned theorem/engine source is not UTF-8") from exc
    missing = [marker for marker in _ENGINE_MARKERS if marker not in engine_text]
    if missing:
        raise CensusError(f"engine atomic-PLANT markers drifted: {missing!r}")

    module = types.ModuleType("_titan_v5_pinned_plantquorum")
    module.__file__ = str(theorem_path)
    try:
        code = compile(theorem_text, str(theorem_path), "exec")
        exec(code, module.__dict__)
    except Exception as exc:
        raise CensusError(f"cannot load pinned plant-quorum theorem: {exc}") from exc
    if getattr(module, "EXPECTED_ENGINE_BLOB", None) != PINNED_ENGINE_BLOB:
        raise CensusError("theorem's embedded engine authority disagrees with census pin")
    for name in ("relieve_atomic_plant_collateral", "effective_rows_under_engine_preflight"):
        if not callable(getattr(module, name, None)):
            raise CensusError(f"pinned theorem lacks {name}")

    return module, {
        "theorem_git_blob": theorem_blob,
        "engine_git_blob": engine_blob,
        "theorem_sha256": hashlib.sha256(theorem_raw).hexdigest(),
        "engine_sha256": hashlib.sha256(engine_raw).hexdigest(),
    }


def _source_rows(action: Mapping[str, Any]) -> list[Any]:
    hands = action.get("hands", [])
    if not isinstance(hands, list):
        hands = []
    return [deepcopy(action.get("farmer", ["PASS"])), *deepcopy(hands)]


def observe_with_authority(
    authority: types.ModuleType,
    provenance: Mapping[str, str],
    observation: Mapping[str, Any],
    returned_action: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Evaluate one returned action without rereading authority or changing gameplay."""
    if not isinstance(observation, Mapping) or not isinstance(returned_action, Mapping):
        raise CensusError("observation and returned_action must be mappings")
    if provenance.get("theorem_git_blob") != PINNED_THEOREM_BLOB:
        raise CensusError("preloaded theorem authority is not canonical")
    if provenance.get("engine_git_blob") != PINNED_ENGINE_BLOB:
        raise CensusError("preloaded engine authority is not canonical")

    source = deepcopy(dict(returned_action))
    source_before = deepcopy(source)
    try:
        candidate, report = authority.relieve_atomic_plant_collateral(
            deepcopy(dict(observation)),
            source,
            enabled=True,
        )
    except Exception as exc:
        raise CensusError(f"pinned plant-quorum theorem raised: {exc}") from exc
    if source != source_before:
        raise CensusError("plant-quorum theorem mutated caller-owned source action")
    if not isinstance(candidate, dict) or not isinstance(report, dict):
        raise CensusError("plant-quorum theorem returned malformed candidate/report")
    changed = report.get("changed")
    if type(changed) is not bool:
        raise CensusError("plant-quorum changed flag is not exact bool")
    if changed == (candidate == source_before):
        raise CensusError("plant-quorum changed flag disagrees with candidate action bytes")

    effective_before = effective_after = None
    if changed:
        private = observation.get("private")
        if not isinstance(private, Mapping):
            raise CensusError("changed witness has no private seed state")
        seeds = private.get("seeds", {})
        try:
            effective_before = authority.effective_rows_under_engine_preflight(
                _source_rows(source_before), seeds
            )
            effective_after = authority.effective_rows_under_engine_preflight(
                _source_rows(candidate), seeds
            )
        except Exception as exc:
            raise CensusError(f"cannot verify engine-effective PLANT witness: {exc}") from exc
        if effective_before == effective_after:
            raise CensusError("changed theorem postimage does not change engine PLANT preflight")
        if not any(
            isinstance(row, list) and len(row) >= 2 and row[0] == "PLANT"
            for row in effective_after
        ):
            raise CensusError("changed theorem postimage leaves no effective PLANT survivor")

    witness = {
        "schema": WITNESS_SCHEMA,
        "changed": changed,
        "source_authority": dict(provenance),
        "original_action_sha256": _canonical_sha256(source_before),
        "candidate_action_sha256": _canonical_sha256(candidate),
        "original_action": deepcopy(source_before),
        "candidate_action": deepcopy(candidate),
        "theorem_report": deepcopy(report),
        "control_action_preserved": True,
        "effective_before": deepcopy(effective_before),
        "effective_after": deepcopy(effective_after),
    }
    return deepcopy(source_before), witness


def observe(
    observation: Mapping[str, Any],
    returned_action: Mapping[str, Any],
    *,
    root: Path = LAB_ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Convenience one-shot observer for source tests and manual probes."""
    authority, provenance = load_authority(root)
    return observe_with_authority(authority, provenance, observation, returned_action)
