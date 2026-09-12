#!/usr/bin/env python3
"""Fail-closed coherence audit across TITAN V4 canonical/integration/composition ledgers.

This module is control-plane only.  It never edits ledgers, executes gameplay,
materializes a runtime, or authorizes merge/promotion.  Its job is to detect
semantic split-brain that can survive the independent ledger validators.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_BRANCH = "main"
EXPECTED_ROOT = "revenue/kaggriculture/cloud-execution-lab/candidates/v4"
INTEGRATION_SCHEMA = "titan-v4-integration-ledger/v1"
COMPOSITION_SCHEMA = "titan-v4-composition/v1"
COMPOSITION_STATES = {"compose", "blocked", "evidence_only"}


class AuditError(ValueError):
    pass


def _pairs_no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise AuditError(f"duplicate JSON object key: {key!r}")
        out[key] = value
    return out


def load_json(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AuditError(f"cannot read {path}: {exc}") from exc
    try:
        value = json.loads(text, object_pairs_hook=_pairs_no_dupes)
    except (json.JSONDecodeError, AuditError) as exc:
        raise AuditError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{path} must contain a JSON object")
    return value


def _issue(code: str, **details: Any) -> dict[str, Any]:
    return {"code": code, **details}


def _sorted_issues(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))


def _safe_relpath(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and "." not in path.parts and ".." not in path.parts


def _require_list(value: Any, where: str, errors: list[dict[str, Any]]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(_issue("not_list", where=where))
        return []
    return value


def _canonical_identity(canonical: dict[str, Any], integration: dict[str, Any], composition: dict[str, Any], errors: list[dict[str, Any]]) -> None:
    if integration.get("schema") != INTEGRATION_SCHEMA:
        errors.append(_issue("bad_integration_schema", actual=integration.get("schema"), expected=INTEGRATION_SCHEMA))
    if composition.get("schema") != COMPOSITION_SCHEMA:
        errors.append(_issue("bad_composition_schema", actual=composition.get("schema"), expected=COMPOSITION_SCHEMA))

    branches = {
        "canonical": canonical.get("canonical_branch"),
        "integration": integration.get("canonical_branch"),
        "composition": composition.get("canonical_branch"),
    }
    for source, branch in branches.items():
        if branch != EXPECTED_BRANCH:
            errors.append(_issue("wrong_canonical_branch", source=source, actual=branch, expected=EXPECTED_BRANCH))
    if len(set(branches.values())) != 1:
        errors.append(_issue("branch_split_brain", values=branches))

    roots = {
        "canonical": canonical.get("workspace"),
        "integration": integration.get("workspace"),
        "composition": composition.get("canonical_root"),
    }
    for source, root in roots.items():
        if root != EXPECTED_ROOT:
            errors.append(_issue("wrong_canonical_root", source=source, actual=root, expected=EXPECTED_ROOT))
    if len(set(roots.values())) != 1:
        errors.append(_issue("root_split_brain", values=roots))

    # These production coordinates are duplicated intentionally between the
    # canonical declaration and integration ledger.  A disagreement means the
    # two control planes are talking about different executable targets.
    for field in ("production_target", "production_archive", "entrypoint"):
        cval = canonical.get(field)
        ival = integration.get(field)
        if not isinstance(cval, str) or not cval:
            errors.append(_issue("bad_canonical_coordinate", field=field, actual=cval))
        if not isinstance(ival, str) or not ival:
            errors.append(_issue("bad_integration_coordinate", field=field, actual=ival))
        if cval != ival:
            errors.append(_issue("production_coordinate_split_brain", field=field, canonical=cval, integration=ival))


def _landed_index(integration: dict[str, Any], errors: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_lane: dict[str, dict[str, Any]] = {}
    by_path: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(_require_list(integration.get("landed"), "INTEGRATION.landed", errors)):
        if not isinstance(raw, dict):
            errors.append(_issue("landed_row_not_object", index=index))
            continue
        lane = raw.get("lane")
        if not isinstance(lane, str) or not lane.strip():
            errors.append(_issue("bad_landed_lane", index=index, actual=lane))
            continue
        lane = lane.strip()
        if lane in by_lane:
            errors.append(_issue("duplicate_landed_lane", lane=lane))
        else:
            by_lane[lane] = raw

        repair_path = raw.get("repair_path")
        if repair_path is None:
            if "composition_state" in raw or "composition_intake_pr" in raw:
                errors.append(_issue("composition_marked_landed_row_without_repair_path", lane=lane))
            continue
        if not _safe_relpath(repair_path):
            errors.append(_issue("unsafe_landed_repair_path", lane=lane, path=repair_path))
            continue
        if repair_path in by_path:
            errors.append(_issue("duplicate_landed_repair_path", path=repair_path, lanes=sorted([lane, str(by_path[repair_path].get("lane"))])))
        else:
            by_path[repair_path] = raw
    return by_lane, by_path


def _component_index(composition: dict[str, Any], errors: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_package: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(_require_list(composition.get("components"), "COMPOSITION.components", errors)):
        if not isinstance(raw, dict):
            errors.append(_issue("component_not_object", index=index))
            continue
        cid = raw.get("id")
        if not isinstance(cid, str) or not cid.strip():
            errors.append(_issue("bad_component_id", index=index, actual=cid))
            continue
        cid = cid.strip()
        if cid in by_id:
            errors.append(_issue("duplicate_component_id", component=cid))
        else:
            by_id[cid] = raw
        state = raw.get("state")
        if state not in COMPOSITION_STATES:
            errors.append(_issue("bad_component_state", component=cid, actual=state))
        package = raw.get("package")
        if not _safe_relpath(package):
            errors.append(_issue("unsafe_component_package", component=cid, path=package))
            continue
        if package in by_package:
            errors.append(_issue("duplicate_component_package", package=package, components=sorted([cid, str(by_package[package].get("id"))])))
        else:
            by_package[package] = raw
    return by_id, by_package


def audit(canonical: dict[str, Any], integration: dict[str, Any], composition: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    _canonical_identity(canonical, integration, composition, errors)
    _, landed_by_path = _landed_index(integration, errors)
    _, component_by_package = _component_index(composition, errors)

    mappings: list[dict[str, Any]] = []
    for package, comp in sorted(component_by_package.items()):
        row = landed_by_path.get(package)
        if row is None:
            if comp.get("state") == "compose":
                errors.append(_issue(
                    "compose_without_landed_custody",
                    component=comp.get("id"),
                    package=package,
                ))
            else:
                warnings.append(_issue(
                    "noncompose_without_exact_landed_path",
                    component=comp.get("id"),
                    package=package,
                    state=comp.get("state"),
                ))
            continue
        mappings.append({
            "component": comp.get("id"),
            "package": package,
            "state": comp.get("state"),
            "lane": row.get("lane"),
            "landed_status": row.get("status"),
        })

    # Rows which explicitly opted into composition custody are a hard bilateral
    # contract, not a heuristic.  They must point to exactly the same package and
    # report the same state as COMPOSITION.json.
    for package, row in sorted(landed_by_path.items()):
        explicit = "composition_state" in row or "composition_intake_pr" in row
        if not explicit:
            continue
        lane = str(row.get("lane"))
        comp = component_by_package.get(package)
        if comp is None:
            errors.append(_issue("landed_composition_link_missing_component", lane=lane, package=package))
            continue
        declared_state = row.get("composition_state")
        if declared_state is None:
            errors.append(_issue("composition_intake_without_state", lane=lane, package=package))
        elif declared_state not in COMPOSITION_STATES:
            errors.append(_issue("bad_landed_composition_state", lane=lane, package=package, actual=declared_state))
        elif declared_state != comp.get("state"):
            errors.append(_issue(
                "composition_state_split_brain",
                lane=lane,
                component=comp.get("id"),
                package=package,
                integration_state=declared_state,
                composition_state=comp.get("state"),
            ))
        intake = row.get("composition_intake_pr")
        if intake is not None and (isinstance(intake, bool) or not isinstance(intake, int) or intake <= 0):
            errors.append(_issue("bad_composition_intake_pr", lane=lane, actual=intake))

    # A negative/parked path must never be the exact package of a live COMPOSE
    # node.  Today most negative rows have no path; this remains a hard guard for
    # future richer ledger rows.
    negatives = _require_list(integration.get("negative_or_parked"), "INTEGRATION.negative_or_parked", errors)
    for index, row in enumerate(negatives):
        if not isinstance(row, dict):
            errors.append(_issue("negative_row_not_object", index=index))
            continue
        repair_path = row.get("repair_path")
        if repair_path is None:
            continue
        if not _safe_relpath(repair_path):
            errors.append(_issue("unsafe_negative_repair_path", index=index, path=repair_path))
            continue
        comp = component_by_package.get(repair_path)
        if comp is not None and comp.get("state") == "compose":
            errors.append(_issue(
                "negative_lane_is_composed",
                lane=row.get("lane"),
                component=comp.get("id"),
                package=repair_path,
                disposition=row.get("disposition"),
            ))

    mapped_components = {row["component"] for row in mappings}
    compose_components = sorted(
        str(comp.get("id")) for comp in component_by_package.values() if comp.get("state") == "compose"
    )
    unmapped_compose = sorted(cid for cid in compose_components if cid not in mapped_components)

    return {
        "schema": "titan-v4-cross-ledger-audit/v1",
        "ok": not errors,
        "canonical_branch": EXPECTED_BRANCH,
        "canonical_root": EXPECTED_ROOT,
        "mappings": sorted(mappings, key=lambda row: (str(row["component"]), str(row["package"]))),
        "compose_components": compose_components,
        "unmapped_compose_components": unmapped_compose,
        "errors": _sorted_issues(errors),
        "warnings": _sorted_issues(warnings),
        "policy": {
            "decision_authority": False,
            "auto_merge": False,
            "auto_close": False,
            "mutates_ledgers": False,
            "runtime_promotion_authority": False,
            "economic_authority": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parents[2] if len(Path(__file__).resolve().parents) >= 3 else Path.cwd()
    parser.add_argument("--canonical", type=Path, default=here / "CANONICAL.json")
    parser.add_argument("--integration", type=Path, default=here / "INTEGRATION.json")
    parser.add_argument("--composition", type=Path, default=here / "COMPOSITION.json")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = audit(load_json(args.canonical), load_json(args.integration), load_json(args.composition))
    except AuditError as exc:
        result = {
            "schema": "titan-v4-cross-ledger-audit/v1",
            "ok": False,
            "errors": [_issue("load_error", error=str(exc))],
            "warnings": [],
            "mappings": [],
            "compose_components": [],
            "unmapped_compose_components": [],
            "policy": {
                "decision_authority": False,
                "auto_merge": False,
                "auto_close": False,
                "mutates_ledgers": False,
                "runtime_promotion_authority": False,
                "economic_authority": False,
            },
        }
    print(json.dumps(result, sort_keys=True, indent=2 if args.pretty else None, separators=None if args.pretty else (",", ":")))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
