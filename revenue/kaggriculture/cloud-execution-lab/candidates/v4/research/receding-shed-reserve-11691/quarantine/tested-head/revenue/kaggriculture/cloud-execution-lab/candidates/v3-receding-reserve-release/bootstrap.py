# SPDX-License-Identifier: Apache-2.0
"""Source-tree bootstrap shared by the paired control and candidate."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]


def install_source_paths() -> None:
    """Expose exactly the root modules packaged by build_integrated."""
    for path in (LAB, HERE):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)

    from build_integrated import source_files

    parents: list[Path] = []
    seen: set[Path] = set()
    for member, source in source_files().items():
        if Path(member).parent != Path("."):
            continue
        origin = (LAB / source).resolve()
        if not origin.is_file():
            raise FileNotFoundError(
                f"mapped root module {member!r} is missing at {origin}"
            )
        parent = origin.parent
        if parent not in seen:
            seen.add(parent)
            parents.append(parent)
    # Keep candidate-local modules first, then the canonical lab, then mapped
    # external roots in deterministic manifest order.
    for parent in reversed(parents):
        text = str(parent)
        if text not in sys.path:
            sys.path.insert(2, text)


def load_canonical(module_name: str):
    install_source_paths()
    spec = importlib.util.spec_from_file_location(module_name, LAB / "main.py")
    if spec is None or spec.loader is None:
        raise ImportError("unable to load canonical Titan entrypoint")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
