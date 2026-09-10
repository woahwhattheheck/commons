#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Measure the causal contribution of the first returned-action divergence.

This is an offline diagnostic for two immutable TITAN archives or agent entry
points.  It discovers the first action difference on a shared baseline
trajectory, then runs two one-action interventions:

* inject the candidate action while retaining the baseline policy state;
* ablate the candidate action with the baseline action while retaining the
  candidate policy state.

The official pinned interpreter and process-isolated Actor from ``evaluate.py``
remain the execution boundary.  No hosted submission or network access occurs.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import time
from typing import Any, Callable

import evaluate as ev


SCHEMA_VERSION = 1
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_MEMBER_BYTES = 64 * 1024 * 1024


def _digest(value: Any) -> str:
    return hashlib.sha256(ev.encoded(value)).hexdigest()


def differing_paths(before: Any, after: Any, path: str = "$",) -> list[str]:
    """Return stable JSON-like paths whose leaf values differ."""
    if type(before) is not type(after):
        return [path]
    if isinstance(before, dict):
        output: list[str] = []
        for key in sorted(set(before) | set(after), key=str):
            child = f"{path}.{key}"
            if key not in before or key not in after:
                output.append(child)
            else:
                output.extend(differing_paths(before[key], after[key], child))
        return output
    if isinstance(before, list):
        output = []
        for index in range(max(len(before), len(after))):
            child = f"{path}[{index}]"
            if index >= len(before) or index >= len(after):
                output.append(child)
            else:
                output.extend(differing_paths(before[index], after[index], child))
        return output
    return [] if before == after else [path]


def _inside(root: Path, target: Path) -> bool:
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def extract_agent_archive(archive_path: Path, destination: Path) -> dict[str, Any]:
    """Extract regular files/directories only, with traversal and size bounds."""
    archive_path = archive_path.resolve(strict=True)
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    total = 0
    members = 0
    with tarfile.open(archive_path, "r:*") as archive:
        for member in archive:
            members += 1
            if member.name.startswith("/") or member.name.startswith("\\"):
                raise ValueError(f"Archive member is absolute: {member.name!r}")
            target = (destination / member.name).resolve()
            if not _inside(destination, target):
                raise ValueError(f"Archive member escapes destination: {member.name!r}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise ValueError(f"Archive member is not a regular file: {member.name!r}")
            if member.size < 0 or member.size > MAX_MEMBER_BYTES:
                raise ValueError(f"Archive member exceeds size bound: {member.name!r}")
            total += member.size
            if total > MAX_ARCHIVE_BYTES:
                raise ValueError("Archive exceeds extracted-size bound")
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"Cannot read archive member: {member.name!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name("." + target.name + ".extracting")
            try:
                with temporary.open("xb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
    entry = destination / "main.py"
    if not entry.is_file():
        raise ValueError("Agent archive has no root main.py")
    return {
        "archive_sha256": ev.sha256(archive_path),
        "archive_bytes": archive_path.stat().st_size,
        "members": members,
        "extracted_bytes": total,
        "entry_sha256": ev.sha256(entry),
    }


def materialize_agent(value: str, workspace: Path, label: str) -> tuple[str, dict[str, Any]]:
    """Resolve an archive, directory or evaluator agent specification."""
    path_text, separator, function = value.partition("::")
    path = Path(path_text).expanduser()
    if path.exists() and path.is_file() and (
        path.name.endswith(".tar.gz") or path.suffix == ".tgz"
    ):
        if separator:
            raise ValueError("Archive inputs always expose root main.py::agent")
        destination = workspace / label
        receipt = extract_agent_archive(path, destination)
        spec = str((destination / "main.py").resolve()) + "::agent"
        return spec, {"kind": "archive", "path": str(path.resolve()), **receipt}
    if path.exists() and path.is_dir():
        if separator:
            raise ValueError("Directory inputs always expose main.py::agent")
        entry = (path / "main.py").resolve(strict=True)
        spec = str(entry) + "::agent"
        return spec, {
            "kind": "directory",
            "path": str(path.resolve()),
            "entry_sha256": ev.sha256(entry),
        }
    spec = ev.resolve_spec(value)
    return spec, {"kind": "entrypoint", **ev.fingerprint(spec)}


def _configuration(engine: Any, seed: int, episode_steps: int | None) -> Any:
    cfg = ev.Struct(
        {
            key: value.get("default") if isinstance(value, dict) else value
            for key, value in engine.specification["configuration"].items()
        }
    )
    if episode_steps is not None:
        cfg.episodeSteps = episode_steps
    if not isinstance(cfg.episodeSteps, int) or cfg.episodeSteps < 2:
        raise ValueError("episodeSteps must be at least 2")
    if not isinstance(cfg.turnsPerDay, int) or cfg.turnsPerDay < 1:
        raise ValueError("turnsPerDay must be positive")
    cfg.seed = seed
    return cfg


def _metric(result: dict[str, Any], seat: int) -> dict[str, float] | None:
    scores = result.get("scores")
    if result.get("status") != "complete" or not isinstance(scores, list):
        return None
    own = float(scores[seat])
    rival = float(scores[1 - seat])
    return {"focal_score": own, "opponent_score": rival, "margin": own - rival}


def _subtract(after: dict[str, float], before: dict[str, float]) -> dict[str, float]:
    return {key: after[key] - before[key] for key in after}


def _action_response(
    actor: Any,
    observation: Any,
    configuration: Any,
    timeout: float,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    response = actor.act(observation, configuration, timeout)
    if response.get("kind") != "action":
        return None, response
    action = response.get("action")
    if not isinstance(action, dict):
        return None, {"kind": "protocol_error", "error": "Action is not an object"}
    return action, None


def run_variant(
    engine: Any,
    *,
    policy_spec: str,
    opponent_spec: str,
    cache: Path,
    loader: Path,
    seed: int,
    focal_seat: int,
    rng_seed: int,
    shadow_spec: str | None = None,
    discover: bool = False,
    intervention_step: int | None = None,
    expected_policy_action: dict[str, Any] | None = None,
    expected_shadow_action: dict[str, Any] | None = None,
    capture_step: int | None = None,
    action_timeout: float = 1.0,
    startup_timeout: float = 10.0,
    game_timeout: float = 120.0,
    episode_steps: int | None = None,
    actor_factory: Callable[..., Any] = ev.Actor,
) -> dict[str, Any]:
    """Run one policy with an optional shadow and one output-level intervention."""
    if focal_seat not in (0, 1):
        raise ValueError("focal_seat must be 0 or 1")
    if intervention_step is not None and shadow_spec is None:
        raise ValueError("An intervention requires a shadow policy")
    if intervention_step is not None and intervention_step < 0:
        raise ValueError("intervention_step must be nonnegative")
    if discover and shadow_spec is None:
        raise ValueError("Discovery requires a shadow policy")

    cfg = _configuration(engine, seed, episode_steps)
    env = ev.Struct(configuration=cfg, done=False, info={})
    state = [
        ev.Struct(observation=ev.Struct(), action={}, status="ACTIVE", reward=0)
        for _ in range(2)
    ]
    trace = hashlib.sha256()
    actors: dict[str, Any] = {}
    started = time.perf_counter()
    result: dict[str, Any] = {
        "seed": seed,
        "focal_seat": focal_seat,
        "status": "failed",
        "failure": None,
        "scores": None,
        "steps": 0,
        "episode_steps": int(cfg.episodeSteps),
        "turns_per_day": int(cfg.turnsPerDay),
        "first_divergence": None,
        "target": None,
        "captured_action": None,
    }

    def fail(kind: str, **details: Any) -> None:
        if result["failure"] is None:
            result["failure"] = {"kind": kind, **details}

    try:
        engine.interpreter(state, env)
        if cfg.get("seed") is not None:
            raise ValueError("Environment seed must not be exposed to agents")

        actors["policy"] = actor_factory(
            policy_spec, cache, loader, rng_seed, startup_timeout
        )
        actors["opponent"] = actor_factory(
            opponent_spec, cache, loader, rng_seed + 1, startup_timeout
        )
        if shadow_spec is not None:
            actors["shadow"] = actor_factory(
                shadow_spec, cache, loader, rng_seed, startup_timeout
            )
        for role, actor in actors.items():
            ready = actor.ready
            if ready.get("kind") != "ready":
                fail("startup", role=role, response=ready)
                break

        if result["failure"] is None:
            for step in range(cfg.episodeSteps):
                remaining = game_timeout - (time.perf_counter() - started)
                if remaining <= 0:
                    fail("game_timeout", step=step)
                    break

                focal_observation = state[focal_seat].observation
                rival_observation = state[1 - focal_seat].observation
                for observation in (focal_observation, rival_observation):
                    observation.step = step
                    observation.remainingOverageTime = 0

                policy_action, error = _action_response(
                    actors["policy"], focal_observation, cfg, min(action_timeout, remaining)
                )
                if error is not None:
                    fail("action", role="policy", step=step, response=error)
                    break

                need_shadow = (
                    shadow_spec is not None
                    and (
                        (discover and result["first_divergence"] is None)
                        or (intervention_step is not None and step <= intervention_step)
                    )
                )
                shadow_action = None
                if need_shadow:
                    remaining = game_timeout - (time.perf_counter() - started)
                    if remaining <= 0:
                        fail("game_timeout", step=step)
                        break
                    shadow_action, error = _action_response(
                        actors["shadow"],
                        focal_observation,
                        cfg,
                        min(action_timeout, remaining),
                    )
                    if error is not None:
                        fail("action", role="shadow", step=step, response=error)
                        break

                if discover and shadow_action is not None and policy_action != shadow_action:
                    result["first_divergence"] = {
                        "step": step,
                        "day": step // int(cfg.turnsPerDay),
                        "within_day": step % int(cfg.turnsPerDay),
                        "observation_sha256": _digest(focal_observation),
                        "prefix_trace_sha256": trace.hexdigest(),
                        "policy_action": policy_action,
                        "shadow_action": shadow_action,
                        "policy_action_sha256": _digest(policy_action),
                        "shadow_action_sha256": _digest(shadow_action),
                        "differing_paths": differing_paths(policy_action, shadow_action),
                    }

                if intervention_step is not None and step < intervention_step:
                    if shadow_action is None or policy_action != shadow_action:
                        fail(
                            "prefix_mismatch",
                            step=step,
                            policy_action_sha256=_digest(policy_action),
                            shadow_action_sha256=(
                                _digest(shadow_action) if shadow_action is not None else None
                            ),
                        )
                        break

                executed_action = policy_action
                if intervention_step is not None and step == intervention_step:
                    if shadow_action is None:
                        fail("missing_shadow_action", step=step)
                        break
                    if (
                        expected_policy_action is not None
                        and policy_action != expected_policy_action
                    ):
                        fail(
                            "target_policy_mismatch",
                            step=step,
                            expected_sha256=_digest(expected_policy_action),
                            actual_sha256=_digest(policy_action),
                        )
                        break
                    if (
                        expected_shadow_action is not None
                        and shadow_action != expected_shadow_action
                    ):
                        fail(
                            "target_shadow_mismatch",
                            step=step,
                            expected_sha256=_digest(expected_shadow_action),
                            actual_sha256=_digest(shadow_action),
                        )
                        break
                    executed_action = shadow_action
                    result["target"] = {
                        "step": step,
                        "day": step // int(cfg.turnsPerDay),
                        "within_day": step % int(cfg.turnsPerDay),
                        "observation_sha256": _digest(focal_observation),
                        "prefix_trace_sha256": trace.hexdigest(),
                        "policy_action": policy_action,
                        "shadow_action": shadow_action,
                        "executed_action": executed_action,
                        "policy_action_sha256": _digest(policy_action),
                        "shadow_action_sha256": _digest(shadow_action),
                        "executed_action_sha256": _digest(executed_action),
                        "differing_paths": differing_paths(policy_action, shadow_action),
                    }

                if capture_step is not None and step == capture_step:
                    result["captured_action"] = {
                        "step": step,
                        "observation_sha256": _digest(focal_observation),
                        "prefix_trace_sha256": trace.hexdigest(),
                        "action": policy_action,
                        "action_sha256": _digest(policy_action),
                    }

                remaining = game_timeout - (time.perf_counter() - started)
                if remaining <= 0:
                    fail("game_timeout", step=step)
                    break
                rival_action, error = _action_response(
                    actors["opponent"],
                    rival_observation,
                    cfg,
                    min(action_timeout, remaining),
                )
                if error is not None:
                    fail("action", role="opponent", step=step, response=error)
                    break

                actions = [None, None]
                actions[focal_seat] = executed_action
                actions[1 - focal_seat] = rival_action
                for seat in range(2):
                    state[seat].action = actions[seat]
                engine.interpreter(state, env)
                result["steps"] += 1
                bank = [
                    float(state[0].observation.farms[index]["money"])
                    for index in range(2)
                ]
                trace.update(ev.encoded({"step": step, "actions": actions, "bank": bank}))
                done = all(item.status == "DONE" for item in state)
                if done:
                    scores = [item.reward for item in state]
                    if not all(
                        isinstance(score, (int, float)) and math.isfinite(score)
                        for score in scores
                    ):
                        raise ValueError("Nonfinite or missing terminal score")
                    result.update(status="complete", scores=scores)
                    env.done = True
                    break
            if result["failure"] is None and result["status"] != "complete":
                fail("incomplete", step=result["steps"])
    except Exception as exc:
        fail("engine_error", step=result["steps"], error=f"{type(exc).__name__}: {exc}"[:1000])
    finally:
        for actor in actors.values():
            actor.close()
        result["actors"] = {
            role: actor.report() for role, actor in actors.items()
        }
        result["wall_seconds"] = time.perf_counter() - started
        try:
            trace.update(ev.encoded([item.observation for item in state]))
        except (TypeError, ValueError, OverflowError):
            pass
        result["trace_sha256"] = trace.hexdigest()
    return result


def _classify(treatment: float, ablation: float, tolerance: float = 1e-9) -> str:
    if treatment > tolerance and ablation > tolerance:
        return "supported"
    if treatment < -tolerance and ablation < -tolerance:
        return "harmful"
    if abs(treatment) <= tolerance and abs(ablation) <= tolerance:
        return "neutral"
    return "mixed"


def evaluate_cell(
    engine: Any,
    *,
    baseline_spec: str,
    candidate_spec: str,
    opponent_spec: str,
    cache: Path,
    loader: Path,
    seed: int,
    focal_seat: int,
    rng_seed: int = 20260907,
    action_timeout: float = 1.0,
    startup_timeout: float = 10.0,
    game_timeout: float = 120.0,
    episode_steps: int | None = None,
    actor_factory: Callable[..., Any] = ev.Actor,
) -> dict[str, Any]:
    """Evaluate one seed/seat cell with replay, treatment and ablation."""
    common = dict(
        engine=engine,
        opponent_spec=opponent_spec,
        cache=cache,
        loader=loader,
        seed=seed,
        focal_seat=focal_seat,
        rng_seed=rng_seed,
        action_timeout=action_timeout,
        startup_timeout=startup_timeout,
        game_timeout=game_timeout,
        episode_steps=episode_steps,
        actor_factory=actor_factory,
    )
    discovery = run_variant(
        policy_spec=baseline_spec,
        shadow_spec=candidate_spec,
        discover=True,
        **common,
    )
    cell: dict[str, Any] = {
        "seed": seed,
        "focal_seat": focal_seat,
        "classification": "failed",
        "divergence": discovery.get("first_divergence"),
        "runs": {"baseline_discovery": discovery},
        "effects": None,
    }
    if discovery["status"] != "complete":
        return cell

    divergence = discovery["first_divergence"]
    capture = None if divergence is None else int(divergence["step"])
    baseline_replay = run_variant(
        policy_spec=baseline_spec,
        capture_step=capture,
        **common,
    )
    cell["runs"]["baseline_replay"] = baseline_replay
    if baseline_replay["status"] != "complete":
        return cell
    if (
        baseline_replay["trace_sha256"] != discovery["trace_sha256"]
        or baseline_replay["scores"] != discovery["scores"]
    ):
        cell["classification"] = "unstable"
        cell["replay"] = {
            "same_trace": baseline_replay["trace_sha256"] == discovery["trace_sha256"],
            "same_scores": baseline_replay["scores"] == discovery["scores"],
        }
        return cell

    if divergence is None:
        cell["classification"] = "dormant"
        cell["replay"] = {"same_trace": True, "same_scores": True}
        return cell

    target_step = int(divergence["step"])
    baseline_action = divergence["policy_action"]
    candidate_action = divergence["shadow_action"]
    replay_capture = baseline_replay.get("captured_action")
    if (
        replay_capture is None
        or replay_capture["action"] != baseline_action
        or replay_capture["observation_sha256"] != divergence["observation_sha256"]
        or replay_capture["prefix_trace_sha256"] != divergence["prefix_trace_sha256"]
    ):
        cell["classification"] = "unstable"
        cell["replay"] = {"same_trace": True, "same_scores": True, "target_reproduced": False}
        return cell

    candidate_native = run_variant(
        policy_spec=candidate_spec,
        capture_step=target_step,
        **common,
    )
    candidate_replay = run_variant(
        policy_spec=candidate_spec,
        capture_step=target_step,
        **common,
    )
    injection = run_variant(
        policy_spec=baseline_spec,
        shadow_spec=candidate_spec,
        intervention_step=target_step,
        expected_policy_action=baseline_action,
        expected_shadow_action=candidate_action,
        **common,
    )
    ablation = run_variant(
        policy_spec=candidate_spec,
        shadow_spec=baseline_spec,
        intervention_step=target_step,
        expected_policy_action=candidate_action,
        expected_shadow_action=baseline_action,
        **common,
    )
    cell["runs"].update(
        candidate_native=candidate_native,
        candidate_replay=candidate_replay,
        candidate_action_on_baseline=injection,
        baseline_action_on_candidate=ablation,
    )
    if any(
        run["status"] != "complete"
        for run in (candidate_native, candidate_replay, injection, ablation)
    ):
        return cell
    if (
        candidate_replay["trace_sha256"] != candidate_native["trace_sha256"]
        or candidate_replay["scores"] != candidate_native["scores"]
    ):
        cell["classification"] = "unstable"
        cell["replay"] = {
            "same_trace": True,
            "same_scores": True,
            "target_reproduced": True,
            "candidate_replay_same_trace": (
                candidate_replay["trace_sha256"] == candidate_native["trace_sha256"]
            ),
            "candidate_replay_same_scores": (
                candidate_replay["scores"] == candidate_native["scores"]
            ),
        }
        return cell

    candidate_capture = candidate_native.get("captured_action")
    if (
        candidate_capture is None
        or candidate_capture["action"] != candidate_action
        or candidate_capture["observation_sha256"] != divergence["observation_sha256"]
        or candidate_capture["prefix_trace_sha256"] != divergence["prefix_trace_sha256"]
    ):
        cell["classification"] = "unstable"
        cell["replay"] = {
            "same_trace": True,
            "same_scores": True,
            "target_reproduced": True,
            "candidate_prefix_reproduced": False,
        }
        return cell

    baseline_metrics = _metric(discovery, focal_seat)
    candidate_metrics = _metric(candidate_native, focal_seat)
    injection_metrics = _metric(injection, focal_seat)
    ablation_metrics = _metric(ablation, focal_seat)
    assert all(
        metrics is not None
        for metrics in (
            baseline_metrics,
            candidate_metrics,
            injection_metrics,
            ablation_metrics,
        )
    )
    effects = {
        "candidate_native_minus_baseline": _subtract(candidate_metrics, baseline_metrics),
        "candidate_action_on_baseline": _subtract(injection_metrics, baseline_metrics),
        "candidate_action_on_candidate": _subtract(candidate_metrics, ablation_metrics),
    }
    cell["effects"] = effects
    cell["classification"] = _classify(
        effects["candidate_action_on_baseline"]["margin"],
        effects["candidate_action_on_candidate"]["margin"],
    )
    cell["replay"] = {
        "same_trace": True,
        "same_scores": True,
        "target_reproduced": True,
        "candidate_prefix_reproduced": True,
        "candidate_replay_same_trace": True,
        "candidate_replay_same_scores": True,
    }
    return cell


def summarize(cells: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(cell["classification"] for cell in cells)
    complete = [
        cell for cell in cells if cell.get("effects") is not None
    ]
    mean_effects: dict[str, dict[str, float]] = {}
    for name in (
        "candidate_native_minus_baseline",
        "candidate_action_on_baseline",
        "candidate_action_on_candidate",
    ):
        rows = [cell["effects"][name] for cell in complete]
        if rows:
            mean_effects[name] = {
                metric: sum(row[metric] for row in rows) / len(rows)
                for metric in ("focal_score", "opponent_score", "margin")
            }
    return {
        "scheduled": len(cells),
        "classifications": dict(sorted(counts.items())),
        "causal_cells": len(complete),
        "mean_effects": mean_effects,
    }


def _parse_ints(value: str, *, allowed: set[int] | None = None) -> list[int]:
    parsed = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not parsed or len(parsed) != len(set(parsed)):
        raise ValueError("Values must be distinct comma-separated integers")
    if allowed is not None and not set(parsed) <= allowed:
        raise ValueError(f"Values must be drawn from {sorted(allowed)}")
    return parsed


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, default=Path(__file__).resolve().parent.parent / "engine")
    parser.add_argument("--loader", type=Path, default=ev.LOADER)
    parser.add_argument("--baseline", required=True, help="Archive, directory, or path.py::agent")
    parser.add_argument("--candidate", required=True, help="Archive, directory, or path.py::agent")
    parser.add_argument("--opponent", default="official_starter")
    parser.add_argument("--seeds", default="2027")
    parser.add_argument("--seats", default="0,1")
    parser.add_argument("--rng-seed", type=int, default=20260907)
    parser.add_argument("--action-timeout", type=float, default=1.0)
    parser.add_argument("--startup-timeout", type=float, default=10.0)
    parser.add_argument("--game-timeout", type=float, default=120.0)
    parser.add_argument("--episode-steps", type=int)
    parser.add_argument("--output", type=Path, default=Path("causal-action-splice.json"))
    args = parser.parse_args()

    for value in (args.action_timeout, args.startup_timeout, args.game_timeout):
        if not math.isfinite(value) or value <= 0:
            parser.error("Timeouts must be finite and positive")
    try:
        seeds = _parse_ints(args.seeds)
        seats = _parse_ints(args.seats, allowed={0, 1})
    except ValueError as exc:
        parser.error(str(exc))

    engine, engine_hashes = ev.get_engine(args.engine_dir, args.loader)
    with tempfile.TemporaryDirectory(prefix="titan-causal-splice-") as directory:
        workspace = Path(directory)
        baseline_spec, baseline_input = materialize_agent(
            args.baseline, workspace, "baseline"
        )
        candidate_spec, candidate_input = materialize_agent(
            args.candidate, workspace, "candidate"
        )
        opponent_spec = ev.resolve_spec(args.opponent)
        cells = []
        for seed in seeds:
            for seat in seats:
                cell = evaluate_cell(
                    engine,
                    baseline_spec=baseline_spec,
                    candidate_spec=candidate_spec,
                    opponent_spec=opponent_spec,
                    cache=args.engine_dir,
                    loader=args.loader,
                    seed=seed,
                    focal_seat=seat,
                    rng_seed=args.rng_seed,
                    action_timeout=args.action_timeout,
                    startup_timeout=args.startup_timeout,
                    game_timeout=args.game_timeout,
                    episode_steps=args.episode_steps,
                )
                cells.append(cell)
                print(
                    json.dumps(
                        {
                            "seed": seed,
                            "focal_seat": seat,
                            "classification": cell["classification"],
                            "step": (
                                None
                                if cell["divergence"] is None
                                else cell["divergence"]["step"]
                            ),
                            "effects": cell["effects"],
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )

        report = {
            "schema_version": SCHEMA_VERSION,
            "method": (
                "First returned-action divergence on a shared baseline prefix; "
                "baseline replay; candidate-action treatment under baseline policy "
                "continuation; baseline-action ablation under candidate policy "
                "continuation. Output-level effects do not by themselves attribute "
                "the whole feature or predict hosted leaderboard score."
            ),
            "engine_ref": ev.ENGINE_REF,
            "engine_sha256": engine_hashes,
            "loader_sha256": ev.sha256(args.loader),
            "evaluator_sha256": ev.sha256(ev.__file__),
            "splice_evaluator_sha256": ev.sha256(__file__),
            "inputs": {
                "baseline": baseline_input,
                "candidate": candidate_input,
                "opponent": ev.fingerprint(opponent_spec),
            },
            "seeds": seeds,
            "seats": seats,
            "agent_rng_seed": args.rng_seed,
            "limits": {
                "action_rpc_seconds": args.action_timeout,
                "startup_seconds": args.startup_timeout,
                "game_seconds": args.game_timeout,
                "episode_steps_override": args.episode_steps,
            },
            "summary": summarize(cells),
            "cells": cells,
        }
        _write_json(args.output, report)
        print("SUMMARY " + json.dumps(report["summary"], sort_keys=True), flush=True)
        bad = {"failed", "unstable"}
        return int(any(cell["classification"] in bad for cell in cells))


if __name__ == "__main__":
    raise SystemExit(main())
