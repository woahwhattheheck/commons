# SPDX-License-Identifier: Apache-2.0
"""Static closure-checking entrypoint copied beside one measured V2 arm."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import sys
from pathlib import Path
from typing import Any

EXPECTED_CANDIDATE_SHA256 = "2e4897fb3aa8b0bee3e97709808c3aa25fa5055bcf5ce7d433b493eb334870f2"


class BoundClosureError(RuntimeError):
    """The measured package no longer matches its execution binding."""


def _strict_object(path: Path) -> dict[str, Any]:
    def reject_pairs(pairs):
        output = {}
        for key, value in pairs:
            if key in output:
                raise BoundClosureError(f"duplicate JSON key {key!r} in {path.name}")
            output[key] = value
        return output

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                BoundClosureError(f"non-finite JSON token {token} in {path.name}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BoundClosureError(
            f"cannot read {path.name}: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise BoundClosureError(f"{path.name} must contain one JSON object")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _closure(root: Path) -> str:
    if not root.is_dir():
        raise BoundClosureError(f"bound package is not a directory: {root.name}")
    digest = hashlib.sha256()
    found = False
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise BoundClosureError(f"non-regular package member: {relative}")
        data = path.read_bytes()
        found = True
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(_sha256(data).encode("ascii"))
        digest.update(b"\0")
    if not found:
        raise BoundClosureError("bound package is empty")
    return digest.hexdigest()


def _sha256_value(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise BoundClosureError(f"{label} is not a lowercase SHA-256 digest")
    return value


_here = Path(__file__).resolve()
_label = _here.stem.removesuffix("_entry")
if _label not in {"control", "candidate"}:
    raise BoundClosureError("entrypoint filename must be control_entry.py or candidate_entry.py")
_binding_path = _here.with_name(f"{_label}.binding.json")
_binding = _strict_object(_binding_path)
if _binding.get("schema_version") != 1 or _binding.get("label") != _label:
    raise BoundClosureError("entrypoint sidecar identity mismatch")
if _binding.get("package") != _label or _binding.get("candidate_entry") != "candidate.py":
    raise BoundClosureError("entrypoint sidecar package contract mismatch")
if _binding.get("candidate_entry_sha256") != EXPECTED_CANDIDATE_SHA256:
    raise BoundClosureError("entrypoint sidecar is not bound to the frozen V2 candidate")

_package = _here.with_name(_label)
_expected_closure = _sha256_value(
    _binding.get("closure_sha256"), "expected package closure"
)
_actual_closure = _closure(_package)
if _actual_closure != _expected_closure:
    raise BoundClosureError(
        f"{_label} package closure mismatch: expected {_expected_closure}, got {_actual_closure}"
    )
_entry = _package / "candidate.py"
if _sha256(_entry.read_bytes()) != EXPECTED_CANDIDATE_SHA256:
    raise BoundClosureError("frozen V2 candidate entry bytes drifted")

# Each evaluator actor is a fresh process. Prepending the exact measured package
# makes its bare sibling imports resolve inside the closure just verified above.
sys.path.insert(0, str(_package))
_spec = importlib.util.spec_from_file_location(
    f"v2_bound_{_label}_{_actual_closure[:12]}", _entry
)
if _spec is None or _spec.loader is None:
    raise BoundClosureError("cannot construct frozen V2 candidate module")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
agent = getattr(_module, "agent", None)
if not callable(agent):
    raise BoundClosureError("frozen V2 candidate does not export callable agent")
