# SPDX-License-Identifier: Apache-2.0
"""Materialize four closure-bound V2 seller-policy factorial arms.

The frozen V2 bundle is never modified in place.  Each arm is copied to an
isolated output directory, exact source seams are patched with cardinality
checks, and a generated entrypoint verifies the complete sibling closure before
exposing ``agent`` to the official evaluator.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
SOURCE = LAB / "runtime/variants/v2"
OPERATION = "titan-v3-v1v2-seller-factorial-20260909-01"
EXPECTED_SCHEDULER_SHA256 = "72865b83e66d0c1ed27ddc35e5ab428f8212872e8e8e918f2826eb7665fbe7f8"
EXPECTED_SCHEDULER_GIT_BLOB = "7c068b7078c3d7c09bb3836590ad42b0af934cdf"

ARMS: Mapping[str, tuple[bool, bool]] = {
    "control": (False, False),
    "carry_095": (True, False),
    "force_end": (False, True),
    "both": (True, True),
}

CARRY_CONTROL = "            carry=float(self.single(inv,remaining)[0])\n"
CARRY_PATCH = "            carry=.95*self.single(inv,remaining)[0]\n"
REFERENCE_CONTROL = (
    "            # Remaining stock keeps a continuation value; no artificial liquidation.\n"
    "            reference=tuple((t,sum(q for d,q in reference if d==t)) "
    "for t in sorted({t for t,_ in reference}))\n"
)
REFERENCE_PATCH = (
    "            if rem>0:reference.append((end,rem))\n"
    "            reference=tuple((t,sum(q for d,q in reference if d==t)) "
    "for t in sorted({t for t,_ in reference}))\n"
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _ignored(relative: Path) -> bool:
    return (
        any(part in {"__pycache__", ".pytest_cache"} for part in relative.parts)
        or relative.suffix in {".pyc", ".pyo"}
    )


def tree_receipt(root: Path, *, exclude: frozenset[str] = frozenset()) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    entries: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative_path = path.relative_to(root)
        relative = relative_path.as_posix()
        if path.is_symlink():
            raise RuntimeError(f"symlink forbidden in closure: {relative}")
        if path.is_dir() or relative in exclude or _ignored(relative_path):
            continue
        if not path.is_file():
            raise RuntimeError(f"non-regular closure member: {relative}")
        content_sha = sha256_file(path)
        size = path.stat().st_size
        digest.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(content_sha))
        entries.append({"path": relative, "bytes": size, "sha256": content_sha})
    return {
        "schema_version": 1,
        "files": len(entries),
        "bytes": sum(int(item["bytes"]) for item in entries),
        "sha256": digest.hexdigest(),
        "entries": entries,
    }


def verify_frozen_source(source: Path = SOURCE) -> dict[str, Any]:
    source = source.resolve()
    freeze_path = source / "FREEZE.json"
    if not freeze_path.is_file():
        raise FileNotFoundError(freeze_path)
    manifest = json.loads(freeze_path.read_text(encoding="utf-8"))
    if manifest.get("variant") != "v2" or not isinstance(manifest.get("files"), dict):
        raise RuntimeError("unexpected V2 freeze schema")
    prefix = Path("runtime/variants/v2")
    expected_members: set[str] = {"FREEZE.json"}
    checks: dict[str, dict[str, Any]] = {}
    for declared, metadata in sorted(manifest["files"].items()):
        declared_path = Path(declared)
        try:
            relative = declared_path.relative_to(prefix)
        except ValueError as exc:
            raise RuntimeError(f"freeze member escapes V2 root: {declared}") from exc
        local = source / relative
        relative_name = relative.as_posix()
        expected_members.add(relative_name)
        if local.is_symlink() or not local.is_file():
            raise RuntimeError(f"freeze member missing or non-regular: {relative_name}")
        actual_sha = sha256_file(local)
        actual_bytes = local.stat().st_size
        expected_sha = str(metadata.get("sha256"))
        expected_bytes = int(metadata.get("bytes", -1))
        if actual_sha != expected_sha or actual_bytes != expected_bytes:
            raise RuntimeError(
                f"freeze mismatch {relative_name}: sha={actual_sha} bytes={actual_bytes}"
            )
        checks[relative_name] = {"bytes": actual_bytes, "sha256": actual_sha}

    actual_members: set[str] = set()
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if path.is_symlink():
            raise RuntimeError(f"symlink forbidden in frozen V2: {relative.as_posix()}")
        if path.is_file() and not _ignored(relative):
            actual_members.add(relative.as_posix())
    if actual_members != expected_members:
        missing = sorted(expected_members - actual_members)
        extra = sorted(actual_members - expected_members)
        raise RuntimeError(f"V2 freeze member-set drift: missing={missing}, extra={extra}")

    scheduler = (source / "scheduler.py").read_bytes()
    scheduler_sha = sha256_bytes(scheduler)
    scheduler_blob = git_blob_sha1(scheduler)
    if scheduler_sha != EXPECTED_SCHEDULER_SHA256:
        raise RuntimeError(f"unexpected frozen V2 scheduler sha256: {scheduler_sha}")
    if scheduler_blob != EXPECTED_SCHEDULER_GIT_BLOB:
        raise RuntimeError(f"unexpected frozen V2 scheduler git blob: {scheduler_blob}")
    return {
        "variant": "v2",
        "freeze_sha256": sha256_file(freeze_path),
        "scheduler_sha256": scheduler_sha,
        "scheduler_git_blob": scheduler_blob,
        "members": checks,
    }


def patch_scheduler(text: str, arm: str) -> tuple[str, dict[str, Any]]:
    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    apply_carry, apply_reference = ARMS[arm]
    counts = {
        "carry_control": text.count(CARRY_CONTROL),
        "carry_patch": text.count(CARRY_PATCH),
        "reference_control": text.count(REFERENCE_CONTROL),
        "reference_patch": text.count(REFERENCE_PATCH),
    }
    if counts != {
        "carry_control": 1,
        "carry_patch": 0,
        "reference_control": 1,
        "reference_patch": 0,
    }:
        raise RuntimeError(f"frozen V2 source seam drift: {counts}")
    patched = text
    if apply_carry:
        patched = patched.replace(CARRY_CONTROL, CARRY_PATCH, 1)
    if apply_reference:
        patched = patched.replace(REFERENCE_CONTROL, REFERENCE_PATCH, 1)
    expected = {
        "carry_control": 0 if apply_carry else 1,
        "carry_patch": 1 if apply_carry else 0,
        "reference_control": 0 if apply_reference else 1,
        "reference_patch": 1 if apply_reference else 0,
    }
    after = {
        "carry_control": patched.count(CARRY_CONTROL),
        "carry_patch": patched.count(CARRY_PATCH),
        "reference_control": patched.count(REFERENCE_CONTROL),
        "reference_patch": patched.count(REFERENCE_PATCH),
    }
    if after != expected:
        raise RuntimeError(f"arm patch cardinality failure for {arm}: {after}")
    diff = "".join(
        difflib.unified_diff(
            text.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile="frozen-v2/scheduler.py",
            tofile=f"{arm}/scheduler.py",
            n=3,
        )
    )
    return patched, {
        "arm": arm,
        "carry_discount": 0.95 if apply_carry else 1.0,
        "force_residual_reference_at_horizon": apply_reference,
        "source_counts": counts,
        "result_counts": after,
        "changed": patched != text,
        "unified_diff": diff,
    }


def _bound_entry_source(expected: Mapping[str, Any], arm: str) -> str:
    return f'''# SPDX-License-Identifier: Apache-2.0
"""Generated fail-closed entrypoint for factorial arm {arm}."""
from __future__ import annotations
import hashlib
from pathlib import Path

_EXPECTED_SHA256 = {expected["sha256"]!r}
_EXPECTED_FILES = {int(expected["files"])}
_EXPECTED_BYTES = {int(expected["bytes"])}
_ROOT = Path(__file__).resolve().parent


def _ignored(relative: Path) -> bool:
    return (any(part in {{"__pycache__", ".pytest_cache"}} for part in relative.parts)
            or relative.suffix in {{".pyc", ".pyo"}})


def _closure() -> tuple[str, int, int]:
    digest = hashlib.sha256()
    files = 0
    total = 0
    for path in sorted(_ROOT.rglob("*"), key=lambda item: item.relative_to(_ROOT).as_posix()):
        relative_path = path.relative_to(_ROOT)
        relative = relative_path.as_posix()
        if path.is_symlink():
            raise RuntimeError(f"symlink forbidden in factorial closure: {{relative}}")
        if path.is_dir() or relative == "bound_entry.py" or _ignored(relative_path):
            continue
        if not path.is_file():
            raise RuntimeError(f"non-regular factorial closure member: {{relative}}")
        payload = path.read_bytes()
        content_sha = hashlib.sha256(payload).digest()
        digest.update(relative.encode("utf-8") + b"\\0" + content_sha)
        files += 1
        total += len(payload)
    return digest.hexdigest(), files, total


_actual = _closure()
_expected = (_EXPECTED_SHA256, _EXPECTED_FILES, _EXPECTED_BYTES)
if _actual != _expected:
    raise RuntimeError(f"factorial closure mismatch: expected={{_expected}} actual={{_actual}}")

from candidate import agent as agent  # noqa: E402,F401
'''


def materialize_arm(
    arm: str,
    *,
    source: Path = SOURCE,
    output: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    source = source.resolve()
    output = output.resolve()
    if source == output or source in output.parents:
        raise ValueError("output must not be the frozen source or its descendant")
    output.parent.mkdir(parents=True, exist_ok=True)
    freeze = verify_frozen_source(source)
    original = (source / "scheduler.py").read_text(encoding="utf-8")
    patched, patch = patch_scheduler(original, arm)

    staging = output.with_name(output.name + ".staging")
    shutil.rmtree(staging, ignore_errors=True)
    shutil.copytree(source, staging, symlinks=True)
    for path in staging.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"copied factorial arm contains symlink: {path}")
    (staging / "scheduler.py").write_text(patched, encoding="utf-8", newline="\n")
    arm_record = {
        "schema_version": 1,
        "operation": OPERATION,
        "arm": arm,
        "frozen_source": {
            "variant": "v2",
            "scheduler_sha256": freeze["scheduler_sha256"],
            "scheduler_git_blob": freeze["scheduler_git_blob"],
        },
        "interventions": {
            "carry_discount": patch["carry_discount"],
            "force_residual_reference_at_horizon": patch[
                "force_residual_reference_at_horizon"
            ],
        },
        "scheduler_sha256": sha256_file(staging / "scheduler.py"),
    }
    atomic_json(staging / "ARM.json", arm_record)
    closure = tree_receipt(staging, exclude=frozenset({"bound_entry.py"}))
    (staging / "bound_entry.py").write_text(
        _bound_entry_source(closure, arm), encoding="utf-8", newline="\n"
    )
    final_bundle = tree_receipt(staging)

    shutil.rmtree(output, ignore_errors=True)
    os.replace(staging, output)
    receipt = {
        "schema_version": 1,
        "operation": OPERATION,
        "arm": arm,
        "source": freeze,
        "patch": patch,
        "closure_bound_at_entry": closure,
        "entrypoint": {
            "relative_path": "bound_entry.py",
            "sha256": sha256_file(output / "bound_entry.py"),
        },
        "materialized_bundle": final_bundle,
    }
    atomic_json(receipt_path, receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=sorted(ARMS), required=True)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = materialize_arm(
        args.arm, source=args.source, output=args.output, receipt_path=args.receipt
    )
    print(
        json.dumps(
            {
                "arm": args.arm,
                "entry_sha256": receipt["entrypoint"]["sha256"],
                "closure_sha256": receipt["closure_bound_at_entry"]["sha256"],
                "files": receipt["closure_bound_at_entry"]["files"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
