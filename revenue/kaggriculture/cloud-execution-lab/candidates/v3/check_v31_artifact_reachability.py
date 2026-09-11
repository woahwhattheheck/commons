#!/usr/bin/env python3
"""Fail if a manifest-declared V3 key does not reach the built artifact.

This complements ``build_v3.py --check``. The builder already proves byte-for-byte
reproducibility; this preflight proves that every manifest lane with a declared module
ships byte-identical/import-reachable, and that every declared config key/parameter has
the manifest value and a semantic use in code reachable from the package entrypoint.

Usage:
    python check_v31_artifact_reachability.py
    python check_v31_artifact_reachability.py --canonical /path/to/titan-current.tar.gz
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_v3  # noqa: E402


_MODULE_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\.py")


def manifest_keys(manifest):
    """Return the manifest keys object, rejecting present malformed containers."""
    keys = manifest.get("keys", {})
    if not isinstance(keys, dict):
        raise AssertionError("manifest keys must be an object")
    return keys


def declared_modules(spec):
    """Return the local Python modules named by a manifest key's module field."""
    raw = spec.get("module")
    if isinstance(raw, (list, tuple)):
        raw = ",".join(str(item) for item in raw)
    return _MODULE_RE.findall(str(raw or ""))


def keyed_specs(manifest):
    """Yield (key, spec) for switchable manifest lanes with declared modules."""
    for key, spec in manifest_keys(manifest).items():
        if isinstance(spec, dict) and "default" in spec and "module" in spec:
            yield key, spec


def config_contracts(manifest):
    """Yield every manifest value that must be present and consumed at runtime."""
    keys = manifest_keys(manifest)
    for key, spec in keyed_specs(manifest):
        yield key, spec["default"]
    params = keys.get("params", {})
    if not isinstance(params, dict):
        raise AssertionError("manifest keys.params must be an object")
    for key, value in params.items():
        yield key, value


def _parse_python(files, path):
    try:
        return ast.parse(files[path].decode("utf-8"), filename=path)
    except (SyntaxError, UnicodeDecodeError) as error:
        raise AssertionError("cannot parse packed Python file %s: %s" % (path, error))


def local_import_graph(files):
    """Build a local-module import graph for root-level Python files in a package."""
    local = {
        PurePosixPath(name).stem: name
        for name in files
        if name.endswith(".py") and "/" not in name
    }
    graph = {path: set() for path in local.values()}
    for path in graph:
        tree = _parse_python(files, path)
        for node in ast.walk(tree):
            roots = []
            if isinstance(node, ast.Import):
                roots = [alias.name.split(".", 1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots = [node.module.split(".", 1)[0]]
            for root in roots:
                if root in local:
                    graph[path].add(local[root])
    return graph


def reachable_paths(files, root="main.py"):
    graph = local_import_graph(files)
    if root not in graph:
        return set()
    seen = set()
    pending = [root]
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        pending.extend(sorted(graph.get(path, ()), reverse=True))
    return seen


def _string_constant(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def executable_key_references(files, paths):
    """Return config-key names used semantically in reachable executable AST.

    Deliberately ignore arbitrary string constants, comments and docstrings. A key counts
    when code accesses it as an attribute, mapping subscript, mapping-style get/pop/
    setdefault call, or getattr/hasattr/setattr/delattr target.
    """
    refs = set()
    for path in sorted(paths):
        if not path.endswith(".py"):
            continue
        tree = _parse_python(files, path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                refs.add(node.attr)
                continue
            if isinstance(node, ast.Subscript):
                value = _string_constant(node.slice)
                if value is not None:
                    refs.add(value)
                continue
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute) and node.func.attr in {"get", "pop", "setdefault"}:
                if node.args:
                    value = _string_constant(node.args[0])
                    if value is not None:
                        refs.add(value)
            elif isinstance(node.func, ast.Name) and node.func.id in {"getattr", "hasattr", "setattr", "delattr"}:
                if len(node.args) >= 2:
                    value = _string_constant(node.args[1])
                    if value is not None:
                        refs.add(value)
    return refs


def _same_json_scalar(actual, expected):
    """Keep JSON booleans distinct from integers and integers distinct from floats."""
    return type(actual) is type(expected) and actual == expected


def validate_reachability(manifest, files, overlay):
    """Return deterministic human-readable contract failures for one built package."""
    errors = []
    if "main.py" not in files:
        errors.append("package missing main.py")
        reachable = set()
    else:
        reachable = reachable_paths(files)
        if not reachable:
            errors.append("could not derive local import graph from main.py")

    try:
        config = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
        config = {}
        errors.append("invalid or missing TITAN-CONFIG.json: %s" % type(error).__name__)

    runtime_refs = executable_key_references(files, reachable)
    contracts = list(config_contracts(manifest))
    seen_contracts = set()
    for key, expected in contracts:
        if key in seen_contracts:
            errors.append("%s: duplicate manifest config contract" % key)
            continue
        seen_contracts.add(key)
        if key not in config:
            errors.append("%s: missing from TITAN-CONFIG.json" % key)
        elif not _same_json_scalar(config[key], expected):
            errors.append("%s: config default %r != manifest %r" % (key, config[key], expected))
        if key not in runtime_refs:
            errors.append("%s: not referenced by executable code reachable from main.py" % key)

    for key, spec in keyed_specs(manifest):
        modules = declared_modules(spec)
        if not modules:
            errors.append("%s: manifest module field names no .py modules" % key)
        for module in modules:
            if module not in overlay:
                errors.append("%s: declared module %s missing from overlay" % (key, module))
                continue
            if module not in files:
                errors.append("%s: declared module %s missing from built package" % (key, module))
                continue
            if files[module] != overlay[module]:
                errors.append("%s: built %s differs from overlay source" % (key, module))
            if module not in reachable:
                errors.append("%s: %s not import-reachable from main.py" % (key, module))

    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, help="alternate canonical archive")
    args = parser.parse_args(argv)

    manifest = build_v3.manifest()
    overlay = build_v3.overlay_files()
    files = build_v3.package_files(args.canonical)
    errors = validate_reachability(manifest, files, overlay)
    if errors:
        for error in errors:
            print("V31 REACHABILITY FAIL", error, file=sys.stderr)
        return 1

    specs = list(keyed_specs(manifest))
    contracts = list(config_contracts(manifest))
    modules = sorted({module for _, spec in specs for module in declared_modules(spec)})
    print(
        "V31 REACHABILITY OK",
        len(specs),
        "lanes",
        len(contracts),
        "config contracts",
        len(modules),
        "declared modules",
        len(files),
        "packed files",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
