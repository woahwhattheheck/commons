# SPDX-License-Identifier: Apache-2.0
"""Fail-closed convergence gate for recovered submitted-V3.1 R04 behavior.

This module does not implement gameplay.  It validates that independently
recovered current-V5 component carriers converge through one declared topology,
with current-source custody and paired-economics authority, before they may be
treated as a composition-ready default-OFF V5 stack.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "titan-v5-r04-recovery-composition-gate/v1"
RECEIPT_SCHEMA = "titan-v5-r04-recovery-composition-receipt/v1"

SUBMITTED_V31_SOURCE = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
SUBMITTED_V31_ARCHIVE_SHA256 = (
    "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"
)

REQUIRED_SLOTS = (
    "sale_window_h8_l3",
    "h4_strawberry_topup",
    "row_shed",
    "evening_flush",
    "b5_carrot_jit",
    "fert_hand_boundary",
    "b9_terminal_fertilizer",
    "h3c_goose_rescue",
)

SUBMITTED_TOPOLOGY = {
    "inner_return_pipeline": [
        "sale_window_h8_l3",
        "h4_strawberry_topup",
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

# These existed in historical source but were OFF/identity in the exact submitted
# winner.  Their mere existence is not recovery authority.
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
    """Manifest is malformed or violates a hard convergence invariant."""


def _reject_constant(value: str) -> None:
    raise GateError(f"non-finite JSON constant is forbidden: {value}")


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise GateError(f"duplicate JSON object key: {key}")
        out[key] = value
    return out


def load_manifest_bytes(raw: bytes) -> Mapping[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError("manifest must be UTF-8 JSON") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object,
            parse_constant=_reject_constant,
        )
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError("manifest is not valid JSON") from exc
    if type(value) is not dict:
        raise GateError("manifest must be a JSON object")
    return value


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
    if len(text) != length or any(c not in "0123456789abcdef" for c in text):
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
    out: list[str] = []
    for index, item in enumerate(value):
        out.append(_string(item, f"{field}[{index}]"))
    if len(set(out)) != len(out):
        raise GateError(f"{field} contains duplicates")
    return out


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _validate_topology(value: Any) -> None:
    if type(value) is not dict:
        raise GateError("submitted_topology must be an object")
    if value != SUBMITTED_TOPOLOGY:
        raise GateError("submitted_topology does not match exact submitted V3.1 ordering")


def _validate_lineage(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema") != SCHEMA:
        raise GateError(f"schema must equal {SCHEMA}")
    if manifest.get("target_version") != "v5":
        raise GateError("target_version must be v5")
    if manifest.get("source_architecture") != "current_v5":
        raise GateError("source_architecture must be current_v5")

    authority = manifest.get("submitted_v31_authority")
    if type(authority) is not dict:
        raise GateError("submitted_v31_authority must be an object")
    if authority.get("source_commit") != SUBMITTED_V31_SOURCE:
        raise GateError("submitted V3.1 source commit mismatch")
    if authority.get("archive_sha256") != SUBMITTED_V31_ARCHIVE_SHA256:
        raise GateError("submitted V3.1 archive mismatch")

    for field in (
        "v4_thaw",
        "legacy_whole_router_transplant",
        "production_default_flip",
        "release_requested",
        "kaggle_submission_requested",
    ):
        if _exact_bool(manifest.get(field), field):
            raise GateError(f"{field} must remain false on the convergence carrier")

    _validate_topology(manifest.get("submitted_topology"))


def _validate_component_shape(component: Any, index: int) -> tuple[str, dict[str, Any]]:
    prefix = f"components[{index}]"
    if type(component) is not dict:
        raise GateError(f"{prefix} must be an object")

    slot = _string(component.get("slot"), f"{prefix}.slot")
    if slot in FORBIDDEN_ACTIVE_SLOTS:
        raise GateError(f"{slot} was OFF/identity in submitted V3.1 and cannot be recovered active")
    if slot not in REQUIRED_SLOTS:
        raise GateError(f"unknown recovery slot: {slot}")

    if not _exact_bool(component.get("current_abi"), f"{prefix}.current_abi"):
        raise GateError(f"{slot} must be expressed on a current-V5 ABI")

    ownership = _string(component.get("producer_ownership"), f"{prefix}.producer_ownership")
    expected_ownership = "single_parent_delegate" if slot == "fert_hand_boundary" else "none"
    if ownership != expected_ownership:
        raise GateError(
            f"{slot} producer_ownership must be {expected_ownership}; second producers are forbidden"
        )

    source_paths = _string_list(component.get("source_paths"), f"{prefix}.source_paths")
    if not source_paths:
        raise GateError(f"{slot} must declare at least one current carrier source path")
    for path in source_paths:
        normalized = "/" + path.lstrip("/")
        if normalized.endswith(FORBIDDEN_WHOLE_ROUTER_SUFFIXES):
            raise GateError(f"{slot} attempts forbidden whole-router/tape transplant: {path}")

    carrier = component.get("carrier")
    if type(carrier) is not dict:
        raise GateError(f"{prefix}.carrier must be an object")
    pr = _integer(carrier.get("pr"), f"{prefix}.carrier.pr", minimum=1)
    head_sha = _sha(carrier.get("head_sha"), f"{prefix}.carrier.head_sha", 40)
    source_receipt_sha256 = _sha(
        carrier.get("source_receipt_sha256"),
        f"{prefix}.carrier.source_receipt_sha256",
        64,
    )

    economics = component.get("economics")
    if type(economics) is not dict:
        raise GateError(f"{prefix}.economics must be an object")
    status = _string(economics.get("status"), f"{prefix}.economics.status")
    if status == "PENDING":
        if set(economics) != {"status"}:
            raise GateError(f"{slot} PENDING economics may contain only status")
        normalized_economics: dict[str, Any] = {"status": "PENDING"}
    elif status == ECONOMICS_PASS:
        report_sha256 = _sha(
            economics.get("report_sha256"),
            f"{prefix}.economics.report_sha256",
            64,
        )
        control_id = _string(economics.get("control_id"), f"{prefix}.economics.control_id")
        candidate_id = _string(economics.get("candidate_id"), f"{prefix}.economics.candidate_id")
        if not control_id.startswith("v5c:") or not candidate_id.startswith("v5c:"):
            raise GateError(f"{slot} economics identities must be v5c-bound")
        if control_id == candidate_id:
            raise GateError(f"{slot} control and candidate identities must differ")

        opponents = _string_list(economics.get("opponents"), f"{prefix}.economics.opponents")
        seeds_per_opponent = _integer(
            economics.get("seeds_per_opponent"),
            f"{prefix}.economics.seeds_per_opponent",
        )
        both_seats = _exact_bool(economics.get("both_seats"), f"{prefix}.economics.both_seats")
        paired_cells = _integer(economics.get("paired_cells"), f"{prefix}.economics.paired_cells")
        mean_margin_delta = _number(
            economics.get("mean_margin_delta"),
            f"{prefix}.economics.mean_margin_delta",
        )
        normalized_economics = {
            "status": status,
            "report_sha256": report_sha256,
            "control_id": control_id,
            "candidate_id": candidate_id,
            "opponents": opponents,
            "seeds_per_opponent": seeds_per_opponent,
            "both_seats": both_seats,
            "paired_cells": paired_cells,
            "mean_margin_delta": mean_margin_delta,
        }
    else:
        raise GateError(f"{slot} economics.status must be PENDING or {ECONOMICS_PASS}")

    normalized = {
        "slot": slot,
        "current_abi": True,
        "producer_ownership": ownership,
        "source_paths": source_paths,
        "carrier": {
            "pr": pr,
            "head_sha": head_sha,
            "source_receipt_sha256": source_receipt_sha256,
        },
        "economics": normalized_economics,
    }
    return slot, normalized


def evaluate_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one convergence manifest and return a deterministic receipt.

    Hard semantic/custody violations raise GateError.  Legitimate incomplete or
    non-promotable component evidence returns BLOCKED with explicit blockers.
    """
    _validate_lineage(manifest)

    raw_components = manifest.get("components")
    if type(raw_components) is not list:
        raise GateError("components must be a JSON array")

    components: dict[str, dict[str, Any]] = {}
    for index, raw_component in enumerate(raw_components):
        slot, component = _validate_component_shape(raw_component, index)
        if slot in components:
            raise GateError(f"duplicate semantic slot: {slot}")
        components[slot] = component

    blockers: list[str] = []
    for slot in REQUIRED_SLOTS:
        component = components.get(slot)
        if component is None:
            blockers.append(f"missing_component:{slot}")
            continue

        economics = component["economics"]
        if economics["status"] != ECONOMICS_PASS:
            blockers.append(f"economics_not_pass:{slot}")
            continue
        if len(economics["opponents"]) < 2:
            blockers.append(f"opponent_diversity:{slot}")
        if economics["seeds_per_opponent"] < 4:
            blockers.append(f"seed_depth:{slot}")
        if economics["both_seats"] is not True:
            blockers.append(f"both_seats_required:{slot}")
        if economics["paired_cells"] < 16:
            blockers.append(f"paired_cell_floor:{slot}")
        if economics["mean_margin_delta"] < 0:
            blockers.append(f"negative_mean_margin:{slot}")

    extra = sorted(set(components) - set(REQUIRED_SLOTS))
    if extra:
        # Normally unreachable because shape validation rejects unknown slots.
        raise GateError(f"unexpected component slots: {extra}")

    normalized_components = [components[slot] for slot in REQUIRED_SLOTS if slot in components]
    evidence = {
        "submitted_v31_source": SUBMITTED_V31_SOURCE,
        "submitted_v31_archive_sha256": SUBMITTED_V31_ARCHIVE_SHA256,
        "submitted_topology": SUBMITTED_TOPOLOGY,
        "components": normalized_components,
    }

    ready = not blockers and tuple(components) != () and set(components) == set(REQUIRED_SLOTS)
    return {
        "schema": RECEIPT_SCHEMA,
        "status": (
            "CURRENT_V5_COMPOSITION_READY_DEFAULT_OFF"
            if ready
            else "BLOCKED"
        ),
        "target_version": "v5",
        "component_count": len(components),
        "required_component_count": len(REQUIRED_SLOTS),
        "blockers": blockers,
        "evidence_sha256": _canonical_sha256(evidence),
        "component_heads": {
            slot: components[slot]["carrier"]["head_sha"]
            for slot in REQUIRED_SLOTS
            if slot in components
        },
        # Composition-ready is intentionally not release/default/submission authority.
        "default_flip_authority": False,
        "release_authority": False,
        "kaggle_submission_authority": False,
    }


def _receipt_text(receipt: Mapping[str, Any]) -> str:
    return json.dumps(receipt, sort_keys=True, indent=2) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="strict convergence manifest JSON")
    parser.add_argument("--output", help="optional write-once receipt path; stdout otherwise")
    args = parser.parse_args(argv)

    try:
        raw = Path(args.manifest).read_bytes()
        manifest = load_manifest_bytes(raw)
        receipt = evaluate_manifest(manifest)
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
