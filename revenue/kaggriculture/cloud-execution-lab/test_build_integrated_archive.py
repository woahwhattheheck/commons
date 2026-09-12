# SPDX-License-Identifier: Apache-2.0
"""Regression coverage for standalone TITAN release closure."""
import ast
import io
import json
from pathlib import Path
import tarfile

import build_integrated


def test_enabled_town_procurement_is_in_standalone_archive():
    config = json.loads((build_integrated.ROOT / "TITAN-CONFIG.json").read_text())
    assert config["town_procurement"] is True

    data, _manifest, receipt = build_integrated.render()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        names = set(archive.getnames())

    assert "main.py" in names
    assert "town_procurement.py" in names
    assert receipt["runtime_files"] == len(build_integrated.source_files())


def _absolute_import_roots(source):
    tree = ast.parse(source)
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_packaged_root_modules_are_closed_over_local_imports():
    """A packaged root module cannot depend on an omitted local root module."""
    mapping = build_integrated.source_files()
    missing = {}
    for member, source_path in mapping.items():
        if "/" in member or not member.endswith(".py"):
            continue
        source = (build_integrated.ROOT / source_path).read_text()
        omitted = sorted(
            name for name in _absolute_import_roots(source)
            if (build_integrated.ROOT / f"{name}.py").is_file()
            and f"{name}.py" not in mapping
        )
        if omitted:
            missing[member] = omitted

    assert not missing, f"standalone local-import closure holes: {missing}"
