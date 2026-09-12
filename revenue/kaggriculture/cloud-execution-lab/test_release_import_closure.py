# SPDX-License-Identifier: Apache-2.0
"""Fail closed when a canonical root runtime import is omitted from the archive."""
from __future__ import annotations

import ast
from pathlib import Path, PurePosixPath
import unittest

import build_integrated


ROOT = Path(__file__).resolve().parent


def _module_path(name: str) -> str:
    return name.replace(".", "/")


def _archive_provides(paths: set[str], name: str) -> bool:
    """Whether archive paths can satisfy an absolute Python module import."""
    stem = _module_path(name)
    if f"{stem}.py" in paths or f"{stem}/__init__.py" in paths:
        return True
    prefix = stem + "/"
    return any(path.startswith(prefix) and path.endswith(".py") for path in paths)


def _local_module_exists(source: Path, name: str) -> bool:
    """Resolve only repo-local modules; stdlib/third-party imports are out of scope."""
    relative = Path(*name.split("."))
    for base in (source.parent, ROOT):
        target = base / relative
        if target.with_suffix(".py").is_file() or (target / "__init__.py").is_file():
            return True
        if target.is_dir() and any(target.glob("*.py")):
            return True
    return False


def _relative_archive_name(destination: str, level: int, module: str | None) -> str | None:
    package = list(PurePosixPath(destination).parent.parts)
    if level <= 0:
        return module
    climb = level - 1
    if climb > len(package):
        return None
    package = package[: len(package) - climb]
    if module:
        package.extend(module.split("."))
    return ".".join(package) if package else None


def _relative_local_exists(source: Path, level: int, module: str | None) -> bool:
    base = source.parent
    for _ in range(max(0, level - 1)):
        base = base.parent
    if module:
        base = base.joinpath(*module.split("."))
    if base.with_suffix(".py").is_file() or (base / "__init__.py").is_file():
        return True
    return base.is_dir() and any(base.glob("*.py"))


def _runtime_destinations(mapping: dict[str, str]) -> set[str]:
    """Archive-root Python modules imported under ordinary submission sys.path."""
    return {path for path in mapping if path.endswith(".py") and "/" not in path}


class ReleaseImportClosureTests(unittest.TestCase):
    def test_repo_local_root_runtime_imports_are_packaged(self):
        mapping = build_integrated.source_files()
        archive_paths = set(mapping)
        missing: list[tuple[str, str, str]] = []

        for destination in sorted(_runtime_destinations(mapping)):
            source_name = mapping[destination]
            source = (ROOT / source_name).resolve()
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.name
                        if not _archive_provides(archive_paths, name) and _local_module_exists(source, name):
                            missing.append((destination, source_name, name))
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        name = _relative_archive_name(destination, node.level, node.module)
                        if (name and not _archive_provides(archive_paths, name)
                                and _relative_local_exists(source, node.level, node.module)):
                            missing.append((destination, source_name, "." * node.level + (node.module or "")))
                    elif node.module:
                        name = node.module
                        if not _archive_provides(archive_paths, name) and _local_module_exists(source, name):
                            missing.append((destination, source_name, name))

        self.assertEqual(
            missing,
            [],
            "canonical archive omits repo-local root-runtime imports: "
            + "; ".join(f"{dest} ({src}) -> {name}" for dest, src, name in missing),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
