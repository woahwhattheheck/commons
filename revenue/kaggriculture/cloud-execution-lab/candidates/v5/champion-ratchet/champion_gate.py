#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticate and score a full V5 champion panel against exact submitted V3.1."""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, sys, uuid
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "titan-v5-champion-ratchet-receipt/v2"
V31_ARCHIVE_SHA256 = "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"
V31_SOURCE_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
V31_SUBMISSION_ID = 56172377
CORPUS_MANIFEST_SHA256 = "510ca5c5438fb65d29755f2009f07bb85bbf3e8963054b88c4abe3ec3737924e"
CORPUS_REL = "cloud-execution-lab/candidates/v5/gauntlet-top30-union/manifest.json"
EXPECTED_TARGETS = 41
EXPECTED_REPLAYS_PER_TARGET = 3
EXPECTED_CALLBACKS = 719
REPO_GIT_BLOBS = {
    "cloud-execution-lab/reference/evaluator/evaluate.py": "1fb6b655bb4ca1e1684be165a8ef513e2e6c2325",
    "20260907-offline-agent/evaluate.py": "23948e10cfc3d32f46c9abb1321b0d8fc8db21d5",
    "cloud-pack/pack.py": "2407c7467fc60eda8864283d736c743a886bc549",
}
ENGINE_GIT_BLOBS = {
    "kaggriculture.py": "3c202c7ee921da239356789e266b694635103fc4",
    "kaggriculture.json": "b354d06b742fe48402513792253f1a5c29366b20",
    "utils.py": "91c8822ee6201ba4a5a8416c7dbe34f95dd61c87",
}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")

class ChampionError(ValueError):
    pass

def _strict_object(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ChampionError(f"duplicate JSON key: {k}")
        out[k]=v
    return out

def _reject_constant(token):
    raise ChampionError(f"non-finite JSON constant: {token}")

def _loads(raw: bytes, source: str):
    try:
        text=raw.decode("utf-8")
        return json.loads(text, object_pairs_hook=_strict_object, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ChampionError(f"{source}: invalid UTF-8 JSON") from exc

def _read_json(path: Path):
    path=Path(path)
    try: raw=path.read_bytes()
    except OSError as exc: raise ChampionError(f"cannot read {path}") from exc
    return _loads(raw, str(path)), hashlib.sha256(raw).hexdigest()

def _canon(v):
    return json.dumps(v, sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False).encode()

def _digest(v):
    return hashlib.sha256(_canon(v)).hexdigest()

def _git_blob(data: bytes):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _sha_file(path: Path):
    try: data=Path(path).read_bytes()
    except OSError as exc: raise ChampionError(f"cannot read {path}") from exc
    return hashlib.sha256(data).hexdigest()

def _plain_int(v, field, lo=0):
    if type(v) is not int or v < lo: raise ChampionError(f"{field} must be a plain int >= {lo}")
    return v

def _score(v, field):
    if type(v) not in (int,float) or not math.isfinite(v): raise ChampionError(f"{field} must be finite")
    return v

def authenticate_v31_identity(*, source_commit=None, submission_id=None, archive_sha256=None):
    """Bind source+submission+archive. Stale claimed identity is non-authorizing."""
    if source_commit is None:
        source_commit = V31_SOURCE_COMMIT
    if submission_id is None:
        submission_id = V31_SUBMISSION_ID
    if archive_sha256 is None:
        archive_sha256 = V31_ARCHIVE_SHA256
    if type(source_commit) is not str or _HEX40.fullmatch(source_commit) is None:
        raise ChampionError("V3.1 source_commit malformed")
    if source_commit != V31_SOURCE_COMMIT:
        raise ChampionError("stale V3.1 source_commit")
    if type(submission_id) is not int or submission_id != V31_SUBMISSION_ID:
        raise ChampionError("stale V3.1 submission_id")
    if type(archive_sha256) is not str or _HEX64.fullmatch(archive_sha256) is None:
        raise ChampionError("V3.1 archive SHA256 malformed")
    if archive_sha256 != V31_ARCHIVE_SHA256:
        raise ChampionError("V3.1 archive bytes do not match exact submitted V3.1")
    return {
        "v31_source_commit": V31_SOURCE_COMMIT,
        "v31_submission_id": V31_SUBMISSION_ID,
        "v31_archive_sha256": V31_ARCHIVE_SHA256,
    }
