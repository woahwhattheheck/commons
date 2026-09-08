# SPDX-License-Identifier: Apache-2.0
"""Profile one actor over saved observations; never advance a game or retry an action.

The two passes run in separate Python processes. The ordinary pass supplies wall
costs; the instrumented pass supplies cumulative hot-function costs. Output/action
hash correspondence is checked rather than assumed. TANDEM's existing TimedFactory
is consumed as a file dependency, not copied or replaced.
"""
from __future__ import annotations

import argparse
import copy
import cProfile
import hashlib
import importlib.util
import inspect
import json
import math
import os
from pathlib import Path
import platform
import pstats
import resource
import subprocess
import sys
import time
import gzip


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("not an importable Python source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def bind_action(fn):
    """Select shape before the first invocation; a body TypeError is never retried."""
    signature = inspect.signature(fn)
    try:
        signature.bind({}, {})
    except TypeError:
        signature.bind({})
        return lambda obs, cfg: fn(obs)
    return lambda obs, cfg: fn(obs, cfg)


def load_workload(path: Path, seat: int, limit: int):
    raw = path.read_bytes()
    decoded = gzip.decompress(raw) if raw.startswith(b"\x1f\x8b") else raw
    value = json.loads(decoded)
    for _ in range(8):
        if isinstance(value, str):
            value = json.loads(value)
        elif isinstance(value, dict) and ("steps" in value or "records" in value):
            break
        elif isinstance(value, dict):
            keys = [k for k in ("replay", "result", "episode", "Replay") if k in value]
            if len(keys) != 1:
                raise ValueError("ambiguous or unrecognized workload envelope")
            value = value[keys[0]]
        else:
            raise ValueError("no observation workload")
    if not isinstance(value, dict):
        raise ValueError("no observation workload object")
    cfg = copy.deepcopy(value.get("configuration", {}))
    if not isinstance(cfg, dict):
        raise ValueError("configuration must be a mapping")
    cfg.pop("seed", None)  # labels and hidden seed never become agent input
    records = []
    if value.get("schema") == "titan.profile.observations.v1":
        for row in value["records"][:limit]:
            records.append(copy.deepcopy(row))
        provenance = value.get("provenance", {})
    elif isinstance(value.get("steps"), list):
        for step, frame in enumerate(value["steps"][:-1][:limit]):
            rows = frame.get("state") if isinstance(frame, dict) else frame
            if not isinstance(rows, list) or len(rows) != 2:
                raise ValueError("expected two player rows")
            own = copy.deepcopy(rows[seat].get("observation", {}))
            for key in ("farms", "market", "town", "step", "day", "hour"):
                if key not in own:
                    source = next((r.get("observation", {})[key] for r in rows
                                   if key in r.get("observation", {})), None)
                    if source is not None:
                        own[key] = copy.deepcopy(source)
            own["player"] = seat
            own.setdefault("step", step)
            records.append({"observation": own})
        provenance = {"kind": "retained_replay_off_policy", "info_id":
                      (value.get("info") or {}).get("EpisodeId")}
    else:
        raise ValueError("no complete observations; summary/action/timing rows cannot be replayed")
    if not records:
        raise ValueError("empty observation workload")
    last = -1
    for row in records:
        obs = row.get("observation")
        if not isinstance(obs, dict) or not all(k in obs for k in ("farms", "private", "market")):
            raise ValueError("full own observation is required")
        step = obs.get("step")
        if step is None:
            step = int(obs["day"]) * int(cfg.get("turnsPerDay", 24)) + int(obs["hour"])
            obs["step"] = step
        if type(step) is not int or step != last + 1:
            raise ValueError("stateful actor requires an uninterrupted prefix starting at zero")
        if obs.get("player", seat) != seat:
            raise ValueError("observation player does not match selected seat")
        last = step
    return cfg, records, {"transport_sha256": digest(raw), "decoded_sha256": digest(decoded),
                          "records": len(records), "provenance": provenance}


def describe_environment():
    result = {"python": sys.version, "platform": platform.platform(), "logical_cpus": os.cpu_count(),
              "cpu_affinity_count": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None}
    for name in ("cpu.max", "memory.max"):
        p = Path("/sys/fs/cgroup") / name
        result["cgroup_" + name] = p.read_text().strip() if p.exists() else None
    return result


def source_rows(root: Path):
    return {str(p.relative_to(root)): digest(p.read_bytes())
            for p in sorted(root.rglob("*.py")) if "__pycache__" not in p.parts}


def worker(args):
    report = {"schema": "titan.saved-runtime-pass.v1", "mode": args.worker_mode,
              "status": "error", "classification": args.classification,
              "calls": [], "environment": describe_environment(),
              "process_id": os.getpid(),
              "entrypoint": str(args.entrypoint), "profiler_sha256": digest(Path(__file__).read_bytes())}
    observer = None
    source_before = None
    prof = cProfile.Profile() if args.worker_mode == "profile" else None
    profile_steps = {int(step) for step in (getattr(args, "profile_steps", "") or "").split(",") if step}
    report["profiled_steps"] = sorted(profile_steps) if prof else []
    try:
        t0 = time.perf_counter()
        cfg, records, report["input"] = load_workload(args.replay, args.seat, args.max_decisions)
        report["input_load_s"] = time.perf_counter() - t0
        timing = load_module(args.timing_source, "finch_existing_timing")
        report["timing_source_sha256"] = digest(args.timing_source.read_bytes())
        source_before = source_rows(args.entrypoint.parent)
        sys.path.insert(0, str(args.entrypoint.parent))
        t0 = time.perf_counter()
        target_load_started = t0
        module = load_module(args.entrypoint, "finch_profile_target")
        report["entry_import_s"] = time.perf_counter() - t0
        holder = {}

        def factory():
            actor = getattr(module, args.factory)()
            holder["actor"] = actor
            method = actor if args.method == "__call__" else getattr(actor, args.method)
            return bind_action(method)

        observer = timing.TimedFactory(factory)
        actor = observer()
        output_hash = hashlib.sha256()
        report["expected_actions"] = {"present": 0, "mismatches": 0, "first_mismatch": None}
        for row in records:
            obs = copy.deepcopy(row["observation"])
            configuration = copy.deepcopy(cfg)
            step = obs["step"]
            started = time.perf_counter()
            cpu_started = time.process_time()
            try:
                if prof and step in profile_steps:
                    prof.enable()
                action = actor(obs, configuration)
            finally:
                if prof:
                    prof.disable()
                elapsed = time.perf_counter() - started
                cpu_elapsed = time.process_time() - cpu_started
                report["calls"].append({"step": step, "wall_s": elapsed, "cpu_s": cpu_elapsed})
                if len(report["calls"]) == 1:
                    report["target_load_through_first_attempt_wall_s"] = time.perf_counter() - target_load_started
            if not isinstance(action, dict):
                raise TypeError("policy returned a non-dict action")
            encoded = canonical(action)
            output_hash.update(len(encoded).to_bytes(8, "big") + encoded)
            report["calls"][-1]["action_sha256"] = digest(encoded)
            diagnostics = getattr(holder["actor"], "diagnostics", {})
            if not isinstance(diagnostics, dict):
                diagnostics = {}
            report["calls"][-1]["diagnostics"] = {k: diagnostics.get(k) for k in
                ("status", "reason", "seed_reason") if k in diagnostics}
            if "expected_action" in row:
                expected = report["expected_actions"]
                expected["present"] += 1
                if canonical(row["expected_action"]) != encoded:
                    expected["mismatches"] += 1
                    if expected["first_mismatch"] is None:
                        expected["first_mismatch"] = step
        report["action_sequence_sha256"] = output_hash.hexdigest()
        report["status"] = "complete"
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)[:300]}
    finally:
        report["timings"] = observer.timings() if observer else None
        report["runtime_sources"] = source_before
        report["sources_unchanged"] = source_before == source_rows(args.entrypoint.parent) if source_before else None
        report["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        values = [r["wall_s"] for r in report["calls"]]
        report["ordinary_threshold_s"] = 1.0
        report["calls_over_threshold"] = sum(t > 1.0 for t in values)
        report["total_observed_excess_s"] = sum(max(0.0, t - 1.0) for t in values)
        report["p99_call_s"] = sorted(values)[math.ceil(.99 * len(values))-1] if values else None
        if report["timings"] and report["timings"]["initialization_plus_first_action_s"] is not None:
            report["entry_import_through_first_action_s"] = report["entry_import_s"] + report["timings"]["initialization_plus_first_action_s"]
        if prof and prof.getstats():
            stats = pstats.Stats(prof)
            report["hot_functions"] = sorted([
                {"file": str(Path(filename).relative_to(args.entrypoint.parent)), "line": lineno,
                 "function": name, "primitive_calls": cc, "calls": nc,
                 "self_s": tt, "cumulative_s": ct}
                for (filename, lineno, name), (cc, nc, tt, ct, _callers) in stats.stats.items()
                if str(filename).startswith(str(args.entrypoint.parent) + os.sep)
            ], key=lambda r: r["cumulative_s"], reverse=True)[:50]
        args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return 0 if report["status"] == "complete" else 2


def supervise(args):
    args.output.parent.mkdir(parents=True, exist_ok=True)
    outputs = [args.output] + [args.output.with_name(args.output.stem + "." + mode + suffix)
        for mode in ("ordinary", "profile") for suffix in (".json", ".log")]
    if any(path.exists() for path in outputs):
        raise FileExistsError("use a new result basename; previous receipts are preserved")
    reports = []
    for mode in ("ordinary", "profile"):
        child_output = args.output.with_name(args.output.stem + "." + mode + ".json")
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker-mode", mode,
                   "--entrypoint", str(args.entrypoint), "--factory", args.factory,
                   "--method", args.method, "--timing-source", str(args.timing_source),
                   "--replay", str(args.replay), "--seat", str(args.seat),
                   "--max-decisions", str(args.max_decisions), "--classification", args.classification,
                   "--output", str(child_output)]
        if mode == "profile" and reports and reports[0].get("calls"):
            calls = reports[0]["calls"]
            steps = {calls[0]["step"], calls[-1]["step"]}
            steps.update(row["step"] for row in sorted(calls, key=lambda row: row["wall_s"], reverse=True)[:getattr(args,"profile_slowest",5)])
            command.extend(["--profile-steps", ",".join(map(str, sorted(steps)))])
        started = time.perf_counter()
        try:
            run = subprocess.run(command, capture_output=True, text=True, timeout=args.process_timeout)
            code, log = run.returncode, run.stdout + run.stderr
            report = json.loads(child_output.read_text()) if child_output.exists() else {
                "status": "process_error", "error": {"type": "MissingChildReport"}}
        except subprocess.TimeoutExpired as exc:
            code = None
            def decoded(value):
                return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else (value or "")
            log = decoded(exc.stdout) + decoded(exc.stderr)
            report = {"status": "process_timeout", "mode": mode,
                      "error": {"type": "ProcessTimeout", "limit_s": args.process_timeout}}
        elapsed = time.perf_counter() - started
        report["process_start_to_exit_wall_s"] = elapsed
        report["process_exit_code"] = code
        child_output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        args.output.with_name(args.output.stem + "." + mode + ".log").write_text(log)
        reports.append(report)
    normal, profiled = reports
    matching = (normal.get("status") == profiled.get("status") == "complete" and
                normal.get("action_sequence_sha256") == profiled.get("action_sequence_sha256") and
                len(normal["calls"]) == len(profiled["calls"]) and
                normal.get("runtime_sources") == profiled.get("runtime_sources") and
                normal.get("input") == profiled.get("input") and
                normal.get("sources_unchanged") is True and profiled.get("sources_unchanged") is True and
                normal.get("process_exit_code") == profiled.get("process_exit_code") == 0)
    result = {"schema": "titan.saved-runtime-budget.v1", "ordinary": normal,
              "instrumented": profiled, "instrumentation_action_parity": matching,
              "limits": ["No engine transitions or game outcomes are computed.",
                         "Saved replay workloads are off-policy unless separately established by their owner.",
                         "Instrumented wall timings include profiler overhead; ordinary timings are the cost result.",
                         "Hot-function data covers the first, last and selected slowest ordinary-pass steps only.",
                         "Cumulative functions overlap; do not sum their maxima or durations.",
                         "Process duration includes workload parsing, profiling, serialization and interpreter shutdown.",
                         "The one-second threshold is not a hosted timeout verdict; official overage rules are separate."]}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "parity": matching,
                      "calls": len(normal.get("calls", [])), "status": normal["status"]}))
    return 0 if matching else 2


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("entrypoint", "timing-source", "replay", "output"):
        ap.add_argument("--" + name, type=Path,
                        required=True)
    ap.add_argument("--factory", default="make_agent")
    ap.add_argument("--method", default="act")
    ap.add_argument("--seat", type=int, choices=(0, 1), default=0)
    ap.add_argument("--max-decisions", type=int, default=719)
    ap.add_argument("--classification", default="retained-public-off-policy")
    ap.add_argument("--process-timeout", type=float, default=180)
    ap.add_argument("--worker-mode", choices=("ordinary", "profile"))
    ap.add_argument("--profile-slowest", type=int, default=5)
    ap.add_argument("--profile-steps", default="")
    args = ap.parse_args()
    for name in ("entrypoint", "timing_source", "replay", "output"):
        setattr(args, name, getattr(args, name).resolve())
    if args.process_timeout <= 0:
        ap.error("--process-timeout must be positive")
    if args.profile_slowest < 1:
        ap.error("--profile-slowest must be positive")
    if args.max_decisions < 1:
        ap.error("--max-decisions must be positive")
    return worker(args) if args.worker_mode else supervise(args)


if __name__ == "__main__":
    raise SystemExit(main())
