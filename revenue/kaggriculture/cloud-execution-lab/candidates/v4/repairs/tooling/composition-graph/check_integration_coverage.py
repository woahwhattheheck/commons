#!/usr/bin/env python3
"""Fail-closed custody audit between TITAN V4 INTEGRATION and COMPOSITION ledgers."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

COVERAGE_SCHEMA = "titan-v4-integration-composition-coverage/v1"
INTEGRATION_SCHEMA = "titan-v4-integration-ledger/v1"
COMPOSITION_SCHEMA = "titan-v4-composition/v1"
ALLOWED_DISPOSITIONS = {"compose", "blocked", "evidence_only", "non_applicable"}
GRAPH_STATES = {"compose", "blocked", "evidence_only"}


def _issue(code: str, **details: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"code": code}
    out.update(details)
    return out


def _stable(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))


def _safe_relpath(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    p = PurePosixPath(value)
    return not p.is_absolute() and ".." not in p.parts and "." not in p.parts


def _canonical_digest(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def audit_ledgers(integration: dict[str, Any], composition: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    action_required: list[dict[str, Any]] = []
    graph_bound: list[dict[str, Any]] = []
    non_applicable: list[dict[str, Any]] = []

    if integration.get("schema") != INTEGRATION_SCHEMA:
        errors.append(_issue("bad_integration_schema", actual=integration.get("schema")))
    if composition.get("schema") != COMPOSITION_SCHEMA:
        errors.append(_issue("bad_composition_schema", actual=composition.get("schema")))
    if coverage.get("schema") != COVERAGE_SCHEMA:
        errors.append(_issue("bad_coverage_schema", actual=coverage.get("schema")))
    if coverage.get("mode") != "fail_closed":
        errors.append(_issue("coverage_not_fail_closed", actual=coverage.get("mode")))

    landed = integration.get("landed")
    if not isinstance(landed, list):
        landed = []
        errors.append(_issue("integration_landed_not_list"))

    integration_by_path: dict[str, dict[str, Any]] = {}
    for idx, item in enumerate(landed):
        if not isinstance(item, dict):
            errors.append(_issue("integration_entry_not_object", index=idx))
            continue
        path = item.get("repair_path")
        if path is None:
            continue
        if not _safe_relpath(path):
            errors.append(_issue("unsafe_integration_repair_path", index=idx, path=path))
            continue
        if path in integration_by_path:
            errors.append(_issue("duplicate_integration_repair_path", path=path))
            continue
        lane = item.get("lane")
        if not isinstance(lane, str) or not lane.strip():
            errors.append(_issue("integration_repair_missing_lane", path=path))
        integration_by_path[path] = item

    raw_components = composition.get("components")
    if not isinstance(raw_components, list):
        raw_components = []
        errors.append(_issue("composition_components_not_list"))

    component_by_id: dict[str, dict[str, Any]] = {}
    graph_by_package: dict[str, list[str]] = {}
    for idx, comp in enumerate(raw_components):
        if not isinstance(comp, dict):
            errors.append(_issue("composition_component_not_object", index=idx))
            continue
        cid = comp.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append(_issue("bad_graph_component_id", index=idx))
            continue
        if cid in component_by_id:
            errors.append(_issue("duplicate_graph_component_id", component=cid))
            continue
        component_by_id[cid] = comp
        package = comp.get("package")
        if isinstance(package, str):
            graph_by_package.setdefault(package, []).append(cid)

    raw_entries = coverage.get("entries")
    if not isinstance(raw_entries, list):
        raw_entries = []
        errors.append(_issue("coverage_entries_not_list"))

    coverage_by_path: dict[str, dict[str, Any]] = {}
    referenced_components: dict[str, str] = {}
    for idx, entry in enumerate(raw_entries):
        if not isinstance(entry, dict):
            errors.append(_issue("coverage_entry_not_object", index=idx))
            continue
        path = entry.get("repair_path")
        if not _safe_relpath(path):
            errors.append(_issue("unsafe_coverage_repair_path", index=idx, path=path))
            continue
        if path in coverage_by_path:
            errors.append(_issue("duplicate_coverage_repair_path", path=path))
            continue
        coverage_by_path[path] = entry

        disposition = entry.get("disposition")
        if disposition not in ALLOWED_DISPOSITIONS:
            errors.append(_issue("bad_disposition", path=path, actual=disposition))
        reason = entry.get("reason")
        if disposition != "compose" and (not isinstance(reason, str) or not reason.strip()):
            errors.append(_issue("disposition_without_reason", path=path, disposition=disposition))

        component = entry.get("graph_component")
        if component is not None and (not isinstance(component, str) or not component):
            errors.append(_issue("bad_graph_component_reference", path=path, component=component))
            component = None
        if isinstance(component, str):
            prior = referenced_components.get(component)
            if prior is not None and prior != path:
                errors.append(_issue("duplicate_graph_component_binding", component=component, path=path, other=prior))
            else:
                referenced_components[component] = path

    integration_paths = set(integration_by_path)
    coverage_paths = set(coverage_by_path)
    for path in sorted(integration_paths - coverage_paths):
        item = integration_by_path[path]
        errors.append(_issue("unclassified_integration_path", path=path, lane=item.get("lane")))
    for path in sorted(coverage_paths - integration_paths):
        errors.append(_issue("coverage_path_not_in_integration", path=path))

    for path in sorted(integration_paths & coverage_paths):
        item = integration_by_path[path]
        entry = coverage_by_path[path]
        if entry.get("lane") != item.get("lane"):
            errors.append(_issue("lane_mismatch", path=path, integration_lane=item.get("lane"), coverage_lane=entry.get("lane")))

        disposition = entry.get("disposition")
        component_id = entry.get("graph_component")
        explicit_state = item.get("composition_state")
        if explicit_state is not None:
            if explicit_state not in GRAPH_STATES:
                errors.append(_issue("bad_integration_composition_state", path=path, actual=explicit_state))
            if disposition != explicit_state:
                errors.append(_issue("integration_composition_state_mismatch", path=path, integration_state=explicit_state, disposition=disposition))
            if not isinstance(component_id, str) or not component_id:
                errors.append(_issue("integration_composition_state_unbound", path=path, state=explicit_state))

        if disposition == "non_applicable":
            if component_id is not None:
                errors.append(_issue("non_applicable_has_graph_component", path=path, component=component_id))
            non_applicable.append({"repair_path": path, "lane": item.get("lane"), "reason": entry.get("reason")})
            continue

        if component_id is None:
            if disposition == "compose":
                errors.append(_issue("compose_without_graph_component", path=path))
            elif disposition in {"blocked", "evidence_only"}:
                action_required.append({
                    "repair_path": path,
                    "lane": item.get("lane"),
                    "disposition": disposition,
                    "reason": entry.get("reason"),
                })
            continue

        comp = component_by_id.get(component_id)
        if comp is None:
            errors.append(_issue("unknown_graph_component", path=path, component=component_id))
            continue
        if comp.get("package") != path:
            errors.append(_issue("graph_package_mismatch", path=path, component=component_id, graph_package=comp.get("package")))
        graph_state = comp.get("state")
        if graph_state != disposition:
            errors.append(_issue("graph_state_mismatch", path=path, component=component_id, graph_state=graph_state, disposition=disposition))
        graph_bound.append({
            "repair_path": path,
            "lane": item.get("lane"),
            "component": component_id,
            "state": graph_state,
        })

    for path in sorted(integration_paths):
        for component_id in sorted(graph_by_package.get(path, [])):
            bound_path = referenced_components.get(component_id)
            if bound_path != path:
                errors.append(_issue("graph_component_not_bound_to_coverage", path=path, component=component_id, bound_path=bound_path))

    classified = sorted(coverage_paths & integration_paths)
    digest_payload = {
        "classified": [
            {
                "repair_path": path,
                "lane": coverage_by_path[path].get("lane"),
                "disposition": coverage_by_path[path].get("disposition"),
                "graph_component": coverage_by_path[path].get("graph_component"),
                "reason": coverage_by_path[path].get("reason"),
            }
            for path in classified
        ],
        "graph_components": [
            {
                "id": cid,
                "package": component_by_id[cid].get("package"),
                "state": component_by_id[cid].get("state"),
            }
            for cid in sorted(component_by_id)
            if component_by_id[cid].get("package") in integration_paths
        ],
    }

    return {
        "ok": not errors,
        "classified_count": len(classified),
        "graph_bound": sorted(graph_bound, key=lambda x: (str(x.get("repair_path")), str(x.get("component")))),
        "action_required": sorted(action_required, key=lambda x: str(x.get("repair_path"))),
        "non_applicable": sorted(non_applicable, key=lambda x: str(x.get("repair_path"))),
        "coverage_digest": _canonical_digest(digest_payload),
        "errors": _stable(errors),
    }


def _load_json(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    data = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )
    if not isinstance(data, dict):
        raise ValueError("top-level JSON must be an object")
    return data


def main() -> int:
    here = Path(__file__).resolve().parent
    default_root = here.parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(default_root))
    parser.add_argument("--integration", default="INTEGRATION.json")
    parser.add_argument("--composition", default="COMPOSITION.json")
    parser.add_argument("--coverage", default="repairs/tooling/composition-graph/INTEGRATION-COVERAGE.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    try:
        integration = _load_json(root / args.integration)
        composition = _load_json(root / args.composition)
        coverage = _load_json(root / args.coverage)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "ok": False,
            "classified_count": 0,
            "graph_bound": [],
            "action_required": [],
            "non_applicable": [],
            "coverage_digest": None,
            "errors": [_issue("ledger_load_error", error=str(exc))],
        }
    else:
        result = audit_ledgers(integration, composition, coverage)

    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print("OK" if result["ok"] else "FAIL")
        print("classified:", result["classified_count"])
        print("graph_bound:", len(result["graph_bound"]))
        print("action_required:", len(result["action_required"]))
        for item in result["action_required"]:
            print("ACTION", json.dumps(item, sort_keys=True))
        for item in result["errors"]:
            print("ERROR", json.dumps(item, sort_keys=True))
        print("coverage_digest:", result["coverage_digest"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
