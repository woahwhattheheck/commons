#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compile an exact-prestate-certified child of an S13 prefix route arm."""
from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping
import zlib

from certified_route_runtime import (
    CERTIFICATE_DONOR_BLOB,
    CERTIFICATE_DONOR_HEAD,
    CERTIFICATE_MODE,
    CertificateError,
    canonical,
    exact_action,
    prestate_certificate,
    sha,
    strict_json,
)

SCHEMA = "titan-v3-s13-certified-prefix/v1"
RECEIPT_SCHEMA = "titan-v3-s13-certified-prefix-receipt/v1"
SHA256_RE = re.compile(r"[0-9a-f]{64}")
REQUIRED = (
    "ARM_ID",
    "PARENT_ARM_ID",
    "PREFIX_CUTOFF",
    "SOURCE_EPISODE",
    "SOURCE_TEAM",
    "SOURCE_SEAT",
    "SOURCE_REWARD",
    "SOURCE_SHA256",
    "PARENT_TAPE_SHA256",
    "TAPE_SHA256",
    "_PACKED",
)


class CertifiedPrefixError(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _literal_metadata(path: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        source = path.read_bytes()
        tree = ast.parse(source.decode("utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise CertifiedPrefixError(f"cannot read/parse source arm: {exc}") from exc
    found: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in REQUIRED:
            continue
        if target.id in found:
            raise CertifiedPrefixError(f"duplicate source-arm literal: {target.id}")
        try:
            found[target.id] = ast.literal_eval(node.value)
        except (TypeError, ValueError, SyntaxError) as exc:
            raise CertifiedPrefixError(f"{target.id} must be a literal") from exc
    missing = [name for name in REQUIRED if name not in found]
    if missing:
        raise CertifiedPrefixError(f"source arm is missing literals: {missing!r}")
    return source, found


def _mode(meta: Mapping[str, Any]) -> str:
    parent = meta.get("PARENT_ARM_ID")
    if not isinstance(parent, str):
        raise CertifiedPrefixError("PARENT_ARM_ID must be a string")
    matches = [mode for mode in CERTIFICATE_MODE if parent.endswith("--" + mode)]
    if len(matches) != 1:
        raise CertifiedPrefixError("cannot derive one route mode from PARENT_ARM_ID")
    return matches[0]


def decode_prefix_arm(
    path: Path,
    *,
    expected_python_sha256: str | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    source, meta = _literal_metadata(path)
    python_sha = sha256(source)
    if expected_python_sha256 is not None and python_sha != expected_python_sha256:
        raise CertifiedPrefixError(
            f"source arm SHA-256 mismatch: expected={expected_python_sha256} actual={python_sha}"
        )
    if not isinstance(meta["_PACKED"], str) or not isinstance(meta["TAPE_SHA256"], str):
        raise CertifiedPrefixError("packed tape literals must be strings")
    try:
        raw = zlib.decompress(base64.b85decode(meta["_PACKED"].encode("ascii")))
    except (UnicodeEncodeError, ValueError, zlib.error) as exc:
        raise CertifiedPrefixError(f"cannot decode source tape: {exc}") from exc
    if sha256(raw) != meta["TAPE_SHA256"]:
        raise CertifiedPrefixError("source tape SHA-256 mismatch")
    try:
        tape_value = strict_json(raw, "source tape")
    except CertificateError as exc:
        raise CertifiedPrefixError(str(exc)) from exc
    if not isinstance(tape_value, Mapping) or not tape_value:
        raise CertifiedPrefixError("source tape must be a nonempty object")
    numbered: dict[int, dict[str, Any]] = {}
    for key, entry in tape_value.items():
        if (
            not isinstance(key, str)
            or not key.isdigit()
            or str(int(key)) != key
            or not isinstance(entry, Mapping)
            or int(key) in numbered
        ):
            raise CertifiedPrefixError("source tape has a noncanonical step or entry")
        numbered[int(key)] = dict(entry)
    cutoff = meta.get("PREFIX_CUTOFF")
    if type(cutoff) is not int or cutoff < 24:
        raise CertifiedPrefixError("PREFIX_CUTOFF must be an integer >= 24")
    if sorted(numbered) != list(range(cutoff + 1)):
        raise CertifiedPrefixError("source tape must be contiguous from zero through PREFIX_CUTOFF")
    if not isinstance(meta.get("SOURCE_EPISODE"), str) or not meta["SOURCE_EPISODE"].isdigit():
        raise CertifiedPrefixError("SOURCE_EPISODE must be a decimal string")
    if type(meta.get("SOURCE_SEAT")) is not int or meta["SOURCE_SEAT"] < 0:
        raise CertifiedPrefixError("SOURCE_SEAT must be a nonnegative integer")
    for field in ("SOURCE_SHA256", "PARENT_TAPE_SHA256", "TAPE_SHA256"):
        if not isinstance(meta.get(field), str) or not SHA256_RE.fullmatch(meta[field]):
            raise CertifiedPrefixError(f"{field} is not a SHA-256 digest")
    return (
        dict(meta, python_sha256=python_sha, mode=_mode(meta)),
        {str(step): numbered[step] for step in range(cutoff + 1)},
    )


def _observation(value: Any, label: str) -> Mapping[str, Any]:
    if isinstance(value, str):
        try:
            value = strict_json(value.encode("utf-8"), label)
        except CertificateError as exc:
            raise CertifiedPrefixError(str(exc)) from exc
    if not isinstance(value, Mapping):
        raise CertifiedPrefixError(f"{label}: observation is not an object")
    return value


def _signature(observation: Mapping[str, Any], seat: int) -> dict[str, int]:
    farms = observation.get("farms")
    if not isinstance(farms, list) or not 0 <= seat < len(farms):
        raise CertifiedPrefixError("observation lacks source-seat farm")
    farm = farms[seat]
    if not isinstance(farm, Mapping):
        raise CertifiedPrefixError("source-seat farm is not an object")
    hands = farm.get("hands")
    quadrants = farm.get("unlocked_quadrants")
    if not isinstance(hands, list) or not isinstance(quadrants, list):
        raise CertifiedPrefixError("source farm hands/quadrants are not arrays")
    return {"hands": len(hands), "quadrants": len(quadrants)}


def _team_names(replay: Mapping[str, Any], seats: int) -> list[str]:
    info = replay.get("info")
    raw = info.get("TeamNames") if isinstance(info, Mapping) else None
    if isinstance(raw, Mapping):
        return [str(raw.get(str(i), raw.get(i, f"seat-{i}"))) for i in range(seats)]
    if isinstance(raw, list) and len(raw) >= seats:
        return [str(raw[i]) for i in range(seats)]
    return [f"seat-{i}" for i in range(seats)]


def load_source_replay(
    path: Path,
    *,
    expected_sha256: str,
    expected_episode: str,
    expected_seat: int,
    expected_team: str,
) -> tuple[dict[int, tuple[int, Mapping[str, Any], dict[str, Any]]], Mapping[str, Any], dict[str, Any]]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise CertifiedPrefixError(f"cannot read source replay: {exc}") from exc
    actual_sha = sha256(data)
    if actual_sha != expected_sha256:
        raise CertifiedPrefixError(
            f"source replay SHA-256 mismatch: expected={expected_sha256} actual={actual_sha}"
        )
    try:
        replay = strict_json(data, str(path))
    except CertificateError as exc:
        raise CertifiedPrefixError(str(exc)) from exc
    if not isinstance(replay, Mapping):
        raise CertifiedPrefixError("source replay root is not an object")
    steps = replay.get("steps")
    if not isinstance(steps, list) or len(steps) < 2 or not isinstance(steps[0], list):
        raise CertifiedPrefixError("source replay has no usable steps")
    seats = len(steps[0])
    if not 0 <= expected_seat < seats:
        raise CertifiedPrefixError("source seat is absent from replay")
    teams = _team_names(replay, seats)
    if teams[expected_seat] != expected_team:
        raise CertifiedPrefixError(
            f"source team mismatch: expected={expected_team!r} actual={teams[expected_seat]!r}"
        )
    configuration = replay.get("configuration")
    if not isinstance(configuration, Mapping):
        raise CertifiedPrefixError("source replay configuration is not an object")
    rows: dict[int, tuple[int, Mapping[str, Any], dict[str, Any]]] = {}
    for frame in range(len(steps) - 1):
        before_frame, after_frame = steps[frame], steps[frame + 1]
        if not isinstance(before_frame, list) or not isinstance(after_frame, list):
            raise CertifiedPrefixError(f"episode {expected_episode}: malformed frame {frame}")
        if expected_seat >= len(before_frame) or expected_seat >= len(after_frame):
            raise CertifiedPrefixError(f"episode {expected_episode}: source seat missing at frame {frame}")
        before, after = before_frame[expected_seat], after_frame[expected_seat]
        if not isinstance(before, Mapping) or not isinstance(after, Mapping):
            raise CertifiedPrefixError(f"episode {expected_episode}: malformed seat frame {frame}")
        action = after.get("action")
        if action is None:
            continue
        obs = _observation(
            before.get("observation"),
            f"episode {expected_episode} frame {frame} observation",
        )
        step = obs.get("step", frame)
        if type(step) is not int or step < 0:
            raise CertifiedPrefixError(f"episode {expected_episode}: invalid step at frame {frame}")
        if step in rows:
            raise CertifiedPrefixError(f"episode {expected_episode}: duplicate action step {step}")
        try:
            normalized = exact_action(action)
        except CertificateError as exc:
            raise CertifiedPrefixError(
                f"episode {expected_episode} seat {expected_seat} step {step}: {exc}"
            ) from exc
        rows[step] = (frame, obs, normalized)
    identity = {
        "episode": expected_episode,
        "seat": expected_seat,
        "team": expected_team,
        "bytes": len(data),
        "sha256": actual_sha,
        "frames": len(steps),
        "actions": len(rows),
    }
    return rows, configuration, identity


def certify_tape(
    tape: Mapping[str, Mapping[str, Any]],
    replay_rows: Mapping[int, tuple[int, Mapping[str, Any], dict[str, Any]]],
    configuration: Mapping[str, Any],
    *,
    seat: int,
    certificate_mode: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    certified: dict[str, dict[str, Any]] = {}
    certificates: list[dict[str, Any]] = []
    observation_hashes: list[str] = []
    owned = 0
    for key in sorted(tape, key=int):
        step = int(key)
        entry = tape[key]
        replay_row = replay_rows.get(step)
        if replay_row is None:
            raise CertifiedPrefixError(f"source replay has no aligned action for tape step {step}")
        frame, observation, replay_action = replay_row
        try:
            tape_action = exact_action(entry.get("action"))
        except CertificateError as exc:
            raise CertifiedPrefixError(f"tape step {step}: {exc}") from exc
        if canonical(tape_action) != canonical(replay_action):
            raise CertifiedPrefixError(f"tape/replay action mismatch at step {step}")
        signature = entry.get("signature")
        if signature != _signature(observation, seat):
            raise CertifiedPrefixError(f"tape/replay structural signature mismatch at step {step}")
        try:
            certificate = prestate_certificate(
                observation,
                configuration,
                tape_action,
                seat=seat,
                mode=certificate_mode,
            )
        except CertificateError as exc:
            raise CertifiedPrefixError(f"cannot certify step {step}: {exc}") from exc
        observation_sha = sha(observation)
        row = dict(entry)
        row["certificate"] = certificate
        row["source_frame"] = frame
        row["source_observation_sha256"] = observation_sha
        certified[key] = row
        certificates.append(certificate)
        observation_hashes.append(observation_sha)
        owned += step >= 24
    summary = {
        "rows": len(certified),
        "owned_rows": owned,
        "first_step": min(map(int, certified)),
        "last_step": max(map(int, certified)),
        "certificate_set_sha256": sha(certificates),
        "source_observation_set_sha256": sha(observation_hashes),
    }
    return certified, summary


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise CertifiedPrefixError(f"refusing to replace existing output: {path}")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _distinct_paths(paths: Mapping[str, Path]) -> None:
    resolved: dict[Path, str] = {}
    for label, path in paths.items():
        candidate = path.resolve(strict=False)
        prior = resolved.get(candidate)
        if prior is not None:
            raise CertifiedPrefixError(f"path alias: {label} and {prior} resolve to {candidate}")
        resolved[candidate] = label


def render(
    *,
    meta: Mapping[str, Any],
    tape: Mapping[str, Mapping[str, Any]],
    runtime: Path,
    baseline: Path,
) -> tuple[str, bytes]:
    raw = json.dumps(
        tape,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    packed = base64.b85encode(zlib.compress(raw, 9)).decode("ascii")
    certified_id = f"{meta['ARM_ID']}--certified"
    source = f'''# SPDX-License-Identifier: Apache-2.0
# Deterministically generated by certified_prefix.py; research arm, not canonical runtime.
from __future__ import annotations
import base64, hashlib, importlib.util, json, zlib

ARM_ID = {certified_id!r}
PARENT_ARM_ID = {meta['ARM_ID']!r}
PREFIX_CUTOFF = {meta['PREFIX_CUTOFF']!r}
SOURCE_EPISODE = {meta['SOURCE_EPISODE']!r}
SOURCE_TEAM = {meta['SOURCE_TEAM']!r}
SOURCE_SEAT = {meta['SOURCE_SEAT']!r}
SOURCE_REWARD = {meta['SOURCE_REWARD']!r}
SOURCE_SHA256 = {meta['SOURCE_SHA256']!r}
PARENT_TAPE_SHA256 = {meta['TAPE_SHA256']!r}
TAPE_SHA256 = {sha256(raw)!r}
ROUTE_MODE = {meta['mode']!r}
CERTIFICATE_DONOR_HEAD = {CERTIFICATE_DONOR_HEAD!r}
CERTIFICATE_DONOR_BLOB = {CERTIFICATE_DONOR_BLOB!r}
_PACKED = {packed!r}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {{path}}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_runtime = _load("s13_certified_runtime_" + hashlib.sha256(ARM_ID.encode()).hexdigest()[:12], {str(runtime)!r})
if _runtime.CERTIFICATE_DONOR_HEAD != CERTIFICATE_DONOR_HEAD:
    raise RuntimeError("certificate donor head drift")
if _runtime.CERTIFICATE_DONOR_BLOB != CERTIFICATE_DONOR_BLOB:
    raise RuntimeError("certificate donor blob drift")
_baseline = _load("s13_certified_baseline_" + hashlib.sha256(ARM_ID.encode()).hexdigest()[:12], {str(baseline)!r})
_raw = zlib.decompress(base64.b85decode(_PACKED.encode("ascii")))
if hashlib.sha256(_raw).hexdigest() != TAPE_SHA256:
    raise RuntimeError("embedded certified tape digest mismatch")
_tape = json.loads(_raw.decode("utf-8"))
_policy = _runtime.CertifiedLeaderRoutePolicy(
    _baseline.agent,
    _tape,
    mode=ROUTE_MODE,
    source_seat=SOURCE_SEAT,
    start_step=24,
)


def agent(obs, configuration=None):
    return _policy.agent(obs, configuration)


def diagnostics():
    return _policy.diagnostics()
'''
    return source, raw


def build_certified_prefix(
    *,
    source_arm: Path,
    source_replay: Path,
    runtime: Path,
    baseline_entry: Path,
    output: Path,
    receipt: Path,
    expected_source_arm_sha256: str,
    expected_replay_sha256: str,
    expected_episode: str,
    expected_cutoff: int,
) -> dict[str, Any]:
    _distinct_paths(
        {
            "source_arm": source_arm,
            "source_replay": source_replay,
            "runtime": runtime,
            "baseline_entry": baseline_entry,
            "output": output,
            "receipt": receipt,
        }
    )
    if output.exists() or receipt.exists() or output.is_symlink() or receipt.is_symlink():
        raise CertifiedPrefixError("output and receipt must be absent")
    if not runtime.is_file() or not baseline_entry.is_file():
        raise CertifiedPrefixError("runtime and baseline entry must be regular files")
    meta, tape = decode_prefix_arm(
        source_arm,
        expected_python_sha256=expected_source_arm_sha256,
    )
    if meta["SOURCE_EPISODE"] != expected_episode:
        raise CertifiedPrefixError("source arm episode drift")
    if meta["PREFIX_CUTOFF"] != expected_cutoff:
        raise CertifiedPrefixError("source arm cutoff drift")
    if meta["SOURCE_SHA256"] != expected_replay_sha256:
        raise CertifiedPrefixError("source arm replay digest drift")
    replay_rows, configuration, replay_identity = load_source_replay(
        source_replay,
        expected_sha256=expected_replay_sha256,
        expected_episode=expected_episode,
        expected_seat=meta["SOURCE_SEAT"],
        expected_team=str(meta["SOURCE_TEAM"]),
    )
    certificate_mode = CERTIFICATE_MODE[meta["mode"]]
    certified, summary = certify_tape(
        tape,
        replay_rows,
        configuration,
        seat=meta["SOURCE_SEAT"],
        certificate_mode=certificate_mode,
    )
    rendered, raw = render(
        meta=meta,
        tape=certified,
        runtime=runtime.resolve(strict=True),
        baseline=baseline_entry.resolve(strict=True),
    )
    runtime_bytes = runtime.read_bytes()
    baseline_bytes = baseline_entry.read_bytes()
    result = {
        "schema": RECEIPT_SCHEMA,
        "operation": "TITAN-V3-S13-CERTIFIED-PREFIX695-RUNTIME-COMPOSITION-20260910-01",
        "source_arm": str(source_arm),
        "source_arm_sha256": meta["python_sha256"],
        "source_prefix_tape_sha256": meta["TAPE_SHA256"],
        "source_replay": replay_identity,
        "source_team": meta["SOURCE_TEAM"],
        "source_seat": meta["SOURCE_SEAT"],
        "source_seat_portability": False,
        "prefix_cutoff": meta["PREFIX_CUTOFF"],
        "route_mode": meta["mode"],
        "certificate_mode": certificate_mode,
        "certificate_donor_head": CERTIFICATE_DONOR_HEAD,
        "certificate_donor_blob": CERTIFICATE_DONOR_BLOB,
        "certificate_summary": summary,
        "certified_tape_sha256": sha256(raw),
        "runtime": str(runtime.resolve()),
        "runtime_sha256": sha256(runtime_bytes),
        "baseline_entry": str(baseline_entry.resolve()),
        "baseline_entry_sha256": sha256(baseline_bytes),
        "output": str(output),
        "output_python_sha256": sha256(rendered.encode()),
        "receipt": str(receipt),
        "handoff_contract": "incumbent called first every turn; any seat/row/action/certificate mismatch permanently hands off before route emission",
        "market_outcome_claim": False,
        "promotion_claim": False,
        "schema_source": SCHEMA,
    }
    _atomic_write(output, rendered.encode())
    _atomic_write(
        receipt,
        (json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(),
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-arm", type=Path, required=True)
    parser.add_argument("--source-replay", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--baseline-entry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--expected-source-arm-sha256", required=True)
    parser.add_argument("--expected-replay-sha256", required=True)
    parser.add_argument("--expected-episode", required=True)
    parser.add_argument("--expected-cutoff", type=int, required=True)
    args = parser.parse_args(argv)
    result = build_certified_prefix(
        source_arm=args.source_arm,
        source_replay=args.source_replay,
        runtime=args.runtime,
        baseline_entry=args.baseline_entry,
        output=args.output,
        receipt=args.receipt,
        expected_source_arm_sha256=args.expected_source_arm_sha256,
        expected_replay_sha256=args.expected_replay_sha256,
        expected_episode=args.expected_episode,
        expected_cutoff=args.expected_cutoff,
    )
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CertifiedPrefixError, CertificateError) as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        raise SystemExit(2)
