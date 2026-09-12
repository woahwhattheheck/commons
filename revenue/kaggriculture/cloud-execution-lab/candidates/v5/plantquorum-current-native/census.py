#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pinned, observation-only CURRENT-V5 census shim for atomic PLANT quorum relief.

This module does not alter TITAN's returned action.  It loads the already-landed
#12954 theorem from an authenticated single-read source snapshot, authenticates
the official engine rule from a single-read engine snapshot, and evaluates the
theorem on a deep copy.  The caller receives the exact original action for the
control execution plus a separate witness containing the hypothetical candidate
postimage.  Natural engagement therefore can be measured before any production
hook exists.
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


def load_authority(root: Path = LAB_ROOT) -> tuple[types.ModuleType, dict[str, str]]:
    """Authenticate exact theorem + engine bytes before executing theorem source."""
    root = root.resolve(strict=True)
    theorem_path = root / THEOREM_REL
    engine_path = root / ENGINE_REL
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

    # Execute only the already-authenticated theorem snapshot.  Do not import the
    # live path after authentication; that would reopen a checkout TOCTOU seam.
    module = types.ModuleType("_titan_v5_pinned_plantquorum")
    module.__file__ = str(theorem_path)
    try:
        code = compile(theorem_text, str(theorem_path), "exec")
        exec(code, module.__dict__)
    except Exception as exc:
        raise CensusError(f"cannot load pinned plant-quorum theorem: {exc}") from exc
    if getattr(module, "EXPECTED_ENGINE_BLOB", None) != PINNED_ENGINE_BLOB:
        raise CensusError("theorem's embedded engine authority disagrees with census pin")
    if not callable(getattr(module, "relieve_atomic_plant_collateral", None)):
        raise CensusError("pinned theorem lacks relieve_atomic_plant_collateral")

    return module, {
        "theorem_git_blob": theorem_blob,
        "engine_git_blob": engine_blob,
        "theorem_sha256": hashlib.sha256(theorem_raw).hexdigest(),
        "engine_sha256": hashlib.sha256(engine_raw).hexdigest(),
    }


def observe(
    observation: Mapping[str, Any],
    returned_action: Mapping[str, Any],
    *,
    root: Path = LAB_ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return exact control action plus a separate hypothetical-candidate witness."""
    if not isinstance(observation, Mapping) or not isinstance(returned_action, Mapping):
        raise CensusError("observation and returned_action must be mappings")
    source = deepcopy(dict(returned_action))
    source_before = deepcopy(source)
    authority, provenance = load_authority(root)
    try:
        candidate, report = authority.relieve_atomic_plant_collateral(
            observation,
            source,
            enabled=True,
        )
    except Exception as exc:
        raise CensusError(f"pinned plant-quorum theorem raised: {exc}") from exc
    if source != source_before:
        raise CensusError("plant-quorum theorem mutated caller-owned source action")
    if not isinstance(candidate, dict) or not isinstance(report, dict):
        raise CensusError("plant-quorum theorem returned malformed candidate/report")
    changed = report.get("changed") is True
    if changed == (candidate == source_before):
        raise CensusError("plant-quorum changed flag disagrees with candidate action bytes")

    witness = {
        "schema": WITNESS_SCHEMA,
        "changed": changed,
        "source_authority": provenance,
        "original_action_sha256": _canonical_sha256(source_before),
        "candidate_action_sha256": _canonical_sha256(candidate),
        "original_action": deepcopy(source_before),
        "candidate_action": deepcopy(candidate),
        "theorem_report": deepcopy(report),
        "control_action_preserved": True,
    }
    # Deep-copy again so caller mutation of the control result cannot mutate the
    # witness's authenticated original-action record.
    return deepcopy(source_before), witness
