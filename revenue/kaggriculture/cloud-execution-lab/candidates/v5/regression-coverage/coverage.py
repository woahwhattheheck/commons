#!/usr/bin/env python3
"""Package-first V3.1 -> V4 regression coverage authority.

The submitted tarballs are the root of truth. Git source refs are provenance only.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

COVERAGE_SCHEMA = "titan-v5-v31-v4-package-regression-coverage/v2"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalize_member_path(name: str) -> str:
    while name.startswith("./"):
        name = name[2:]
    if not name or "\\" in name:
        raise ValueError(f"unsafe archive member path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", "..") for part in path.parts):
        raise ValueError(f"unsafe archive member path: {name!r}")
    normalized = str(path)
    if normalized in ("", "."):
        raise ValueError(f"unsafe archive member path: {name!r}")
    return normalized


def archive_inventory(path: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    archive = path.read_bytes()
    members: dict[str, dict[str, Any]] = {}
    contents: dict[str, bytes] = {}
    with tarfile.open(path, "r:gz") as handle:
        for item in handle.getmembers():
            if item.isdir():
                continue
            if not item.isfile():
                raise ValueError(f"non-regular archive member rejected: {item.name}")
            member_path = normalize_member_path(item.name)
            if member_path in members:
                raise ValueError(f"duplicate archive member: {member_path}")
            extracted = handle.extractfile(item)
            if extracted is None:
                raise ValueError(f"unable to read archive member: {member_path}")
            raw = extracted.read()
            members[member_path] = {"sha256": sha256_bytes(raw), "size": len(raw)}
            contents[member_path] = raw
    return ({
        "archive_sha256": sha256_bytes(archive),
        "archive_size": len(archive),
        "member_count": len(members),
        "members": dict(sorted(members.items())),
    }, contents)


def pair_summary(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    lm, rm = left["members"], right["members"]
    common = set(lm) & set(rm)
    identical = {path for path in common if lm[path] == rm[path]}
    changed = common - identical
    return {
        "common_count": len(common),
        "identical_common_count": len(identical),
        "changed_common_count": len(changed),
        "v31_only_count": len(set(lm) - set(rm)),
        "v4_only_count": len(set(rm) - set(lm)),
        "changed_common_paths": sorted(changed),
        "v4_only_paths": sorted(set(rm) - set(lm)),
    }


def config_delta(v31_raw: bytes, v4_raw: bytes) -> dict[str, Any]:
    v31 = json.loads(v31_raw)
    v4 = json.loads(v4_raw)
    common = set(v31) & set(v4)
    return {
        "common_equal_count": sum(v31[key] == v4[key] for key in common),
        "changed_common": {
            key: [v31[key], v4[key]] for key in sorted(common) if v31[key] != v4[key]
        },
        "v31_only": {key: v31[key] for key in sorted(set(v31) - set(v4))},
        "v4_only": {key: v4[key] for key in sorted(set(v4) - set(v31))},
    }


def _symbol_map(raw: bytes) -> tuple[dict[str, str], dict[str, str], str]:
    tree = ast.parse(raw.decode("utf-8"))
    functions: dict[str, str] = {}
    class_shells: dict[str, str] = {}
    module_nodes: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions[node.name] = ast.dump(node, include_attributes=False)
        elif isinstance(node, ast.ClassDef):
            shell_body: list[ast.stmt] = []
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions[f"{node.name}.{child.name}"] = ast.dump(child, include_attributes=False)
                else:
                    shell_body.append(child)
            kwargs = dict(
                name=node.name,
                bases=node.bases,
                keywords=node.keywords,
                body=shell_body,
                decorator_list=node.decorator_list,
            )
            if hasattr(node, "type_params"):
                kwargs["type_params"] = node.type_params
            class_shells[node.name] = ast.dump(ast.ClassDef(**kwargs), include_attributes=False)
        else:
            module_nodes.append(node)
    module_shell = ast.dump(ast.Module(body=module_nodes, type_ignores=[]), include_attributes=False)
    return functions, class_shells, module_shell


def changed_symbols(v31_raw: bytes, v4_raw: bytes) -> list[str]:
    left, left_classes, left_module = _symbol_map(v31_raw)
    right, right_classes, right_module = _symbol_map(v4_raw)
    changes = sorted(key for key in set(left) | set(right) if left.get(key) != right.get(key))
    if left_module != right_module:
        changes.append("__module__")
    changes.extend(sorted(
        f"{key}.__class__"
        for key in set(left_classes) | set(right_classes)
        if left_classes.get(key) != right_classes.get(key)
    ))
    return changes


def _find_method(raw: bytes, class_name: str, method_name: str) -> ast.FunctionDef:
    tree = ast.parse(raw.decode("utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == method_name:
                    return child
    raise ValueError(f"missing {class_name}.{method_name}")


def verify_v31_route_authority(v31: dict[str, bytes], v4: dict[str, bytes], coverage: dict[str, Any]) -> None:
    cfg31 = json.loads(v31["TITAN-CONFIG.json"])
    cfg4 = json.loads(v4["TITAN-CONFIG.json"])
    if cfg31.get("r04_sale_window") is not True:
        raise ValueError("V3.1 package does not activate r04_sale_window")
    if "r04_sale_window" in cfg4:
        raise ValueError("V4 unexpectedly carries r04_sale_window config")
    if "r04_full_router.py" not in v31 or "r04_full_router.py" in v4:
        raise ValueError("R04 package topology mismatch")

    act = _find_method(v31["titan_runtime.py"], "TitanAgent", "act")
    r03 = _find_method(v31["titan_runtime.py"], "TitanAgent", "_v3_r03_act")
    branch_lines: list[int] = []
    init_lines: list[int] = []
    for node in ast.walk(act):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Attribute) and func.attr == "_v3_r03_act":
                branch_lines.append(node.lineno)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "_initialize":
            init_lines.append(node.lineno)
    if not branch_lines:
        raise ValueError("V3.1 act lacks R03/R04 early return")
    if init_lines and min(branch_lines) >= min(init_lines):
        raise ValueError("R04 return is not before canonical initialization")
    if not any(
        isinstance(node, ast.ImportFrom) and node.module == "r04_full_router"
        and any(alias.name == "install" for alias in node.names)
        for node in ast.walk(r03)
    ):
        raise ValueError("V3.1 delegate does not import r04_full_router.install")

    router = ast.parse(v31["r04_full_router.py"].decode("utf-8"))
    install = next((node for node in router.body if isinstance(node, ast.FunctionDef) and node.name == "install"), None)
    if install is None:
        raise ValueError("R04 install missing")
    returns_v3_agent = any(
        isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "v3_agent"
        for node in ast.walk(install)
    )
    if not returns_v3_agent:
        raise ValueError("R04 install does not return v3_agent")

    declared = coverage["reachability"]
    if declared["v31_active_route"]["canonical_controller_bypassed"] is not True:
        raise ValueError("coverage reachability does not bind canonical-controller bypass")
    if declared["v4_active_route"]["r04_full_router_member_present"] is not False:
        raise ValueError("coverage V4 reachability declaration drift")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def verify(v31_archive: Path, v4_archive: Path, coverage_path: Path) -> dict[str, Any]:
    coverage = load_json(coverage_path)
    if coverage.get("schema") != COVERAGE_SCHEMA:
        raise ValueError("coverage schema mismatch")

    actual: dict[str, dict[str, Any]] = {}
    contents: dict[str, dict[str, bytes]] = {}
    for label, archive in (("v31", v31_archive), ("v4", v4_archive)):
        inventory, raw_members = archive_inventory(archive)
        expected = coverage["authority"][label]
        for key in ("archive_sha256", "archive_size", "member_count"):
            if inventory[key] != expected[key]:
                raise ValueError(f"{label} {key} mismatch")
        inventory_root = sha256_bytes(canonical_json({"members": inventory["members"]}))
        if inventory_root != expected["inventory_root_sha256"]:
            raise ValueError(f"{label} inventory root mismatch")
        actual[label] = inventory
        contents[label] = raw_members

    summary = pair_summary(actual["v31"], actual["v4"])
    if summary != coverage.get("pair_summary"):
        raise ValueError("pair summary mismatch")

    delta = config_delta(contents["v31"]["TITAN-CONFIG.json"], contents["v4"]["TITAN-CONFIG.json"])
    if delta != coverage.get("config_delta"):
        raise ValueError("config delta mismatch")

    symbol_changes: dict[str, list[str]] = {}
    for member in summary["changed_common_paths"]:
        if member.endswith(".py"):
            symbol_changes[member] = changed_symbols(contents["v31"][member], contents["v4"][member])
    if symbol_changes != coverage.get("python_symbol_changes"):
        raise ValueError("package Python symbol delta mismatch")

    verify_v31_route_authority(contents["v31"], contents["v4"], coverage)

    if coverage["authority"]["v31"].get("source_ref_is_package_authority") is not False:
        raise ValueError("raw V3.1 source ref must be provenance-only")
    if coverage["authority"]["v4"].get("source_ref_is_package_authority") is not False:
        raise ValueError("raw V4 source ref must remain annotation, not archive authority")

    return {
        "schema": COVERAGE_SCHEMA,
        "v31_archive_sha256": actual["v31"]["archive_sha256"],
        "v4_archive_sha256": actual["v4"]["archive_sha256"],
        "pair_summary": summary,
        "config_delta": delta,
        "python_symbol_changes": symbol_changes,
        "reachability": "V31_R04_WHOLE_ROUTE__V4_CANONICAL_RUNTIME",
        "decision": coverage["decision"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v31-archive", required=True, type=Path)
    parser.add_argument("--v4-archive", required=True, type=Path)
    parser.add_argument("--coverage", type=Path, default=Path(__file__).with_name("COVERAGE.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify(args.v31_archive, args.v4_archive, args.coverage)
    rendered = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
