#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact submitted-V4 module-cache namespace-binding ablation helpers."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import PurePosixPath
import tarfile

BASELINE_SHA256 = "4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b"
V31_RUNTIME_GIT_BLOB = "a10ad66f990c430dc27299f518b04ea3fde9e39b"
V4_RUNTIME_GIT_BLOB = "998bf5da08f61f82eafaf5750c8a86fc3adad7fb"
RUNTIME_MEMBER = "titan_runtime.py"

V31_CACHE_HIT = (
    "    if cache and key in _MODULE_CACHE:\n"
    "        return _MODULE_CACHE[key]\n"
)
V4_CACHE_HIT = (
    "    if cache and key in _MODULE_CACHE:\n"
    "        # A different relocated package may have rebound this public name.\n"
    "        # Restore this completed module before a sibling imports the name.\n"
    "        module = _MODULE_CACHE[key]\n"
    "        sys.modules[name] = module\n"
    "        return module\n"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_bytes(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def archive_members_bytes(raw: bytes) -> dict[str, bytes]:
    """Parse one already-captured archive buffer; never reopen caller paths."""
    if type(raw) is not bytes:
        raise TypeError("archive bytes must be bytes")
    data: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as archive:
        for member in archive:
            rel = PurePosixPath(member.name)
            if (not member.name or "\\" in member.name or rel.is_absolute()
                    or ".." in rel.parts or str(rel) != member.name.rstrip("/")):
                raise ValueError(f"Invalid archive path: {member.name}")
            if member.isdir():
                continue
            if not member.isfile() or member.name in data:
                raise ValueError(f"Non-file or duplicate member: {member.name}")
            if member.size > 100 * 1024**2:
                raise ValueError(f"Oversized member: {member.name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"Unreadable archive member: {member.name}")
            with stream:
                payload = stream.read()
            if len(payload) != member.size:
                raise ValueError(f"Truncated archive member: {member.name}")
            data[member.name] = payload
    if "main.py" not in data or "frozen_selected.py" not in data:
        raise ValueError("Expected canonical V4 flat archive layout")
    return data


def rewrite_cache_hit_v31(raw: bytes, expected_blob: str | None = None) -> bytes:
    """Restore only exact V3.1 cache-hit namespace behavior in exact V4 runtime."""
    if type(raw) is not bytes:
        raise TypeError("runtime source must be bytes")
    expected_blob = V4_RUNTIME_GIT_BLOB if expected_blob is None else expected_blob
    actual = git_blob_bytes(raw)
    if actual != expected_blob:
        raise ValueError(f"runtime source drift: expected {expected_blob}, got {actual}")
    text = raw.decode("utf-8")
    if text.count(V4_CACHE_HIT) != 1:
        raise ValueError("exact V4 cache-hit block not found exactly once")
    if V31_CACHE_HIT in text:
        raise ValueError("V3.1 cache-hit block already present in V4 preimage")
    changed = text.replace(V4_CACHE_HIT, V31_CACHE_HIT, 1)
    compile(changed, "<module-cache-binding-treatment>", "exec")
    result = changed.encode("utf-8")
    if result == raw:
        raise AssertionError("module-cache ablation did not change runtime")
    return result


def exact_v4_arms(baseline_raw: bytes) -> dict[str, dict[str, bytes]]:
    """Return exact V4 control plus one-member V3.1 cache-hit treatment."""
    if type(baseline_raw) is not bytes:
        raise TypeError("baseline archive capture must be bytes")
    actual = sha256_bytes(baseline_raw)
    if actual != BASELINE_SHA256:
        raise ValueError(f"baseline is not exact submitted V4: {actual}")
    control = archive_members_bytes(baseline_raw)
    runtime = control.get(RUNTIME_MEMBER, b"")
    if git_blob_bytes(runtime) != V4_RUNTIME_GIT_BLOB:
        raise ValueError("submitted V4 titan_runtime.py preimage mismatch")
    treatment = dict(control)
    treatment[RUNTIME_MEMBER] = rewrite_cache_hit_v31(runtime)
    if set(treatment) != set(control):
        raise AssertionError("treatment changed archive membership")
    changed = [name for name in control if control[name] != treatment[name]]
    if changed != [RUNTIME_MEMBER]:
        raise AssertionError(f"expected only {RUNTIME_MEMBER} to change; got {changed}")
    return {"control": control, "v31_cache_hit": treatment}


def treatment_receipt(baseline_raw: bytes) -> dict:
    arms = exact_v4_arms(baseline_raw)
    control = arms["control"]
    treatment = arms["v31_cache_hit"]
    return {
        "schema": "astra.v5.v31-v4-module-cache-binding-ablation.v1",
        "baseline_archive_sha256": sha256_bytes(baseline_raw),
        "v31_runtime_git_blob": V31_RUNTIME_GIT_BLOB,
        "v4_runtime_git_blob": V4_RUNTIME_GIT_BLOB,
        "changed_members": [
            name for name in control if control[name] != treatment[name]
        ],
        "control_runtime_sha256": sha256_bytes(control[RUNTIME_MEMBER]),
        "treatment_runtime_sha256": sha256_bytes(treatment[RUNTIME_MEMBER]),
        "treatment_runtime_git_blob": git_blob_bytes(treatment[RUNTIME_MEMBER]),
        "semantic_delta": (
            "On a path-aware cache hit, V4 restores the cached module into "
            "sys.modules[name]; treatment restores exact V3.1 behavior and "
            "returns the cached module without rebinding that public name."
        ),
    }


def encoded(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
