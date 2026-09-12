# SPDX-License-Identifier: Apache-2.0
"""Authenticated native reachability/economics runner for W1 with H1 shadow census.

Each invocation runs one complete two-seat official-engine game. ``baseline``
executes canonical V4 unchanged; ``w1`` applies the landed capacity-safe W1 only
at the returned-action boundary. H1 is always observed counterfactually and is
never executed here. Compare baseline/w1 with identical seed+seat.

The canonical b567 archive is captured once and is the execution authority. The
caller-supplied native root is checked against that capture but is never executed.
W1/H1 donors are independently captured and Git-blob authenticated by HarvestProbe.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import platform
import sys
import tarfile
import tempfile
import time

from harvest_probe import HarvestProbe

ARCHIVE_SHA = "b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9"
ENGINE_PINS = {
    "kaggriculture.py": "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e",
    "kaggriculture.json": "a82c89c1a2315b93f39775d8e025471a01b738647c9772658368ee6b1b6f4867",
    "utils.py": "537b627b11784d424147ef57ebb0369b039bf83c9f891e81f10486b1f552334b",
}
LOADER_SHA = "cd113a94ae99b03492502e425bdcf09c3db17a2aa2a8fd866f0d78caec9e311e"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _safe_member(name: str) -> PurePosixPath:
    require(isinstance(name, str) and name and "\\" not in name,
            "unsafe archive member")
    rel = PurePosixPath(name)
    require(not rel.is_absolute() and all(part not in ("", ".", "..") for part in rel.parts),
            "unsafe archive member")
    return rel


def _safe_live_path(root: Path, rel: PurePosixPath) -> Path:
    current = root
    for part in rel.parts:
        current = current / part
        require(not current.is_symlink(), "symlink native member: " + rel.as_posix())
    require(current.is_file(), "native member missing: " + rel.as_posix())
    return current


def capture_runtime(root: Path, archive: Path):
    """Capture canonical archive bytes once; validate live root against the capture."""
    root = Path(root)
    archive = Path(archive)
    require(not root.is_symlink() and root.is_dir(), "unsafe native root")
    root = root.resolve(strict=True)
    require(not archive.is_symlink() and archive.is_file(), "unsafe archive path")
    archive_raw = archive.read_bytes()
    require(digest(archive_raw) == ARCHIVE_SHA, "archive hash mismatch")

    captured: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(archive_raw), mode="r:*") as tar:
        for entry in tar.getmembers():
            name = entry.name.removeprefix("./")
            if entry.isdir():
                continue
            require(entry.isfile(), "unsupported archive member type: " + name)
            rel = _safe_member(name)
            canonical = rel.as_posix()
            require(canonical not in captured, "duplicate archive member: " + canonical)
            stream = tar.extractfile(entry)
            require(stream is not None, "archive member unreadable: " + canonical)
            captured[canonical] = stream.read()

    require("main.py" in captured, "archive missing native main.py")
    require("checks/reference/evaluator/loader.py" in captured,
            "archive missing official evaluator loader")
    for name, data in captured.items():
        target = _safe_live_path(root, PurePosixPath(name))
        require(target.read_bytes() == data, "native member mismatch: " + name)

    for name, expected in ENGINE_PINS.items():
        key = "checks/reference/engine/" + name
        require(key in captured and digest(captured[key]) == expected,
                "engine hash mismatch: " + name)
    require(digest(captured["checks/reference/evaluator/loader.py"]) == LOADER_SHA,
            "loader hash mismatch")
    return dict(sorted((name, digest(data)) for name, data in captured.items())), captured


def materialize_runtime(root: Path, captured: dict[str, bytes]):
    """Materialize exactly the authenticated archive capture into a fresh private tree."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    for name, data in captured.items():
        rel = _safe_member(name)
        target = root / Path(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _system_paths(prior: list[str]) -> list[str]:
    roots = {Path(sys.base_prefix).resolve(), Path(sys.prefix).resolve()}
    result = []
    for value in prior:
        if not value:
            continue
        try:
            resolved = Path(value).resolve()
        except OSError:
            continue
        if any(_under(resolved, root) for root in roots):
            result.append(value)
    return result


def _reject_preloaded_runtime_modules(captured: dict[str, bytes]):
    names = {
        PurePosixPath(name).stem
        for name in captured
        if "/" not in name and name.endswith(".py") and name != "main.py"
    }
    system_roots = {Path(sys.base_prefix).resolve(), Path(sys.prefix).resolve()}
    for name in sorted(names):
        module = sys.modules.get(name)
        if module is None:
            continue
        origin = getattr(module, "__file__", None)
        require(origin is not None, "preloaded runtime module has no auditable origin: " + name)
        try:
            path = Path(origin).resolve()
        except OSError as exc:
            raise RuntimeError("preloaded runtime module origin unreadable: " + name) from exc
        require(any(_under(path, root) for root in system_roots),
                f"preloaded runtime module escapes frozen custody: {name} -> {path}")


def initialize(loader, engine, seed: int):
    cfg = loader.Struct({key: value.get("default") if isinstance(value, dict) else value
                         for key, value in engine.specification["configuration"].items()})
    cfg.seed = seed
    env = loader.Struct(configuration=cfg, done=False, info={})
    state = [loader.Struct(observation=loader.Struct(), action={}, status="ACTIVE", reward=0)
             for _ in range(2)]
    engine.interpreter(state, env)
    return cfg, env, state


def json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def game(root: Path, workspace: Path, loader, engine, *, seed: int, seat: int, variant: str):
    parent = load(f"harvest_native_parent_{variant}_{seat}", root / "main.py")
    probe = HarvestProbe(workspace)
    donor_identity = probe.source_identity()
    donor_sha256 = {name: row["sha256"] for name, row in donor_identity.items()}
    donor_git_blob = {name: row["git_blob"] for name, row in donor_identity.items()}
    cfg, env, state = initialize(loader, engine, seed)
    counters = Counter()
    statuses = Counter()
    times = []
    action_trace = hashlib.sha256()
    state_trace = hashlib.sha256()
    events = []

    for step in range(cfg.episodeSteps):
        returned = []
        for player, item in enumerate(state):
            item.observation.step = step
            visible = deepcopy(item.observation)
            started = time.perf_counter()
            action = (parent.agent(deepcopy(visible), cfg) if player == seat
                      else engine.starter_agent(deepcopy(visible)))
            elapsed = time.perf_counter() - started
            require(isinstance(action, dict), "agent returned non-dict action")
            if player == seat:
                times.append(elapsed)
                instance = getattr(parent, "_INSTANCE", None)
                statuses[getattr(instance, "diagnostics", {}).get("status", "missing")] += 1
                census = probe.inspect(visible, cfg, action)
                counters["callbacks"] += 1
                counters["w1_would_change"] += int(census["w1_changed"])
                counters["h1_would_change"] += int(census["h1_changed"])
                counters["h1_only"] += int(census["h1_only"])
                if census["w1_changed"] or census["h1_changed"]:
                    events.append({
                        "step": step,
                        "w1_changed": census["w1_changed"],
                        "h1_changed": census["h1_changed"],
                        "h1_only": census["h1_only"],
                        "w1_actor_indices": census["w1_actor_indices"],
                        "h1_actor_indices": census["h1_actor_indices"],
                    })
                if variant == "w1":
                    candidate = probe.apply_candidate(visible, cfg, action)
                    counters["w1_executed_changes"] += int(candidate != action)
                    action = candidate
            item.action = action
            returned.append(action)
        action_data = json_bytes(returned)
        action_trace.update(action_data + b"\n")
        engine.interpreter(state, env)
        state_data = json_bytes([state, env])
        state_trace.update(state_data + b"\n")
        if any(item.status == "DONE" for item in state):
            break

    require(step + 1 == 719 and all(item.status == "DONE" for item in state),
            "incomplete native game")
    require(statuses == {"completed": 719},
            "native fallback or incomplete callback: " + str(statuses))
    return {
        "seed": seed,
        "seat": seat,
        "variant": variant,
        "opponent": "official_starter",
        "steps": step + 1,
        "rewards": [item.reward for item in state],
        "callback_status": dict(statuses),
        "census": dict(counters),
        "events": events,
        "donor_reports": probe.reports(),
        "donor_sha256": donor_sha256,
        "donor_git_blob": donor_git_blob,
        "donors_executed_from_captured_bytes": True,
        "action_trace_sha256": action_trace.hexdigest(),
        "state_trace_sha256": state_trace.hexdigest(),
        "max_parent_call_seconds": max(times),
        "mean_parent_call_seconds": sum(times) / len(times),
        "promotion_authorized": False,
        "scope": "official-engine vs starter; H1 shadow-only; no hosted/gauntlet claim",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True,
                        help="materialized native runtime root; validated but never executed")
    parser.add_argument("--workspace", type=Path, required=True,
                        help="canonical candidates/v4 workspace containing W1/H1 donors")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variant", choices=("baseline", "w1"), default="baseline")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--seat", type=int, choices=(0, 1), required=True)
    args = parser.parse_args()

    source_root = args.root.resolve()
    workspace = args.workspace.resolve()
    archive = args.archive.resolve()
    require(workspace.is_dir(), "V4 workspace missing")
    members, captured = capture_runtime(source_root, archive)
    prior_path = list(sys.path)
    _reject_preloaded_runtime_modules(captured)
    with tempfile.TemporaryDirectory(prefix="harvest-gate-runtime-") as tmp:
        frozen = Path(tmp) / "runtime"
        materialize_runtime(frozen, captured)
        sys.path[:] = [str(frozen), str(frozen / "checks"), *_system_paths(prior_path)]
        try:
            loader = load("harvest_official_loader", frozen / "checks/reference/evaluator/loader.py")
            engine, engine_hashes = loader.get_engine(frozen / "checks/reference/engine")
            result = game(frozen, workspace, loader, engine,
                          seed=args.seed, seat=args.seat, variant=args.variant)
        finally:
            sys.path[:] = prior_path
    result.update({
        "python": platform.python_version(),
        "optimized": bool(sys.flags.optimize),
        "archive_sha256": ARCHIVE_SHA,
        "runtime_members_authenticated": len(members),
        "runtime_member_sha256": members,
        "engine_sha256": engine_hashes,
        "runtime_executed_from_captured_archive": True,
        "production_or_default_changed": False,
    })
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "seed": result["seed"], "seat": result["seat"], "variant": result["variant"],
        "rewards": result["rewards"], "census": result["census"],
        "events": len(result["events"]), "donor_sha256": result["donor_sha256"],
        "donor_git_blob": result["donor_git_blob"],
        "promotion_authorized": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
