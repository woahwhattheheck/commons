# SPDX-License-Identifier: Apache-2.0
"""Hash-bound reuse of the reviewed SOL-KEEL execution-custody helpers."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, MutableMapping

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "v2-forced-feasibility-ablation-sol-keel"

EXPECTED_PARENT_BLOBS = {
    "bind_execution.py": "3bf8cfb22f2708be37b0f7955444e7a36a6e258d",
    "compare.py": "49614b4ec0eb5e5c09f5d345dd13c3c982b6ab39",
    "compare_bound.py": "ab516c55b909ed922b2a821ccebc52c1dfd831df",
    "materialize_evaluator.py": "fe535fda2573ce198e34da4c4639ab14587ba8b8",
}


class DelegateError(RuntimeError):
    """A reviewed parent helper is unavailable or has changed bytes."""


def git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def load_parent(filename: str, module_name: str) -> ModuleType:
    expected = EXPECTED_PARENT_BLOBS.get(filename)
    if expected is None:
        raise DelegateError(f"unregistered parent helper: {filename}")
    path = PARENT / filename
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise DelegateError(f"cannot read parent helper {path}: {exc}") from exc
    actual = git_blob_sha1(data)
    if actual != expected:
        raise DelegateError(
            f"parent helper drift for {filename}: expected {expected}, got {actual}"
        )
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise DelegateError(f"cannot construct import for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reexport(module: ModuleType, namespace: MutableMapping[str, Any]) -> None:
    for name in dir(module):
        if name.startswith("__"):
            continue
        namespace[name] = getattr(module, name)
