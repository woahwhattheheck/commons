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

def authenticate_repo(kg_root: Path, *, repo_pins=REPO_GIT_BLOBS):
    kg=Path(kg_root).resolve(strict=True); repo={}
    for rel,pin in repo_pins.items():
        p=(kg/rel).resolve(strict=True)
        try: p.relative_to(kg)
        except ValueError: raise ChampionError(f"repo path escaped: {rel}")
        data=p.read_bytes()
        if _git_blob(data)!=pin: raise ChampionError(f"repo authority drift: {rel}")
        repo[rel]={"git_blob":pin,"sha256":hashlib.sha256(data).hexdigest()}
    return repo

def authenticate_engine(engine_dir: Path, *, engine_pins=ENGINE_GIT_BLOBS):
    eng=Path(engine_dir).resolve(strict=True); engine={}
    for name,pin in engine_pins.items():
        p=(eng/name).resolve(strict=True)
        try: p.relative_to(eng)
        except ValueError: raise ChampionError(f"engine path escaped: {name}")
        data=p.read_bytes()
        if _git_blob(data)!=pin: raise ChampionError(f"engine authority drift: {name}")
        engine[name]=hashlib.sha256(data).hexdigest()
    return engine

def authenticate_harness(kg_root: Path, engine_dir: Path, *,
                         repo_pins=REPO_GIT_BLOBS, engine_pins=ENGINE_GIT_BLOBS):
    return {"repo":authenticate_repo(kg_root,repo_pins=repo_pins),
            "engine":authenticate_engine(engine_dir,engine_pins=engine_pins)}

def load_manifest(path: Path, *, expected_sha256=CORPUS_MANIFEST_SHA256,
                  expected_targets=EXPECTED_TARGETS, replays_per_target=EXPECTED_REPLAYS_PER_TARGET):
    manifest, sha=_read_json(path)
    if sha != expected_sha256: raise ChampionError("corpus manifest SHA256 mismatch")
    if type(manifest) is not dict or manifest.get("schema")!="titan.gauntlet.top30-union.v1":
        raise ChampionError("unexpected corpus manifest schema")
    targets=manifest.get("targets")
    if type(targets) is not list or len(targets)!=expected_targets:
        raise ChampionError(f"expected {expected_targets} corpus targets")
    fixtures=[]; seen_sub=set(); seen_fixture=set()
    for ti,target in enumerate(targets):
        if type(target) is not dict or target.get("status")!="complete":
            raise ChampionError(f"target[{ti}] is incomplete")
        sub=_plain_int(target.get("submission_id"), f"target[{ti}].submission_id", 1)
        if sub in seen_sub: raise ChampionError("duplicate submission_id")
        seen_sub.add(sub)
        replays=target.get("replays")
        if type(replays) is not list or len(replays)!=replays_per_target:
            raise ChampionError(f"submission {sub} must have {replays_per_target} replays")
        for ri,replay in enumerate(replays):
            if type(replay) is not dict or replay.get("kind")!="recorded_action_trace":
                raise ChampionError(f"submission {sub} replay[{ri}] malformed")
            ep=_plain_int(replay.get("episode_id"), "episode_id", 1)
            seed=_plain_int(replay.get("seed"), "seed", 0)
            recorded_seat=_plain_int(replay.get("recorded_opponent_seat"), "recorded_opponent_seat", 0)
            if recorded_seat not in (0,1): raise ChampionError("recorded_opponent_seat must be 0 or 1")
            fid=f"trace-sub-{sub}-ep-{ep}"
            if fid in seen_fixture: raise ChampionError("duplicate fixture id")
            seen_fixture.add(fid)
            fixtures.append({"id":fid,"submission_id":sub,"seed":seed,
                             "candidate_seat_for_recorded_orientation":1-recorded_seat})
    return {"sha256":sha,"fixtures":fixtures,"target_count":len(targets)}
