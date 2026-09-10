#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize byte-bound control and live-seam intent-priority debug roots."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
from typing import Any

ARCHIVE_SHA256 = "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
ARCHIVE_BYTES = 428_158
SOURCE_SHA256 = "3249398b6aa56d1b3464db8d0cce5aa35e8edee397fc4341bd710d1f74dad469"
FROZEN_SELECTED_GIT_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
RUNTIME_FILES = 109
MAX_MEMBERS = 512
MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
OPERATION = "titan-v3-intent-priority-2609097304-causal-closure-20260910-01"

OLD = (
    "        targets={p:max(0,int(shed.get(p,0))) for p in PRODUCTS "
    "if shed.get(p,0)>0}\n"
).encode()
NEW = (
    "        target_order={\n"
    "            p:None for p in [*self.pending,*baseline_q,*PRODUCTS]\n"
    "            if p in PRODUCTS\n"
    "        }\n"
    "        targets={\n"
    "            p:max(0,int(shed.get(p,0))) for p in target_order\n"
    "            if shed.get(p,0)>0\n"
    "        }\n"
).encode()


class MaterializationError(RuntimeError):
    """The current closure, candidate seam, or output violated a hard contract."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def strict_json(data: bytes, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise MaterializationError(f"{label} has duplicate key {key!r}")
            out[key] = value
        return out

    def reject(value: str) -> Any:
        raise MaterializationError(f"{label} has non-finite constant {value}")

    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MaterializationError(f"{label} is not strict UTF-8 JSON: {exc}") from exc


def canonical_name(raw: Any, label: str) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw or "\x00" in raw:
        raise MaterializationError(f"{label} is not a canonical relative path")
    path = PurePosixPath(raw)
    if path.is_absolute() or raw != path.as_posix() or any(part in ("", ".", "..") for part in path.parts):
        raise MaterializationError(f"{label} is not a canonical relative path")
    return raw


def true_int(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise MaterializationError(f"{label} must be an integer >= {minimum}")
    return value


def digest(value: Any, label: str, length: int = 64) -> str:
    if not isinstance(value, str) or len(value) != length or value.lower() != value:
        raise MaterializationError(f"{label} must be lowercase {length}-hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise MaterializationError(f"{label} must be lowercase {length}-hex") from exc
    return value


def read_archive(archive_path: Path, source_manifest_path: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = archive_path.read_bytes()
    if len(data) != ARCHIVE_BYTES or sha256(data) != ARCHIVE_SHA256:
        raise MaterializationError("current archive identity drift")
    source_repository = source_manifest_path.read_bytes()
    if sha256(source_repository) != SOURCE_SHA256:
        raise MaterializationError("CURRENT-SOURCE.json identity drift")

    members: dict[str, bytes] = {}
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            infos = archive.getmembers()
            if len(infos) > MAX_MEMBERS:
                raise MaterializationError("archive member bound exceeded")
            names = [canonical_name(info.name, "archive member") for info in infos]
            if names != sorted(names) or len(names) != len(set(names)):
                raise MaterializationError("archive members are not unique canonical sorted paths")
            for info, name in zip(infos, names):
                if not info.isreg() or info.issym() or info.islnk():
                    raise MaterializationError(f"archive member is not a regular file: {name}")
                if info.size < 0 or info.size > MAX_MEMBER_BYTES:
                    raise MaterializationError(f"unsafe archive member size: {name}")
                total += info.size
                if total > MAX_TOTAL_BYTES:
                    raise MaterializationError("archive expansion bound exceeded")
                stream = archive.extractfile(info)
                if stream is None:
                    raise MaterializationError(f"cannot read archive member: {name}")
                payload = stream.read(info.size + 1)
                if len(payload) != info.size:
                    raise MaterializationError(f"archive member size mismatch: {name}")
                members[name] = payload
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise MaterializationError(f"cannot parse current archive: {exc}") from exc

    source_bytes = members.get("SOURCE.json")
    if source_bytes is None or sha256(source_bytes) != SOURCE_SHA256:
        raise MaterializationError("archive SOURCE.json identity drift")
    if source_bytes != source_repository:
        raise MaterializationError("archive SOURCE.json differs from CURRENT-SOURCE.json")
    source = strict_json(source_bytes, "SOURCE.json")
    if not isinstance(source, dict) or source.get("entrypoint") != "main.py::agent":
        raise MaterializationError("source manifest entrypoint drift")
    runtime = source.get("runtime")
    if not isinstance(runtime, dict) or len(runtime) != RUNTIME_FILES:
        raise MaterializationError("source manifest runtime cardinality drift")
    expected = set(runtime) | {"SOURCE.json"}
    if set(members) != expected:
        raise MaterializationError(
            f"archive/source member-set drift: missing={sorted(expected-set(members))!r}, "
            f"extra={sorted(set(members)-expected)!r}"
        )
    for raw_name, record in runtime.items():
        name = canonical_name(raw_name, "runtime member")
        if not isinstance(record, dict):
            raise MaterializationError(f"runtime record is not an object: {name}")
        expected_bytes = true_int(record.get("bytes"), f"runtime[{name}].bytes")
        expected_sha = digest(record.get("sha256"), f"runtime[{name}].sha256")
        payload = members[name]
        if len(payload) != expected_bytes or sha256(payload) != expected_sha:
            raise MaterializationError(f"runtime member identity drift: {name}")
    frozen = members.get("frozen_selected.py")
    if frozen is None or git_blob_sha1(frozen) != FROZEN_SELECTED_GIT_BLOB:
        raise MaterializationError("frozen_selected.py Git blob drift")
    return members, source


def patch_frozen_selected(original: bytes) -> tuple[bytes, dict[str, Any]]:
    if git_blob_sha1(original) != FROZEN_SELECTED_GIT_BLOB:
        raise MaterializationError("candidate source is not the pinned frozen_selected.py")
    if original.count(OLD) != 1 or original.count(NEW) != 0:
        raise MaterializationError("intent-priority seam cardinality drift")
    candidate = original.replace(OLD, NEW, 1)
    if candidate.count(OLD) != 0 or candidate.count(NEW) != 1:
        raise MaterializationError("candidate seam replacement failed")
    try:
        compile(candidate.decode("utf-8"), "frozen_selected.py", "exec")
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise MaterializationError(f"candidate frozen_selected.py does not compile: {exc}") from exc
    return candidate, {
        "source_sha256": sha256(original),
        "source_git_blob_sha1": git_blob_sha1(original),
        "candidate_sha256": sha256(candidate),
        "candidate_git_blob_sha1": git_blob_sha1(candidate),
        "source_bytes": len(original),
        "candidate_bytes": len(candidate),
    }


def write_exclusive(root: Path, name: str, payload: bytes) -> None:
    target = root / Path(*PurePosixPath(canonical_name(name, "output member")).parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(payload)
    os.chmod(target, 0o644)


def entry_source(*, mode: str, frozen_sha256: str, frozen_bytes: int) -> bytes:
    entry_name = f"{mode}_entry.py"
    source = f'''# Generated by {OPERATION}; do not edit.
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
ENTRY_NAME = {entry_name!r}
EXPECTED_SOURCE_SHA256 = {SOURCE_SHA256!r}
EXPECTED_FROZEN_SHA256 = {frozen_sha256!r}
EXPECTED_FROZEN_BYTES = {frozen_bytes!r}
EXPECTED_RUNTIME_FILES = {RUNTIME_FILES!r}
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(raw):
    if not isinstance(raw, str) or not raw or "\\\\" in raw or "\\x00" in raw:
        raise RuntimeError("noncanonical runtime member")
    path = PurePosixPath(raw)
    if path.is_absolute() or raw != path.as_posix() or any(p in ("", ".", "..") for p in path.parts):
        raise RuntimeError("noncanonical runtime member")
    return raw


def _verify_root():
    source_bytes = (ROOT / "SOURCE.json").read_bytes()
    if _sha(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("SOURCE.json drift")
    source = json.loads(source_bytes)
    runtime = source.get("runtime")
    if not isinstance(runtime, dict) or len(runtime) != EXPECTED_RUNTIME_FILES:
        raise RuntimeError("runtime manifest drift")
    expected = set(runtime) | {{"SOURCE.json", ENTRY_NAME}}
    actual = set()
    for path in ROOT.rglob("*"):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise RuntimeError("unsafe runtime path")
        if path.is_file():
            actual.add(path.relative_to(ROOT).as_posix())
    if actual != expected:
        raise RuntimeError("runtime root member-set drift")
    for raw_name, record in runtime.items():
        name = _canonical(raw_name)
        data = (ROOT / Path(*PurePosixPath(name).parts)).read_bytes()
        expected_sha = EXPECTED_FROZEN_SHA256 if name == "frozen_selected.py" else record.get("sha256")
        expected_bytes = EXPECTED_FROZEN_BYTES if name == "frozen_selected.py" else record.get("bytes")
        if len(data) != expected_bytes or _sha(data) != expected_sha:
            raise RuntimeError("runtime member drift: " + name)


_verify_root()
import frozen_selected as _frozen

_ORIGINAL_TRANSFORM = _frozen.FrozenSelected.transform
_LAST_DEBUG = None


def _json_safe(value, depth=0):
    if depth > 8:
        return None
    if value is None or isinstance(value, (bool, str)):
        return value[:1000] if isinstance(value, str) else value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, depth + 1) for item in value[:256]]
    if isinstance(value, dict):
        out = {{}}
        for key, item in list(value.items())[:256]:
            if isinstance(key, str):
                out[key[:200]] = _json_safe(item, depth + 1)
        return out
    return None


def _chosen_summary(info):
    if not isinstance(info, dict):
        return None
    keys = (
        "item", "items", "plan", "plans", "worst_relative_gain",
        "named_worst_relative_gain", "acceptance_rule", "forced_feasibility",
        "minimum_now", "baseline_horizon_end", "horizon_end",
    )
    return {{key: _json_safe(info[key]) for key in keys if key in info}}


def _stable_unique(rows):
    out = []
    seen = set()
    for value in rows:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _debug_transform(self, obs, config, base):
    global _LAST_DEBUG
    cfg = dict(config or {{}})
    products = list(_frozen.PRODUCTS)
    allowed = set(products)
    pending_before = [p for p in getattr(self, "pending", {{}}) if p in allowed]
    planned_before = _json_safe(getattr(self, "planned", {{}}))
    baseline_order = []
    for row in base.get("market", []):
        if row and len(row) > 2 and row[0] == "SELL" and row[1] in allowed:
            baseline_order.append(row[1])
    baseline_order = _stable_unique(baseline_order)
    result = _ORIGINAL_TRANSFORM(self, obs, config, base)
    # Observation-only reconstruction runs after the policy has returned and on
    # detached inputs, so it cannot affect the action or controller state.
    farm, private = _frozen.post_units(copy.deepcopy(obs), copy.deepcopy(base), cfg)
    shed = {{p: max(0, int(private["shed"].get(p, 0))) for p in products}}
    control_order = [p for p in products if shed[p] > 0]
    intent_order = [
        p for p in _stable_unique([*pending_before, *baseline_order, *products])
        if shed[p] > 0
    ]
    chosen = _chosen_summary(getattr(self, "diagnostics", {{}}).get("chosen"))
    _LAST_DEBUG = {{
        "schema_version": 1,
        "mode": {mode!r},
        "step": int(obs["step"]),
        "player": int(obs["player"]),
        "max_market_orders": int(cfg.get("maxMarketOrdersPerTurn", 10)),
        "money": int(farm["money"]),
        "shed": shed,
        "pending_before": pending_before,
        "pending_after": _json_safe(getattr(self, "pending", {{}})),
        "planned_before": planned_before,
        "baseline_order": baseline_order,
        "control_order": control_order,
        "intent_order": intent_order,
        "order_changed": control_order != intent_order,
        "base_market": _json_safe(base.get("market", [])),
        "returned_market": _json_safe(result.get("market", [])),
        "chosen": chosen,
    }}
    return result


_frozen.FrozenSelected.transform = _debug_transform
import main as _main


def agent(observation, configuration=None):
    return _main.agent(observation, configuration)


def debug_snapshot():
    return copy.deepcopy(_LAST_DEBUG)
'''
    payload = source.encode("utf-8")
    compile(source, entry_name, "exec")
    return payload


def materialize(archive: Path, source_manifest: Path, output: Path, head: str | None) -> dict[str, Any]:
    archive = archive.resolve(strict=True)
    source_manifest = source_manifest.resolve(strict=True)
    output = output.resolve()
    if output.exists():
        raise MaterializationError(f"output already exists: {output}")
    members, _source = read_archive(archive, source_manifest)
    candidate_frozen, candidate_identity = patch_frozen_selected(members["frozen_selected.py"])
    control_identity = {
        "source_sha256": sha256(members["frozen_selected.py"]),
        "source_git_blob_sha1": git_blob_sha1(members["frozen_selected.py"]),
        "candidate_sha256": sha256(members["frozen_selected.py"]),
        "candidate_git_blob_sha1": git_blob_sha1(members["frozen_selected.py"]),
        "source_bytes": len(members["frozen_selected.py"]),
        "candidate_bytes": len(members["frozen_selected.py"]),
    }
    identities = {"control": control_identity, "candidate": candidate_identity}
    stage = output.parent / f".{output.name}.{os.getpid()}.tmp"
    stage.mkdir(parents=True, exist_ok=False)
    try:
        for mode in ("control", "candidate"):
            root = stage / mode
            root.mkdir()
            for name in sorted(members):
                payload = candidate_frozen if mode == "candidate" and name == "frozen_selected.py" else members[name]
                write_exclusive(root, name, payload)
            identity = identities[mode]
            entry = entry_source(
                mode=mode,
                frozen_sha256=identity["candidate_sha256"],
                frozen_bytes=identity["candidate_bytes"],
            )
            write_exclusive(root, f"{mode}_entry.py", entry)
        receipt = {
            "schema_version": 1,
            "operation": OPERATION,
            "git_head": head,
            "archive": {"sha256": ARCHIVE_SHA256, "bytes": ARCHIVE_BYTES},
            "source_manifest": {"sha256": SOURCE_SHA256, "runtime_files": RUNTIME_FILES},
            "factor": {
                "source_path": "frozen_selected.py",
                "source_git_blob_sha1": FROZEN_SELECTED_GIT_BLOB,
                "changed_field": "FrozenSelected.transform targets iteration order",
                "control_order": "PRODUCTS",
                "candidate_order": ["pending intent", "baseline SELL first-seen", "PRODUCTS"],
                "target_membership_and_stock_quantities": "unchanged",
            },
            "arms": {
                mode: {
                    "root": mode,
                    "entrypoint": f"{mode}/{mode}_entry.py::agent",
                    "frozen_selected_sha256": identities[mode]["candidate_sha256"],
                    "frozen_selected_git_blob_sha1": identities[mode]["candidate_git_blob_sha1"],
                    "entry_sha256": sha256((stage / mode / f"{mode}_entry.py").read_bytes()),
                }
                for mode in ("control", "candidate")
            },
            "only_runtime_delta": ["frozen_selected.py"],
            "canonical_repository_modified": False,
            "strength_claim": False,
        }
        write_exclusive(
            stage,
            "PAIR-RECEIPT.json",
            (json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(),
        )
        os.replace(stage, output)
        return receipt
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--head")
    args = parser.parse_args(argv)
    receipt = materialize(args.archive, args.source_manifest, args.output, args.head)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
