# SPDX-License-Identifier: Apache-2.0
"""Authenticated convergence gate for recovered submitted-V3.1 R04 behavior.

The gate is intentionally evidence-only.  It never implements gameplay or grants
release/default/submission authority.  "READY" requires two independent custody
classes:

* every declared component head/path must resolve to actual Git object bytes; and
* every PASS economics claim must point at an exact raw paired-cell JSON report.
  The report is read once, SHA-authenticated, strictly parsed, and all panel
  topology / score deltas are recomputed from its cells.

Summary-only evidence is non-authorizing by construction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Protocol, Sequence

SCHEMA = "titan-v5-r04-recovery-composition-gate/v2"
RECEIPT_SCHEMA = "titan-v5-r04-recovery-composition-receipt/v2"
ECONOMICS_REPORT_SCHEMA = "titan-v5-r04-paired-economics-report/v1"

SUBMITTED_V31_SOURCE = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
SUBMITTED_V31_ARCHIVE_SHA256 = (
    "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"
)

REQUIRED_SLOTS = (
    "sale_window_h8_l3",
    "h4_strawberry_topup",
    "row_order",
    "row_shed",
    "evening_flush",
    "b5_carrot_jit",
    "fert_hand_boundary",
    "b9_terminal_fertilizer",
    "h3c_goose_rescue",
    "v231_late_cow",
)

# Historical source topology is provenance, not current runtime staging.  V231-late
# is an independently score-shipped stateful feature; the returned-action order is
# retained exactly rather than being misused as a current integration order.
SUBMITTED_TOPOLOGY = {
    "stateful_controller_features": ["v231_late_cow"],
    "inner_return_pipeline": [
        "sale_window_h8_l3",
        "h4_strawberry_topup",
        "row_order",
        "row_shed",
        "evening_flush",
        "b5_carrot_jit",
    ],
    "around_inner": ["fert_hand_boundary"],
    "outer_return_pipeline": [
        "b9_terminal_fertilizer",
        "h3c_goose_rescue",
    ],
}

# Current V5 has one hot integration seam.  In particular H3c changes unit work
# before capacity projection, row-shed belongs to final market ordering, and B9 is
# post-market.  This is deliberately separate from the historical wrapper order.
CURRENT_RUNTIME_STAGES = {
    "sale_window_h8_l3": "selected_action",
    "h4_strawberry_topup": "selected_action",
    "row_order": "selected_action",
    "row_shed": "final_market_order",
    "evening_flush": "selected_action",
    "b5_carrot_jit": "selected_action",
    "fert_hand_boundary": "selected_action_boundary",
    "b9_terminal_fertilizer": "post_market",
    "h3c_goose_rescue": "pre_capacity",
    "v231_late_cow": "selected_action",
}

FORBIDDEN_ACTIVE_SLOTS = frozenset(
    {
        "cattle_early",
        "kill_late_water",
        "strawberry_endgame",
        "dribble_dump",
        "mirror_horizon",
        "opening_roundtrip",
        "r01_standalone",
        "r02_standalone",
        "r03_standalone",
    }
)
FORBIDDEN_WHOLE_ROUTER_SUFFIXES = (
    "/r04_full_router.py",
    "/r01_tapes.py",
)
ECONOMICS_PASS = "PASS_PAIRED_ECONOMICS"


class GateError(ValueError):
    """Input/evidence is malformed or violates a hard custody invariant."""


class SourceReader(Protocol):
    def commit_exists(self, head_sha: str) -> bool: ...
    def read_file(self, head_sha: str, path: str) -> bytes: ...


class GitSourceReader:
    """Read component source directly from local Git objects, never the worktree."""

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()

    @classmethod
    def discover(cls, start: Path) -> "GitSourceReader":
        proc = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode:
            raise GateError("cannot locate Git repository for source authority")
        return cls(Path(proc.stdout.decode("utf-8").strip()))

    def _git(self, *args: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", "-C", str(self.repo_root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def commit_exists(self, head_sha: str) -> bool:
        return self._git("cat-file", "-e", f"{head_sha}^{{commit}}").returncode == 0

    def read_file(self, head_sha: str, path: str) -> bytes:
        proc = self._git("show", f"{head_sha}:{path}")
        if proc.returncode:
            raise GateError(f"declared source does not exist at carrier head: {path}")
        return bytes(proc.stdout)


def _reject_constant(value: str) -> None:
    raise GateError(f"non-finite JSON constant is forbidden: {value}")


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise GateError(f"duplicate JSON object key: {key}")
        out[key] = value
    return out


def _strict_json(raw: bytes, *, label: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError(f"{label} must be UTF-8 JSON") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_object,
            parse_constant=_reject_constant,
        )
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError(f"{label} is not valid JSON") from exc


def load_manifest_bytes(raw: bytes) -> Mapping[str, Any]:
    value = _strict_json(raw, label="manifest")
    if type(value) is not dict:
        raise GateError("manifest must be a JSON object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], field: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise GateError(f"{field} keys mismatch; missing={missing}, extra={extra}")


def _exact_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise GateError(f"{field} must be an exact JSON boolean")
    return value


def _string(value: Any, field: str) -> str:
    if type(value) is not str or not value:
        raise GateError(f"{field} must be a non-empty string")
    return value


def _sha(value: Any, field: str, length: int) -> str:
    text = _string(value, field)
    if len(text) != length or any(ch not in "0123456789abcdef" for ch in text):
        raise GateError(f"{field} must be a {length}-character lowercase hex digest")
    return text


def _integer(value: Any, field: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise GateError(f"{field} must be an integer >= {minimum}")
    return value


def _number(value: Any, field: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise GateError(f"{field} must be a finite JSON number")
    result = float(value)
    if result != result or result in (float("inf"), float("-inf")):
        raise GateError(f"{field} must be finite")
    return result


def _string_list(value: Any, field: str) -> list[str]:
    if type(value) is not list:
        raise GateError(f"{field} must be a JSON array")
    out = [_string(item, f"{field}[{index}]") for index, item in enumerate(value)]
    if len(set(out)) != len(out):
        raise GateError(f"{field} contains duplicates")
    return out


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _bytes_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def _validate_lineage(manifest: Mapping[str, Any]) -> None:
    _exact_keys(
        manifest,
        {
            "schema",
            "target_version",
            "source_architecture",
            "submitted_v31_authority",
            "v4_thaw",
            "legacy_whole_router_transplant",
            "production_default_flip",
            "release_requested",
            "kaggle_submission_requested",
            "submitted_topology",
            "current_runtime_stages",
            "components",
            "composition_economics",
        },
        "manifest",
    )
    if manifest.get("schema") != SCHEMA:
        raise GateError(f"schema must equal {SCHEMA}")
    if manifest.get("target_version") != "v5":
        raise GateError("target_version must be v5")
    if manifest.get("source_architecture") != "current_v5":
        raise GateError("source_architecture must be current_v5")

    authority = manifest.get("submitted_v31_authority")
    if type(authority) is not dict:
        raise GateError("submitted_v31_authority must be an object")
    _exact_keys(
        authority,
        {"source_commit", "archive_sha256"},
        "submitted_v31_authority",
    )
    if authority.get("source_commit") != SUBMITTED_V31_SOURCE:
        raise GateError("submitted V3.1 source commit mismatch")
    if authority.get("archive_sha256") != SUBMITTED_V31_ARCHIVE_SHA256:
        raise GateError("submitted V3.1 archive mismatch")

    if manifest.get("submitted_topology") != SUBMITTED_TOPOLOGY:
        raise GateError("submitted_topology does not match exact recovery topology")
    if manifest.get("current_runtime_stages") != CURRENT_RUNTIME_STAGES:
        raise GateError("current_runtime_stages does not match V5 staged integration")

    for field in (
        "v4_thaw",
        "legacy_whole_router_transplant",
        "production_default_flip",
        "release_requested",
        "kaggle_submission_requested",
    ):
        if _exact_bool(manifest.get(field), field):
            raise GateError(f"{field} must remain false on convergence carrier")


def _safe_evidence_path(root: Path, raw_path: Any, field: str) -> Path:
    text = _string(raw_path, field)
    candidate = Path(text)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise GateError(f"{field} must be a relative path inside evidence root")
    root = root.resolve()
    path = (root / candidate).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise GateError(f"{field} escapes evidence root") from exc
    if not path.is_file():
        raise GateError(f"{field} does not name an existing regular file")
    return path


def _validate_report(
    economics: Any,
    prefix: str,
    *,
    expected_label: str,
    evidence_root: Path,
    expected_component_source_sha256: str | None = None,
) -> dict[str, Any]:
    if type(economics) is not dict:
        raise GateError(f"{prefix} must be an object")
    status = _string(economics.get("status"), f"{prefix}.status")
    if status == "PENDING":
        _exact_keys(economics, {"status"}, prefix)
        return {"status": "PENDING"}
    if status != ECONOMICS_PASS:
        raise GateError(f"{prefix}.status must be PENDING or {ECONOMICS_PASS}")
    _exact_keys(economics, {"status", "report_path", "report_sha256"}, prefix)
    expected_sha = _sha(economics["report_sha256"], f"{prefix}.report_sha256", 64)
    report_path = _safe_evidence_path(
        evidence_root, economics["report_path"], f"{prefix}.report_path"
    )

    # One captured read is the sole authority for SHA and parse.
    raw = report_path.read_bytes()
    actual_sha = _bytes_sha256(raw)
    if actual_sha != expected_sha:
        raise GateError(f"{prefix} report SHA256 mismatch")
    report = _strict_json(raw, label=f"{prefix} report")
    if type(report) is not dict:
        raise GateError(f"{prefix} report must be a JSON object")

    required = {
        "schema",
        "label",
        "control_id",
        "candidate_id",
        "engine_id",
        "harness_id",
        "opponent_pack_id",
        "cells",
    }
    if expected_component_source_sha256 is not None:
        required.add("component_source_sha256")
    _exact_keys(report, required, f"{prefix}.report")
    if report["schema"] != ECONOMICS_REPORT_SCHEMA:
        raise GateError(f"{prefix} report schema mismatch")
    if report["label"] != expected_label:
        raise GateError(f"{prefix} report label mismatch")

    control_id = _string(report["control_id"], f"{prefix}.report.control_id")
    candidate_id = _string(report["candidate_id"], f"{prefix}.report.candidate_id")
    for field, value in (("control_id", control_id), ("candidate_id", candidate_id)):
        if not value.startswith("v5c:"):
            raise GateError(f"{prefix}.report.{field} must be v5c-bound")
        _sha(value[4:], f"{prefix}.report.{field}[4:]", 64)
    if control_id == candidate_id:
        raise GateError(f"{prefix} control and candidate identities must differ")

    engine_id = _string(report["engine_id"], f"{prefix}.report.engine_id")
    harness_id = _string(report["harness_id"], f"{prefix}.report.harness_id")
    opponent_pack_id = _string(
        report["opponent_pack_id"], f"{prefix}.report.opponent_pack_id"
    )

    if expected_component_source_sha256 is not None:
        supplied = _sha(
            report["component_source_sha256"],
            f"{prefix}.report.component_source_sha256",
            64,
        )
        if supplied != expected_component_source_sha256:
            raise GateError(
                f"{prefix} report component_source_sha256 does not match exact source set"
            )

    raw_cells = report["cells"]
    if type(raw_cells) is not list:
        raise GateError(f"{prefix}.report.cells must be a JSON array")
    cells: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    seats_by_pair: dict[tuple[str, int], set[int]] = {}
    for index, raw_cell in enumerate(raw_cells):
        field = f"{prefix}.report.cells[{index}]"
        if type(raw_cell) is not dict:
            raise GateError(f"{field} must be an object")
        _exact_keys(
            raw_cell,
            {
                "opponent",
                "seed",
                "seat",
                "control_own",
                "control_rival",
                "candidate_own",
                "candidate_rival",
            },
            field,
        )
        opponent = _string(raw_cell["opponent"], f"{field}.opponent")
        seed = _integer(raw_cell["seed"], f"{field}.seed")
        seat = _integer(raw_cell["seat"], f"{field}.seat")
        if seat not in (0, 1):
            raise GateError(f"{field}.seat must be 0 or 1")
        key = (opponent, seed, seat)
        if key in seen:
            raise GateError(f"duplicate paired cell: {key}")
        seen.add(key)
        seats_by_pair.setdefault((opponent, seed), set()).add(seat)
        cells.append(
            {
                "opponent": opponent,
                "seed": seed,
                "seat": seat,
                "control_own": _number(raw_cell["control_own"], f"{field}.control_own"),
                "control_rival": _number(raw_cell["control_rival"], f"{field}.control_rival"),
                "candidate_own": _number(raw_cell["candidate_own"], f"{field}.candidate_own"),
                "candidate_rival": _number(raw_cell["candidate_rival"], f"{field}.candidate_rival"),
            }
        )

    for pair, seats in seats_by_pair.items():
        if seats != {0, 1}:
            raise GateError(f"paired report must contain both seats for {pair}")

    opponents = sorted({cell["opponent"] for cell in cells})
    seeds_by_opponent = {
        opponent: sorted(
            {cell["seed"] for cell in cells if cell["opponent"] == opponent}
        )
        for opponent in opponents
    }
    depths = {len(seeds) for seeds in seeds_by_opponent.values()}
    seeds_per_opponent = next(iter(depths)) if len(depths) == 1 else 0

    sorted_cells = sorted(
        cells, key=lambda cell: (cell["opponent"], cell["seed"], cell["seat"])
    )
    deltas: list[float] = []
    per_opponent_values: dict[str, list[float]] = {opponent: [] for opponent in opponents}
    for cell in sorted_cells:
        control_margin = cell["control_own"] - cell["control_rival"]
        candidate_margin = cell["candidate_own"] - cell["candidate_rival"]
        delta = candidate_margin - control_margin
        deltas.append(delta)
        per_opponent_values[cell["opponent"]].append(delta)

    mean_margin_delta = sum(deltas) / len(deltas) if deltas else 0.0
    per_opponent_margin_delta = {
        opponent: (sum(values) / len(values) if values else 0.0)
        for opponent, values in per_opponent_values.items()
    }
    panel_digest = _canonical_sha256(
        {
            "schema": ECONOMICS_REPORT_SCHEMA,
            "label": expected_label,
            "control_id": control_id,
            "candidate_id": candidate_id,
            "engine_id": engine_id,
            "harness_id": harness_id,
            "opponent_pack_id": opponent_pack_id,
            "cells": sorted_cells,
        }
    )
    return {
        "status": ECONOMICS_PASS,
        "report_path": economics["report_path"],
        "report_sha256": actual_sha,
        "panel_digest": panel_digest,
        "control_id": control_id,
        "candidate_id": candidate_id,
        "engine_id": engine_id,
        "harness_id": harness_id,
        "opponent_pack_id": opponent_pack_id,
        "opponents": opponents,
        "seeds_per_opponent": seeds_per_opponent,
        "both_seats": all(seats == {0, 1} for seats in seats_by_pair.values()),
        "paired_cells": len(sorted_cells),
        "mean_margin_delta": mean_margin_delta,
        "per_opponent_margin_delta": per_opponent_margin_delta,
        **(
            {"component_source_sha256": expected_component_source_sha256}
            if expected_component_source_sha256 is not None
            else {}
        ),
    }


def _validate_component(
    component: Any,
    index: int,
    *,
    source_reader: SourceReader,
    evidence_root: Path,
) -> tuple[str, dict[str, Any]]:
    prefix = f"components[{index}]"
    if type(component) is not dict:
        raise GateError(f"{prefix} must be an object")
    _exact_keys(
        component,
        {
            "slot",
            "current_abi",
            "producer_ownership",
            "source_paths",
            "carrier",
            "economics",
        },
        prefix,
    )
    slot = _string(component["slot"], f"{prefix}.slot")
    if slot in FORBIDDEN_ACTIVE_SLOTS:
        raise GateError(f"{slot} was OFF/identity in submitted V3.1")
    if slot not in REQUIRED_SLOTS:
        raise GateError(f"unknown recovery slot: {slot}")
    if not _exact_bool(component["current_abi"], f"{prefix}.current_abi"):
        raise GateError(f"{slot} must be expressed on current-V5 ABI")

    ownership = _string(
        component["producer_ownership"], f"{prefix}.producer_ownership"
    )
    expected_ownership = "single_parent_delegate" if slot == "fert_hand_boundary" else "none"
    if ownership != expected_ownership:
        raise GateError(
            f"{slot} producer_ownership must be {expected_ownership}; second producers forbidden"
        )

    source_paths = _string_list(component["source_paths"], f"{prefix}.source_paths")
    if not source_paths:
        raise GateError(f"{slot} must declare source_paths")
    for path in source_paths:
        normalized = "/" + path.lstrip("/")
        if normalized.endswith(FORBIDDEN_WHOLE_ROUTER_SUFFIXES):
            raise GateError(f"{slot} attempts forbidden whole-router/tape transplant: {path}")
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise GateError(f"{prefix}.source_paths must be repository-relative")

    carrier = component["carrier"]
    if type(carrier) is not dict:
        raise GateError(f"{prefix}.carrier must be an object")
    _exact_keys(carrier, {"pr", "head_sha"}, f"{prefix}.carrier")
    pr = _integer(carrier["pr"], f"{prefix}.carrier.pr", minimum=1)
    head_sha = _sha(carrier["head_sha"], f"{prefix}.carrier.head_sha", 40)
    if not source_reader.commit_exists(head_sha):
        raise GateError(f"{prefix}.carrier.head_sha does not resolve to a Git commit")

    source_files: list[dict[str, str]] = []
    for path in source_paths:
        raw = source_reader.read_file(head_sha, path)
        source_files.append(
            {
                "path": path,
                "git_blob_sha1": _git_blob_sha1(raw),
                "sha256": _bytes_sha256(raw),
            }
        )
    source_tree_sha256 = _canonical_sha256(source_files)
    component_source_sha256 = _canonical_sha256(
        {
            "slot": slot,
            "current_abi": True,
            "producer_ownership": ownership,
            "runtime_stage": CURRENT_RUNTIME_STAGES[slot],
            "source_paths": source_paths,
            "carrier": {"pr": pr, "head_sha": head_sha},
            "source_files": source_files,
            "source_tree_sha256": source_tree_sha256,
        }
    )

    economics = _validate_report(
        component["economics"],
        f"{prefix}.economics",
        expected_label=slot,
        evidence_root=evidence_root,
        expected_component_source_sha256=component_source_sha256,
    )
    return slot, {
        "slot": slot,
        "current_abi": True,
        "producer_ownership": ownership,
        "runtime_stage": CURRENT_RUNTIME_STAGES[slot],
        "source_paths": source_paths,
        "carrier": {"pr": pr, "head_sha": head_sha},
        "source_files": source_files,
        "source_tree_sha256": source_tree_sha256,
        "component_source_sha256": component_source_sha256,
        "economics": economics,
    }


def _component_source_view(
    components: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    return [
        {
            "slot": slot,
            "current_abi": components[slot]["current_abi"],
            "producer_ownership": components[slot]["producer_ownership"],
            "runtime_stage": components[slot]["runtime_stage"],
            "source_paths": components[slot]["source_paths"],
            "carrier": components[slot]["carrier"],
            "source_files": components[slot]["source_files"],
            "source_tree_sha256": components[slot]["source_tree_sha256"],
            "component_source_sha256": components[slot]["component_source_sha256"],
        }
        for slot in REQUIRED_SLOTS
        if slot in components
    ]


def _economics_blockers(prefix: str, economics: Mapping[str, Any]) -> list[str]:
    if economics["status"] != ECONOMICS_PASS:
        return [f"economics_not_pass:{prefix}"]
    blockers: list[str] = []
    if len(economics["opponents"]) < 2:
        blockers.append(f"opponent_diversity:{prefix}")
    if economics["seeds_per_opponent"] < 4:
        blockers.append(f"seed_depth:{prefix}")
    if economics["both_seats"] is not True:
        blockers.append(f"both_seats_required:{prefix}")
    if economics["paired_cells"] < 16:
        blockers.append(f"paired_cell_floor:{prefix}")
    if economics["mean_margin_delta"] < 0:
        blockers.append(f"negative_mean_margin:{prefix}")
    for opponent, delta in economics["per_opponent_margin_delta"].items():
        if delta < 0:
            blockers.append(f"negative_opponent_margin:{prefix}:{opponent}")
    return blockers


def evaluate_manifest(
    manifest: Mapping[str, Any],
    *,
    evidence_root: Path,
    source_reader: SourceReader,
) -> dict[str, Any]:
    """Validate one manifest against raw report bytes and Git source objects."""
    _validate_lineage(manifest)
    raw_components = manifest.get("components")
    if type(raw_components) is not list:
        raise GateError("components must be a JSON array")

    components: dict[str, dict[str, Any]] = {}
    for index, raw_component in enumerate(raw_components):
        slot, component = _validate_component(
            raw_component,
            index,
            source_reader=source_reader,
            evidence_root=evidence_root,
        )
        if slot in components:
            raise GateError(f"duplicate semantic slot: {slot}")
        components[slot] = component

    blockers: list[str] = []
    for slot in REQUIRED_SLOTS:
        component = components.get(slot)
        if component is None:
            blockers.append(f"missing_component:{slot}")
            continue
        blockers.extend(_economics_blockers(slot, component["economics"]))

    component_source_view = _component_source_view(components)
    component_source_sha256 = _canonical_sha256(
        {
            "submitted_v31_source": SUBMITTED_V31_SOURCE,
            "submitted_v31_archive_sha256": SUBMITTED_V31_ARCHIVE_SHA256,
            "submitted_topology": SUBMITTED_TOPOLOGY,
            "current_runtime_stages": CURRENT_RUNTIME_STAGES,
            "components": component_source_view,
        }
    )

    composition_economics = _validate_report(
        manifest.get("composition_economics"),
        "composition_economics",
        expected_label="combined_composition",
        evidence_root=evidence_root,
        expected_component_source_sha256=component_source_sha256,
    )
    blockers.extend(
        _economics_blockers("combined_composition", composition_economics)
    )

    normalized_components = [
        components[slot] for slot in REQUIRED_SLOTS if slot in components
    ]
    evidence = {
        "submitted_v31_source": SUBMITTED_V31_SOURCE,
        "submitted_v31_archive_sha256": SUBMITTED_V31_ARCHIVE_SHA256,
        "submitted_topology": SUBMITTED_TOPOLOGY,
        "current_runtime_stages": CURRENT_RUNTIME_STAGES,
        "component_source_sha256": component_source_sha256,
        "components": normalized_components,
        "composition_economics": composition_economics,
    }
    ready = not blockers and set(components) == set(REQUIRED_SLOTS)
    return {
        "schema": RECEIPT_SCHEMA,
        "status": (
            "CURRENT_V5_COMPOSITION_READY_DEFAULT_OFF" if ready else "BLOCKED"
        ),
        "target_version": "v5",
        "component_count": len(components),
        "required_component_count": len(REQUIRED_SLOTS),
        "blockers": blockers,
        "component_source_sha256": component_source_sha256,
        "evidence_sha256": _canonical_sha256(evidence),
        "component_heads": {
            slot: components[slot]["carrier"]["head_sha"]
            for slot in REQUIRED_SLOTS
            if slot in components
        },
        "component_source_trees": {
            slot: components[slot]["source_tree_sha256"]
            for slot in REQUIRED_SLOTS
            if slot in components
        },
        "combined_candidate_id": (
            composition_economics.get("candidate_id")
            if composition_economics["status"] == ECONOMICS_PASS
            else None
        ),
        "default_flip_authority": False,
        "release_authority": False,
        "kaggle_submission_authority": False,
    }


def _receipt_text(receipt: Mapping[str, Any]) -> str:
    return json.dumps(receipt, sort_keys=True, indent=2) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="strict convergence manifest JSON")
    parser.add_argument("--repo", help="Git repository root; auto-discovered by default")
    parser.add_argument("--output", help="optional write-once receipt path; stdout otherwise")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    try:
        raw = manifest_path.read_bytes()
        manifest = load_manifest_bytes(raw)
        source_reader = (
            GitSourceReader(Path(args.repo))
            if args.repo
            else GitSourceReader.discover(manifest_path.parent)
        )
        receipt = evaluate_manifest(
            manifest,
            evidence_root=manifest_path.parent,
            source_reader=source_reader,
        )
    except (OSError, GateError) as exc:
        parser.exit(2, f"composition gate error: {exc}\n")

    text = _receipt_text(receipt)
    if args.output:
        path = Path(args.output)
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(text)
        except FileExistsError:
            parser.exit(2, "composition gate error: refusing to overwrite receipt\n")
    else:
        print(text, end="")
    return 0 if receipt["status"] != "BLOCKED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
